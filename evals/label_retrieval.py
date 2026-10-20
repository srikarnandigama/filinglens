"""Interactive human-only retrieval labeling. No questions or labels are generated."""

import argparse
import asyncio
import json
import os
import pydoc
import sys
from pathlib import Path
from uuid import uuid4

from psycopg.rows import dict_row

from filinglens.config import ROOT, Settings
from filinglens.db import pool_for
from filinglens.ingest.embed import embedding_fingerprint
from filinglens.ingest.identity import digest
from filinglens.retrieval.service import MODES, ChunkHit, SearchService, hit


def atomic_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temporary, path)


def load_records(path: Path) -> list[dict]:
    if not path.exists():
        return []
    records = [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]
    ids = [r["id"] for r in records]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate question IDs in label file")
    return records


def save_record(path: Path, record: dict, valid_ids: set[str]) -> None:
    gold = record.get("gold_chunk_ids", [])
    if not record.get("question", "").strip() or not gold:
        raise ValueError("A finalized record needs your question and at least one gold chunk")
    if not set(gold) <= valid_ids:
        raise ValueError("Gold IDs must belong to this corpus")
    record = record | {"gold_chunk_ids": sorted(set(gold))}
    records = load_records(path)
    if any(r["corpus_id"] != record["corpus_id"] for r in records):
        raise ValueError("Use separate label files for different corpora")
    records = [r for r in records if r["id"] != record["id"]] + [record]
    records.sort(key=lambda r: r["id"])
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".jsonl.tmp")
    temporary.write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records), encoding="utf-8"
    )
    os.replace(temporary, path)


async def candidates(service: SearchService, question: str, filters: dict, depth: int):
    union: dict[str, ChunkHit] = {}
    ranks: dict[str, dict[str, int]] = {}
    for mode in MODES:
        for rank, value in enumerate(
            await service.search(question, mode=mode, k=depth, **filters), 1
        ):
            union[value.chunk_id] = value
            ranks.setdefault(value.chunk_id, {})[mode] = rank
    return [union[key] for key in sorted(union)], ranks


def display(value: ChunkHit, ranks: dict | None = None) -> str:
    return (
        f"{value.chunk_id}\n{value.ticker} | {value.form} {value.accession} | "
        f"FY{value.fiscal_year} {value.fiscal_period} | report {value.report_date}\n"
        f"{value.item}: {value.title}\n{value.url}\n"
        f"Mode ranks: {ranks or {}}\n\n{value.text}\n"
    )


def candidate_index(values: list[ChunkHit], gold: list[str]) -> None:
    print(f"{len(values)} combined candidates; use show for full text or pool to page all.")
    for number, value in enumerate(values, 1):
        marker = "*" if value.chunk_id in gold else " "
        print(
            f"{number}{marker} {value.chunk_id}\n"
            f"  {value.ticker} {value.form} {value.accession} "
            f"FY{value.fiscal_year} {value.fiscal_period} {value.item}: {value.title}\n"
            f"  {value.text[:160].replace(chr(10), ' ')}"
        )


async def freeze_ready_corpus(pool, corpus_id: str) -> tuple[set[str], str]:
    async with pool.connection() as conn:
        corpus = await (
            await conn.execute(
                "SELECT configuration FROM retrieval_corpora WHERE id=%s FOR UPDATE", (corpus_id,)
            )
        ).fetchone()
        if not corpus:
            raise ValueError("Unknown corpus")
        docs = await (
            await conn.execute(
                "SELECT accession,source_hash,status FROM corpus_documents WHERE corpus_id=%s "
                "ORDER BY accession",
                (corpus_id,),
            )
        ).fetchall()
        rows = await (
            await conn.execute(
                "SELECT c.id,c.embedding IS NOT NULL,c.embedding_fingerprint, "
                "c.embedding_input_hash,c.context_header,c.text,c.oversized_row FROM chunks c "
                "JOIN corpus_chunks cc ON cc.chunk_id=c.id WHERE cc.corpus_id=%s ORDER BY c.id",
                (corpus_id,),
            )
        ).fetchall()
        expected = corpus[0].get("filing_count")
        if not docs or (expected is not None and len(docs) != expected):
            raise ValueError("Corpus parsing is incomplete")
        if any(d[2] != "complete" for d in docs) or not rows:
            raise ValueError("Corpus has incomplete documents or no chunks")
        if any(
            not r[1] or r[2] != embedding_fingerprint() or r[3] != digest([r[4], r[5], r[6]])
            for r in rows
        ):
            raise ValueError("Full corpus embedding must finish before labeling")
        await conn.execute("UPDATE retrieval_corpora SET frozen=TRUE WHERE id=%s", (corpus_id,))
        return {r[0] for r in rows}, digest([corpus[0], docs, [r[0] for r in rows]])


async def interactive(args) -> None:
    settings = Settings()
    corpus_id = args.corpus or settings.retrieval_corpus
    if not corpus_id:
        raise ValueError("Pass --corpus or set RETRIEVAL_CORPUS")
    draft_path = args.output.with_suffix(".draft.json")
    async with pool_for(settings.database_url) as pool:
        valid_ids, corpus_hash = await freeze_ready_corpus(pool, corpus_id)
        service = SearchService(pool, corpus_id)
        record = None
        if draft_path.exists():
            draft = json.loads(draft_path.read_text(encoding="utf-8"))
            if draft["corpus_id"] == corpus_id:
                record = draft
                print("Resuming your draft.")
        while True:
            if record is None:
                question = input("Your question (or :quit / :edit QUESTION_ID): ").strip()
                if question == ":quit":
                    return
                if question.startswith(":edit "):
                    key = question.split(maxsplit=1)[1]
                    record = next((r for r in load_records(args.output) if r["id"] == key), None)
                    if record is None:
                        print("Question ID not found.")
                        continue
                elif question:
                    record = {
                        "id": "hq_" + uuid4().hex,
                        "question": question,
                        "corpus_id": corpus_id,
                        "corpus_hash": corpus_hash,
                        "filters": {},
                        "gold_chunk_ids": [],
                    }
                else:
                    continue
            atomic_json(draft_path, record)
            try:
                values, ranks = await candidates(
                    service, record["question"], record["filters"], args.depth
                )
            except ValueError as error:
                print(f"Search needs a correction: {error}")
                replacement = input("Edit your question (or :quit to preserve the draft): ").strip()
                if replacement == ":quit":
                    return
                if replacement:
                    record["question"] = replacement
                    atomic_json(draft_path, record)
                continue
            atomic_json(draft_path, record)
            print(record["question"])
            candidate_index(values, record["gold_chunk_ids"])
            print("Commands: list, pool, show N/ID, mark N/ID, unmark N/ID, more DEPTH,")
            print("filters JSON, browse ACCESSION [ITEM], reference, save, quit")
            while True:
                command = input("label> ").strip()
                verb, _, argument = command.partition(" ")
                try:
                    if verb == "quit":
                        return
                    if verb == "unmark" and argument in record["gold_chunk_ids"]:
                        record["gold_chunk_ids"].remove(argument)
                        atomic_json(draft_path, record)
                        continue
                    if verb == "list":
                        candidate_index(values, record["gold_chunk_ids"])
                    elif verb == "pool":
                        pydoc.pager("\n\n".join(display(v, ranks.get(v.chunk_id)) for v in values))
                    elif verb in {"show", "mark", "unmark"}:
                        value = (
                            values[int(argument) - 1]
                            if argument.isdigit()
                            else next(v for v in values if v.chunk_id == argument)
                        )
                        if argument.isdigit() and int(argument) < 1:
                            raise ValueError("Selection numbers start at 1")
                        if verb == "show":
                            pydoc.pager(display(value, ranks.get(value.chunk_id)))
                        elif verb == "mark":
                            record["gold_chunk_ids"] = sorted(
                                set([*record["gold_chunk_ids"], value.chunk_id])
                            )
                        else:
                            record["gold_chunk_ids"] = [
                                x for x in record["gold_chunk_ids"] if x != value.chunk_id
                            ]
                    elif verb in {"more", "filters"}:
                        if verb == "filters":
                            proposed = json.loads(argument)
                            if not isinstance(proposed, dict) or set(proposed) - {
                                "ticker",
                                "fiscal_year",
                                "fiscal_period",
                                "items",
                            }:
                                raise ValueError("Unsupported filters")
                            record["filters"] = proposed
                        else:
                            args.depth = int(argument)
                        values, ranks = await candidates(
                            service, record["question"], record["filters"], args.depth
                        )
                    elif verb == "browse":
                        accession, *item = argument.split()
                        async with pool.connection() as conn:
                            conn.row_factory = dict_row
                            extra = " AND c.item=%s" if item else ""
                            rows = await (
                                await conn.execute(
                                    "SELECT c.*,co.ticker,s.title,f.report_date,f.url "
                                    f"{service.source} "
                                    f"WHERE cc.corpus_id=%s AND c.accession=%s {extra} "
                                    "ORDER BY s.item,c.ordinal",
                                    [corpus_id, accession, *item],
                                )
                            ).fetchall()
                        values = list(
                            {v.chunk_id: v for v in [*values, *(hit(r, 0) for r in rows)]}.values()
                        )
                        print(f"{len(rows)} chunks added; use list/show/mark.")
                    elif verb == "reference":
                        record["reference_answer"] = input("Your reference answer: ")
                    elif verb == "save":
                        save_record(args.output, record, valid_ids)
                        draft_path.unlink(missing_ok=True)
                        print(f"Saved {record['id']}; {len(load_records(args.output))} questions.")
                        record = None
                        break
                    else:
                        print("Unknown command.")
                    atomic_json(draft_path, record)
                except (ValueError, IndexError, StopIteration) as error:
                    print(f"Cannot apply command: {error}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus")
    parser.add_argument("--output", type=Path, default=ROOT / "evals/handwritten.jsonl")
    parser.add_argument("--depth", type=int, default=30)
    args = parser.parse_args()
    if args.depth < 1:
        parser.error("--depth must be positive")
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    try:
        asyncio.run(interactive(args))
    except (KeyboardInterrupt, EOFError):
        print("Draft preserved. Run the same command to resume.")
    except ValueError as error:
        parser.exit(2, f"{error}\n")


if __name__ == "__main__":
    main()

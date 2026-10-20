"""Offline corpus repair audit, exact label migration, and vector reuse.

No relevance judgments or retrieval evaluation. All writes target new corpus rows
or explicitly named v2 artifacts. Run from the project root.
"""

import argparse
import asyncio
import hashlib
import json
from collections import Counter
from pathlib import Path

from psycopg.rows import dict_row

from filinglens.config import Settings
from filinglens.db import INGESTION_LOCK, INGESTION_UNLOCK, pool_for
from filinglens.ingest.embed import embedding_fingerprint, input_fingerprint
from filinglens.ingest.identity import digest

V1 = "corpus_2fb48958e274daed46c19e3fbf2583213e308b1eebaa16a04cfdc8052eea82e7"
BASELINE = Path("docs/CORPUS_V2_BASELINE.json")
LABELS = Path("evals/handwritten.jsonl")
V2_LABELS = Path("evals/handwritten_v2.jsonl")
MANIFEST = Path("evals/corpus_v2_migration.json")


def repaired(ticker, form, item):
    return (
        form == "10-K"
        and (
            ticker in {"CVX", "JPM", "XOM"}
            and item in {"7", "7A", "8"}
            or ticker in {"DIS", "NVDA"}
            and item == "8"
        )
        or form == "10-Q"
        and ticker in {"BAC", "JPM"}
        and item == "P1-2"
    )


async def immutable_state(pool):
    state = {}
    async with pool.connection() as c:
        c.row_factory = dict_row
        for table, order in [
            ("financial_facts", "id"),
            ("companies", "cik"),
            ("filings", "accession"),
            ("ingestion_snapshots", "id"),
            ("metric_availability", "cik,metric,fiscal_year,fiscal_period"),
        ]:
            rows = await (await c.execute(f"SELECT * FROM {table} ORDER BY {order}")).fetchall()
            state[table] = {
                "count": len(rows),
                "sha256": hashlib.sha256(
                    json.dumps(rows, default=str, sort_keys=True).encode()
                ).hexdigest(),
            }
        for query, key in [
            (
                "SELECT * FROM chunks WHERE id IN "
                "(SELECT chunk_id FROM corpus_chunks WHERE corpus_id=%s) ORDER BY id",
                "v1_chunks",
            ),
            (
                "SELECT * FROM corpus_documents WHERE corpus_id=%s ORDER BY accession",
                "v1_documents",
            ),
            ("SELECT * FROM retrieval_corpora WHERE id=%s", "v1_corpus"),
        ]:
            rows = await (await c.execute(query, (V1,))).fetchall()
            state[key] = {
                "count": len(rows),
                "sha256": hashlib.sha256(
                    json.dumps(rows, default=str, sort_keys=True).encode()
                ).hexdigest(),
            }
    baseline = json.loads(BASELINE.read_text())
    # Phase C explicitly authorizes updating the living milestone status. Keep
    # historical reports and every other protected artifact in the baseline.
    baseline["files"] = {
        p: value for p, value in baseline["files"].items() if Path(p).name != "M2_STATUS.md"
    }
    state["files"] = {
        p: hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in baseline["files"]
    }
    if state != baseline:
        raise ValueError(
            "Immutable v1/M1 baseline changed: "
            + str([k for k in state if state[k] != baseline[k]])
        )
    return state


async def read_corpus(pool, corpus_id):
    async with pool.connection() as c:
        c.row_factory = dict_row
        config = await (
            await c.execute("SELECT * FROM retrieval_corpora WHERE id=%s", (corpus_id,))
        ).fetchone()
        docs = await (
            await c.execute(
                "SELECT d.*,f.form,f.fiscal_year,f.fiscal_period,f.url,co.ticker "
                "FROM corpus_documents d "
                "JOIN filings f USING(accession) JOIN companies co USING(cik) "
                "WHERE corpus_id=%s ORDER BY accession",
                (corpus_id,),
            )
        ).fetchall()
        sections = await (
            await c.execute(
                "SELECT s.* FROM sections s WHERE EXISTS (SELECT 1 FROM chunks c "
                "JOIN corpus_chunks cc ON cc.chunk_id=c.id "
                "WHERE c.section_id=s.id AND cc.corpus_id=%s)",
                (corpus_id,),
            )
        ).fetchall()
        chunks = await (
            await c.execute(
                "SELECT c.*,co.ticker FROM chunks c JOIN corpus_chunks cc ON cc.chunk_id=c.id "
                "JOIN companies co USING(cik) WHERE cc.corpus_id=%s ORDER BY c.id",
                (corpus_id,),
            )
        ).fetchall()
    return config, docs, sections, chunks


async def audit(pool, corpus_id):
    if corpus_id == V1:
        raise ValueError("v2 actions require a new corpus")
    await immutable_state(pool)
    old_config, old_docs, old_sections, old_chunks = await read_corpus(pool, V1)
    config, docs, sections, chunks = await read_corpus(pool, corpus_id)
    if not config or config["configuration"].get("resolver") != "financial-references-v1":
        raise ValueError("Not a v2 resolver corpus")
    if len(docs) != len(old_docs) or any(d["status"] != "complete" for d in docs):
        raise ValueError("Incomplete documents")
    if {(d["accession"], d["source_hash"]) for d in docs} != {
        (d["accession"], d["source_hash"]) for d in old_docs
    }:
        raise ValueError("v2 must use exactly the same verified primary documents")
    if set(c["id"] for c in old_chunks) & set(c["id"] for c in chunks):
        raise ValueError("v1/v2 IDs overlap")
    old_s = {(s["accession"], s["item"]): s for s in old_sections}
    new_s = {(s["accession"], s["item"]): s for s in sections}
    old_counts = Counter((c["accession"], c["item"]) for c in old_chunks)
    new_counts = Counter((c["accession"], c["item"]) for c in chunks)
    old_texts = {}
    new_texts = {}
    for source, destination in [(old_chunks, old_texts), (chunks, new_texts)]:
        for c in source:
            destination.setdefault((c["accession"], c["item"]), []).append(
                (
                    c["ordinal"],
                    c["text"],
                    c["context_header"],
                    c["oversized_row"],
                    c["token_count"],
                    c["source_start"],
                    c["source_end"],
                )
            )
    rows = []
    ownership = []
    unexpected = []
    unresolved = []
    migration = []
    affected = []
    new_by_text = {}
    for chunk in chunks:
        new_by_text.setdefault((chunk["accession"], chunk["item"], chunk["text"]), []).append(chunk)
    old_by_id = {c["id"]: c for c in old_chunks}
    records = [
        json.loads(line) for line in LABELS.read_text(encoding="utf-8").splitlines() if line.strip()
    ]
    for doc in docs:
        if doc["details"].get("unresolved_substantive"):
            unresolved.append(doc["accession"])
        for item in ["1", "1A", "7", "7A", "8"] if doc["form"] == "10-K" else ["P1-2", "P2-1A"]:
            key = (doc["accession"], item)
            a, b = old_s.get(key), new_s.get(key)
            same = (a["text"] if a else None) == (b["text"] if b else None)
            same_blocks = (a["blocks"] if a else None) == (b["blocks"] if b else None)
            same_chunks = sorted(old_texts.get(key, [])) == sorted(new_texts.get(key, []))
            repair = repaired(doc["ticker"], doc["form"], item)
            if not repair and (not same or not same_chunks or not same_blocks):
                unexpected.append(key)
            detail = doc["details"]["coverage"][item]
            rows.append(
                {k: doc[k] for k in ["ticker", "fiscal_year", "fiscal_period", "form", "accession"]}
                | {
                    "item": item,
                    "v1_chunks": old_counts[key],
                    "v2_chunks": new_counts[key],
                    "approved_repair": repair,
                    "source_hash": doc["source_hash"],
                    "source_url": doc["url"],
                    "section_byte_identical": same,
                    "blocks_identical": same_blocks,
                    "chunk_inputs_identical": same_chunks,
                    "coverage": detail,
                }
            )
        if doc["form"] == "10-K" and doc["ticker"] in {"CVX", "JPM", "XOM", "DIS", "NVDA"}:
            ownership.append(
                {k: doc[k] for k in ["ticker", "fiscal_year", "accession"]}
                | {
                    "rule": doc["details"]["coverage"]["7A"].get(
                        "ownership", "separate section outside MD&A"
                    ),
                    "target_item": doc["details"]["coverage"]["7A"].get("target_item", "7A"),
                }
            )
    for record in records:
        gold = []
        for old_id in record["gold_chunk_ids"]:
            old = old_by_id[old_id]
            matches = new_by_text.get((old["accession"], old["item"], old["text"]), [])
            gold.append(
                {
                    "old_id": old_id,
                    "accession": old["accession"],
                    "item": old["item"],
                    "status": "unique exact match"
                    if len(matches) == 1
                    else "unmatched"
                    if not matches
                    else "ambiguous",
                    "new_ids": [c["id"] for c in matches],
                    **(
                        {
                            "old_text": old["text"],
                            "candidate_passages": [
                                {"id": c["id"], "text": c["text"]}
                                for c in chunks
                                if c["accession"] == old["accession"] and c["item"] == old["item"]
                            ],
                        }
                        if len(matches) != 1
                        else {}
                    ),
                }
            )
        migration.append({"id": record["id"], "question": record["question"], "gold": gold})
        filters = record["filters"]
        covered = [
            r
            for r in rows
            if r["approved_repair"]
            and all(r[k] == v for k, v in filters.items() if k != "items")
            and ("items" not in filters or r["item"] in filters["items"])
        ]
        if covered:
            affected.append(
                {
                    "id": record["id"],
                    "question": record["question"],
                    "filters": filters,
                    "repaired_sections": [
                        {
                            k: r[k]
                            for k in ["accession", "item", "fiscal_year", "v1_chunks", "v2_chunks"]
                        }
                        for r in covered
                    ],
                }
            )
    migration_errors = [
        g for r in migration for g in r["gold"] if g["status"] != "unique exact match"
    ]
    report = {
        "v1": V1,
        "v2": corpus_id,
        "v1_chunks": len(old_chunks),
        "v2_chunks": len(chunks),
        "frozen": config["frozen"],
        "processing_fingerprint": digest(
            {k: v for k, v in config["configuration"].items() if k != "filing_count"}
        ),
        "corpus_hash": digest(
            [
                config["configuration"],
                [(d["accession"], d["source_hash"], d["status"]) for d in docs],
                sorted(c["id"] for c in chunks),
            ]
        ),
        "filings": len(docs),
        "items": rows,
        "ownership": ownership,
        "unexpected_changes": unexpected,
        "unresolved_substantive": unresolved,
        "migration": migration,
        "migration_errors": migration_errors,
        "review_questions": affected,
        "immutable_baseline_unchanged": True,
    }
    if unexpected or unresolved or migration_errors:
        raise ValueError(
            "Freeze blocked: "
            + json.dumps(
                {
                    k: report[k]
                    for k in ["unexpected_changes", "unresolved_substantive", "migration_errors"]
                }
            )
        )
    return report, config, docs, chunks, records


async def reuse_vectors(pool, corpus_id):
    async with pool.connection() as c:
        if not (await (await c.execute(INGESTION_LOCK)).fetchone())[0]:
            raise RuntimeError("Another ingestion process is active")
        try:
            report, config, docs, chunks, records = await audit(pool, corpus_id)
            if config["frozen"]:
                raise ValueError("Frozen corpus cannot receive copied vectors")
            _, _, _, old = await read_corpus(pool, V1)
            reusable = {}
            fp = embedding_fingerprint()
            for row in old:
                if (
                    row["embedding"] is not None
                    and row["embedding_fingerprint"] == fp
                    and row["embedding_input_hash"] == input_fingerprint(row)
                ):
                    reusable[(row["context_header"], row["text"], row["oversized_row"])] = row
            copied = 0
            async with c.cursor() as cur:
                values = []
                for row in chunks:
                    old = reusable.get((row["context_header"], row["text"], row["oversized_row"]))
                    if old and row["embedding"] is None:
                        values.append((old["embedding"], fp, input_fingerprint(row), row["id"]))
                await cur.executemany(
                    "UPDATE chunks SET embedding=%s::vector,embedding_fingerprint=%s,"
                    "embedding_input_hash=%s WHERE id=%s AND embedding IS NULL",
                    values,
                )
                copied = len(values)
            return {
                "total": len(chunks),
                "copied_this_run": copied,
                "reusable": sum(
                    (r["context_header"], r["text"], r["oversized_row"]) in reusable for r in chunks
                ),
                "new": sum(
                    (r["context_header"], r["text"], r["oversized_row"]) not in reusable
                    for r in chunks
                ),
            }
        finally:
            await c.execute(INGESTION_UNLOCK)


async def main_async(args):
    async with pool_for(Settings().database_url) as pool:
        if args.action == "reuse":
            result = await reuse_vectors(pool, args.corpus)
            Path("docs/CORPUS_V2_REUSE.json").write_text(json.dumps(result, indent=2))
        else:
            report, config, docs, chunks, records = await audit(pool, args.corpus)
            Path("docs/CORPUS_V2_AUDIT.json").write_text(
                json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
            )
            if args.action == "migrate":
                if V2_LABELS.exists():
                    raise ValueError("Refusing to overwrite student v2 labels")
                corpus_hash = digest(
                    [
                        config["configuration"],
                        [(d["accession"], d["source_hash"], d["status"]) for d in docs],
                        sorted(c["id"] for c in chunks),
                    ]
                )
                mapped = {
                    r["id"]: [g["new_ids"][0] for g in r["gold"]] for r in report["migration"]
                }
                migrated = [
                    r
                    | {
                        "corpus_id": args.corpus,
                        "corpus_hash": corpus_hash,
                        "gold_chunk_ids": mapped[r["id"]],
                    }
                    for r in records
                ]
                V2_LABELS.write_text(
                    "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in migrated),
                    encoding="utf-8",
                )
                MANIFEST.write_text(
                    json.dumps(
                        {
                            "v1": V1,
                            "v2": args.corpus,
                            "corpus_hash": corpus_hash,
                            "records": report["migration"],
                            "unmatched_or_ambiguous": report["migration_errors"],
                            "review_questions": report["review_questions"],
                        },
                        indent=2,
                        ensure_ascii=False,
                    ),
                    encoding="utf-8",
                )
            if args.action == "freeze":
                from evals.label_retrieval import freeze_ready_corpus

                if not MANIFEST.exists() or not V2_LABELS.exists():
                    raise ValueError("Exact migration must be written before freeze")
                ids, fingerprint = await freeze_ready_corpus(pool, args.corpus)
                if any(
                    r["corpus_hash"] != fingerprint
                    for r in [
                        json.loads(line)
                        for line in V2_LABELS.read_text(encoding="utf-8").splitlines()
                    ]
                ):
                    raise ValueError("Migrated corpus fingerprint mismatch")
                report["frozen"] = True
                report["corpus_hash"] = fingerprint
                report["frozen_chunks"] = len(ids)
                Path("docs/CORPUS_V2_AUDIT.json").write_text(
                    json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
                )
            result = {
                k: report[k]
                for k in [
                    "v2",
                    "v2_chunks",
                    "filings",
                    "unexpected_changes",
                    "unresolved_substantive",
                    "migration_errors",
                ]
            }
        print(json.dumps(result, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["audit", "reuse", "migrate", "freeze"])
    parser.add_argument("--corpus", required=True)
    args = parser.parse_args()
    with asyncio.Runner(loop_factory=asyncio.SelectorEventLoop) as runner:
        runner.run(main_async(args))


if __name__ == "__main__":
    main()

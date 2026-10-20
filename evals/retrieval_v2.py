"""Phase C: frozen v2 validation and retrieval evaluation; no ingestion or labeling."""

import argparse
import asyncio
import hashlib
import json
from collections import Counter
from pathlib import Path

from evals.corpus_v2 import LABELS as V1_LABELS
from evals.corpus_v2 import MANIFEST, immutable_state, read_corpus
from evals.label_retrieval import load_records
from evals.retrieval_audit import CROSS_YEAR
from evals.retrieval_eval import check_reranker_pool, first_gold_rank, metrics
from filinglens.config import ROOT, Settings
from filinglens.db import pool_for
from filinglens.ingest.embed import embedding_fingerprint, input_fingerprint
from filinglens.ingest.identity import digest
from filinglens.ingest.models import model_revision
from filinglens.retrieval.service import MODES, RETRIEVAL_VERSION, SearchService

V2 = "corpus_3f3c2a9affddcc6a29eca9e768c65bcbd3e2f131fb69595b24b9b92005738739"
LABELS = ROOT / "evals/handwritten_v2.jsonl"
OUTPUT = ROOT / "evals/results/retrieval_v2.json"
APPROVED_ADDITIONS = {
    "hq_af3e0e0473af430b83dd4dc7e4bb1eef": {
        "chk_021110f70060ece24f43bb90853f0a55e0800ba742a560117bc473b4c7147e54",
        "chk_c322c2651975aa09a7091a8b8608aa632282a76a3365b282535563343eb0d813",
    },
    "hq_e9bf3b51fc6948de9eaa071fdbdb0e46": {
        "chk_ac40d0b888b22106ef53175cb5c3996f79aa6298dc5fb4cae00b326cb3709543",
    },
}


def check_review(records: list[dict], original: list[dict], manifest: dict) -> dict:
    """Require exactly the student-approved additions and preserve every other field."""
    if len(records) != 30 or len({r["id"] for r in records}) != 30:
        raise ValueError("Require exactly 30 unique IDs")
    if len({r["question"] for r in records}) != 30:
        raise ValueError("Duplicate question texts")
    old = {r["id"]: r for r in original}
    mapped = {r["id"]: {g["new_ids"][0] for g in r["gold"]} for r in manifest["records"]}
    if set(old) != set(mapped) or {r["id"] for r in records} != set(old):
        raise ValueError("Question IDs changed since migration")
    changes = {}
    for record in records:
        key = record["id"]
        fields = {
            k: v
            for k, v in record.items()
            if k not in {"corpus_id", "corpus_hash", "gold_chunk_ids"}
        }
        expected = {
            k: v
            for k, v in old[key].items()
            if k not in {"corpus_id", "corpus_hash", "gold_chunk_ids"}
        }
        if fields != expected:
            raise ValueError(f"Question/filter/reference fields changed: {key}")
        gold = record["gold_chunk_ids"]
        if not gold or len(gold) != len(set(gold)):
            raise ValueError(f"Empty or duplicate gold: {key}")
        added, removed = set(gold) - mapped[key], mapped[key] - set(gold)
        if removed or added != APPROVED_ADDITIONS.get(key, set()):
            raise ValueError(f"Unexpected gold edit: {key}")
        changes[key] = {
            "group": "b" if added else "a",
            "added": sorted(added),
            "removed": [],
            "migrated_gold": sorted(mapped[key]),
            "reviewed_gold": sorted(gold),
        }
    if sum(len(r["gold_chunk_ids"]) for r in records) != 64:
        raise ValueError("Expected 64 total gold judgments")
    return changes


def cache_path(record: dict, mode: str) -> Path:
    options = dict(ticker=None, fiscal_year=None, fiscal_period=None, items=None, mode=mode, k=30)
    options.update(record["filters"])
    key = digest(
        [
            RETRIEVAL_VERSION,
            V2,
            record["question"],
            options,
            embedding_fingerprint(),
            model_revision("rerank"),
        ]
    )
    return ROOT / "data/retrieval_cache" / f"{key}.json"


async def validate(pool) -> tuple[list[dict], dict, dict, list[dict], list[dict]]:
    records = load_records(LABELS)
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    changes = check_review(records, load_records(V1_LABELS), manifest)
    await immutable_state(pool)
    corpus, docs, sections, chunks = await read_corpus(pool, V2)
    if not corpus or not corpus["frozen"] or len(docs) != 275 or len(chunks) != 32960:
        raise ValueError("Expected frozen v2 with 275 filings and 32,960 chunks")
    if any(d["status"] != "complete" or d["details"].get("unresolved_substantive") for d in docs):
        raise ValueError("Incomplete corpus or unresolved substantive reference")
    fingerprint = digest(
        [
            corpus["configuration"],
            [(d["accession"], d["source_hash"], d["status"]) for d in docs],
            sorted(c["id"] for c in chunks),
        ]
    )
    if manifest["v2"] != V2 or manifest["corpus_hash"] != fingerprint:
        raise ValueError("Corpus fingerprint differs from migration manifest")
    by_id = {c["id"]: c for c in chunks}
    ticker_only = []
    for record in records:
        key, filters = record["id"], record["filters"]
        if record["corpus_id"] != V2 or record["corpus_hash"] != fingerprint:
            raise ValueError(f"Corpus identity/fingerprint mismatch: {key}")
        if not record["reference_answer"].strip() or not record["question"].strip():
            raise ValueError(f"Incomplete record: {key}")
        if "items" in filters:
            raise ValueError(f"Unexpected item filter: {key}")
        if set(filters) == {"ticker"}:
            if CROSS_YEAR.get(key) != filters["ticker"]:
                raise ValueError(f"Unexpected cross-year question: {key}")
            ticker_only.append(key)
        elif set(filters) != {"ticker", "fiscal_year", "fiscal_period"}:
            raise ValueError(f"Unexpected filter shape: {key}")
        for chunk_id in record["gold_chunk_ids"]:
            chunk = by_id.get(chunk_id)
            if not chunk or any(chunk[k] != v for k, v in filters.items()):
                raise ValueError(
                    f"Gold absent from v2 or inconsistent with filters: {key}: {chunk_id}"
                )
            if chunk_id in APPROVED_ADDITIONS.get(key, set()):
                expected = ("JPM", "7") if filters["ticker"] == "JPM" else ("CVX", "8")
                if (chunk["ticker"], chunk["item"]) != expected or (
                    chunk["fiscal_year"],
                    chunk["fiscal_period"],
                ) != (2024, "FY"):
                    raise ValueError(f"Added gold is outside approved repair: {chunk_id}")
    if set(ticker_only) != set(CROSS_YEAR):
        raise ValueError("Cross-year set changed")
    if any(
        c["embedding"] is None
        or c["embedding_fingerprint"] != embedding_fingerprint()
        or c["embedding_input_hash"] != input_fingerprint(c)
        for c in chunks
    ):
        raise ValueError("Incomplete or incompatible stored vectors")
    validation = {
        "records": 30,
        "unique_ids": 30,
        "unique_questions": 30,
        "gold_total": 64,
        "corpus_id": V2,
        "corpus_hash": fingerprint,
        "frozen": True,
        "chunks": len(chunks),
        "filings": len(docs),
        "filters_unchanged": True,
        "label_sha256": hashlib.sha256(LABELS.read_bytes()).hexdigest(),
        "corpus_content_hash": digest(
            [corpus, docs, sorted(sections, key=lambda s: s["id"]), chunks]
        ),
        "groups": dict(Counter(c["group"] for c in changes.values())),
        "ticker_only": ticker_only,
        "item_filters": [],
        "gold_sizes": dict(sorted(Counter(len(r["gold_chunk_ids"]) for r in records).items())),
        "broad": [
            {"id": r["id"], "question": r["question"], "gold": len(r["gold_chunk_ids"])}
            for r in records
            if len(r["gold_chunk_ids"]) > 3
        ],
    }
    return records, validation, changes, chunks, docs


async def run(validate_only: bool = False) -> None:
    async with pool_for(Settings().database_url) as pool:
        records, validation, changes, chunks, docs = await validate(pool)
        print("PRE-RUN VALIDATION", json.dumps(validation, indent=2), flush=True)
        (ROOT / "docs/CORPUS_V2_PHASE_C_VALIDATION.json").write_text(
            json.dumps(validation, indent=2), encoding="utf-8"
        )
        if validate_only:
            return
        # Preserve the pre-evaluation cache inventory; evaluation must not create
        # evidence that the student previously viewed a passage.
        pool_file = ROOT / "evals/results/retrieval_v2_pool_inventory.json"
        if pool_file.exists():
            inventory = json.loads(pool_file.read_text(encoding="utf-8"))
            if inventory["label_sha256"] != validation["label_sha256"]:
                raise ValueError("Pre-evaluation pool inventory belongs to different labels")
        else:
            inventory = {"label_sha256": validation["label_sha256"], "pools": {}}
            for record in records:
                inventory["pools"][record["id"]] = {
                    mode: [h["chunk_id"] for h in json.loads(path.read_text(encoding="utf-8"))]
                    for mode in MODES
                    if (path := cache_path(record, mode)).exists()
                }
            pool_file.write_text(json.dumps(inventory, indent=2), encoding="utf-8")
        service = SearchService(pool, V2)
        details = []
        for mode in MODES:
            for record in records:
                path = cache_path(record, mode)
                source = "cache" if path.exists() else "fresh"
                hits = await service.search(
                    record["question"], mode=mode, k=30, **record["filters"]
                )
                ranked = [h.chunk_id for h in hits]
                by_id = {c["id"]: c for c in chunks}
                if any(
                    key not in by_id
                    or any(by_id[key][k] != v for k, v in record["filters"].items())
                    for key in ranked
                ):
                    raise ValueError("Retrieved hit is outside the saved scope")
                details.append(
                    {
                        "question_id": record["id"],
                        "mode": mode,
                        "ranked_ids": ranked,
                        "first_gold_rank": first_gold_rank(ranked, set(record["gold_chunk_ids"])),
                        "source": source,
                        "cache_path": path.relative_to(ROOT).as_posix(),
                        **metrics(ranked, set(record["gold_chunk_ids"])),
                    }
                )
                print(f"{mode} {record['id']} {source}: {len(ranked)} hits", flush=True)
        check_reranker_pool(details)
        _, after, _, _, _ = await validate(pool)
        if after != validation:
            raise ValueError("Corpus or labels changed during evaluation")
        OUTPUT.write_text(
            json.dumps(
                {
                    "retrieval_version": RETRIEVAL_VERSION,
                    "validation": validation,
                    "unchanged_after": after,
                    "changes": changes,
                    "details": details,
                },
                indent=2,
            ),
            encoding="utf-8",
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    with asyncio.Runner(loop_factory=asyncio.SelectorEventLoop) as runner:
        runner.run(run(args.validate_only))


if __name__ == "__main__":
    main()

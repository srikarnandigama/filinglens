"""Retrieval-only metrics over human labels; run after the student's labeling handoff."""

import argparse
import asyncio
import json
import sys
from pathlib import Path

from evals.label_retrieval import freeze_ready_corpus, load_records
from filinglens.config import ROOT, Settings
from filinglens.db import pool_for
from filinglens.retrieval.service import MODES, SearchService


def metrics(ranked: list[str], gold: set[str]) -> dict[str, float]:
    if not gold:
        raise ValueError("Every question requires at least one human-labeled gold chunk")
    if len(ranked) != len(set(ranked)):
        raise ValueError("Duplicate retrieval hits invalidate ranks")
    first = next((rank for rank, key in enumerate(ranked[:30], 1) if key in gold), None)
    return {
        "recall@5": len(set(ranked[:5]) & gold) / len(gold),
        "recall@10": len(set(ranked[:10]) & gold) / len(gold),
        "MRR@30": 1 / first if first else 0.0,
    }


async def evaluate(labels: Path, output: Path) -> None:
    records = load_records(labels)
    if len(records) < 30:
        raise ValueError("M2 evaluation requires at least 30 human-written labeled questions")
    corpus_ids = {r["corpus_id"] for r in records}
    if len(corpus_ids) != 1:
        raise ValueError("All records must refer to the same frozen corpus")
    corpus_id = corpus_ids.pop()
    settings = Settings()
    async with pool_for(settings.database_url) as pool:
        valid_ids, corpus_hash = await freeze_ready_corpus(pool, corpus_id)
        for record in records:
            if not record["question"].strip() or not record["gold_chunk_ids"]:
                raise ValueError(f"Incomplete record: {record['id']}")
            if not set(record["gold_chunk_ids"]) <= valid_ids:
                raise ValueError(f"Unknown gold chunk in {record['id']}")
            if record.get("corpus_hash") != corpus_hash:
                raise ValueError(f"Corpus fingerprint mismatch in {record['id']}")
        service = SearchService(pool, corpus_id)
        lines = [
            "# Retrieval evaluation",
            "",
            f"Corpus: `{corpus_id}`",
            "",
            f"Questions: {len(records)}; manually judged pooled relevance labels.",
            "",
            "Recall is macro-averaged across questions; MRR is truncated at 30.",
            "",
            "| Mode | Recall@5 | Recall@10 | MRR@30 |",
            "|---|---:|---:|---:|",
        ]
        details = []
        for mode in MODES:
            scores = []
            for record in records:
                hits = await service.search(
                    record["question"], mode=mode, k=30, **record.get("filters", {})
                )
                values = metrics([h.chunk_id for h in hits], set(record["gold_chunk_ids"]))
                scores.append(values)
                details.append(
                    {
                        "question_id": record["id"],
                        "mode": mode,
                        "ranked_ids": [h.chunk_id for h in hits],
                        **values,
                    }
                )
            averages = {key: sum(s[key] for s in scores) / len(scores) for key in scores[0]}
            lines.append(
                f"| {mode} | {averages['recall@5']:.4f} | "
                f"{averages['recall@10']:.4f} | {averages['MRR@30']:.4f} |"
            )
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text("\n".join(lines) + "\n", encoding="utf-8")
        output.with_suffix(".json").write_text(json.dumps(details, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--labels", type=Path, default=ROOT / "evals/handwritten.jsonl")
    parser.add_argument("--output", type=Path, default=ROOT / "evals/results/retrieval.md")
    args = parser.parse_args()
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(evaluate(args.labels, args.output))


if __name__ == "__main__":
    main()

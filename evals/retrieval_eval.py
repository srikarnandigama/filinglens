"""Retrieval-only metrics over human labels; run after the student's labeling handoff."""

import argparse
import asyncio
import json
import sys
from collections import Counter
from pathlib import Path

from evals.retrieval_audit import CORPUS_ID, CROSS_YEAR, coverage, validate
from filinglens.config import ROOT, Settings
from filinglens.db import pool_for
from filinglens.ingest.embed import embedding_fingerprint
from filinglens.ingest.identity import digest
from filinglens.ingest.models import model_revision
from filinglens.retrieval.service import MODES, RETRIEVAL_VERSION, SearchService


def first_gold_rank(ranked: list[str], gold: set[str]) -> int | None:
    return next((rank for rank, key in enumerate(ranked[:30], 1) if key in gold), None)


def metrics(ranked: list[str], gold: set[str]) -> dict[str, float]:
    if not gold:
        raise ValueError("Every question requires at least one human-labeled gold chunk")
    if len(ranked) != len(set(ranked)):
        raise ValueError("Duplicate retrieval hits invalidate ranks")
    result = {}
    for k in (5, 10):
        found = len(set(ranked[:k]) & gold)
        result[f"capped_recall@{k}"] = found / min(k, len(gold))
        result[f"recall@{k}"] = found / len(gold)
        result[f"hit@{k}"] = float(found > 0)
    first = first_gold_rank(ranked, gold)
    result["MRR@30"] = 1 / first if first else 0.0
    return result


METRIC_KEYS = (
    "capped_recall@5",
    "capped_recall@10",
    "recall@5",
    "recall@10",
    "hit@5",
    "hit@10",
    "MRR@30",
)


def cache_path(record: dict, mode: str) -> Path:
    options = dict(ticker=None, fiscal_year=None, fiscal_period=None, items=None, mode=mode, k=30)
    options.update(record["filters"])
    key = digest(
        [
            RETRIEVAL_VERSION,
            CORPUS_ID,
            record["question"],
            options,
            embedding_fingerprint(),
            model_revision("rerank"),
        ]
    )
    return ROOT / "data/retrieval_cache" / f"{key}.json"


def metric_table(details: list[dict]) -> list[str]:
    lines = [
        "| Mode | Capped recall@5 | Capped recall@10 | Recall@5 | Recall@10 "
        "| Hit@5 | Hit@10 | MRR@30 |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for mode in MODES:
        values = [d for d in details if d["mode"] == mode]
        means = [sum(d[k] for d in values) / len(values) for k in METRIC_KEYS]
        lines.append(f"| {mode} | " + " | ".join(f"{v:.4f}" for v in means) + " |")
    return lines


def cell(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def check_reranker_pool(details: list[dict]) -> None:
    by_key = {(d["question_id"], d["mode"]): d for d in details}
    for (question_id, mode), value in by_key.items():
        if mode == "hybrid_rerank":
            hybrid = by_key[question_id, "hybrid"]["ranked_ids"]
            if set(hybrid) != set(value["ranked_ids"]):
                raise ValueError(
                    f"Reranker did not preserve full hybrid candidate pool: {question_id}"
                )


def report(records: list[dict], validation: dict, details: list[dict], audit: list[dict]) -> str:
    by_key = {(d["question_id"], d["mode"]): d for d in details}

    def mean(mode: str, metric: str, cross: bool | None = None) -> float:
        values = [
            d[metric]
            for d in details
            if d["mode"] == mode and (cross is None or (d["question_id"] in CROSS_YEAR) == cross)
        ]
        return sum(values) / len(values)

    lines = [
        "# M2 retrieval evaluation",
        "",
        f"Corpus: `{CORPUS_ID}`; snapshot `2026-10-19-v1`.",
        "23,441 chunks, 275 filings; corpus and labels unchanged throughout this run.",
        "",
        "## Pre-run validation",
        "",
        "Validation was reported to the student before metrics were computed: exactly 30 records, "
        "unique IDs and question texts; every corpus ID/fingerprint and gold ID/filter matches. "
        "No `items` filters. JNJ was re-saved by the student with FY2024/FY filters; verified. "
        "There are exactly six approved ticker-only searches and 24 company/year/period searches.",
        "",
        f"Corpus fingerprint: `{validation['corpus_hash']}`.",
        f"Label SHA-256: `{validation['label_sha256']}`.",
        "Chunk metadata/text/vector digest before and after: "
        f"`{validation['corpus_content_hash']}`.",
        "",
        "Gold sizes: 12 questions with 1, 12 with 2, 4 with 3, 1 with 6, and 1 with 7.",
        "",
        "Questions with more than three gold chunks:",
        "",
    ]
    for r in validation["broad"]:
        lines.append(f"- `{r['id']}`: {r['question']} ({r['gold_count']} gold).")
    lines += [
        "",
        "### Intentional cross-year subset (n=6)",
        "",
        "These searches span all available periods; only the filing named in the question "
        "is gold. This is a harder search scope than period-filtered retrieval, although "
        "these small, different question groups are not a controlled difficulty comparison.",
        "",
    ]
    for r in records:
        if r["id"] in CROSS_YEAR:
            lines.append(f"- `{r['id']}` ({r['filters']['ticker']}): {r['question']}")
    lines += [
        "",
        "The NVIDIA export-control question is both broad (7 gold chunks) and cross-year.",
        "",
        "## Metric definitions fixed before results",
        "",
        "G is the question's saved gold-ID set; T_k is the first k unique retrieved IDs. "
        "All metrics are macro-averaged over questions, without weighting by gold-set size.",
        "",
        "- **Primary capped recall@k** = |G ∩ T_k| / min(k, |G|), for k=5 and 10. "
        "Chosen before seeing results (D027), so 6- and 7-gold questions can reach 1 at k=5.",
        "- **Standard recall@k** = |G ∩ T_k| / |G|, for k=5 and 10.",
        "- **Hit@k** = 1 if G ∩ T_k is nonempty, otherwise 0, for k=5 and 10.",
        "- **MRR@30** = mean of 1/r, where r is the first gold rank within the top 30; "
        "0 if there is no gold in those 30.",
        "",
        "Every search uses saved filters exactly and k=30. The existing service reranks the "
        "entire hybrid top 30 before returning 30; rankings are not truncated to 5/10 beforehand. "
        "Keyword search can return fewer than 30 actual matches.",
        "The reranked ID set equals the complete hybrid candidate ID set for every question; "
        "all available candidates were retained for the MRR@30 calculation.",
        "The Apple FY2025 Q3 tariff question has only 15 eligible frozen chunks, verified "
        "by a read-only count; vector/hybrid/rerank return all 15. Every other hybrid "
        "and reranked pool contains 30 candidates. This reflects eligible-corpus size; "
        "there is no HNSW underfill.",
        "Its 15-chunk eligible set makes the Apple tariff question easier than questions "
        "with larger eligible sets; it is not directly comparable in search difficulty.",
        "",
    ]
    pre = json.loads((ROOT / "evals/results/retrieval_pre_fix.json").read_text(encoding="utf-8"))
    lines += ["## Pre-fix (keyword AND-semantics defect)", ""]
    for title, cross in [
        ("Full set (n=30)", None),
        ("Cross-year (n=6)", True),
        ("Period-filtered (n=24)", False),
    ]:
        subset = [
            d for d in pre["details"] if cross is None or (d["question_id"] in CROSS_YEAR) == cross
        ]
        lines += [f"### {title}", "", *metric_table(subset), ""]
    lines += [
        "## Post-fix full set (n=30)",
        "",
        *metric_table(details),
        "",
    ]
    for title, cross in [
        ("Cross-year subset (n=6)", True),
        ("Period-filtered subset (n=24)", False),
    ]:
        subset = [d for d in details if (d["question_id"] in CROSS_YEAR) == cross]
        lines += [f"## Post-fix {title}", "", *metric_table(subset), ""]
    sources = Counter(d["source"] for d in details)
    keyword_lengths = Counter(len(d["ranked_ids"]) for d in details if d["mode"] == "keyword")
    identical = sum(
        by_key[r["id"], "vector"]["ranked_ids"] == by_key[r["id"], "hybrid"]["ranked_ids"]
        for r in records
    )
    lines += [
        "## Retrieval cache",
        "",
        f"D026: {sources['cache']} searches reused valid frozen-corpus caches; "
        f"{sources['fresh']} were fresh runs (120 question/mode combinations total). "
        "Keys include exact question, saved filters, depth 30, mode, corpus and model versions. "
        "Per-run source and exact cache path are saved in retrieval.json.",
        "",
        "### Keyword and fusion limitation",
        "",
        "Keyword result-count distribution (hits: questions): "
        f"{dict(sorted(keyword_lengths.items()))}. "
        f"Vector and hybrid ID rankings were identical for {identical}/30 questions. "
        "The single correctness fix chosen before this rerun derives distinct English stemmed, "
        "stopword-filtered lexemes with to_tsvector, ORs the quoted lexemes, and ranks by "
        "unchanged ts_rank_cd. RRF remains 60. No alternatives or weights were tried. "
        f"Cache implementation version is `{RETRIEVAL_VERSION}`; v1 keyword and fusion "
        "rankings cannot populate this run. The pre-fix tables remain above for comparison.",
        "",
        "## Post-fix per-question first-gold ranks",
        "",
        "`>30` means no gold in the returned top 30, including empty keyword results.",
        "",
        "| ID | Short question | Ticker | Gold | vector | keyword | hybrid | hybrid_rerank |",
        "|---|---|---|---:|---:|---:|---:|---:|",
    ]
    for r in records:
        ranks = [by_key[r["id"], m]["first_gold_rank"] or ">30" for m in MODES]
        lines.append(
            "| "
            + " | ".join(
                map(
                    cell,
                    [
                        r["id"],
                        r["question"][:95],
                        r["filters"]["ticker"],
                        len(r["gold_chunk_ids"]),
                        *ranks,
                    ],
                )
            )
            + " |"
        )
    changes = Counter()
    demotions = []
    for r in records:
        a = by_key[r["id"], "hybrid"]["first_gold_rank"] or 31
        b = by_key[r["id"], "hybrid_rerank"]["first_gold_rank"] or 31
        changes["better" if b < a else "worse" if b > a else "same"] += 1
        thresholds = [str(k) for k in (5, 10) if a <= k < b]
        if thresholds:
            demotions.append((r, a, b, ", ".join(thresholds)))
    lines += [
        "",
        "## Post-fix reranker check",
        "",
        f"First-gold rank versus hybrid: **{changes['better']} better / "
        f"{changes['worse']} worse / {changes['same']} same**.",
        "",
        "Every first-gold demotion out of the top 5 or top 10:",
        "",
        "| ID | Ticker | Hybrid rank | Reranked rank | Pushed outside top-k |",
        "|---|---|---:|---:|---|",
    ]
    for r, a, b, thresholds in demotions:
        lines.append(f"| {r['id']} | {r['filters']['ticker']} | {a} | {b} | {thresholds} |")
    for mode in ("hybrid", "hybrid_rerank"):
        values = [d for d in details if d["mode"] == mode]
        recall = sum(d["recall@10"] for d in values) / len(values)
        hit = sum(d["hit@10"] for d in values)
        lines += [
            "",
            f"{mode}: standard and capped recall@10 = {recall:.4f}; hit@10 = {int(hit)}/30.",
        ]
    effect = (
        "hurts"
        if mean("hybrid_rerank", "recall@10") < mean("hybrid", "recall@10")
        else "does not hurt"
    )
    lines += [
        "",
        "The two recall@10 definitions coincide here because every gold set has at most 7 chunks.",
        f"Reranking {effect} "
        f"overall recall@10: {mean('hybrid', 'recall@10'):.4f} → "
        f"{mean('hybrid_rerank', 'recall@10'):.4f}. "
        f"Period-filtered recall@10: {mean('hybrid', 'recall@10', False):.4f} → "
        f"{mean('hybrid_rerank', 'recall@10', False):.4f}; "
        f"cross-year recall@10: {mean('hybrid', 'recall@10', True):.4f} → "
        f"{mean('hybrid_rerank', 'recall@10', True):.4f}. "
        f"Overall capped recall@5: {mean('hybrid', 'capped_recall@5'):.4f} → "
        f"{mean('hybrid_rerank', 'capped_recall@5'):.4f}; "
        f"MRR@30: {mean('hybrid', 'MRR@30'):.4f} → {mean('hybrid_rerank', 'MRR@30'):.4f}.",
        "",
        "### Labeling observations checked against finalized gold",
        "",
    ]
    for r in records:
        if r["id"] in {
            "hq_4d5d9efc06f34ddaa145f699ce2c2e4d",
            "hq_69c1bbc69ab243d29a5b85972d80828e",
            "hq_cdeefd822cd94dd98c915d26380f37ed",
        }:
            ranks = ", ".join(
                f"{m}={by_key[r['id'], m]['first_gold_rank'] or '>30'}" for m in MODES
            )
            lines.append(f"- `{r['id']}`: {r['question']} First-gold ranks: {ranks}.")
            lines += [
                "",
                "| Gold chunk ID | vector | hybrid | hybrid_rerank |",
                "|---|---:|---:|---:|",
            ]
            for gold in r["gold_chunk_ids"]:
                gold_ranks = []
                for mode in ("vector", "hybrid", "hybrid_rerank"):
                    ids = by_key[r["id"], mode]["ranked_ids"]
                    gold_ranks.append(str(ids.index(gold) + 1) if gold in ids else ">30")
                lines.append(f"| {gold} | " + " | ".join(gold_ranks) + " |")
            lines.append("")
    lines += [
        "These tables use post-fix candidate pools; earlier labeling positions need not match. "
        "First-gold rank alone can hide losses of additional relevant passages, "
        "which the recall metrics capture. No new relevance labels were assigned."
    ]
    lines += [
        "",
        "### Paired comparisons",
        "",
        "Wins compare per-question primary capped recall@10, as specified before results. "
        "A win means strictly more gold recovered within 10; ties include equal zero scores. "
        "n=30 is small; differences of a few questions are not conclusive.",
        "",
        "| Mode A | Mode B | A wins | B wins | Ties |",
        "|---|---|---:|---:|---:|",
    ]
    for i, a in enumerate(MODES):
        for b in MODES[i + 1 :]:
            wins = Counter()
            for r in records:
                av, bv = (by_key[r["id"], m]["capped_recall@10"] for m in (a, b))
                wins["A" if av > bv else "B" if bv > av else "tie"] += 1
            lines.append(f"| {a} | {b} | {wins['A']} | {wins['B']} | {wins['tie']} |")
    lines += [
        "",
        "## Known coverage gaps",
        "",
        "Read-only inventory: all 20 companies, all 275 frozen filings, 730 expected item slots. "
        "The tables below list every item with fewer than 3 chunks, including missing items. "
        "First line is the first nonblank stored line, including a heading when present. "
        "Counts alone do not establish a parsing error. The full inventory and short-section "
        "texts are saved in retrieval.json for inspection.",
        "",
    ]
    for form, title in [
        ("10-K", "Annual items 1, 1A, 7, 7A and 8"),
        ("10-Q", "Quarterly items P1-2 and P2-1A"),
    ]:
        lines += [
            f"### {title}",
            "",
            "| Ticker | FY | Accession | Item | Chunks | First line | Assessment |",
            "|---|---:|---|---|---:|---|---|",
        ]
        for row in audit:
            if row["form"] == form and row["chunks"] < 3:
                vals = [
                    row[k]
                    for k in ("ticker", "fiscal_year", "accession", "item", "chunks", "first_line")
                ]
                lines.append("| " + " | ".join(map(cell, [*vals, assessment(row)])) + " |")
    ko = [
        r["chunks"]
        for r in audit
        if r["ticker"] == "KO" and r["fiscal_year"] == 2024 and r["item"] == "7A"
    ]
    lines += [
        "",
        f"KO FY2024 Item 7A: {ko[0]} chunks; not a short-section finding.",
        "",
        (ROOT / "evals/retrieval_notes.md").read_text(encoding="utf-8"),
    ]
    return "\n".join(lines) + "\n"


def assessment(row: dict) -> str:
    ticker, item = row["ticker"], row["item"]
    if row["chunks"] == 0:
        return "Absent in cached source: annual risk reference only; see source audit"
    if row["form"] == "10-Q":
        if item == "P1-2":
            return "TOC capture; substantive MD&A missing"
        if row["chunks"] == 2:
            return "Brief risk update/cross-reference; substantive text present"
        return "Brief risk disclosure/reference; shortness alone is not a gap"
    if ticker in {"CVX", "JPM", "XOM"} and item in {"7", "7A", "8"}:
        return "Cross-reference stub; referenced financial section not retained"
    if (ticker, item) in {("DIS", "8"), ("NVDA", "8")}:
        return "Cross-reference stub; referenced content outside this item"
    if (ticker, item) in {("BAC", "7A"), ("JNJ", "7A"), ("PFE", "7A"), ("PG", "7A")}:
        return "Cross-reference to retained MD&A; not a stand-alone disclosure"
    return "Substantive short market-risk disclosure"


async def evaluate(labels: Path, output: Path, validate_only: bool = False) -> None:
    settings = Settings()
    async with pool_for(settings.database_url) as pool:
        records, validation = await validate(pool, labels)
        print("PRE-RUN VALIDATION", json.dumps(validation), flush=True)
        if validate_only:
            return
        audit = await coverage(pool)
        service = SearchService(pool, CORPUS_ID)
        details = []
        for mode in MODES:
            for record in records:
                path = cache_path(record, mode)
                source = "cache" if path.exists() else "fresh"
                hits = await service.search(
                    record["question"], mode=mode, k=30, **record.get("filters", {})
                )
                values = metrics([h.chunk_id for h in hits], set(record["gold_chunk_ids"]))
                details.append(
                    {
                        "question_id": record["id"],
                        "mode": mode,
                        "ranked_ids": [h.chunk_id for h in hits],
                        "first_gold_rank": first_gold_rank(
                            [h.chunk_id for h in hits], set(record["gold_chunk_ids"])
                        ),
                        "source": source,
                        "cache_path": path.relative_to(ROOT).as_posix(),
                        "filters": record["filters"],
                        **values,
                    }
                )
                print(f"{mode} {record['id']} {source}: {len(hits)} hits", flush=True)
        check_reranker_pool(details)
        _, after = await validate(pool, labels)
        if validation != after:
            raise ValueError("Labels or frozen corpus changed during evaluation; stop")
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(report(records, validation, details, audit), encoding="utf-8")
        output.with_suffix(".json").write_text(
            json.dumps(
                {
                    "retrieval_version": RETRIEVAL_VERSION,
                    "validation": validation,
                    "unchanged_after": after,
                    "details": details,
                    "coverage": audit,
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        print("\n".join(metric_table(details)), flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--labels", type=Path, default=ROOT / "evals/handwritten.jsonl")
    parser.add_argument("--output", type=Path, default=ROOT / "evals/results/retrieval.md")
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(evaluate(args.labels, args.output, args.validate_only))


if __name__ == "__main__":
    main()

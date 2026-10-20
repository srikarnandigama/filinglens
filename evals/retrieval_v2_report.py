"""Phase C comparisons and transparent labeling-pool reconstruction; no labels written."""

import asyncio
import json
from collections import Counter, defaultdict

from evals.corpus_v2 import V1, read_corpus
from evals.label_retrieval import load_records
from evals.retrieval_audit import CROSS_YEAR
from evals.retrieval_eval import METRIC_KEYS, cell, first_gold_rank, metric_table, metrics
from evals.retrieval_followup import containment, shingles, unjudged
from evals.retrieval_v2 import LABELS, OUTPUT, V2
from filinglens.config import ROOT, Settings
from filinglens.db import pool_for
from filinglens.retrieval.service import MODES


def bridge_scores(details: list[dict], changes: dict) -> list[dict]:
    """Hold v2 rankings fixed while using the original, exactly migrated labels."""
    return [
        d
        | metrics(d["ranked_ids"], set(changes[d["question_id"]]["migrated_gold"]))
        | {
            "first_gold_rank": first_gold_rank(
                d["ranked_ids"], set(changes[d["question_id"]]["migrated_gold"])
            )
        }
        for d in details
    ]


def averages(details: list[dict], mode: str) -> dict:
    rows = [d for d in details if d["mode"] == mode]
    return {key: sum(d[key] for d in rows) / len(rows) for key in METRIC_KEYS}


def reconstruct_exposure(
    records: list[dict],
    old_chunks: list[dict],
    new_chunks: list[dict],
    old_pools: dict,
    inventory: dict,
    reviewed: set[str],
) -> tuple[dict, dict]:
    """Map historical exposure conservatively; never use newly computed eval pools."""
    old = {c["id"]: c for c in old_chunks}
    lookup = defaultdict(list)
    for chunk in new_chunks:
        lookup[chunk["accession"], chunk["item"], chunk["text"]].append(chunk["id"])
    pools, evidence = {}, {}
    for record in records:
        key = record["id"]
        mapped = set()
        unmatched, ambiguous = [], []
        for chunk_id in old_pools[key]:
            c = old[chunk_id]
            matches = lookup[c["accession"], c["item"], c["text"]]
            if len(matches) == 1:
                mapped.add(matches[0])
            elif not matches:
                unmatched.append(chunk_id)
            else:
                ambiguous.append(chunk_id)
        modes = inventory["pools"][key]
        if key in reviewed and set(modes) != set(MODES):
            raise ValueError("Reviewed question lacks a complete pre-evaluation v2 pool")
        review_pool = (
            set().union(*(set(ids) for ids in modes.values())) if key in reviewed else set()
        )
        pools[key] = mapped | review_pool | set(record["gold_chunk_ids"])
        evidence[key] = {
            "mapped_v1_pool": sorted(mapped),
            "pre_eval_review_pool": sorted(review_pool),
            "known_gold": record["gold_chunk_ids"],
            "pool": sorted(pools[key]),
            "unmatched_old_candidates": unmatched,
            "ambiguous_old_candidates": ambiguous,
        }
    return pools, evidence


async def build() -> None:
    result = json.loads(OUTPUT.read_text(encoding="utf-8"))
    old_result = json.loads((ROOT / "evals/results/retrieval.json").read_text(encoding="utf-8"))
    old_analysis = json.loads(
        (ROOT / "evals/results/retrieval_analyses.json").read_text(encoding="utf-8")
    )
    inventory = json.loads(
        (ROOT / "evals/results/retrieval_v2_pool_inventory.json").read_text(encoding="utf-8")
    )
    migration = json.loads((ROOT / "evals/corpus_v2_migration.json").read_text(encoding="utf-8"))
    records = load_records(LABELS)
    reviewed = {r["id"] for r in migration["review_questions"]}
    async with pool_for(Settings().database_url) as pool:
        _, _, _, old_chunks = await read_corpus(pool, V1)
        _, _, _, chunks = await read_corpus(pool, V2)
    exposures, exposure_evidence = reconstruct_exposure(
        records, old_chunks, chunks, old_analysis["pool_reconstruction"], inventory, reviewed
    )
    details, changes = result["details"], result["changes"]
    old_details = old_result["details"]
    bridge = bridge_scores(details, changes)
    by_key = {(d["question_id"], d["mode"]): d for d in details}
    old_by_key = {(d["question_id"], d["mode"]): d for d in old_details}
    by_id = {c["id"]: c for c in chunks}
    pool_definition = {
        r["id"]: set().union(*(set(by_key[r["id"], m]["ranked_ids"]) for m in MODES))
        for r in records
    }
    unknown = []
    for r in records:
        for mode in MODES:
            for k in (5, 10):
                ids = by_key[r["id"], mode]["ranked_ids"]
                unknown.append(
                    {
                        "question_id": r["id"],
                        "mode": mode,
                        "exposure_proxy": unjudged(
                            ids, exposures[r["id"]], set(r["gold_chunk_ids"]), k
                        ),
                        "reconstructed_v2_definition": unjudged(
                            ids, pool_definition[r["id"]], set(r["gold_chunk_ids"]), k
                        ),
                    }
                )
    near = []
    for r in records:
        if r["id"] not in CROSS_YEAR:
            continue
        for mode in ("vector", "hybrid_rerank"):
            for rank, chunk_id in enumerate(by_key[r["id"], mode]["ranked_ids"][:10], 1):
                c = by_id[chunk_id]
                matches = [
                    (containment(shingles(c["text"]), shingles(by_id[g]["text"])), g)
                    for g in r["gold_chunk_ids"]
                    if by_id[g]["accession"] != c["accession"]
                ]
                overlap, closest = max(matches, default=(0.0, None))
                near.append(
                    {
                        k: c[k]
                        for k in [
                            "id",
                            "ticker",
                            "form",
                            "fiscal_year",
                            "fiscal_period",
                            "item",
                            "accession",
                        ]
                    }
                    | {
                        "question_id": r["id"],
                        "mode": mode,
                        "rank": rank,
                        "overlap": overlap,
                        "closest_gold": closest,
                        "near_duplicate": overlap >= 0.70,
                        "gold": chunk_id in r["gold_chunk_ids"],
                    }
                )
    eligible = {
        r["id"]: sum(all(c[k] == v for k, v in r["filters"].items()) for c in chunks)
        for r in records
    }
    analysis = {
        "bridge_details": bridge,
        "pool_exposure_evidence": exposure_evidence,
        "unjudged": unknown,
        "near_duplicates": near,
        "eligible_counts": eligible,
    }
    (ROOT / "evals/results/retrieval_v2_analyses.json").write_text(
        json.dumps(analysis, indent=2), encoding="utf-8"
    )
    v = result["validation"]
    lines = [
        "# M2 corpus-v2 retrieval evaluation — Phase C",
        "",
        "Phase C evaluation is complete and awaits the student's acceptance. M3 has not started. "
        "V2 is the active corpus selected for M3 onward; v1 and all "
        "historical results remain available.",
        "",
        f"Corpus: `{V2}`; fingerprint `{v['corpus_hash']}`; snapshot `2026-10-19-v1`. "
        "32,960 chunks, 275 filings. Evaluation made no corpus, embedding,"
        " schema, dependency or label changes.",
        "",
        "## Pre-run validation",
        "",
        "Validation passed before metrics: 30 records, 30 unique "
        "IDs/texts, 64 gold labels, matching "
        "v2 identity/fingerprint, every gold in v2 and consistent with its"
        " saved filters. Questions, "
        "filters and reference answers exactly match the original/migrated records. All 61 mapped "
        "golds were retained; only the student's three approved additions were present. "
        "No item filters; six ticker-only cross-year questions and 24 "
        "fully period-filtered questions. "
        f"Gold-size distribution: `{v['gold_sizes']}`. Label SHA-256: `{v['label_sha256']}`. "
        f"Corpus content SHA-256 (including stored vectors): `{v['corpus_content_hash']}`. "
        "The same validation and hashes passed after the run.",
        "",
        "The two broad questions remain NVIDIA export controls (7 gold, also cross-year) and "
        "Microsoft Copilot overview (6 gold); every other question has at most 3 gold chunks.",
        "",
        "Cross-year searches use ticker-only filters exactly as saved, but only their named filing "
        "is gold: " + ", ".join(f"{ticker} (`{key}`)" for key, ticker in CROSS_YEAR.items()) + ".",
        "",
        "## Fixed protocol and metric definitions",
        "",
        "Every mode returns depth 30 with saved filters unchanged. The "
        "reranker scores the complete "
        "hybrid top 30; candidate-ID sets are checked for equality. D031 OR-over-English-lexemes "
        "keyword search, ts_rank_cd, RRF 60, model revisions and the retrieval implementation "
        "`retrieval-v2-keyword-or` are unchanged. No variants, weights or "
        "thresholds were selected on these results.",
        "",
        "For gold set G and the first k distinct results T_k, all metrics "
        "are macro-averaged over questions:",
        "",
        "- **Primary capped recall@k:** `|G ∩ T_k| / min(k, |G|)` for k=5,10.",
        "- **Standard recall@k:** `|G ∩ T_k| / |G|` for k=5,10.",
        "- **Hit@k:** 1 if `G ∩ T_k` is nonempty, otherwise 0, for k=5,10.",
        "- **MRR@30:** reciprocal rank of the first gold in the first 30, or 0 if absent. "
        "An underfilled eligible set is not padded. Capped recall was chosen before the original "
        "results (D027), to avoid an unavoidable ceiling for the 6/7-gold questions at k=5.",
        "",
    ]
    subsets = [
        ("Full set (n=30)", set(r["id"] for r in records)),
        ("Cross-year (n=6)", set(CROSS_YEAR)),
        ("Period-filtered (n=24)", {r["id"] for r in records} - set(CROSS_YEAR)),
    ]
    for title, ids in subsets:
        lines += [
            f"## V2 {title}",
            "",
            *metric_table([d for d in details if d["question_id"] in ids]),
            "",
        ]
    lines += [
        "### Main findings",
        "",
        "Every mode's reviewed-v2 recall@10 is lower than the archived v1 value. "
        "The table below separates changed corpus/rankings from the gold-label effect; "
        "these are descriptive differences, not evidence that recovering source content "
        "improves this pooled benchmark. Group (a)'s aggregate vector recall@10 is unchanged, "
        "while its keyword, hybrid and reranked recall@10 decline.",
        "",
        "| Mode | V1 recall@10 | V2 migrated gold | V2 reviewed gold "
        "| Corpus/ranking change (pp) | Label-only change (pp) |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for mode in MODES:
        a, b, c = [averages(source, mode)["recall@10"] for source in (old_details, bridge, details)]
        lines.append(
            f"| {mode} | {a:.4f} | {b:.4f} | {c:.4f} "
            f"| {(b - a) * 100:+.2f} | {(c - b) * 100:+.2f} |"
        )
    sources = Counter(d["source"] for d in details)
    different_rankings = sum(
        by_key[r["id"], "vector"]["ranked_ids"] != by_key[r["id"], "hybrid"]["ranked_ids"]
        for r in records
    )
    lines += [
        "## Cache and candidate checks",
        "",
        f"D026: {sources['cache']} cached and {sources['fresh']} fresh question/mode searches "
        "(120 total). Rankings are independent of labels, so caches remain"
        " valid after gold additions. "
        "Exact paths/source are saved in retrieval_v2.json. The pre-evaluation cache inventory "
        "has four modes for each of the six reviewed questions and no caches for the other 24; "
        "it was saved before evaluation populated any new cache.",
        "",
        f"Hybrid differs from vector on {different_rankings}/30 rankings. "
        "All 30 reranked pools preserve the full hybrid candidate set. "
        f"The Apple FY2025 Q3 tariff question (`hq_d2c0efbeda48446e88c1160406bc4452`) has "
        f"{eligible['hq_d2c0efbeda48446e88c1160406bc4452']} eligible chunks, making it easier "
        "than the larger search scopes. Short output there is "
        "eligible-corpus size, not HNSW starvation.",
        "",
        "## V1 versus V2",
        "",
        "V1 numbers are the archived **post-keyword-fix** run in retrieval.json/retrieval.md. "
        "V1 used 61 gold labels; reviewed v2 uses 64. Overall differences therefore combine "
        "corpus/ranking changes and the two student label revisions; the "
        "attribution below separates them.",
        "",
    ]
    for title, ids in subsets:
        lines += [
            f"### V1 {title}",
            "",
            *metric_table([d for d in old_details if d["question_id"] in ids]),
            "",
        ]
        delta = []
        for mode in MODES:
            a = averages([d for d in old_details if d["question_id"] in ids], mode)
            b = averages([d for d in details if d["question_id"] in ids], mode)
            delta.append({"mode": mode, **{k: b[k] - a[k] for k in METRIC_KEYS}})
        lines += [f"### V2 minus V1: {title}", "", *metric_table(delta), ""]
    lines += [
        "## Label-change attribution",
        "",
        "Group (a): 28 questions with identical semantic gold after exact-ID migration. This "
        "compares changed candidate corpus/rankings with fixed labels. All IDs changed, so "
        "ID-based tie-breaking can also change ranks, even where eligible "
        "passage text is identical. "
        "This is not a controlled estimate of the parser alone. Group (b): the two student-changed "
        "questions, JPM cybersecurity (+2 FY2024 Item 7) and Chevron/Hess (+1 FY2024 Item 8). "
        "No gold was removed. For group (b), score the same v2 rankings twice: first with the 61 "
        "original migrated golds (bridge), then with the 64 reviewed golds. The second difference "
        "is only the label effect, including changed denominators.",
        "",
    ]
    for group, label in [("a", "Group (a), n=28"), ("b", "Group (b), n=2")]:
        ids = {key for key, change in changes.items() if change["group"] == group}
        for name, source in [
            ("V1 original gold", old_details),
            ("V2 migrated gold (bridge)", bridge),
            ("V2 reviewed gold", details),
        ]:
            lines += [
                f"### {label}: {name}",
                "",
                *metric_table([d for d in source if d["question_id"] in ids]),
                "",
            ]
    lines += [
        "### Group (b) added passages",
        "",
        "| Question | Added gold ID | Item | Vector rank | Keyword rank | "
        "Hybrid rank | Reranked rank |",
        "|---|---|---|---:|---:|---:|---:|",
    ]
    for r in records:
        for gold in changes[r["id"]]["added"]:
            ranks = [
                by_key[r["id"], m]["ranked_ids"].index(gold) + 1
                if gold in by_key[r["id"], m]["ranked_ids"]
                else ">30"
                for m in MODES
            ]
            lines.append(
                "| " + " | ".join(map(cell, [r["id"], gold, by_id[gold]["item"], *ranks])) + " |"
            )
    lines += [
        "",
        "## Per-question first-gold rank changes",
        "",
        "Each mode cell is **v1 original-gold rank → v2 reviewed-gold rank**; `>30` means no gold "
        "in the returned top 30. Group (b) also changes labels; its bridge results are preserved "
        "in retrieval_v2_analyses.json.",
        "",
        "| ID | Short question | Ticker | Group | Gold v1→v2 | Vector | "
        "Keyword | Hybrid | Hybrid rerank |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for r in records:
        key = r["id"]
        ranks = [
            f"{old_by_key[key, m]['first_gold_rank'] or '>30'} → "
            f"{by_key[key, m]['first_gold_rank'] or '>30'}"
            for m in MODES
        ]
        vals = [
            key,
            r["question"][:85],
            r["filters"]["ticker"],
            changes[key]["group"],
            f"{len(changes[key]['migrated_gold'])}→{len(r['gold_chunk_ids'])}",
            *ranks,
        ]
        lines.append("| " + " | ".join(map(cell, vals)) + " |")
    rank_changes = Counter()
    demotions = []
    for r in records:
        a, b = [by_key[r["id"], m]["first_gold_rank"] or 31 for m in ["hybrid", "hybrid_rerank"]]
        rank_changes["better" if b < a else "worse" if b > a else "same"] += 1
        if ks := [k for k in [5, 10] if a <= k < b]:
            demotions.append([r["id"], a, b if b != 31 else ">30", ", ".join(map(str, ks))])
    lines += [
        "",
        "## Reranker check",
        "",
        f"First-gold ranks: {rank_changes['better']} better / {rank_changes['worse']} worse / "
        f"{rank_changes['same']} same versus hybrid. Every demotion out of the top 5 or top 10:",
        "",
        "| Question | Hybrid | Reranked | Pushed outside k |",
        "|---|---:|---:|---|",
    ]
    for vals in demotions:
        lines.append("| " + " | ".join(map(cell, vals)) + " |")
    for title, ids in subsets:
        a, b = [
            averages([d for d in details if d["question_id"] in ids], m)
            for m in ["hybrid", "hybrid_rerank"]
        ]
        lines += [
            "",
            f"{title}: hybrid → reranked recall@10 {a['recall@10']:.4f} → {b['recall@10']:.4f}; "
            f"capped recall@5 {a['capped_recall@5']:.4f} → {b['capped_recall@5']:.4f}; "
            f"MRR@30 {a['MRR@30']:.4f} → {b['MRR@30']:.4f}.",
        ]
    overall_hybrid = averages(details, "hybrid")
    overall_rerank = averages(details, "hybrid_rerank")
    lines += [
        "",
        "Overall, reranking raises recall@10 from "
        f"{overall_hybrid['recall@10']:.4f} to {overall_rerank['recall@10']:.4f}, "
        "but lowers MRR@30 from "
        f"{overall_hybrid['MRR@30']:.4f} to {overall_rerank['MRR@30']:.4f}. "
        "It improves recovery within ten while worsening first-gold ordering on average; "
        "the counts and individual demotions above describe the observed behavior.",
    ]
    lines += [
        "",
        "### Paired comparisons",
        "",
        "Wins use each question's primary capped recall@10. n=30 is small; differences of a few "
        "questions are not conclusive.",
        "",
        "| Mode A | Mode B | A wins | B wins | Ties |",
        "|---|---|---:|---:|---:|",
    ]
    for i, a in enumerate(MODES):
        for b in MODES[i + 1 :]:
            counts = Counter(
                "A"
                if by_key[r["id"], a]["capped_recall@10"] > by_key[r["id"], b]["capped_recall@10"]
                else "B"
                if by_key[r["id"], a]["capped_recall@10"] < by_key[r["id"], b]["capped_recall@10"]
                else "tie"
                for r in records
            )
            lines.append(f"| {a} | {b} | {counts['A']} | {counts['B']} | {counts['tie']} |")
    lines += [
        "",
        "## Unjudged candidates and pooled-label limitations",
        "",
        "The CLI did not save pool-membership/view history. We cannot assert which non-gold "
        "passages the student read. Two reconstructions are reported without assigning new labels:",
        "",
        "1. **Labeling-exposure proxy (primary analysis):** uniquely exact-map the archived v1 "
        "labeling-pool IDs by accession/item/text into v2; add the "
        "pre-evaluation four-mode depth-30 "
        "v2 pools for the six reviewed questions and all 64 known golds "
        "(manual browsing evidence). "
        "Do not add evaluation-generated caches. Unmatched/ambiguous old non-gold candidates "
        "are excluded and listed in the JSON evidence. This remains a "
        "reconstruction, not a view log.",
        "2. **V2 pooling-definition reconstruction:** union all four current v2 depth-30 rankings "
        "per question with its saved filters. Every mode's top 5/10 is necessarily in that union, "
        "so its unjudged rate is zero by construction. That does not show that all these passages "
        "were reviewed or are relevant; the other 24 questions were migrated without v2 rejudging.",
        "",
        "For each mode/k, the fraction is unjudged returned slots / actual returned slots, pooled "
        "over questions. Known gold always counts as judged. Unjudged relevant chunks receive "
        "no credit under these labels, so keyword/hybrid and other modes may be under-credited. "
        "Golds are not exhaustive judgments, and the same systems supply the candidate pools.",
        "",
        "| Mode | Exposure proxy top-5 | Exposure proxy top-10 | V2 "
        "definition top-5 | V2 definition top-10 |",
        "|---|---:|---:|---:|---:|",
    ]
    for mode in MODES:
        vals = []
        for typ in ["exposure_proxy", "reconstructed_v2_definition"]:
            for k in [5, 10]:
                rows = [d[typ] for d in unknown if d["mode"] == mode and d[typ]["k"] == k]
                n, total = sum(d["unjudged"] for d in rows), sum(d["returned"] for d in rows)
                vals.append(f"{n}/{total} ({n / total:.2%})")
        lines.append(f"| {mode} | " + " | ".join(vals) + " |")
    lines += [
        "",
        "### Per-question unjudged rates",
        "",
        "Each cell shows exposure-proxy top-5 / top-10 counts and rates. "
        "The separate v2-definition "
        "rates are 0% for every question/mode, as explained above.",
        "",
        "| Question | Vector | Keyword | Hybrid | Hybrid rerank |",
        "|---|---|---|---|---|",
    ]
    for r in records:
        vals = []
        for mode in MODES:
            rows = [
                d["exposure_proxy"]
                for d in unknown
                if d["question_id"] == r["id"] and d["mode"] == mode
            ]
            vals.append(
                " / ".join(f"{d['unjudged']}/{d['returned']} ({d['fraction']:.1%})" for d in rows)
            )
        lines.append(f"| {r['id']} | " + " | ".join(vals) + " |")
    lines += [
        "",
        "## Cross-year different-filing overlap",
        "",
        "D032's unchanged heuristic flags five-word-shingle containment ≥0.70 with a gold from "
        "a different accession, requiring at least 20 shingles on each side. It is not a relevance "
        "label or proof of answer equivalence. The JSON lists all 120 top-10 vector/reranked slots "
        "with IDs, ticker, form, fiscal year, period, item, accession, overlap and closest gold.",
        "",
        "| Question | Ticker | Vector near-duplicates / 10 | Reranked near-duplicates / 10 |",
        "|---|---|---:|---:|",
    ]
    for r in records:
        if r["id"] in CROSS_YEAR:
            counts = [
                sum(
                    d["near_duplicate"]
                    for d in near
                    if d["question_id"] == r["id"] and d["mode"] == m
                )
                for m in ["vector", "hybrid_rerank"]
            ]
            lines.append(f"| {r['id']} | {r['filters']['ticker']} | {counts[0]} | {counts[1]} |")
    lines += [
        "",
        "These measured overlaps do not establish that cross-year misses mostly reflect "
        "year disambiguation rather than topical retrieval failure. Unjudged passages cannot be "
        "classified from these labels alone. Period resolution is the M4 planner's responsibility.",
        "",
        "## Coverage, methodology and remaining limits",
        "",
        "The [Phase B report](../../docs/CORPUS_V2_PHASE_B.md) and "
        "[730-slot audit](../../docs/CORPUS_V2_AUDIT.json) document 46 "
        "resolved substantive sections, "
        "nine retained Item 7A reference stubs in the 55 repair slots, and byte-identical "
        "sections outside them. CVX/JPM/XOM market risk remains inside Item 7; DIS/NVIDIA retain "
        "separate Item 7A spans. All 22 JNJ/XOM quarterly risk items are "
        "absent from cached source, "
        "with provenance; no content was synthesized. Source absence and annual-reference "
        "availability still require explicit handling in later interfaces."
        " No corpus repair ran in Phase C.",
        "",
        "Gold means the passage answers the question as a main point. Passing mentions and an "
        "overlap-only tail do not count. Adjacent chunks are both gold when both are needed. "
        "A how-much table is not gold for a why question. Cross-year gold is confined to the named "
        "filing. Questions were narrowed to at most three chunks except the two intentional broad "
        "ones. Questions were AI-assisted drafts, then "
        "student-edited/narrowed and student-labeled; "
        "all new relevance judgments in this review were the student's. Original labeling edits "
        "and limitations remain documented in the unchanged [v1 report](retrieval.md).",
        "",
        "Saved filters resolve yearless questions in M2; a future text-only agent must resolve "
        "that ambiguity. PG ends June 30 and joins the non-December fiscal-calendar cases; add "
        "calendar-year-phrased planner questions in a later milestone. There is no held-out "
        "relevance set here, and no prompt or retrieval tuning was performed in Phase C.",
        "",
        "## Checks and handoff",
        "",
        "See [Phase C checks](../../docs/CORPUS_V2_PHASE_C_CHECKS.md) for exact commands, "
        "Ruff/pytest results and preservation hashes. Machine-readable results: "
        "[rankings/metrics](retrieval_v2.json), [analyses](retrieval_v2_analyses.json), "
        "[pre-evaluation pool inventory](retrieval_v2_pool_inventory.json). "
        "The original retrieval.md/JSON, v1 labels, Phase B reports and "
        "both frozen corpora remain unchanged. "
        "Stop for the student's Phase C acceptance; do not begin M3.",
        "",
    ]
    (ROOT / "evals/results/retrieval_v2.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(metric_table(details)))


def main() -> None:
    with asyncio.Runner(loop_factory=asyncio.SelectorEventLoop) as runner:
        runner.run(build())


if __name__ == "__main__":
    main()

"""evals/results/report.md from cached records only (SPEC §13.6; D094). No API calls.

The report replays the given eval configs from the cache, scores every record with the shared
scorer, and renders: the headline table on test, paired tests against the system, breakdowns by
template / cutoff / restated / derived / B2 gold visibility, the handwritten judge and retrieval
results, the frozen M2 v2 retrieval table, and an uncategorized failure list (categories are M6).
"""

import argparse
import asyncio
import json
import tomllib
from collections import Counter, defaultdict
from decimal import Decimal
from pathlib import Path
from typing import Any

from evals.runner import Runner, load_config, load_questions, replay_deps
from evals.scorers import (
    bootstrap_ci,
    bootstrap_mean_ci,
    holm,
    mcnemar_exact,
    paired_diff_ci,
    percentile,
    score,
)
from filinglens.config import ROOT
from filinglens.llm.pricing import PRICING_PATH

REPORT_PATH = ROOT / "evals" / "results" / "report.md"
NOTES_PATH = ROOT / "evals" / "results" / "report_notes.md"
RETRIEVAL_V2 = ROOT / "evals" / "results" / "retrieval_v2.json"
TEMPLATES = [
    "lookup",
    "yoy_growth",
    "margin",
    "trend_avg",
    "derived_q4",
    "comparison",
    "multi_step",
]
SMALL_N = 30


def pct(x: float) -> str:
    return "–" if x != x else f"{100 * x:.1f}%"


def ci_cell(outcomes: list[bool]) -> str:
    if not outcomes:
        return "–"
    acc, lo, hi = bootstrap_ci(outcomes)
    flag = "*" if len(outcomes) < SMALL_N else ""
    return f"{pct(acc)} [{pct(lo)}, {pct(hi)}] n={len(outcomes)}{flag}"


def scored(
    questions: list[dict[str, Any]], records: list[dict[str, Any]]
) -> dict[str, dict[str, Any]]:
    by_q = {q["id"]: q for q in questions}
    out = {}
    for r in records:
        if r.get("status") == "skipped_spend_cap":
            continue
        q = by_q[r["question_id"]]
        s = score(
            q,
            r.get("prediction"),
            (r.get("error") or {}).get("type") if r.get("status") == "error" else None,
        )
        out[q["id"]] = {"question": q, "record": r, "score": s}
    return out


def bucket(q: dict[str, Any], model: str = "claude-sonnet-5-5") -> str:
    return (q.get("fairness") or {}).get("cutoff_bucket", {}).get(model, "unknown")


def headline_row(name: str, rows: dict[str, dict[str, Any]]) -> list[str]:
    items = list(rows.values())
    outcomes = [x["score"].correct for x in items]
    by_t = {
        t: [x["score"].correct for x in items if x["question"]["template"] == t] for t in TEMPLATES
    }
    before = [x["score"].correct for x in items if bucket(x["question"]) == "before"]
    after = [x["score"].correct for x in items if bucket(x["question"]) == "after"]
    abstain = sum(x["score"].outcome == "abstained" for x in items)
    parse = sum(x["score"].outcome == "parse_failure" for x in items)
    costs = [Decimal(x["record"].get("cost_usd") or 0) for x in items]
    correct = sum(outcomes)
    lat = [x["record"]["latency_ms"] for x in items if x["record"].get("latency_ms") is not None]
    note = items[0]["record"].get("latency_note") if items else None
    cit = [x["record"].get("citations") for x in items if x["record"].get("citations")]
    num_t = sum(c["numeric_total"] for c in cit)
    num_v = sum(c["numeric_valid"] for c in cit)
    cost_total = sum(costs, Decimal(0))
    return [
        name,
        ci_cell(outcomes),
        *[pct(sum(v) / len(v)) if v else "–" for v in by_t.values()],
        pct(sum(before) / len(before)) if before else "–",
        pct(sum(after) / len(after)) if after else "–",
        pct(abstain / len(items)) if items else "–",
        pct(parse / len(items)) if items else "–",
        f"{pct(num_v / num_t)} ({num_v}/{num_t})" if num_t else "–",
        f"${cost_total / len(items):.4f}" if items else "–",
        f"${cost_total / correct:.4f}" if correct else "–",
        note
        or (
            f"{percentile(lat, 0.5) / 1000:.1f}s / {percentile(lat, 0.95) / 1000:.1f}s"
            if lat
            else "–"
        ),
    ]


def disney_segment_oi(q: dict[str, Any]) -> bool:
    """Gold reads Disney's OperatingIncomeLoss, its total segment operating income (D110)."""
    return any(
        i.get("ticker") == "DIS" and i.get("concept") == "OperatingIncomeLoss"
        for i in (q.get("computation") or {}).get("inputs", [])
    )


def cost_per_question(rows: dict[str, dict[str, Any]]) -> tuple[Decimal, bool]:
    """Mean cost per question and whether it was charged at Batch API prices."""
    items = list(rows.values())
    total = sum((Decimal(x["record"].get("cost_usd") or 0) for x in items), Decimal(0))
    batch = any("batch" in (x["record"].get("latency_note") or "") for x in items)
    return total / len(items), batch


def table(header: list[str], rows: list[list[str]]) -> str:
    lines = ["| " + " | ".join(header) + " |", "|" + "|".join("---" for _ in header) + "|"]
    lines += ["| " + " | ".join(r) + " |" for r in rows]
    return "\n".join(lines)


def paired(system: dict[str, Any], others: dict[str, dict[str, Any]]) -> list[list[str]]:
    raw = {}
    rows = []
    for name, other in others.items():
        common = sorted(set(system) & set(other))
        a = [system[q]["score"].correct for q in common]
        b = [other[q]["score"].correct for q in common]
        if not common:
            continue
        sa, sb, p = mcnemar_exact(a, b)
        d, lo, hi = paired_diff_ci(a, b)
        raw[name] = p
        rows.append(
            [
                name,
                str(len(common)),
                str(sa),
                str(sb),
                f"{100 * d:+.1f} pp [{100 * lo:+.1f}, {100 * hi:+.1f}]",
                p,
            ]
        )
    adjusted = holm(raw)
    return [r[:5] + [f"{r[5]:.4f}", f"{adjusted[r[0]]:.4f}"] for r in rows]


def breakdown(name: str, rows: dict[str, dict[str, Any]], key) -> list[list[str]]:
    groups: dict[str, list[bool]] = defaultdict(list)
    for x in rows.values():
        groups[str(key(x))].append(x["score"].correct)
    return [[name, g, ci_cell(v)] for g, v in sorted(groups.items())]


def retrieval_table() -> str:
    data = json.loads(RETRIEVAL_V2.read_text(encoding="utf-8"))
    by_mode: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for d in data["details"]:
        by_mode[d["mode"]].append(d)
    rows = []
    for mode in ("vector", "keyword", "hybrid", "hybrid_rerank"):
        ds = by_mode[mode]
        mean = lambda k, ds=ds: sum(d[k] for d in ds) / len(ds)  # noqa: E731
        mrr = sum(1 / d["first_gold_rank"] if d["first_gold_rank"] else 0 for d in ds) / len(ds)
        rows.append(
            [
                mode,
                f"{mean('capped_recall@5'):.4f}",
                f"{mean('capped_recall@10'):.4f}",
                f"{mean('recall@5'):.4f}",
                f"{mean('recall@10'):.4f}",
                f"{mean('hit@5'):.4f}",
                f"{mean('hit@10'):.4f}",
                f"{mrr:.4f}",
                str(len(ds)),
            ]
        )
    return table(
        [
            "Mode",
            "Capped recall@5",
            "Capped recall@10",
            "Recall@5",
            "Recall@10",
            "Hit@5",
            "Hit@10",
            "MRR@30",
            "n",
        ],
        rows,
    )


async def collect(config_paths: list[Path]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for path in config_paths:
        cfg = load_config(path)
        questions = load_questions(cfg)
        result = await Runner(cfg, replay_deps(cfg), replay_only=True).run()
        for system_id, records in result["records"].items():
            if cfg.split == "handwritten":  # free text: judged (D093), not numerically scored
                out.setdefault("handwritten_questions", {}).update({q["id"]: q for q in questions})
                out.setdefault("handwritten", {}).setdefault(system_id, {}).update(
                    {r["question_id"]: r for r in records}
                )
                continue
            out.setdefault(cfg.split, {}).setdefault(system_id, {}).update(
                scored(questions, records)
            )
    return out


def handwritten_section(data: dict[str, Any]) -> list[str]:
    """Judge scores, calibration agreement, text-claim support and system-level recall."""
    from evals import judge as j
    from evals.system_adapter import recall_at

    judged = data.get("judge", [])
    rubric = [r for r in judged if r["kind"] == "rubric"]
    by_key = {r["key"]: r for r in rubric}
    order_v1, labels_v1 = j.load_labels(j.CALIBRATION_JSONL)
    order, labels = j.load_labels(j.CALIBRATION_V2_JSONL, j.CALIBRATION_V2_MAP)
    complete = bool(order) and len(labels) == len(order)  # v2 is the primary result (D110)
    judge_scores = {k: by_key[k]["result"]["score"] for k in order + order_v1 if k in by_key}
    a = j.agreement(judge_scores, labels) if complete else None
    a_v1 = j.agreement(judge_scores, labels_v1) if labels_v1 else None
    indicative = a is not None and a["indicative_only"]
    mark = " (indicative only)" if indicative else ""
    parts = [f"## Handwritten explanatory questions (30; Opus 5.5 judge, D093){mark}", ""]
    if indicative:
        parts += [
            "**Judge scores in this section are indicative only:** quadratic-weighted κ against "
            f"the student's labels is {a['quadratic_kappa']:.2f} (< 0.6).",
            "",
        ]
    answers = data.get("handwritten", {})
    rows = []
    for sid in sorted({r["system_id"] for r in rubric}):
        mine = [r for r in rubric if r["system_id"] == sid]
        scores = [r["result"]["score"] for r in mine if (r.get("result") or {}).get("parse_ok")]
        no_answer = sum(  # D108: no answer (e.g. token budget) is not judged and scores 1
            r.get("status") == "error" or not (r.get("prediction") or {}).get("text", "").strip()
            for r in answers.get(sid, {}).values()
        )
        total = len(answers.get(sid, {})) or len(mine)
        cells = []
        for values in (scores + [1] * no_answer, scores):
            mean, lo, hi = bootstrap_mean_ci(values)
            cells.append(f"{mean:.2f} [{lo:.2f}, {hi:.2f}]" if values else "–")
        dist = Counter(scores)
        rows.append(
            [
                sid,
                *cells,
                f"{no_answer}/{total}",
                " / ".join(str(dist[s]) for s in range(1, 6)),
                str(len(mine) - len(scores)),
            ]
        )
    parts += [
        table(
            [
                "System",
                "Mean, no answer = 1 [95% CI]",
                "Mean over answered [95% CI]",
                "No answer",
                "Judged scores 1/2/3/4/5",
                "Unparsed",
            ],
            rows,
        ),
        "",
    ]

    def stats(x: dict[str, Any]) -> str:
        return (
            f"n={x['n']}: exact {pct(x['exact'])}, within 1 {pct(x['within_1'])}, "
            f"quadratic-weighted κ {x['quadratic_kappa']:.2f}"
        )

    if a is not None:
        parts += [
            f"Judge calibration (primary, v2: shuffled blind sheet, D110) {stats(a)}"
            + (" — the judge is indicative only (κ < 0.6)." if a["indicative_only"] else "."),
            "",
        ]
    else:
        parts += [
            "Judge calibration (primary, v2: shuffled blind sheet, D110): pending the "
            "student's labels.",
            "",
        ]
    if a_v1 is not None:
        parts += [
            f"First attempt (v1, contaminated) {stats(a_v1)}. The v1 sheet listed answers in a "
            "cycle of judge scores (2, 3, 4, 5 repeated), so position matched the judge's score; "
            "it is kept as provenance, not as the calibration result (D110).",
            "",
        ]
    sampled = [judge_scores[k] for k in order or order_v1 if k in judge_scores]
    if sampled and 1 not in sampled:
        parts += [
            f"The calibration sample covers judge scores {min(sampled)}-{max(sampled)} only: no "
            "answered output was judged 1, so agreement at the bottom of the scale is untested.",
            "",
        ]
    if a is not None:  # per-item table only once v2 labeling is complete
        parts += [
            table(
                ["v2 item", "Key", "System", "Judge", "Student v2", "Δ", "Student v1"],
                [
                    [
                        str(i),
                        f"`{k[:8]}`",
                        by_key[k]["system_id"],
                        str(judge_scores[k]),
                        str(labels[k]),
                        f"{labels[k] - judge_scores[k]:+d}",
                        str(labels_v1.get(k, "–")),
                    ]
                    for i, k in enumerate(order, 1)
                    if k in judge_scores
                ],
            ),
            "",
        ]
    system = data.get("handwritten", {}).get("system", {})
    cites = [r.get("citations") or {} for r in system.values()]
    text_total = sum(c.get("text_total", 0) for c in cites)
    string_ok = sum(c.get("text_string_supported", 0) for c in cites)
    claims = [r for r in judged if r["kind"] == "claim" and (r.get("result") or {}).get("parse_ok")]
    judge_ok = sum(r["result"]["supported"] for r in claims)
    parts += [
        f"System text claims: {text_total}; supported by string match {string_ok}, by the claim "
        f"judge{mark} {judge_ok} of {len(claims)} judged"
        + (f" ({pct((string_ok + judge_ok) / text_total)} supported)." if text_total else "."),
        "",
    ]
    questions = data.get("handwritten_questions", {})
    recall = {5: [], 10: []}
    for qid, rec in system.items():
        gold = questions.get(qid, {}).get("gold_chunk_ids") or []
        if gold and rec.get("retrieval"):
            for k in recall:
                recall[k].append(recall_at(gold, rec["retrieval"], k))
    if recall[5]:
        parts += [
            "System-level retrieval (filings workers' first search, D099): "
            f"recall@5 {sum(recall[5]) / len(recall[5]):.3f}, "
            f"recall@10 {sum(recall[10]) / len(recall[10]):.3f} (n={len(recall[5])}).",
            "",
        ]
    return parts


METHODOLOGY = [
    "## Methodology and limitations",
    "",
    "- **What system accuracy measures (D104).** Gold values are computed from the same "
    "`financial_facts` table the system's `get_financial_metric` tool reads. System accuracy "
    "therefore measures planning, fiscal-period mapping, arithmetic and answer formatting given "
    "correct structured data. It does not measure extraction of numbers from filings.",
    "- **How the gold was checked.** The student verified all 20 review-sample gold values "
    "against the original SEC filings and/or the companies' earnings releases, with no "
    "discrepancies. The other gold values rest on the same M1 extraction.",
    "- **Comparisons with data access.** B2 and B1 can reach the same numbers as the system and "
    "are listed first after it. B2 is an oracle-context baseline: it is given the gold filings' "
    "financial statements, so it skips finding the company, filing and period, which the "
    "system does itself. B1 has open web search. B0 (closed book) measures what the model knows "
    "without any data.",
    "- **Scope (D105, D109).** The system, B0 Sonnet, B1 and B2 run on a frozen 180-question "
    "test subset (the 100-question sample plus 80 stratified questions). B0 Opus and B0 Fable "
    "5.2 run on the 100-question sample, where every system answers the same questions and is "
    "paired with the system.",
    "- **B2 context limit (D109).** B2 contexts were capped at 25K tokens per filing and 50K "
    "per question (D089), but those caps were measured as characters/4. Financial-statement "
    "tables tokenize about 1.9 times denser, so real contexts averaged about 23K tokens and the "
    "largest were near 95K.",
    "- **Cutoff and sample notes.** The test split includes a 20% after-cutoff floor per "
    "template (D086), except comparison at 14.5% (8 of 55): the same-sector pool has only 8 "
    "after-cutoff pairs (D101). After-cutoff questions concentrate in companies whose fiscal "
    "year ends mid-year (NKE, MSFT, PG, COST), so the cutoff breakdown is descriptive. "
    "Comparisons pair same-sector companies only (GICS, D101). JPM has no question in the "
    "100-question sample (seeded draw).",
    "",
]
DATA_ACCESS = {
    "system": "XBRL facts + filing passages (MCP tools)",
    "b2": "gold filings' statements in context",
    "b1": "open web search",
    "b0": "none (closed book)",
}
ORDER = ("system", "b2", "b1", "b0")


def access(name: str) -> str:
    return next((v for k, v in DATA_ACCESS.items() if name.startswith(k)), "–")


def ordered(systems: dict[str, Any]) -> list[str]:
    """The system first, then the equal-data-access baselines (B2, B1), then B0 (D104)."""
    rank = {k: i for i, k in enumerate(ORDER)}
    return sorted(systems, key=lambda n: (next((rank[k] for k in ORDER if n.startswith(k)), 9), n))


def interpretation(
    test: dict[str, dict[str, Any]], system_id: str, batch_multiplier: Decimal | None
) -> list[str]:
    """B2 as an oracle-context baseline (with costs) and the Disney gold-definition sensitivity."""
    system = test.get(system_id)
    b2 = next((test[k] for k in ordered(test) if k.startswith("b2")), None)
    if not system or not b2:
        return []
    common = sorted(set(system) & set(b2))
    sys_acc = sum(system[q]["score"].correct for q in common) / len(common)
    b2_acc = sum(b2[q]["score"].correct for q in common) / len(common)
    sys_cost, _ = cost_per_question({q: system[q] for q in common})
    b2_cost, b2_batch = cost_per_question({q: b2[q] for q in common})
    real_time = b2_batch and batch_multiplier is not None
    b2_real = b2_cost / batch_multiplier if real_time else b2_cost
    parts = [
        "## Interpretation",
        "",
        "- **B2 is an oracle-context baseline.** It is handed the financial statements of the "
        "gold filings, so it never has to find the company, the filing or the fiscal period. "
        "The system starts from the question alone and locates the data itself (company "
        "resolution, filing and fiscal-period mapping, metric lookup, arithmetic). On the "
        f"{len(common)} questions both answered, the system scores {pct(sys_acc)} and B2 "
        f"{pct(b2_acc)}: the system matches the oracle-context baseline while locating the data "
        f"itself. Cost per question: system ${sys_cost:.3f} (real time); B2 ${b2_cost:.3f}"
        + (
            f" at Batch API prices, about ${b2_real:.3f} in real time, so the system costs "
            f"{sys_cost / b2_real:.1f}x B2's real-time price."
            if real_time
            else (" at Batch API prices." if b2_batch else ".")
        ),
        "- **Disney operating income is a gold-definition ambiguity.** Disney's income statement "
        "has no operating-income line; the stored `OperatingIncomeLoss` fact is its total "
        "segment operating income from the segment disclosure, and the gold uses it. A reader "
        "of the income statement can reasonably build a different figure. Results are shown "
        "with and without these questions; the definition is an M6 data-definition item (D110).",
        "",
    ]
    excluded = {q for q, x in system.items() if disney_segment_oi(x["question"])}
    rows = []
    for name in ordered(test):
        v = test[name]
        kept = [x["score"].correct for q, x in v.items() if q not in excluded]
        rows.append(
            [
                name,
                ci_cell([x["score"].correct for x in v.values()]),
                str(sum(q in excluded for q in v)),
                ci_cell(kept),
            ]
        )
    without = {k: {q: x for q, x in v.items() if q not in excluded} for k, v in test.items()}
    parts += [
        table(
            ["System", "Accuracy (all)", "Disney segment-OI questions", "Accuracy without"], rows
        ),
        "",
        "Paired tests vs the system without the Disney segment-operating-income questions:",
        "",
        table(
            ["vs", "n", "system only", "other only", "Δ accuracy [95% CI]", "McNemar p", "Holm p"],
            paired(without[system_id], {k: v for k, v in without.items() if k != system_id}),
        ),
        "",
    ]
    return parts


def render(data: dict[str, Any], system_id: str = "system") -> str:
    parts = [
        "# FilingLens benchmark report",
        "",
        "Generated from cached run records only (`python -m evals.report`). Accuracy cells: "
        "accuracy [95% bootstrap CI] n; `*` marks n < 30 (descriptive).",
        "",
        *METHODOLOGY,
    ]
    test = data.get("test", {})
    header = [
        "System",
        "Data access",
        "Accuracy",
        *TEMPLATES,
        "Before cutoff",
        "After cutoff",
        "Abstained",
        "Parse fail",
        "Citation validity (numeric)",
        "$/question",
        "$/correct",
        "Latency p50/p95",
    ]
    sample = {
        k: {q: x for q, x in v.items() if x["question"].get("sample_100")} for k, v in test.items()
    }

    def rows_for(group: dict[str, dict[str, Any]]) -> list[list[str]]:
        return [
            [r[0], access(r[0]), *r[1:]]
            for r in (headline_row(k, group[k]) for k in ordered(group) if group[k])
        ]

    parts += [
        "## Headline: every system on the same frozen 100-question test sample",
        "",
        "B2 and B1 have data access comparable to the system's; B0 has none (D104).",
        "",
        table(header, rows_for(sample)),
        "",
        "## Larger test subset: every system run on all 180 questions (D105, D109)",
        "",
        table(header, rows_for({k: v for k, v in test.items() if len(v) > len(sample[k])})),
        "",
    ]
    if system_id in test:
        parts += [
            "## Paired tests vs the system",
            "",
            table(
                [
                    "vs",
                    "n",
                    "system only",
                    "other only",
                    "Δ accuracy [95% CI]",
                    "McNemar p",
                    "Holm p",
                ],
                paired(test[system_id], {k: v for k, v in test.items() if k != system_id}),
            ),
            "",
        ]
        multiplier = data.get("batch_multiplier")  # from pricing.toml [eval], set by main
        parts += interpretation(test, system_id, Decimal(multiplier) if multiplier else None)
    parts += ["## Breakdowns (test)", ""]
    rows: list[list[str]] = []
    for name in ordered(test):
        v = test[name]
        rows += breakdown(name, v, lambda x: f"template {x['question']['template']}")
        rows += breakdown(name, v, lambda x: f"cutoff {bucket(x['question'])}")
        rows += breakdown(name, v, lambda x: f"restated {x['question']['fairness']['restated']}")
        rows += breakdown(name, v, lambda x: f"derived {x['question']['fairness']['derived_q4']}")
        b2 = [x for x in v.values() if x["record"].get("b2_context")]
        if b2:
            rows += breakdown(
                name,
                {x["question"]["id"]: x for x in b2},
                lambda x: f"gold_visible {x['record']['b2_context']['gold_visible']}",
            )
    parts += [table(["System", "Group", "Accuracy"], rows), ""]
    probe = data.get("probe", {})
    if probe:
        parts += [
            "## Abstention probe (outside the headline)",
            "",
            table(
                ["System", "Correct abstentions"],
                [[k, ci_cell([x["score"].correct for x in v.values()])] for k, v in probe.items()],
            ),
            "",
        ]
    if data.get("judge") or data.get("handwritten"):
        parts += handwritten_section(data)
    parts += ["## Retrieval (frozen M2 v2, 30 handwritten questions)", "", retrieval_table(), ""]
    parts += ["## Failures (uncategorized; categorization is M6)", ""]
    for name, v in test.items():
        wrong = [x for x in v.values() if not x["score"].correct]
        hints = defaultdict(int)
        for x in wrong:
            hints[x["score"].outcome + (" (unit rescue)" if x["score"].unit_rescue else "")] += 1
        parts.append(
            f"- **{name}**: {len(wrong)} wrong — "
            + ", ".join(f"{k} {n}" for k, n in sorted(hints.items()))
        )
    abstained = [x for x in test.get(system_id, {}).values() if x["score"].outcome == "abstained"]
    if abstained:
        parts += [
            "",
            f"### System abstentions on test ({len(abstained)})",
            "",
            "Every generated question has a gold value computed from stored facts, so the data "
            "never justifies an abstention here (D085).",
            "",
        ]
        for x in abstained:
            q, answer = x["question"], x["record"].get("raw_output") or {}
            reason = " ".join([answer.get("summary") or "", *answer.get("caveats", [])]).strip()
            parts += [
                f"- `{q['id']}` ({q['template']}, {', '.join(q['companies'])}): {q['question']} "
                f"Gold {q['gold_value']} {q['gold_unit']}; the system answered "
                f"{x['record']['prediction'].get('status')}. Stated reason: {reason or '–'}",
            ]
    if NOTES_PATH.exists():  # the analyst's notes on the results, included verbatim
        parts += ["", NOTES_PATH.read_text(encoding="utf-8").strip()]
    parts += ["", "## Ablations", "", "_M6._", ""]
    return "\n".join(parts)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Render evals/results/report.md from the cache.")
    parser.add_argument("configs", nargs="+", type=Path)
    args = parser.parse_args(argv)
    data = asyncio.run(collect(args.configs))
    from evals import judge
    from evals.runner import SystemConfig, resolve_model
    from filinglens.agents.settings import RuntimeSettings

    model = resolve_model(
        SystemConfig(
            id="judge",
            kind="b0",
            model_env=judge.JUDGE_MODEL_ENV,
            model_index=judge.JUDGE_MODEL_INDEX,
        ),
        RuntimeSettings(),
    )
    data["judge"] = judge.load_judged(model)
    data["batch_multiplier"] = tomllib.loads(PRICING_PATH.read_text(encoding="utf-8"))["eval"][
        "batch_multiplier"
    ]
    REPORT_PATH.write_text(render(data), encoding="utf-8")
    print(f"wrote {REPORT_PATH}")


if __name__ == "__main__":
    main()

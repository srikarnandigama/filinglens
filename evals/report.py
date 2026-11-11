"""evals/results/report.md from cached records only (SPEC §13.6; D094). No API calls.

The report replays the given eval configs from the cache, scores every record with the shared
scorer, and renders: the headline table on test, paired tests against the system, breakdowns by
template / cutoff / restated / derived / B2 gold visibility, the handwritten judge and retrieval
results, the frozen M2 v2 retrieval table, and an uncategorized failure list (categories are M6).
"""

import argparse
import asyncio
import json
from collections import defaultdict
from decimal import Decimal
from pathlib import Path
from typing import Any

from evals.runner import Runner, load_config, load_questions, replay_deps
from evals.scorers import bootstrap_ci, holm, mcnemar_exact, paired_diff_ci, percentile, score
from filinglens.config import ROOT

REPORT_PATH = ROOT / "evals" / "results" / "report.md"
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
            out.setdefault(cfg.split, {}).setdefault(system_id, {}).update(
                scored(questions, records)
            )
    return out


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
    "- **Comparisons with equal data access.** B2 (the gold filings' financial statements in "
    "context) and B1 (open web search) can reach the same numbers as the system. They are the "
    "fair comparisons and are listed first after the system. B0 (closed book) measures what "
    "the model knows without any data.",
    "- **Scope (D105).** The system and B0 Sonnet run on a frozen 180-question test subset (the "
    "100-question sample plus 80 stratified questions). B0 Opus, B1 and B2 run on the "
    "100-question sample, where every system answers the same questions and is paired with the "
    "system.",
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
        "## Larger test subset (system and B0 Sonnet, 180 questions, D105)",
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
    parts += ["## Breakdowns (test)", ""]
    rows: list[list[str]] = []
    for name, v in test.items():
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
    parts += ["", "## Ablations", "", "_M6._", ""]
    return "\n".join(parts)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Render evals/results/report.md from the cache.")
    parser.add_argument("configs", nargs="+", type=Path)
    args = parser.parse_args(argv)
    data = asyncio.run(collect(args.configs))
    REPORT_PATH.write_text(render(data), encoding="utf-8")
    print(f"wrote {REPORT_PATH}")


if __name__ == "__main__":
    main()

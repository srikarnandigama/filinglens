"""M6 report sections (D111-D125): before/after on identical questions, dev validation, the
ablation table and the failure analysis.

Two steps, so the report itself needs no database or API:

    python -m evals.m6_report collect   # traces -> evals/results/m6_mechanics.json (needs the DB)
    python -m evals.report <M5 configs> --m6   # renders everything from caches and that file

`collect` reads each cached run's trace read-only and stores its mechanics (price-weighted
tokens, cost at uncached prices, cache tokens, guard events, revisions) and its D112 failure
categories. `sections` pairs records by question ID; every comparison uses identical questions.
"""

import argparse
import asyncio
import json
import math
import random
import statistics as st
from collections import Counter
from decimal import Decimal
from pathlib import Path
from typing import Any

from evals.scorers import bootstrap_ci, bootstrap_mean_ci, mcnemar_exact, paired_diff_ci, percentile
from filinglens.config import ROOT

MECHANICS_PATH = ROOT / "evals" / "results" / "m6_mechanics.json"
CONFIGS = ROOT / "evals" / "configs"
SEED = 20261109
# (config, system id) pairs whose runs are collected; M5 rows are the accepted system's records.
RUNS = (
    ("m5_dev_pilot", "system"),
    ("m5_test_subset", "system"),
    ("m5_handwritten", "system"),
    ("m6_dev_numeric", "m6"),
    ("m6_dev_explanatory_m5", "system"),
    ("m6_dev_explanatory", "m6"),
    ("m6_test_sample", "m6"),
    ("m6_test_no_verifier", "m6-no-verifier"),
    ("m6_test_no_quant", "m6-no-quant"),
    ("m6_handwritten", "m6"),
    ("m6_handwritten_rerank", "m6-rerank"),
    ("m6_handwritten_hybrid", "m6-hybrid"),
)


# ---------------------------------------------------------------- loading


def load(config: str, system_id: str) -> tuple[list[dict], dict[str, dict]]:
    """Questions and this system's cached records by question ID (replay only)."""
    from evals.runner import Runner, load_config, load_questions, replay_deps

    cfg = load_config(CONFIGS / f"{config}.toml")
    result = asyncio.run(Runner(cfg, replay_deps(cfg), replay_only=True).run())
    return load_questions(cfg), {r["question_id"]: r for r in result["records"][system_id]}


def mechanics(events: list[Any], prices: Any, reference: str) -> dict[str, Any]:
    """Per-run mechanics from the trace (D113 weights, D116 cache tokens, D115 guards)."""
    from filinglens.agents.toolbox import ROLE_TOOLS

    known = {t for tools in ROLE_TOOLS.values() for t in tools}
    m: Counter = Counter()
    weighted = uncached = Decimal(0)
    instances = set()
    ref = prices.prices[reference].input_per_mtok
    for e in events:
        p = e.payload
        if e.event_type == "llm_call":
            u = p["response"]["usage"]
            price = prices.prices[p["model"]]
            cached = u.get("cache_read_tokens", 0) + u.get("cache_write_tokens", 0)
            total = u["input_tokens"] + u["output_tokens"] + cached
            weighted += total * price.input_per_mtok / ref
            uncached += (
                (u["input_tokens"] + cached) * price.input_per_mtok
                + u["output_tokens"] * price.output_per_mtok
            ) / Decimal(1_000_000)
            instances.add(p["instance"])
            if (
                not p["response"].get("tool_calls")
                and not (p["response"].get("text") or "").strip()
            ):
                m["empty_replies"] += 1
        elif e.event_type == "tool_call":
            if p.get("rejected") == "TOOL_NOT_ALLOWED" and p.get("tool") not in known:
                m["invalid_tool_calls"] += 1
        elif e.event_type == "stall_guard":
            m[f"guard_{p['reason']}"] += 1
        elif e.event_type == "verification" and "failing" in p:
            m["verifier_rounds"] += 1
        elif e.event_type in (
            "revision_skipped",
            "budget_finalized",
            "budget_stopped_without_draft",
        ):
            m[e.event_type] += 1
    m["analyst_rounds"] = sum(i.startswith("analyst") for i in instances)
    m["filings_workers"] = sum(i.startswith("filings") for i in instances)
    return {**m, "weighted_tokens": int(weighted), "uncached_cost": str(uncached)}


def collect(out: Path = MECHANICS_PATH) -> dict[str, Any]:
    from uuid import UUID

    from evals.failures import categorize
    from evals.runner import HANDWRITTEN
    from filinglens.agents.settings import RuntimeSettings
    from filinglens.agents.tracing import load_run
    from filinglens.llm.pricing import PriceTable

    settings = RuntimeSettings()
    gold = {
        row["id"]: row["gold_chunk_ids"]
        for row in map(json.loads, HANDWRITTEN.read_text(encoding="utf-8").splitlines())
    }
    data: dict[str, Any] = {}
    for config, system_id in RUNS:
        _, records = load(config, system_id)
        rows = {}
        for qid, record in sorted(records.items()):
            if not record.get("run_id"):
                continue
            meta, events = load_run(settings.database_url, UUID(record["run_id"]))
            prices = PriceTable.from_snapshot(meta["config"]["pricing"])
            reference = meta["config"]["models"]["planner"]["id"]
            rows[qid] = {
                "split": record["split"],
                "mechanics": mechanics(events, prices, reference),
                "categories": categorize(record, events, gold.get(qid)),
            }
        data[f"{config}:{system_id}"] = rows
    out.write_text(json.dumps(data, indent=1, sort_keys=True), encoding="utf-8")
    return data


# ---------------------------------------------------------------- statistics


def mean_diff_ci(a: list[float], b: list[float], n: int = 10_000) -> tuple[float, float, float]:
    """Mean of paired differences a - b with a percentile bootstrap CI (D094 style)."""
    pairs = list(zip(a, b, strict=True))
    rng = random.Random(SEED)
    diffs = sorted(
        sum(x - y for x, y in rng.choices(pairs, k=len(pairs))) / len(pairs) for _ in range(n)
    )
    return (st.mean(x - y for x, y in pairs), diffs[int(0.025 * n)], diffs[int(0.975 * n)])


def sign_test(a: list[float], b: list[float]) -> tuple[int, int, float]:
    """Exact two-sided sign test on paired scores: (a higher, b higher, p)."""
    up = sum(x > y for x, y in zip(a, b, strict=True))
    down = sum(x < y for x, y in zip(a, b, strict=True))
    n = up + down
    if n == 0:
        return (0, 0, 1.0)
    tail = sum(math.comb(n, i) for i in range(min(up, down) + 1)) / 2**n
    return (up, down, min(1.0, 2 * tail))


def pct(x: float) -> str:
    return f"{100 * x:.1f}%"


def money(x: float) -> str:
    sign = "−" if x < 0 else ""
    return f"{sign}${abs(x):.4f}" if abs(x) < 1 else f"{sign}${abs(x):.2f}"


def table(header: list[str], rows: list[list[str]]) -> str:
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    return "\n".join(lines + ["| " + " | ".join(r) + " |" for r in rows])


def latency(records: list[dict]) -> str:
    values = [(r.get("latency_ms") or 0) / 1000 for r in records]
    return f"{percentile(values, 0.5):.1f}s / {percentile(values, 0.95):.1f}s"


# ---------------------------------------------------------------- numeric questions


def numeric_rows(questions, records) -> dict[str, dict]:
    from evals.report import scored

    return scored(questions, list(records.values()))


def citation_cells(records: list[dict]) -> tuple[str, str, str]:
    """Numeric validity (Stage 1 offline, D092), text claims supported by string match, and
    numeric claims without a fact or computation citation (model arithmetic)."""
    cites = [r.get("citations") or {} for r in records]
    num_total = sum(c.get("numeric_total", 0) for c in cites)
    num_ok = sum(c.get("numeric_valid", 0) for c in cites)
    text_total = sum(c.get("text_total", 0) for c in cites)
    text_ok = sum(c.get("text_string_supported", 0) for c in cites)
    model_math = sum(
        1
        for r in records
        for c in (r.get("raw_output") or {}).get("claims") or []
        if c.get("kind") == "numeric" and c.get("value_basis") == "model_arithmetic"
    )
    numeric = f"{pct(num_ok / num_total)} ({num_ok}/{num_total})" if num_total else "–"
    text = f"{text_ok}/{text_total} by string match" if text_total else "no text claims"
    return numeric, text, f"{model_math}/{num_total}" if num_total else "–"


def before_after_numeric(m5q, m5r, m6r) -> list[str]:
    from evals.report import disney_segment_oi

    ids = sorted(set(m6r))
    s5, s6 = numeric_rows(m5q, {i: m5r[i] for i in ids}), numeric_rows(m5q, m6r)
    a6 = [s6[i]["score"].correct for i in ids]
    a5 = [s5[i]["score"].correct for i in ids]
    c6 = [float(m6r[i]["cost_usd"]) for i in ids]
    c5 = [float(m5r[i]["cost_usd"]) for i in ids]
    l6 = [m6r[i]["latency_ms"] / 1000 for i in ids]
    l5 = [m5r[i]["latency_ms"] / 1000 for i in ids]
    only6, only5, p = mcnemar_exact(a6, a5)
    d, lo, hi = paired_diff_ci(a6, a5)
    rows = []
    for name, acc in (("M5 system", a5), ("M6 system", a6)):
        mean, alo, ahi = bootstrap_ci(acc)
        rows.append([name, f"{pct(mean)} [{pct(alo)}, {pct(ahi)}] n={len(acc)}"])
    no_dis = [i for i in ids if not disney_segment_oi(s6[i]["question"])]
    out = [
        "### Numeric test sample (50 questions, frozen, D121): M5 vs M6",
        "",
        table(["System", "Accuracy [95% CI]"], rows),
        "",
        f"Paired: M6 only correct {only6}, M5 only correct {only5}; Δ accuracy "
        f"{100 * d:+.1f} pp [{100 * lo:+.1f}, {100 * hi:+.1f}], exact McNemar p = {p:.3f}. "
        f"Without the Disney segment-operating-income questions (D119): n = {len(no_dis)}, "
        f"M5 {sum(s5[i]['score'].correct for i in no_dis)}/{len(no_dis)}, "
        f"M6 {sum(s6[i]['score'].correct for i in no_dis)}/{len(no_dis)}.",
        "",
    ]
    dc = mean_diff_ci(c6, c5)
    dl = mean_diff_ci(l6, l5)
    m5_latency = latency([m5r[i] for i in ids])
    out += [
        f"$/question: M5 {money(st.mean(c5))}, M6 {money(st.mean(c6))} (Δ {money(dc[0])} "
        f"[{money(dc[1])}, {money(dc[2])}]). Latency p50/p95: M5 {m5_latency}, "
        f"M6 {latency(list(m6r.values()))} (mean Δ {dl[0]:+.1f}s [{dl[1]:+.1f}, {dl[2]:+.1f}]).",
        "",
    ]
    costco = "q_7efc51f876d501c0"
    if costco in ids:
        out += [
            f"The M5 test miss (`{costco}`, Costco trend_avg): M5 {s5[costco]['score'].outcome} at "
            f"{money(c5[ids.index(costco)])}; M6 {s6[costco]['score'].outcome} at "
            f"{money(c6[ids.index(costco)])}.",
            "",
        ]
    return out


# ---------------------------------------------------------------- handwritten questions


def judged_scores(judged: list[dict], system_id: str) -> dict[str, int]:
    return {
        r["question_id"]: r["result"]["score"]
        for r in judged
        if r["kind"] == "rubric"
        and r["system_id"] == system_id
        and (r.get("result") or {}).get("parse_ok")
    }


def answered(record: dict) -> bool:
    return record.get("status") != "error" and bool(
        (record.get("prediction") or {}).get("text", "").strip()
    )


def hw_scores(records: dict[str, dict], scores: dict[str, int], ids: list[str]) -> list[int]:
    """Judge score per question; no answer scores 1 (D108)."""
    return [scores.get(q, 1) if answered(records[q]) else 1 for q in ids]


def recall(records: dict[str, dict], questions: dict[str, dict], k: int) -> float:
    from evals.system_adapter import recall_at

    values = [
        recall_at(questions[q]["gold_chunk_ids"], r["retrieval"], k)
        for q, r in records.items()
        if r.get("retrieval") and questions[q].get("gold_chunk_ids")
    ]
    return sum(values) / len(values) if values else float("nan")


def text_validity(records: dict[str, dict], judged: list[dict], system_id: str) -> str:
    cites = [r.get("citations") or {} for r in records.values()]
    total = sum(c.get("text_total", 0) for c in cites)
    string_ok = sum(c.get("text_string_supported", 0) for c in cites)
    pending = {
        (q, c["claim_id"])
        for q, r in records.items()
        for c in (r.get("citations") or {}).get("text_pending_judge", [])
    }
    claims = [
        r
        for r in judged
        if r["kind"] == "claim"
        and r["system_id"] == system_id  # claim ids repeat across answers; match the system
        and (r["question_id"], r.get("claim_id")) in pending
        and (r.get("result") or {}).get("parse_ok")
    ]
    judge_ok = sum(r["result"]["supported"] for r in claims)
    if not total:
        return "–"
    return (
        f"{pct((string_ok + judge_ok) / total)} ({string_ok} string + {judge_ok} judge of "
        f"{total}; {len(pending) - len(claims)} unjudged)"
    )


def before_after_handwritten(questions, m5r, m6r, judged) -> list[str]:
    ids = sorted(m6r)
    q = {x["id"]: x for x in questions}
    s5 = hw_scores(m5r, judged_scores(judged, "system"), ids)
    s6 = hw_scores(m6r, judged_scores(judged, "m6"), ids)
    a5 = [answered(m5r[i]) for i in ids]
    a6 = [answered(m6r[i]) for i in ids]
    rows = []
    for name, s, a, r in (("M5 system", s5, a5, m5r), ("M6 system", s6, a6, m6r)):
        mean, lo, hi = bootstrap_mean_ci(s)
        answered_scores = [x for x, ok in zip(s, a, strict=True) if ok]
        amean, alo, ahi = bootstrap_mean_ci(answered_scores)
        costs = [float(r[i]["cost_usd"]) for i in ids]
        rows.append(
            [
                name,
                f"{mean:.2f} [{lo:.2f}, {hi:.2f}]",
                f"{amean:.2f} [{alo:.2f}, {ahi:.2f}]" if answered_scores else "–",
                f"{len(ids) - sum(a)}/{len(ids)}",
                f"{recall(r, q, 5):.3f} / {recall(r, q, 10):.3f}",
                money(st.mean(costs)),
                latency([r[i] for i in ids]),
            ]
        )
    d = mean_diff_ci([float(x) for x in s6], [float(x) for x in s5])
    up, down, p_sign = sign_test(s6, s5)
    gained, lost, p_mc = mcnemar_exact(a6, a5)
    formerly = [i for i, ok in zip(ids, a5, strict=True) if not ok]
    return [
        "### Handwritten explanatory questions (30, test, run once with the final M6 system)",
        "",
        table(
            [
                "System",
                "Judge mean, no answer = 1 [95% CI]",
                "Mean over answered [95% CI]",
                "No answer",
                "Recall@5 / @10 (D099)",
                "$/question",
                "Latency p50/p95",
            ],
            rows,
        ),
        "",
        f"Paired on the same 30: Δ judge mean (no answer = 1) {d[0]:+.2f} [{d[1]:+.2f}, "
        f"{d[2]:+.2f}]; M6 scored higher on {up}, lower on {down} (exact sign test p = "
        f"{p_sign:.3f}). Answered: M6 only {gained}, M5 only {lost} (exact McNemar p = "
        f"{p_mc:.3f}). The {len(formerly)} M5 no-answers scored "
        + ", ".join(str(s6[ids.index(i)]) for i in formerly)
        + " under M6.",
        "",
    ]


# ---------------------------------------------------------------- the report sections


def sections(judged: list[dict]) -> list[str]:
    data = json.loads(MECHANICS_PATH.read_text(encoding="utf-8"))
    tq, m5_test = load("m5_test_subset", "system")
    _, m6_test = load("m6_test_sample", "m6")
    _, nv = load("m6_test_no_verifier", "m6-no-verifier")
    _, nq = load("m6_test_no_quant", "m6-no-quant")
    hq, m5_hw = load("m5_handwritten", "system")
    _, m6_hw = load("m6_handwritten", "m6")
    _, rerank = load("m6_handwritten_rerank", "m6-rerank")
    _, hybrid = load("m6_handwritten_hybrid", "m6-hybrid")

    def uncached(key: str, ids: list[str]) -> float:
        return st.mean(float(data[key][i]["mechanics"]["uncached_cost"]) for i in ids)

    ids50 = sorted(m6_test)
    ids30 = sorted(m6_hw)
    m5_cost50 = st.mean(float(m5_test[i]["cost_usd"]) for i in ids50)
    m6_cost50 = st.mean(float(m6_test[i]["cost_usd"]) for i in ids50)
    m5_cost30 = st.mean(float(m5_hw[i]["cost_usd"]) for i in ids30)
    m6_cost30 = st.mean(float(m6_hw[i]["cost_usd"]) for i in ids30)
    parts = [
        "## M6: improvement, ablations and failure analysis",
        "",
        "Generated by `python -m evals.report ... --m6` from cached records, the judge cache and "
        "`evals/results/m6_mechanics.json` (trace mechanics, `python -m evals.m6_report collect`). "
        "The M5 sections above are unchanged and still regenerate from the M5 cache alone. Every "
        "before/after comparison uses identical questions with paired tests (exact McNemar or "
        "sign test, paired bootstrap CIs, 10,000 resamples, seed 20261109).",
        "",
        "### What changed in M6, and what the evidence covers",
        "",
        "- **Fixes (D113-D115), each behind a flag whose default is M5 behavior (D118):** a "
        "price-weighted run token budget (Haiku worker tokens count 1/20, Sonnet runs unchanged); "
        "an explicit answer instead of a run error when the budget stops a run before any draft "
        "(still scored as no answer); a guard that forces the final step after 2 no-progress "
        "tool steps; a hint for nonexistent tool names; and empty replies answered with the "
        "final-step guard. **Cost changes:** prompt caching (D116) and summary numbers that "
        "round cited values (D117).",
        f"- **(a) The cost saving is prompt caching; the other fixes were cost-neutral on dev.** "
        f"On the 50 numeric test questions M6 costs {money(m6_cost50)}/question vs M5's "
        f"{money(m5_cost50)}; at uncached prices M6 would cost "
        f"{money(uncached('m6_test_sample:m6', ids50))}. On the 35 dev numeric questions M6 "
        "measured $0.062 vs $0.138, and $0.140 at uncached prices (Δ vs M5 +$0.002 [−0.007, "
        "+0.011]): the fixes changed steps and outcomes, not cost.",
        "- **(b) The dev explanatory prompts did not reproduce the original budget failure.** "
        "The M5 system answered all 10 of them, so the no-draft fix (A2, D114) and the weighted "
        "budget's effect on no-answers are validated only by the handwritten test rerun below. "
        "On dev, two M6 runs went past 200K raw tokens and finished within the weighted budget, "
        "and M5 skipped two revisions for budget that M6 did not.",
        "- **(c) Dev validation for the explanatory fixes was mechanical only** (D111, D120): no "
        "reference answers and no judge, so it says nothing about answer quality.",
        "- **Selection caveat (D111):** the budget and loop failures behind the fixes were found "
        "on test in M5, so the test rerun measures fixes partly selected from test failures.",
        "",
        "### Fixes: before/after on identical test questions",
        "",
    ]
    parts += before_after_numeric(tq, m5_test, m6_test)
    parts += before_after_handwritten(hq, m5_hw, m6_hw, judged)
    parts += [
        'Cost per question, separating caching (cache tokens repriced as input for "M6 uncached"):',
        "",
        table(
            ["Question set", "M5", "M6 uncached", "M6 (with caching)"],
            [
                [
                    "Numeric test sample (50)",
                    money(m5_cost50),
                    money(uncached("m6_test_sample:m6", ids50)),
                    money(m6_cost50),
                ],
                [
                    "Handwritten (30)",
                    money(m5_cost30),
                    money(uncached("m6_handwritten:m6", ids30)),
                    money(m6_cost30),
                ],
                ["Dev numeric (35, Phase C)", "$0.1377", "$0.1402", "$0.0619"],
                ["Dev explanatory (10, Phase C)", "$0.1930", "$0.2116", "$0.1451"],
            ],
        ),
        "",
    ]
    parts += dev_section(data)
    parts += ablation_section(tq, hq, m6_test, nv, nq, m6_hw, rerank, hybrid, judged)
    parts += failure_section(data)
    return parts


def dev_section(data: dict[str, Any]) -> list[str]:
    def agg(key: str) -> dict[str, float]:
        rows = data[key].values()
        mech = [r["mechanics"] for r in rows]
        return {
            "n": len(mech),
            "weighted": st.mean(m["weighted_tokens"] for m in mech),
            "guard": sum(m.get("guard_no_progress", 0) for m in mech),
            "empty": sum(m.get("empty_replies", 0) for m in mech),
            "guard_empty": sum(m.get("guard_empty_reply", 0) for m in mech),
            "skipped": sum(m.get("revision_skipped", 0) for m in mech),
            "revised": sum(m["analyst_rounds"] > 1 for m in mech),
        }

    rows = []
    for label, key in (
        ("M5, xd01-xd10", "m6_dev_explanatory_m5:system"),
        ("M6, xd01-xd10", "m6_dev_explanatory:m6"),
        ("M6, 35 dev numeric", "m6_dev_numeric:m6"),
    ):
        a = agg(key)
        rows.append(
            [
                label,
                str(a["n"]),
                f"{a['weighted'] / 1000:.1f}K",
                str(a["revised"]),
                str(a["skipped"]),
                str(a["guard"]),
                f"{a['empty']} / {a['guard_empty']}",
            ]
        )
    return [
        "### Dev validation (Phase C; mechanical only for explanatory prompts)",
        "",
        "Dev numeric (35 dev-pilot questions, paired with M5): accuracy 35/35 for both; full "
        "tables in docs/M6_PHASE_C.md. Explanatory dev prompts xd01-xd10 (no references, no "
        "judge): both systems answered 10/10.",
        "",
        table(
            [
                "Run",
                "n",
                "Mean price-weighted tokens",
                "Runs revised",
                "Revisions skipped (budget)",
                "Stall guard",
                "Empty replies / guarded",
            ],
            rows,
        ),
        "",
    ]


def ablation_section(tq, hq, m6, nv, nq, m6_hw, rerank, hybrid, judged) -> list[str]:
    ids50 = sorted(m6)
    s_m6 = numeric_rows(tq, m6)
    base = [s_m6[i]["score"].correct for i in ids50]
    rows = []
    for name, recs in (("M6 system", m6), ("−verifier", nv), ("−quant tools", nq)):
        s = numeric_rows(tq, recs)
        acc = [s[i]["score"].correct for i in ids50]
        mean, lo, hi = bootstrap_ci(acc)
        if recs is m6:
            delta = "–"
        else:
            d, dlo, dhi = paired_diff_ci(acc, base)
            _, _, p = mcnemar_exact(acc, base)
            delta = f"{100 * d:+.1f} pp [{100 * dlo:+.1f}, {100 * dhi:+.1f}], p = {p:.2f}"
        numeric, text, model_math = citation_cells([recs[i] for i in ids50])
        costs = [float(recs[i]["cost_usd"]) for i in ids50]
        correct = sum(acc)
        rows.append(
            [
                name,
                "numeric test sample",
                f"{pct(mean)} [{pct(lo)}, {pct(hi)}] n={len(acc)}",
                delta,
                numeric,
                text,
                model_math,
                money(st.mean(costs)),
                money(sum(costs) / correct) if correct else "–",
                latency([recs[i] for i in ids50]),
            ]
        )
    q = {x["id"]: x for x in hq}
    ids30 = sorted(m6_hw)
    base_hw = hw_scores(m6_hw, judged_scores(judged, "m6"), ids30)
    for name, sid, recs in (
        ("M6 system (vector)", "m6", m6_hw),
        ("+rerank (hybrid_rerank)", "m6-rerank", rerank),
        ("−rerank (hybrid)", "m6-hybrid", hybrid),
    ):
        scores = hw_scores(recs, judged_scores(judged, sid), ids30)
        mean, lo, hi = bootstrap_mean_ci(scores)
        if sid == "m6":
            delta = "–"
        else:
            d = mean_diff_ci([float(x) for x in scores], [float(x) for x in base_hw])
            _, _, p = sign_test(scores, base_hw)
            delta = f"{d[0]:+.2f} [{d[1]:+.2f}, {d[2]:+.2f}], sign p = {p:.2f}"
        numeric, _, model_math = citation_cells([recs[i] for i in ids30])
        costs = [float(recs[i]["cost_usd"]) for i in ids30]
        rows.append(
            [
                name,
                "handwritten 30",
                f"judge {mean:.2f} [{lo:.2f}, {hi:.2f}]; recall@5/10 "
                f"{recall(recs, q, 5):.2f}/{recall(recs, q, 10):.2f}; no answer "
                f"{sum(not answered(recs[i]) for i in ids30)}",
                delta,
                numeric,
                text_validity({i: recs[i] for i in ids30}, judged, sid),
                model_math,
                money(st.mean(costs)),
                "–",
                latency([recs[i] for i in ids30]),
            ]
        )
    hw = {}
    for sid, recs in (("m6", m6_hw), ("m6-rerank", rerank), ("m6-hybrid", hybrid)):
        scores = hw_scores(recs, judged_scores(judged, sid), ids30)
        p50 = percentile([recs[i]["latency_ms"] / 1000 for i in ids30], 0.5)
        hw[sid] = (st.mean(scores), recall(recs, q, 10), p50)
    retrieval_note = (
        f"On the handwritten 30, reranking raised system-level recall@10 from "
        f"{hw['m6'][1]:.2f} (vector) to {hw['m6-rerank'][1]:.2f} (hybrid_rerank; hybrid "
        f"{hw['m6-hybrid'][1]:.2f}), but the judge means are within noise (vector "
        f"{hw['m6'][0]:.2f}, hybrid_rerank {hw['m6-rerank'][0]:.2f}, hybrid "
        f"{hw['m6-hybrid'][0]:.2f}; paired CIs include 0), and reranking costs latency "
        f"(p50 {hw['m6'][2]:.0f}s vs {hw['m6-rerank'][2]:.0f}s; cross-encoder on CPU). Vector "
        "stays the default (D044)."
    )
    nv_cost = st.mean(float(nv[i]["cost_usd"]) for i in ids50)
    nq_cost = st.mean(float(nq[i]["cost_usd"]) for i in ids50)
    m6_cost = st.mean(float(m6[i]["cost_usd"]) for i in ids50)
    acc = {
        n: sum(numeric_rows(tq, r)[i]["score"].correct for i in ids50)
        for n, r in (("m6", m6), ("nv", nv), ("nq", nq))
    }
    return [
        "### Ablations (SPEC §13.5, D121)",
        "",
        "Each variant is the final M6 system with one flag changed, paired with it on the same "
        "questions. Numeric variants run on the frozen 50-question test sample; retrieval "
        "variants on the handwritten 30 (numeric questions never start a filings worker). "
        "Vector retrieval is the M6 default, so it is the vector-only arm.",
        "",
        table(
            [
                "Variant",
                "Questions",
                "Accuracy or judge [95% CI]",
                "Δ vs M6 [95% CI], paired p",
                "Citation validity, numeric",
                "Text claims supported",
                "Numeric claims without fact/computation citation",
                "$/question",
                "$/correct",
                "Latency p50/p95",
            ],
            rows,
        ),
        "",
        f"**−verifier and −quant matched the M6 system's accuracy on the 50 numeric questions** "
        f"(M6 {acc['m6']}/50, −verifier {acc['nv']}/50, −quant {acc['nq']}/50). Removing the "
        f"verifier saves {money(m6_cost - nv_cost)}/question "
        f"({pct((m6_cost - nv_cost) / m6_cost)} of M6's cost); removing the quant tools costs "
        f"{money(nq_cost - m6_cost)}/question more ({pct((nq_cost - m6_cost) / m6_cost)}), "
        "because the analyst writes about 65% more output tokens working the arithmetic in "
        "text and benefits less from caching (D125). With the system near 100% on numeric "
        "questions, n = 50 cannot detect small accuracy differences; per-template and n = 30 "
        "results are descriptive. Without quant tools, numeric claims computed by the model "
        "carry no computation citation, so Stage 1 cannot verify them (D056): see the column "
        "above.",
        "",
        retrieval_note,
        "",
    ]


def failure_section(data: dict[str, Any]) -> list[str]:
    from evals.failures import CATEGORIES, SPOT_CHECK_N, _rank

    columns = (
        ("M5 dev pilot (100)", "m5_dev_pilot:system"),
        ("M5 test subset (180)", "m5_test_subset:system"),
        ("M5 handwritten (30)", "m5_handwritten:system"),
        ("M6 dev numeric (35)", "m6_dev_numeric:m6"),
        ("M5 / M6 xd01-10", None),
        ("M6 test sample (50)", "m6_test_sample:m6"),
        ("M6 handwritten (30)", "m6_handwritten:m6"),
    )

    def count(key: str, category: str) -> int:
        return sum(category in r["categories"] for r in data[key].values())

    rows = []
    for category in CATEGORIES:
        cells = []
        for _, key in columns:
            if key is None:
                cells.append(
                    f"{count('m6_dev_explanatory_m5:system', category)} / "
                    f"{count('m6_dev_explanatory:m6', category)}"
                )
            else:
                cells.append(str(count(key, category)))
        rows.append([category, *cells])
    examples = []
    for category in CATEGORIES:
        members = [
            (key, qid, r["categories"][category])
            for key in ("m6_test_sample:m6", "m6_handwritten:m6", "m6_dev_numeric:m6")
            + tuple(k for _, k in columns if k and k.startswith("m5"))
            for qid, r in data[key].items()
            if category in r["categories"]
        ]
        if not members:
            continue
        ranked = sorted(members, key=lambda m: _rank(category, m[1]))
        shown = "; ".join(
            f"`{qid[:12]}…` ({key.split(':')[0]}): {evidence[:110]}"
            for key, qid, evidence in ranked[:2]
        )
        spot = ", ".join(
            f"`{qid[:12]}…` ({key.split(':')[0]})" for key, qid, _ in ranked[:SPOT_CHECK_N]
        )
        examples.append(f"- **{category}** — {shown}. Spot-check: {spot}.")
    return [
        "### Failure analysis (SPEC §13.6, D112)",
        "",
        "Deterministic rules over each run's record and trace (`evals/failures.py`), no LLM; a "
        "run can fall into several categories and counts are runs. SPEC's wrong-period, "
        "wrong-concept and arithmetic categories had no system case in M5 or M6. The M5 dev "
        'pilot answered every question correctly, so SPEC\'s "≥ 25 failures from dev" is met as '
        "failure events (133 in 74 of 100 dev runs, D111). Guard events in M6 columns are the "
        "fixes acting, not new failures. Disney segment operating income (3 test questions) is "
        'a gold-definition item, not a system failure (D119). "Near budget" counts raw '
        "tokens: M6 runs are limited by the price-weighted budget (D113), so an M6 run above "
        "150K raw tokens is not necessarily near its limit.",
        "",
        table(["Category", *[c for c, _ in columns]], rows),
        "",
        "Two examples per category and a seeded spot-check list of up to 5 runs, in one seeded "
        "order across the M5 and M6 runs (seed 20261112):",
        "",
        *examples,
        "",
    ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="M6 report data (D111-D125)")
    parser.add_argument("command", choices=["collect"])
    parser.parse_args(argv)
    data = collect()
    print({k: len(v) for k, v in data.items()})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

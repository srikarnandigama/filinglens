"""Orchestrator over the real MCP servers with scripted roles (no LLM, no hardcoded SEC values).

Scripted roles read every number they use from the tool results and evidence they receive at
runtime, so these tests exercise period resolution, locks, the ledger and verification without
embedding financial facts.
"""

import os
from decimal import Decimal

import pytest

from filinglens.agents.mcp_client import McpHub
from filinglens.agents.orchestrator import RunConfig, run_question
from filinglens.agents.settings import RuntimeSettings
from filinglens.agents.tracing import MemoryTraceStore
from tests.agent_fakes import (
    ScriptedProvider,
    calls,
    envelopes,
    evidence,
    fake_prices,
    final,
    proactor_run,
    tool_results,
)

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.environ.get("FILINGLENS_TEST_DB") != "1", reason="Set FILINGLENS_TEST_DB=1"
    ),
]
ORDER = {"Q1": 0, "Q2": 1, "Q3": 2, "Q4": 3, "FY": 4}


def settings() -> RuntimeSettings:
    return RuntimeSettings(
        planner_model="fake-large", worker_model="fake-small", verifier_model="fake-large"
    )


def views(messages):
    return {
        body["data"]["ticker"]: body["data"]
        for _, body in tool_results(messages, "list_available_metrics")
    }


def metric(view, name):
    return next(m for m in view["metrics"] if m["metric"] == name)


def periods(view, name):
    return {(int(y), p) for y, ps in metric(view, name)["available"].items() for p in ps}


def parse_period(label):  # "FY2026 FY" -> (2026, "FY")
    year, period = label.split()
    return int(year.removeprefix("FY")), period


def lookup(sid, ticker, name, pairs):
    return {
        "id": sid,
        "type": "metric_lookup",
        "description": f"{ticker} {name}",
        "params": {
            "kind": "metric_lookup",
            "ticker": ticker,
            "metric": name,
            "periods": [{"fiscal_year": y, "fiscal_period": p} for y, p in pairs],
        },
    }


def search(sid, ticker, year, period, items, query):
    return {
        "id": sid,
        "type": "filing_search",
        "description": query,
        "params": {
            "kind": "filing_search",
            "ticker": ticker,
            "fiscal_year": year,
            "fiscal_period": period,
            "items": items,
            "query": query,
            "k": 5,
        },
    }


def computation(sid, operation, inputs, note):
    return {
        "id": sid,
        "type": "computation",
        "description": note,
        "depends_on": inputs,
        "params": {
            "kind": "computation",
            "operation": operation,
            "inputs": [{"subtask_id": i} for i in inputs],
            "note": note,
        },
    }


def planner(tickers, build, question_type="lookup"):
    def handle(step, messages, model):
        if step == 0:
            return calls(*[("list_available_metrics", {"ticker": t}) for t in tickers])
        subtasks, resolutions = build(views(messages))
        return final(
            {
                "question_type": question_type,
                "companies": tickers,
                "period_resolutions": resolutions,
                "answerability": "answerable",
                "subtasks": subtasks,
            }
        )

    return handle


def filings_worker(step, messages, model):
    subtask = next(body for tag, _, body in envelopes(messages[:1]) if tag == "evidence")
    params = {k: v for k, v in subtask["params"].items() if k != "kind"}
    if step == 0:
        return calls(("search_filings", params))
    hits = [h for _, body in tool_results(messages, "search_filings") for h in body["data"]["hits"]]
    if step == 1 and hits:
        return calls(("get_passage", {"chunk_id": hits[0]["chunk_id"]}))
    passages = [body["data"] for _, body in tool_results(messages, "get_passage")]
    return final(
        {
            "subtask_id": subtask["id"],
            "found": bool(passages),
            "passages": [
                {
                    "chunk_id": p["chunk_id"],
                    "relevance": "top filtered hit",
                    "quotes": [p["text"][:120]],
                }
                for p in passages
            ],
            "notes": None if passages else "no hits",
        }
    )


def verifier_all_supported(step, messages, model):
    draft = next(body for tag, _, body in envelopes(messages[:1]) if tag == "evidence")
    return final(
        {
            "verdicts": [
                {
                    "claim_id": c["id"],
                    "verdict": "supported",
                    "reason": "matches",
                    "citations_checked": [x["ref"] for x in c["citations"]],
                }
                for c in draft["claims"]
            ],
            "summary_verdict": {"claim_id": "summary", "verdict": "supported", "reason": "ok"},
        }
    )


def pack(messages):
    return next(e for e in evidence(messages) if isinstance(e, dict) and "facts" in e)


def records(messages):
    return [r for group in pack(messages)["facts"] for r in group["records"]]


def computed(messages, tool):
    return [(a["computation_id"], body["data"]) for a, body in tool_results(messages, tool)]


def fact_claim(cid, record, **extra):
    return {
        "id": cid,
        "kind": "numeric",
        "text": f"{record['ticker']} {record['metric']} FY{record['fiscal_year']} "
        f"{record['fiscal_period']} was {record['value']} USD.",
        "value": record["value"],
        "unit": record["unit"],
        "value_basis": "fact",
        "ticker": record["ticker"],
        "period": {"fiscal_year": record["fiscal_year"], "fiscal_period": record["fiscal_period"]},
        "citations": [{"kind": "fact", "ref": record["fact_id"]}],
        **extra,
    }


def pct_claim(cid, comp_id, value, label, unit="percent"):
    return {
        "id": cid,
        "kind": "numeric",
        "text": f"{label}: {value}.",
        "value": value,
        "unit": unit,
        "value_basis": "computation",
        "citations": [{"kind": "computation", "ref": comp_id}],
    }


def single_value_analyst(step, messages, model):
    (record,) = records(messages)
    return final(
        {
            "status": "answered",
            "summary": f"The value was {record['value']} USD.",
            "claims": [fact_claim("c1", record)],
            "final_value": record["value"],
            "final_unit": "USD",
            "final_claim_id": "c1",
            "caveats": ["Derived Q4 value."] if record["derived"] else [],
        }
    )


def run(question, handlers, tmp_path, cfg=None):
    async def exercise():
        provider = ScriptedProvider({"verifier": verifier_all_supported, **handlers})
        cfg_ = cfg or RunConfig(retrieval_mode="keyword")
        async with McpHub(
            settings(), retrieval_mode=cfg_.retrieval_mode, log_dir=tmp_path / "logs"
        ) as hub:
            result = await run_question(
                question,
                cfg_,
                settings(),
                providers={"anthropic": provider},
                store=MemoryTraceStore(),
                prices=fake_prices("fake-large", "fake-small"),
                hub=hub,
            )
        return result, provider

    result, provider = proactor_run(exercise())
    assert result.status == "done", result.error
    return result, provider


def assert_verified(result):
    assert result.answer.claims and all(c.citations for c in result.answer.claims)
    assert result.verification[-1]["failing"] == {}


def test_lookup_derived_and_llm_data_worker(tmp_path):
    def aapl(v):
        assert (2025, "Q2") in periods(v["AAPL"], "revenue")
        return [lookup("s1", "AAPL", "revenue", [(2025, "Q2")])], [
            {
                "phrase": "fiscal Q2 2025",
                "ticker": "AAPL",
                "resolved": [{"fiscal_year": 2025, "fiscal_period": "Q2"}],
                "basis": "explicit",
            }
        ]

    result, provider = run(
        "What was Apple's total revenue in fiscal Q2 2025?",
        {"planner": planner(["AAPL"], aapl), "analyst": single_value_analyst},
        tmp_path,
    )
    assert_verified(result)
    fact = result.ledger.facts[result.answer.claims[0].citations[0].ref]
    assert (fact.ticker, fact.fiscal_year, fact.fiscal_period) == ("AAPL", 2025, "Q2")
    assert result.answer.final_value == fact.value
    assert "data" not in {r["role"] for r in provider.requests}  # direct data worker

    def msft(v):
        return [lookup("s1", "MSFT", "operating_income", [(2025, "Q4")])], []

    result, _ = run(
        "What was Microsoft's Q4 FY2025 operating income?",
        {"planner": planner(["MSFT"], msft), "analyst": single_value_analyst},
        tmp_path,
    )
    assert_verified(result)
    fact = result.ledger.facts[result.answer.claims[0].citations[0].ref]
    assert fact.derived is True and result.answer.caveats == ["Derived Q4 value."]

    def data_worker(step, messages, model):
        subtask = next(body for tag, _, body in envelopes(messages[:1]) if tag == "evidence")
        if step == 0:
            args = {k: v for k, v in subtask["params"].items() if k != "kind"}
            return calls(("get_financial_metric", args))
        ((_, body),) = tool_results(messages, "get_financial_metric")
        return final(
            {
                "subtask_id": subtask["id"],
                "fact_ids": [f["fact_id"] for f in body["data"]["facts"]],
                "notes": None,
            }
        )

    result, provider = run(
        "What was Apple's total revenue in fiscal Q2 2025?",
        {"planner": planner(["AAPL"], aapl), "analyst": single_value_analyst, "data": data_worker},
        tmp_path,
        RunConfig(retrieval_mode="keyword", data_worker="llm"),
    )
    assert_verified(result)
    assert [r["tools"] for r in provider.requests if r["role"] == "data"][0] == [
        "get_financial_metric"
    ]


def test_trend_last_eight_quarters_from_discovery(tmp_path):
    def nvda(v):
        both = periods(v["NVDA"], "revenue") & periods(v["NVDA"], "gross_profit")
        quarters = sorted((p for p in both if p[1] != "FY"), key=lambda p: (p[0], ORDER[p[1]]))[-8:]
        common = v["NVDA"]["latest_common_quarter"]
        # The snapshot-bounded latest quarter, not today's calendar quarter.
        assert quarters[-1] == (common["fiscal_year"], common["fiscal_period"])
        return [
            lookup("s1", "NVDA", "revenue", quarters),
            lookup("s2", "NVDA", "gross_profit", quarters),
            computation("s3", "margin", ["s1", "s2"], "gross_profit / revenue per quarter"),
        ], [
            {
                "phrase": "last 8 quarters",
                "ticker": "NVDA",
                "resolved": [{"fiscal_year": y, "fiscal_period": p} for y, p in quarters],
                "basis": "latest_common_quarter and available periods",
            }
        ]

    def analyst(step, messages, model):
        recs = records(messages)
        by = {(r["metric"], r["fiscal_year"], r["fiscal_period"]): r for r in recs}
        keys = sorted(
            {(r["fiscal_year"], r["fiscal_period"]) for r in recs},
            key=lambda p: (p[0], ORDER[p[1]]),
        )
        if step == 0:
            return calls(
                *[
                    (
                        "margin",
                        {
                            "numerator": by[("gross_profit", *k)]["value"],
                            "denominator": by[("revenue", *k)]["value"],
                        },
                    )
                    for k in keys
                ]
            )
        claims = [
            pct_claim(f"c{i + 1}", cid, data["value_pct"], f"Gross margin FY{k[0]} {k[1]}")
            for i, ((cid, data), k) in enumerate(
                zip(computed(messages, "margin"), keys, strict=True)
            )
        ]
        return final(
            {
                "status": "answered",
                "summary": "Quarterly gross margins are listed.",
                "claims": claims,
            }
        )

    result, _ = run(
        "How did Nvidia's gross margin change over the last 8 quarters?",
        {"planner": planner(["NVDA"], nvda, "trend"), "analyst": analyst},
        tmp_path,
    )
    assert_verified(result)
    assert len(result.answer.claims) == 8 and len(result.ledger.computations) == 8


def test_comparison_with_different_fiscal_year_ends(tmp_path):
    def build(v):
        subtasks, resolutions = [], []
        for i, t in enumerate(["WMT", "COST"]):
            year = parse_period(metric(v[t], "revenue")["latest_annual"])
            assert year == parse_period(metric(v[t], "net_income")["latest_annual"])
            subtasks += [
                lookup(f"s{2 * i + 1}", t, "revenue", [year]),
                lookup(f"s{2 * i + 2}", t, "net_income", [year]),
            ]
            resolutions.append(
                {
                    "phrase": "most recent fiscal year",
                    "ticker": t,
                    "resolved": [{"fiscal_year": year[0], "fiscal_period": "FY"}],
                    "basis": "latest_annual",
                }
            )
        subtasks.append(computation("s5", "margin", ["s1", "s2", "s3", "s4"], "net margins"))
        return subtasks, resolutions

    def analyst(step, messages, model):
        by = {(r["ticker"], r["metric"]): r["value"] for r in records(messages)}
        if step == 0:
            return calls(
                *[
                    (
                        "margin",
                        {"numerator": by[(t, "net_income")], "denominator": by[(t, "revenue")]},
                    )
                    for t in ("WMT", "COST")
                ]
            )
        margins = computed(messages, "margin")
        if step == 1:
            return calls(
                (
                    "evaluate",
                    {"expression": f"{margins[0][1]['value_pct']} - {margins[1][1]['value_pct']}"},
                )
            )
        ((diff_id, diff),) = computed(messages, "evaluate")
        claims = [
            pct_claim("c1", margins[0][0], margins[0][1]["value_pct"], "WMT net margin"),
            pct_claim("c2", margins[1][0], margins[1][1]["value_pct"], "COST net margin"),
            pct_claim("c3", diff_id, diff["value"], "Difference", "percentage_points"),
        ]
        return final(
            {
                "status": "answered",
                "summary": "Net margins are compared below.",
                "claims": claims,
                "final_value": diff["value"],
                "final_unit": "percentage_points",
                "final_claim_id": "c3",
                "caveats": ["The companies' fiscal years end on different dates."],
            }
        )

    result, _ = run(
        "Compare Walmart's and Costco's net margins for their most recent fiscal year.",
        {"planner": planner(["WMT", "COST"], build, "comparison"), "analyst": analyst},
        tmp_path,
    )
    assert_verified(result)
    assert result.answer.final_unit == "percentage_points"


def test_explanatory_and_diff_use_filtered_filings(tmp_path):
    def tsla(v):
        latest = parse_period(metric(v["TSLA"], "operating_income")["latest_annual"])
        return [
            lookup("s1", "TSLA", "operating_income", [(latest[0] - 1, "FY"), latest]),
            search("s2", "TSLA", latest[0], "FY", ["7"], "operating income decreased"),
        ], [
            {
                "phrase": "last year",
                "ticker": "TSLA",
                "resolved": [{"fiscal_year": latest[0], "fiscal_period": "FY"}],
                "basis": "latest_annual",
            }
        ]

    def analyst(step, messages, model):
        old, new = records(messages)
        if step == 0:
            return calls(("growth_rate", {"old": old["value"], "new": new["value"]}))
        ((cid, growth),) = computed(messages, "growth_rate")
        passage = pack(messages)["passages"][0]["passages"][0]
        assert passage["verified_quotes"]
        return final(
            {
                "status": "answered",
                "summary": "Management's explanation is quoted.",
                "claims": [
                    pct_claim("c1", cid, growth["value_pct"], "Operating income change"),
                    {
                        "id": "c2",
                        "kind": "textual",
                        "text": "Tesla discussed operating income in its MD&A.",
                        "citations": [{"kind": "chunk", "ref": passage["chunk_id"]}],
                    },
                ],
            }
        )

    result, provider = run(
        "According to management, why did Tesla's operating income decline last year?",
        {
            "planner": planner(["TSLA"], tsla, "explanatory"),
            "analyst": analyst,
            "filings": filings_worker,
        },
        tmp_path,
    )
    assert_verified(result)
    chunk = result.ledger.passages[result.answer.claims[1].citations[0].ref]
    assert (chunk.ticker, chunk.form, chunk.item) == ("TSLA", "10-K", "7")
    assert [r["tools"] for r in provider.requests if r["role"] == "filings"][0] == [
        "search_filings",
        "get_passage",
    ]

    def meta(v):
        latest = parse_period(metric(v["META"], "revenue")["latest_annual"])[0]
        return [
            search("s1", "META", latest, "FY", ["1A"], "new risk factors regulation"),
            search("s2", "META", latest - 1, "FY", ["1A"], "new risk factors regulation"),
        ], []

    def diff_analyst(step, messages, model):
        groups = pack(messages)["passages"]
        claims = [
            {
                "id": f"c{i + 1}",
                "kind": "textual",
                "text": f"The FY{g['filing']['fiscal_year']} 10-K discusses regulatory risk.",
                "citations": [{"kind": "chunk", "ref": g["passages"][0]["chunk_id"]}],
            }
            for i, g in enumerate(groups)
            if g["passages"]
        ]
        return final(
            {
                "status": "partially_answered",
                "summary": "Search-based comparison.",
                "claims": claims,
                "caveats": ["Search-based comparison is not exhaustive."],
            }
        )

    result, _ = run(
        "What new risk factors did Meta add in its latest 10-K vs. the prior one?",
        {
            "planner": planner(["META"], meta, "diff"),
            "analyst": diff_analyst,
            "filings": filings_worker,
        },
        tmp_path,
    )
    assert_verified(result)
    years = {result.ledger.passages[c.citations[0].ref].fiscal_year for c in result.answer.claims}
    assert len(years) == 2


def aapl_plan(v):
    return [lookup("s1", "AAPL", "revenue", [(2025, "Q2"), (2025, "Q1")])], []


def two_claims(records_, bump_second):
    first, second = records_
    bad = dict(second)
    if bump_second:
        bad["value"] = str(Decimal(second["value"]) + 1)
    return [fact_claim("c1", first), fact_claim("c2", bad)]


def test_revision_fixes_or_drops_claims_and_verifier_off(tmp_path):
    rounds = []

    def fixing(step, messages, model):
        rounds.append(1)
        claims = two_claims(records(messages), bump_second=len(rounds) == 1)
        return final({"status": "answered", "summary": "Two quarters.", "claims": claims})

    result, provider = run(
        "Apple revenue in fiscal Q1 and Q2 2025?",
        {"planner": planner(["AAPL"], aapl_plan), "analyst": fixing},
        tmp_path,
    )
    assert len(result.verification) == 2 and result.verification[0]["failing"].keys() == {"c2"}
    assert_verified(result)
    assert len(result.answer.claims) == 2

    def stubborn(step, messages, model):
        claims = two_claims(records(messages), bump_second=True)
        return final(
            {
                "status": "answered",
                "summary": "Two quarters.",
                "claims": claims,
                "final_value": claims[1]["value"],
                "final_unit": "USD",
                "final_claim_id": "c2",
            }
        )

    result, provider = run(
        "Apple revenue in fiscal Q1 and Q2 2025?",
        {"planner": planner(["AAPL"], aapl_plan), "analyst": stubborn},
        tmp_path,
    )
    answer = result.answer
    assert [c.id for c in answer.claims] == ["c1"] and answer.status == "partially_answered"
    assert answer.final_value is None and answer.caveats[0].startswith("Removed unsupported claim")
    assert sum(r["role"] == "analyst" and r["step"] == 0 for r in provider.requests) == 3

    result, provider = run(
        "Apple revenue in fiscal Q1 and Q2 2025?",
        {"planner": planner(["AAPL"], aapl_plan), "analyst": stubborn},
        tmp_path,
        RunConfig(retrieval_mode="keyword", verifier=False),
    )
    assert len(result.answer.claims) == 2  # verifier off: recorded, not applied
    assert result.verification[0]["applied"] is False and "c2" in result.verification[0]["failing"]
    assert "verifier" not in {r["role"] for r in provider.requests}


def test_no_quant_mode_and_not_available_plan(tmp_path):
    def margin_plan(v):
        return [
            lookup("s1", "AAPL", "revenue", [(2025, "Q2")]),
            lookup("s2", "AAPL", "gross_profit", [(2025, "Q2")]),
        ], []

    def model_math(step, messages, model):
        by = {r["metric"]: r for r in records(messages)}
        value = str(Decimal(by["gross_profit"]["value"]) * 100 / Decimal(by["revenue"]["value"]))
        value = value if "E" not in value else format(Decimal(value), "f")
        return final(
            {
                "status": "answered",
                "summary": "Margin computed without tools.",
                "claims": [
                    {
                        "id": "c1",
                        "kind": "numeric",
                        "text": "Gross margin.",
                        "value": value,
                        "unit": "percent",
                        "value_basis": "model_arithmetic",
                        "citations": [
                            {"kind": "fact", "ref": by["revenue"]["fact_id"]},
                            {"kind": "fact", "ref": by["gross_profit"]["fact_id"]},
                        ],
                    }
                ],
            }
        )

    result, provider = run(
        "What was Apple's gross margin in fiscal Q2 2025?",
        {"planner": planner(["AAPL"], margin_plan), "analyst": model_math},
        tmp_path,
        RunConfig(retrieval_mode="keyword", use_quant_tools=False),
    )
    assert [r["tools"] for r in provider.requests if r["role"] == "analyst"] == [[]]
    checks = result.verification[0]["deterministic"]
    assert checks["c1"]["verdict"] == "unverifiable_model_arithmetic"
    assert result.verification[-1]["failing"] == {}

    def unavailable(step, messages, model):
        if step == 0:
            return calls(("list_available_metrics", {"ticker": "AAPL"}))
        return final(
            {
                "question_type": "lookup",
                "companies": ["AAPL"],
                "answerability": "not_available",
                "answerability_reason": "FY2035 is outside the snapshot.",
                "subtasks": [],
            }
        )

    result, provider = run(
        "What was Apple's revenue in fiscal 2035?", {"planner": unavailable}, tmp_path
    )
    assert result.answer.status == "not_available" and result.answer.claims == []
    assert {r["role"] for r in provider.requests} == {"planner"}

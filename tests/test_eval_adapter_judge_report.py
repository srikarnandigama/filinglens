"""System adapter, judge parsing/calibration and report rendering (D091-D094); offline test data."""

from types import SimpleNamespace

import pytest

from evals.judge import agreement, blind_export, calibration_sample, parse_claim, parse_rubric
from evals.report import headline_row, paired, render
from evals.scorers import score
from evals.system_adapter import (
    citation_summary,
    comparison_choice,
    prediction_of,
    recall_at,
    retrieval_from_trace,
    string_supported,
)
from filinglens.agents.ledger import FactRecord, Ledger, PassageRecord
from filinglens.agents.schemas import Answer

CHUNK = "chk_" + "b" * 64
PASSAGE = "Net sales increased due to higher demand for services across all geographic segments."


def ledger() -> Ledger:
    led = Ledger()
    for fid, ticker, value in (("1", "AAA", "400"), ("2", "BBB", "300")):
        led.facts[fid] = FactRecord(
            fact_id=fid,
            ticker=ticker,
            metric="revenue",
            fiscal_year=2025,
            fiscal_period="FY",
            value=value,
            unit="USD",
            status="available",
        )
    led.passages[CHUNK] = PassageRecord(
        chunk_id=CHUNK,
        ticker="AAA",
        form="10-K",
        fiscal_year=2025,
        fiscal_period="FY",
        item="7",
        full_text=PASSAGE,
    )
    return led


def claim(cid, value=None, unit=None, ticker=None, ref="1", kind="numeric", text="x"):
    out = {"id": cid, "kind": kind, "text": text, "ticker": ticker}
    out["citations"] = [{"kind": "chunk" if kind == "textual" else "fact", "ref": ref}]
    if kind == "numeric":
        out |= {"value": value, "unit": unit, "value_basis": "fact"}
    return out


def answer(claims, status="answered", final=None, unit=None):
    return Answer.model_validate(
        {
            "status": status,
            "summary": "s",
            "claims": claims,
            "final_value": final,
            "final_unit": unit,
            "final_claim_id": claims[-1]["id"] if final is not None else None,
        }
    )


CMP_Q = {"template": "comparison", "companies": ["AAA", "BBB"]}
LOOKUP_Q = {"template": "lookup", "companies": ["AAA"]}


def test_prediction_maps_status_value_and_comparison_choice():
    led = ledger()
    a = answer(
        [
            claim("c1", "12.5", "percent", ticker="AAA"),
            claim("c2", "10.1", "percent", ref="2"),  # ticker from the cited fact
            claim("c3", "2.4", "percentage_points", ticker="AAA"),
        ],
        final="2.4",
        unit="percentage_points",
    )
    assert comparison_choice(a, led, ["AAA", "BBB"]) == "AAA"
    p = prediction_of(a, CMP_Q, led)
    assert p["parse_ok"] and p["choice"] == "AAA" and p["value"] == "2.4"
    one_sided = answer([claim("c1", "12.5", "percent", ticker="AAA")], final="12.5", unit="percent")
    assert not prediction_of(one_sided, CMP_Q, led)["parse_ok"]  # D091: unresolvable choice
    na = answer([], status="not_applicable")
    assert prediction_of(na, LOOKUP_Q, led)["status"] == "not_applicable"
    assert not prediction_of(None, LOOKUP_Q, led)["parse_ok"]
    no_final = answer([claim("c1", "400", "USD", ticker="AAA")])
    assert prediction_of(no_final, LOOKUP_Q, led)["parse_error"] == "Answer has no final_value"


def test_string_support_needs_an_eight_word_verbatim_run():
    assert string_supported("Net sales increased due to higher demand for services.", [PASSAGE])
    assert not string_supported("Sales rose on demand.", [PASSAGE])  # under 8 words
    assert not string_supported("Net sales decreased due to lower demand for products.", [PASSAGE])


def test_citation_summary_checks_numeric_offline_and_defers_text_to_the_judge():
    led = ledger()
    a = answer(
        [
            claim("c1", "400", "USD", ticker="AAA"),
            claim("c2", "999", "USD", ticker="AAA"),
            claim("c3", kind="textual", ref=CHUNK, text=PASSAGE),
            claim("c4", kind="textual", ref=CHUNK, text="Margins expanded on a favorable mix."),
        ]
    )
    s = citation_summary(a, led)
    assert (s["numeric_total"], s["numeric_valid"]) == (2, 1)
    assert (s["text_total"], s["text_string_supported"]) == (2, 1)
    assert [p["claim_id"] for p in s["text_pending_judge"]] == ["c4"]


def test_retrieval_from_trace_and_recall_at_k():
    def ev(tool, instance, data):
        payload = {"tool": tool, "instance": instance, "structured": {"data": data}}
        return SimpleNamespace(event_type="tool_result", payload=payload)

    events = [
        ev("search_filings", "w1", {"hits": [{"chunk_id": "a"}, {"chunk_id": "b"}]}),
        ev("search_filings", "w1", {"hits": [{"chunk_id": "z"}]}),  # not a first search
        ev("search_filings", "w2", {"hits": [{"chunk_id": "c"}]}),
        ev("get_passage", "w1", {"chunk_id": "d"}),
        SimpleNamespace(event_type="llm_call", payload={}),
    ]
    r = retrieval_from_trace(events)
    assert r["first_search"] == {"w1": ["a", "b"], "w2": ["c"]}
    assert r["seen"] == ["a", "b", "z", "c", "d"]
    assert recall_at(["a", "c", "z"], r, 1) == 1.0  # a and c: 2 of min(1 x 2 workers, 3)
    assert recall_at(["a", "c", "z"], r, 5) == pytest.approx(2 / 3)  # z was not a first search
    assert recall_at(["b"], r, 1) == 0.0


def test_judge_parsing_calibration_and_agreement(tmp_path):
    assert parse_rubric('notes {"score": 4, "missing_points": ["x"]}')["score"] == 4
    assert not parse_rubric('{"score": 7}')["parse_ok"]
    assert parse_claim('{"supported": false, "reason": "no"}')["supported"] is False
    assert not parse_claim('{"supported": "yes"}')["parse_ok"]
    judged = [
        {"key": f"k{i}", "score": i % 5 + 1, "question": "q", "reference": "r", "answer": "a"}
        for i in range(40)
    ]
    sample = calibration_sample(judged, n=20)
    assert len(sample) == 20 and {r["score"] for r in sample} == {1, 2, 3, 4, 5}
    assert sample == calibration_sample(judged, n=20)  # seeded
    path = blind_export(sample, tmp_path / "blind.jsonl")
    assert '"score"' not in path.read_text(encoding="utf-8")  # judge scores stay hidden
    same = agreement({"a": 1, "b": 3, "c": 5}, {"a": 1, "b": 3, "c": 5, "d": 2})
    assert same["n"] == 3 and same["exact"] == 1.0 and not same["indicative_only"]
    off = agreement({"a": 1, "b": 5, "c": 3}, {"a": 5, "b": 1, "c": 3})
    assert off["indicative_only"] and off["within_1"] == pytest.approx(1 / 3)


def _rows(correct: list[bool], sample=False):
    out = {}
    for i, ok in enumerate(correct):
        q = {
            "id": f"q{i}",
            "template": "lookup",
            "gold_value": "100",
            "gold_unit": "USD",
            "gold_choice": None,
            "tolerance": {"kind": "relative", "value": "0.005"},
            "sample_100": sample,
            "fairness": {
                "cutoff_bucket": {"claude-sonnet-5-5": "after" if i % 5 == 0 else "before"},
                "restated": False,
                "derived_q4": False,
            },
        }
        pred = {"value": "100" if ok else "50", "unit": "USD", "status": "answered"}
        pred |= {"choice": None, "parse_ok": True}
        rec = {"question_id": q["id"], "status": "done", "cost_usd": "0.01", "latency_ms": 1000}
        out[q["id"]] = {"question": q, "record": rec, "score": score(q, pred)}
    return out


def test_report_headline_paired_and_render_on_synthetic_records(monkeypatch):
    system = _rows([True] * 160 + [False] * 40)
    b0 = _rows([True] * 120 + [False] * 80)
    row = headline_row("system", system)
    assert row[1].startswith("80.0% [") and row[2] == "80.0%" and row[-3] == "$0.0100"
    p = paired(system, {"b0": b0})
    assert p[0][:4] == ["b0", "200", "40", "0"] and float(p[0][5]) < 0.001
    monkeypatch.setattr("evals.report.retrieval_table", lambda: "(retrieval)")
    text = render({"test": {"system": system, "b0": b0}})
    assert "## Headline (test split)" in text and "| b0 | 60.0% [" in text
    assert "McNemar" in text and "_M6._" in text

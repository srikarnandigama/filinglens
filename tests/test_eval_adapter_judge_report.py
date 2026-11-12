"""System adapter, judge parsing/calibration and report rendering (D091-D094); offline test data."""

import asyncio
import json
from decimal import Decimal
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
    sampled = {f"s{k}": v for k, v in _rows([True] * 3 + [False], sample=True).items()}
    text = render(
        {
            "test": {
                "system": system | sampled,
                "b0": b0 | sampled,
                "b1-sonnet": sampled,
                "b2-sonnet": sampled,
            }
        }
    )
    head = text.split("## Headline")[1].split("## Larger")[0]
    order = [line.split(" | ")[0] for line in head.splitlines() if line.startswith("| ")]
    assert order[1:] == ["| system", "| b2-sonnet", "| b1-sonnet", "| b0"]  # equal access first
    assert "| b2-sonnet | gold filings' statements in context | 75.0% [" in head
    larger = text.split("## Larger")[1].split("## Paired")[0]
    assert "| b0 | none (closed book) | 60.3% [" in larger and "b1-sonnet" not in larger
    assert "not measure extraction" in text and "no discrepancies" in text  # D104, stated plainly
    assert "McNemar" in text and "_M6._" in text


# ---------------------------------------------------------------- judge runner (D107)


def _judge_inputs():
    questions = [
        {"id": "hq_1", "question": "Why?", "reference_answer": "Because A and B."},
        {"id": "hq_2", "question": "How?", "reference_answer": "By C."},
    ]
    pending = [
        {"claim_id": "c1", "text": "Revenue rose on A.", "chunk_ids": ["chk_1"]},
        {"claim_id": "c2", "text": "Unreadable.", "chunk_ids": ["chk_missing"]},
    ]
    records = {
        "system": [
            {
                "question_id": "hq_1",
                "prediction": {"text": "A and B."},
                "citations": {"text_pending_judge": pending},
            },
            {"question_id": "hq_2", "status": "error", "prediction": None},  # token budget, D108
        ],
        "b0-sonnet": [{"question_id": "hq_2", "prediction": {"text": "Maybe C."}}],
        "b0-opus": [{"question_id": "hq_1", "prediction": {"text": "not judged (cut 2)"}}],
    }
    return questions, records, {"chk_1": "Revenue rose because of A."}


def test_judge_items_cover_judged_systems_and_claims_with_passages():
    from evals import judge

    items = judge.judge_items(*_judge_inputs(), model="opus")
    kinds = [(i["kind"], i["system_id"], i["question_id"]) for i in items]
    assert kinds == [
        ("rubric", "system", "hq_1"),
        ("rubric", "b0-sonnet", "hq_2"),
        ("claim", "system", "hq_1"),
    ]  # no B0 Opus; the claim without a passage is not sent
    assert "Revenue rose because of A." in items[2]["params"]["messages"][0]["content"]
    assert items[0]["params"]["model"] == "opus" and len({i["key"] for i in items}) == 3


def test_judge_runner_batches_parses_caches_and_caps(tmp_path):
    from types import SimpleNamespace

    from evals import judge
    from filinglens.llm.pricing import ModelPrice
    from tests.test_eval_runner import FakeMessages, message

    items = judge.judge_items(*_judge_inputs(), model="opus")
    price = ModelPrice(input_per_mtok=Decimal("4"), output_per_mtok=Decimal("20"))
    replies = [
        message(text='ok {"score": 4, "missing_points": ["B"], "errors": []}'),
        message(text='{"score": 2, "missing_points": [], "errors": ["x"]}'),
        message(text='{"supported": true, "reason": "stated"}'),
    ]
    fake = FakeMessages(replies)
    kwargs = dict(
        client=SimpleNamespace(messages=fake),
        model_price=price,
        batch_multiplier=Decimal("0.5"),
        model="opus",
        cache_dir=tmp_path,
    )
    out = asyncio.run(judge.run_judges(items, **kwargs))
    assert len(fake.batches.submitted) == 1 and out["summary"]["judged"] == 3
    by_kind = {(r["kind"], r["system_id"]): r for r in out["records"]}
    assert {r["result"].get("score") for r in out["records"] if r["kind"] == "rubric"} == {2, 4}
    assert by_kind[("claim", "system")]["result"]["supported"] is True
    assert Decimal(out["summary"]["spent_usd"]) > 0
    again = asyncio.run(judge.run_judges(items, **kwargs))  # cached: no new batch, no spend
    assert len(fake.batches.submitted) == 1 and again["summary"]["spent_usd"] == "0"
    assert len(judge.load_judged("opus", tmp_path)) == 3
    fake.responses.append(message(text='{"score": 3, "missing_points": [], "errors": []}'))
    tight = kwargs | {"cache_dir": tmp_path / "new", "cap": Decimal("0.03")}
    capped = asyncio.run(judge.run_judges(items, **tight))
    assert len(capped["summary"]["skipped_spend_cap"]) == 2  # rubric first, then the cap stops


def test_calibration_sheet_is_blind(tmp_path):
    from evals import judge

    judged = [
        {
            "key": f"k{i}",
            "kind": "rubric",
            "system_id": "system" if i % 2 else "b0-sonnet",
            "question": f"Q{i}",
            "reference": "R",
            "answer": "line one\n\nline two",
            "result": {"score": 1 + i % 5, "parse_ok": True},
        }
        for i in range(30)
    ]
    sample = judge.calibration_sample(judge.calibration_rows(judged))
    assert len(sample) == 20 and {s["score"] for s in sample} == {1, 2, 3, 4, 5}
    rows = [
        json.loads(line)
        for line in judge.blind_export(sample, tmp_path / "b.jsonl").read_text().splitlines()
    ]
    assert all(set(r) == {"key", "question", "reference", "answer", "student_score"} for r in rows)
    text = judge.calibration_markdown(sample, tmp_path / "b.md").read_text(encoding="utf-8")
    assert "Your score (1-5)" in text and "b0-sonnet" not in text and '"score"' not in text


def test_report_handwritten_section_scores_recall_and_pending_calibration(tmp_path, monkeypatch):
    from evals import judge, report

    monkeypatch.setattr(judge, "CALIBRATION_JSONL", tmp_path / "none.jsonl")
    monkeypatch.setattr(judge, "CALIBRATION_V2_JSONL", tmp_path / "none_v2.jsonl")
    rubric = [
        {
            "key": f"{s}{i}",
            "kind": "rubric",
            "system_id": s,
            "result": {"score": score_, "parse_ok": True},
        }
        for s, scores in (("system", [5, 4, 4]), ("b0-sonnet", [2, 3, 1]))
        for i, score_ in enumerate(scores)
    ]
    supported = {"supported": True, "parse_ok": True}
    claim = {"kind": "claim", "system_id": "system", "result": supported}
    data = {
        "judge": rubric + [claim],
        "handwritten_questions": {"hq": {"id": "hq", "gold_chunk_ids": ["a", "b"]}},
        "handwritten": {
            "system": {
                "hq": {
                    "status": "done",
                    "prediction": {"text": "An answer."},
                    "retrieval": {"first_search": {"w1": ["a", "x", "y", "z", "q", "b"]}},
                    "citations": {"text_total": 2, "text_string_supported": 1},
                },
                "hq_budget": {"status": "error", "prediction": None},  # no answer (D108)
            }
        },
    }
    text = "\n".join(report.handwritten_section(data))
    # (5 + 4 + 4 + 1) / 4 with the no-answer run scored 1; 4.33 over answered; 1 of 2 no answer
    assert "| system | 3.50 [" in text and "| 4.33 [" in text and "| 1/2 |" in text
    assert "| b0-sonnet | 2.00 [" in text and "| 0/3 |" in text
    assert "v2: shuffled blind sheet, D110): pending" in text and "v1" not in text
    assert "string match 1, by the claim judge 1 of 1 judged (100.0% supported)" in text
    assert "recall@5 0.500, recall@10 1.000 (n=1)" in text
    v1 = tmp_path / "v1.jsonl"
    v1.write_text(
        "".join(
            json.dumps({"key": r["key"], "question": "Q", "reference": "R", "answer": "A"}).replace(
                "}", ', "student_score": 4}'
            )
            + "\n"
            for r in rubric
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(judge, "CALIBRATION_JSONL", v1)
    text = "\n".join(report.handwritten_section(data))
    assert "v1, contaminated) n=6: exact 33.3%" in text and "): pending" in text
    assert "covers judge scores" not in text  # a judge 1 is in this sample
    assert "indicative" not in text and "| v2 item |" not in text  # v1 never decides
    v2, items = tmp_path / "v2.jsonl", tmp_path / "map.json"
    judge.export_v2(v1, v2, tmp_path / "v2.md", items)
    monkeypatch.setattr(judge, "CALIBRATION_V2_JSONL", v2)
    monkeypatch.setattr(judge, "CALIBRATION_V2_MAP", items)
    item_map = json.loads(items.read_text(encoding="utf-8"))["items"]
    rows = [json.loads(line) for line in v2.read_text(encoding="utf-8").splitlines()]
    by_key = {r["key"]: r["result"]["score"] for r in rubric}
    rows[0]["student_score"] = 2  # partial labels: still pending, no table
    v2.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    assert "): pending" in "\n".join(report.handwritten_section(data))
    for r in rows:  # all 2s except the judge's own score on item 1
        r["student_score"] = 2
    v2.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    text = "\n".join(report.handwritten_section(data))
    assert "(primary, v2: shuffled blind sheet, D110) n=6" in text
    assert "D093) (indicative only)" in text and "claim judge (indicative only)" in text
    first = item_map["1"]
    assert f"| 1 | `{first[:8]}` |" in text and f"| {by_key[first]} | 2 |" in text
    for r in rows:
        r["student_score"] = by_key[item_map[str(r["item"])]]
    v2.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    text = "\n".join(report.handwritten_section(data))
    assert "v2: shuffled blind sheet, D110) n=6: exact 100.0%" in text and "κ 1.00." in text
    assert "D093) (indicative only)" not in text and "| v2 item |" in text


def test_calibration_v2_sheet_is_shuffled_neutral_and_never_overwritten(tmp_path):
    from evals import judge

    v1 = tmp_path / "v1.jsonl"
    rows = [
        {
            "key": f"k{i:02d}",
            "question": f"Q{i}",
            "reference": "R",
            "answer": "A",
            "student_score": 3,
        }
        for i in range(20)
    ]
    v1.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    before = v1.read_bytes()
    out, md, items = tmp_path / "v2.jsonl", tmp_path / "v2.md", tmp_path / "map.json"
    sheet = judge.export_v2(v1, out, md, items, seed=7)
    assert v1.read_bytes() == before  # v1 labels untouched
    assert [r["item"] for r in sheet] == list(range(1, 21))
    assert all(
        set(r) == {"item", "question", "reference", "answer", "student_score"} for r in sheet
    )
    assert all(r["student_score"] is None for r in sheet)
    mapping = json.loads(items.read_text(encoding="utf-8"))
    assert mapping["seed"] == 7 and sorted(mapping["items"].values()) == [r["key"] for r in rows]
    assert list(mapping["items"].values()) != [r["key"] for r in rows]  # reordered
    assert judge.shuffled_sheet(rows, 7) == judge.shuffled_sheet(rows, 7)  # seeded
    for r in sheet:
        assert r["question"] == f"Q{mapping['items'][str(r['item'])][1:].lstrip('0') or '0'}"
    text = md.read_text(encoding="utf-8")
    assert "## Item 1\n" in text and "k0" not in text and "seed 7" in text
    assert "judge_calibration_blind_v2.jsonl` (same item numbers)" in text
    with pytest.raises(FileExistsError):
        judge.export_v2(v1, out, md, items, seed=7)


def test_report_interpretation_b2_oracle_cost_and_disney_sensitivity():
    from evals import report

    system = _rows([True] * 10)
    b2 = _rows([True] * 8 + [False] * 2)
    for rows in (system, b2):
        for i in (8, 9):  # Disney segment operating income in the gold (D110)
            rows[f"q{i}"]["question"]["computation"] = {
                "inputs": [{"ticker": "DIS", "concept": "OperatingIncomeLoss"}]
            }
        for x in rows.values():
            x["record"] = dict(x["record"])
    for x in b2.values():
        x["record"] |= {"cost_usd": "0.002", "latency_note": "batch, not comparable"}
    text = "\n".join(
        report.interpretation({"system": system, "b2-sonnet": b2}, "system", Decimal("0.5"))
    )
    assert "oracle-context baseline" in text and "scores 100.0% and B2 80.0%" in text
    assert "system $0.010 (real time); B2 $0.002 at Batch API prices, about $0.004" in text
    assert "2.5x B2's real-time price" in text and "M6 data-definition item" in text
    assert "| b2-sonnet | 80.0% [" in text and "| 2 | 100.0% [100.0%, 100.0%] n=8* |" in text
    no_multiplier = "\n".join(
        report.interpretation({"system": system, "b2-sonnet": b2}, "system", None)
    )
    assert (
        "B2 $0.002 at Batch API prices." in no_multiplier and "real-time price" not in no_multiplier
    )

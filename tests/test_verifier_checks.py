"""Deterministic verification (D056) on a synthetic ledger; values are test data, not SEC facts."""

from filinglens.agents.ledger import Ledger
from filinglens.agents.schemas import Answer
from filinglens.agents.verifier import check_claim, deterministic_checks, resolve_field

CHUNK = "chk_" + "a" * 64


def ledger() -> Ledger:
    led = Ledger()
    led.register(
        "get_financial_metric",
        {},
        {
            "data": {
                "ticker": "TEST",
                "metric": "revenue",
                "snapshot": {},
                "facts": [
                    {
                        "fact_id": "1",
                        "metric": "revenue",
                        "fiscal_year": 2025,
                        "fiscal_period": "Q1",
                        "value": "400",
                        "unit": "USD",
                        "status": "available",
                    },
                    {
                        "fact_id": "2",
                        "metric": "gross_profit",
                        "fiscal_year": 2025,
                        "fiscal_period": "Q1",
                        "value": "100",
                        "unit": "USD",
                        "status": "available",
                    },
                    {
                        "fact_id": None,
                        "metric": "gross_profit",
                        "fiscal_year": 2025,
                        "fiscal_period": "Q2",
                        "value": None,
                        "unit": "USD",
                        "status": "unavailable",
                        "reason": "missing",
                    },
                ],
            }
        },
        False,
        None,
    )
    led.register(
        "margin",
        {"numerator": "100", "denominator": "400"},
        {"data": {"numerator": "100", "denominator": "400", "value_pct": "25"}},
        False,
        led.next_computation_id(),
    )
    led.register(
        "evaluate",
        {"expression": "25 - 7.5"},
        {"data": {"expression": "25 - 7.5", "normalized_expression": "25 - 7.5", "value": "17.5"}},
        False,
        led.next_computation_id(),
    )
    led.register(
        "yoy_series",
        {},
        {
            "data": {
                "points": [
                    {
                        "label": "a",
                        "value": "100",
                        "change_pct": None,
                        "reason": "first_observation",
                    },
                    {"label": "b", "value": "400", "change_pct": "300", "reason": None},
                ]
            }
        },
        False,
        led.next_computation_id(),
    )
    led.register(
        "search_filings",
        {},
        {
            "data": {
                "hits": [
                    {
                        "chunk_id": CHUNK,
                        "ticker": "TEST",
                        "form": "10-K",
                        "fiscal_year": 2025,
                        "fiscal_period": "FY",
                        "item": "7",
                        "text": "Management said revenue grew.",
                    }
                ]
            }
        },
        False,
        None,
    )
    return led


def claim(**kw):
    base = {
        "id": "c1",
        "kind": "numeric",
        "text": "Revenue was 400.",
        "value": "400",
        "unit": "USD",
        "value_basis": "fact",
        "citations": [{"kind": "fact", "ref": "1"}],
    }
    return Answer.model_validate(
        {
            "status": "answered",
            "summary": "s",
            "claims": [{**base, **kw}],
        }
    ).claims[0]


def test_fact_and_computation_values_must_match_exactly():
    led = ledger()
    assert check_claim(claim(), led, True).verdict == "supported"
    assert check_claim(claim(value="400.00"), led, True).verdict == "supported"  # Decimal equality
    wrong = check_claim(claim(value="401"), led, True)
    assert wrong.verdict == "needs_revision" and "fact 1=400" in wrong.reasons[0]
    margin = claim(
        value="25",
        unit="percent",
        value_basis="computation",
        citations=[{"kind": "computation", "ref": "cmp_1"}, {"kind": "fact", "ref": "2"}],
    )
    assert check_claim(margin, led, True).verdict == "supported"
    bad_unit = check_claim(margin.model_copy(update={"unit": "USD"}), led, True)
    assert bad_unit.verdict == "needs_revision" and "percent" in bad_unit.reasons[0]
    yoy = claim(
        value="300",
        unit="percent",
        value_basis="computation",
        citations=[{"kind": "computation", "ref": "cmp_3", "field": "points[1].change_pct"}],
    )
    assert check_claim(yoy, led, True).verdict == "supported"
    assert resolve_field(led.computations["cmp_3"].output, "points[5].change_pct") is None


def test_citations_must_come_from_this_run_and_status_records_carry_no_value():
    led = ledger()
    missing = claim(citations=[{"kind": "fact", "ref": "999"}])
    assert check_claim(missing, led, True).verdict == "unsupported"
    assert (
        check_claim(
            claim(
                kind="textual",
                value=None,
                unit=None,
                value_basis=None,
                citations=[{"kind": "chunk", "ref": CHUNK}],
            ),
            led,
            True,
        ).verdict
        == "supported"
    )
    status = claim(value="0", citations=[{"kind": "fact", "ref": "na_TEST_gross_profit_2025_Q2"}])
    assert check_claim(status, led, True).verdict == "needs_revision"
    assert led.facts["na_TEST_gross_profit_2025_Q2"].status == "unavailable"


def test_lineage_rejects_untraced_inputs_but_allows_small_constants():
    led = ledger()
    diff = claim(
        value="17.5",
        unit="percentage_points",
        value_basis="computation",
        citations=[{"kind": "computation", "ref": "cmp_2"}],
    )
    result = check_claim(diff, led, True)
    assert result.verdict == "needs_revision" and "7.5" in result.reasons[0]
    led.register(
        "evaluate",
        {},
        {"data": {"expression": "25 - 5", "normalized_expression": "25 - 5", "value": "20"}},
        False,
        led.next_computation_id(),
    )
    ok = claim(
        value="20",
        unit="percentage_points",
        value_basis="computation",
        citations=[{"kind": "computation", "ref": "cmp_4"}],
    )
    assert check_claim(ok, led, True).verdict == "supported"  # 25 from cmp_1, 5 a small constant


def test_model_arithmetic_depends_on_quant_mode_and_other_fields():
    led = ledger()
    model_math = claim(
        value="25",
        unit="percent",
        value_basis="model_arithmetic",
        citations=[{"kind": "fact", "ref": "1"}, {"kind": "fact", "ref": "2"}],
    )
    assert check_claim(model_math, led, True).verdict == "needs_revision"
    assert check_claim(model_math, led, False).verdict == "unverifiable_model_arithmetic"
    period = claim(period={"fiscal_year": 2024, "fiscal_period": "Q1"})
    assert "period" in check_claim(period, led, True).reasons[0]
    assert "ticker" in check_claim(claim(ticker="OTHER"), led, True).reasons[0]


def test_summary_numbers_and_final_value():
    led = ledger()
    answer = Answer.model_validate(
        {
            "status": "answered",
            "summary": "Revenue was $400 in fiscal 2025 across 4 quarters; margin 31.5%.",
            "claims": [
                {
                    "id": "c1",
                    "kind": "numeric",
                    "text": "Revenue was $400.",
                    "value": "400",
                    "unit": "USD",
                    "value_basis": "fact",
                    "citations": [{"kind": "fact", "ref": "1"}],
                }
            ],
            "final_value": "400",
            "final_unit": "percent",
            "final_claim_id": "c1",
        }
    )
    checks = deterministic_checks(answer, led, True)
    assert checks["c1"].verdict == "supported"
    assert checks["summary"].verdict == "needs_revision" and "31.5" in checks["summary"].reasons[0]
    assert checks["answer"].verdict == "needs_revision"

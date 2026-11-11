"""Answer parsing, unit normalization, tolerances and statistics (D085, D087, D094); offline."""

import math
from decimal import Decimal

import pytest

from evals.answers import parse_answer, system_prompt
from evals.scorers import (
    bootstrap_ci,
    holm,
    mcnemar_exact,
    normalize,
    paired_diff_ci,
    score,
    weighted_kappa,
    within,
)

USD = {
    "template": "lookup",
    "gold_value": "95359000000",
    "gold_unit": "USD",
    "gold_choice": None,
    "tolerance": {"kind": "relative", "value": "0.005"},
}
PCT = {
    "template": "yoy_growth",
    "gold_value": "-38.453928773318",
    "gold_unit": "percent",
    "gold_choice": None,
    "tolerance": {"kind": "absolute", "value": "0.1"},
}
EPS = {
    "template": "lookup",
    "gold_value": "0.27",
    "gold_unit": "USD/shares",
    "gold_choice": None,
    "tolerance": {"kind": "eps", "relative": "0.005", "absolute": "0.005"},
}
CMP = {
    "template": "comparison",
    "gold_value": "0.026507473111",
    "gold_unit": "percentage_points",
    "gold_choice": "WMT",
    "tolerance": {"kind": "absolute", "value": "0.1"},
}


def pred(value, unit, status="answered", choice=None):
    return {"value": value, "unit": unit, "choice": choice, "status": status, "parse_ok": True}


def test_parse_answer_takes_the_last_json_object_and_reports_failures():
    text = (
        'Some thinking {"note": 1}\n```json\n{"value": "1,234.5", "unit": "USD millions", '
        '"choice": null, "status": "answered"}\n```'
    )
    p = parse_answer(text)
    assert p.parse_ok and p.value == "1234.5" and p.unit == "USD millions" and p.choice is None
    two = '{"value": 1, "unit": "USD"} then {"value": 2, "unit": "USD", "choice": "wmt"}'
    assert parse_answer(two).value == "2" and parse_answer(two).choice == "WMT"
    assert not parse_answer("no json here").parse_ok
    assert not parse_answer('{"value": null, "unit": "USD", "status": "answered"}').parse_ok
    assert parse_answer('{"value": null, "status": "not_applicable"}').status == "not_applicable"
    assert not parse_answer('{"value": true}').parse_ok
    assert not parse_answer('{"value": 5, "status": "maybe"}').parse_ok
    assert "You may search the web." in system_prompt("b1") and "excerpts" in system_prompt("b2")
    assert system_prompt("b0").endswith('"status": "<answered | not_available | not_applicable>"}')


def test_unit_normalization_without_guessing():
    v = Decimal("95.359")
    assert normalize(v, "USD billions", "USD") == Decimal("95359000000.000")
    assert normalize(Decimal("95359"), "$ millions", "USD") == Decimal("95359000000")
    assert normalize(Decimal("95359000"), "thousands", "USD") == Decimal("95359000000")
    assert normalize(Decimal("95359000000"), "USD", "USD") == Decimal("95359000000")
    assert normalize(Decimal("1"), "USD/share", "USD") is None  # wrong dimension
    assert normalize(Decimal("-0.3845"), "fraction", "percent") == Decimal("-38.4500")
    assert normalize(Decimal("2.65"), "pp", "percentage_points") == Decimal("2.65")
    assert normalize(Decimal("0.27"), "USD per share", "USD/shares") == Decimal("0.27")
    assert normalize(Decimal("1"), "furlongs", "USD") is None


def test_tolerance_edges_eps_signs_and_comparison_choice():
    assert score(USD, pred("95.36", "USD billions")).correct  # 0.0006% off
    exactly = Decimal("95359000000") * Decimal("1.005")
    assert within(exactly, Decimal("95359000000"), USD["tolerance"])  # boundary inclusive
    assert not score(USD, pred(str(exactly + 1), "USD")).correct
    assert score(PCT, pred("-38.36", "percent")).correct  # 0.094 pp
    assert not score(PCT, pred("38.45", "percent")).correct  # sign matters
    assert score(EPS, pred("0.275", "USD/share")).correct  # within the $0.005 floor
    assert not score(EPS, pred("0.28", "USD/share")).correct
    assert score(CMP, pred("-0.03", "percentage_points", choice="WMT")).correct  # magnitude
    wrong_choice = score(CMP, pred("0.03", "percentage_points", choice="COST"))
    assert not wrong_choice.correct and "choice" in wrong_choice.detail


def test_abstentions_parse_failures_errors_and_unit_rescue_are_separate():
    assert score(USD, pred(None, None, "not_available")).outcome == "abstained"
    assert score(USD, {"parse_ok": False, "parse_error": "x"}).outcome == "parse_failure"
    assert score(USD, None, error="ProviderError").outcome == "error"
    rescue = score(USD, pred("95359", "USD"))  # millions given without the unit
    assert rescue.outcome == "wrong" and rescue.unit_rescue
    probe = {"template": "abstention_probe", "gold_value": None, "gold_status": "not_applicable"}
    assert score(probe, pred(None, None, "not_applicable")).correct
    assert score(probe, pred(None, None, "not_available")).correct
    assert not score(probe, pred("1", "percent")).correct


def test_statistics_on_known_small_cases():
    acc, lo, hi = bootstrap_ci([True] * 8 + [False] * 2, resamples=2000)
    assert acc == 0.8 and lo <= 0.8 <= hi and 0.4 < lo < hi <= 1.0
    assert bootstrap_ci([True] * 5)[1:] == (1.0, 1.0)
    assert mcnemar_exact([True, True, False], [True, False, False]) == (1, 0, 1.0)
    only_a, only_b, p = mcnemar_exact([True] * 10, [False] * 10)
    assert (only_a, only_b) == (10, 0) and math.isclose(p, 2 / 2**10)
    d, lo, hi = paired_diff_ci(
        [True, True, False, True], [False, True, False, False], resamples=2000
    )
    assert d == 0.5 and lo <= d <= hi
    assert holm({"a": 0.01, "b": 0.04, "c": 0.03}) == pytest.approx(
        {"a": 0.03, "b": 0.06, "c": 0.06}
    )
    assert weighted_kappa([1, 2, 3, 4, 5], [1, 2, 3, 4, 5]) == 1.0
    assert weighted_kappa([1, 2, 3, 4, 5], [5, 4, 3, 2, 1]) < 0

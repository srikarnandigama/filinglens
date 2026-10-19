"""Financial values come exclusively from downloaded SEC fixtures.

Structural perturbations remove observations or change metadata to exercise
selection behavior; they never introduce invented expected financial values.
"""

import copy
import json
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from filinglens.edgar.filings import FiscalYear, fiscal_calendar
from filinglens.edgar.xbrl import METRICS, normalized_facts, observations

DIRECTORY = Path(__file__).parent / "fixtures"
EXPECTED = json.loads((DIRECTORY / "revenue_expected.json").read_text())


def load_company(ticker):
    company = next(row for row in EXPECTED["companies"] if row["ticker"] == ticker)
    raw = json.loads((DIRECTORY / company["companyfacts_fixture"]).read_text())
    dates = company["calendar"]
    year = FiscalYear(
        dates["year"],
        date.fromisoformat(dates["start"]),
        date.fromisoformat(dates["end"]),
        tuple(date.fromisoformat(end) for end in dates["quarter_ends"]),
    )
    return company, raw, year


@pytest.mark.parametrize("ticker", ["AAPL", "MSFT", "NVDA"])
def test_twelve_revenue_values_against_filing_tags(ticker):
    company, raw, year = load_company(ticker)
    facts = normalized_facts(raw, [year], date.fromisoformat(EXPECTED["cutoff"]))
    by_period = {fact.fiscal_period: fact for fact in facts if fact.metric == "revenue"}
    for expected in company["expected"]:
        fact = by_period[expected["fiscal_period"]]
        assert fact.value == Decimal(expected["value"])
        assert str(fact.start_date) == expected["start_date"]
        assert str(fact.end_date) == expected["end_date"]
        assert fact.unit == expected["unit"]
        assert fact.source_accession
        if fact.derived:
            assert fact.value == sum(
                Decimal(row["value"]) * row["coefficient"] for row in fact.derivation_inputs
            )


def test_misleading_filing_fy_fp_ignored_and_q4_derived():
    _, raw, year = load_company("AAPL")
    for concept in raw["facts"]["us-gaap"].values():
        for values in concept["units"].values():
            for row in values:
                row["fy"], row["fp"] = 1900, "FY"
    facts = normalized_facts(raw, [year], date.fromisoformat(EXPECTED["cutoff"]))
    q4 = next(fact for fact in facts if fact.fiscal_period == "Q4")
    assert q4.fiscal_year == 2025
    assert q4.derived
    assert len(q4.derivation_inputs) == 2


@pytest.mark.parametrize("period", ["Q2", "Q3"])
def test_ytd_difference_when_direct_quarter_missing(period):
    company, raw, year = load_company("AAPL")
    expected = next(row for row in company["expected"] if row["fiscal_period"] == period)
    for concept in raw["facts"]["us-gaap"].values():
        for unit, values in concept["units"].items():
            concept["units"][unit] = [
                row
                for row in values
                if not (
                    row.get("start") == expected["start_date"]
                    and row["end"] == expected["end_date"]
                )
            ]
    fact = next(
        fact
        for fact in normalized_facts(raw, [year], date.fromisoformat(EXPECTED["cutoff"]))
        if fact.fiscal_period == period
    )
    assert fact.derived
    assert fact.value == Decimal(expected["value"])
    assert {row["concept"] for row in fact.derivation_inputs} == {fact.concept}


def test_q4_fallback_to_three_direct_quarters():
    company, raw, year = load_company("AAPL")
    for concept in raw["facts"]["us-gaap"].values():
        for unit, values in concept["units"].items():
            concept["units"][unit] = [
                row
                for row in values
                if not (
                    row.get("start") == str(year.start) and row["end"] == str(year.quarter_ends[2])
                )
            ]
    fact = next(
        fact
        for fact in normalized_facts(raw, [year], date.fromisoformat(EXPECTED["cutoff"]))
        if fact.fiscal_period == "Q4"
    )
    assert len(fact.derivation_inputs) == 4
    assert fact.value == Decimal(company["expected"][3]["value"])


def test_latest_filed_selection_and_cutoff():
    _, raw, _ = load_company("AAPL")
    data = raw["facts"]["us-gaap"]
    concept = next(name for name in METRICS["revenue"] if name in data)
    original = data[concept]["units"]["USD"]
    cutoff = date(2025, 1, 31)
    selected = observations(data, concept, "USD", cutoff)
    for obs in selected:
        candidates = [
            row
            for row in original
            if row.get("start") == str(obs.start)
            and row["end"] == str(obs.end)
            and row["filed"] <= str(cutoff)
            and row["form"] in {"10-K", "10-Q"}
        ]
        latest = max(candidates, key=lambda row: (row["filed"], row["accn"]))
        assert obs.value == Decimal(str(latest["val"]))
        assert obs.accession == latest["accn"]
        assert obs.filed <= cutoff
    assert selected


def test_actual_dates_determine_calendar():
    company, raw, year = load_company("AAPL")
    filings = [
        {"form": row["form"], "reportDate": row["report_date"]}
        for row in company["sources"].values()
    ]
    calendar = fiscal_calendar(filings, raw, 1)
    assert calendar == [year]


def test_missing_metric_is_absent_not_zero():
    _, raw, year = load_company("AAPL")
    assert not [
        fact
        for fact in normalized_facts(raw, [year], date(2026, 10, 19))
        if fact.metric == "gross_profit"
    ]


def test_incompatible_ytd_concepts_not_combined():
    company, raw, year = load_company("AAPL")
    concept = company["expected"][0]["inputs"][0]["concept"].split(":")[-1]
    source = copy.deepcopy(raw["facts"]["us-gaap"][concept])
    # Retain only annual data in one concept, nine-month data in another.
    annual = [
        row
        for row in source["units"]["USD"]
        if row.get("start") == str(year.start) and row["end"] == str(year.end)
    ]
    ytd = [
        row
        for row in source["units"]["USD"]
        if row.get("start") == str(year.start) and row["end"] == str(year.quarter_ends[2])
    ]
    raw["facts"]["us-gaap"] = {
        METRICS["revenue"][0]: {"units": {"USD": annual}},
        METRICS["revenue"][1]: {"units": {"USD": ytd}},
    }
    assert not [
        fact
        for fact in normalized_facts(raw, [year], date(2026, 10, 19))
        if fact.fiscal_period == "Q4"
    ]


def test_eps_never_derived_and_instant_facts_not_summed():
    _, _, year = load_company("AAPL")
    raw = json.loads((DIRECTORY / "aapl_normalization_inputs.json").read_text())
    eps = raw["facts"]["us-gaap"]["EarningsPerShareDiluted"]
    for unit, rows in eps["units"].items():
        # Remove direct later quarters, retain genuine annual and YTD EPS.
        eps["units"][unit] = [row for row in rows if row.get("start") == str(year.start)]
    facts = normalized_facts(raw, [year], date(2026, 10, 19))
    assert all(not fact.derived for fact in facts if fact.metric == "eps_diluted")
    assert {fact.fiscal_period for fact in facts if fact.metric == "eps_diluted"} <= {"Q1", "FY"}
    assets = [fact for fact in facts if fact.metric == "total_assets"]
    assert len(assets) == 4
    assert all(fact.start_date is None and not fact.derived for fact in assets)


def test_no_mixed_units_and_per_period_fallback():
    company, raw, year = load_company("AAPL")
    data = raw["facts"]["us-gaap"]
    concept = company["expected"][0]["inputs"][0]["concept"].split(":")[-1]
    source = copy.deepcopy(data[concept])
    q1_end = str(year.quarter_ends[0])
    # Structural concept-switch scenario using only genuine downloaded values.
    raw["facts"]["us-gaap"] = {
        METRICS["revenue"][0]: {
            "units": {"USD": [row for row in source["units"]["USD"] if row["end"] == q1_end]}
        },
        METRICS["revenue"][1]: source,
    }
    facts = normalized_facts(raw, [year], date(2026, 10, 19))
    assert (
        next(fact for fact in facts if fact.fiscal_period == "Q1").concept == METRICS["revenue"][0]
    )
    assert (
        next(fact for fact in facts if fact.fiscal_period == "Q2").concept == METRICS["revenue"][1]
    )
    for concept in raw["facts"]["us-gaap"].values():
        concept["units"]["CAD"] = concept["units"].pop("USD")
    assert normalized_facts(raw, [year], date(2026, 10, 19)) == []


def test_costco_nonstandard_quarter_lengths_use_actual_boundaries():
    data = json.loads((DIRECTORY / "cost_revenue_calendar.json").read_text())
    raw = data["calendar"]
    year = FiscalYear(
        raw["year"],
        date.fromisoformat(raw["start"]),
        date.fromisoformat(raw["end"]),
        tuple(date.fromisoformat(end) for end in raw["quarter_ends"]),
    )
    facts = normalized_facts(data, [year], date(2026, 10, 19))
    quarters = [fact for fact in facts if fact.fiscal_period != "FY"]
    assert {fact.fiscal_period for fact in quarters} == {"Q1", "Q2", "Q3", "Q4"}
    # Fixed 80-100 day bands would incorrectly discard the 16-week Q4.
    q4 = next(fact for fact in quarters if fact.fiscal_period == "Q4")
    assert (q4.end_date - q4.start_date).days + 1 == 112
    assert sum(fact.value for fact in quarters) == next(
        fact.value for fact in facts if fact.fiscal_period == "FY"
    )

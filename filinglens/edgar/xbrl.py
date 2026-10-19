"""Normalize SEC facts without using the filing's fy/fp as period labels."""

from dataclasses import asdict, dataclass
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from filinglens.edgar.filings import FiscalYear

METRICS: dict[str, tuple[str, ...]] = {
    "revenue": (
        "Revenues",
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "RevenueFromContractWithCustomerIncludingAssessedTax",
        "SalesRevenueNet",
    ),
    "cost_of_revenue": ("CostOfRevenue", "CostOfGoodsAndServicesSold", "CostOfGoodsSold"),
    "gross_profit": ("GrossProfit",),
    "operating_income": ("OperatingIncomeLoss",),
    "net_income": ("NetIncomeLoss",),
    "eps_diluted": ("EarningsPerShareDiluted",),
    "rnd_expense": ("ResearchAndDevelopmentExpense",),
    "operating_cash_flow": ("NetCashProvidedByUsedInOperatingActivities",),
    "capex": ("PaymentsToAcquirePropertyPlantAndEquipment",),
    "total_assets": ("Assets",),
    "cash": ("CashAndCashEquivalentsAtCarryingValue",),
}
INSTANT = {"total_assets", "cash"}


@dataclass(frozen=True)
class Observation:
    concept: str
    start: date | None
    end: date
    value: Decimal
    unit: str
    accession: str
    filed: date

    def provenance(self, coefficient: int = 1) -> dict[str, Any]:
        result = {
            key: str(value) if isinstance(value, (date, Decimal)) else value
            for key, value in asdict(self).items()
        }
        result["coefficient"] = coefficient
        return result


@dataclass(frozen=True)
class Fact:
    metric: str
    concept: str
    period_type: str
    start_date: date | None
    end_date: date
    fiscal_year: int
    fiscal_period: str
    value: Decimal
    unit: str
    derived: bool
    source_accession: str
    source_filed: date
    derivation_inputs: list[dict[str, Any]]


def observations(data: dict[str, Any], concept: str, unit: str, cutoff: date) -> list[Observation]:
    latest: dict[tuple[date | None, date], Observation] = {}
    for raw in data.get(concept, {}).get("units", {}).get(unit, []):
        if raw["form"] not in {"10-K", "10-Q"} or raw["filed"] > str(cutoff):
            continue
        observation = Observation(
            concept,
            date.fromisoformat(raw["start"]) if raw.get("start") else None,
            date.fromisoformat(raw["end"]),
            Decimal(str(raw["val"])),
            unit,
            raw["accn"],
            date.fromisoformat(raw["filed"]),
        )
        key = (observation.start, observation.end)
        old = latest.get(key)
        if old is None or (observation.filed, observation.accession) > (old.filed, old.accession):
            latest[key] = observation
        elif (observation.filed, observation.accession) == (
            old.filed,
            old.accession,
        ) and observation.value != old.value:
            raise ValueError(f"Conflicting identical-context facts: {concept} {key}")
    return list(latest.values())


def normalized_facts(
    companyfacts: dict[str, Any], calendar: list[FiscalYear], cutoff: date
) -> list[Fact]:
    data = companyfacts.get("facts", {}).get("us-gaap", {})
    result = []
    for metric, concepts in METRICS.items():
        unit = "USD/shares" if metric == "eps_diluted" else "USD"
        by_concept = {concept: observations(data, concept, unit, cutoff) for concept in concepts}
        for year in calendar:
            periods = [(f"Q{i + 1}", end) for i, end in enumerate(year.quarter_ends)]
            if year.end:
                periods.append(("FY", year.end))
            for period, end in periods:
                quarter = int(period[1]) if period != "FY" else 0
                start = (
                    None
                    if metric in INSTANT
                    else (
                        year.start
                        if quarter <= 1
                        else year.quarter_ends[quarter - 2] + timedelta(days=1)
                    )
                )
                if period == "FY" and metric in INSTANT:
                    # Q4 already represents this same balance-sheet instant.
                    continue
                period_type = (
                    "instant" if metric in INSTANT else "annual" if period == "FY" else "quarter"
                )
                chosen: Fact | None = None
                # Direct observations win over derivations, then concept priority applies.
                for concept in concepts:
                    match = next(
                        (
                            obs
                            for obs in by_concept[concept]
                            if obs.start == start and obs.end == end
                        ),
                        None,
                    )
                    if match:
                        chosen = Fact(
                            metric,
                            concept,
                            period_type,
                            start,
                            end,
                            year.year,
                            period,
                            match.value,
                            unit,
                            False,
                            match.accession,
                            match.filed,
                            [],
                        )
                        break
                if (
                    chosen is None
                    and metric not in INSTANT
                    and metric != "eps_diluted"
                    and quarter >= 2
                ):
                    for concept in concepts:
                        observations_for_concept = by_concept[concept]
                        cumulative = next(
                            (
                                obs
                                for obs in observations_for_concept
                                if obs.start == year.start and obs.end == end
                            ),
                            None,
                        )
                        prior_end = year.quarter_ends[quarter - 2]
                        prior = next(
                            (
                                obs
                                for obs in observations_for_concept
                                if obs.start == year.start and obs.end == prior_end
                            ),
                            None,
                        )
                        inputs: list[tuple[Observation, int]] = []
                        if cumulative and prior:
                            inputs = [(cumulative, 1), (prior, -1)]
                        elif quarter == 4 and cumulative:
                            direct_quarters = []
                            for index in range(3):
                                qstart = (
                                    year.start
                                    if index == 0
                                    else year.quarter_ends[index - 1] + timedelta(days=1)
                                )
                                obs = next(
                                    (
                                        obs
                                        for obs in observations_for_concept
                                        if obs.start == qstart
                                        and obs.end == year.quarter_ends[index]
                                    ),
                                    None,
                                )
                                if obs:
                                    direct_quarters.append(obs)
                            if len(direct_quarters) == 3:
                                inputs = [(cumulative, 1)] + [(obs, -1) for obs in direct_quarters]
                        if inputs:
                            chosen = Fact(
                                metric,
                                concept,
                                period_type,
                                start,
                                end,
                                year.year,
                                period,
                                sum(
                                    (obs.value * coefficient for obs, coefficient in inputs),
                                    Decimal(0),
                                ),
                                unit,
                                True,
                                cumulative.accession,
                                max(obs.filed for obs, _ in inputs),
                                [obs.provenance(coefficient) for obs, coefficient in inputs],
                            )
                            break
                if chosen:
                    result.append(chosen)
    return result

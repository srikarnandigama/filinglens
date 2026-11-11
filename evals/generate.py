"""Generated benchmark v1 (SPEC §13.1; D083-D086).

Every gold value is computed here, in Python, from financial_facts of the frozen snapshot with
Decimal arithmetic; no LLM is involved. Fairness metadata (original filing dates, restatements)
comes from the frozen companyfacts JSON in the raw snapshot. The pure functions below take plain
Fact objects, so tests can exercise them on synthetic facts without a database.
"""

import argparse
import gzip
import hashlib
import json
import math
from collections import Counter, defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date
from decimal import ROUND_HALF_EVEN, Context, Decimal
from pathlib import Path
from typing import Any

from filinglens.config import ROOT

SEED = 20261109
GENERATOR_VERSION = "gen-v1"
SNAPSHOT_ID = "2026-10-19-v1"
INGESTION_CUTOFF = "2026-10-19"
DRAFT_PATH = ROOT / "evals" / "questions_v1.draft.jsonl"
FROZEN_PATH = ROOT / "evals" / "questions_v1.jsonl"
MANIFEST_PATH = ROOT / "evals" / "questions_v1.manifest.json"
B2_META_PATH = ROOT / "evals" / "b2_contexts_v1.meta.jsonl"
SUBSET_PATH = ROOT / "evals" / "questions_v1.subset180.json"
SUBSET_SIZE = 180
TARGETS = {
    "lookup": 60,
    "yoy_growth": 60,
    "margin": 60,
    "trend_avg": 55,
    "derived_q4": 55,
    "comparison": 55,
    "multi_step": 55,
}
DEV_SHARE = Decimal("0.3")
POST_CUTOFF_FLOOR = Decimal("0.2")
SAMPLE_SIZE = 100
MIN_COMPARISON_GAP = Decimal("0.2")
# D097: a derived fact whose inputs come from different filings and
# include a restated input mixes reporting vintages (e.g. BAC FY2024 revenue restated in the 2026
# 10-K minus the original 9M), so its "Q4" was never reported; questions using it are skipped.
EXCLUDE_MIXED_VINTAGE = True
# Official "Jun 2026" training-data and reliable-knowledge cutoffs (models overview, D096).
MODEL_CUTOFFS = {"claude-sonnet-5-5": "2026-06", "claude-opus-5-5": "2026-06"}
CTX = Context(prec=80, rounding=ROUND_HALF_EVEN)  # as quant-mcp (D040)
RATIO_PLACES = Decimal("1e-12")
FLOW_METRICS = (
    "revenue",
    "cost_of_revenue",
    "gross_profit",
    "operating_income",
    "net_income",
    "rnd_expense",
    "operating_cash_flow",
    "capex",
)
INSTANT_METRICS = ("total_assets", "cash")
MARGINS = {"gross_profit": "gross", "operating_income": "operating", "net_income": "net"}
PHRASES = {
    "revenue": "total revenue",
    "cost_of_revenue": "cost of revenue",
    "gross_profit": "gross profit",
    "operating_income": "operating income",
    "net_income": "net income",
    "rnd_expense": "research and development expense",
    "operating_cash_flow": "net cash provided by operating activities",
    "capex": "capital expenditures",
    "eps_diluted": "diluted earnings per share",
    "total_assets": "total assets",
    "cash": "cash and cash equivalents",
}
NAMES = {
    "AAPL": "Apple",
    "AMZN": "Amazon",
    "BAC": "Bank of America",
    "COST": "Costco",
    "CVX": "Chevron",
    "DIS": "Disney",
    "GOOGL": "Alphabet",
    "JNJ": "Johnson & Johnson",
    "JPM": "JPMorgan Chase",
    "KO": "Coca-Cola",
    "META": "Meta",
    "MSFT": "Microsoft",
    "NKE": "Nike",
    "NVDA": "Nvidia",
    "PFE": "Pfizer",
    "PG": "Procter & Gamble",
    "TSLA": "Tesla",
    "UNH": "UnitedHealth",
    "WMT": "Walmart",
    "XOM": "ExxonMobil",
}
BANKS = ("BAC", "JPM")
# D101: GICS sectors (S&P/MSCI, as listed for the S&P 500 constituents, checked 2026-11-09).
# Comparison questions only pair companies of the same sector; Financials holds only the banks.
SECTORS = {
    "AAPL": "Information Technology",
    "MSFT": "Information Technology",
    "NVDA": "Information Technology",
    "GOOGL": "Communication Services",
    "META": "Communication Services",
    "DIS": "Communication Services",
    "AMZN": "Consumer Discretionary",
    "TSLA": "Consumer Discretionary",
    "NKE": "Consumer Discretionary",
    "WMT": "Consumer Staples",
    "COST": "Consumer Staples",
    "KO": "Consumer Staples",
    "PG": "Consumer Staples",
    "JPM": "Financials",
    "BAC": "Financials",
    "XOM": "Energy",
    "CVX": "Energy",
    "JNJ": "Health Care",
    "PFE": "Health Care",
    "UNH": "Health Care",
}


@dataclass(frozen=True)
class Observation:
    """A value as first reported: the earliest-filed companyfacts observation for a context."""

    value: Decimal
    filed: str
    accession: str


@dataclass(frozen=True)
class Fact:
    fact_id: str
    ticker: str
    cik: str
    metric: str
    concept: str
    period_type: str  # quarter | annual | instant
    start: str | None
    end: str
    fiscal_year: int
    fiscal_period: str
    value: Decimal
    unit: str
    derived: bool
    accession: str | None
    filed: str
    url: str | None
    inputs: tuple[dict, ...] = ()  # derivation_inputs, signed by coefficient
    # As first reported (None when no observation was found in the frozen companyfacts).
    first_value: Decimal | None = None
    first_filed: str | None = None
    input_urls: tuple[str, ...] = ()

    @property
    def mixed_vintage(self) -> bool:
        """Derived from inputs of different filings where any input was later restated."""
        if not self.derived or len({i.get("accession") for i in self.inputs}) < 2:
            return False
        return any(
            i.get("first_value") is not None and Decimal(i["first_value"]) != Decimal(i["value"])
            for i in self.inputs
        )


@dataclass
class Candidate:
    template: str
    question: str
    unit: str
    companies: tuple[str, ...]
    metric: str
    periods: tuple[tuple[int, str], ...]
    facts: tuple[Fact, ...]
    compute: Callable[[dict[str, Decimal]], Decimal]
    formula: str
    choice_from: Callable[[dict[str, Decimal]], str] | None = None
    gold: Decimal = field(init=False)
    gold_choice: str | None = field(init=False, default=None)

    def __post_init__(self) -> None:
        latest = {f.fact_id: f.value for f in self.facts}
        self.gold = self.compute(latest)
        self.gold_choice = self.choice_from(latest) if self.choice_from else None

    @property
    def key(self) -> str:
        periods = ",".join(f"{y}{p}" for y, p in self.periods)
        return f"{self.template}|{'+'.join(self.companies)}|{self.metric}|{periods}"

    @property
    def id(self) -> str:
        return "q_" + hashlib.sha256(self.key.encode()).hexdigest()[:16]


# ---------------------------------------------------------------- Decimal arithmetic


def pct(numerator: Decimal, denominator: Decimal) -> Decimal:
    return CTX.multiply(CTX.divide(numerator, denominator), Decimal(100))


def growth(new: Decimal, old: Decimal) -> Decimal:
    """Percent change on a positive base (callers skip non-positive bases)."""
    return pct(CTX.subtract(new, old), old)


def mean(values: list[Decimal]) -> Decimal:
    return CTX.divide(sum(values, Decimal(0)), Decimal(len(values)))


def fixed(value: Decimal, ratio: bool) -> str:
    """Gold as a fixed-point string; ratios are rounded to 12 places like quant-mcp."""
    if ratio:
        value = value.quantize(RATIO_PLACES, context=CTX)
    text = format(value, "f")
    return text.rstrip("0").rstrip(".") if "." in text else text


# ---------------------------------------------------------------- fairness (D086)


def first_reported(fact: Fact) -> Decimal | None:
    """The fact's value as first reported; a derived value is rebuilt from its inputs."""
    if not fact.derived:
        return fact.first_value
    total = Decimal(0)
    for item in fact.inputs:
        original = item.get("first_value")
        if original is None:
            return None
        total += Decimal(str(item["coefficient"])) * Decimal(original)
    return total


def fact_first_filed(fact: Fact) -> str | None:
    if not fact.derived:
        return fact.first_filed
    dates = [item.get("first_filed") for item in fact.inputs]
    return None if any(d is None for d in dates) else max(dates)


def cutoff_bucket(first_filed: str | None, cutoff_month: str) -> str:
    if first_filed is None:
        return "unknown"
    month = first_filed[:7]
    return "before" if month < cutoff_month else "june" if month == cutoff_month else "after"


def fairness(c: Candidate) -> dict[str, Any]:
    filed = [fact_first_filed(f) for f in c.facts]
    first_filed_max = None if any(d is None for d in filed) else max(filed)
    originals = {f.fact_id: first_reported(f) for f in c.facts}
    restated: bool | None
    detail = None
    if any(v is None for v in originals.values()):
        restated = None
    else:
        original_gold = c.compute(originals)  # type: ignore[arg-type]
        ratio = c.unit in ("percent", "percentage_points")
        restated = fixed(original_gold, ratio) != fixed(c.gold, ratio)
        if restated:
            detail = {
                "gold_as_first_reported": fixed(original_gold, ratio),
                "changed_inputs": {
                    f.fact_id: {"first_reported": str(originals[f.fact_id]), "latest": str(f.value)}
                    for f in c.facts
                    if originals[f.fact_id] != f.value
                },
            }
    return {
        "period_end_max": max(f.end for f in c.facts),
        "first_filed_max": first_filed_max,
        "cutoff_bucket": {
            m: cutoff_bucket(first_filed_max, cut) for m, cut in MODEL_CUTOFFS.items()
        },
        "restated": restated,
        "restated_detail": detail,
        "derived_q4": any(f.derived for f in c.facts),
    }


def is_after_cutoff(c: Candidate) -> bool:
    return fairness(c)["cutoff_bucket"]["claude-sonnet-5-5"] == "after"


# ---------------------------------------------------------------- templates (D083)


def quarter_label(fp: str, fy: int) -> str:
    return f"fiscal {fp} {fy}" if fp != "FY" else f"fiscal {fy}"


def lookup_question(f: Fact) -> str:
    name, phrase = NAMES[f.ticker], PHRASES[f.metric]
    if f.period_type == "instant":
        verb = "were" if f.metric == "total_assets" else "was"
        return (
            f"What {verb} {name}'s {phrase} at the end of fiscal {f.fiscal_period} {f.fiscal_year}?"
        )
    return f"What was {name}'s {phrase} in {quarter_label(f.fiscal_period, f.fiscal_year)}?"


def unit_of(metric: str) -> str:
    return "USD/shares" if metric == "eps_diluted" else "USD"


def candidates(facts: list[Fact]) -> dict[str, list[Candidate]]:
    """Every answerable combination per template; missing data is simply never generated."""
    if EXCLUDE_MIXED_VINTAGE:
        facts = [f for f in facts if not f.mixed_vintage]
    by = {(f.ticker, f.metric, f.fiscal_year, f.fiscal_period, f.period_type): f for f in facts}
    out: dict[str, list[Candidate]] = defaultdict(list)

    def one(fid: str) -> Callable[[dict[str, Decimal]], Decimal]:
        return lambda v: v[fid]

    for f in facts:
        # lookup: direct facts only (derived values are reserved for derived_q4).
        if not f.derived and f.metric in (*FLOW_METRICS, "eps_diluted", *INSTANT_METRICS):
            if f.period_type != "instant" or f.metric in INSTANT_METRICS:
                out["lookup"].append(
                    Candidate(
                        "lookup",
                        lookup_question(f),
                        unit_of(f.metric),
                        (f.ticker,),
                        f.metric,
                        ((f.fiscal_year, f.fiscal_period),),
                        (f,),
                        one(f.fact_id),
                        "fact value",
                    )
                )
        # derived_q4: only where derived = TRUE (SPEC §13.1).
        if f.derived and f.period_type == "quarter" and f.fiscal_period == "Q4":
            q = f"What was {NAMES[f.ticker]}'s {PHRASES[f.metric]} in fiscal Q4 {f.fiscal_year}?"
            out["derived_q4"].append(
                Candidate(
                    "derived_q4",
                    q,
                    "USD",
                    (f.ticker,),
                    f.metric,
                    ((f.fiscal_year, "Q4"),),
                    (f,),
                    one(f.fact_id),
                    "derived Q4 = FY - 9M (stored derivation)",
                )
            )
        # yoy_growth: annual pairs, positive base.
        if f.period_type == "annual" and f.metric in (*FLOW_METRICS, "eps_diluted"):
            old = by.get((f.ticker, f.metric, f.fiscal_year - 1, "FY", "annual"))
            if old is not None and old.value > 0:
                q = (
                    f"By what percent did {NAMES[f.ticker]}'s {PHRASES[f.metric]} change from "
                    f"fiscal {f.fiscal_year - 1} to fiscal {f.fiscal_year}?"
                )
                out["yoy_growth"].append(
                    Candidate(
                        "yoy_growth",
                        q,
                        "percent",
                        (f.ticker,),
                        f.metric,
                        ((f.fiscal_year - 1, "FY"), (f.fiscal_year, "FY")),
                        (old, f),
                        lambda v, n=f.fact_id, o=old.fact_id: growth(v[n], v[o]),
                        "(FY - FY_prev) / FY_prev * 100",
                    )
                )
        # margin: quarter numerator over revenue of the same quarter.
        if f.metric in MARGINS and f.period_type == "quarter":
            rev = by.get((f.ticker, "revenue", f.fiscal_year, f.fiscal_period, "quarter"))
            if rev is not None and rev.value > 0:
                q = (
                    f"What was {NAMES[f.ticker]}'s {MARGINS[f.metric]} margin in fiscal "
                    f"{f.fiscal_period} {f.fiscal_year}?"
                )
                out["margin"].append(
                    Candidate(
                        "margin",
                        q,
                        "percent",
                        (f.ticker,),
                        f"{MARGINS[f.metric]}_margin",
                        ((f.fiscal_year, f.fiscal_period),),
                        (f, rev),
                        lambda v, n=f.fact_id, r=rev.fact_id: pct(v[n], v[r]),
                        f"{f.metric} / revenue * 100",
                    )
                )
        # multi_step: Q1 to derived Q4 growth, same fiscal year.
        if f.derived and f.period_type == "quarter" and f.fiscal_period == "Q4":
            q1 = by.get((f.ticker, f.metric, f.fiscal_year, "Q1", "quarter"))
            if q1 is not None and q1.value > 0:
                q = (
                    f"By what percent did {NAMES[f.ticker]}'s {PHRASES[f.metric]} change from "
                    f"fiscal Q1 {f.fiscal_year} to fiscal Q4 {f.fiscal_year}?"
                )
                out["multi_step"].append(
                    Candidate(
                        "multi_step",
                        q,
                        "percent",
                        (f.ticker,),
                        f.metric,
                        ((f.fiscal_year, "Q1"), (f.fiscal_year, "Q4")),
                        (q1, f),
                        lambda v, a=q1.fact_id, b=f.fact_id: growth(v[b], v[a]),
                        "(Q4_derived - Q1) / Q1 * 100",
                    )
                )
    # trend_avg: all four quarters of a fiscal year (Q4 may be derived).
    quarters: dict[tuple[str, str, int], dict[str, Fact]] = defaultdict(dict)
    for f in facts:
        if f.period_type == "quarter" and f.metric in FLOW_METRICS:
            quarters[(f.ticker, f.metric, f.fiscal_year)][f.fiscal_period] = f
    for (ticker, metric, fy), qs in quarters.items():
        if set(qs) == {"Q1", "Q2", "Q3", "Q4"}:
            used = tuple(qs[p] for p in ("Q1", "Q2", "Q3", "Q4"))
            q = f"What was {NAMES[ticker]}'s average quarterly {PHRASES[metric]} over fiscal {fy}?"
            out["trend_avg"].append(
                Candidate(
                    "trend_avg",
                    q,
                    "USD",
                    (ticker,),
                    metric,
                    ((fy, "FY"),),
                    used,
                    lambda v, ids=tuple(x.fact_id for x in used): mean([v[i] for i in ids]),
                    "(Q1 + Q2 + Q3 + Q4) / 4",
                )
            )
    # comparison: annual margins of two same-sector companies with the same fiscal-year number.
    annual: dict[tuple[str, int], list[tuple[Fact, Fact]]] = defaultdict(list)
    for f in facts:
        if f.metric in MARGINS and f.period_type == "annual":
            rev = by.get((f.ticker, "revenue", f.fiscal_year, "FY", "annual"))
            if rev is not None and rev.value > 0:
                annual[(f.metric, f.fiscal_year)].append((f, rev))
    for (metric, fy), rows in annual.items():
        rows.sort(key=lambda r: r[0].ticker)
        for i, (na, ra) in enumerate(rows):
            for nb, rb in rows[i + 1 :]:
                if SECTORS[na.ticker] != SECTORS[nb.ticker]:
                    continue  # D101: same sector only
                if (na.ticker in BANKS) != (nb.ticker in BANKS):
                    continue  # never a bank against a non-bank, whatever the sector table says
                gap = abs(pct(na.value, ra.value) - pct(nb.value, rb.value))
                if gap < MIN_COMPARISON_GAP:
                    continue  # too close to call (D083)
                a, b = (na, ra), (nb, rb)
                order = hashlib.sha256(f"{SEED}|{na.ticker}|{nb.ticker}|{metric}|{fy}".encode())
                if order.digest()[0] % 2:
                    a, b = b, a
                (an, ar), (bn, br) = a, b
                q = (
                    f"Which had the higher {MARGINS[metric]} margin in fiscal {fy}, "
                    f"{NAMES[an.ticker]} or {NAMES[bn.ticker]}, and by how many percentage "
                    "points?"
                )
                ids = (an.fact_id, ar.fact_id, bn.fact_id, br.fact_id)
                out["comparison"].append(
                    Candidate(
                        "comparison",
                        q,
                        "percentage_points",
                        (an.ticker, bn.ticker),
                        f"{MARGINS[metric]}_margin",
                        ((fy, "FY"),),
                        (an, ar, bn, br),
                        lambda v, i=ids: abs(pct(v[i[0]], v[i[1]]) - pct(v[i[2]], v[i[3]])),
                        f"|{metric}_A / revenue_A - {metric}_B / revenue_B| * 100",
                        choice_from=lambda v, i=ids, t=(an.ticker, bn.ticker): (
                            t[0] if pct(v[i[0]], v[i[1]]) > pct(v[i[2]], v[i[3]]) else t[1]
                        ),
                    )
                )
    return out


# ---------------------------------------------------------------- selection and split


def _rank(seed: int, *parts: str) -> str:
    return hashlib.sha256("|".join([str(seed), *parts]).encode()).hexdigest()


def sector_of(c: Candidate) -> str:
    return SECTORS[c.companies[0]]


def balanced_pick(
    pool: list[Candidate], n: int, counts: dict[str, Counter], seed: int, by_sector: bool = False
) -> list[Candidate]:
    """Greedy: always take the candidate whose company, then metric, then year is least used.

    With by_sector (comparison, D101) the least-used sector comes first, so sectors fill evenly
    until a small sector's pool runs out."""
    remaining = sorted(pool, key=lambda c: _rank(seed, c.id))
    picked: list[Candidate] = []
    while remaining and len(picked) < n:
        best = min(
            remaining,
            key=lambda c: (
                counts["sector"][sector_of(c)] if by_sector else 0,
                max(counts["company"][t] for t in c.companies),
                counts["metric"][c.metric],
                counts["year"][c.periods[-1][0]],
                _rank(seed, c.id),
            ),
        )
        remaining.remove(best)
        picked.append(best)
        if by_sector:
            counts["sector"][sector_of(best)] += 1
        for t in best.companies:
            counts["company"][t] += 1
        counts["metric"][best.metric] += 1
        counts["year"][best.periods[-1][0]] += 1
    return picked


def select(pools: dict[str, list[Candidate]], seed: int = SEED) -> dict[str, list[Candidate]]:
    chosen: dict[str, list[Candidate]] = {}
    for template, n in TARGETS.items():
        pool = list({c.id: c for c in pools.get(template, [])}.values())
        counts: dict[str, Counter] = {
            "sector": Counter(),
            "company": Counter(),
            "metric": Counter(),
            "year": Counter(),
        }
        by_sector = template == "comparison"
        after = [c for c in pool if is_after_cutoff(c)]
        floor = min(len(after), math.ceil(POST_CUTOFF_FLOOR * n))
        picked = balanced_pick(after, floor, counts, seed, by_sector)  # D086 post-cutoff floor
        taken = {c.id for c in picked}
        picked += balanced_pick(
            [c for c in pool if c.id not in taken], n - len(picked), counts, seed, by_sector
        )
        chosen[template] = picked
    return chosen


def split(chosen: dict[str, list[Candidate]], seed: int = SEED) -> dict[str, str]:
    """30/70 dev/test per template, ordered by SHA-256(seed, id) (D084)."""
    out = {}
    for items in chosen.values():
        ordered = sorted(items, key=lambda c: _rank(seed, "split", c.id))
        n_dev = int((DEV_SHARE * len(ordered)).to_integral_value(rounding=ROUND_HALF_EVEN))
        for i, c in enumerate(ordered):
            out[c.id] = "dev" if i < n_dev else "test"
    return out


def sample(
    chosen: dict[str, list[Candidate]],
    splits: dict[str, str],
    size: int = SAMPLE_SIZE,
    seed: int = SEED,
) -> set[str]:
    """One stratified test sample for B1/B2, largest-remainder allocation by template."""
    tests = {t: [c for c in items if splits[c.id] == "test"] for t, items in chosen.items()}
    total = sum(len(v) for v in tests.values())
    quotas = {t: Decimal(size * len(v)) / Decimal(total) for t, v in tests.items()}
    alloc = {t: int(q) for t, q in quotas.items()}
    for t in sorted(quotas, key=lambda t: (-(quotas[t] - alloc[t]), t))[
        : size - sum(alloc.values())
    ]:
        alloc[t] += 1
    ids: set[str] = set()
    for t, items in tests.items():
        ordered = sorted(items, key=lambda c: _rank(seed, "sample", c.id))
        ids.update(c.id for c in ordered[: alloc[t]])
    return ids


def tolerance(unit: str) -> dict[str, str]:
    if unit == "USD/shares":
        return {"kind": "eps", "relative": "0.005", "absolute": "0.005"}
    if unit in ("percent", "percentage_points"):
        return {"kind": "absolute", "value": "0.1"}
    return {"kind": "relative", "value": "0.005"}


def record(c: Candidate, split_name: str, in_sample: bool) -> dict[str, Any]:
    ratio = c.unit in ("percent", "percentage_points")
    urls = sorted({u for f in c.facts for u in (f.url, *f.input_urls) if u})
    return {
        "id": c.id,
        "template": c.template,
        "question": c.question,
        "gold_value": fixed(c.gold, ratio),
        "gold_unit": c.unit,
        "gold_choice": c.gold_choice,
        "gold_status": "answered",
        "tolerance": tolerance(c.unit),
        "companies": list(c.companies),
        "metric": c.metric,
        "periods": [{"fiscal_year": y, "fiscal_period": p} for y, p in c.periods],
        "gold_fact_ids": [f.fact_id for f in c.facts],
        "computation": {
            "formula": c.formula,
            "inputs": [
                {
                    "fact_id": f.fact_id,
                    "ticker": f.ticker,
                    "metric": f.metric,
                    "fiscal_year": f.fiscal_year,
                    "fiscal_period": f.fiscal_period,
                    "period": f"{f.start or '-'} to {f.end}",
                    "value": format(f.value, "f"),
                    "unit": f.unit,
                    "concept": f.concept,
                    "derived": f.derived,
                    "source_accession": f.accession,
                    "source_filed": f.filed,
                    "derivation_inputs": [
                        {
                            k: item.get(k)
                            for k in (
                                "coefficient",
                                "value",
                                "concept",
                                "start",
                                "end",
                                "accession",
                                "filed",
                            )
                        }
                        for item in f.inputs
                    ],
                }
                for f in c.facts
            ],
        },
        "source_urls": urls,
        "fairness": fairness(c),
        "split": split_name,
        "sample_100": in_sample,
        "snapshot_id": SNAPSHOT_ID,
        "generator_version": GENERATOR_VERSION,
    }


# ---------------------------------------------------------------- abstention probe (D083)


def probe_records(facts: list[Fact]) -> list[dict[str, Any]]:
    """~10 status-only questions: banks' gross profit/margin (not applicable) and operating
    income (no standard fact), on periods that exist in the snapshot for those banks."""
    periods = sorted(
        {
            (f.ticker, f.fiscal_year, f.fiscal_period, f.period_type)
            for f in facts
            if f.ticker in BANKS and f.metric == "net_income"
        },
        key=lambda p: (p[0], p[1], p[2]),
    )
    out = []
    for ticker in BANKS:
        mine = [p for p in periods if p[0] == ticker]
        annual = [p for p in mine if p[3] == "annual"][-2:]
        quarter = [p for p in mine if p[3] == "quarter"][-3:]
        if not annual or not quarter:
            continue  # no periods in the snapshot for this bank
        for (_, fy, fp, _), metric, status in [
            (annual[-1], "gross_margin", "not_applicable"),
            (quarter[-1], "gross_profit", "not_applicable"),
            (annual[0], "gross_profit", "not_applicable"),
            (quarter[0], "operating_income", "unavailable"),
            (annual[-1], "operating_income", "unavailable"),
        ]:
            label = quarter_label(fp, fy)
            question = (
                f"What was {NAMES[ticker]}'s gross margin in {label}?"
                if metric == "gross_margin"
                else f"What was {NAMES[ticker]}'s {PHRASES[metric]} in {label}?"
            )
            key = f"probe|{ticker}|{metric}|{fy}{fp}"
            out.append(
                {
                    "id": "p_" + hashlib.sha256(key.encode()).hexdigest()[:16],
                    "template": "abstention_probe",
                    "question": question,
                    "gold_value": None,
                    "gold_unit": None,
                    "gold_choice": None,
                    "gold_status": status,
                    "tolerance": None,
                    "companies": [ticker],
                    "metric": metric,
                    "periods": [{"fiscal_year": fy, "fiscal_period": fp}],
                    "gold_fact_ids": [],
                    "computation": None,
                    "source_urls": [],
                    "fairness": None,
                    "split": "probe",
                    "sample_100": False,
                    "snapshot_id": SNAPSHOT_ID,
                    "generator_version": GENERATOR_VERSION,
                }
            )
    return out


# ---------------------------------------------------------------- loading (read-only)


def _body(raw_dir: Path, url: str) -> bytes | None:
    path = raw_dir / SNAPSHOT_ID / (hashlib.sha256(url.encode()).hexdigest() + ".body")
    if not path.exists():
        return None
    data = path.read_bytes()
    try:
        return gzip.decompress(data)
    except OSError:
        return data


class FirstReported:
    """Earliest-filed observation per (cik, concept, unit, start, end) within the cutoff."""

    def __init__(self, raw_dir: Path) -> None:
        self.raw_dir = raw_dir
        self.cache: dict[str, dict] = {}

    def lookup(
        self, cik: str, concept: str, unit: str, start: str | None, end: str
    ) -> Observation | None:
        if cik not in self.cache:
            body = _body(self.raw_dir, f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json")
            self.cache[cik] = json.loads(body) if body else {}
        units = (
            self.cache[cik].get("facts", {}).get("us-gaap", {}).get(concept, {}).get("units", {})
        )
        observations = [
            o
            for o in units.get(unit, [])
            if o.get("end") == end
            and o.get("start") == start
            and o.get("form") in ("10-K", "10-Q", "10-K/A", "10-Q/A")
            and o.get("filed", "") <= INGESTION_CUTOFF
        ]
        if not observations:
            return None
        first = min(observations, key=lambda o: (o["filed"], o["accn"]))
        return Observation(Decimal(str(first["val"])), first["filed"], first["accn"])


def load_facts(database_url: str, raw_dir: Path) -> list[Fact]:
    import psycopg

    from filinglens.db import connection_options

    with psycopg.connect(database_url, **connection_options(database_url)) as conn:
        conn.execute("SET default_transaction_read_only = on")
        rows = conn.execute(
            """SELECT f.id, c.ticker, f.cik, f.metric, f.concept, f.period_type, f.start_date,
                      f.end_date, f.fiscal_year, f.fiscal_period, f.value, f.unit, f.derived,
                      f.source_accession, f.source_filed, fl.url, f.derivation_inputs
               FROM financial_facts f JOIN companies c USING (cik)
               LEFT JOIN filings fl ON fl.accession = f.source_accession
               WHERE f.snapshot_id = %s ORDER BY f.id""",
            (SNAPSHOT_ID,),
        ).fetchall()
        urls = dict(conn.execute("SELECT accession, url FROM filings").fetchall())
    first = FirstReported(raw_dir)
    facts = []
    for (
        fid,
        ticker,
        cik,
        metric,
        concept,
        ptype,
        start,
        end,
        fy,
        fp,
        value,
        unit,
        derived,
        accession,
        filed,
        url,
        inputs,
    ) in rows:
        start_s = start.isoformat() if start else None
        end_s = end.isoformat()
        enriched = []
        for item in inputs or []:
            obs = first.lookup(cik, item["concept"], item["unit"], item.get("start"), item["end"])
            enriched.append(
                item
                | {
                    "first_value": str(obs.value) if obs else None,
                    "first_filed": obs.filed if obs else None,
                }
            )
        obs = None if derived else first.lookup(cik, concept, unit, start_s, end_s)
        input_urls = tuple(urls[i["accession"]] for i in inputs or [] if i.get("accession") in urls)
        facts.append(
            Fact(
                fact_id=str(fid),
                ticker=ticker,
                cik=cik,
                metric=metric,
                concept=concept,
                period_type=ptype,
                start=start_s,
                end=end_s,
                fiscal_year=fy,
                fiscal_period=fp,
                value=Decimal(value),
                unit=unit,
                derived=derived,
                accession=accession,
                filed=filed.isoformat() if isinstance(filed, date) else str(filed),
                url=url,
                inputs=tuple(enriched),
                first_value=obs.value if obs else None,
                first_filed=obs.filed if obs else None,
                input_urls=input_urls,
            )
        )
    return facts


# ---------------------------------------------------------------- build, write, freeze


def build(facts: list[Fact], seed: int = SEED) -> list[dict[str, Any]]:
    chosen = select(candidates(facts), seed)
    splits = split(chosen, seed)
    in_sample = sample(chosen, splits, seed=seed)
    records = [
        record(c, splits[c.id], c.id in in_sample) for items in chosen.values() for c in items
    ]
    records += probe_records(facts)
    return sorted(records, key=lambda r: r["id"])


def dumps(records: list[dict[str, Any]]) -> str:
    return "".join(json.dumps(r, sort_keys=True, ensure_ascii=False) + "\n" for r in records)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_draft(records: list[dict[str, Any]], path: Path = DRAFT_PATH) -> Path:
    if FROZEN_PATH.exists() and path == FROZEN_PATH:
        raise FileExistsError("questions_v1 is frozen; generate a new version instead (D084)")
    path.write_text(dumps(records), encoding="utf-8", newline="\n")
    return path


def freeze(
    draft: Path = DRAFT_PATH, frozen: Path = FROZEN_PATH, manifest: Path = MANIFEST_PATH
) -> dict[str, Any]:
    """Promote the approved draft; refuses to overwrite a frozen set (D084)."""
    if frozen.exists() or manifest.exists():
        raise FileExistsError(f"{frozen.name} is frozen and is never regenerated in place")
    data = draft.read_bytes()
    records = [json.loads(line) for line in data.decode("utf-8").splitlines()]
    frozen.write_bytes(data)
    info = {
        "file": frozen.name,
        "sha256": hashlib.sha256(data).hexdigest(),
        "sample_100_sha256": hashlib.sha256(
            "\n".join(sorted(r["id"] for r in records if r["sample_100"])).encode()
        ).hexdigest(),
        "counts": dict(Counter(f"{r['template']}:{r['split']}" for r in records)),
        "seed": SEED,
        "generator_version": GENERATOR_VERSION,
        "snapshot_id": SNAPSHOT_ID,
        "b2_meta_sha256": sha256_file(B2_META_PATH) if B2_META_PATH.exists() else None,
    }
    manifest.write_text(json.dumps(info, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return info


def load_frozen(path: Path = FROZEN_PATH, manifest: Path = MANIFEST_PATH) -> list[dict[str, Any]]:
    """Read the frozen set after checking its hash against the manifest."""
    expected = json.loads(manifest.read_text(encoding="utf-8"))["sha256"]
    if sha256_file(path) != expected:
        raise ValueError(f"{path.name} does not match its frozen manifest hash")
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def ids_sha256(ids: list[str]) -> str:
    return hashlib.sha256("\n".join(sorted(ids)).encode()).hexdigest()


def subset(records: list[dict[str, Any]], size: int = SUBSET_SIZE, seed: int = SEED) -> list[str]:
    """The approved test subset (D105): the frozen 100-question sample plus a seeded share of
    the other test questions, so that each template gets its largest-remainder share of size."""
    test = [r for r in records if r["split"] == "test"]
    counts = Counter(r["template"] for r in test)
    quotas = {t: Decimal(size * n) / Decimal(len(test)) for t, n in counts.items()}
    target = {t: int(q) for t, q in quotas.items()}
    for t in sorted(quotas, key=lambda t: (-(quotas[t] - target[t]), t))[
        : size - sum(target.values())
    ]:
        target[t] += 1
    ids = [r["id"] for r in test if r["sample_100"]]
    for t in sorted(counts):
        have = sum(r["sample_100"] for r in test if r["template"] == t)
        rest = sorted(
            (r["id"] for r in test if r["template"] == t and not r["sample_100"]),
            key=lambda i: _rank(seed, "subset", i),
        )
        if target[t] < have:
            raise ValueError(f"{t}: the sample already exceeds its subset share")
        ids += rest[: target[t] - have]
    return sorted(ids)


def freeze_subset(path: Path = SUBSET_PATH, size: int = SUBSET_SIZE) -> dict[str, Any]:
    """Write the subset ID list once, tied to the frozen set's hash; never overwritten (D105)."""
    if path.exists():
        raise FileExistsError(f"{path.name} is frozen and is never regenerated in place")
    records = load_frozen()
    ids = subset(records, size)
    by_id = {r["id"]: r for r in records}
    info = {
        "ids": ids,
        "ids_sha256": ids_sha256(ids),
        "size": len(ids),
        "seed": SEED,
        "includes_sample_100": True,
        "per_template": dict(sorted(Counter(by_id[i]["template"] for i in ids).items())),
        "questions_sha256": sha256_file(FROZEN_PATH),
    }
    path.write_text(json.dumps(info, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return info


def main(argv: list[str] | None = None) -> None:
    from filinglens.config import Settings

    parser = argparse.ArgumentParser(description="Generate or freeze benchmark questions v1.")
    parser.add_argument("command", choices=["draft", "b2meta", "freeze", "subset"])
    args = parser.parse_args(argv)
    if args.command == "freeze":
        print(json.dumps(freeze(), indent=2))
        return
    if args.command == "subset":
        info = freeze_subset()
        print(json.dumps({k: v for k, v in info.items() if k != "ids"}, indent=2))
        return
    settings = Settings()
    if args.command == "b2meta":  # B2 context metadata for the draft's 100-question sample
        from evals.b2_context import build_meta, write_meta

        records = [json.loads(line) for line in DRAFT_PATH.read_text(encoding="utf-8").splitlines()]
        path = write_meta(build_meta(records, settings.database_url, settings.raw_dir, SNAPSHOT_ID))
        print(f"wrote {path}")
        return
    records = build(load_facts(settings.database_url, settings.raw_dir))
    path = write_draft(records)
    print(f"wrote {len(records)} records to {path}")


if __name__ == "__main__":
    main()

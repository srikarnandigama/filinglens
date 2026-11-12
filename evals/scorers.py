"""Scoring and statistics shared by the system and every baseline (SPEC §13.4; D085, D094)."""

import math
import random
import re
from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

SCALES = {
    "": Decimal(1),
    "usd": Decimal(1),
    "dollars": Decimal(1),
    "thousand": Decimal(10) ** 3,
    "thousands": Decimal(10) ** 3,
    "k": Decimal(10) ** 3,
    "million": Decimal(10) ** 6,
    "millions": Decimal(10) ** 6,
    "m": Decimal(10) ** 6,
    "mm": Decimal(10) ** 6,
    "mn": Decimal(10) ** 6,
    "billion": Decimal(10) ** 9,
    "billions": Decimal(10) ** 9,
    "b": Decimal(10) ** 9,
    "bn": Decimal(10) ** 9,
}
PERCENT = {"percent", "%", "pct", "percentage", "percent_change"}
FRACTION = {"fraction", "ratio", "decimal"}
POINTS = {"percentage_points", "percentage points", "pp", "points", "ppt", "pts"}
PER_SHARE = {
    "usd/share",
    "usd/shares",
    "usd per share",
    "per share",
    "$/share",
    "dollars per share",
}


@dataclass
class Score:
    correct: bool
    outcome: str  # correct | wrong | abstained | parse_failure | error
    normalized: str | None = None
    unit_rescue: bool = False
    detail: str | None = None


def _words(unit: str) -> str:
    text = unit.strip().lower().replace("$", " ").replace("usd", " usd ")
    return re.sub(r"\s+", " ", text).strip()


def normalize(value: Decimal, unit: str | None, gold_unit: str) -> Decimal | None:
    """Convert a predicted value into the gold's base unit; None when the units do not fit."""
    u = (unit or "").strip().lower()
    if gold_unit in ("percent", "percentage_points"):
        if u in FRACTION:
            return value * 100
        if u in PERCENT or u in POINTS or u == "":
            return value
        return None
    if gold_unit == "USD/shares":
        return value if (u in PER_SHARE or u in ("", "usd", "dollars")) else None
    words = _words(u)
    if any(w in words for w in ("share", "percent", "point")):
        return None
    scale_words = [w for w in words.split() if w != "usd"]
    if len(scale_words) > 1:
        return None
    scale = SCALES.get(scale_words[0] if scale_words else "")
    return None if scale is None else value * scale


def within(pred: Decimal, gold: Decimal, tolerance: dict[str, str]) -> bool:
    error = abs(pred - gold)
    kind = tolerance["kind"]
    if kind == "relative":
        return error <= Decimal(tolerance["value"]) * abs(gold)
    if kind == "absolute":
        return error <= Decimal(tolerance["value"])
    if kind == "eps":
        limit = max(Decimal(tolerance["relative"]) * abs(gold), Decimal(tolerance["absolute"]))
        return error <= limit
    raise ValueError(f"unknown tolerance kind {kind}")


def score(
    question: dict[str, Any], prediction: dict[str, Any] | None, error: str | None = None
) -> Score:
    """numeric_correct for one question (comparison also needs the right company)."""
    if error:
        return Score(False, "error", detail=error)
    if prediction is None or not prediction.get("parse_ok"):
        return Score(False, "parse_failure", detail=(prediction or {}).get("parse_error"))
    status = prediction.get("status")
    if question["template"] == "abstention_probe":
        ok = status in ("not_available", "not_applicable")
        return Score(ok, "correct" if ok else "wrong", detail=f"status {status}")
    if status in ("not_available", "not_applicable"):
        return Score(False, "abstained", detail=status)
    gold = Decimal(question["gold_value"])
    value = Decimal(prediction["value"])
    unit = question["gold_unit"]
    if unit == "percentage_points":  # comparison: magnitude, plus the choice
        value = abs(value)
    normalized = normalize(value, prediction.get("unit"), unit)
    rescue = False
    if normalized is None or not within(normalized, gold, question["tolerance"]):
        candidates = [
            value * s
            for s in (
                Decimal(1),
                Decimal(10) ** 3,
                Decimal(10) ** 6,
                Decimal(10) ** 9,
                Decimal(100),
            )
        ]
        rescue = any(within(c, gold, question["tolerance"]) for c in candidates)
        return Score(
            False,
            "wrong",
            None if normalized is None else format(normalized, "f"),
            unit_rescue=rescue,
            detail="unit not recognized" if normalized is None else None,
        )
    if question.get("gold_choice") and prediction.get("choice") != question["gold_choice"]:
        return Score(
            False, "wrong", format(normalized, "f"), detail=f"choice {prediction.get('choice')}"
        )
    return Score(True, "correct", format(normalized, "f"))


# ---------------------------------------------------------------- statistics (D094)


def bootstrap_ci(
    outcomes: Sequence[bool], resamples: int = 10_000, seed: int = 20261109, level: float = 0.95
) -> tuple[float, float, float]:
    """Accuracy with a percentile bootstrap CI."""
    n = len(outcomes)
    if n == 0:
        return (math.nan, math.nan, math.nan)
    rng = random.Random(seed)
    values = [1 if o else 0 for o in outcomes]
    means = sorted(sum(rng.choices(values, k=n)) / n for _ in range(resamples))
    lo = means[int((1 - level) / 2 * resamples)]
    hi = means[min(resamples - 1, int((1 + level) / 2 * resamples))]
    return (sum(values) / n, lo, hi)


def bootstrap_mean_ci(
    values: Sequence[float], resamples: int = 10_000, seed: int = 20261109, level: float = 0.95
) -> tuple[float, float, float]:
    """Mean with a percentile bootstrap CI (judge scores 1-5)."""
    n = len(values)
    if n == 0:
        return (math.nan, math.nan, math.nan)
    rng = random.Random(seed)
    means = sorted(sum(rng.choices(values, k=n)) / n for _ in range(resamples))
    lo = means[int((1 - level) / 2 * resamples)]
    hi = means[min(resamples - 1, int((1 + level) / 2 * resamples))]
    return (sum(values) / n, lo, hi)


def paired_diff_ci(
    a: Sequence[bool], b: Sequence[bool], resamples: int = 10_000, seed: int = 20261109
) -> tuple[float, float, float]:
    """Accuracy difference a - b on the same questions, with a paired bootstrap CI."""
    n = len(a)
    if n == 0 or n != len(b):
        raise ValueError("paired outcomes must be non-empty and the same length")
    rng = random.Random(seed)
    pairs = list(zip(a, b, strict=True))
    diffs = sorted(sum(x - y for x, y in rng.choices(pairs, k=n)) / n for _ in range(resamples))
    return (
        sum(x - y for x, y in pairs) / n,
        diffs[int(0.025 * resamples)],
        diffs[min(resamples - 1, int(0.975 * resamples))],
    )


def mcnemar_exact(a: Sequence[bool], b: Sequence[bool]) -> tuple[int, int, float]:
    """Exact two-sided McNemar test: (a right/b wrong, a wrong/b right, p-value)."""
    only_a = sum(1 for x, y in zip(a, b, strict=True) if x and not y)
    only_b = sum(1 for x, y in zip(a, b, strict=True) if y and not x)
    n = only_a + only_b
    if n == 0:
        return (0, 0, 1.0)
    k = min(only_a, only_b)
    tail = sum(math.comb(n, i) for i in range(k + 1)) / 2**n
    return (only_a, only_b, min(1.0, 2 * tail))


def holm(pvalues: dict[str, float]) -> dict[str, float]:
    """Holm-adjusted p-values (step-down, monotone)."""
    ordered = sorted(pvalues.items(), key=lambda kv: kv[1])
    m = len(ordered)
    adjusted, running = {}, 0.0
    for i, (name, p) in enumerate(ordered):
        running = max(running, min(1.0, (m - i) * p))
        adjusted[name] = running
    return adjusted


def percentile(values: Sequence[float], q: float) -> float:
    if not values:
        return math.nan
    ordered = sorted(values)
    rank = q * (len(ordered) - 1)
    low, high = math.floor(rank), math.ceil(rank)
    return ordered[low] + (ordered[high] - ordered[low]) * (rank - low)


def weighted_kappa(
    a: Sequence[int], b: Sequence[int], categories: Sequence[int] = (1, 2, 3, 4, 5)
) -> float:
    """Quadratic-weighted Cohen's kappa for judge-human calibration (D093)."""
    k = len(categories)
    index = {c: i for i, c in enumerate(categories)}
    n = len(a)
    if n == 0:
        return math.nan
    observed = [[0.0] * k for _ in range(k)]
    for x, y in zip(a, b, strict=True):
        observed[index[x]][index[y]] += 1
    row = [sum(r) for r in observed]
    col = [sum(observed[i][j] for i in range(k)) for j in range(k)]
    num = den = 0.0
    for i in range(k):
        for j in range(k):
            w = (i - j) ** 2 / (k - 1) ** 2
            num += w * observed[i][j]
            den += w * row[i] * col[j] / n
    return 1.0 - num / den if den else 1.0

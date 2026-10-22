"""Six auditable Decimal tools, served through the official MCP v2 SDK."""

from decimal import Decimal

from mcp_servers.decimal_math import Expression, ToolFailure, change, computed, fixed, number
from mcp_servers.models import (
    CagrData,
    CagrInput,
    ChangePoint,
    EvaluateInput,
    EvaluationData,
    GrowthData,
    GrowthRateInput,
    LabeledValue,
    MarginData,
    MarginInput,
    Numeric,
    StatsData,
    SummaryStatsInput,
    YoyData,
    YoySeriesInput,
)
from mcp_servers.runtime import ContractServer, serve


def growth_rate(old: Numeric, new: Numeric) -> GrowthData:
    """Compute one percentage change: 100*(new-old)/abs(old). Use yoy_series for
    consecutive comparable periods, or cagr for compounded annual growth. Negative
    bases are allowed: improvement from a loss to profit is positive. Zero old is
    DIVISION_BY_ZERO; this is not a percentage-point difference.

    Pass exact decimal strings from EDGAR, or JSON numbers; strings preserve source
    precision. Use compatible units/periods. Return input strings and value_pct
    (25.3 means 25.3%), rounded to 12 decimal places, half-even. INVALID_INPUT rejects
    booleans/nonfinite values; NUMERIC_RANGE identifies exceeded bounds. Missing or
    not-applicable data must never be supplied as zero.
    """
    a, b = number(old), number(new)
    return GrowthData(old=fixed(a), new=fixed(b), value_pct=computed(change(a, b)))


def margin(numerator: Numeric, denominator: Numeric) -> MarginData:
    """Compute 100*numerator/denominator; use growth_rate for changes instead.
    Fetch compatible same-period financial facts first. For gross/operating/net
    margins, use the corresponding profit and revenue, both in raw USD, not display
    millions. Pass exact decimal strings unchanged from EDGAR, or JSON numbers.

    Return input strings and value_pct: 25.3 means 25.3%, rounded to 12 decimal
    places, half-even. Negative signs are preserved; denominator zero gives
    DIVISION_BY_ZERO. Unavailable means missing data, while not_applicable requires
    evidence; neither permits a synthesized bank gross margin or zero substitution.
    INVALID_INPUT rejects booleans/nonfinite values; NUMERIC_RANGE reports bounds.
    """
    a, b = number(numerator), number(denominator)
    if not b:
        raise ToolFailure("DIVISION_BY_ZERO", "Margin denominator must be nonzero.")
    return MarginData(numerator=fixed(a), denominator=fixed(b), value_pct=computed(a / b * 100))


def cagr(start_value: Numeric, end_value: Numeric, years: Numeric) -> CagrData:
    """Compute compounded annual growth: 100*((end/start)**(1/years)-1), using
    Decimal power. Use growth_rate for simple change and yoy_series for individual
    comparisons. Supply comparable endpoints and elapsed years, not fiscal-year
    labels or a count of quarters; positive fractional years are allowed.

    Both endpoints must be positive (NON_POSITIVE_INPUT); years must be >0 and
    <=1000 (INVALID_YEARS). Prefer exact decimal strings; JSON numbers are accepted
    through Decimal(str(x)). Return input strings and value_pct (25.3 means 25.3%),
    rounded to 12 decimal places, half-even. Intermediate changes are not measured.
    INVALID_INPUT rejects booleans/nonfinite values; NUMERIC_RANGE reports bounds.
    """
    start, end, duration = number(start_value), number(end_value), number(years)
    if start <= 0 or end <= 0:
        raise ToolFailure("NON_POSITIVE_INPUT", "CAGR endpoints must both be positive.")
    if duration <= 0 or duration > 1000:
        raise ToolFailure("INVALID_YEARS", "Years must be greater than zero and at most 1000.")
    result = ((end / start) ** (Decimal(1) / duration) - 1) * 100
    return CagrData(
        start_value=fixed(start),
        end_value=fixed(end),
        years=fixed(duration),
        value_pct=computed(result),
    )


def yoy_series(values: list[LabeledValue]) -> YoyData:
    """Compute changes between consecutive supplied values, preserving order.
    Use growth_rate for one pair and summary_stats to summarize levels. To mean
    year-over-year, supply annual values or the same fiscal quarter across years;
    adjacent quarters yield quarter-over-quarter changes. No dates, gaps or sorting
    are inferred. Fiscal years mean their ending calendar year, including
    non-December AAPL/MSFT/NVDA/COST/NKE/DIS/WMT/PG.

    Supply 2-1000 distinct labeled decimal strings or JSON numbers. Return ordered
    change_pct values (25.3 means 25.3%); the first is null. Use abs(prior), so
    negative bases are allowed. A zero comparison base fails the entire call with
    DIVISION_BY_ZERO. DUPLICATE_LABEL or INSUFFICIENT_DATA requires corrected inputs.
    Unavailable/not_applicable values cannot be substituted with zero.
    """
    if len({v.label for v in values}) != len(values):
        raise ToolFailure("DUPLICATE_LABEL", "Every series label must be distinct.")
    points = []
    prior = None
    for item in values:
        if not item.label.strip():
            raise ToolFailure("INVALID_INPUT", "Series labels cannot be blank.")
        current = number(item.value)
        if prior == 0:
            raise ToolFailure("DIVISION_BY_ZERO", f"Prior value is zero before label {item.label}.")
        points.append(
            ChangePoint(
                label=item.label,
                value=fixed(current),
                change_pct=computed(change(prior, current)) if prior is not None else None,
                reason="first_observation" if prior is None else None,
            )
        )
        prior = current
    return YoyData(points=points)


def summary_stats(values: list[Numeric]) -> StatsData:
    """Summarize 2-1000 comparable values with mean, median, min, max and sample
    standard deviation (n-1). Use yoy_series for changes and cagr for compounded
    endpoint growth. Negative/repeated values are allowed; missing values are never
    dropped or converted to zero. Supply same-unit decimal strings or JSON numbers.

    Return input/result strings, count and stdev_kind=sample, rounding computed
    outputs to 12 fractional places, half-even. An even-size median averages the
    middle two values. Results retain input units: USD stays raw USD, EPS stays
    USD/shares and percentage inputs remain percentage units. INSUFFICIENT_DATA
    requires at least two observations; INVALID_INPUT/NUMERIC_RANGE requires valid
    finite inputs within the advertised bounds.
    """
    nums = [number(v) for v in values]
    size = len(nums)
    if size < 2:
        raise ToolFailure("INSUFFICIENT_DATA", "Sample statistics require at least two values.")
    ordered = sorted(nums)
    mean = sum(nums, Decimal(0)) / size
    middle = (ordered[(size - 1) // 2] + ordered[size // 2]) / 2
    stdev = (sum(((v - mean) ** 2 for v in nums), Decimal(0)) / (size - 1)).sqrt()
    return StatsData(
        values=[fixed(v) for v in nums],
        count=size,
        mean=computed(mean),
        median=computed(middle),
        min=computed(ordered[0]),
        max=computed(ordered[-1]),
        stdev=computed(stdev),
    )


def evaluate(expression: str) -> EvaluationData:
    """Evaluate explicit decimal arithmetic with + - * /, unary signs and
    parentheses; Unicode minus/multiply/divide are also accepted. Prefer margin,
    growth_rate, cagr or summary_stats when their named semantics fit. No variables,
    function calls, exponent notation/powers, %, // or implicit multiplication are
    allowed. A bounded handwritten parser is used, never eval/exec.

    Limit 512 characters, 128 tokens and nesting/unary depth 32; literals use the
    shared numeric bounds. Return original/normalized expressions and a fixed-point
    value rounded to 12 places, half-even. Units follow the supplied expression;
    no percent conversion is automatic. INVALID_EXPRESSION needs corrected syntax,
    EXPRESSION_LIMIT/NUMERIC_RANGE smaller inputs, and DIVISION_BY_ZERO a nonzero divisor.
    """
    parser = Expression(expression)
    return EvaluationData(
        expression=expression,
        normalized_expression=parser.normalized,
        value=computed(parser.calculate()),
    )


def create_server() -> ContractServer:
    server = ContractServer("quant-mcp", version="1.0.0")
    for fn, inputs, data in [
        (growth_rate, GrowthRateInput, GrowthData),
        (margin, MarginInput, MarginData),
        (cagr, CagrInput, CagrData),
        (yoy_series, YoySeriesInput, YoyData),
        (summary_stats, SummaryStatsInput, StatsData),
        (evaluate, EvaluateInput, EvaluationData),
    ]:
        server.register(fn, inputs, data)
    return server


if __name__ == "__main__":
    serve(create_server())

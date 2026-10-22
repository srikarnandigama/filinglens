"""Pydantic contracts shared by both servers; no network/model loading."""

from datetime import date
from typing import Annotated, Literal

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, model_validator

from mcp_servers.decimal_math import fixed, number

PeriodName = Literal["Q1", "Q2", "Q3", "Q4", "FY"]
Form = Literal["10-K", "10-Q"]
Item = Literal["1", "1A", "7", "7A", "8", "P1-2", "P2-1A"]
Mode = Literal["vector", "keyword", "hybrid", "hybrid_rerank"]
Metric = Literal[
    "revenue",
    "cost_of_revenue",
    "gross_profit",
    "operating_income",
    "net_income",
    "eps_diluted",
    "rnd_expense",
    "operating_cash_flow",
    "capex",
    "total_assets",
    "cash",
]
Status = Literal["available", "unavailable", "not_applicable"]
FiscalYear = Annotated[int, Field(strict=True, ge=1900, le=2200)]
Ticker = Annotated[str, Field(min_length=1, max_length=10, pattern=r"^[A-Za-z][A-Za-z0-9.-]*$")]
Numeric = Annotated[str | int | float, BeforeValidator(lambda value: fixed(number(value)))]
Label = Annotated[str, Field(min_length=1, max_length=128)]


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Input(Model):
    model_config = ConfigDict(extra="forbid", strict=True)


class Period(Input):
    fiscal_year: FiscalYear
    fiscal_period: PeriodName


class ResolveCompanyInput(Input):
    query: Annotated[str, Field(min_length=1, max_length=200)]


class ListFilingsInput(Input):
    ticker: Ticker
    form: Form | None = None
    fiscal_year: FiscalYear | None = None


class GetFinancialMetricInput(Input):
    ticker: Ticker
    metric: Metric
    periods: Annotated[list[Period], Field(min_length=1, max_length=40)]

    @model_validator(mode="after")
    def distinct_periods(self):
        if len({(p.fiscal_year, p.fiscal_period) for p in self.periods}) != len(self.periods):
            raise ValueError("Period requests must be unique.")
        return self


class ListAvailableMetricsInput(Input):
    ticker: Ticker


class SearchFilingsInput(Input):
    query: Annotated[str, Field(min_length=1, max_length=2000)]
    ticker: Ticker | None = None
    fiscal_year: FiscalYear | None = None
    fiscal_period: PeriodName | None = None
    items: Annotated[list[Item], Field(min_length=1, max_length=7)] | None = None
    k: Annotated[int, Field(strict=True, ge=1, le=30)] = 8


class GetPassageInput(Input):
    chunk_id: Annotated[str, Field(pattern=r"^chk_[0-9a-f]{64}$")]


class FilingSectionInput(Input):
    accession: Annotated[str, Field(pattern=r"^[0-9]{10}-[0-9]{2}-[0-9]{6}$")]
    item: Item


class GrowthRateInput(Input):
    old: Numeric
    new: Numeric


class MarginInput(Input):
    numerator: Numeric
    denominator: Numeric


class CagrInput(Input):
    start_value: Numeric
    end_value: Numeric
    years: Numeric


class LabeledValue(Input):
    label: Label
    value: Numeric


class YoySeriesInput(Input):
    values: Annotated[list[LabeledValue], Field(min_length=2, max_length=1000)]


class SummaryStatsInput(Input):
    values: Annotated[list[Numeric], Field(min_length=2, max_length=1000)]


class EvaluateInput(Input):
    expression: Annotated[str, Field(min_length=1, max_length=512)]


ErrorCode = Literal[
    "INVALID_INPUT",
    "COMPANY_NOT_FOUND",
    "AMBIGUOUS_COMPANY",
    "INVALID_FILTER",
    "INVALID_METRIC",
    "QUERY_TOO_LONG",
    "PASSAGE_NOT_FOUND",
    "FILING_NOT_FOUND",
    "SECTION_NOT_FOUND",
    "DATA_INTEGRITY",
    "CORPUS_UNAVAILABLE",
    "SNAPSHOT_UNAVAILABLE",
    "DATABASE_UNAVAILABLE",
    "MODEL_UNAVAILABLE",
    "INTERNAL_ERROR",
    "DIVISION_BY_ZERO",
    "NON_POSITIVE_INPUT",
    "INVALID_YEARS",
    "INSUFFICIENT_DATA",
    "DUPLICATE_LABEL",
    "INVALID_EXPRESSION",
    "EXPRESSION_LIMIT",
    "NUMERIC_RANGE",
    "UNKNOWN_TOOL",
]


class ErrorDetail(Model):
    code: ErrorCode
    message: str


class Response[T](Model):
    data: T | None = None
    error: ErrorDetail | None = None

    @model_validator(mode="after")
    def one_branch(self):
        if (self.data is None) == (self.error is None):
            raise ValueError("Exactly one response branch is required.")
        return self


class SnapshotInfo(Model):
    snapshot_id: str
    cutoff_date: date


class CorpusInfo(SnapshotInfo):
    corpus_id: str


class CompanyData(Model):
    cik: str
    ticker: str
    name: str
    fiscal_year_end: str
    snapshot: SnapshotInfo


class Filing(Model):
    accession: str
    form: Form
    fiscal_year: int
    fiscal_period: PeriodName
    filing_date: date
    report_date: date
    url: str


class FilingsData(Model):
    ticker: str
    corpus: CorpusInfo
    filings: list[Filing]


class Source(Model):
    accession: str | None
    filed_date: date | None
    url: str | None


class Evidence(Model):
    policy_id: str
    source: Source
    chunk_ids: list[str]
    explanation: str


class DerivationInput(Model):
    coefficient: Literal[-1, 1]
    value: str
    unit: str
    concept: str
    start_date: date | None
    end_date: date
    source: Source


class MetricFact(Model):
    fact_id: str | None = None
    metric: Metric
    fiscal_year: int
    fiscal_period: PeriodName
    stored_fiscal_period: PeriodName | None = None
    period_type: Literal["quarter", "annual", "instant"] | None = None
    period_start: date | None = None
    period_end: date | None = None
    value: str | None = None
    unit: Literal["USD", "USD/shares"]
    status: Status
    reason: str | None = None
    derived: bool | None = None
    concept: str | None = None
    source_accession: str | None = None
    source_filed: date | None = None
    source_filing_date: date | None = None
    source_url: str | None = None
    derivation_inputs: list[DerivationInput] = Field(default_factory=list)
    stored_availability_status: Status | None = None
    applicability_evidence: list[Evidence] = Field(default_factory=list)


class FactsData(Model):
    ticker: str
    metric: Metric
    snapshot: SnapshotInfo
    facts: list[MetricFact]


class AvailablePeriod(Model):
    fiscal_year: int
    fiscal_period: PeriodName
    period_start: date | None
    period_end: date
    period_type: Literal["quarter", "annual", "instant"]
    stored_fiscal_period: PeriodName


class PeriodStatus(Model):
    fiscal_year: int
    fiscal_period: PeriodName
    status: Status
    stored_status: Status | None
    reason: str


class MetricAvailability(Model):
    metric: Metric
    unit: Literal["USD", "USD/shares"]
    status: Status
    reason: str | None
    available_periods: list[AvailablePeriod]
    earliest: AvailablePeriod | None
    latest: AvailablePeriod | None
    latest_quarter: AvailablePeriod | None
    latest_annual: AvailablePeriod | None
    latest_year_end: AvailablePeriod | None
    year_end_alias: Literal["FY_to_Q4"] | None
    period_statuses: list[PeriodStatus]
    applicability_evidence: list[Evidence]


class MetricsData(Model):
    ticker: str
    snapshot: SnapshotInfo
    metrics: list[MetricAvailability]
    latest_common_quarter: AvailablePeriod | None
    latest_common_quarter_reason: str | None


class CoverageDiagnostic(Model):
    code: Literal[
        "EXTRACTED",
        "RESOLVED",
        "REFERENCE_COVERED_ELSEWHERE",
        "SOURCE_ABSENT",
        "NOT_PARSED",
        "NO_Q4_FILING",
    ]
    accession: str | None = None
    item: Item | None = None
    reason: str
    target_resource: str | None = None
    source_url: str | None = None
    source_hash: str | None = None
    method: str | None = None
    evidence_text: str | None = None


class PassageHit(Model):
    chunk_id: str
    ticker: str
    form: Form
    fiscal_year: int
    fiscal_period: PeriodName
    item: Item
    text: str
    score: float | None
    accession: str
    title: str
    report_date: date
    url: str
    oversized_row: bool
    text_truncated: bool
    full_text_characters: int
    content_trust: Literal["untrusted_sec_text"] = "untrusted_sec_text"
    coverage_diagnostics: list[CoverageDiagnostic]


class PassageData(PassageHit):
    corpus: CorpusInfo
    section_id: str
    ordinal: int
    token_count: int


class SearchData(Model):
    corpus: CorpusInfo
    retrieval_mode: Mode
    hits: list[PassageHit]
    coverage_diagnostics: list[CoverageDiagnostic]


class SectionSpan(Model):
    section_id: str
    occurrence: int
    title: str
    text: str
    source_hash: str


class SectionData(Model):
    corpus: CorpusInfo
    accession: str
    ticker: str
    form: Form
    fiscal_year: int
    fiscal_period: PeriodName
    item: Item
    text: None = None
    sections: list[SectionSpan]
    coverage_diagnostics: list[CoverageDiagnostic]
    content_trust: Literal["untrusted_sec_text"] = "untrusted_sec_text"


class Precision(Model):
    context_precision: Literal[80] = 80
    decimal_places: Literal[12] = 12
    rounding: Literal["ROUND_HALF_EVEN"] = "ROUND_HALF_EVEN"


class QuantData(Model):
    precision: Precision = Field(default_factory=Precision)


class GrowthData(QuantData):
    old: str
    new: str
    value_pct: str
    base_convention: Literal["absolute_old"] = "absolute_old"


class MarginData(QuantData):
    numerator: str
    denominator: str
    value_pct: str


class CagrData(QuantData):
    start_value: str
    end_value: str
    years: str
    value_pct: str


class ChangePoint(Model):
    label: str
    value: str
    change_pct: str | None
    reason: Literal["first_observation"] | None


class YoyData(QuantData):
    points: list[ChangePoint]
    base_convention: Literal["absolute_old"] = "absolute_old"


class StatsData(QuantData):
    values: list[str]
    count: int
    mean: str
    median: str
    min: str
    max: str
    stdev: str
    stdev_kind: Literal["sample"] = "sample"


class EvaluationData(QuantData):
    expression: str
    normalized_expression: str
    value: str

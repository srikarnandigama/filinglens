"""Plan, worker, answer and verdict contracts (SPEC §10.4 as amended by D055)."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

DecimalStr = Annotated[str, Field(pattern=r"^-?(0|[1-9][0-9]*)(\.[0-9]+)?$")]
PeriodName = Literal["Q1", "Q2", "Q3", "Q4", "FY"]
FilingPeriod = Literal["Q1", "Q2", "Q3", "FY"]
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
Item = Literal["1", "1A", "7", "7A", "8", "P1-2", "P2-1A"]
Ticker = Annotated[str, Field(min_length=1, max_length=10, pattern=r"^[A-Z][A-Z0-9.-]*$")]
ClaimUnit = Literal["USD", "USD/shares", "percent", "percentage_points"]
ANNUAL_ITEMS = {"1", "1A", "7", "7A", "8"}
QUARTERLY_ITEMS = {"P1-2", "P2-1A"}


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PeriodRef(Contract):
    fiscal_year: int = Field(ge=1900, le=2200)
    fiscal_period: PeriodName

    def label(self) -> str:
        return f"FY{self.fiscal_year} {self.fiscal_period}"


class MetricLookupParams(Contract):
    kind: Literal["metric_lookup"]
    ticker: Ticker
    metric: Metric
    periods: list[PeriodRef] = Field(min_length=1, max_length=40)

    @model_validator(mode="after")
    def unique_periods(self):
        keys = [(p.fiscal_year, p.fiscal_period) for p in self.periods]
        if len(set(keys)) != len(keys):
            raise ValueError("periods must be unique")
        return self


class FilingSearchParams(Contract):
    kind: Literal["filing_search"]
    ticker: Ticker
    fiscal_year: int = Field(ge=1900, le=2200)
    fiscal_period: FilingPeriod
    items: list[Item] = Field(min_length=1, max_length=7)
    query: str = Field(min_length=1, max_length=300)
    k: int = Field(default=8, ge=1, le=10)

    @model_validator(mode="after")
    def items_match_form(self):
        allowed = ANNUAL_ITEMS if self.fiscal_period == "FY" else QUARTERLY_ITEMS
        if not set(self.items) <= allowed:
            raise ValueError(
                f"items for fiscal_period {self.fiscal_period} must be among {sorted(allowed)}"
            )
        return self


class InputRef(Contract):
    subtask_id: str
    ticker: Ticker | None = None
    metric: Metric | None = None
    period: PeriodRef | None = None


class ComputationParams(Contract):
    kind: Literal["computation"]
    operation: Literal["growth_rate", "margin", "cagr", "yoy_series", "summary_stats", "evaluate"]
    inputs: list[InputRef] = Field(min_length=1)
    note: str = Field(max_length=500)


class SubTask(Contract):
    id: str = Field(pattern=r"^s[0-9]+$")
    type: Literal["metric_lookup", "filing_search", "computation"]
    description: str = Field(max_length=500)
    depends_on: list[str] = Field(default_factory=list)
    params: Annotated[
        MetricLookupParams | FilingSearchParams | ComputationParams, Field(discriminator="kind")
    ]

    @model_validator(mode="after")
    def kind_matches_type(self):
        if self.params.kind != self.type:
            raise ValueError(f"subtask {self.id}: params.kind must equal type")
        return self


class PeriodResolution(Contract):
    phrase: str
    ticker: Ticker | None = None
    resolved: list[PeriodRef]
    basis: str


class Plan(Contract):
    question_type: Literal[
        "lookup", "trend", "derived", "comparison", "explanatory", "diff", "other"
    ]
    companies: list[Ticker]
    period_resolutions: list[PeriodResolution] = Field(default_factory=list)
    answerability: Literal["answerable", "not_available", "out_of_scope"]
    answerability_reason: str | None = None
    subtasks: list[SubTask] = Field(default_factory=list)

    @model_validator(mode="after")
    def structure(self):
        ids = [s.id for s in self.subtasks]
        if len(set(ids)) != len(ids):
            raise ValueError("subtask ids must be unique")
        if self.answerability == "answerable" and not self.subtasks:
            raise ValueError("an answerable plan needs at least one subtask")
        if self.answerability != "answerable" and not self.answerability_reason:
            raise ValueError("answerability_reason is required when not answerable")
        return self


class Citation(Contract):
    kind: Literal["fact", "chunk", "computation"]
    ref: str
    field: str | None = None


class Claim(Contract):
    id: str = Field(pattern=r"^c[0-9]+$")
    kind: Literal["numeric", "textual"]
    text: str = Field(min_length=1, max_length=1200)
    value: DecimalStr | None = None
    unit: ClaimUnit | None = None
    value_basis: Literal["fact", "computation", "model_arithmetic"] | None = None
    ticker: Ticker | None = None
    period: PeriodRef | None = None
    citations: list[Citation] = Field(min_length=1)

    @model_validator(mode="after")
    def numeric_fields(self):
        if self.kind == "numeric" and (
            self.value is None or self.unit is None or self.value_basis is None
        ):
            raise ValueError(f"claim {self.id}: numeric claims need value, unit and value_basis")
        if self.kind == "textual" and self.value is not None:
            raise ValueError(f"claim {self.id}: textual claims carry no value")
        return self


class Answer(Contract):
    status: Literal["answered", "partially_answered", "not_available", "not_applicable"]
    summary: str = Field(min_length=1)
    claims: list[Claim]
    final_value: DecimalStr | None = None
    final_unit: ClaimUnit | None = None
    final_claim_id: str | None = None
    caveats: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def consistency(self):
        ids = [c.id for c in self.claims]
        if len(set(ids)) != len(ids):
            raise ValueError("claim ids must be unique")
        if not self.claims and self.status in {"answered", "partially_answered"}:
            raise ValueError("answered statuses need at least one claim")
        if self.final_claim_id is not None and self.final_claim_id not in ids:
            raise ValueError("final_claim_id must name a claim")
        if (self.final_value is None) != (self.final_claim_id is None):
            raise ValueError("final_value and final_claim_id must be set together")
        return self


class DataWorkerOutput(Contract):
    subtask_id: str
    fact_ids: list[str]
    notes: str | None = None


class PassageFinding(Contract):
    chunk_id: str = Field(pattern=r"^chk_[0-9a-f]{64}$")
    relevance: str = Field(max_length=400)
    quotes: list[str] = Field(min_length=1, max_length=3)


class FilingsWorkerOutput(Contract):
    subtask_id: str
    found: bool
    passages: list[PassageFinding] = Field(default_factory=list, max_length=6)
    notes: str | None = None


class ClaimVerdict(Contract):
    claim_id: str
    verdict: Literal["supported", "unsupported", "needs_revision"]
    reason: str
    citations_checked: list[str] = Field(default_factory=list)


class VerifierOutput(Contract):
    verdicts: list[ClaimVerdict]
    summary_verdict: ClaimVerdict

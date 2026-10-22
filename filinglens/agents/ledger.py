"""Run-scoped evidence ledger: every citable ID produced by a tool result in this run (D056)."""

from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field

QUANT_TOOLS = {"growth_rate", "margin", "cagr", "yoy_series", "summary_stats", "evaluate"}


def status_record_id(ticker: str, metric: str, fiscal_year: int, fiscal_period: str) -> str:
    """Citable ID for a period the server returned without a fact (unavailable/not_applicable)."""
    return f"na_{ticker}_{metric}_{fiscal_year}_{fiscal_period}"


class FactRecord(BaseModel):
    fact_id: str
    ticker: str
    metric: str
    fiscal_year: int
    fiscal_period: str
    value: str | None
    unit: str
    status: str
    reason: str | None = None
    derived: bool | None = None
    period_start: str | None = None
    period_end: str | None = None
    concept: str | None = None
    source_accession: str | None = None
    source_url: str | None = None
    applicability_chunk_ids: list[str] = Field(default_factory=list)
    synthetic_id: bool = False


class PassageRecord(BaseModel):
    chunk_id: str
    ticker: str
    form: str
    fiscal_year: int
    fiscal_period: str
    item: str
    title: str | None = None
    accession: str | None = None
    url: str | None = None
    snippet: str | None = None
    full_text: str | None = None


class ComputationRecord(BaseModel):
    computation_id: str
    tool: str
    arguments: dict[str, Any]
    output: dict[str, Any] | None
    is_error: bool


class Ledger:
    def __init__(self) -> None:
        self.facts: dict[str, FactRecord] = {}
        self.passages: dict[str, PassageRecord] = {}
        self.computations: dict[str, ComputationRecord] = {}
        self.discovery: dict[str, dict] = {}
        self.companies: dict[str, dict] = {}
        self.evidence_chunk_ids: set[str] = set()
        self._next_computation = 1

    def next_computation_id(self) -> str:
        cid = f"cmp_{self._next_computation}"
        self._next_computation += 1
        return cid

    def register(
        self, tool: str, arguments: dict, structured: dict | None, is_error: bool, cid: str | None
    ) -> list[str]:
        """Record a tool result; returns the IDs it introduced."""
        if tool in QUANT_TOOLS and cid:
            data = (structured or {}).get("data") if not is_error else None
            self.computations[cid] = ComputationRecord(
                computation_id=cid, tool=tool, arguments=arguments, output=data, is_error=is_error
            )
            return [cid]
        if is_error or not structured or "data" not in structured:
            return []
        data = structured["data"]
        if tool == "get_financial_metric":
            return self._facts(data)
        if tool in {"search_filings", "get_passage"}:
            hits = data.get("hits", []) if tool == "search_filings" else [data]
            for hit in hits:
                self._passage(hit, full=tool == "get_passage")
            return [h["chunk_id"] for h in hits]
        if tool == "list_available_metrics":
            self.discovery[data["ticker"]] = data
            for metric in data.get("metrics", []):
                for evidence in metric.get("applicability_evidence", []):
                    self.evidence_chunk_ids.update(evidence.get("chunk_ids", []))
            return []
        if tool == "resolve_company":
            self.companies[data["ticker"]] = data
        return []

    def _facts(self, data: dict) -> list[str]:
        ids = []
        for fact in data["facts"]:
            evidence = [c for e in fact.get("applicability_evidence", []) for c in e["chunk_ids"]]
            self.evidence_chunk_ids.update(evidence)
            fid = fact.get("fact_id") or status_record_id(
                data["ticker"], fact["metric"], fact["fiscal_year"], fact["fiscal_period"]
            )
            self.facts[fid] = FactRecord(
                fact_id=fid,
                ticker=data["ticker"],
                metric=fact["metric"],
                fiscal_year=fact["fiscal_year"],
                fiscal_period=fact["fiscal_period"],
                value=fact.get("value"),
                unit=fact["unit"],
                status=fact["status"],
                reason=fact.get("reason"),
                derived=fact.get("derived"),
                period_start=fact.get("period_start"),
                period_end=fact.get("period_end"),
                concept=fact.get("concept"),
                source_accession=fact.get("source_accession"),
                source_url=fact.get("source_url"),
                applicability_chunk_ids=evidence,
                synthetic_id=fact.get("fact_id") is None,
            )
            ids.append(fid)
        return ids

    def _passage(self, hit: dict, *, full: bool) -> None:
        existing = self.passages.get(hit["chunk_id"])
        record = PassageRecord(
            chunk_id=hit["chunk_id"],
            ticker=hit["ticker"],
            form=hit["form"],
            fiscal_year=hit["fiscal_year"],
            fiscal_period=hit["fiscal_period"],
            item=hit["item"],
            title=hit.get("title"),
            accession=hit.get("accession"),
            url=hit.get("url"),
            snippet=hit["text"] if not full else (existing.snippet if existing else None),
            full_text=hit["text"] if full else (existing.full_text if existing else None),
        )
        self.passages[hit["chunk_id"]] = record

    def known_chunk(self, chunk_id: str) -> bool:
        return chunk_id in self.passages or chunk_id in self.evidence_chunk_ids

    def numeric_values(self) -> list[Decimal]:
        """Every available fact value and computation output number, for lineage checks."""
        values = [Decimal(f.value) for f in self.facts.values() if f.value is not None]
        for record in self.computations.values():
            if record.output:
                values.extend(_numbers(record.output))
        return values


def _numbers(node: Any) -> list[Decimal]:
    found: list[Decimal] = []
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "precision":
                continue
            found.extend(_numbers(value))
    elif isinstance(node, list):
        for item in node:
            found.extend(_numbers(item))
    elif isinstance(node, str):
        try:
            number = Decimal(node)
        except ArithmeticError:
            return found
        if number.is_finite():
            found.append(number)
    return found

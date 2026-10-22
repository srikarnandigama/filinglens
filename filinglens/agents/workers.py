"""Data worker (direct or LLM), filings worker and the evidence pack handed to the analyst."""

import re
from typing import Any

from pydantic import BaseModel, Field

from filinglens.agents.context import RunContext
from filinglens.agents.ledger import status_record_id
from filinglens.agents.loop import AgentOutputError, SemanticError, run_agent
from filinglens.agents.schemas import (
    DataWorkerOutput,
    FilingSearchParams,
    FilingsWorkerOutput,
    MetricLookupParams,
    Plan,
    SubTask,
)
from filinglens.agents.toolbox import Toolbox, wrap_evidence

WS = re.compile(r"\s+")


class SubtaskResult(BaseModel):
    subtask_id: str
    fact_ids: list[str] = Field(default_factory=list)
    filings: FilingsWorkerOutput | None = None
    notes: list[str] = Field(default_factory=list)


def fact_ids_from(structured: dict | None, ticker: str) -> list[str]:
    if not structured or "data" not in structured:
        return []
    data = structured["data"]
    return [
        f.get("fact_id")
        or status_record_id(data["ticker"], f["metric"], f["fiscal_year"], f["fiscal_period"])
        for f in data["facts"]
    ]


def metric_arguments(p: MetricLookupParams) -> dict[str, Any]:
    return {
        "ticker": p.ticker,
        "metric": p.metric,
        "periods": [
            {"fiscal_year": x.fiscal_year, "fiscal_period": x.fiscal_period} for x in p.periods
        ],
    }


async def run_data_direct(ctx: RunContext, subtask: SubTask) -> SubtaskResult:
    params = subtask.params
    assert isinstance(params, MetricLookupParams)
    outcome, _ = await Toolbox(ctx, f"data:{subtask.id}").call(
        "get_financial_metric", metric_arguments(params)
    )
    result = SubtaskResult(subtask_id=subtask.id)
    if outcome.is_error:
        error = (outcome.structured or {}).get("error", {})
        result.notes.append(
            f"get_financial_metric failed: {error.get('code')} {error.get('message')}"
        )
    result.fact_ids = fact_ids_from(outcome.structured, params.ticker)
    return result


def _metric_lock(params: MetricLookupParams):
    expected = metric_arguments(params)

    def lock(args: dict) -> str | None:
        periods = {(p.get("fiscal_year"), p.get("fiscal_period")) for p in args.get("periods", [])}
        wanted = {(p["fiscal_year"], p["fiscal_period"]) for p in expected["periods"]}
        if (args.get("ticker"), args.get("metric"), periods) != (
            expected["ticker"],
            expected["metric"],
            wanted,
        ):
            return f"Use exactly ticker, metric and periods {expected}."
        return None

    return lock


async def run_data_llm(ctx: RunContext, cfg, models, prompts, subtask: SubTask) -> SubtaskResult:
    params = subtask.params
    assert isinstance(params, MetricLookupParams)
    instance = f"data:{subtask.id}"

    def validate(out: DataWorkerOutput) -> None:
        if out.subtask_id != subtask.id:
            raise SemanticError(f"subtask_id must be {subtask.id}")
        unknown = [f for f in out.fact_ids if f not in ctx.ledger.facts]
        if unknown:
            raise SemanticError(f"Unknown fact_ids (not returned in this run): {unknown}")

    out = await run_agent(
        ctx,
        instance=instance,
        system=prompts["data_worker"][0],
        task="Execute this metric_lookup subtask exactly:\n"
        + wrap_evidence(subtask.model_dump(mode="json")),
        model=models["worker"],
        provider=cfg.provider,
        output_model=DataWorkerOutput,
        toolbox=Toolbox(ctx, instance, locks={"get_financial_metric": _metric_lock(params)}),
        validator=validate,
        max_steps=cfg.max_steps,
        max_tokens=cfg.max_tokens_per_call,
        effort=cfg.effort.get("worker"),
        temperature=cfg.temperature,
    )
    return SubtaskResult(
        subtask_id=subtask.id, fact_ids=out.fact_ids, notes=[out.notes] if out.notes else []
    )


def search_lock(params: FilingSearchParams):
    def lock(args: dict) -> str | None:
        same = (
            args.get("ticker") == params.ticker
            and args.get("fiscal_year") == params.fiscal_year
            and args.get("fiscal_period") == params.fiscal_period
            and set(args.get("items") or []) == set(params.items)
        )
        if not same:
            return (
                f"Filters are locked: ticker={params.ticker}, fiscal_year={params.fiscal_year}, "
                f"fiscal_period={params.fiscal_period}, items={params.items}. "
                "Only query may change."
            )
        if int(args.get("k", 8)) > params.k:
            return f"k must be at most {params.k}."
        return None

    return lock


async def run_filings(
    ctx: RunContext, cfg, models, prompts, subtask: SubTask, question: str
) -> SubtaskResult:
    params = subtask.params
    assert isinstance(params, FilingSearchParams)
    instance = f"filings:{subtask.id}"

    def validate(out: FilingsWorkerOutput) -> None:
        if out.subtask_id != subtask.id:
            raise SemanticError(f"subtask_id must be {subtask.id}")
        unknown = [p.chunk_id for p in out.passages if p.chunk_id not in ctx.ledger.passages]
        if unknown:
            raise SemanticError(f"Unknown chunk_ids (not returned in this run): {unknown}")

    task = (
        f"User question (context only): {question}\n\n"
        f"Execute this filing_search subtask:\n{wrap_evidence(subtask.model_dump(mode='json'))}"
    )
    result = SubtaskResult(subtask_id=subtask.id)
    try:
        out = await run_agent(
            ctx,
            instance=instance,
            system=prompts["filings_worker"][0],
            task=task,
            model=models["worker"],
            provider=cfg.provider,
            output_model=FilingsWorkerOutput,
            toolbox=Toolbox(
                ctx, instance, locks={"search_filings": search_lock(params)}, known_chunks_only=True
            ),
            validator=validate,
            max_steps=cfg.max_steps,
            max_tokens=cfg.max_tokens_per_call,
            effort=cfg.effort.get("worker"),
            temperature=cfg.temperature,
        )
    except AgentOutputError as exc:
        out = FilingsWorkerOutput(subtask_id=subtask.id, found=False, notes=f"Worker failed: {exc}")
    # Quotes are checked against full text, so fetch any passage only seen as a snippet.
    prefetch = Toolbox(ctx, instance, tools=("get_passage",))
    for passage in out.passages:
        if ctx.ledger.passages[passage.chunk_id].full_text is None:
            await prefetch.call("get_passage", {"chunk_id": passage.chunk_id})
    result.filings = out
    return result


def normalize_ws(text: str) -> str:
    return WS.sub(" ", text).strip()


def evidence_pack(ctx: RunContext, plan: Plan, results: dict[str, SubtaskResult]) -> dict:
    """Authoritative evidence from the ledger, in plan order (never completion order)."""
    ledger = ctx.ledger
    facts, passages, computations = [], [], []
    for subtask in plan.subtasks:
        result = results.get(subtask.id)
        if subtask.type == "metric_lookup" and result:
            facts.append(
                {
                    "subtask_id": subtask.id,
                    "records": [
                        ledger.facts[f].model_dump(mode="json", exclude={"synthetic_id"})
                        for f in result.fact_ids
                        if f in ledger.facts
                    ],
                    "notes": result.notes,
                }
            )
        elif subtask.type == "filing_search" and result and result.filings:
            out = result.filings
            items = []
            for finding in out.passages:
                record = ledger.passages[finding.chunk_id]
                full = normalize_ws(record.full_text or "")
                verified = [
                    q for q in finding.quotes if normalize_ws(q) and normalize_ws(q) in full
                ]
                items.append(
                    {
                        "chunk_id": finding.chunk_id,
                        "ticker": record.ticker,
                        "form": record.form,
                        "fiscal_year": record.fiscal_year,
                        "fiscal_period": record.fiscal_period,
                        "item": record.item,
                        "title": record.title,
                        "url": record.url,
                        "relevance": finding.relevance,
                        "verified_quotes": verified,
                        "dropped_quotes": len(finding.quotes) - len(verified),
                    }
                )
            passages.append(
                {
                    "subtask_id": subtask.id,
                    "filing": subtask.params.model_dump(mode="json", exclude={"kind"}),
                    "found": out.found,
                    "notes": out.notes,
                    "passages": items,
                }
            )
        elif subtask.type == "computation":
            computations.append(
                {
                    "subtask_id": subtask.id,
                    "description": subtask.description,
                    **subtask.params.model_dump(mode="json", exclude={"kind"}),
                }
            )
    return {
        "facts": facts,
        "passages": passages,
        "required_computations": computations,
    }

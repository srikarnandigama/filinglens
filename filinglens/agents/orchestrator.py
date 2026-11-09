"""Planner → workers → analyst → verifier with revisions; live runs are traced (SPEC §10.6)."""

import asyncio
import importlib.metadata
import subprocess
import time
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from filinglens.agents.budget import BudgetExceeded, RunBudget
from filinglens.agents.context import LiveGateway, RunContext
from filinglens.agents.ledger import Ledger
from filinglens.agents.loop import run_agent
from filinglens.agents.mcp_client import McpHub, ToolHub
from filinglens.agents.planner import plan_validator
from filinglens.agents.prompts import load_prompt
from filinglens.agents.schemas import (
    Answer,
    Claim,
    DataWorkerOutput,
    FilingsWorkerOutput,
    Plan,
    VerifierOutput,
)
from filinglens.agents.settings import RuntimeSettings
from filinglens.agents.toolbox import Toolbox, wrap_evidence
from filinglens.agents.tracing import PostgresTraceStore, Recorder, RunTotals, TraceStore
from filinglens.agents.verifier import (
    CheckResult,
    caveat_id,
    caveat_index,
    deterministic_checks,
    run_verifier,
)
from filinglens.agents.views import DISCOVERY_VIEW_VERSION
from filinglens.agents.workers import (
    SubtaskResult,
    evidence_pack,
    run_data_direct,
    run_data_llm,
    run_filings,
)
from filinglens.config import ROOT
from filinglens.llm.base import Provider, canonical_sha256
from filinglens.llm.pricing import PriceTable

CONFIG_VERSION = 1
RUNTIME_VERSION = "m4-runtime-1"
PROMPTS = {
    "planner": Plan,
    "data_worker": DataWorkerOutput,
    "filings_worker": FilingsWorkerOutput,
    "analyst": Answer,
    "analyst_no_quant": Answer,
    "verifier": VerifierOutput,
}


class RunConfig(BaseModel):
    provider: Literal["anthropic", "openai_compat"] = "anthropic"
    planner_model_env: str = "PLANNER_MODEL"
    worker_model_env: str = "WORKER_MODEL"
    verifier_model_env: str = "VERIFIER_MODEL"
    verifier: bool = True
    retrieval_mode: Literal["vector", "keyword", "hybrid", "hybrid_rerank"] = "vector"
    use_quant_tools: bool = True
    data_worker: Literal["direct", "llm"] = "direct"
    effort: dict[str, str] = Field(default_factory=dict)  # planner|worker|analyst|verifier
    max_steps: int = 8
    max_tokens_per_call: int = 16_000
    max_run_tokens: int = 200_000
    max_cost_usd: Decimal | None = None
    temperature: float | None = None
    max_concurrency: int = 4
    revision_rounds: int = 2
    max_passage_reads: int = 4  # get_passage calls per filings worker (D074)


class RunResult(BaseModel):
    model_config = {"arbitrary_types_allowed": True}
    run_id: UUID
    status: str
    answer: Answer | None
    error: dict | None
    totals: RunTotals
    ledger: Any
    verification: list[dict] = Field(default_factory=list)


def resolve_models(cfg: RunConfig, settings: RuntimeSettings) -> dict[str, str]:
    env = {
        "PLANNER_MODEL": settings.planner_model,
        "WORKER_MODEL": settings.worker_model,
        "VERIFIER_MODEL": settings.verifier_model,
        "OPEN_MODEL": settings.open_model,
    }
    fallback = settings.open_model if cfg.provider == "openai_compat" else None
    models = {}
    for role, name in (
        ("planner", cfg.planner_model_env),
        ("worker", cfg.worker_model_env),
        ("verifier", cfg.verifier_model_env),
    ):
        if name not in env:
            raise ValueError(f"{role} model env var must be one of {sorted(env)}")
        value = env[name] or fallback
        if not value:
            raise ValueError(f"Set {name} in .env (model IDs come only from env vars).")
        models[role] = value
    return models


def load_prompts() -> dict[str, tuple[str, str]]:
    return {name: load_prompt(name, model) for name, model in PROMPTS.items()}


def answer_sha256(answer: Answer) -> str:
    return canonical_sha256(answer.model_dump(mode="json"))


def _claim_key(claim: Claim) -> str:
    return canonical_sha256(claim.model_dump(mode="json", exclude={"id"}))


def _analyst_task(question: str, plan: Plan, evidence: dict) -> str:
    plan_view = {
        "question_type": plan.question_type,
        "companies": plan.companies,
        "period_resolutions": [p.model_dump(mode="json") for p in plan.period_resolutions],
    }
    return (
        f"Question: {question}\n\nPlan context:\n{wrap_evidence(plan_view)}\n\n"
        f"Evidence gathered by the workers:\n{wrap_evidence(evidence)}\n\n"
        "Write the answer. Reply with only the Answer JSON object."
    )


def _revision_task(
    base: str, answer: Answer, failures: dict[str, list[str]], ledger: Ledger
) -> str:
    computations = {
        cid: r.model_dump(mode="json") for cid, r in ledger.computations.items() if not r.is_error
    }
    feedback = [{"claim_id": cid, "problems": reasons} for cid, reasons in failures.items()]
    return (
        f"{base}\n\nYour previous answer:\n{wrap_evidence(answer.model_dump(mode='json'))}\n\n"
        f"Earlier computations you may cite by computation_id:\n{wrap_evidence(computations)}\n\n"
        f"Verifier feedback to address:\n{wrap_evidence(feedback)}\n\n"
        "Fix or remove every flagged claim and caveat (caveat_N is the N-th entry of caveats) "
        "and return the full revised Answer JSON object."
    )


async def _execute_subtasks(
    ctx: RunContext, cfg: RunConfig, models, prompts, plan: Plan, question: str
) -> dict[str, SubtaskResult]:
    semaphore = asyncio.Semaphore(cfg.max_concurrency)
    tasks: dict[str, asyncio.Task] = {}

    async def run_one(subtask) -> SubtaskResult | None:
        for dep in subtask.depends_on:
            await tasks[dep]
        if subtask.type == "computation":
            return None
        async with semaphore:
            if subtask.type == "metric_lookup":
                if cfg.data_worker == "direct":
                    return await run_data_direct(ctx, subtask)
                return await run_data_llm(ctx, cfg, models, prompts, subtask)
            return await run_filings(ctx, cfg, models, prompts, subtask, question)

    for subtask in plan.subtasks:
        tasks[subtask.id] = asyncio.ensure_future(run_one(subtask))
    try:
        results = await asyncio.gather(*tasks.values())
    except BaseException:
        for task in tasks.values():
            task.cancel()
        raise
    return {r.subtask_id: r for r in results if r is not None}


def _count(n: int, noun: str) -> str:
    return (
        f"1 {noun} could not be verified and was removed."
        if n == 1
        else (f"{n} {noun}s could not be verified and were removed.")
    )


def removed_items(answer: Answer, failures: dict[str, list[str]]) -> dict[str, dict]:
    """Full text and verifier reasons of everything dropped; for the trace only (D078)."""
    items = {
        c.id: {"text": c.text, "reasons": failures[c.id]} for c in answer.claims if c.id in failures
    }
    for i, text in enumerate(answer.caveats):
        if caveat_id(i) in failures:
            items[caveat_id(i)] = {"text": text, "reasons": failures[caveat_id(i)]}
    for key in ("summary", "answer"):
        if key in failures:
            items[key] = {
                "text": answer.summary if key == "summary" else None,
                "reasons": failures[key],
            }
    return items


def _drop(answer: Answer, failures: dict[str, list[str]]) -> Answer:
    """Remove failing items. User-facing caveats stay neutral; reasons live in the trace (D078)."""
    kept = [c for c in answer.claims if c.id not in failures]
    caveats = [c for i, c in enumerate(answer.caveats) if caveat_id(i) not in failures]
    dropped_caveats = sum(caveat_id(i) in failures for i in range(len(answer.caveats)))
    if dropped_caveats:
        caveats.append(_count(dropped_caveats, "caveat"))
    if len(kept) < len(answer.claims):
        caveats.append(_count(len(answer.claims) - len(kept), "claim"))
    final_value, final_unit, final_id = answer.final_value, answer.final_unit, answer.final_claim_id
    status = answer.status
    if final_id in failures or "answer" in failures:
        final_value = final_unit = final_id = None
    if len(kept) < len(answer.claims) and status == "answered":
        status = "partially_answered"
    if not kept and status in {"answered", "partially_answered"}:
        status = "not_available"
    summary = answer.summary
    if "summary" in failures:
        caveats.append("Summary rewritten from verified claims.")
        summary = " ".join(c.text for c in kept) or "No verified claims remain."
    return Answer(
        status=status,
        summary=summary,
        claims=kept,
        final_value=final_value,
        final_unit=final_unit,
        final_claim_id=final_id,
        caveats=caveats,
    )


REVISION_MARGIN = Decimal("1.5")
BUDGET_LIMITS = {
    "tokens": "the run's token budget (MAX_RUN_TOKENS)",
    "cost": "the run's cost cap",
    "steps": "an agent's step limit",
}


def revision_estimate(budget: RunBudget) -> int:
    """Tokens one revision round needs: the largest analyst call plus the largest verifier
    call measured in this run, times a 1.5 margin for the longer revision prompt (D072)."""
    largest = budget.max_call_tokens.get("analyst", 0) + budget.max_call_tokens.get("verifier", 0)
    return int(largest * REVISION_MARGIN)


@dataclass
class Verified:
    """Exact forms that passed Stage 2 in this run, plus the latest complete draft."""

    claims: set[str] = field(default_factory=set)  # claim keys (_claim_key)
    summaries: set[str] = field(default_factory=set)
    caveats: set[str] = field(default_factory=set)
    draft: Answer | None = None


def budget_finalize(
    answer: Answer, ledger: Ledger, use_quant_tools: bool, verified: Verified, kind: str
) -> tuple[Answer, dict[str, list[str]]]:
    """Keep only what passes Stage 1 now and already passed Stage 2 in its exact form (D073)."""
    checks = deterministic_checks(answer, ledger, use_quant_tools)
    unverified = "not verified before the run stopped"
    failures: dict[str, list[str]] = {}
    for claim in answer.claims:
        check = checks[claim.id]
        if check.verdict != "supported":
            failures[claim.id] = check.reasons or [check.verdict]
        elif _claim_key(claim) not in verified.claims:
            failures[claim.id] = [unverified]
    if checks["summary"].verdict != "supported" or answer.summary not in verified.summaries:
        failures["summary"] = checks["summary"].reasons or [unverified]
    if "answer" in checks:
        failures["answer"] = checks["answer"].reasons
    for i, text in enumerate(answer.caveats):
        if text not in verified.caveats:
            failures[caveat_id(i)] = [unverified]
    final = _drop(answer, failures)
    final = final.model_copy(
        update={
            "status": "partially_answered" if final.claims else "not_available",
            "caveats": [
                *final.caveats,
                f"Verification was cut short by {BUDGET_LIMITS.get(kind, kind)}; only claims "
                "verified in both stages were kept.",
            ],
        }
    )
    return Answer.model_validate(final.model_dump()), failures


async def orchestrate(
    ctx: RunContext, question: str, cfg: RunConfig, models: dict[str, str], prompts
) -> tuple[Answer, list[dict]]:
    rec = ctx.recorder
    plan = await run_agent(
        ctx,
        instance="planner",
        system=prompts["planner"][0],
        task=f"Question: {question}",
        model=models["planner"],
        provider=cfg.provider,
        output_model=Plan,
        toolbox=Toolbox(ctx, "planner"),
        validator=plan_validator(ctx.ledger),
        max_steps=cfg.max_steps,
        max_tokens=cfg.max_tokens_per_call,
        effort=cfg.effort.get("planner"),
        temperature=cfg.temperature,
    )
    await rec.emit("planner", "plan", {"plan": plan.model_dump(mode="json")})
    if plan.answerability != "answerable":
        reason = plan.answerability_reason or "not answerable from the stored data"
        answer = Answer(
            status="not_available",
            summary=f"This cannot be answered from the stored SEC data: {reason}",
            claims=[],
            caveats=[reason],
        )
        await rec.emit("analyst", "final", _final_payload(answer))
        return answer, []
    results = await _execute_subtasks(ctx, cfg, models, prompts, plan, question)
    evidence = evidence_pack(ctx, plan, results)
    base_task = _analyst_task(question, plan, evidence)
    analyst_prompt = prompts["analyst" if cfg.use_quant_tools else "analyst_no_quant"][0]

    async def analyst(round_no: int, task: str) -> Answer:
        instance = f"analyst:r{round_no}"
        answer = await run_agent(
            ctx,
            instance=instance,
            system=analyst_prompt,
            task=task,
            model=models["planner"],
            provider=cfg.provider,
            output_model=Answer,
            toolbox=Toolbox(ctx, instance, traced_inputs=True) if cfg.use_quant_tools else None,
            max_steps=cfg.max_steps,
            max_tokens=cfg.max_tokens_per_call,
            effort=cfg.effort.get("analyst"),
            temperature=cfg.temperature,
        )
        for claim in answer.claims:
            await rec.emit(
                "analyst", "claim", {"round": round_no, "claim": claim.model_dump(mode="json")}
            )
        return answer

    answer = await analyst(0, base_task)  # no draft yet: a budget stop here is a run error
    verified = Verified(draft=answer)
    verification_log: list[dict] = []
    try:
        answer = await _verify_and_revise(
            ctx,
            cfg,
            models,
            prompts,
            question,
            evidence,
            base_task,
            answer,
            analyst,
            verified,
            verification_log,
        )
    except BudgetExceeded as exc:  # D073: never discard a draft; keep only verified content
        draft = verified.draft
        answer, dropped = budget_finalize(
            draft, ctx.ledger, cfg.use_quant_tools, verified, exc.kind
        )
        ctx.budget_finalized = {
            "type": "BudgetExceeded",
            "kind": exc.kind,
            "message": str(exc),
            "handled": "budget_finalized",
        }
        await rec.emit(
            "orchestrator",
            "budget_finalized",
            {
                **ctx.budget_finalized,
                "dropped": dropped,
                "removed": removed_items(draft, dropped),
                "kept": [c.id for c in answer.claims],
            },
        )
    await rec.emit("analyst", "final", _final_payload(answer))
    return answer, verification_log


async def _verify_and_revise(
    ctx,
    cfg,
    models,
    prompts,
    question,
    evidence,
    base_task,
    answer,
    analyst,
    verified,
    verification_log,
) -> Answer:
    """Verification rounds with revisions; `answer` always holds the latest complete draft."""
    rec = ctx.recorder
    supported, supported_summaries = verified.claims, verified.summaries
    supported_caveats = verified.caveats
    for round_no in range(cfg.revision_rounds + 1):
        checks = deterministic_checks(answer, ctx.ledger, cfg.use_quant_tools)
        failures = {
            cid: r.reasons
            for cid, r in checks.items()
            if r.verdict in {"unsupported", "needs_revision"}
        }
        llm_verdicts: dict[str, Any] = {}
        if cfg.verifier:
            to_check = {
                c.id
                for c in answer.claims
                if c.id not in failures and _claim_key(c) not in supported
            }
            summary_pending = (
                answer.summary not in supported_summaries and "summary" not in failures
            )
            caveats_pending = {
                caveat_id(i) for i, c in enumerate(answer.caveats) if c not in supported_caveats
            }
            if to_check or ((summary_pending or caveats_pending) and not failures):
                computations = {
                    cid: r.model_dump(mode="json")
                    for cid, r in ctx.ledger.computations.items()
                    if not r.is_error
                }
                out = await run_verifier(
                    ctx,
                    cfg,
                    models,
                    prompts,
                    question=question,
                    answer=answer,
                    claim_ids=to_check,
                    round_no=round_no,
                    caveat_ids=caveats_pending,
                    run_evidence={**evidence, "computations": computations},
                )
                for verdict in out.caveat_verdicts:
                    if verdict.verdict == "supported":
                        supported_caveats.add(answer.caveats[caveat_index(verdict.claim_id)])
                for verdict in [*out.verdicts, out.summary_verdict, *out.caveat_verdicts]:
                    llm_verdicts[verdict.claim_id] = verdict.model_dump(mode="json")
                    if verdict.verdict != "supported":
                        failures.setdefault(verdict.claim_id, []).append(
                            f"verifier ({verdict.verdict}): {verdict.reason}"
                        )
                if out.summary_verdict.verdict == "supported" and "summary" not in failures:
                    supported_summaries.add(answer.summary)
            for claim in answer.claims:
                if claim.id not in failures:
                    supported.add(_claim_key(claim))
        entry = {
            "round": round_no,
            "applied": cfg.verifier,
            "deterministic": {k: v.model_dump(mode="json") for k, v in checks.items()},
            "llm": llm_verdicts,
            "failing": failures,
        }
        verification_log.append(entry)
        await rec.emit("verifier", "verification", entry)
        if not cfg.verifier or not failures:
            break
        if round_no == cfg.revision_rounds:
            removed = removed_items(answer, failures)
            answer = _drop(answer, failures)
            await rec.emit(
                "verifier",
                "verification",
                {"round": round_no, "dropped": failures, "removed": removed},
            )
            break
        needed, remaining = revision_estimate(ctx.budget), ctx.budget.remaining_tokens
        if needed > remaining:  # D072: a revision that cannot also be verified is not started
            removed = removed_items(answer, failures)
            answer = _drop(answer, failures)
            await rec.emit(
                "orchestrator",
                "revision_skipped",
                {
                    "round": round_no + 1,
                    "estimated_tokens": needed,
                    "remaining_tokens": remaining,
                    "dropped": failures,
                    "removed": removed,
                },
            )
            break
        answer = await analyst(
            round_no + 1, _revision_task(base_task, answer, failures, ctx.ledger)
        )
        verified.draft = answer
    return answer


def _final_payload(answer: Answer) -> dict:
    return {"answer": answer.model_dump(mode="json"), "answer_sha256": answer_sha256(answer)}


def git_state() -> dict:
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True
        ).stdout.strip()
        dirty = bool(
            subprocess.run(
                ["git", "status", "--porcelain"], cwd=ROOT, capture_output=True, text=True
            ).stdout.strip()
        )
    except (OSError, subprocess.CalledProcessError):
        return {"commit": None, "dirty": None}
    return {"commit": commit, "dirty": dirty}


def build_config(
    cfg: RunConfig, models, prompts, hub: ToolHub, settings: RuntimeSettings, prices: PriceTable
) -> dict:
    versions = {p: importlib.metadata.version(p) for p in ("anthropic", "openai", "mcp")}
    return {
        "config_version": CONFIG_VERSION,
        "runtime_version": RUNTIME_VERSION,
        "flags": cfg.model_dump(mode="json"),
        "models": {
            "planner": {"env": cfg.planner_model_env, "id": models["planner"]},
            "analyst": {"env": cfg.planner_model_env, "id": models["planner"]},
            "worker": {"env": cfg.worker_model_env, "id": models["worker"]},
            "verifier": {"env": cfg.verifier_model_env, "id": models["verifier"]},
        },
        "prompts": {name: {"sha256": sha} for name, (_, sha) in prompts.items()},
        "tool_specs": {"sha256": hub.tool_specs_sha256, "names": sorted(hub.specs)},
        "servers": {
            "snapshot_id": settings.snapshot_id,
            "corpus_id": settings.retrieval_corpus,
            "retrieval_mode": hub.retrieval_mode,
        },
        "sdk_versions": versions,
        "discovery_view_version": DISCOVERY_VIEW_VERSION,
        "pricing": prices.snapshot(set(models.values())),
        "git": git_state(),
    }


def build_providers(cfg: RunConfig, settings: RuntimeSettings) -> dict[str, Provider]:
    if cfg.provider == "anthropic":
        from filinglens.llm.anthropic_provider import AnthropicProvider

        if settings.anthropic_api_key is None:
            raise ValueError("Set ANTHROPIC_API_KEY in .env for live runs.")
        return {
            "anthropic": AnthropicProvider(api_key=settings.anthropic_api_key.get_secret_value())
        }
    from filinglens.llm.openai_compat_provider import OpenAICompatProvider

    if settings.openai_compat_api_key is None or not settings.openai_compat_base_url:
        raise ValueError("Set OPENAI_COMPAT_API_KEY and OPENAI_COMPAT_BASE_URL in .env.")
    return {
        "openai_compat": OpenAICompatProvider(
            api_key=settings.openai_compat_api_key.get_secret_value(),
            base_url=settings.openai_compat_base_url,
        )
    }


def _error_payload(exc: BaseException) -> dict:
    payload = {"type": type(exc).__name__, "message": str(exc)[:2000]}
    for attr in ("kind", "instance", "step"):
        if hasattr(exc, attr):
            payload[attr] = getattr(exc, attr)
    return payload


async def run_question(
    question: str,
    cfg: RunConfig,
    settings: RuntimeSettings,
    *,
    providers: dict[str, Provider] | None = None,
    store: TraceStore | None = None,
    prices: PriceTable | None = None,
    hub: ToolHub | None = None,
    log_root: Path | None = None,
) -> RunResult:
    """A live run: preflight, start servers (unless a hub is supplied), orchestrate, persist."""
    models = resolve_models(cfg, settings)
    prices = prices or PriceTable.load()
    prices.require(set(models.values()))
    prompts = load_prompts()
    providers = providers or build_providers(cfg, settings)
    run_id = uuid4()
    own_store = store is None
    store = store or PostgresTraceStore(settings.database_url)
    started = time.perf_counter()
    try:
        if hub is None:
            log_dir = (log_root or ROOT / "data" / "runs") / str(run_id)
            async with McpHub(settings, retrieval_mode=cfg.retrieval_mode, log_dir=log_dir) as live:
                return await _run(
                    question,
                    cfg,
                    settings,
                    providers,
                    store,
                    prices,
                    live,
                    models,
                    prompts,
                    run_id,
                    started,
                )
        return await _run(
            question, cfg, settings, providers, store, prices, hub, models, prompts, run_id, started
        )
    finally:
        if own_store:
            store.close()


async def _run(
    question, cfg, settings, providers, store, prices, hub, models, prompts, run_id, started
):
    config = build_config(cfg, models, prompts, hub, settings, prices)
    await asyncio.to_thread(store.create_run, run_id, question, config)
    recorder = Recorder(store, run_id)
    budget = RunBudget(max_tokens=cfg.max_run_tokens, prices=prices, max_cost_usd=cfg.max_cost_usd)
    ctx = RunContext(
        hub=hub, gateway=LiveGateway(providers, budget, recorder), recorder=recorder, budget=budget
    )
    answer, error, status, log = None, None, "done", []
    await recorder.emit(
        "orchestrator",
        "tool_specs",
        {
            "sha256": hub.tool_specs_sha256,
            "specs": [hub.specs[n].model_dump(mode="json") for n in sorted(hub.specs)],
        },
    )
    try:
        answer, log = await orchestrate(ctx, question, cfg, models, prompts)
        error = ctx.budget_finalized  # status stays "done"; the stop reason is kept (D073)
    except Exception as exc:  # recorded and reported; never swallowed silently
        status, error = "error", _error_payload(exc)
        await recorder.emit("orchestrator", "error", error)
    budget.totals.latency_ms = int((time.perf_counter() - started) * 1000)
    await asyncio.to_thread(
        store.finish,
        run_id,
        status,
        answer.model_dump(mode="json") if answer else None,
        budget.totals,
        error,
    )
    return RunResult(
        run_id=run_id,
        status=status,
        answer=answer,
        error=error,
        totals=budget.totals,
        ledger=ctx.ledger,
        verification=log,
    )


__all__ = ["CheckResult", "RunConfig", "RunResult", "orchestrate", "run_question"]

"""Offline replay of a recorded run with a divergence check (D059)."""

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from filinglens.agents.budget import RunBudget
from filinglens.agents.context import RunContext, llm_call_payload, role_of
from filinglens.agents.mcp_client import ToolOutcome
from filinglens.agents.orchestrator import (
    RunConfig,
    answer_sha256,
    load_prompts,
    orchestrate,
)
from filinglens.agents.tracing import MemoryTraceStore, Recorder, TraceEvent, load_run
from filinglens.llm.base import LLMRequest, LLMResponse, Msg, ToolSpec, canonical_sha256
from filinglens.llm.pricing import PriceTable


class ReplayDivergence(RuntimeError):
    def __init__(self, where: str, detail: str) -> None:
        super().__init__(f"Replay diverged at {where}: {detail}")
        self.where = where
        self.detail = detail


class RecordedFailure(RuntimeError):
    """The recorded run failed at this point; replay reproduces the failure."""

    def __init__(self, error: dict) -> None:
        super().__init__(f"recorded {error.get('type')}: {error.get('message')}")
        self.error = error


class ReplayReport(BaseModel):
    run_id: UUID
    identical: bool
    recorded_status: str
    replay_status: str
    recorded_answer_sha256: str | None = None
    replay_answer_sha256: str | None = None
    prompt_drift: list[str] = Field(default_factory=list)
    divergence: str | None = None


class ReplayHub:
    def __init__(self, events: list[TraceEvent], specs: dict[str, ToolSpec], mode: str) -> None:
        self.calls = {
            e.payload["call_id"]: e.payload for e in events if e.event_type == "tool_call"
        }
        self.results = {
            e.payload["call_id"]: e.payload for e in events if e.event_type == "tool_result"
        }
        self.specs = specs
        self.retrieval_mode = mode
        self.tool_specs_sha256 = ""

    async def call(self, call_id: str, tool: str, arguments: dict[str, Any]) -> ToolOutcome:
        recorded = self.calls.get(call_id)
        if recorded is None or call_id not in self.results:
            raise ReplayDivergence(call_id, f"no recorded result for {tool}")
        if recorded["tool"] != tool or canonical_sha256(recorded["arguments"]) != canonical_sha256(
            arguments
        ):
            raise ReplayDivergence(
                call_id,
                f"tool call {tool}({arguments}) differs from recorded "
                f"{recorded['tool']}({recorded['arguments']})",
            )
        result = self.results[call_id]
        return ToolOutcome(structured=result["structured"], is_error=result["is_error"])


class ReplayGateway:
    def __init__(
        self,
        events: list[TraceEvent],
        budget: RunBudget,
        recorder: Recorder,
        recorded_error: dict | None,
    ):
        self.calls = {
            (e.payload["instance"], e.payload["step"]): e.payload
            for e in events
            if e.event_type == "llm_call"
        }
        self.systems = {k[0]: v["system"] for k, v in self.calls.items() if "system" in v}
        self.budget = budget
        self.recorder = recorder
        self.recorded_error = recorded_error

    async def complete(
        self, instance: str, step: int, request: LLMRequest, new_messages: list[Msg]
    ) -> LLMResponse:
        self.budget.check_before_call()
        recorded = self.calls.get((instance, step))
        if recorded is None:
            err = self.recorded_error or {}
            if err.get("instance") == instance and err.get("step") == step:
                raise RecordedFailure(err)
            raise ReplayDivergence(f"{instance} step {step}", "no recorded LLM call")
        if request.fingerprint() != recorded["request_sha256"]:
            raise ReplayDivergence(
                f"{instance} step {step}", self._explain(instance, request, recorded, new_messages)
            )
        response = LLMResponse.model_validate(recorded["response"])
        self.budget.add(request.model, response.usage)
        await self.recorder.emit(
            role_of(instance),
            "llm_call",
            llm_call_payload(instance, step, request, new_messages, response),
        )
        return response

    def _explain(self, instance, request: LLMRequest, recorded: dict, new_messages) -> str:
        if instance in self.systems and self.systems[instance] != request.system:
            return "system prompt differs from the recorded prompt"
        if [t.name for t in request.tools] != recorded["tool_names"]:
            return f"tool list {[t.name for t in request.tools]} != {recorded['tool_names']}"
        if (request.model, request.max_tokens, request.effort) != (
            recorded["model"],
            recorded["max_tokens"],
            recorded["effort"],
        ):
            return "model or request parameters differ"
        now = [m.model_dump(mode="json") for m in new_messages]
        for index, (a, b) in enumerate(zip(now, recorded["new_messages"], strict=False)):
            if a != b:
                return f"new message {index} differs (role {a.get('role')})"
        if len(now) != len(recorded["new_messages"]):
            return "a different number of new messages was sent"
        return "tool specifications or earlier conversation differ"


async def replay_run(database_url: str, run_id: UUID) -> ReplayReport:
    meta, events = load_run(database_url, run_id)
    config = meta["config"]
    cfg = RunConfig.model_validate(config["flags"])
    models = {role: config["models"][role]["id"] for role in ("planner", "worker", "verifier")}
    prompts = load_prompts()
    drift = [
        name
        for name, (_, sha) in prompts.items()
        if config["prompts"].get(name, {}).get("sha256") != sha
    ]
    specs = _recorded_specs(events)
    store = MemoryTraceStore()
    store.create_run(run_id, meta["question"], config)
    recorder = Recorder(store, run_id)
    budget = RunBudget(
        max_tokens=cfg.max_run_tokens,
        prices=PriceTable.from_snapshot(config["pricing"]),
        max_cost_usd=cfg.max_cost_usd,
    )
    gateway = ReplayGateway(events, budget, recorder, meta["error"])
    ctx = RunContext(
        hub=ReplayHub(events, specs, config["servers"]["retrieval_mode"]),
        gateway=gateway,
        recorder=recorder,
        budget=budget,
    )
    recorded_sha = next(
        (e.payload["answer_sha256"] for e in events if e.event_type == "final"), None
    )
    report = ReplayReport(
        run_id=run_id,
        identical=False,
        recorded_status=meta["status"],
        replay_status="error",
        recorded_answer_sha256=recorded_sha,
        prompt_drift=drift,
    )
    try:
        answer, _ = await orchestrate(ctx, meta["question"], cfg, models, prompts)
    except ReplayDivergence as exc:
        report.divergence = str(exc)
        return report
    except Exception as exc:  # the recorded run may have failed the same way
        recorded = meta["error"] or {}
        failure = exc.error if isinstance(exc, RecordedFailure) else {"type": type(exc).__name__}
        report.identical = meta["status"] == "error" and failure.get("type") == recorded.get("type")
        if not report.identical:
            report.divergence = f"replay raised {type(exc).__name__}: {exc}"
        return report
    report.replay_status = "done"
    report.replay_answer_sha256 = answer_sha256(answer)
    report.identical = meta["status"] == "done" and report.replay_answer_sha256 == recorded_sha
    if not report.identical and report.divergence is None:
        report.divergence = "final Answer differs from the recorded Answer"
    return report


def _recorded_specs(events: list[TraceEvent]) -> dict[str, ToolSpec]:
    """Tool specs are part of each request fingerprint; rebuild them from the first requests."""
    specs: dict[str, ToolSpec] = {}
    for event in events:
        if event.event_type == "tool_specs":
            for spec in event.payload["specs"]:
                specs[spec["name"]] = ToolSpec.model_validate(spec)
    return specs

"""Per-run state shared by the loop, toolboxes and orchestrator, plus the live LLM gateway."""

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Protocol

from filinglens.agents.budget import RunBudget
from filinglens.agents.ledger import Ledger
from filinglens.agents.mcp_client import ToolHub
from filinglens.agents.tracing import Recorder
from filinglens.llm.base import LLMRequest, LLMResponse, Msg, Provider


def role_of(instance: str) -> str:
    return instance.split(":", 1)[0]


class LLMGateway(Protocol):
    async def complete(
        self, instance: str, step: int, request: LLMRequest, new_messages: list[Msg]
    ) -> LLMResponse: ...


def llm_call_payload(
    instance: str, step: int, request: LLMRequest, new_messages: list[Msg], response: LLMResponse
) -> dict:
    payload = {
        "instance": instance,
        "step": step,
        "provider": request.provider,
        "model": request.model,
        "request_sha256": request.fingerprint(),
        "new_messages": [m.model_dump(mode="json") for m in new_messages],
        "tool_names": [t.name for t in request.tools],
        "max_tokens": request.max_tokens,
        "effort": request.effort,
        "temperature": request.temperature,
        "response": response.model_dump(mode="json"),
    }
    if step == 0:
        payload["system"] = request.system
    return payload


class LiveGateway:
    def __init__(self, providers: dict[str, Provider], budget: RunBudget, recorder: Recorder):
        self.providers = providers
        self.budget = budget
        self.recorder = recorder

    async def complete(
        self, instance: str, step: int, request: LLMRequest, new_messages: list[Msg]
    ) -> LLMResponse:
        self.budget.check_before_call()
        try:
            response = await self.providers[request.provider].complete(
                system=request.system,
                messages=request.messages,
                tools=request.tools or None,
                model=request.model,
                max_tokens=request.max_tokens,
                temperature=request.temperature,
                effort=request.effort,
            )
        except Exception as exc:
            exc.instance, exc.step = instance, step  # lets replay match the recorded failure
            raise
        cost = self.budget.add(request.model, response.usage)
        payload = llm_call_payload(instance, step, request, new_messages, response)
        payload["cost_usd"] = str(cost)
        await self.recorder.emit(
            role_of(instance),
            "llm_call",
            payload,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            latency_ms=response.latency_ms,
        )
        return response


@dataclass
class RunContext:
    hub: ToolHub
    gateway: LLMGateway
    recorder: Recorder
    budget: RunBudget
    ledger: Ledger = field(default_factory=Ledger)
    tool_counters: dict[str, int] = field(default_factory=lambda: defaultdict(int))

    def next_call_id(self, instance: str) -> str:
        self.tool_counters[instance] += 1
        return f"{instance}/t{self.tool_counters[instance]}"

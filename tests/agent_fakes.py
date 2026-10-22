"""Scripted fakes for offline agent tests: no LLM API is ever called.

Synthetic numbers in these helpers are labeled test data, not SEC values.
"""

import asyncio
import json
import os
import re
from collections.abc import Callable
from decimal import Decimal
from typing import Any

from filinglens.agents.budget import RunBudget
from filinglens.agents.context import LiveGateway, RunContext
from filinglens.agents.mcp_client import ToolOutcome
from filinglens.agents.tracing import MemoryTraceStore, Recorder
from filinglens.llm.base import LLMResponse, Msg, ToolCall, ToolSpec, Usage
from filinglens.llm.pricing import ModelPrice, PriceTable

ENVELOPE = re.compile(r"<(tool_result_data|evidence)([^>]*)>\n(.*?)\n</\1>", re.DOTALL)
ROLE_MARKERS = {
    "You are the planner": "planner",
    "You are the data worker": "data",
    "You are the filings worker": "filings",
    "You are the analyst": "analyst",
    "You are the verifier": "verifier",
}
USAGE = Usage(input_tokens=100, output_tokens=50)


def proactor_run(coro):
    """Stdio servers need Windows' Proactor loop regardless of any global policy."""
    factory = asyncio.ProactorEventLoop if os.name == "nt" else asyncio.new_event_loop
    with asyncio.Runner(loop_factory=factory) as runner:
        return runner.run(coro)


def fake_prices(*models: str) -> PriceTable:
    names = models or ("fake-large", "fake-small")
    return PriceTable(
        {m: ModelPrice(input_per_mtok=Decimal("1"), output_per_mtok=Decimal("2")) for m in names}
    )


def final(obj: Any, *, stop: str = "end_turn", usage: Usage = USAGE) -> LLMResponse:
    text = obj if isinstance(obj, str) else json.dumps(obj)
    return LLMResponse(
        text=text,
        tool_calls=[],
        stop_reason=stop,
        raw_stop_reason=stop,
        usage=usage,
        model="fake",
        provider_raw=[{"type": "text", "text": text}],
    )


_call_counter = 0


def calls(*specs: tuple[str, dict], usage: Usage = USAGE) -> LLMResponse:
    global _call_counter
    tool_calls = []
    for name, args in specs:
        _call_counter += 1
        tool_calls.append(ToolCall(id=f"toolu_{_call_counter}", name=name, arguments=args))
    return LLMResponse(
        text="",
        tool_calls=tool_calls,
        stop_reason="tool_use",
        raw_stop_reason="tool_use",
        usage=usage,
        model="fake",
        provider_raw=[
            {"type": "tool_use", "id": c.id, "name": c.name, "input": c.arguments}
            for c in tool_calls
        ],
    )


def role_of_system(system: str) -> str:
    for marker, role in ROLE_MARKERS.items():
        if marker in system:
            return role
    raise AssertionError("unknown system prompt")


def envelopes(messages: list[Msg]) -> list[tuple[str, dict, Any]]:
    """All (tag, attributes, parsed JSON) envelopes in user and tool-result messages."""
    found = []
    for msg in messages:
        texts = [msg.text or ""] + [p.content for p in msg.tool_results]
        for text in texts:
            for tag, attrs, body in ENVELOPE.findall(text):
                attributes = dict(re.findall(r'(\w+)="([^"]*)"', attrs))
                found.append((tag, attributes, json.loads(body)))
    return found


def tool_results(messages: list[Msg], tool: str) -> list[tuple[dict, Any]]:
    return [(a, body) for tag, a, body in envelopes(messages) if a.get("tool") == tool]


def evidence(messages: list[Msg]) -> list[Any]:
    return [body for tag, _, body in envelopes(messages[:1]) if tag == "evidence"]


class Script:
    """Returns a fixed sequence of responses and records the messages it was sent."""

    name = "anthropic"

    def __init__(self, *responses: LLMResponse) -> None:
        self.responses = list(responses)
        self.seen: list[list[Msg]] = []

    async def complete(self, *, system, messages, tools, model, max_tokens, **kw):
        self.seen.append(list(messages))
        return self.responses.pop(0)


Handler = Callable[[int, list[Msg], str], LLMResponse]


class ScriptedProvider:
    """Dispatches by role (detected from the system prompt) to scripted handlers."""

    name = "anthropic"

    def __init__(self, handlers: dict[str, Handler]) -> None:
        self.handlers = handlers
        self.requests: list[dict] = []

    async def complete(self, *, system, messages, tools, model, max_tokens, **kwargs):
        role = role_of_system(system)
        step = sum(1 for m in messages if m.role == "assistant")
        self.requests.append({"role": role, "step": step, "tools": [t.name for t in tools or []]})
        return self.handlers[role](step, messages, model)


class FakeHub:
    """In-memory ToolHub with synthetic results for loop tests."""

    def __init__(self, results: dict[str, Callable[[dict], dict]], *, barrier=None) -> None:
        self.results = results
        self.barrier = barrier
        self.calls: list[tuple[str, str, dict]] = []
        self.specs = {
            name: ToolSpec(
                name=name, description=f"{name} test tool", input_schema={"type": "object"}
            )
            for name in [
                "resolve_company",
                "list_filings",
                "get_financial_metric",
                "list_available_metrics",
                "search_filings",
                "get_passage",
                "growth_rate",
                "margin",
                "cagr",
                "yoy_series",
                "summary_stats",
                "evaluate",
            ]
        }
        self.retrieval_mode = "vector"
        self.tool_specs_sha256 = "fake"

    async def call(self, call_id: str, tool: str, arguments: dict) -> ToolOutcome:
        self.calls.append((call_id, tool, arguments))
        if self.barrier is not None:
            await asyncio.wait_for(self.barrier.wait(), timeout=5)
        structured = self.results[tool](arguments)
        return ToolOutcome(structured=structured, is_error="error" in structured)


def make_context(
    hub, provider, *, max_tokens: int = 200_000, max_cost=None, prices=None
) -> tuple[RunContext, MemoryTraceStore]:
    from uuid import uuid4

    store = MemoryTraceStore()
    run_id = uuid4()
    store.create_run(run_id, "test", {})
    recorder = Recorder(store, run_id)
    budget = RunBudget(
        max_tokens=max_tokens, prices=prices or fake_prices("fake-large"), max_cost_usd=max_cost
    )
    gateway = LiveGateway({"anthropic": provider}, budget, recorder)
    return RunContext(hub=hub, gateway=gateway, recorder=recorder, budget=budget), store

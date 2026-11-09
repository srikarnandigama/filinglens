"""Role-filtered tool access with argument locks, ledger registration and data envelopes."""

import asyncio
import hashlib
import json
from collections.abc import Callable
from typing import Any

from filinglens.agents.context import RunContext, role_of
from filinglens.agents.ledger import QUANT_TOOLS
from filinglens.agents.mcp_client import QUANT_TOOLS as ANALYST_TOOLS
from filinglens.agents.mcp_client import ToolOutcome
from filinglens.agents.views import DISCOVERY_VIEW_VERSION, discovery_view
from filinglens.llm.base import ToolCall, ToolResultPart, ToolSpec, canonical_json

ROLE_TOOLS: dict[str, tuple[str, ...]] = {
    "planner": ("resolve_company", "list_available_metrics"),
    "data": ("get_financial_metric",),
    "filings": ("search_filings", "get_passage"),
    "analyst": ANALYST_TOOLS,
    "verifier": ("get_passage", "get_financial_metric"),
}
TRUST = {
    "search_filings": "untrusted_sec_text",
    "get_passage": "untrusted_sec_text",
    **{t: "computed" for t in QUANT_TOOLS},
}
Lock = Callable[[dict[str, Any]], str | None]
DUPLICATE_NOTE = "duplicate call: result already provided"


def envelope(tool: str, call_id: str, payload: Any, *, computation_id: str | None = None) -> str:
    trust = TRUST.get(tool, "sec_structured_data")
    body = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    body = body.replace("</tool_result_data", "<\\/tool_result_data")
    extra = f' computation_id="{computation_id}"' if computation_id else ""
    return (
        f'<tool_result_data tool="{tool}" call="{call_id}" trust="{trust}"{extra}>\n'
        f"{body}\n</tool_result_data>"
    )


def wrap_evidence(payload: Any) -> str:
    body = json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=1)
    body = body.replace("</evidence", "<\\/evidence")
    return f'<evidence trust="untrusted_sec_text_and_data">\n{body}\n</evidence>'


def _local_error(code: str, message: str) -> ToolOutcome:
    return ToolOutcome(structured={"error": {"code": code, "message": message}}, is_error=True)


class Toolbox:
    def __init__(
        self,
        ctx: RunContext,
        instance: str,
        tools: tuple[str, ...] | None = None,
        *,
        locks: dict[str, Lock] | None = None,
        known_chunks_only: bool = False,
        limits: dict[str, int] | None = None,
    ) -> None:
        self.ctx = ctx
        self.instance = instance
        self.role = role_of(instance)
        self.allowed = tools if tools is not None else ROLE_TOOLS[self.role]
        self.locks = locks or {}
        self.known_chunks_only = known_chunks_only
        # Per-tool caps on executed model-issued calls (D074); rejected and duplicate calls
        # do not count, and orchestrator-issued calls are not limited.
        self.limits = limits or {}
        self.executed: dict[str, int] = {}
        # Model-issued successful calls of this agent instance, by (server, tool, canonical
        # args) -> (call_id, computation_id, outcome, part); repeats reuse them (D067).
        self.memo: dict[tuple[str, str, str], tuple[str, str | None, ToolOutcome, Any]] = {}

    @property
    def specs(self) -> list[ToolSpec]:
        return [self.ctx.hub.specs[name] for name in self.allowed]

    @staticmethod
    def memo_key(call: ToolCall) -> tuple[str, str, str]:
        server = "quant" if call.name in QUANT_TOOLS else "edgar"
        return server, call.name, canonical_json(call.arguments)

    def _precheck(self, call: ToolCall) -> ToolOutcome | None:
        if call.arguments_error:
            return _local_error("INVALID_TOOL_ARGUMENTS", call.arguments_error)
        if call.name not in self.allowed:
            return _local_error(
                "TOOL_NOT_ALLOWED", f"{call.name} is not available to the {self.role} role."
            )
        lock = self.locks.get(call.name)
        if lock and (problem := lock(call.arguments)):
            return _local_error("ARGUMENT_LOCKED", problem)
        if self.known_chunks_only and call.name == "get_passage":
            if not self.ctx.ledger.known_chunk(str(call.arguments.get("chunk_id", ""))):
                return _local_error(
                    "ARGUMENT_LOCKED", "Only chunk IDs returned earlier in this run may be fetched."
                )
        return None

    async def call_many(self, calls: list[ToolCall]) -> list[ToolResultPart]:
        prepared, duplicates, first = [], {}, {}
        for index, call in enumerate(calls):  # IDs follow call order, before execution.
            call_id = self.ctx.next_call_id(self.instance)
            key = self.memo_key(call) if not call.arguments_error else None
            if key is not None and (key in self.memo or key in first):
                duplicates[index] = (call_id, key)
                continue
            if key is not None:
                first[key] = index
            cid = self.ctx.ledger.next_computation_id() if call.name in QUANT_TOOLS else None
            local = self._precheck(call) or self._limit(call)
            prepared.append((index, call, call_id, cid, local))
        outcomes = await asyncio.gather(
            *(self._execute(c, i, cid, local) for _, c, i, cid, local in prepared)
        )
        prepared = [entry[:4] for entry in prepared]
        parts: dict[int, ToolResultPart] = {}
        for (index, call, call_id, cid), outcome in zip(prepared, outcomes, strict=True):
            parts[index] = self._finish(call, call_id, cid, outcome)
        for (index, call, call_id, cid), outcome in zip(prepared, outcomes, strict=True):
            await self._record_result(call, call_id, cid, outcome, parts[index])
            if not outcome.is_error:
                self.memo[self.memo_key(call)] = (call_id, cid, outcome, parts[index])
        for index, (call_id, key) in sorted(duplicates.items()):
            parts[index] = await self._duplicate(calls[index], call_id, key, first, parts)
        return [parts[index] for index in range(len(calls))]

    def _limit(self, call: ToolCall) -> ToolOutcome | None:
        """Counted in call order before execution, so the cap is deterministic (D074)."""
        cap = self.limits.get(call.name)
        if cap is None:
            return None
        if self.executed.get(call.name, 0) >= cap:
            return _local_error(
                "CALL_LIMIT",
                f"{call.name} limit reached: at most {cap} calls per {self.role} worker. Use the "
                "results you already have (search snippets and passages already read) and "
                "return your final JSON.",
            )
        self.executed[call.name] = self.executed.get(call.name, 0) + 1
        return None

    async def _duplicate(self, call, call_id, key, first, parts) -> ToolResultPart:
        """Answer an identical repeat from the earlier result; traced, never re-executed."""
        if key in self.memo:
            original, cid, outcome, earlier = self.memo[key]
        else:  # repeated within one turn whose first copy failed: same error, no memo entry
            earlier = parts[first[key]]
            original, cid = None, None
            outcome = ToolOutcome(structured=None, is_error=earlier.is_error)
        part = ToolResultPart(
            tool_call_id=call.id,
            content=f"{DUPLICATE_NOTE} (call {original or 'in this turn'}).\n{earlier.content}",
            is_error=earlier.is_error,
        )
        payload = {
            "instance": self.instance,
            "call_id": call_id,
            "provider_call_id": call.id,
            "tool": call.name,
            "arguments": call.arguments,
            "computation_id": cid,
            "rejected": None,
            "duplicate_of": original,
        }
        await self.ctx.recorder.emit(self.role, "tool_call", payload)
        await self.ctx.recorder.emit(
            self.role,
            "tool_result",
            {
                "instance": self.instance,
                "call_id": call_id,
                "tool": call.name,
                "is_error": part.is_error,
                "structured": outcome.structured,
                "model_view_sha256": hashlib.sha256(part.content.encode()).hexdigest(),
                "computation_id": cid,
                "duplicate_of": original,
            },
            latency_ms=0,
        )
        return part

    async def call(
        self, tool: str, arguments: dict[str, Any]
    ) -> tuple[ToolOutcome, ToolResultPart]:
        """Orchestrator-issued call (direct data lookups, verification prefetch)."""
        call = ToolCall(id="orchestrator", name=tool, arguments=arguments)
        call_id = self.ctx.next_call_id(self.instance)
        cid = self.ctx.ledger.next_computation_id() if tool in QUANT_TOOLS else None
        outcome = await self._execute(call, call_id, cid, self._precheck(call))
        part = self._finish(call, call_id, cid, outcome)
        await self._record_result(call, call_id, cid, outcome, part)
        return outcome, part

    async def _execute(
        self, call: ToolCall, call_id: str, cid: str | None, local: ToolOutcome | None
    ) -> ToolOutcome:
        await self.ctx.recorder.emit(
            self.role,
            "tool_call",
            {
                "instance": self.instance,
                "call_id": call_id,
                "provider_call_id": call.id,
                "tool": call.name,
                "arguments": call.arguments,
                "computation_id": cid,
                "rejected": local.structured["error"]["code"] if local else None,
            },
        )
        if local:
            return local
        return await self.ctx.hub.call(call_id, call.name, call.arguments)

    def _finish(self, call, call_id, cid, outcome: ToolOutcome) -> ToolResultPart:
        self.ctx.ledger.register(
            call.name, call.arguments, outcome.structured, outcome.is_error, cid
        )
        payload: Any = outcome.structured
        if (
            call.name == "list_available_metrics"
            and not outcome.is_error
            and payload
            and "data" in payload
        ):
            payload = {"data": discovery_view(payload["data"])}
        return ToolResultPart(
            tool_call_id=call.id,
            content=envelope(call.name, call_id, payload, computation_id=cid),
            is_error=outcome.is_error,
        )

    async def _record_result(self, call, call_id, cid, outcome: ToolOutcome, part) -> None:
        raw = json.dumps(outcome.structured, sort_keys=True, ensure_ascii=False)
        await self.ctx.recorder.emit(
            self.role,
            "tool_result",
            {
                "instance": self.instance,
                "call_id": call_id,
                "tool": call.name,
                "is_error": outcome.is_error,
                "structured": outcome.structured,
                "raw_sha256": hashlib.sha256(raw.encode()).hexdigest(),
                "model_view_sha256": hashlib.sha256(part.content.encode()).hexdigest(),
                "view": DISCOVERY_VIEW_VERSION if call.name == "list_available_metrics" else None,
                "computation_id": cid,
            },
            latency_ms=outcome.latency_ms,
        )

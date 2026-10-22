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
from filinglens.llm.base import ToolCall, ToolResultPart, ToolSpec

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
    ) -> None:
        self.ctx = ctx
        self.instance = instance
        self.role = role_of(instance)
        self.allowed = tools if tools is not None else ROLE_TOOLS[self.role]
        self.locks = locks or {}
        self.known_chunks_only = known_chunks_only

    @property
    def specs(self) -> list[ToolSpec]:
        return [self.ctx.hub.specs[name] for name in self.allowed]

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
        prepared = []
        for call in calls:  # IDs are assigned in call order, before concurrent execution.
            call_id = self.ctx.next_call_id(self.instance)
            cid = self.ctx.ledger.next_computation_id() if call.name in QUANT_TOOLS else None
            prepared.append((call, call_id, cid))
        outcomes = await asyncio.gather(*(self._execute(c, i, cid) for c, i, cid in prepared))
        parts = []
        for (call, call_id, cid), outcome in zip(prepared, outcomes, strict=True):
            parts.append(self._finish(call, call_id, cid, outcome))
        for (call, call_id, cid), outcome, part in zip(prepared, outcomes, parts, strict=True):
            await self._record_result(call, call_id, cid, outcome, part)
        return parts

    async def call(
        self, tool: str, arguments: dict[str, Any]
    ) -> tuple[ToolOutcome, ToolResultPart]:
        """Orchestrator-issued call (direct data lookups, verification prefetch)."""
        call = ToolCall(id="orchestrator", name=tool, arguments=arguments)
        call_id = self.ctx.next_call_id(self.instance)
        cid = self.ctx.ledger.next_computation_id() if tool in QUANT_TOOLS else None
        outcome = await self._execute(call, call_id, cid)
        part = self._finish(call, call_id, cid, outcome)
        await self._record_result(call, call_id, cid, outcome, part)
        return outcome, part

    async def _execute(self, call: ToolCall, call_id: str, cid: str | None) -> ToolOutcome:
        local = self._precheck(call)
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

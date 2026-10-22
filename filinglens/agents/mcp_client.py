"""Stdio MCP client hub for edgar-mcp and quant-mcp with an explicit server environment (D054)."""

import asyncio
import os
import sys
import time
from contextlib import AsyncExitStack
from pathlib import Path
from typing import Any, Protocol

from mcp import Client, StdioServerParameters, stdio_client
from mcp.shared.exceptions import MCPError
from pydantic import BaseModel

from filinglens.config import ROOT, Settings
from filinglens.llm.base import ToolSpec, canonical_sha256
from filinglens.llm.tools import spec_from_mcp

EDGAR_TOOLS = (
    "resolve_company",
    "list_filings",
    "get_financial_metric",
    "list_available_metrics",
    "search_filings",
    "get_passage",
)
QUANT_TOOLS = ("growth_rate", "margin", "cagr", "yoy_series", "summary_stats", "evaluate")
SERVERS = {
    "edgar": ("mcp_servers.edgar_mcp.server", EDGAR_TOOLS),
    "quant": ("mcp_servers.quant_mcp.server", QUANT_TOOLS),
}
MODES = ("vector", "keyword", "hybrid", "hybrid_rerank")
REQUEST_TIMEOUT = -32001


class McpTransportError(RuntimeError):
    """The server process or protocol failed; the run cannot continue."""


class ToolOutcome(BaseModel):
    structured: dict[str, Any] | None
    is_error: bool
    latency_ms: int = 0


class ToolHub(Protocol):
    retrieval_mode: str
    specs: dict[str, ToolSpec]
    tool_specs_sha256: str

    async def call(self, call_id: str, tool: str, arguments: dict[str, Any]) -> ToolOutcome: ...


def server_python() -> str:
    venv = ROOT / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    return str(venv if venv.exists() else Path(sys.executable))


def server_env(settings: Settings, retrieval_mode: str) -> dict[str, str]:
    """Everything a server needs, built explicitly; no API keys, no inherited os.environ."""
    if retrieval_mode not in MODES:
        raise ValueError(f"retrieval_mode must be one of {MODES}")
    return {
        "PYTHONPATH": str(ROOT),
        "DATABASE_URL": settings.database_url,
        "SEC_USER_AGENT": settings.sec_user_agent,
        "SNAPSHOT_ID": settings.snapshot_id,
        "RETRIEVAL_CORPUS": settings.retrieval_corpus,
        "RETRIEVAL_MODE": retrieval_mode,
        "HF_HUB_OFFLINE": "1",
        "TRANSFORMERS_OFFLINE": "1",
        "HF_HUB_DISABLE_PROGRESS_BARS": "1",
    }


def specs_sha256(specs: dict[str, ToolSpec]) -> str:
    return canonical_sha256([specs[name].model_dump(mode="json") for name in sorted(specs)])


class McpHub:
    """Starts both stdio servers, verifies their tools and routes calls by tool name."""

    def __init__(
        self,
        settings: Settings,
        *,
        retrieval_mode: str,
        log_dir: Path,
        read_timeout_seconds: float = 120.0,
        cwd: Path = ROOT,
    ) -> None:
        self.env = server_env(settings, retrieval_mode)
        self.retrieval_mode = retrieval_mode
        self.log_dir = log_dir
        self.read_timeout_seconds = read_timeout_seconds
        self.cwd = cwd
        self.clients: dict[str, Any] = {}
        self.route: dict[str, str] = {}
        self.specs: dict[str, ToolSpec] = {}
        self.tool_specs_sha256 = ""
        self._stack = AsyncExitStack()

    async def __aenter__(self) -> "McpHub":
        self.log_dir.mkdir(parents=True, exist_ok=True)
        try:
            for server, (module, expected) in SERVERS.items():
                log = self._stack.enter_context(
                    (self.log_dir / f"{server}-mcp.stderr.log").open("w", encoding="utf-8")
                )
                params = StdioServerParameters(
                    command=server_python(), args=["-m", module], env=self.env, cwd=self.cwd
                )
                client = await self._stack.enter_async_context(
                    Client(
                        stdio_client(params, errlog=log),
                        mode="legacy",
                        read_timeout_seconds=self.read_timeout_seconds,
                    )
                )
                tools = (await client.list_tools()).tools
                names = {t.name for t in tools}
                if names != set(expected):
                    raise McpTransportError(
                        f"{server}-mcp tools {sorted(names)} differ from {sorted(expected)}"
                    )
                self.clients[server] = client
                for tool in tools:
                    self.route[tool.name] = server
                    self.specs[tool.name] = spec_from_mcp(tool)
        except BaseException:
            await self._stack.aclose()
            raise
        self.tool_specs_sha256 = specs_sha256(self.specs)
        return self

    async def __aexit__(self, *exc) -> None:
        await self._stack.aclose()

    async def call(self, call_id: str, tool: str, arguments: dict[str, Any]) -> ToolOutcome:
        server = self.route.get(tool)
        if server is None:
            return ToolOutcome(structured=_error("UNKNOWN_TOOL", tool), is_error=True)
        started = time.perf_counter()
        try:
            result = await self.clients[server].call_tool(tool, arguments)
        except MCPError as exc:
            if exc.code == REQUEST_TIMEOUT:
                return ToolOutcome(
                    structured=_error("TOOL_TIMEOUT", f"{tool} exceeded the client timeout."),
                    is_error=True,
                    latency_ms=int((time.perf_counter() - started) * 1000),
                )
            raise McpTransportError(f"{tool} failed at the protocol level: {exc.message}") from exc
        except (OSError, asyncio.CancelledError, RuntimeError) as exc:
            if isinstance(exc, asyncio.CancelledError):
                raise
            raise McpTransportError(f"{server}-mcp transport failed during {tool}") from exc
        structured = result.structured_content
        if tool == "search_filings" and not result.is_error:
            mode = (structured or {}).get("data", {}).get("retrieval_mode")
            if mode != self.retrieval_mode:
                raise McpTransportError(
                    f"edgar-mcp searched with {mode!r}, configured {self.retrieval_mode!r}"
                )
        return ToolOutcome(
            structured=structured,
            is_error=bool(result.is_error),
            latency_ms=int((time.perf_counter() - started) * 1000),
        )


def _error(code: str, message: str) -> dict[str, Any]:
    return {"error": {"code": code, "message": message}}

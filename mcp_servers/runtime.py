"""Official MCP v2 transport plus one typed, structured tool-error boundary."""

import asyncio
import inspect
import json
import logging
import os
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from decimal import ROUND_HALF_EVEN, DecimalException, localcontext
from typing import Any

import psycopg
from mcp.server import MCPServer
from mcp.types import (
    CallToolResult,
    ReadResourceResult,
    TextContent,
    TextResourceContents,
    ToolAnnotations,
)
from psycopg.conninfo import conninfo_to_dict, make_conninfo
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool, PoolTimeout
from pydantic import ValidationError

from filinglens.config import Settings
from filinglens.db import connection_options
from mcp_servers.decimal_math import ToolFailure
from mcp_servers.models import ErrorDetail, Input, Mode, Model, Response

logger = logging.getLogger(__name__)


class ServerSettings(Settings):
    retrieval_mode: Mode = "vector"


@asynccontextmanager
async def readonly_pool(url: str) -> AsyncIterator[AsyncConnectionPool]:
    options = conninfo_to_dict(url).get("options", "")
    readonly_url = make_conninfo(url, options=options + " -c default_transaction_read_only=on")
    async with AsyncConnectionPool(
        readonly_url,
        open=False,
        min_size=1,
        max_size=4,
        kwargs={**connection_options(url), "row_factory": dict_row},
    ) as pool:
        await pool.wait(timeout=30)
        yield pool


def failure(exc: Exception) -> ErrorDetail:
    if isinstance(exc, ToolFailure):
        return ErrorDetail(code=exc.code, message=str(exc))
    if isinstance(exc, ValidationError):
        paths = {str(e["loc"][0]) for e in exc.errors() if e["loc"]}
        code = "INVALID_INPUT"
        if paths & {"item", "items", "form"}:
            code = "INVALID_FILTER"
        elif "metric" in paths:
            code = "INVALID_METRIC"
        elif "values" in paths and any(e["type"] == "too_short" for e in exc.errors()):
            code = "INSUFFICIENT_DATA"
        elif "expression" in paths and any(
            e["type"] in {"string_too_short", "string_too_long"} for e in exc.errors()
        ):
            code = "EXPRESSION_LIMIT"
        return ErrorDetail(code=code, message="Check argument fields: " + ", ".join(sorted(paths)))
    if isinstance(exc, (psycopg.OperationalError, PoolTimeout)):
        return ErrorDetail(
            code="DATABASE_UNAVAILABLE", message="The configured database is unavailable."
        )
    if isinstance(exc, DecimalException):
        return ErrorDetail(code="NUMERIC_RANGE", message="The calculation exceeds Decimal bounds.")
    logger.error("Operation failed (%s); internal details withheld", type(exc).__name__)
    return ErrorDetail(
        code="INTERNAL_ERROR", message="The operation failed; inspect server stderr."
    )


def tool_result(payload: dict, *, is_error: bool = False) -> CallToolResult:
    return CallToolResult(
        content=[TextContent(type="text", text=json.dumps(payload, ensure_ascii=False))],
        structured_content=payload,
        is_error=is_error,
    )


class ContractServer(MCPServer):
    """Keep SDK transport/discovery/resources; own strict typed tool dispatch."""

    def __init__(self, name: str, **kwargs: Any) -> None:
        self.contracts: dict[str, tuple[type[Input], type[Model], Callable]] = {}
        super().__init__(name, **kwargs)

    def register(self, fn: Callable, inputs: type[Input], data: type[Model]) -> None:
        self.contracts[fn.__name__] = (inputs, data, fn)
        self.add_tool(
            fn,
            annotations=ToolAnnotations(
                read_only_hint=True,
                destructive_hint=False,
                idempotent_hint=True,
                open_world_hint=False,
            ),
        )

    def _tool_input_schema(self, name: str) -> None:
        # v2 validates before the handler otherwise, producing a native protocol
        # error. Strict Pydantic validation below owns the promised error envelope.
        return None

    async def list_tools(self):
        tools = await super().list_tools()
        for tool in tools:
            inputs, output, _ = self.contracts[tool.name]
            tool.input_schema = inputs.model_json_schema()
            tool.output_schema = Response[output].model_json_schema()
        return tools

    async def _handle_call_tool(self, ctx, params):
        return await self.call_tool(params.name, params.arguments or {})

    async def call_tool(self, name: str, arguments: dict, context=None) -> CallToolResult:
        try:
            if name not in self.contracts:
                raise ToolFailure("UNKNOWN_TOOL", "Use one of the tools returned by tools/list.")
            inputs, output, fn = self.contracts[name]
            request = inputs.model_validate(arguments)
            with localcontext() as ctx:
                ctx.prec = 80
                ctx.rounding = ROUND_HALF_EVEN
                value = fn(
                    **{field: getattr(request, field) for field in type(request).model_fields}
                )
                if inspect.isawaitable(value):
                    value = await value
                response = Response[output](data=value)
            # Omit only the unused top-level branch, not nested missing values.
            return tool_result({"data": response.model_dump(mode="json")["data"]})
        except Exception as exc:
            error = failure(exc)
            return tool_result({"error": error.model_dump()}, is_error=True)

    async def _handle_read_resource(self, ctx, params):
        try:
            return await super()._handle_read_resource(ctx, params)
        except Exception as exc:
            # Resources have contents, not CallToolResult/is_error.
            error = ErrorDetail(
                code="SECTION_NOT_FOUND", message="Unknown or invalid filing resource."
            )
            if isinstance(exc, ToolFailure):
                error = failure(exc)
            return ReadResourceResult(
                contents=[
                    TextResourceContents(
                        uri=params.uri,
                        mime_type="application/json",
                        text=json.dumps({"error": error.model_dump()}),
                    )
                ]
            )


def serve(server: MCPServer) -> None:
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"
    logging.basicConfig(level=logging.INFO)  # StreamHandler defaults to stderr.
    loop_factory = asyncio.SelectorEventLoop if os.name == "nt" else asyncio.new_event_loop
    with asyncio.Runner(loop_factory=loop_factory) as runner:
        runner.run(server.run_stdio_async())

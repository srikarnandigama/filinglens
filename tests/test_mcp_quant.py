"""Hand-made arithmetic cases are mathematical inputs, never invented SEC facts."""

import asyncio
import json
from decimal import Decimal, localcontext

import pytest
from mcp import Client, StdioServerParameters, stdio_client

from filinglens.config import ROOT
from mcp_servers.decimal_math import Expression, ToolFailure, computed, number
from mcp_servers.models import Response
from mcp_servers.quant_mcp.server import create_server


def run(coro):
    with asyncio.Runner() as runner:
        return runner.run(coro)


@pytest.mark.parametrize(
    "name,arguments,field,expected",
    [
        ("growth_rate", {"old": "100", "new": "125.3"}, "value_pct", "25.3"),
        ("growth_rate", {"old": -10, "new": 5}, "value_pct", "150"),
        ("growth_rate", {"old": 10, "new": -5}, "value_pct", "-150"),
        ("margin", {"numerator": 0.1, "denominator": 0.4}, "value_pct", "25"),
        ("margin", {"numerator": "1", "denominator": "-4"}, "value_pct", "-25"),
        ("cagr", {"start_value": "100", "end_value": "121", "years": 2}, "value_pct", "10"),
        ("cagr", {"start_value": 100, "end_value": 110, "years": 0.5}, "value_pct", "21"),
        ("summary_stats", {"values": [1, 2, 3]}, "stdev", "1"),
        ("summary_stats", {"values": [1, 2, 3, 4]}, "median", "2.5"),
        ("evaluate", {"expression": "-(2 + .5) × 4 ÷ 2 + 1"}, "value", "-4"),
        ("evaluate", {"expression": "1/3"}, "value", "0.333333333333"),
        ("evaluate", {"expression": "9007199254740993+1"}, "value", "9007199254740994"),
    ],
)
def test_quant_results_through_real_protocol(name, arguments, field, expected):
    async def exercise():
        async with Client(create_server(), raise_exceptions=True) as client:
            result = await client.call_tool(name, arguments)
            assert not result.is_error
            assert result.structured_content["data"][field] == expected
            assert json.loads(result.content[0].text) == result.structured_content

    run(exercise())


@pytest.mark.parametrize(
    "name,args,code",
    [
        ("growth_rate", {"old": 0, "new": 1}, "DIVISION_BY_ZERO"),
        ("margin", {"numerator": 1, "denominator": 0}, "DIVISION_BY_ZERO"),
        ("margin", {"numerator": True, "denominator": 1}, "INVALID_INPUT"),
        ("margin", {"numerator": "NaN", "denominator": 1}, "INVALID_INPUT"),
        ("margin", {"numerator": "1e3", "denominator": 1}, "INVALID_INPUT"),
        ("margin", {"numerator": "1" * 51, "denominator": 1}, "NUMERIC_RANGE"),
        ("margin", {"numerator": 1}, "INVALID_INPUT"),
        ("margin", {"numerator": 1, "denominator": 1, "mode": "other"}, "INVALID_INPUT"),
        ("cagr", {"start_value": 0, "end_value": 1, "years": 1}, "NON_POSITIVE_INPUT"),
        ("cagr", {"start_value": -1, "end_value": 1, "years": 1}, "NON_POSITIVE_INPUT"),
        ("cagr", {"start_value": 1, "end_value": 0, "years": 1}, "NON_POSITIVE_INPUT"),
        ("cagr", {"start_value": 1, "end_value": 2, "years": 0}, "INVALID_YEARS"),
        ("cagr", {"start_value": 1, "end_value": 2, "years": -1}, "INVALID_YEARS"),
        ("cagr", {"start_value": 1, "end_value": 2, "years": 1001}, "INVALID_YEARS"),
        (
            "yoy_series",
            {"values": [{"label": "a", "value": 0}, {"label": "b", "value": 1}]},
            "DIVISION_BY_ZERO",
        ),
        (
            "yoy_series",
            {"values": [{"label": "a", "value": 1}, {"label": "a", "value": 2}]},
            "DUPLICATE_LABEL",
        ),
        ("summary_stats", {"values": [1]}, "INSUFFICIENT_DATA"),
        ("summary_stats", {"values": []}, "INSUFFICIENT_DATA"),
        ("evaluate", {"expression": "1/0"}, "DIVISION_BY_ZERO"),
        ("evaluate", {"expression": "__import__('os')"}, "INVALID_EXPRESSION"),
        ("evaluate", {"expression": "2**3"}, "INVALID_EXPRESSION"),
        ("evaluate", {"expression": "1e3"}, "INVALID_EXPRESSION"),
        ("evaluate", {"expression": "2(3)"}, "INVALID_EXPRESSION"),
        ("evaluate", {"expression": "2//1"}, "INVALID_EXPRESSION"),
        ("evaluate", {"expression": "2%1"}, "INVALID_EXPRESSION"),
        ("evaluate", {"expression": "(1"}, "INVALID_EXPRESSION"),
        ("evaluate", {"expression": "(" * 34 + "1" + ")" * 34}, "EXPRESSION_LIMIT"),
        ("evaluate", {"expression": "1+" * 65 + "1"}, "EXPRESSION_LIMIT"),
        ("unknown", {}, "UNKNOWN_TOOL"),
    ],
)
def test_structured_errors_and_session_recovery(name, args, code):
    async def exercise():
        async with Client(create_server(), raise_exceptions=True) as client:
            result = await client.call_tool(name, args)
            assert result.is_error
            assert result.structured_content["error"]["code"] == code
            assert json.loads(result.content[0].text) == result.structured_content
            later = await client.call_tool("evaluate", {"expression": "1+1"})
            assert later.structured_content["data"]["value"] == "2"

    run(exercise())


def test_series_schema_decimal_precision_and_failure_boundary():
    async def exercise():
        server = create_server()
        async with Client(server, raise_exceptions=True) as client:
            tools = (await client.list_tools()).tools
            assert len(tools) == 6
            for tool in tools:
                assert tool.input_schema["additionalProperties"] is False
                assert "error" in tool.output_schema["properties"]
                assert 60 <= len(tool.description.split()) <= 150
            r = await client.call_tool(
                "yoy_series",
                {"values": [{"label": "2024", "value": "-10"}, {"label": "2025", "value": "5"}]},
            )
            points = r.structured_content["data"]["points"]
            assert points[0]["change_pct"] is None
            assert points[1]["change_pct"] == "150"
            inputs, output, _ = server.contracts["evaluate"]

            def broken(**kwargs):
                raise RuntimeError("sensitive internal detail")

            server.contracts["evaluate"] = (inputs, output, broken)
            r = await client.call_tool("evaluate", {"expression": "1"})
            assert r.is_error and r.structured_content["error"]["code"] == "INTERNAL_ERROR"
            assert "sensitive" not in r.content[0].text

    run(exercise())
    assert number(0.1) == Decimal("0.1")
    assert number(1e-20) == Decimal("0.00000000000000000001")
    assert number(9007199254740993) == Decimal("9007199254740993")
    for invalid in [True, float("nan"), float("inf"), float("-inf")]:
        with pytest.raises(ToolFailure):
            number(invalid)
    with localcontext() as ctx:
        ctx.prec = 80
        assert computed(Decimal("0.0000000000005")) == "0"
        assert computed(Decimal("0.0000000000015")) == "0.000000000002"
    with pytest.raises(ValueError):
        Response[str](data="x", error={"code": "x", "message": "x"})
    with pytest.raises(ToolFailure):
        Expression("1" * 513)


def test_quant_stdio_smoke(tmp_path):
    async def exercise():
        parameters = StdioServerParameters(
            command=str(ROOT / ".venv/Scripts/python.exe"),
            args=["-m", "mcp_servers.quant_mcp.server"],
            cwd=ROOT,
            env={"PYTHONPATH": str(ROOT), "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1"},
        )
        with (tmp_path / "quant-stderr.log").open("w", encoding="utf-8") as log:
            async with Client(stdio_client(parameters, errlog=log), mode="legacy") as client:
                assert len((await client.list_tools()).tools) == 6
                r = await client.call_tool("evaluate", {"expression": "-(2+3)*4"})
                assert r.structured_content["data"]["value"] == "-20"

    run(exercise())

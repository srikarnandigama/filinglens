"""Real stdio edgar-mcp/quant-mcp through the M4 hub; no LLM is involved."""

import json
import os
from decimal import Decimal

import pytest
from mcp.client.stdio import get_default_environment

from filinglens.agents.mcp_client import EDGAR_TOOLS, QUANT_TOOLS, McpHub, server_env
from filinglens.agents.settings import RuntimeSettings
from filinglens.agents.toolbox import ROLE_TOOLS, Toolbox
from filinglens.agents.views import discovery_view
from tests.agent_fakes import FakeHub, Script, calls, make_context, proactor_run

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.environ.get("FILINGLENS_TEST_DB") != "1", reason="Set FILINGLENS_TEST_DB=1"
    ),
]


def test_server_env_is_explicit_and_never_carries_keys(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "canary-not-a-key")
    monkeypatch.setenv("OPENAI_COMPAT_API_KEY", "canary-not-a-key")
    settings = RuntimeSettings()
    env = server_env(settings, "keyword")
    assert set(env) == {
        "PYTHONPATH",
        "DATABASE_URL",
        "SEC_USER_AGENT",
        "SNAPSHOT_ID",
        "RETRIEVAL_CORPUS",
        "RETRIEVAL_MODE",
        "HF_HUB_OFFLINE",
        "TRANSFORMERS_OFFLINE",
        "HF_HUB_DISABLE_PROGRESS_BARS",
    }
    assert env["RETRIEVAL_MODE"] == "keyword"
    inherited = get_default_environment()  # what the SDK adds to our explicit env
    assert "canary-not-a-key" not in json.dumps({**inherited, **env})
    with pytest.raises(ValueError):
        server_env(settings, "fast")


def test_hub_lists_tools_routes_calls_maps_errors_and_enforces_mode(tmp_path):
    async def exercise():
        settings = RuntimeSettings()
        # cwd outside the project proves PYTHONPATH and env are explicit.
        async with McpHub(
            settings, retrieval_mode="keyword", log_dir=tmp_path / "logs", cwd=tmp_path
        ) as hub:
            assert set(hub.specs) == set(EDGAR_TOOLS) | set(QUANT_TOOLS)
            assert len(hub.tool_specs_sha256) == 64
            for spec in hub.specs.values():
                assert "$ref" not in json.dumps(spec.input_schema)
            ok = await hub.call("x/t1", "resolve_company", {"query": "AAPL"})
            assert not ok.is_error and ok.structured["data"]["ticker"] == "AAPL"
            missing = await hub.call("x/t2", "resolve_company", {"query": "ZZZZZZ"})
            assert missing.is_error and missing.structured["error"]["code"] == "COMPANY_NOT_FOUND"
            bad = await hub.call("x/t3", "search_filings", {"query": "risk", "items": ["9"]})
            assert bad.is_error and bad.structured["error"]["code"] == "INVALID_FILTER"
            search = await hub.call(
                "x/t4",
                "search_filings",
                {
                    "query": "share repurchase",
                    "ticker": "AAPL",
                    "fiscal_year": 2025,
                    "fiscal_period": "FY",
                    "items": ["7"],
                    "k": 3,
                },
            )
            assert search.structured["data"]["retrieval_mode"] == "keyword"
            calc = await hub.call("x/t5", "margin", {"numerator": "1", "denominator": "4"})
            assert Decimal(calc.structured["data"]["value_pct"]) == 25
            hub.retrieval_mode = "vector"  # simulate a mismatch between config and server
            from filinglens.agents.mcp_client import McpTransportError

            with pytest.raises(McpTransportError, match="configured 'vector'"):
                await hub.call(
                    "x/t6",
                    "search_filings",
                    {"query": "risk", "ticker": "AAPL", "fiscal_year": 2025, "fiscal_period": "FY"},
                )
            discovery = await hub.call("x/t7", "list_available_metrics", {"ticker": "JPM"})
            return discovery.structured["data"]

    data = proactor_run(exercise())
    assert (tmp_path / "logs" / "edgar-mcp.stderr.log").exists()
    view = discovery_view(data)
    assert len(json.dumps(view)) < len(json.dumps(data)) / 4
    for raw, compact in zip(data["metrics"], view["metrics"], strict=True):
        listed = {(int(y), p) for y, ps in compact["available"].items() for p in ps}
        assert listed == {(p["fiscal_year"], p["fiscal_period"]) for p in raw["available_periods"]}
        hidden = {p for group in compact["not_available"] for p in group["periods"]}
        assert hidden == {
            f"FY{s['fiscal_year']} {s['fiscal_period']}"
            for s in raw["period_statuses"]
            if s["status"] != "available"
        }
        for field in ("latest_quarter", "latest_annual", "latest_year_end"):
            p = raw[field]
            assert compact[field] == (
                None if p is None else f"FY{p['fiscal_year']} {p['fiscal_period']}"
            )
    gross = next(m for m in view["metrics"] if m["metric"] == "gross_profit")
    assert gross["applicability_evidence_chunk_ids"]  # bank overlay evidence survives the view


async def test_role_toolboxes_expose_only_their_tools():
    ctx, _ = make_context(FakeHub({}), Script())
    assert [s.name for s in Toolbox(ctx, "planner").specs] == [
        "resolve_company",
        "list_available_metrics",
    ]
    assert [s.name for s in Toolbox(ctx, "filings:s1").specs] == ["search_filings", "get_passage"]
    assert [s.name for s in Toolbox(ctx, "analyst:r0").specs] == list(QUANT_TOOLS)
    assert ROLE_TOOLS["verifier"] == ("get_passage", "get_financial_metric")
    assert calls(("x", {})).tool_calls[0].name == "x"

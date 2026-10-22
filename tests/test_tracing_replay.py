"""Persisted traces in an isolated schema and offline replay with divergence detection."""

import os
import socket
from uuid import uuid4

import psycopg
import pytest
from psycopg import sql
from psycopg.conninfo import make_conninfo

import filinglens.agents.replay as replay_module
from db.migrate import migrate
from filinglens.agents import mcp_client, orchestrator
from filinglens.agents.mcp_client import McpHub
from filinglens.agents.orchestrator import RunConfig, run_question
from filinglens.agents.replay import replay_run
from filinglens.agents.tracing import PostgresTraceStore
from filinglens.db import connection_options
from tests.agent_fakes import ScriptedProvider, fake_prices, proactor_run
from tests.test_orchestrator import (
    lookup,
    planner,
    settings,
    single_value_analyst,
    verifier_all_supported,
)

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.environ.get("FILINGLENS_TEST_DB") != "1", reason="Set FILINGLENS_TEST_DB=1"
    ),
]


@pytest.fixture(scope="module")
def trace_db():
    url = settings().database_url
    schema = "test_m4_" + uuid4().hex
    with psycopg.connect(url, **connection_options(url), autocommit=True) as conn:
        conn.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
    isolated = make_conninfo(url, options=f"-csearch_path={schema},public")
    try:
        migrate(isolated)
        yield isolated
    finally:
        with psycopg.connect(url, **connection_options(url), autocommit=True) as conn:
            conn.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))


def aapl(v):
    return [lookup("s1", "AAPL", "revenue", [(2025, "Q2")])], []


def live_run(url, tmp_path, cfg=None):
    async def exercise():
        provider = ScriptedProvider(
            {
                "planner": planner(["AAPL"], aapl),
                "analyst": single_value_analyst,
                "verifier": verifier_all_supported,
            }
        )
        cfg_ = cfg or RunConfig(retrieval_mode="keyword")
        store = PostgresTraceStore(url)
        try:
            async with McpHub(settings(), retrieval_mode="keyword", log_dir=tmp_path) as hub:
                return await run_question(
                    "What was Apple's total revenue in fiscal Q2 2025?",
                    cfg_,
                    settings(),
                    providers={"anthropic": provider},
                    store=store,
                    prices=fake_prices("fake-large", "fake-small"),
                    hub=hub,
                )
        finally:
            store.close()

    return proactor_run(exercise())


def replay_offline(monkeypatch, url, run_id):
    """Replay must start no server, build no provider and resolve no remote host."""

    async def no_servers(self):
        raise AssertionError("replay started an MCP server")

    def no_providers(*args, **kwargs):
        raise AssertionError("replay built an LLM provider")

    real = socket.getaddrinfo

    def local_only(host, *args, **kwargs):
        if host not in {"localhost", "127.0.0.1", "::1", None}:
            raise AssertionError(f"replay attempted network access to {host}")
        return real(host, *args, **kwargs)

    with monkeypatch.context() as m:
        m.setattr(mcp_client.McpHub, "__aenter__", no_servers)
        m.setattr(orchestrator, "build_providers", no_providers)
        m.setattr(socket, "getaddrinfo", local_only)
        return proactor_run(replay_run(url, run_id))


def test_trace_rows_totals_and_identical_replay(trace_db, tmp_path, monkeypatch):
    result = live_run(trace_db, tmp_path)
    assert result.status == "done"
    with psycopg.connect(trace_db, **connection_options(trace_db)) as conn:
        status, answer, tokens_in, cost, finished, config = conn.execute(
            "SELECT status, answer, total_input_tokens, cost_usd, finished_at, config "
            "FROM runs WHERE id=%s",
            (result.run_id,),
        ).fetchone()
        kinds = [
            r[0]
            for r in conn.execute(
                "SELECT event_type FROM trace_events WHERE run_id=%s ORDER BY seq", (result.run_id,)
            )
        ]
        seqs = [
            r[0]
            for r in conn.execute(
                "SELECT seq FROM trace_events WHERE run_id=%s ORDER BY seq", (result.run_id,)
            )
        ]
    assert status == "done" and answer["final_value"] == result.answer.final_value
    assert tokens_in == result.totals.input_tokens > 0 and cost == result.totals.cost_usd
    assert finished is not None and seqs == list(range(1, len(seqs) + 1))
    assert {
        "tool_specs",
        "llm_call",
        "tool_call",
        "tool_result",
        "plan",
        "claim",
        "verification",
        "final",
        "agent_start",
        "agent_end",
    } <= set(kinds)
    assert config["models"]["analyst"] == {"env": "PLANNER_MODEL", "id": "fake-large"}
    assert config["pricing"]["models"]["fake-large"]["input_per_mtok"] == "1"
    assert set(config["prompts"]) >= {"planner", "analyst", "verifier"}

    report = replay_offline(monkeypatch, trace_db, result.run_id)
    assert report.identical, report.divergence
    assert (
        report.prompt_drift == [] and report.replay_answer_sha256 == report.recorded_answer_sha256
    )

    original = replay_module.load_prompts

    def drifted():
        prompts = original()
        system, sha = prompts["planner"]
        return {**prompts, "planner": (system + "\nExtra rule.", sha + "x")}

    monkeypatch.setattr(replay_module, "load_prompts", drifted)
    report = replay_offline(monkeypatch, trace_db, result.run_id)
    assert not report.identical and report.prompt_drift == ["planner"]
    assert "system prompt differs" in report.divergence
    monkeypatch.setattr(replay_module, "load_prompts", original)

    with psycopg.connect(trace_db, **connection_options(trace_db), autocommit=True) as conn:
        conn.execute(
            """UPDATE trace_events SET payload = jsonb_set(payload,
            '{structured,data,facts,0,value}', '"1"') WHERE run_id=%s
            AND event_type='tool_result' AND payload->>'tool'='get_financial_metric'""",
            (result.run_id,),
        )
    report = replay_offline(monkeypatch, trace_db, result.run_id)
    assert not report.identical and "analyst:r0" in report.divergence


def test_budget_failure_is_persisted_and_replayed(trace_db, tmp_path, monkeypatch):
    result = live_run(trace_db, tmp_path, RunConfig(retrieval_mode="keyword", max_run_tokens=150))
    assert result.status == "error" and result.error["type"] == "BudgetExceeded"
    assert result.error["kind"] == "tokens"
    with psycopg.connect(trace_db, **connection_options(trace_db)) as conn:
        status, error = conn.execute(
            "SELECT status, error FROM runs WHERE id=%s", (result.run_id,)
        ).fetchone()
        events = conn.execute(
            "SELECT count(*) FROM trace_events WHERE run_id=%s AND event_type='error'",
            (result.run_id,),
        ).fetchone()[0]
    assert status == "error" and error["type"] == "BudgetExceeded" and events == 1
    report = replay_offline(monkeypatch, trace_db, result.run_id)
    assert report.identical and report.recorded_status == "error"

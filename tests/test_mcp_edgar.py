"""Real-data isolated-schema checks for all EDGAR tools and resource cases."""

import asyncio
import json
import os
import threading
from decimal import Decimal
from uuid import uuid4

import anyio
import psycopg
import pytest
from mcp import Client, StdioServerParameters, stdio_client
from psycopg import sql
from psycopg.conninfo import make_conninfo

from db.migrate import migrate
from filinglens.config import ROOT
from filinglens.db import connection_options
from filinglens.edgar.xbrl import METRICS
from mcp_servers.decimal_math import ToolFailure
from mcp_servers.edgar_mcp.repository import EdgarRepository
from mcp_servers.edgar_mcp.server import create_server
from mcp_servers.models import Period
from mcp_servers.runtime import ServerSettings, readonly_pool

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.environ.get("FILINGLENS_TEST_DB") != "1", reason="Set FILINGLENS_TEST_DB=1"
    ),
]


def run(coro):
    with asyncio.Runner(loop_factory=asyncio.SelectorEventLoop) as runner:
        return runner.run(coro)


@pytest.fixture(scope="module")
def m3_settings():
    settings = ServerSettings()
    schema = "test_m3_" + uuid4().hex
    with psycopg.connect(
        settings.database_url, **connection_options(settings.database_url), autocommit=True
    ) as conn:
        conn.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
    isolated = settings.model_copy(
        update={
            "database_url": make_conninfo(
                settings.database_url, options=f"-csearch_path={schema},public"
            )
        }
    )
    try:
        migrate(isolated.database_url)
        policies = json.loads((ROOT / "mcp_servers/edgar_mcp/applicability.json").read_text())
        evidence_ids = [p["chunk_id"] for entry in policies.values() for p in entry["passages"]]
        with psycopg.connect(
            isolated.database_url, **connection_options(isolated.database_url)
        ) as c:
            # All values and passage bodies are copied from the accepted SEC data;
            # these are disposable test fixtures, never another production corpus.
            for table in [
                "ingestion_snapshots",
                "companies",
                "filings",
                "financial_facts",
                "metric_availability",
                "retrieval_corpora",
                "corpus_documents",
            ]:
                c.execute(f"INSERT INTO {table} SELECT * FROM public.{table}")
            c.execute(
                """CREATE TEMP TABLE selected_chunks AS
                SELECT ch.id,ch.section_id FROM public.chunks ch
                JOIN public.corpus_chunks cc ON cc.chunk_id=ch.id
                JOIN public.companies co ON co.cik=ch.cik
                WHERE cc.corpus_id=%s AND (
                  co.ticker='AAPL' OR ch.id=ANY(%s) OR
                  co.ticker='CVX' AND ch.fiscal_year=2024 AND ch.fiscal_period='FY' OR
                  co.ticker IN ('JNJ','XOM') AND ch.fiscal_year=2024 AND ch.fiscal_period='Q1')""",
                (settings.retrieval_corpus, evidence_ids),
            )
            c.execute(
                "INSERT INTO sections SELECT * FROM public.sections "
                "WHERE id IN (SELECT section_id FROM selected_chunks)"
            )
            c.execute("""INSERT INTO chunks(id,section_id,accession,cik,form,fiscal_year,
                fiscal_period,item,ordinal,text,token_count,embedding,source_hash,fingerprint,
                context_header,source_start,source_end,oversized_row,embedding_fingerprint,
                embedding_input_hash) SELECT id,section_id,accession,cik,form,fiscal_year,
                fiscal_period,item,ordinal,text,token_count,embedding,source_hash,fingerprint,
                context_header,source_start,source_end,oversized_row,embedding_fingerprint,
                embedding_input_hash FROM public.chunks
                WHERE id IN (SELECT id FROM selected_chunks)""")
            c.execute(
                "INSERT INTO corpus_chunks SELECT * FROM public.corpus_chunks "
                "WHERE corpus_id=%s AND chunk_id IN (SELECT id FROM selected_chunks)",
                (settings.retrieval_corpus,),
            )
        yield isolated
    finally:
        with psycopg.connect(
            settings.database_url, **connection_options(settings.database_url), autocommit=True
        ) as c:
            c.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))


def test_all_metadata_tools_real_protocol_and_provenance(m3_settings):
    async def exercise():
        async with Client(create_server(m3_settings), raise_exceptions=True) as client:
            tools = (await client.list_tools()).tools
            assert len(tools) == 6
            assert all(60 <= len(t.description.split()) <= 150 for t in tools)
            assert (
                "mode"
                not in next(t for t in tools if t.name == "search_filings").input_schema[
                    "properties"
                ]
            )
            r = await client.call_tool("resolve_company", {"query": "apple"})
            assert r.structured_content["data"]["ticker"] == "AAPL"
            r = await client.call_tool("list_filings", {"ticker": "AAPL", "form": "10-Q"})
            assert r.structured_content["data"]["filings"]
            assert all(
                f["fiscal_period"] in {"Q1", "Q2", "Q3"}
                for f in r.structured_content["data"]["filings"]
            )
            discovery = await client.call_tool("list_available_metrics", {"ticker": "AAPL"})
            data = discovery.structured_content["data"]
            assert len(data["metrics"]) == len(METRICS)
            period = data["latest_common_quarter"]
            request_period = {k: period[k] for k in ["fiscal_year", "fiscal_period"]}
            r = await client.call_tool(
                "get_financial_metric",
                {"ticker": "AAPL", "metric": "revenue", "periods": [request_period]},
            )
            fact = r.structured_content["data"]["facts"][0]
            assert fact["period_end"] == period["period_end"]
            assert fact["unit"] == "USD" and isinstance(fact["value"], str)
            async with readonly_pool(m3_settings.database_url) as p, p.connection() as c:
                source = await (
                    await c.execute(
                        "SELECT * FROM financial_facts WHERE id=%s", (int(fact["fact_id"]),)
                    )
                ).fetchone()
                assert source["value"] == Decimal(fact["value"])
                assert source["source_accession"] == fact["source_accession"]
                quarter = await (
                    await c.execute(
                        "SELECT fiscal_year FROM financial_facts "
                        "WHERE metric='revenue' AND derived AND cik='0000320193' LIMIT 1"
                    )
                ).fetchone()
                year = quarter["fiscal_year"]
            r = await client.call_tool(
                "get_financial_metric",
                {
                    "ticker": "AAPL",
                    "metric": "total_assets",
                    "periods": [
                        {"fiscal_year": year, "fiscal_period": "Q4"},
                        {"fiscal_year": year, "fiscal_period": "FY"},
                    ],
                },
            )
            q4, fy = r.structured_content["data"]["facts"]
            assert fy["fact_id"] == q4["fact_id"] and fy["value"] == q4["value"]
            assert fy["stored_fiscal_period"] == "Q4" and fy["fiscal_period"] == "FY"
            r = await client.call_tool(
                "get_financial_metric",
                {
                    "ticker": "AAPL",
                    "metric": "revenue",
                    "periods": [{"fiscal_year": year, "fiscal_period": "Q4"}],
                },
            )
            derived = r.structured_content["data"]["facts"][0]
            assert derived["derived"] and len(derived["derivation_inputs"]) >= 2
            assert all(i["source"]["url"] for i in derived["derivation_inputs"])
            r = await client.call_tool(
                "get_financial_metric",
                {
                    "ticker": "AAPL",
                    "metric": "eps_diluted",
                    "periods": [{"fiscal_year": 2199, "fiscal_period": "Q4"}],
                },
            )
            missing = r.structured_content["data"]["facts"][0]
            assert missing["value"] is None and missing["status"] == "unavailable"
            assert missing["derived"] is None and missing["unit"] == "USD/shares"

    run(exercise())


def test_bank_policy_evidence_and_missing_evidence(m3_settings):
    async def exercise():
        async with readonly_pool(m3_settings.database_url) as p:
            repo = EdgarRepository(m3_settings, p)
            await repo.initialize()
            for ticker in ["JPM", "BAC"]:
                r = await repo.get_financial_metric(
                    ticker, "gross_profit", [Period(fiscal_year=2024, fiscal_period="FY")]
                )
                fact = r.facts[0]
                assert fact.status == "not_applicable" and fact.value is None
                assert fact.stored_availability_status == "unavailable"
                assert fact.applicability_evidence[0].source.url
                inventory = await repo.list_available_metrics(ticker)
                assert (
                    next(m for m in inventory.metrics if m.metric == "gross_profit").status
                    == "not_applicable"
                )
            repo._policies["BAC"]["passages"][0]["chunk_id"] = "chk_" + "0" * 64
            r = await repo.get_financial_metric(
                "BAC", "gross_profit", [Period(fiscal_year=2024, fiscal_period="FY")]
            )
            assert r.facts[0].status == "unavailable"
            assert not r.facts[0].applicability_evidence
            with pytest.raises(psycopg.errors.ReadOnlySqlTransaction):
                async with p.connection() as connection:
                    await connection.execute("UPDATE companies SET name=name")

    run(exercise())


@pytest.mark.parametrize(
    "name,args,code",
    [
        ("resolve_company", {"query": "definitely not a company"}, "COMPANY_NOT_FOUND"),
        ("resolve_company", {"query": " "}, "INVALID_INPUT"),
        ("resolve_company", {"query": "Inc"}, "AMBIGUOUS_COMPANY"),
        ("list_filings", {"ticker": "AAPL", "form": "8-K"}, "INVALID_FILTER"),
        ("list_filings", {"ticker": "UNKNOWN"}, "COMPANY_NOT_FOUND"),
        ("list_available_metrics", {"ticker": "UNKNOWN"}, "COMPANY_NOT_FOUND"),
        (
            "get_financial_metric",
            {"ticker": "AAPL", "metric": "invented", "periods": []},
            "INVALID_METRIC",
        ),
        (
            "get_financial_metric",
            {"ticker": "AAPL", "metric": "revenue", "periods": []},
            "INVALID_INPUT",
        ),
        (
            "search_filings",
            {"query": "risk", "fiscal_period": "FY", "items": ["P1-2"]},
            "INVALID_FILTER",
        ),
        (
            "search_filings",
            {"query": "risk", "fiscal_period": "Q1", "items": ["7"]},
            "INVALID_FILTER",
        ),
        ("search_filings", {"query": "risk", "items": ["9"]}, "INVALID_FILTER"),
        ("search_filings", {"query": "risk", "mode": "keyword"}, "INVALID_INPUT"),
        ("search_filings", {"query": "risk", "k": True}, "INVALID_INPUT"),
        ("search_filings", {"query": " "}, "INVALID_INPUT"),
        ("get_passage", {"chunk_id": "bad"}, "INVALID_INPUT"),
        ("get_passage", {"chunk_id": "chk_" + "0" * 64}, "PASSAGE_NOT_FOUND"),
    ],
)
def test_edgar_structured_errors(name, args, code, m3_settings):
    async def exercise():
        async with Client(create_server(m3_settings), raise_exceptions=True) as client:
            r = await client.call_tool(name, args)
            assert r.is_error and r.structured_content["error"]["code"] == code
            assert json.loads(r.content[0].text) == r.structured_content
            r = await client.call_tool("resolve_company", {"query": "AAPL"})
            assert not r.is_error

    run(exercise())


def test_resource_reference_and_source_absence_and_full_passage(m3_settings):
    async def exercise():
        async with Client(create_server(m3_settings), raise_exceptions=True) as client:
            templates = await client.list_resource_templates()
            assert (
                str(templates.resource_templates[0].uri_template) == "filing://{accession}/{item}"
            )
            r = await client.read_resource("filing://0000093410-25-000009/7A")
            section = json.loads(r.contents[0].text)["data"]
            assert r.contents[0].mime_type == "application/json"
            diag = section["coverage_diagnostics"][0]
            assert diag["code"] == "REFERENCE_COVERED_ELSEWHERE"
            assert diag["target_resource"].endswith("/7")
            assert len(section["sections"][0]["text"]) < 1000
            r = await client.read_resource(diag["target_resource"])
            assert len(json.loads(r.contents[0].text)["data"]["sections"][0]["text"]) > 1000
            for ticker in ["JNJ", "XOM"]:
                filings = await client.call_tool(
                    "list_filings", {"ticker": ticker, "fiscal_year": 2024, "form": "10-Q"}
                )
                filing = next(
                    f
                    for f in filings.structured_content["data"]["filings"]
                    if f["fiscal_period"] == "Q1"
                )
                r = await client.read_resource(f"filing://{filing['accession']}/P2-1A")
                data = json.loads(r.contents[0].text)["data"]
                assert data["sections"] == [] and data["text"] is None
                assert data["coverage_diagnostics"][0]["code"] == "SOURCE_ABSENT"
                assert data["coverage_diagnostics"][0]["evidence_text"]
            r = await client.read_resource("filing://0000000000-00-000000/7")
            assert json.loads(r.contents[0].text)["error"]["code"] == "FILING_NOT_FOUND"
            r = await client.read_resource("filing://0000093410-25-000009/9")
            assert json.loads(r.contents[0].text)["error"]["code"] == "INVALID_FILTER"
            async with readonly_pool(m3_settings.database_url) as p, p.connection() as c:
                row = await (
                    await c.execute(
                        "SELECT c.id,c.text FROM chunks c WHERE length(text)>1200 LIMIT 1"
                    )
                ).fetchone()
            r = await client.call_tool("get_passage", {"chunk_id": row["id"]})
            data = r.structured_content["data"]
            assert data["text"] == row["text"] and not data["text_truncated"]
            assert data["score"] is None and data["content_trust"] == "untrusted_sec_text"
            r = await client.call_tool("search_filings", {"query": "risk", "fiscal_period": "Q4"})
            assert r.structured_content["data"]["hits"] == []
            assert r.structured_content["data"]["coverage_diagnostics"][0]["code"] == "NO_Q4_FILING"

    run(exercise())


def test_m2_parity_all_four_configured_modes(m3_settings, tmp_path, monkeypatch):
    import filinglens.retrieval.service as retrieval

    async def exercise():
        query = "What does Apple report about share repurchase authorization?"
        filters = dict(ticker="AAPL", fiscal_year=2025, fiscal_period="FY", k=8)
        for mode in retrieval.MODES:
            settings = m3_settings.model_copy(update={"retrieval_mode": mode})
            monkeypatch.setattr(retrieval, "ROOT", tmp_path / (mode + "-oracle"))
            async with readonly_pool(settings.database_url) as p:
                expected = await retrieval.SearchService(p, settings.retrieval_corpus).search(
                    query, mode=mode, **filters
                )
            monkeypatch.setattr(retrieval, "ROOT", tmp_path / (mode + "-tool"))
            async with Client(create_server(settings), raise_exceptions=True) as client:
                r = await client.call_tool("search_filings", {"query": query, **filters})
                assert not r.is_error, r.structured_content
                hits = r.structured_content["data"]["hits"]
                assert [h["chunk_id"] for h in hits] == [h.chunk_id for h in expected]
                assert [h["score"] for h in hits] == [h.score for h in expected]
                assert [h["text"] for h in hits] == [h.text[:1200] for h in expected]
                assert r.structured_content["data"]["retrieval_mode"] == mode

    run(exercise())


def test_edgar_stdio_smoke(m3_settings, tmp_path):
    async def exercise():
        env = {
            "PYTHONPATH": str(ROOT),
            "DATABASE_URL": m3_settings.database_url,
            "RETRIEVAL_CORPUS": m3_settings.retrieval_corpus,
            "SNAPSHOT_ID": m3_settings.snapshot_id,
            "RETRIEVAL_MODE": "vector",
            "SEC_USER_AGENT": m3_settings.sec_user_agent,
            "HF_HUB_OFFLINE": "1",
            "TRANSFORMERS_OFFLINE": "1",
        }
        parameters = StdioServerParameters(
            command=str(ROOT / ".venv/Scripts/python.exe"),
            args=["-m", "mcp_servers.edgar_mcp.server"],
            env=env,
            cwd=ROOT,
        )
        with (tmp_path / "edgar-stderr.log").open("w", encoding="utf-8") as log:
            async with Client(stdio_client(parameters, errlog=log), mode="legacy") as client:
                assert len((await client.list_tools()).tools) == 6
                r = await client.call_tool("list_available_metrics", {"ticker": "AAPL"})
                assert r.structured_content["data"]["latest_common_quarter"]

    # Subprocess creation requires Windows' default Proactor loop in the client.
    with asyncio.Runner() as runner:
        runner.run(exercise())


def test_context_validation_backend_failures_and_policy_conflict(m3_settings, monkeypatch):
    async def exercise():
        async with readonly_pool(m3_settings.database_url) as pool:
            for changes, code in [
                ({"snapshot_id": "missing"}, "SNAPSHOT_UNAVAILABLE"),
                ({"retrieval_corpus": "missing"}, "CORPUS_UNAVAILABLE"),
            ]:
                repo = EdgarRepository(m3_settings.model_copy(update=changes), pool)
                with pytest.raises(ToolFailure, match=".") as error:
                    await repo.initialize()
                assert error.value.code == code
            repo = EdgarRepository(m3_settings, pool)
            await repo.initialize()
            with pytest.raises(ToolFailure) as error:
                await repo.effective_status(
                    "JPM", "gross_profit", {"status": "unavailable"}, fact_exists=True
                )
            assert error.value.code == "DATA_INTEGRITY"
            repo._policies["JPM"]["passages"][0]["text_sha256"] = "incorrect"
            with pytest.raises(ToolFailure) as error:
                await repo.applicability("JPM")
            assert error.value.code == "DATA_INTEGRITY"
        server = create_server(m3_settings)
        async with Client(server, raise_exceptions=True) as client:

            async def unavailable(*args, **kwargs):
                raise psycopg.OperationalError("database URL must not be exposed")

            monkeypatch.setattr(server.repository, "rows", unavailable)
            r = await client.call_tool("list_filings", {"ticker": "AAPL"})
            assert r.is_error and r.structured_content["error"]["code"] == "DATABASE_UNAVAILABLE"
            assert "URL" not in r.content[0].text

    run(exercise())


def test_worker_cancellation_keeps_inference_slot_and_protocol_responsive(m3_settings, monkeypatch):
    async def exercise():
        started, release = threading.Event(), threading.Event()
        active, peak = 0, 0
        server = create_server(m3_settings)
        async with Client(server, raise_exceptions=True, mode="legacy") as client:

            def blocked(query, filters):
                nonlocal active, peak
                active += 1
                peak = max(peak, active)
                started.set()
                assert release.wait(timeout=10), "Test worker timed out"
                active -= 1
                return []

            monkeypatch.setattr(server.repository, "_retrieve", blocked)
            scope = anyio.CancelScope()

            async def first():
                with scope:
                    await client.call_tool("search_filings", {"query": "first", "ticker": "AAPL"})

            async def second():
                await client.call_tool("search_filings", {"query": "second", "ticker": "AAPL"})

            async with anyio.create_task_group() as tasks:
                tasks.start_soon(first)
                assert await anyio.to_thread.run_sync(lambda: started.wait(timeout=5))
                try:
                    scope.cancel()
                    tasks.start_soon(second)
                    with anyio.fail_after(3):
                        with pytest.warns(Warning, match="ping is removed"):
                            await client.send_ping()
                        response = await client.call_tool("resolve_company", {"query": "AAPL"})
                        assert not response.is_error
                    assert active == 1
                finally:
                    release.set()
            assert peak == 1

    run(exercise())

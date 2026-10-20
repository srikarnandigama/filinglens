"""Integration checks against the M1 Docker database (explicitly enabled)."""

import asyncio
import json
import os
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import psycopg
import pytest
import respx
from psycopg import sql
from psycopg.conninfo import make_conninfo

from db.migrate import migrate
from filinglens.config import Settings
from filinglens.db import connection_options
from filinglens.edgar.tickers import UNIVERSE
from filinglens.ingest.pipeline import ingest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.environ.get("FILINGLENS_TEST_DB") != "1",
        reason="Set FILINGLENS_TEST_DB=1 for local DB tests",
    ),
]


@pytest.fixture
def test_database():
    url = Settings().database_url
    schema = "test_" + uuid4().hex
    with psycopg.connect(url, **connection_options(url), autocommit=True) as conn:
        conn.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
    test_url = make_conninfo(url, options=f"-csearch_path={schema},public")
    try:
        yield test_url, schema
    finally:
        with psycopg.connect(url, **connection_options(url), autocommit=True) as conn:
            conn.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))


def test_clean_migration_rerun_and_indexes(test_database):
    url, schema = test_database
    migrate(url)
    migrate(url)
    with psycopg.connect(url, **connection_options(url)) as conn:
        assert conn.execute("SELECT count(*) FROM schema_migrations").fetchone()[0] == 3
        indexes = {
            row[0]
            for row in conn.execute(
                "SELECT indexname FROM pg_indexes WHERE schemaname=%s", (schema,)
            )
        }
        assert {"chunks_embedding_hnsw", "chunks_tsv_gin", "facts_period_idx"} <= indexes
        assert conn.execute("SELECT extversion FROM pg_extension WHERE extname='vector'").fetchone()
        conn.execute("INSERT INTO companies VALUES ('0000320193','TEST','test','0927')")
        conn.execute("INSERT INTO ingestion_snapshots(id,cutoff_date) VALUES ('test','2026-10-19')")
        # NULLS NOT DISTINCT protects instant facts on repeated ingest.
        insert = """INSERT INTO financial_facts(cik,metric,concept,period_type,end_date,
        fiscal_year,fiscal_period,value,unit,source_filed,snapshot_id)
        SELECT cik,'total_assets','Assets','instant',end_date,fiscal_year,fiscal_period,
        value,unit,source_filed,'test' FROM public.financial_facts
        WHERE cik='0000320193' AND metric='total_assets' LIMIT 1"""
        conn.execute(insert)
        with pytest.raises(psycopg.errors.UniqueViolation), conn.transaction():
            conn.execute(insert)


def test_failed_migration_rolls_back_and_changed_migration_rejected(test_database, tmp_path):
    url, _ = test_database
    migration = tmp_path / "001_test.sql"
    migration.write_text("CREATE TABLE rollback_probe(id int); SELECT missing_test_function();")
    with pytest.raises(psycopg.errors.UndefinedFunction):
        migrate(url, tmp_path)
    with psycopg.connect(url, **connection_options(url)) as conn:
        assert conn.execute("SELECT to_regclass('rollback_probe')").fetchone()[0] is None
    migration.write_text("CREATE TABLE rollback_probe(id int);")
    migrate(url, tmp_path)
    migration.write_text("CREATE TABLE rollback_probe(id bigint);")
    with pytest.raises(RuntimeError, match="Applied migration changed"):
        migrate(url, tmp_path)


def test_twelve_stored_values_and_provenance():
    expected = json.loads((Path(__file__).parent / "fixtures/revenue_expected.json").read_text())
    url = Settings().database_url
    with psycopg.connect(url, **connection_options(url)) as conn:
        for company in expected["companies"]:
            for row in company["expected"]:
                stored = conn.execute(
                    """SELECT value,unit,derived,derivation_inputs FROM financial_facts
                    WHERE snapshot_id=%s AND cik=%s AND metric='revenue'
                    AND fiscal_year=%s AND fiscal_period=%s""",
                    (
                        expected["snapshot"],
                        company["cik"],
                        row["fiscal_year"],
                        row["fiscal_period"],
                    ),
                ).fetchone()
                assert stored is not None
                assert stored[0] == Decimal(row["value"])
                assert stored[1] == row["unit"]
                if stored[2]:
                    assert (
                        sum(Decimal(item["value"]) * item["coefficient"] for item in stored[3])
                        == stored[0]
                    )


def test_full_cached_rerun_preserves_values_and_fact_ids(test_database):
    # Replay M1 in an isolated copy: corpus repair must never write public facts
    # or the accepted snapshot manifest, even when running the full test suite.
    url, _ = test_database
    migrate(url)
    with psycopg.connect(url, **connection_options(url)) as conn:
        for table in (
            "ingestion_snapshots",
            "companies",
            "filings",
            "financial_facts",
            "metric_availability",
        ):
            conn.execute(
                sql.SQL("INSERT INTO {} SELECT * FROM public.{}").format(
                    sql.Identifier(table), sql.Identifier(table)
                )
            )
        conn.execute(
            "SELECT setval(pg_get_serial_sequence('financial_facts','id'), "
            "(SELECT max(id) FROM financial_facts))"
        )
    settings = Settings(database_url=url)

    def rows():
        with psycopg.connect(
            settings.database_url, **connection_options(settings.database_url)
        ) as conn:
            return conn.execute(
                "SELECT * FROM financial_facts WHERE snapshot_id=%s ORDER BY id",
                (settings.snapshot_id,),
            ).fetchall()

    before = rows()
    assert before
    # A cache-only acceptance rerun must not silently fall back to live SEC data.
    with respx.mock(assert_all_called=False) as mock:
        mock.route().mock(side_effect=AssertionError("Unexpected SEC network request"))
        with asyncio.Runner(loop_factory=asyncio.SelectorEventLoop) as runner:
            totals = runner.run(ingest(settings, list(UNIVERSE)))
    assert totals["companies"] == len(UNIVERSE)
    assert totals["network_requests"] == 0
    assert rows() == before

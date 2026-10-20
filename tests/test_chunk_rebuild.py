"""A real filing produces identical IDs after rebuilding empty passage tables."""

import asyncio
import json
import os
from pathlib import Path

import psycopg
import pytest
import respx

from db.migrate import migrate
from filinglens.config import Settings
from filinglens.db import connection_options
from filinglens.ingest.corpus import prepare_corpus
from filinglens.ingest.models import MODEL_DIR
from tests.test_database import test_database as database_fixture

test_database = database_fixture
pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.environ.get("FILINGLENS_TEST_DB") != "1", reason="Set FILINGLENS_TEST_DB=1"
    ),
]


def test_real_filing_rebuild_from_empty_tables_preserves_ids(test_database, monkeypatch):
    url, _ = test_database
    fixture = json.loads((Path(__file__).parent / "fixtures/revenue_expected.json").read_text())
    company = fixture["companies"][1]
    source = company["sources"]["Q3"]
    if not Path(source["cached_file"]).exists() or not (MODEL_DIR / "revisions.json").exists():
        pytest.skip("Requires real cached filing and pinned tokenizers")
    migrate(url)
    settings = Settings(database_url=url)
    with psycopg.connect(url, **connection_options(url)) as conn:
        conn.execute(
            "INSERT INTO ingestion_snapshots(id,cutoff_date) VALUES (%s,%s)",
            (settings.snapshot_id, settings.ingestion_cutoff),
        )
        conn.execute(
            "INSERT INTO companies VALUES (%s,'MSFT','Microsoft','0630')", (company["cik"],)
        )
        conn.execute(
            "INSERT INTO filings VALUES (%s,%s,'10-Q',%s,%s,2025,'Q3',%s)",
            (
                source["accession"],
                company["cik"],
                source["filing_date"],
                source["report_date"],
                source["url"],
            ),
        )

    def run():
        with respx.mock(assert_all_called=False) as mock:
            mock.route().mock(side_effect=AssertionError("Network forbidden"))
            with asyncio.Runner(loop_factory=asyncio.SelectorEventLoop) as runner:
                result = runner.run(prepare_corpus(settings, ["MSFT"], stage="parse", force=True))
        assert not result["failed"] and result["network_requests"] == 0
        with psycopg.connect(url, **connection_options(url)) as conn:
            return conn.execute("SELECT id,section_id,text FROM chunks ORDER BY id").fetchall()

    before = run()
    assert before
    with psycopg.connect(url, **connection_options(url)) as conn:
        # These are isolated test-schema tables, never public passages.
        conn.execute("DELETE FROM corpus_chunks")
        conn.execute("DELETE FROM chunks")
        conn.execute("DELETE FROM sections")
    assert run() == before

    def forbid_reparse(*_):
        raise AssertionError("Completed parsing must be skipped on resume")

    monkeypatch.setattr("filinglens.ingest.corpus.parse_filing", forbid_reparse)
    with asyncio.Runner(loop_factory=asyncio.SelectorEventLoop) as runner:
        resumed = runner.run(prepare_corpus(settings, ["MSFT"], stage="parse"))
    assert resumed["skipped"] == 1 and resumed["completed"] == 0
    monkeypatch.undo()
    # Expanding ingestion scope must not alter an existing filing's citation IDs.
    another = company["sources"]["Q2"]
    with psycopg.connect(url, **connection_options(url)) as conn:
        conn.execute(
            "INSERT INTO filings VALUES (%s,%s,'10-Q',%s,%s,2025,'Q2',%s)",
            (
                another["accession"],
                company["cik"],
                another["filing_date"],
                another["report_date"],
                another["url"],
            ),
        )
    with respx.mock(assert_all_called=False) as mock:
        mock.route().mock(side_effect=AssertionError("Network forbidden"))
        with asyncio.Runner(loop_factory=asyncio.SelectorEventLoop) as runner:
            expanded = runner.run(prepare_corpus(settings, ["MSFT"], stage="parse"))
    assert not expanded["failed"]
    with psycopg.connect(url, **connection_options(url)) as conn:
        after = conn.execute(
            "SELECT id,section_id,text FROM chunks WHERE accession=%s ORDER BY id",
            (source["accession"],),
        ).fetchall()
    assert after == before

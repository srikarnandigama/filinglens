"""Normal parse-stage v2 integration in an isolated schema, with HTTP forbidden."""

import asyncio
import os

import psycopg
import pytest

from db.migrate import migrate
from filinglens.config import Settings
from filinglens.db import connection_options
from filinglens.ingest.corpus import prepare_corpus
from filinglens.ingest.embed import run_embeddings
from tests.test_database import test_database as database_fixture

test_database = database_fixture
pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.environ.get("FILINGLENS_TEST_DB") != "1", reason="Set FILINGLENS_TEST_DB=1"
    ),
]


def test_normal_offline_parse_expands_nvidia_and_replays_identical_ids(test_database, monkeypatch):
    url, _ = test_database
    migrate(url)
    settings = Settings(database_url=url)
    accession = "0001045810-25-000023"
    with psycopg.connect(url, **connection_options(url)) as conn:
        conn.execute("INSERT INTO companies SELECT * FROM public.companies WHERE ticker='NVDA'")
        conn.execute(
            "INSERT INTO filings SELECT * FROM public.filings WHERE accession=%s", (accession,)
        )
        conn.execute(
            "INSERT INTO ingestion_snapshots(id,cutoff_date) VALUES (%s,%s)",
            (settings.snapshot_id, settings.ingestion_cutoff),
        )

    def no_client(*args, **kwargs):
        raise AssertionError("Offline parse must not construct an HTTP client")

    monkeypatch.setattr("filinglens.edgar.client.EdgarClient.__init__", no_client)

    def run(force=False):
        with asyncio.Runner(loop_factory=asyncio.SelectorEventLoop) as runner:
            return runner.run(
                prepare_corpus(settings, ["NVDA"], stage="parse", offline=True, force=force)
            )

    first = run()
    assert first["completed"] == 1 and not first["failed"]
    assert first["network_requests"] == 0
    with psycopg.connect(url, **connection_options(url)) as conn:
        before = conn.execute("SELECT id,section_id,text FROM chunks ORDER BY id").fetchall()
        assert (
            conn.execute("SELECT length(text) FROM sections WHERE item='8'").fetchone()[0] > 50000
        )
        assert conn.execute("SELECT count(*) FROM chunks WHERE item='8'").fetchone()[0] > 30
        assert conn.execute("SELECT manifest FROM ingestion_snapshots").fetchone()[0] == {}
        assert (
            conn.execute(
                "SELECT count(*) FROM document_processing WHERE fingerprint='primary-v1'"
            ).fetchone()[0]
            == 0
        )
        conn.execute("DELETE FROM corpus_chunks")
        conn.execute("DELETE FROM chunks")
        conn.execute("DELETE FROM sections")
    assert not run(force=True)["failed"]
    with psycopg.connect(url, **connection_options(url)) as conn:
        assert (
            conn.execute("SELECT id,section_id,text FROM chunks ORDER BY id").fetchall() == before
        )
    assert run()["skipped"] == 1
    with psycopg.connect(url, **connection_options(url)) as conn:
        conn.execute("UPDATE retrieval_corpora SET frozen=TRUE WHERE id=%s", (first["corpus_id"],))
    with pytest.raises(ValueError, match="Frozen corpora"):
        run(force=True)
    with asyncio.Runner(loop_factory=asyncio.SelectorEventLoop) as runner:
        with pytest.raises(ValueError, match="Frozen corpora"):
            runner.run(run_embeddings(settings, first["corpus_id"], benchmark=False))

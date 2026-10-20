import asyncio
import os

import psycopg
import pytest

from db.migrate import migrate
from filinglens.config import Settings
from filinglens.db import connection_options
from filinglens.ingest import embed
from tests.test_database import test_database as database_fixture

test_database = database_fixture
pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.environ.get("FILINGLENS_TEST_DB") != "1", reason="Set FILINGLENS_TEST_DB=1"
    ),
]


def test_interrupted_embedding_resumes_only_uncommitted_batches(test_database, monkeypatch):
    url, _ = test_database
    migrate(url)
    with psycopg.connect(url, **connection_options(url)) as conn:
        conn.execute("INSERT INTO ingestion_snapshots(id,cutoff_date) VALUES ('s','2026-10-19')")
        conn.execute("INSERT INTO retrieval_corpora VALUES ('c','s','{}',false)")
        conn.execute("INSERT INTO companies VALUES ('test','TEST','test','1231')")
        conn.execute(
            "INSERT INTO filings VALUES ('f','test','10-K','2025-01-01',"
            "'2024-12-31',2024,'FY','https://www.sec.gov/test')"
        )
        conn.execute(
            "INSERT INTO sections VALUES ('section','f','7','MD&A','passage','hash','fp',0,'[]')"
        )
        for i in range(33):
            conn.execute(
                """INSERT INTO chunks(id,section_id,accession,cik,form,fiscal_year,
                fiscal_period,item,ordinal,text,token_count,source_hash,fingerprint,
                context_header,source_start,source_end)
                VALUES (%s,'section','f','test','10-K',2024,'FY','7',%s,'test passage',3,
                'hash','fp','header',0,1)""",
                (f"chunk{i}", i),
            )
            conn.execute("INSERT INTO corpus_chunks VALUES ('c',%s)", (f"chunk{i}",))
    settings = Settings(
        _env_file=None,
        database_url=url,
        snapshot_id="s",
        sec_user_agent="FilingLens tests test@example.org",
    )
    calls = []

    def interrupted(rows):
        calls.append([r["id"] for r in rows])
        if len(calls) == 3:
            raise RuntimeError("simulated power interruption")
        return [[1.0] + [0.0] * 383 for _ in rows]

    monkeypatch.setattr(embed, "embedding_fingerprint", lambda: "test-embedding")
    monkeypatch.setattr(embed, "embedder", lambda: object())
    monkeypatch.setattr(embed, "encode_chunks", interrupted)
    with asyncio.Runner(loop_factory=asyncio.SelectorEventLoop) as runner:
        with pytest.raises(RuntimeError, match="simulated"):
            runner.run(embed.run_embeddings(settings, "c", benchmark=False))
    with psycopg.connect(url, **connection_options(url)) as conn:
        saved = {r[0] for r in conn.execute("SELECT id FROM chunks WHERE embedding IS NOT NULL")}
    assert len(saved) == 16
    calls.clear()

    def resumed(rows):
        calls.append([r["id"] for r in rows])
        return [[1.0] + [0.0] * 383 for _ in rows]

    monkeypatch.setattr(embed, "encode_chunks", resumed)
    with asyncio.Runner(loop_factory=asyncio.SelectorEventLoop) as runner:
        result = runner.run(embed.run_embeddings(settings, "c", benchmark=False))
    assert result["sample_chunks"] == 17
    assert not saved.intersection(key for batch in calls for key in batch)
    calls.clear()
    with asyncio.Runner(loop_factory=asyncio.SelectorEventLoop) as runner:
        result = runner.run(embed.run_embeddings(settings, "c", benchmark=False))
    assert result["sample_chunks"] == 0 and not calls
    with psycopg.connect(url, **connection_options(url)) as conn:
        conn.execute("UPDATE chunks SET context_header='changed header' WHERE id='chunk0'")
    with asyncio.Runner(loop_factory=asyncio.SelectorEventLoop) as runner:
        result = runner.run(embed.run_embeddings(settings, "c", benchmark=False))
    assert result["sample_chunks"] == 1
    assert {key for batch in calls for key in batch} == {"chunk0"}

"""Real pgvector tests using isolated synthetic passages, not invented financial facts."""

import asyncio
import os
from unittest.mock import patch

import psycopg
import pytest
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from db.migrate import migrate
from filinglens.db import connection_options
from filinglens.retrieval.service import SearchService
from tests.test_database import test_database as database_fixture

test_database = database_fixture

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.environ.get("FILINGLENS_TEST_DB") != "1", reason="Set FILINGLENS_TEST_DB=1"
    ),
]


def test_filtered_full_k_and_hnsw_underfill_falls_back_to_exact(test_database):
    url, _ = test_database
    migrate(url)
    with psycopg.connect(url, **connection_options(url)) as conn:
        conn.execute("INSERT INTO ingestion_snapshots(id,cutoff_date) VALUES ('s','2026-10-19')")
        conn.execute("INSERT INTO retrieval_corpora VALUES ('corpus','s','{}',false)")
        for key, ticker in [("target", "TARGET"), ("other", "OTHER")]:
            conn.execute("INSERT INTO companies VALUES (%s,%s,'test','1231')", (key, ticker))
            conn.execute(
                "INSERT INTO filings VALUES (%s,%s,'10-K','2025-01-01',"
                "'2024-12-31',2024,'FY','https://www.sec.gov/test')",
                (key, key),
            )
            conn.execute(
                "INSERT INTO sections VALUES (%s,%s,'7','MD&A','passage','hash','fp',0,'[]')",
                (key, key),
            )
        # Vary components to avoid tie-dependent index behavior.
        for index in range(1800):
            target = index < 40
            key = "target" if target else "other"
            vector = [0.01 if target else 1.0, 1.0 if target else 0.01]
            vector += [((index * 37 + j * 11) % 101) / 10000 for j in range(382)]
            cid = f"chunk{index:05}"
            conn.execute(
                """INSERT INTO chunks(id,section_id,accession,cik,form,fiscal_year,
                fiscal_period,item,ordinal,text,token_count,embedding,source_hash,fingerprint,
                context_header,source_start,source_end,embedding_fingerprint)
                VALUES (%s,%s,%s,%s,'10-K',2024,'FY','7',%s,'test passage',3,%s::vector,
                'hash','fp','test header',0,1,'embedding-test')""",
                (cid, key, key, key, index, str(vector)),
            )
            conn.execute("INSERT INTO corpus_chunks VALUES ('corpus',%s)", (cid,))
        conn.execute("ANALYZE chunks")

    async def exercise():
        async def configure(conn):
            await conn.execute("SET hnsw.max_scan_tuples=1")
            await conn.execute("SET enable_sort=off")
            await conn.commit()

        async with AsyncConnectionPool(
            url,
            open=False,
            min_size=1,
            max_size=2,
            kwargs=connection_options(url),
            configure=configure,
        ) as pool:
            await pool.wait()
            service = SearchService(pool, "corpus")
            vector = [1.0] + [0.0] * 383
            filters = dict(ticker="TARGET", fiscal_year=2024, fiscal_period="FY")
            exact = await service.vector(vector, 30, exact=True, **filters)
            assert len(exact) == 30
            assert all(
                h.ticker == "TARGET" and h.fiscal_year == 2024 and h.fiscal_period == "FY"
                for h in exact
            )
            # Independent exact oracle, using a filtered materialized relation.
            async with pool.connection() as conn:
                conn.row_factory = dict_row
                oracle = await (
                    await conn.execute(
                        """WITH eligible AS MATERIALIZED (
                    SELECT id,embedding FROM chunks WHERE cik='target'
                    AND fiscal_year=2024 AND fiscal_period='FY')
                    SELECT id FROM eligible ORDER BY embedding <=> %s::vector,id LIMIT 30""",
                        (str(vector),),
                    )
                ).fetchall()
                where, args = service.filters(**filters)
                plan = await (
                    await conn.execute(
                        f"EXPLAIN (FORMAT JSON) SELECT c.id {service.source} WHERE {where} "
                        "AND c.embedding IS NOT NULL AND c.embedding_fingerprint=%s "
                        "ORDER BY c.embedding <=> %s::vector LIMIT 30",
                        [*args, "embedding-test", str(vector)],
                    )
                ).fetchone()
                assert "chunks_embedding_hnsw" in str(plan)
            assert [h.chunk_id for h in exact] == [r["id"] for r in oracle]
            import numpy as np

            class QueryModel:
                def encode(self, *args, **kwargs):
                    assert args[0][0].startswith(
                        "Represent this sentence for searching relevant passages: "
                    )
                    return np.array([vector])

            class QueryTokenizer:
                def encode(self, text):
                    return [1, 2]

            with (
                patch("filinglens.retrieval.service.embedder", return_value=QueryModel()),
                patch("filinglens.retrieval.service.tokenizer", return_value=QueryTokenizer()),
            ):
                public_hits = await service.search("test passage", mode="vector", k=10, **filters)
            assert len(public_hits) == 10
            assert [h.chunk_id for h in public_hits] == [h.chunk_id for h in exact[:10]]
            recovered = await service.vector(vector, 30, exact=False, **filters)
            assert service.exact_fallbacks == 1
            assert [h.chunk_id for h in recovered] == [h.chunk_id for h in exact]
            assert len(await service.vector(vector, 100, exact=True, **filters)) == 40
            assert not await service.vector(vector, 10, exact=True, ticker="MISSING")

    with patch("filinglens.retrieval.service.embedding_fingerprint", return_value="embedding-test"):
        with asyncio.Runner(loop_factory=asyncio.SelectorEventLoop) as runner:
            runner.run(exercise())


def test_keyword_or_lexemes_partial_matches_stopwords_and_all_filters(test_database):
    """Synthetic search passages exercise semantics without using evaluation questions."""
    from filinglens.db import pool_for

    url, _ = test_database
    migrate(url)
    with psycopg.connect(url, **connection_options(url)) as conn:
        conn.execute("INSERT INTO ingestion_snapshots(id,cutoff_date) VALUES ('s','2026-10-19')")
        conn.execute("INSERT INTO retrieval_corpora VALUES ('corpus','s','{}',false)")
        conn.execute("INSERT INTO retrieval_corpora VALUES ('outside','s','{}',false)")
        for cik in ("TARGET", "OTHER"):
            conn.execute("INSERT INTO companies VALUES (%s,%s,'test','1231')", (cik, cik))
        rows = [
            ("match", "TARGET", 2024, "FY", "7", "solar panels", "corpus"),
            ("other_item", "TARGET", 2024, "FY", "1A", "solar panels", "corpus"),
            ("other_year", "TARGET", 2025, "FY", "7", "solar panels", "corpus"),
            ("other_period", "TARGET", 2024, "Q1", "7", "solar panels", "corpus"),
            ("other_company", "OTHER", 2024, "FY", "7", "solar panels", "corpus"),
            ("other_corpus", "TARGET", 2024, "FY", "7", "solar panels", "outside"),
            ("stopword_text", "TARGET", 2024, "FY", "7", "the and in", "corpus"),
        ]
        for key, cik, year, period, item, text, corpus in rows:
            conn.execute(
                "INSERT INTO filings VALUES (%s,%s,'10-K','2025-01-01',"
                "'2024-12-31',%s,%s,'https://www.sec.gov/test')",
                (key, cik, year, period),
            )
            conn.execute(
                "INSERT INTO sections VALUES (%s,%s,%s,'test',%s,'hash','fp',0,'[]')",
                (key, key, item, text),
            )
            conn.execute(
                "INSERT INTO chunks(id,section_id,accession,cik,form,fiscal_year,fiscal_period,"
                "item,ordinal,text,token_count,source_hash,fingerprint,context_header,"
                "source_start,source_end) VALUES (%s,%s,%s,%s,'10-K',%s,%s,%s,0,%s,3,"
                "'hash','fp','test',0,1)",
                (key, key, key, cik, year, period, item, text),
            )
            conn.execute("INSERT INTO corpus_chunks VALUES (%s,%s)", (corpus, key))

    async def exercise():
        async with pool_for(url) as pool:
            service = SearchService(pool, "corpus")
            filters = dict(ticker="TARGET", fiscal_year=2024, fiscal_period="FY", items=["7"])
            long_query = (
                "Why did investment in solar batteries transform global electricity supply?"
            )
            hits = await service.keyword(long_query, 30, **filters)
            assert [h.chunk_id for h in hits] == ["match"]
            assert all(h.ticker == "TARGET" and h.item == "7" for h in hits)
            base = await service.keyword("panel", 30, **filters)
            with_stopwords = await service.keyword("the and in panels to of", 30, **filters)
            assert [(h.chunk_id, h.score) for h in base] == [
                (h.chunk_id, h.score) for h in with_stopwords
            ]
            for query in ("", "   ", "the and in to of"):
                assert await service.keyword(query, 30, **filters) == []
            assert len(await service.keyword("solar", 30, ticker="TARGET")) == 4

    with asyncio.Runner(loop_factory=asyncio.SelectorEventLoop) as runner:
        runner.run(exercise())

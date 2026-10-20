"""Resumable M2 corpus stages. No LLM calls or generated financial data."""

import hashlib
import time
from dataclasses import asdict
from typing import Any

from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from filinglens.config import Settings
from filinglens.db import INGESTION_LOCK, INGESTION_UNLOCK, pool_for
from filinglens.edgar.client import EdgarClient
from filinglens.ingest.chunk import CHUNKER_VERSION, MAXIMUM, OVERLAP, TARGET, chunk_section
from filinglens.ingest.identity import digest, identity
from filinglens.ingest.models import model_revision, tokenizer
from filinglens.ingest.parse import PARSER_VERSION, parse_filing


def configuration() -> dict:
    import selectolax
    import tokenizers
    import transformers

    return {
        "parser": PARSER_VERSION,
        "chunker": CHUNKER_VERSION,
        "embed_tokenizer": model_revision("embed"),
        "rerank_tokenizer": model_revision("rerank"),
        "target": TARGET,
        "maximum": MAXIMUM,
        "overlap": OVERLAP,
        "selectolax": selectolax.__version__,
        "transformers": transformers.__version__,
        "tokenizers": tokenizers.__version__,
    }


async def checkpoint(
    conn: Any,
    settings: Settings,
    accession: str,
    fingerprint: str,
    stage: str,
    status: str,
    details: dict,
) -> None:
    await conn.execute(
        """INSERT INTO document_processing(snapshot_id,accession,fingerprint,stage,status,details)
        VALUES (%s,%s,%s,%s,%s,%s) ON CONFLICT(snapshot_id,accession,fingerprint,stage)
        DO UPDATE SET status=excluded.status,details=excluded.details,updated_at=now()""",
        (settings.snapshot_id, accession, fingerprint, stage, status, Jsonb(details)),
    )


async def prepare_corpus(
    settings: Settings, tickers: list[str], *, stage: str, force: bool = False
) -> dict:
    started = time.perf_counter()
    async with pool_for(settings.database_url) as pool, EdgarClient(settings) as client:
        async with pool.connection() as lock_conn:
            locked = await (await lock_conn.execute(INGESTION_LOCK)).fetchone()
            if not locked[0]:
                raise RuntimeError("Another ingestion process is active")
            try:
                async with pool.connection() as conn:
                    conn.row_factory = dict_row
                    filings = await (
                        await conn.execute(
                            """SELECT f.*,c.ticker FROM filings f JOIN companies c USING(cik)
                        WHERE c.ticker=ANY(%s) AND f.filing_date<=%s ORDER BY f.accession""",
                            (tickers, settings.ingestion_cutoff),
                        )
                    ).fetchall()
                config = configuration() if stage == "parse" else {"download": "primary-v1"}
                fingerprint = digest(config)
                # Ingestion scope belongs to the corpus, never to a passage's identity.
                config["filing_count"] = len(filings)
                corpus_id = identity(
                    "corpus",
                    settings.snapshot_id,
                    config,
                    [
                        [
                            f["accession"],
                            f["url"],
                            f["ticker"],
                            f["fiscal_year"],
                            f["fiscal_period"],
                        ]
                        for f in filings
                    ],
                )
                if stage == "parse":
                    async with pool.connection() as conn:
                        await conn.execute(
                            "INSERT INTO retrieval_corpora(id,snapshot_id,configuration) "
                            "VALUES (%s,%s,%s) ON CONFLICT DO NOTHING",
                            (corpus_id, settings.snapshot_id, Jsonb(config)),
                        )
                totals = {
                    "corpus_id": corpus_id,
                    "filings": len(filings),
                    "completed": 0,
                    "skipped": 0,
                    "failed": [],
                    "chunks": 0,
                }
                for filing in filings:
                    accession = filing["accession"]
                    try:
                        if stage == "parse" and not force:
                            async with pool.connection() as conn:
                                done = await (
                                    await conn.execute(
                                        "SELECT status FROM corpus_documents WHERE corpus_id=%s "
                                        "AND accession=%s",
                                        (corpus_id, accession),
                                    )
                                ).fetchone()
                            if done and done[0] == "complete":
                                totals["skipped"] += 1
                                continue
                        body = await client.get(filing["url"], expect_filing=True)
                        source_hash = hashlib.sha256(body).hexdigest()
                        async with pool.connection() as conn:
                            await checkpoint(
                                conn,
                                settings,
                                accession,
                                "primary-v1",
                                "filings",
                                "complete",
                                {"source_hash": source_hash},
                            )
                            await conn.execute(
                                "UPDATE ingestion_snapshots SET manifest=%s WHERE id=%s",
                                (Jsonb(client.manifest()), settings.snapshot_id),
                            )
                        if stage == "parse":
                            sections, diagnostics = parse_filing(body, filing["form"])
                            if diagnostics["ambiguous"] or not sections:
                                raise ValueError(f"Unresolved sections: {diagnostics}")
                            # Missing items are visible diagnostics; do not fabricate content.
                            rows = []
                            for section in sections:
                                sid = identity(
                                    "sec",
                                    accession,
                                    source_hash,
                                    fingerprint,
                                    section.item,
                                    section.occurrence,
                                )
                                header = (
                                    f"{filing['ticker']} {filing['form']} "
                                    f"{filing['fiscal_year']} {filing['fiscal_period']} "
                                    f"— {section.title}"
                                )
                                chunks = chunk_section(
                                    section,
                                    section_id=sid,
                                    header=header,
                                    embed_tok=tokenizer("embed"),
                                    rerank_tok=tokenizer("rerank"),
                                )
                                rows.append((sid, section, header, chunks))
                            async with pool.connection() as conn:
                                existing = await (
                                    await conn.execute(
                                        "SELECT chunk_id FROM corpus_chunks cc JOIN chunks c "
                                        "ON cc.chunk_id=c.id WHERE cc.corpus_id=%s "
                                        "AND c.accession=%s",
                                        (corpus_id, accession),
                                    )
                                ).fetchall()
                                expected = {ch.id for _, _, _, chunks in rows for ch in chunks}
                                if existing and {r[0] for r in existing} != expected:
                                    raise ValueError(
                                        "Reparse changed IDs under the same fingerprint"
                                    )
                                for sid, section, header, chunks in rows:
                                    await conn.execute(
                                        """INSERT INTO sections(id,accession,item,title,text,
                                        source_hash,fingerprint,occurrence,blocks)
                                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                                        ON CONFLICT(id) DO NOTHING""",
                                        (
                                            sid,
                                            accession,
                                            section.item,
                                            section.title,
                                            section.text,
                                            source_hash,
                                            fingerprint,
                                            section.occurrence,
                                            Jsonb(section.serialized_blocks()),
                                        ),
                                    )
                                    for chunk in chunks:
                                        params = (
                                            asdict(chunk)
                                            | filing
                                            | {
                                                "id": chunk.id,
                                                "section_id": sid,
                                                "item": section.item,
                                                "source_hash": source_hash,
                                                "fingerprint": fingerprint,
                                                "context_header": header,
                                            }
                                        )
                                        await conn.execute(
                                            """INSERT INTO chunks(id,section_id,accession,cik,form,
                                            fiscal_year,fiscal_period,item,ordinal,text,token_count,
                                            source_hash,fingerprint,context_header,source_start,
                                            source_end,oversized_row) VALUES (%(id)s,%(section_id)s,
                                            %(accession)s,%(cik)s,%(form)s,%(fiscal_year)s,
                                            %(fiscal_period)s,%(item)s,%(ordinal)s,%(text)s,
                                            %(token_count)s,%(source_hash)s,%(fingerprint)s,
                                            %(context_header)s,%(source_start)s,%(source_end)s,
                                            %(oversized_row)s) ON CONFLICT(id) DO NOTHING""",
                                            params,
                                        )
                                        await conn.execute(
                                            "INSERT INTO corpus_chunks VALUES (%s,%s) "
                                            "ON CONFLICT DO NOTHING",
                                            (corpus_id, chunk.id),
                                        )
                                details = diagnostics | {
                                    "sections": len(rows),
                                    "chunks": len(expected),
                                }
                                await conn.execute(
                                    """INSERT INTO corpus_documents VALUES (%s,%s,%s,'complete',%s)
                                    ON CONFLICT(corpus_id,accession) DO UPDATE SET
                                    status='complete',details=excluded.details""",
                                    (corpus_id, accession, source_hash, Jsonb(details)),
                                )
                                await checkpoint(
                                    conn,
                                    settings,
                                    accession,
                                    fingerprint,
                                    "parse",
                                    "complete",
                                    details,
                                )
                                totals["chunks"] += len(expected)
                        totals["completed"] += 1
                        print(f"{stage} {filing['ticker']} {accession}: complete", flush=True)
                    except Exception as error:
                        detail = {"error": str(error)}
                        async with pool.connection() as conn:
                            await checkpoint(
                                conn, settings, accession, fingerprint, stage, "error", detail
                            )
                        totals["failed"].append({"accession": accession, **detail})
                        print(f"{accession}: {error}", flush=True)
                totals |= {
                    "seconds": time.perf_counter() - started,
                    "network_requests": client.network_requests,
                    "cache_hits": client.cache_hits,
                }
                return totals
            finally:
                await lock_conn.execute(INGESTION_UNLOCK)

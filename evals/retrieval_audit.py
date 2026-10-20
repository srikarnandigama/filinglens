"""Read-only validation and coverage inventory for the frozen M2 benchmark."""

import hashlib
from collections import Counter
from pathlib import Path

from evals.label_retrieval import load_records
from filinglens.ingest.identity import digest

CORPUS_ID = "corpus_2fb48958e274daed46c19e3fbf2583213e308b1eebaa16a04cfdc8052eea82e7"
CROSS_YEAR = {
    "hq_efbdb0ea523543c699eddddde9b1e638": "XOM",
    "hq_84c831be7d16420aae81eb2d9f98c8af": "COST",
    "hq_19ea90a4eeb84991845ef0f0a3c4d316": "MSFT",
    "hq_5404d74f74b4456e9c72c7def4c64227": "AMZN",
    "hq_9e6c0c0dbb5941589c85ed5a923d944e": "NVDA",
    "hq_e9bf3b51fc6948de9eaa071fdbdb0e46": "CVX",
}


async def validate(pool, labels: Path) -> tuple[list[dict], dict]:
    """Fail without changing labels or freezing/updating any database record."""
    records = load_records(labels)
    if len(records) != 30 or len({r["question"] for r in records}) != 30:
        raise ValueError("Require exactly 30 unique IDs and unique question texts")
    async with pool.connection() as conn:
        await conn.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        corpus = await (
            await conn.execute(
                "SELECT configuration,frozen FROM retrieval_corpora WHERE id=%s", (CORPUS_ID,)
            )
        ).fetchone()
        if not corpus or not corpus[1]:
            raise ValueError("Expected corpus must already be frozen")
        docs = await (
            await conn.execute(
                "SELECT accession,source_hash,status FROM corpus_documents WHERE corpus_id=%s "
                "ORDER BY accession",
                (CORPUS_ID,),
            )
        ).fetchall()
        chunks = await (
            await conn.execute(
                "SELECT c.id,co.ticker,c.fiscal_year,c.fiscal_period,c.item,c.text,"
                "c.embedding::text,c.embedding_fingerprint,c.embedding_input_hash "
                "FROM chunks c JOIN corpus_chunks cc ON cc.chunk_id=c.id "
                "JOIN companies co ON co.cik=c.cik WHERE cc.corpus_id=%s ORDER BY c.id",
                (CORPUS_ID,),
            )
        ).fetchall()
    if len(chunks) != 23441 or len(docs) != 275 or any(d[2] != "complete" for d in docs):
        raise ValueError("Frozen corpus size/completion mismatch")
    corpus_hash = digest([corpus[0], docs, [c[0] for c in chunks]])
    lookup = {c[0]: c for c in chunks}
    ticker_only, item_filters, broad = [], [], []
    for r in records:
        key, filters, gold = r["id"], r["filters"], r["gold_chunk_ids"]
        if r["corpus_id"] != CORPUS_ID or r.get("corpus_hash") != corpus_hash:
            raise ValueError(f"Corpus identity/fingerprint mismatch: {key}")
        if not r["question"].strip() or not r.get("reference_answer", "").strip() or not gold:
            raise ValueError(f"Incomplete record: {key}")
        if len(gold) != len(set(gold)):
            raise ValueError(f"Duplicate gold IDs: {key}")
        if set(filters) - {"ticker", "fiscal_year", "fiscal_period", "items"}:
            raise ValueError(f"Unsupported saved filters: {key}")
        for chunk_id in gold:
            if chunk_id not in lookup:
                raise ValueError(f"Gold ID absent from frozen corpus: {key}: {chunk_id}")
            c = lookup[chunk_id]
            for name, index in [("ticker", 1), ("fiscal_year", 2), ("fiscal_period", 3)]:
                if filters.get(name) is not None and filters[name] != c[index]:
                    raise ValueError(f"Gold/filter mismatch: {key}: {name}")
            if filters.get("items") is not None and c[4] not in filters["items"]:
                raise ValueError(f"Gold/item mismatch: {key}")
        if "items" in filters:
            item_filters.append(key)
        if set(filters) == {"ticker"}:
            ticker_only.append(key)
            if CROSS_YEAR.get(key) != filters["ticker"]:
                raise ValueError(f"Unexpected ticker-only filter: {key}")
        elif set(filters) != {"ticker", "fiscal_year", "fiscal_period"}:
            raise ValueError(f"Unexpected period-filter shape: {key}")
        if len(gold) > 3:
            broad.append({"id": key, "question": r["question"], "gold_count": len(gold)})
    if set(ticker_only) != set(CROSS_YEAR):
        raise ValueError("The six approved cross-year records do not match")
    return records, {
        "records": len(records),
        "unique_ids": len({r["id"] for r in records}),
        "unique_questions": len({r["question"] for r in records}),
        "corpus_id": CORPUS_ID,
        "corpus_hash": corpus_hash,
        "label_sha256": hashlib.sha256(labels.read_bytes()).hexdigest(),
        "corpus_content_hash": digest(chunks),
        "chunks": len(chunks),
        "filings": len(docs),
        "frozen": corpus[1],
        "ticker_only": ticker_only,
        "item_filters": item_filters,
        "gold_sizes": dict(sorted(Counter(len(r["gold_chunk_ids"]) for r in records).items())),
        "broad": broad,
    }


async def coverage(pool) -> list[dict]:
    """Inventory every expected retained item, including missing (zero-chunk) items."""
    async with pool.connection() as conn:
        await conn.execute("SET TRANSACTION READ ONLY")
        filings = await (
            await conn.execute(
                "SELECT co.ticker,f.fiscal_year,f.accession,f.form FROM filings f "
                "JOIN companies co ON co.cik=f.cik JOIN corpus_documents cd "
                "ON cd.accession=f.accession WHERE cd.corpus_id=%s "
                "ORDER BY co.ticker,f.fiscal_year,f.accession",
                (CORPUS_ID,),
            )
        ).fetchall()
        rows = await (
            await conn.execute(
                "SELECT c.accession,c.item,count(*),string_agg(c.text,E'\n' ORDER BY c.ordinal) "
                "FROM chunks c JOIN corpus_chunks cc ON cc.chunk_id=c.id "
                "WHERE cc.corpus_id=%s GROUP BY c.accession,c.item",
                (CORPUS_ID,),
            )
        ).fetchall()
    lookup = {(r[0], r[1]): (r[2], r[3]) for r in rows}
    result = []
    for ticker, year, accession, form in filings:
        items = ("1", "1A", "7", "7A", "8") if form == "10-K" else ("P1-2", "P2-1A")
        for item in items:
            count, text = lookup.get((accession, item), (0, ""))
            result.append(
                {
                    "ticker": ticker,
                    "fiscal_year": year,
                    "accession": accession,
                    "form": form,
                    "item": item,
                    "chunks": count,
                    "first_line": next(
                        (s.strip() for s in text.splitlines() if s.strip()), "[missing]"
                    ),
                    "text": text if count < 3 else "",
                }
            )
    return result

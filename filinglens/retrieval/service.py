"""Four retrieval modes over one explicitly selected, versioned corpus."""

import json
import os
from dataclasses import asdict, dataclass, replace
from typing import Literal

from psycopg.rows import dict_row

from filinglens.config import ROOT, Settings
from filinglens.db import pool_for
from filinglens.ingest.chunk import QUERY_BUDGET, model_windows
from filinglens.ingest.embed import embedding_fingerprint
from filinglens.ingest.identity import digest
from filinglens.ingest.models import QUERY_PREFIX, embedder, model_revision, reranker, tokenizer

Mode = Literal["vector", "keyword", "hybrid", "hybrid_rerank"]
MODES = ("vector", "keyword", "hybrid", "hybrid_rerank")


@dataclass(frozen=True)
class ChunkHit:
    chunk_id: str
    ticker: str
    form: str
    fiscal_year: int
    fiscal_period: str
    item: str
    text: str
    score: float
    accession: str
    title: str
    report_date: str
    url: str
    oversized_row: bool = False


def hit(row: dict, score: float) -> ChunkHit:
    return ChunkHit(
        row["id"],
        row["ticker"],
        row["form"],
        row["fiscal_year"],
        row["fiscal_period"],
        row["item"],
        row["text"],
        score,
        row["accession"],
        row["title"],
        str(row["report_date"]),
        row["url"],
        row["oversized_row"],
    )


def rrf(*lists: list[ChunkHit]) -> list[ChunkHit]:
    scores: dict[str, float] = {}
    hits: dict[str, ChunkHit] = {}
    for values in lists:
        seen = set()
        for rank, value in enumerate(values, 1):
            if value.chunk_id in seen:
                continue
            seen.add(value.chunk_id)
            hits[value.chunk_id] = value
            scores[value.chunk_id] = scores.get(value.chunk_id, 0) + 1 / (60 + rank)
    return [
        replace(hits[key], score=scores[key])
        for key in sorted(scores, key=lambda key: (-scores[key], key))
    ]


def rerank(query: str, values: list[ChunkHit]) -> list[ChunkHit]:
    if not values:
        return []
    tok = tokenizer("rerank")
    if len(tok.encode(query, add_special_tokens=False)) > QUERY_BUDGET:
        raise ValueError(f"Shorten the query to at most {QUERY_BUDGET} reranker tokens")
    pairs = []
    ranges = []
    for value in values:
        start = len(pairs)
        windows = (
            model_windows(value.text, tok, query=query) if value.oversized_row else [value.text]
        )
        for window in windows:
            if len(tok.encode(query, text_pair=window)) > 512:
                raise ValueError("Reranker pair exceeds 512; silent truncation is forbidden")
            pairs.append((query, window))
        ranges.append((start, len(pairs)))
    scores = reranker().predict(pairs, batch_size=8, show_progress_bar=False)
    return sorted(
        [
            replace(v, score=float(max(scores[a:b])))
            for v, (a, b) in zip(values, ranges, strict=True)
        ],
        key=lambda v: (-v.score, v.chunk_id),
    )


class SearchService:
    def __init__(self, pool, corpus_id: str) -> None:
        self.pool = pool
        self.corpus_id = corpus_id
        self.exact_fallbacks = 0
        self._frozen: bool | None = None

    def filters(self, *, ticker=None, fiscal_year=None, fiscal_period=None, items=None):
        clauses = ["cc.corpus_id=%s"]
        params: list = [self.corpus_id]
        for column, value in [
            ("co.ticker", ticker),
            ("c.fiscal_year", fiscal_year),
            ("c.fiscal_period", fiscal_period),
        ]:
            if value is not None:
                clauses.append(column + "=%s")
                params.append(value)
        if items is not None:
            clauses.append("c.item=ANY(%s)")
            params.append(items)
        return " AND ".join(clauses), params

    @property
    def source(self) -> str:
        return """FROM chunks c JOIN corpus_chunks cc ON cc.chunk_id=c.id
        JOIN companies co ON co.cik=c.cik JOIN filings f ON f.accession=c.accession
        JOIN sections s ON s.id=c.section_id"""

    async def vector(
        self, vector: list[float], limit: int, *, exact: bool = False, **filters
    ) -> list[ChunkHit]:
        where, params = self.filters(**filters)
        where += " AND c.embedding IS NOT NULL AND c.embedding_fingerprint=%s"
        params.append(embedding_fingerprint())
        columns = "c.*,co.ticker,s.title,f.report_date,f.url"
        async with self.pool.connection() as conn:
            conn.row_factory = dict_row
            if exact:
                query = (
                    f"WITH eligible AS MATERIALIZED (SELECT {columns} {self.source} "
                    f"WHERE {where}) SELECT *,embedding <=> %s::vector AS distance "
                    "FROM eligible ORDER BY distance,id LIMIT %s"
                )
                args = [*params, str(vector), limit]
            else:
                await conn.execute("SET LOCAL hnsw.iterative_scan = strict_order")
                await conn.execute("SET LOCAL hnsw.ef_search = 100")
                query = (
                    f"SELECT {columns},c.embedding <=> %s::vector AS distance "
                    f"{self.source} WHERE {where} "
                    "ORDER BY c.embedding <=> %s::vector LIMIT %s"
                )
                args = [str(vector), *params, str(vector), limit]
            rows = await (await conn.execute(query, args)).fetchall()
        if not exact and len(rows) < limit:
            self.exact_fallbacks += 1
            return await self.vector(vector, limit, exact=True, **filters)
        return sorted(
            [hit(r, 1 - float(r["distance"])) for r in rows], key=lambda v: (-v.score, v.chunk_id)
        )

    async def keyword(self, query: str, limit: int, **filters) -> list[ChunkHit]:
        where, params = self.filters(**filters)
        async with self.pool.connection() as conn:
            conn.row_factory = dict_row
            rows = await (
                await conn.execute(
                    f"""SELECT c.*,co.ticker,s.title,f.report_date,f.url,
                ts_rank_cd(c.tsv,websearch_to_tsquery('english',%s)) AS rank
                {self.source} WHERE {where}
                AND c.tsv @@ websearch_to_tsquery('english',%s)
                ORDER BY rank DESC,c.id LIMIT %s""",
                    [query, *params, query, limit],
                )
            ).fetchall()
        return [hit(row, float(row["rank"])) for row in rows]

    async def _search(
        self,
        query: str,
        *,
        ticker: str | None = None,
        fiscal_year: int | None = None,
        fiscal_period: str | None = None,
        items: list[str] | None = None,
        mode: Mode = "hybrid_rerank",
        k: int = 8,
    ) -> list[ChunkHit]:
        if mode not in MODES or k < 1:
            raise ValueError("Invalid retrieval mode or k")
        if not query.strip():
            return []
        filters = dict(
            ticker=ticker.upper() if ticker else None,
            fiscal_year=fiscal_year,
            fiscal_period=fiscal_period,
            items=items,
        )
        depth = max(30, k)
        if mode == "keyword":
            return (await self.keyword(query, depth, **filters))[:k]
        text = QUERY_PREFIX + query
        if len(tokenizer("embed").encode(text)) > 512:
            raise ValueError("Query exceeds the embedding model input budget")
        vector = (
            embedder()
            .encode([text], normalize_embeddings=True, show_progress_bar=False)[0]
            .tolist()
        )
        exact = all(filters[key] is not None for key in ("ticker", "fiscal_year", "fiscal_period"))
        values = await self.vector(vector, depth, exact=exact, **filters)
        if mode == "vector":
            return values[:k]
        values = rrf(values, await self.keyword(query, depth, **filters))[:depth]
        if mode == "hybrid_rerank":
            values = rerank(query, values)
        return values[:k]

    async def search(
        self,
        query: str,
        *,
        ticker: str | None = None,
        fiscal_year: int | None = None,
        fiscal_period: str | None = None,
        items: list[str] | None = None,
        mode: Mode = "hybrid_rerank",
        k: int = 8,
    ) -> list[ChunkHit]:
        if self._frozen is None:
            async with self.pool.connection() as conn:
                conn.row_factory = dict_row
                row = await (
                    await conn.execute(
                        "SELECT frozen FROM retrieval_corpora WHERE id=%s", (self.corpus_id,)
                    )
                ).fetchone()
            if row is None:
                raise ValueError("Unknown retrieval corpus")
            self._frozen = row["frozen"]
        options = dict(
            ticker=ticker,
            fiscal_year=fiscal_year,
            fiscal_period=fiscal_period,
            items=items,
            mode=mode,
            k=k,
        )
        key = digest(
            [
                "retrieval-v1",
                self.corpus_id,
                query,
                options,
                embedding_fingerprint(),
                model_revision("rerank"),
            ]
        )
        path = ROOT / "data/retrieval_cache" / f"{key}.json"
        if self._frozen and path.exists():
            return [ChunkHit(**r) for r in json.loads(path.read_text(encoding="utf-8"))]
        results = await self._search(query, **options)
        if self._frozen:
            path.parent.mkdir(parents=True, exist_ok=True)
            temporary = path.with_suffix(".tmp")
            temporary.write_text(json.dumps([asdict(r) for r in results]), encoding="utf-8")
            os.replace(temporary, path)
        return results


async def search(
    query: str,
    *,
    ticker: str | None = None,
    fiscal_year: int | None = None,
    fiscal_period: str | None = None,
    items: list[str] | None = None,
    mode: Mode = "hybrid_rerank",
    k: int = 8,
) -> list[ChunkHit]:
    settings = Settings()
    if not settings.retrieval_corpus:
        raise ValueError("Set RETRIEVAL_CORPUS to an explicit corpus ID")
    async with pool_for(settings.database_url) as pool:
        return await SearchService(pool, settings.retrieval_corpus).search(
            query,
            ticker=ticker,
            fiscal_year=fiscal_year,
            fiscal_period=fiscal_period,
            items=items,
            mode=mode,
            k=k,
        )

"""Validate a completed M2 corpus and show four-mode search results, without labeling."""

import argparse
import asyncio
import json
import sys
import time
from dataclasses import asdict
from pathlib import Path

from psycopg.rows import dict_row

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from evals.label_retrieval import freeze_ready_corpus  # noqa: E402
from filinglens.config import ROOT, Settings  # noqa: E402
from filinglens.db import pool_for  # noqa: E402
from filinglens.ingest.embed import embedding_fingerprint  # noqa: E402
from filinglens.ingest.identity import digest  # noqa: E402
from filinglens.ingest.models import QUERY_PREFIX, embedder  # noqa: E402
from filinglens.retrieval.service import MODES, SearchService  # noqa: E402


async def check(args: argparse.Namespace) -> dict:
    settings = Settings()
    async with pool_for(settings.database_url) as pool:
        async with pool.connection() as conn:
            conn.row_factory = dict_row
            counts = await (
                await conn.execute(
                    """SELECT count(*) AS total_chunks,
                count(*) FILTER (WHERE embedding IS NULL) AS missing_embeddings,
                count(*) FILTER (WHERE embedding_fingerprint IS DISTINCT FROM %s) AS wrong_model,
                count(*) FILTER (WHERE vector_dims(embedding) <> 384) AS wrong_dimensions,
                count(*) FILTER (WHERE abs(vector_norm(embedding)-1)>0.00001) AS invalid_norms
                FROM chunks c JOIN corpus_chunks cc ON cc.chunk_id=c.id WHERE cc.corpus_id=%s""",
                    (embedding_fingerprint(), args.corpus),
                )
            ).fetchone()
            index = await (
                await conn.execute(
                    """SELECT ic.relname AS name,am.amname AS method,i.indisvalid AS valid,
                i.indisready AS ready,pg_relation_size(ic.oid) AS size_bytes,
                pg_get_indexdef(ic.oid) AS definition FROM pg_index i
                JOIN pg_class ic ON ic.oid=i.indexrelid
                JOIN pg_namespace ns ON ns.oid=ic.relnamespace
                JOIN pg_am am ON am.oid=ic.relam
                WHERE ns.nspname=current_schema() AND ic.relname='chunks_embedding_hnsw'"""
                )
            ).fetchone()
            identity_rows = await (
                await conn.execute(
                    "SELECT c.id,c.section_id,c.accession,c.ordinal,c.text,c.token_count "
                    "FROM chunks c JOIN corpus_chunks cc ON cc.chunk_id=c.id "
                    "WHERE cc.corpus_id=%s ORDER BY c.id",
                    (args.corpus,),
                )
            ).fetchall()
        if not counts["total_chunks"] or any(counts[k] for k in counts if k != "total_chunks"):
            raise ValueError(f"Incomplete or invalid embeddings: {counts}")
        if not index or not index["valid"] or not index["ready"] or index["method"] != "hnsw":
            raise ValueError(f"HNSW index is not ready: {index}")
        replay = json.loads((ROOT / "docs/M2_CHUNK_REPLAY.json").read_text(encoding="utf-8"))
        identity_hash = digest(
            [
                [r[k] for k in ("id", "section_id", "accession", "ordinal", "text", "token_count")]
                for r in identity_rows
            ]
        )
        if replay["corpus_id"] != args.corpus or replay["after_hash"] != identity_hash:
            raise ValueError("Chunk IDs or text changed since the verified offline replay")
        valid_ids, corpus_hash = await freeze_ready_corpus(pool, args.corpus)
        service = SearchService(pool, args.corpus)
        filters = {
            "ticker": args.ticker,
            "fiscal_year": args.fiscal_year,
            "fiscal_period": args.fiscal_period,
            "items": [args.item],
        }
        samples = {}
        for mode in MODES:
            started = time.perf_counter()
            hits = await service.search(args.query, mode=mode, k=3, **filters)
            if len(hits) != 3 or any(
                h.chunk_id not in valid_ids
                or h.ticker != args.ticker.upper()
                or h.fiscal_year != args.fiscal_year
                or h.fiscal_period != args.fiscal_period
                or h.item != args.item
                for h in hits
            ):
                raise ValueError(f"Expected three valid hits in {mode}; got {len(hits)}")
            samples[mode] = {
                "seconds": time.perf_counter() - started,
                "hits": [asdict(h) for h in hits],
            }
            print(f"{mode}: {len(hits)} hits", flush=True)
        filtered = await service.search(args.query, mode="vector", k=10, **filters)
        if len(filtered) != 10:
            raise ValueError("Real company/period search underfilled k=10")
        vector = (
            embedder()
            .encode(
                [QUERY_PREFIX + args.query], normalize_embeddings=True, show_progress_bar=False
            )[0]
            .tolist()
        )
        async with pool.connection() as conn:
            conn.row_factory = dict_row
            await conn.execute("SET LOCAL hnsw.iterative_scan=strict_order")
            plan = await (
                await conn.execute(
                    "EXPLAIN (ANALYZE,BUFFERS,FORMAT JSON) SELECT id FROM chunks "
                    "WHERE embedding IS NOT NULL ORDER BY embedding <=> %s::vector LIMIT 3",
                    (str(vector),),
                )
            ).fetchone()
        return {
            "corpus_id": args.corpus,
            "corpus_hash": corpus_hash,
            "counts": counts,
            "failures": 0,
            "input_hashes_verified": True,
            "ids_and_text_unchanged": True,
            "identity_hash": identity_hash,
            "frozen_for_labeling": True,
            "hnsw_index": index,
            "hnsw_plan_used": "chunks_embedding_hnsw" in json.dumps(plan),
            "hnsw_explain": plan,
            "filtered_vector_k10_returned": len(filtered),
            "query": args.query,
            "filters": filters,
            "modes": samples,
            "labels_created": False,
        }


def write_report(result: dict, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        "# M2 labeling readiness",
        "",
        f"Corpus: `{result['corpus_id']}`",
        "",
        f"Test query: **{result['query']}**",
        "",
        f"Filters: `{json.dumps(result['filters'])}`",
        "",
        "This is a smoke search, not a handwritten evaluation question or gold label.",
        "",
        f"Validated chunks: {result['counts']['total_chunks']:,}; failures: 0.",
        "HNSW index is valid and ready; complete corpus is frozen for labeling.",
        "",
    ]
    for mode, sample in result["modes"].items():
        lines += [f"## {mode}", "", f"Search time: {sample['seconds']:.3f} seconds.", ""]
        for rank, hit in enumerate(sample["hits"], 1):
            lines += [
                f"### {rank}. `{hit['chunk_id']}`",
                "",
                f"{hit['ticker']} | {hit['form']} {hit['accession']} | "
                f"FY{hit['fiscal_year']} {hit['fiscal_period']} | "
                f"{hit['item']}: {hit['title']} | score {hit['score']:.6f}",
                "",
                f"[Source filing]({hit['url']})",
                "",
                hit["text"],
                "",
            ]
    output.with_suffix(".md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", required=True)
    parser.add_argument("--query", default="cloud revenue growth")
    parser.add_argument("--ticker", default="MSFT")
    parser.add_argument("--fiscal-year", type=int, default=2025)
    parser.add_argument("--fiscal-period", default="Q3")
    parser.add_argument("--item", default="P1-2")
    parser.add_argument("--output", type=Path, default=ROOT / "docs/M2_LABELING_READINESS.json")
    args = parser.parse_args()
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    result = asyncio.run(check(args))
    write_report(result, args.output)
    print(
        json.dumps(
            {k: v for k, v in result.items() if k not in {"modes", "hnsw_explain"}}, indent=2
        )
    )


if __name__ == "__main__":
    main()

"""CPU embedding, batch checkpoints, and an explicitly bounded preflight benchmark."""

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

from psycopg.rows import dict_row

from filinglens.config import ROOT, Settings
from filinglens.db import INGESTION_LOCK, INGESTION_UNLOCK, pool_for
from filinglens.ingest.chunk import count, model_windows
from filinglens.ingest.corpus import checkpoint
from filinglens.ingest.identity import digest
from filinglens.ingest.models import embedder, model_revision, tokenizer


def embedding_fingerprint() -> str:
    return digest(
        {
            "model": model_revision("embed"),
            "normalized": True,
            "version": "single-input-v1",
            "oversized_row": "window-mean-normalize-v1",
        }
    )


def input_fingerprint(row: dict) -> str:
    return digest([row["context_header"], row["text"], row["oversized_row"]])


def encode_chunks(rows: list[dict]) -> list[list[float]]:
    import numpy as np

    inputs = []
    spans = []
    tok = tokenizer("embed")
    for row in rows:
        start = len(inputs)
        header = row["context_header"] + "\n"
        text = row["text"]
        if row["oversized_row"]:
            windows = model_windows(text, tok, prefix=header)
        else:
            if count(tok, header + text) > 460:
                raise ValueError(f"Ordinary chunk exceeds budget: {row['id']}")
            windows = [text]
        inputs.extend(header + w for w in windows)
        spans.append((start, len(inputs)))
    if any(count(tok, text) > 512 for text in inputs):
        raise ValueError("Embedding input exceeds 512; silent truncation is forbidden")
    vectors = embedder().encode(
        inputs,
        batch_size=16,
        normalize_embeddings=True,
        show_progress_bar=False,
        convert_to_numpy=True,
    )
    result = []
    for start, end in spans:
        vector = vectors[start] if end - start == 1 else np.mean(vectors[start:end], axis=0)
        norm = np.linalg.norm(vector)
        if not np.isfinite(vector).all() or norm <= 0 or len(vector) != 384:
            raise ValueError("Invalid embedding")
        result.append((vector / norm).tolist())
    return result


async def run_embeddings(
    settings: Settings, corpus_id: str, *, benchmark: bool = True, sample_size: int = 192
) -> dict:
    if not 1 <= sample_size <= 256:
        raise ValueError("Benchmark sample must be between 1 and 256 chunks")
    fp = embedding_fingerprint()
    async with pool_for(settings.database_url) as pool:
        async with pool.connection() as lock_conn:
            if not (await (await lock_conn.execute(INGESTION_LOCK)).fetchone())[0]:
                raise RuntimeError("Another ingestion process is active")
            try:
                async with pool.connection() as conn:
                    conn.row_factory = dict_row
                    corpus = await (
                        await conn.execute(
                            "SELECT configuration FROM retrieval_corpora WHERE id=%s", (corpus_id,)
                        )
                    ).fetchone()
                    if corpus is None:
                        raise ValueError("Unknown corpus")
                    expected = corpus["configuration"].get("filing_count")
                    completed = await (
                        await conn.execute(
                            "SELECT count(*) AS n FROM corpus_documents WHERE corpus_id=%s "
                            "AND status='complete'",
                            (corpus_id,),
                        )
                    ).fetchone()
                    if expected is not None and completed["n"] != expected:
                        raise ValueError("Finish parsing all corpus documents before embedding")
                    rows = await (
                        await conn.execute(
                            """SELECT c.* FROM chunks c JOIN corpus_chunks cc ON cc.chunk_id=c.id
                        WHERE cc.corpus_id=%s ORDER BY c.form,c.accession,c.item,c.ordinal""",
                            (corpus_id,),
                        )
                    ).fetchall()
                if not rows:
                    raise ValueError("Corpus has no chunks")
                pending = [
                    r
                    for r in rows
                    if r["embedding"] is None
                    or r["embedding_fingerprint"] != fp
                    or r["embedding_input_hash"] != input_fingerprint(r)
                ]
                if benchmark:
                    # Evenly sample the full ordered corpus, rather than only the first filing.
                    n = min(sample_size, len(rows))
                    selected = [rows[i * len(rows) // n] for i in range(n)]
                    extras = [r for r in rows if r["oversized_row"]][:4]
                    selected = list({r["id"]: r for r in [*selected, *extras]}.values())[:256]
                else:
                    selected = pending
                load_start = time.perf_counter()
                embedder()
                load_seconds = time.perf_counter() - load_start
                # Warm-up is reported separately from steady-state encoding + DB commits.
                warm_start = time.perf_counter()
                if selected:
                    encode_chunks(selected[:1])
                warm_seconds = time.perf_counter() - warm_start
                started = time.perf_counter()
                for offset in range(0, len(selected), 16):
                    batch = selected[offset : offset + 16]
                    vectors = encode_chunks(batch)
                    async with pool.connection() as conn:
                        async with conn.cursor() as cur:
                            await cur.executemany(
                                "UPDATE chunks SET embedding=%s::vector,embedding_fingerprint=%s, "
                                "embedding_input_hash=%s "
                                "WHERE id=%s",
                                [
                                    (str(v), fp, input_fingerprint(r), r["id"])
                                    for r, v in zip(batch, vectors, strict=True)
                                ],
                            )
                    print(f"embedded {min(offset + 16, len(selected))}/{len(selected)}", flush=True)
                seconds = time.perf_counter() - started
                pending_ids = {r["id"] for r in pending}
                newly_completed = sum(r["id"] in pending_ids for r in selected)
                remaining = max(0, len(pending) - newly_completed)
                result = {
                    "corpus_id": corpus_id,
                    "benchmark": benchmark,
                    "embedding_fingerprint": fp,
                    "total_chunks": len(rows),
                    "sample_chunks": len(selected),
                    "sample_oversized_rows": sum(r["oversized_row"] for r in selected),
                    "total_oversized_rows": sum(r["oversized_row"] for r in rows),
                    "cpu_threads": 4,
                    "batch_size": 16,
                    "sample_forms": sorted({r["form"] for r in selected}),
                    "sample_companies": len({r["cik"] for r in selected}),
                    "sample_mean_tokens": sum(r["token_count"] for r in selected) / len(selected)
                    if selected
                    else 0,
                    "corpus_mean_tokens": sum(r["token_count"] for r in rows) / len(rows),
                    "model_load_seconds": load_seconds,
                    "warmup_seconds": warm_seconds,
                    "seconds": seconds,
                    "chunks_per_second": len(selected) / seconds if seconds else 0,
                    "projected_total_seconds": seconds * len(rows) / len(selected)
                    if selected
                    else 0,
                    "remaining_before_sample": len(pending),
                    "remaining_after_sample": remaining,
                    "projected_remaining_seconds": seconds * remaining / len(selected)
                    if selected
                    else 0,
                }
                if not benchmark:
                    async with pool.connection() as conn:
                        for accession in sorted({r["accession"] for r in rows}):
                            await checkpoint(
                                conn,
                                settings,
                                accession,
                                digest([fp, corpus_id]),
                                "embed",
                                "complete",
                                {"corpus_id": corpus_id, "embedding_fingerprint": fp},
                            )
                        await conn.execute("ANALYZE chunks")
                return result
            finally:
                await lock_conn.execute(INGESTION_UNLOCK)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", required=True)
    parser.add_argument("--sample-size", type=int, default=192)
    parser.add_argument(
        "--full",
        action="store_true",
        help="Run only after the user approves the measured projection",
    )
    parser.add_argument("--output", type=Path, default=ROOT / "docs/M2_EMBED_BENCHMARK.json")
    args = parser.parse_args()
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    result = asyncio.run(
        run_embeddings(
            Settings(), args.corpus, benchmark=not args.full, sample_size=args.sample_size
        )
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

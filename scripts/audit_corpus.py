"""Check every final chunk's identity and both model input budgets without embedding."""

import argparse
import json
import sys
from pathlib import Path

import psycopg
from psycopg.rows import dict_row

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from filinglens.config import ROOT, Settings  # noqa: E402
from filinglens.db import connection_options  # noqa: E402
from filinglens.ingest.chunk import QUERY_BUDGET, TYPICAL_QUERY, count  # noqa: E402
from filinglens.ingest.identity import identity  # noqa: E402
from filinglens.ingest.models import tokenizer  # noqa: E402


def audit(corpus_id: str) -> dict:
    settings = Settings()
    with psycopg.connect(
        settings.database_url, row_factory=dict_row, **connection_options(settings.database_url)
    ) as conn:
        rows = conn.execute(
            "SELECT c.* FROM chunks c JOIN corpus_chunks cc ON cc.chunk_id=c.id "
            "WHERE cc.corpus_id=%s ORDER BY c.id",
            (corpus_id,),
        ).fetchall()
        sections = conn.execute(
            "SELECT s.* FROM sections s WHERE EXISTS (SELECT 1 FROM chunks c "
            "JOIN corpus_chunks cc ON cc.chunk_id=c.id "
            "WHERE c.section_id=s.id AND cc.corpus_id=%s)",
            (corpus_id,),
        ).fetchall()
    assert rows, "Corpus has no chunks"
    embed_tok, rerank_tok = tokenizer("embed"), tokenizer("rerank")
    maxima = {
        "embedding_input": 0,
        "typical_reranker_pair": 0,
        "reranker_pair_with_48_token_query": 0,
    }
    for row in rows:
        assert row["id"] == identity("chk", row["section_id"], row["ordinal"], row["text"])
        actual = count(embed_tok, row["context_header"] + "\n" + row["text"])
        assert actual == row["token_count"]
        if not row["oversized_row"]:
            pair = len(rerank_tok.encode(TYPICAL_QUERY, text_pair=row["text"]))
            reserved = (
                len(rerank_tok.encode(row["text"], add_special_tokens=False))
                + QUERY_BUDGET
                + rerank_tok.num_special_tokens_to_add(pair=True)
            )
            assert actual <= 460 and pair <= 512 and reserved <= 512
            maxima["embedding_input"] = max(maxima["embedding_input"], actual)
            maxima["typical_reranker_pair"] = max(maxima["typical_reranker_pair"], pair)
            maxima["reranker_pair_with_48_token_query"] = max(
                maxima["reranker_pair_with_48_token_query"], reserved
            )
    for section in sections:
        assert section["id"] == identity(
            "sec",
            section["accession"],
            section["source_hash"],
            section["fingerprint"],
            section["item"],
            section["occurrence"],
        )
        covered = set()
        for row in rows:
            if row["section_id"] == section["id"]:
                covered.update(range(row["source_start"], row["source_end"]))
        assert covered == set(range(len(section["blocks"])))
    result = {
        "corpus_id": corpus_id,
        "chunks": len(rows),
        "sections": len(sections),
        "oversized_rows": sum(r["oversized_row"] for r in rows),
        "maxima": maxima,
        "all_ids_valid": True,
        "all_source_blocks_covered": True,
    }
    (ROOT / "docs/M2_CORPUS_AUDIT.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", required=True)
    print(json.dumps(audit(parser.parse_args().corpus), indent=2))

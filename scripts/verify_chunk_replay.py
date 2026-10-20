"""Force an offline full-corpus reparse and assert every chunk ID and passage is unchanged."""

import argparse
import asyncio
import json
import sys
from pathlib import Path

import psycopg
import respx
from psycopg.types.json import Jsonb

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from filinglens.config import ROOT, Settings  # noqa: E402
from filinglens.db import connection_options  # noqa: E402
from filinglens.edgar.tickers import UNIVERSE  # noqa: E402
from filinglens.ingest.corpus import configuration, prepare_corpus  # noqa: E402
from filinglens.ingest.identity import digest  # noqa: E402


def snapshot(settings: Settings, corpus_id: str) -> list:
    with psycopg.connect(
        settings.database_url, **connection_options(settings.database_url)
    ) as conn:
        return conn.execute(
            "SELECT c.id,c.section_id,c.accession,c.ordinal,c.text,c.token_count "
            "FROM chunks c JOIN corpus_chunks cc ON cc.chunk_id=c.id "
            "WHERE cc.corpus_id=%s ORDER BY c.id",
            (corpus_id,),
        ).fetchall()


def verify(corpus_id: str | None = None) -> dict:
    settings = Settings()
    if corpus_id is None:
        with psycopg.connect(
            settings.database_url, **connection_options(settings.database_url)
        ) as conn:
            config = configuration() | {"filing_count": 275}
            matches = conn.execute(
                "SELECT id FROM retrieval_corpora WHERE configuration=%s", (Jsonb(config),)
            ).fetchall()
            if len(matches) != 1:
                raise ValueError("Pass an explicit full-corpus ID")
            corpus_id = matches[0][0]
    before = snapshot(settings, corpus_id)
    assert before, "Parse the corpus first"
    with respx.mock(assert_all_called=False) as mock:
        mock.route().mock(side_effect=AssertionError("Network forbidden during corpus replay"))
        with asyncio.Runner(loop_factory=asyncio.SelectorEventLoop) as runner:
            result = runner.run(prepare_corpus(settings, list(UNIVERSE), stage="parse", force=True))
    assert not result["failed"], result["failed"]
    assert result["network_requests"] == 0
    assert result["corpus_id"] == corpus_id
    after = snapshot(settings, corpus_id)
    assert before == after, "Chunk identities or text changed on forced reparse"
    result |= {
        "verified_chunks": len(after),
        "before_hash": digest(before),
        "after_hash": digest(after),
        "all_ids_unchanged": True,
    }
    (ROOT / "docs/M2_CHUNK_REPLAY.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus")
    args = parser.parse_args()
    print(json.dumps(verify(args.corpus), indent=2))

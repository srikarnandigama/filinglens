import os

import pytest


@pytest.mark.integration
@pytest.mark.skipif(
    os.environ.get("FILINGLENS_TEST_CORPUS_REPLAY") != "1",
    reason="Explicit full-corpus offline replay; can take several minutes",
)
def test_full_ingestion_reparse_preserves_every_chunk_id():
    from scripts.verify_chunk_replay import verify

    result = verify()
    assert result["all_ids_unchanged"]
    assert result["before_hash"] == result["after_hash"]
    assert result["verified_chunks"] > 0

"""Synthetic examples for analysis definitions and cache invalidation."""

import json
from dataclasses import asdict

import pytest

from evals.retrieval_followup import containment, shingles, unjudged
from filinglens.ingest.identity import digest
from tests.test_labeling_retrieval import passage


def test_unjudged_uses_actual_slots_and_preserves_known_manual_gold():
    result = unjudged(["pool", "gold", "new"], {"pool"}, {"gold"}, 5)
    assert result["outside_pool"] == 2
    assert result["unjudged"] == 1
    assert result["returned"] == 3
    assert result["fraction"] == 1 / 3
    assert result["unjudged_ids"] == ["new"]
    assert unjudged([], set(), set(), 10)["fraction"] == 0
    assert unjudged(["new", "pool"], {"pool"}, set(), 1)["fraction"] == 1


def test_shingles_case_unicode_shifted_boundaries_and_short_text_guard():
    text = " ".join(f"word{i}" for i in range(40))
    shifted = " ".join(f"word{i}" for i in range(10, 50))
    assert containment(shingles(text), shingles(shifted)) == 26 / 36
    assert shingles(text.upper().replace(" ", ", ")) == shingles(text)
    assert shingles("Ａ " + text) == shingles("A " + text)
    assert containment(shingles(text), shingles("unrelated short text")) == 0
    assert containment(shingles(text), shingles(text)) == 1
    assert containment(shingles(text), shingles(" ".join(f"other{i}" for i in range(40)))) == 0


@pytest.mark.asyncio
async def test_new_retrieval_version_never_serves_v1_cache(tmp_path, monkeypatch):
    from filinglens.retrieval import service

    monkeypatch.setattr(service, "ROOT", tmp_path)
    monkeypatch.setattr(service, "embedding_fingerprint", lambda: "embedding")
    monkeypatch.setattr(service, "model_revision", lambda _: "reranker")
    options = dict(
        ticker=None, fiscal_year=None, fiscal_period=None, items=None, mode="keyword", k=30
    )
    key = digest(["retrieval-v1", "corpus", "query", options, "embedding", "reranker"])
    cache = tmp_path / "data/retrieval_cache"
    cache.mkdir(parents=True)
    (cache / f"{key}.json").write_text(json.dumps([asdict(passage("old"))]))
    instance = service.SearchService(object(), "corpus")
    instance._frozen = True
    calls = []

    async def fresh(*args, **kwargs):
        calls.append(kwargs)
        return [passage("fresh")]

    monkeypatch.setattr(instance, "_search", fresh)
    assert (await instance.search("query", **options))[0].chunk_id == "fresh"
    assert (await instance.search("query", **options))[0].chunk_id == "fresh"
    assert len(calls) == 1

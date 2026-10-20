import json
from argparse import Namespace
from contextlib import asynccontextmanager
from dataclasses import replace

import pytest

from evals.label_retrieval import atomic_json, candidates, display, load_records, save_record
from evals.retrieval_eval import metrics
from filinglens.retrieval.service import ChunkHit, rrf


def passage(key):
    return ChunkHit(
        key,
        "TEST",
        "10-K",
        2025,
        "FY",
        "7",
        "source passage",
        1,
        "accession",
        "MD&A",
        "2025-12-31",
        "https://www.sec.gov/source",
    )


def test_rrf_independent_expected_ranks_and_duplicate_identity():
    a, b, c = [passage(k) for k in ["a", "b", "c"]]
    results = rrf([a, b], [c, a])
    assert [r.chunk_id for r in results] == ["a", "c", "b"]
    assert results[0].score == pytest.approx(1 / 61 + 1 / 62)
    assert len(rrf([a, a])) == 1


@pytest.mark.asyncio
async def test_union_shows_full_metadata_and_deduplicates_all_four_modes():
    class FakeSearch:
        modes = []

        async def search(self, query, **kwargs):
            assert query == "human-entered test prompt"
            self.modes.append(kwargs["mode"])
            return [passage("same"), passage(kwargs["mode"])]

    fake = FakeSearch()
    values, ranks = await candidates(fake, "human-entered test prompt", {}, 30)
    assert len(fake.modes) == 4 and len(values) == 5
    assert len(ranks["same"]) == 4
    rendered = display(passage("same"))
    for expected in ["same", "TEST", "accession", "MD&A", "source passage", "2025-12-31"]:
        assert expected in rendered


def test_manual_labels_atomic_save_edit_resume_and_invalid_ids(tmp_path):
    output = tmp_path / "handwritten.jsonl"
    record = {
        "id": "q",
        "question": "human-entered test prompt",
        "corpus_id": "c",
        "gold_chunk_ids": ["a", "a"],
    }
    save_record(output, record, {"a", "b"})
    assert load_records(output)[0]["gold_chunk_ids"] == ["a"]
    save_record(output, record | {"gold_chunk_ids": ["b"]}, {"a", "b"})
    assert len(load_records(output)) == 1
    before = output.read_bytes()
    with pytest.raises(ValueError):
        save_record(output, record | {"gold_chunk_ids": ["missing"]}, {"a"})
    assert output.read_bytes() == before
    with pytest.raises(ValueError):
        save_record(output, record | {"gold_chunk_ids": []}, {"a"})
    draft = tmp_path / "draft.json"
    atomic_json(draft, record)
    assert json.loads(draft.read_text()) == record


def test_ties_are_deterministic():
    a, b = passage("a"), passage("b")
    assert [h.chunk_id for h in rrf([a], [b])] == ["a", "b"]
    assert replace(a, score=0).chunk_id == a.chunk_id


def test_metrics_multiple_gold_and_missing_hits():
    values = metrics(["miss", "a", "b"], {"a", "b", "absent"})
    assert values == {"recall@5": 2 / 3, "recall@10": 2 / 3, "MRR@30": 1 / 2}
    assert metrics([], {"a"}) == {"recall@5": 0, "recall@10": 0, "MRR@30": 0}
    with pytest.raises(ValueError):
        metrics(["a", "a"], {"a"})
    with pytest.raises(ValueError):
        metrics([], set())


@pytest.mark.asyncio
async def test_interactive_manual_mark_unmark_show_and_save(tmp_path, monkeypatch):
    import evals.label_retrieval as label

    @asynccontextmanager
    async def fake_pool(_):
        yield object()

    async def ready(*_):
        return {"a"}, "corpus-hash"

    async def pool_candidates(*_):
        return [passage("a")], {"a": {"vector": 1}}

    answers = iter(
        ["human-entered test prompt", "show 1", "mark 1", "unmark 1", "mark 1", "save", ":quit"]
    )
    monkeypatch.setattr(label, "pool_for", fake_pool)
    monkeypatch.setattr(label, "freeze_ready_corpus", ready)
    monkeypatch.setattr(label, "candidates", pool_candidates)
    monkeypatch.setattr("builtins.input", lambda _: next(answers))
    shown = []
    monkeypatch.setattr(label.pydoc, "pager", shown.append)
    output = tmp_path / "handwritten.jsonl"
    await label.interactive(Namespace(corpus="c", output=output, depth=30))
    records = load_records(output)
    assert len(records) == 1
    assert records[0]["gold_chunk_ids"] == ["a"]
    assert records[0]["question"] == "human-entered test prompt"
    assert "source passage" in shown[0]
    assert not output.with_suffix(".draft.json").exists()


@pytest.mark.asyncio
async def test_draft_exists_before_interrupted_candidate_search(tmp_path, monkeypatch):
    import evals.label_retrieval as label

    @asynccontextmanager
    async def fake_pool(_):
        yield object()

    async def ready(*_):
        return {"a"}, "corpus-hash"

    async def interrupted(*_):
        raise EOFError("simulated interruption")

    monkeypatch.setattr(label, "pool_for", fake_pool)
    monkeypatch.setattr(label, "freeze_ready_corpus", ready)
    monkeypatch.setattr(label, "candidates", interrupted)
    monkeypatch.setattr("builtins.input", lambda _: "human-entered test prompt")
    output = tmp_path / "handwritten.jsonl"
    with pytest.raises(EOFError):
        await label.interactive(Namespace(corpus="c", output=output, depth=30))
    draft = json.loads(output.with_suffix(".draft.json").read_text())
    assert draft["question"] == "human-entered test prompt" and not output.exists()

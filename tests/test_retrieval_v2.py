"""Synthetic Phase C validation/attribution fixtures; never edits student labels."""

from copy import deepcopy

import pytest

from evals.retrieval_eval import metrics
from evals.retrieval_v2 import APPROVED_ADDITIONS, V2, check_review
from evals.retrieval_v2_report import bridge_scores, reconstruct_exposure
from filinglens.config import Settings
from filinglens.retrieval.service import MODES


def review_fixture():
    ids = [*APPROVED_ADDITIONS, *(f"fixture_{i}" for i in range(28))]
    original, reviewed, manifest = [], [], {"records": []}
    for i, key in enumerate(ids):
        size = 1 if i == 0 else 3 if i in {2, 3} else 2
        old = {
            "id": key,
            "question": f"Synthetic fixture question {i}",
            "filters": {"ticker": "TEST", "fiscal_year": 2024, "fiscal_period": "FY"},
            "reference_answer": "Synthetic fixture answer",
            "corpus_id": "v1",
            "corpus_hash": "old",
            "gold_chunk_ids": [f"old_{i}_{j}" for j in range(size)],
        }
        mapped = [f"new_{i}_{j}" for j in range(size)]
        original.append(old)
        reviewed.append(
            old
            | {
                "corpus_id": V2,
                "corpus_hash": "new",
                "gold_chunk_ids": mapped + sorted(APPROVED_ADDITIONS.get(key, [])),
            }
        )
        manifest["records"].append({"id": key, "gold": [{"new_ids": [g]} for g in mapped]})
    return original, reviewed, manifest


def test_review_accepts_only_the_exact_approved_additions():
    original, reviewed, manifest = review_fixture()
    changes = check_review(reviewed, original, manifest)
    assert sum(c["group"] == "a" for c in changes.values()) == 28
    assert sum(c["group"] == "b" for c in changes.values()) == 2
    assert sum(len(c["added"]) for c in changes.values()) == 3
    assert sum(len(r["gold_chunk_ids"]) for r in reviewed) == 64


@pytest.mark.parametrize(
    "field",
    ["filters", "reference_answer", "question", "gold_removed", "gold_added", "duplicate_question"],
)
def test_review_rejects_unapproved_edits_without_repairing_them(field):
    original, reviewed, manifest = review_fixture()
    if field == "gold_removed":
        reviewed[0]["gold_chunk_ids"].pop(0)
    elif field == "gold_added":
        reviewed[4]["gold_chunk_ids"].append("not_approved")
    elif field == "duplicate_question":
        reviewed[1]["question"] = reviewed[0]["question"]
    else:
        reviewed[4][field] = {} if field == "filters" else "changed"
    before = deepcopy(reviewed)
    with pytest.raises(ValueError):
        check_review(reviewed, original, manifest)
    assert reviewed == before


def test_bridge_changes_only_gold_scoring_and_keeps_rankings_fixed():
    details = [
        {"question_id": "q", "mode": "vector", "ranked_ids": ["added", "old"]}
        | metrics(["added", "old"], {"old", "added", "miss"})
    ]
    changes = {"q": {"migrated_gold": ["old"]}}
    result = bridge_scores(details, changes)
    assert result[0]["ranked_ids"] == details[0]["ranked_ids"]
    assert result[0]["MRR@30"] == 0.5 and details[0]["MRR@30"] == 1
    assert result[0]["recall@10"] == 1 and details[0]["recall@10"] == 2 / 3
    assert result[0]["first_gold_rank"] == 2


def test_exposure_uses_pre_eval_review_pools_and_unique_exact_migration_only():
    def chunk(key, text):
        return {"id": key, "accession": "filing", "item": "7", "text": text}

    old = [chunk("old1", "exact"), chunk("old2", "ambiguous"), chunk("old3", "removed")]
    new = [chunk("new1", "exact"), chunk("new2", "ambiguous"), chunk("new3", "ambiguous")]
    records = [{"id": "q", "gold_chunk_ids": ["manual_gold"]}]
    inventory = {"pools": {"q": {m: ["reviewed_candidate"] for m in MODES}}}
    pools, evidence = reconstruct_exposure(
        records, old, new, {"q": [c["id"] for c in old]}, inventory, {"q"}
    )
    assert pools["q"] == {"new1", "reviewed_candidate", "manual_gold"}
    assert evidence["q"]["unmatched_old_candidates"] == ["old3"]
    assert evidence["q"]["ambiguous_old_candidates"] == ["old2"]
    inventory["pools"]["q"].pop("keyword")
    with pytest.raises(ValueError, match="complete pre-evaluation"):
        reconstruct_exposure(records, old, new, {"q": []}, inventory, {"q"})


@pytest.mark.parametrize("override", [None, "", "historical_v1"])
def test_active_v2_default_preserves_explicit_historical_override(monkeypatch, override):
    monkeypatch.delenv("RETRIEVAL_CORPUS", raising=False)
    kwargs = {} if override is None else {"retrieval_corpus": override}
    settings = Settings(
        _env_file=None, sec_user_agent="FilingLens tests tests@example.org", **kwargs
    )
    assert settings.retrieval_corpus == (override or V2)

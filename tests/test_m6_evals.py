"""M6 eval harness (D111-D123): pinned M5 cache keys, frozen artifacts, the M6 question sets,
configs and caps, the replay smoke test, failure categorization and report reproducibility.
No API key, database or model is needed."""

import hashlib
import json
import tomllib
from decimal import Decimal

import pytest

from evals import m6
from evals.failures import CATEGORIES, categorize, stalled_instances, summarize
from evals.generate import FROZEN_PATH, MANIFEST_PATH, load_frozen
from evals.runner import (
    Cache,
    Deps,
    EvalConfig,
    ReplayMiss,
    SystemConfig,
    config_hash,
    load_config,
    load_questions,
    preflight,
    replay_deps,
    subset_ids,
    system_settings,
)
from evals.smoke import run_smoke
from filinglens.agents.settings import RuntimeSettings
from filinglens.agents.tracing import TraceEvent
from filinglens.config import ROOT
from filinglens.llm.pricing import ModelPrice, PriceTable

CONFIGS = ROOT / "evals" / "configs"
MODELS = {
    "PLANNER_MODEL": "claude-sonnet-5-5",
    "WORKER_MODEL": "claude-haiku-5-5",
    "VERIFIER_MODEL": "claude-sonnet-5-5",
    "BASELINE_MODELS": "claude-sonnet-5-5,claude-opus-5-5,claude-fable-5-2",
}
M5_SYSTEM = "2672337d37a1c4749e46b1640e2449249f4b9fce707f2424c3af28481dde7549"
M5_KEYS = {  # D118: the accepted M5 cache keys never change
    ("m5_test_subset", "system"): M5_SYSTEM,
    ("m5_test_subset", "b0-sonnet"): (
        "784e3b2ab5360fe9afb65e4b4af561ff480eb255a9dc8aed1156587e505e45ed"
    ),
    ("m5_test_opus", "b0-opus"): (
        "4c121dace8201ad5984fc587e44ec56860d7e1322cd752ed76724801ac0e3a27"
    ),
    ("m5_test_fable", "b0-fable"): (
        "16e92aec0cb80aa246423b8803435a393d3c367c6455eb10a9b8212a8828396f"
    ),
    ("m5_test_b2_subset", "b2-sonnet"): (
        "46afee6f64fadaba307810dc8a838626fc2c1b798a9bab5d6b59942ea67a654d"
    ),
    ("m5_test_b1_subset", "b1-sonnet"): (
        "462e8302c4c24e61c1d9f2beabcf105643e3d3d8111fcad472c19884276c5b61"
    ),
    ("m5_dev_pilot", "system"): M5_SYSTEM,
    ("m5_handwritten", "system"): M5_SYSTEM,
    ("m5_probe", "system"): M5_SYSTEM,
}
FROZEN_TEXT = {  # SHA-256 of LF-normalized text, so any checkout's line endings verify
    "evals/questions_v1.jsonl": "4f270e35634a4fa3aa86e9bf75e40933bacfa14169188ecf2c4634cb69e6b1cb",
    "evals/handwritten_v2.jsonl": (
        "d71d60aaf2967066a9dd163828e2fbba90e0b0eec1fc74436a8daf109b049868"
    ),
    "evals/b2_contexts_v1.meta.jsonl": (
        "902e5a7a0c81e3f743e7c61e440dc7900eec11ef24b81fef3e06be28606f7846"
    ),
    "evals/b2_contexts_v1.subset_extra.meta.jsonl": (
        "087724b6026642881179f263a47d680fd7ff6ae80115daf34e4d1e3939c6018e"
    ),
}


def settings() -> RuntimeSettings:
    return RuntimeSettings(
        _env_file=None,
        sec_user_agent="FilingLens tests test@example.org",
        **{k.lower(): v for k, v in MODELS.items()},
    )


def keys(name: str) -> dict[str, str]:
    cfg = load_config(CONFIGS / f"{name}.toml")
    deps = replay_deps(cfg, settings())
    return {s.id: config_hash(system_settings(s, deps, cfg)) for s in cfg.systems}


def m6_configs() -> dict[str, dict]:
    return {
        p.stem: tomllib.loads(p.read_text(encoding="utf-8"))
        for p in sorted(CONFIGS.glob("m6_*.toml"))
    }


# ---------------------------------------------------------------- D118 keys and frozen files


def test_m5_cache_keys_are_pinned():
    for (name, system_id), expected in M5_KEYS.items():
        assert keys(name)[system_id] == expected, (name, system_id)


def test_m6_systems_have_their_own_keys_and_c2_is_the_m5_system():
    for name, data in m6_configs().items():
        if "systems" not in data:
            continue  # the judge plan
        for system_id, key in keys(name).items():
            if name == "m6_dev_explanatory_m5":
                assert key == M5_SYSTEM  # the accepted system, flags empty
            else:
                assert key != M5_SYSTEM, (name, system_id)
    assert (
        keys("m6_test_sample")["m6"] == keys("m6_handwritten")["m6"] == keys("m6_dev_numeric")["m6"]
    )  # one M6 system across splits


def test_frozen_artifacts_are_unchanged():
    for path, expected in FROZEN_TEXT.items():
        text = (ROOT / path).read_bytes().decode("utf-8").replace("\r\n", "\n")
        assert hashlib.sha256(text.encode()).hexdigest() == expected, path
    load_frozen(FROZEN_PATH, MANIFEST_PATH)  # the manifest hash check
    assert len(subset_ids()) == 180  # D105 hash check


# ---------------------------------------------------------------- D120/D121 question sets


def test_sample_50_is_frozen_and_reproducible():
    ids = m6.load_sample_50()
    records = {r["id"]: r for r in load_frozen(FROZEN_PATH, MANIFEST_PATH)}
    assert len(ids) == 50 and m6.COSTCO_MISS in ids
    assert all(records[i]["split"] == "test" and records[i]["sample_100"] for i in ids)
    templates = [records[i]["template"] for i in ids]
    assert {t: templates.count(t) for t in set(templates)} == {
        t: 8 if t == "trend_avg" else 7 for t in set(templates)
    }
    assert sorted(ids) == m6.sample_50_ids(list(records.values()))
    with pytest.raises(FileExistsError):
        m6.freeze_sample_50()
    with pytest.raises(ValueError):
        m6.load_sample_50(expected="0" * 64)


def test_explanatory_dev_set_is_frozen_and_distinct_from_handwritten():
    rows = m6.load_explanatory_dev()
    assert [r["id"] for r in rows] == [f"xd{i:02d}" for i in range(1, 11)]
    assert all(set(r) == {"id", "question", "split"} for r in rows)  # no references (D120)
    handwritten = (ROOT / "evals" / "handwritten_v2.jsonl").read_text(encoding="utf-8")
    texts = {json.loads(line)["question"].lower() for line in handwritten.splitlines()}
    assert not texts & {r["question"].lower() for r in rows}
    cfg = load_config(CONFIGS / "m6_dev_explanatory.toml")
    questions = load_questions(cfg)
    assert len(questions) == 10 and {q["template"] for q in questions} == {"explanatory_dev"}
    with pytest.raises(ValueError):
        m6.load_explanatory_dev(expected="0" * 64)


def test_dev_numeric_ids_come_from_the_dev_pilot():
    pilot = {q["id"] for q in load_questions(load_config(CONFIGS / "m5_dev_pilot.toml"))}
    cfg = load_config(CONFIGS / "m6_dev_numeric.toml")
    questions = load_questions(cfg)
    assert len(questions) == 35 and {q["id"] for q in questions} <= pilot
    assert {q["split"] for q in questions} == {"dev"}
    templates = [q["template"] for q in questions]
    assert set(templates.count(t) for t in set(templates)) == {5}


# ---------------------------------------------------------------- D123 caps


def test_m6_caps_fit_the_ceiling_and_cover_their_reservations():
    configs = m6_configs()
    base = [c for c in configs.values() if c.get("budget") == "m6"]
    # D123 re-sum rule: a finished step counts at its recorded actual spend, others at their cap.
    total = sum(Decimal(c.get("spent_usd", c["spend_cap_usd"])) for c in base)
    assert total <= Decimal("40.00")  # the student's hard ceiling (D123, D125)
    assert not [n for n, c in configs.items() if c.get("budget") not in ("m6",)]
    for name, data in configs.items():
        for system in data.get("systems", []):
            reserve = Decimal(system["max_cost_usd"]) * data["concurrency"]
            assert Decimal(data["spend_cap_usd"]) > reserve, name
            flags = system.get("flags", {})
            if name != "m6_dev_explanatory_m5":
                assert flags["budget_weighting"] == "input_price" and flags["prompt_caching"]
                assert flags["stall_guard_steps"] == 2 and flags["summary_cited_values"]
    for plan in ("m6_judges_d1", "m6_judges_ablations"):
        assert all((ROOT / c).exists() for c in configs[plan]["configs"])
    assert Decimal(configs["m6_handwritten"]["spend_cap_usd"].split()[0]) >= Decimal("7.875")


def test_preflight_requires_cache_prices_for_prompt_caching():
    cfg = EvalConfig(
        name="x",
        split="test",
        sample="all",
        systems=[SystemConfig(id="m6", kind="system", flags={"prompt_caching": True})],
        spend_cap_usd=Decimal("1"),
    )
    prices = PriceTable(
        {"m": ModelPrice(input_per_mtok=Decimal("1"), output_per_mtok=Decimal("2"))}
    )
    deps = Deps(prices=prices, system_settings={"models": {"planner": "m"}})
    fake = settings().model_copy(update={"anthropic_api_key": "k"})
    with pytest.raises(ValueError, match="cache prices"):
        preflight(cfg, fake, deps, retrieve=lambda m: m, count_facts=lambda s: 1)


# ---------------------------------------------------------------- D122 smoke


def test_smoke_replays_committed_records_without_keys_or_database(monkeypatch, tmp_path):
    for key, value in MODELS.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setenv("SEC_USER_AGENT", "FilingLens tests test@example.org")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    out = run_smoke(CONFIGS / "ci_smoke.toml")
    assert out["systems"]["m6"] == {
        "n": 10,
        "scored": 10,
        "correct": 10,
        "accuracy": "1",
        "passed": True,
    }
    with pytest.raises(ReplayMiss):
        run_smoke(CONFIGS / "ci_smoke.toml", cache=Cache(tmp_path))


# ---------------------------------------------------------------- D112 failures


def ev(seq, event_type, **payload):
    return TraceEvent(seq=seq, agent="x", event_type=event_type, payload=payload)


def llm(seq, instance, step, tool_calls=(), text="", messages=()):
    return ev(
        seq,
        "llm_call",
        instance=instance,
        step=step,
        response={"tool_calls": list(tool_calls), "text": text},
        new_messages=list(messages),
    )


def result(seq, instance, *, error=False, dup=None, sha="a"):
    payload = {"instance": instance, "is_error": error, "duplicate_of": dup}
    return ev(seq, "tool_result", **payload, **({} if dup else {"raw_sha256": sha}))


def test_stall_rule_matches_the_runtime_guard():
    events = [
        llm(1, "planner", 0, [{"name": "resolve_company"}]),
        result(2, "planner", sha="r"),
        llm(3, "planner", 1, [{"name": "resolve_company"}]),
        result(4, "planner", sha="r"),  # identical result
        llm(5, "planner", 2, [{"name": "list_available_metrics"}]),
        result(6, "planner", dup="planner/t1"),  # duplicate
        llm(7, "planner", 3, text="{}"),
        llm(8, "analyst:r0", 0, [{"name": "margin"}]),
        result(9, "analyst:r0", error=True),
        llm(10, "analyst:r0", 1, [{"name": "margin"}]),
        result(11, "analyst:r0", sha="new"),  # progress resets the analyst
        llm(12, "analyst:r0", 2, [{"name": "margin"}]),
        result(13, "analyst:r0", error=True),
    ]
    assert stalled_instances(events) == [("planner", 2)]


def test_categorize_records_and_traces():
    events = [
        ev(1, "tool_call", instance="analyst:r0", tool="json", rejected="TOOL_NOT_ALLOWED"),
        ev(2, "tool_call", instance="analyst:r0", tool="get_passage", rejected="TOOL_NOT_ALLOWED"),
        ev(3, "tool_call", instance="analyst:r0", tool="evaluate", rejected="UNTRACED_INPUTS"),
        llm(4, "analyst:r0", 1),  # empty reply
        llm(5, "analyst:r0", 2, messages=[{"text": "Your final reply was not valid. Errors:"}]),
        ev(
            6,
            "verification",
            failing={
                "summary": ["summary numbers ['14.87'] do not appear in any claim"],
                "caveat_1": ["verifier (unsupported): seasonality"],
            },
        ),
        ev(7, "verification", failing={"c1": ["verifier (unsupported): later round"]}),
        ev(8, "stall_guard", instance="planner", reason="no_progress", step=3),
    ]
    record = {
        "status": "done",
        "error": {"handled": "budget_finalized", "message": "Run used 201 tokens"},
        "raw_output": {"status": "partially_answered"},
        "usage": {"input_tokens": 160_000, "output_tokens": 1},
        "retrieval": {"seen": ["c9"]},
    }
    found = categorize(record, events, gold_chunks=["c1"])
    assert set(found) == {
        "budget stop after a draft (D073 finalization)",
        "partially answered",
        "retrieval miss (no gold chunk seen)",
        "invalid final-answer tool",  # json only; get_passage is a real tool
        "untraced quant call (D079)",
        "empty reply",
        "corrective retry: analyst",
        "revision: summary numbers not in claims (Stage 1)",
        "revision: unsupported caveat (Stage 2)",  # first round only; c1 came later
        "stall guard fired (D115)",
        "near budget (>150K tokens)",
    }
    no_draft = categorize({"status": "done", "error": {"handled": "stopped_without_draft"}}, [])
    assert set(no_draft) == {CATEGORIES[0]}
    m5_error = {"status": "error", "error": {"type": "BudgetExceeded", "message": "m"}}
    assert set(categorize(m5_error, [])) == {CATEGORIES[0]}


def test_summary_counts_examples_and_seeded_spot_checks():
    runs = [
        {
            "question_id": f"q{i}",
            "split": "dev" if i % 2 else "test",
            "categories": {"empty reply": "x"},
        }
        for i in range(8)
    ]
    out = summarize(runs)["empty reply"]
    assert out["counts"] == {"test": 4, "dev": 4}
    assert len(out["examples"]) == 2 and len(out["spot_check"]) == 5
    assert out["spot_check"] == summarize(list(reversed(runs)))["empty reply"]["spot_check"]


# ---------------------------------------------------------------- D118 report


def test_m5_report_regenerates_byte_for_byte(monkeypatch):
    from evals.report import REPORT_PATH, build_report

    for key, value in MODELS.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setenv("SEC_USER_AGENT", "FilingLens tests test@example.org")
    names = [
        "m5_test_subset",
        "m5_test_opus",
        "m5_test_fable",
        "m5_test_b2_subset",
        "m5_test_b1_subset",
        "m5_probe",
        "m5_handwritten",
    ]
    text = build_report([CONFIGS / f"{n}.toml" for n in names])
    committed = REPORT_PATH.read_bytes().decode("utf-8").replace("\r\n", "\n")
    m5_part = committed.split("\n## M6: improvement", 1)[0]  # the M6 sections follow (D118)
    assert text == m5_part + "\n## Ablations\n\n_M6._\n"


def test_m6_report_sections_render_offline_and_keep_the_m5_report(monkeypatch):
    from evals.m6_report import mean_diff_ci, sign_test
    from evals.report import REPORT_PATH, build_report

    for key, value in MODELS.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setenv("SEC_USER_AGENT", "FilingLens tests test@example.org")
    names = [
        "m5_test_subset",
        "m5_test_opus",
        "m5_test_fable",
        "m5_test_b2_subset",
        "m5_test_b1_subset",
        "m5_probe",
        "m5_handwritten",
    ]
    text = build_report([CONFIGS / f"{n}.toml" for n in names], m6=True)
    assert text == REPORT_PATH.read_bytes().decode("utf-8").replace("\r\n", "\n")
    m5_only = build_report([CONFIGS / f"{n}.toml" for n in names])
    assert text.startswith(m5_only.removesuffix("\n## Ablations\n\n_M6._\n"))
    for heading in ("### Ablations", "### Failure analysis", "### Handwritten explanatory"):
        assert heading in text
    assert sign_test([3, 4, 5], [3, 3, 3]) == (2, 0, 0.5)
    assert mean_diff_ci([1.0, 2.0], [1.0, 1.0])[0] == 0.5

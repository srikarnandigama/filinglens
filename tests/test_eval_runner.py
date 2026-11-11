"""Runner, baselines and B2 context (D087-D090), offline with fake SDK clients (test data only)."""

import asyncio
import json
from decimal import Decimal
from types import SimpleNamespace

import pytest

from evals import runner as r
from evals.b2_context import (
    B2Context,
    FilingWindow,
    build_context,
    printed_forms,
    statements_window,
    visible,
)
from evals.baselines import BaselineSpec, build_params, cost_usd
from filinglens.ingest.parse import Block
from filinglens.llm.pricing import ModelPrice, PriceTable

ANSWER = '{"value": 100, "unit": "USD", "choice": null, "status": "answered"}'


def message(text=ANSWER, stop="end_turn", inp=100, out=50, searches=0):
    block = SimpleNamespace(
        type="text", text=text, model_dump=lambda **_: {"type": "text", "text": text}
    )
    usage = SimpleNamespace(
        input_tokens=inp,
        output_tokens=out,
        cache_read_input_tokens=0,
        cache_creation_input_tokens=0,
        server_tool_use=SimpleNamespace(web_search_requests=searches, web_fetch_requests=0),
    )
    return SimpleNamespace(
        content=[block], usage=usage, stop_reason=stop, _request_id="req_1", id="msg_1"
    )


class FakeMessages:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []
        self.batches = FakeBatches(self)

    async def create(self, **params):
        self.calls.append(params)
        item = self.responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


class FakeBatches:
    def __init__(self, parent):
        self.parent = parent
        self.submitted = []

    async def create(self, requests):
        self.submitted.append(requests)
        self.current = requests
        return SimpleNamespace(id=f"batch_{len(self.submitted)}")

    async def retrieve(self, batch_id):
        return SimpleNamespace(processing_status="ended")

    async def results(self, batch_id):
        parent = self.parent

        async def gen():
            for req in self.current:
                msg = parent.responses.pop(0)
                yield SimpleNamespace(
                    custom_id=req["custom_id"],
                    result=SimpleNamespace(type="succeeded", message=msg),
                )

        return gen()


class StatusError(Exception):
    def __init__(self, status):
        super().__init__(f"status {status}")
        self.status_code = status


def questions(n=6):
    templates = ["lookup", "margin", "yoy_growth"]
    return [
        {
            "id": f"q_{i:02d}",
            "template": templates[i % 3],
            "question": f"Question {i}?",
            "gold_value": "100",
            "gold_unit": "USD",
            "gold_choice": None,
            "tolerance": {"kind": "relative", "value": "0.005"},
            "split": "dev",
            "sample_100": i < 2,
            "fairness": {"cutoff_bucket": {}, "restated": False, "derived_q4": False},
        }
        for i in range(n)
    ]


@pytest.fixture
def draft(tmp_path, monkeypatch):
    path = tmp_path / "draft.jsonl"
    path.write_text("".join(json.dumps(q) + "\n" for q in questions()), encoding="utf-8")
    monkeypatch.setattr(r, "DRAFT_PATH", path)
    monkeypatch.setattr(r, "B2_META", tmp_path / "none.jsonl")
    return path


def config(*systems, cap="10.00", sample="all"):
    return r.EvalConfig(
        name="t",
        split="dev",
        sample=sample,
        systems=list(systems),
        spend_cap_usd=Decimal(cap),
        questions="draft",
        concurrency=2,
    )


def deps(client, **kw):
    prices = PriceTable(
        {"m": ModelPrice(input_per_mtok=Decimal("1000"), output_per_mtok=Decimal("1000"))}
    )
    return r.Deps(
        anthropic_client=client,
        prices=prices,
        models={"BASELINE_MODELS[0]": "m"},
        sleep=_no_sleep,
        **kw,
    )


async def _no_sleep(_):
    return None


B0 = r.SystemConfig(id="b0", kind="b0", model_env="BASELINE_MODELS", model_index=0)


def run(cfg, d, cache, **kw):
    return asyncio.run(r.Runner(cfg, d, cache, **kw).run())


def test_config_rejects_batch_for_b0_and_system(tmp_path):
    path = tmp_path / "c.toml"
    path.write_text(
        'name="x"\nsplit="dev"\nspend_cap_usd="1"\n[[systems]]\nid="s"\nkind="b0"\nbatch=true\n'
    )
    with pytest.raises(ValueError, match="B1 and B2 only"):
        r.load_config(path)
    path.write_text(
        'name="x"\nsplit="dev"\nspend_cap_usd="1"\nsample="sample_100"\n'
        '[[systems]]\nid="s"\nkind="b2"\nbatch=true\nmodel_env="M"\nmodel_index=0\n'
    )
    cfg = r.load_config(path)
    assert cfg.systems[0].batch and cfg.systems[0].model_index == 0 and cfg.sample == "sample_100"


def test_schedule_is_seeded_and_interleaves_templates(draft):
    qs = r.load_questions(config(B0))
    assert [q["id"] for q in qs] == [q["id"] for q in r.load_questions(config(B0))]
    assert len({q["template"] for q in qs[:3]}) == 3  # stratified prefix
    assert len(r.load_questions(config(B0, sample="3"))) == 3
    assert {q["id"] for q in r.load_questions(config(B0, sample="sample_100"))} == {"q_00", "q_01"}


def test_cache_resume_and_question_text_check(draft, tmp_path):
    cache = r.Cache(tmp_path / "cache")
    client = SimpleNamespace(messages=FakeMessages([message() for _ in range(6)]))
    out = run(config(B0), deps(client), cache)
    assert out["summary"]["counts"] == {"b0:done": 6}
    assert all(rec["prediction"]["value"] == "100" for rec in out["records"]["b0"])
    assert Decimal(out["summary"]["spent_usd"]) == Decimal("0.9")  # 6 x 150 tokens x $1000/MTok
    again = run(config(B0), deps(SimpleNamespace(messages=FakeMessages([]))), cache)
    assert again["summary"]["counts"] == {"b0:cached": 6} and again["summary"]["spent_usd"] == "0"
    shash = out["summary"]["systems"]["b0"]["config_hash"]
    changed = dict(questions()[0], question="A different question?")
    assert cache.get(shash, changed) is None  # text changed: a miss, never reused
    assert not list((tmp_path / "cache").rglob("*.tmp"))  # atomic writes leave no temp files


def test_spend_cap_stops_cleanly_and_resumes(draft, tmp_path):
    cache = r.Cache(tmp_path / "cache")
    capped = r.SystemConfig(
        id="b0", kind="b0", model_env="BASELINE_MODELS", model_index=0, reserve_usd=Decimal("0.20")
    )
    client = SimpleNamespace(messages=FakeMessages([message() for _ in range(6)]))
    out = run(config(capped, cap="0.50"), deps(client), cache)
    counts = out["summary"]["counts"]
    assert out["summary"]["stopped_by_cap"] and counts["b0:skipped_spend_cap"] >= 1
    assert Decimal(out["summary"]["spent_usd"]) <= Decimal("0.50")
    done = counts["b0:done"]
    more = SimpleNamespace(messages=FakeMessages([message() for _ in range(6)]))
    resumed = run(config(capped, cap="10.00"), deps(more), cache)
    assert resumed["summary"]["counts"] == {"b0:cached": done, "b0:done": 6 - done}


def test_retries_transient_errors_then_records_failures(draft, tmp_path):
    client = SimpleNamespace(
        messages=FakeMessages(
            [StatusError(429), StatusError(503), message()] + [message() for _ in range(5)]
        )
    )
    out = run(config(B0), deps(client), r.Cache(tmp_path / "a"))
    first = next(x for x in out["records"]["b0"] if x["attempts"] == 3)
    assert first["status"] == "done"
    bad = SimpleNamespace(messages=FakeMessages([StatusError(400)] + [message() for _ in range(5)]))
    out = run(config(B0), deps(bad), r.Cache(tmp_path / "b"))
    errors = [x for x in out["records"]["b0"] if x["status"] == "error"]
    assert len(errors) == 1 and errors[0]["attempts"] == 1  # 400 is not retried


def test_replay_only_never_calls_and_fails_on_a_miss(draft, tmp_path):
    with pytest.raises(r.ReplayMiss):
        run(
            config(B0),
            r.Deps(models={"BASELINE_MODELS[0]": "m"}),
            r.Cache(tmp_path / "c"),
            replay_only=True,
        )


def test_batch_continues_pause_turn_and_marks_latency_not_comparable(draft, tmp_path):
    b1 = r.SystemConfig(id="b1", kind="b1", model_env="BASELINE_MODELS", model_index=0, batch=True)
    paused = message(text="searching ", stop="pause_turn", searches=2)
    fakes = FakeMessages([paused] + [message(searches=1) for _ in range(6)])
    client = SimpleNamespace(messages=fakes)
    d = deps(client, web_search_per_1000=Decimal("10.00"), batch_multiplier=Decimal("0.5"))
    out = run(config(b1), d, r.Cache(tmp_path / "c"))
    records = {x["question_id"]: x for x in out["records"]["b1"]}
    assert len(fakes.batches.submitted) == 2 and len(fakes.batches.submitted[1]) == 1
    continued = next(x for x in records.values() if x["usage"]["web_searches"] == 3)
    assert continued["raw_output"].startswith("searching ") and continued["prediction"]["parse_ok"]
    assert all(
        x["latency_ms"] is None and x["latency_note"] == "batch, not comparable"
        for x in records.values()
    )
    tool = fakes.batches.submitted[0][0]["params"]["tools"][0]
    assert tool == {"type": "web_search_20260209", "name": "web_search", "max_uses": 5}


def test_b1_cost_includes_search_fees_and_batch_discount():
    price = ModelPrice(input_per_mtok=Decimal("2"), output_per_mtok=Decimal("10"))
    usage = {"input_tokens": 1_000_000, "output_tokens": 100_000, "web_searches": 3}
    assert cost_usd(usage, price, Decimal("10.00"), Decimal("0.5")) == Decimal("1.5") + Decimal(
        "0.03"
    )
    with pytest.raises(ValueError, match="web_search"):
        cost_usd(usage, price, None, None)
    params = build_params(BaselineSpec("b2", "m"), {"question": "Q?"}, context="CTX")
    assert (
        params["messages"][0]["content"].startswith("Filing excerpts:")
        and "temperature" not in params
    )


def test_statements_window_skips_contents_and_stops_at_notes():
    blocks = [
        Block("Consolidated Statements of Income | 54", "row", 1),
        Block("INCOME STATEMENTS"),
        *[Block(f"Revenue | 1{i},000 | 2,000", "row", 2) for i in range(5)],
        Block("BALANCE SHEETS"),
        Block("Total assets | 9,999", "row", 3),
        Block("Notes to Consolidated Financial Statements"),
        Block("Note 1 text that must not be included"),
    ]
    text, fallback = statements_window(blocks)
    assert not fallback and text.startswith("INCOME STATEMENTS") and "Total assets | 9,999" in text
    assert "must not be included" not in text and "| 54" not in text
    text, fallback = statements_window([Block("Cover page"), Block("Business text")])
    assert fallback and text.startswith("Cover page")
    tricky = [
        Block("Income Statement - Disaggregation of Income Statement Expenses"),
        Block("In November 2024, the FASB issued a new standard. " * 6),  # prose: a policy note
        *[Block(f"Other | 1{i},000", "row", 1) for i in range(5)],
        Block("INC OME STATEMENTS"),  # words split by the filing's markup
        *[Block(f"Revenue | 2{i},000", "row", 2) for i in range(5)],
    ]
    text, fallback = statements_window(tricky)
    assert not fallback and text.startswith("INC OME STATEMENTS")


def test_gold_visibility_and_truncation_order():
    assert "95,359" in printed_forms(Decimal("95359000000"))
    assert visible(Decimal("-1114000000"), "Other (expense) income, net | (1,114) | 695")
    assert not visible(Decimal("95359000000"), "Revenue | 195,359")  # no partial-number match
    q = {
        "id": "q",
        "computation": {
            "inputs": [
                {
                    "derived": False,
                    "value": "95359000000",
                    "source_accession": "NEW",
                    "source_filed": "2026-05-01",
                },
                {
                    "derived": True,
                    "value": "1",
                    "derivation_inputs": [
                        {"value": "7000000", "accession": "OLD", "filed": "2024-01-01"}
                    ],
                },
            ]
        },
    }
    windows = {
        "NEW": FilingWindow("NEW", "Revenue | 95,359\n" + "x" * 400, False, 105),
        "OLD": FilingWindow("OLD", "Nine months | 7,000\n" + "y" * 400, False, 105),
    }
    ctx = build_context(q, windows, cap_tokens=150)
    assert isinstance(ctx, B2Context) and ctx.truncated and ctx.filings[0] == "NEW"
    assert "95,359" in ctx.text and ctx.tokens <= 160  # the older filing was trimmed first


def test_baseline_cache_key_includes_the_indexed_model_id():
    sonnet = r.SystemConfig(id="b0s", kind="b0", model_env="BASELINE_MODELS", model_index=0)
    opus = r.SystemConfig(id="b0o", kind="b0", model_env="BASELINE_MODELS", model_index=1)
    d = r.Deps(models={"BASELINE_MODELS[0]": "model-a", "BASELINE_MODELS[1]": "model-b"})
    cfg = config(sonnet)
    a = r.system_settings(sonnet, d, cfg)
    b = r.system_settings(opus, d, cfg)
    assert a["model"] == "model-a" and b["model"] == "model-b"
    assert r.config_hash(a) != r.config_hash(b)
    with pytest.raises(ValueError, match="no model ID"):
        r.system_settings(opus, r.Deps(models={"BASELINE_MODELS[0]": "model-a"}), cfg)


def test_baseline_models_come_from_runtime_settings_and_env_file(tmp_path, monkeypatch):
    from filinglens.agents.settings import RuntimeSettings

    monkeypatch.delenv("BASELINE_MODELS", raising=False)
    env = tmp_path / ".env"
    env.write_text(
        "SEC_USER_AGENT=FilingLens test test@example.org\nBASELINE_MODELS=model-a, model-b\n",
        encoding="utf-8",
    )
    settings = RuntimeSettings(_env_file=env)
    opus = r.SystemConfig(id="b0o", kind="b0", model_env="BASELINE_MODELS", model_index=1)
    assert r.resolve_model(opus, settings) == "model-b"
    env.write_text("SEC_USER_AGENT=FilingLens test test@example.org\nBASELINE_MODELS=\n")
    with pytest.raises(ValueError, match="Set BASELINE_MODELS"):
        r.resolve_model(opus, RuntimeSettings(_env_file=env))  # blank is unset
    with open(r.__file__, encoding="utf-8") as source:
        assert "dotenv" not in source.read()  # Settings is the only .env reader


def test_preflight_checks_key_questions_prices_access_and_data(draft):
    b0 = r.SystemConfig(id="b0", kind="b0", model_env="BASELINE_MODELS", model_index=0)
    settings = SimpleNamespace(anthropic_api_key="sk-test-secret", snapshot_id="s")
    required = []
    prices = SimpleNamespace(require=required.append)
    d = r.Deps(
        prices=prices,
        models={"BASELINE_MODELS[0]": "model-a"},
        system_settings={"models": {"planner": "model-p"}},
    )
    report = r.preflight(config(b0), settings, d, retrieve=lambda m: m, count_facts=lambda s: 2715)
    assert report["questions"] == 6 and report["snapshot_facts"] == 2715
    assert required == [{"model-a", "model-p"}]
    assert report["accessible"] == {"model-a": True, "model-p": True}
    assert "sk-test-secret" not in json.dumps(report, default=str)  # never the key itself
    with pytest.raises(ValueError, match="model access failed"):
        r.preflight(config(b0), settings, d, retrieve=lambda m: "other", count_facts=lambda s: 1)
    with pytest.raises(ValueError, match="no financial_facts"):
        r.preflight(config(b0), settings, d, retrieve=lambda m: m, count_facts=lambda s: 0)
    with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
        r.preflight(config(b0), SimpleNamespace(anthropic_api_key=None), d)


# ---------------------------------------------------------------- one MCP hub, clean exit (D103)

SYSTEM = r.SystemConfig(id="system", kind="system")


class Boom(BaseException):
    """A failure that the per-question error handling does not swallow (aborts the run)."""


def _answer(cost="0.01"):
    return {
        "run_status": "done",
        "cost_usd": cost,
        "prediction": {"value": "100", "unit": "USD", "status": "answered", "parse_ok": True},
    }


def test_system_hub_opens_once_and_is_shared_by_concurrent_workers(draft, tmp_path, monkeypatch):
    from evals import system_adapter
    from filinglens.agents import mcp_client, orchestrator

    hubs, seen, live = [], [], {"now": 0, "max": 0}

    class FakeHub:
        def __init__(self, settings, *, retrieval_mode, log_dir):
            self.mode, self.closed = retrieval_mode, False
            hubs.append(self)

        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            self.closed = True

    async def fake_run_system(question, cfg, settings, hub, prices, handwritten):
        live["now"] += 1
        live["max"] = max(live["max"], live["now"])
        await asyncio.sleep(0.01)  # let the other worker start while this one is in flight
        live["now"] -= 1
        seen.append(hub)
        return _answer()

    monkeypatch.setattr(mcp_client, "McpHub", FakeHub)
    monkeypatch.setattr(system_adapter, "run_system", fake_run_system)
    monkeypatch.setattr(orchestrator, "load_prompts", lambda: {})
    monkeypatch.setattr(orchestrator, "resolve_models", lambda cfg, s: {"planner": "p"})
    settings = SimpleNamespace(max_run_tokens=200_000, snapshot_id="s", retrieval_corpus="c")
    run_one, keyed, lifespan = r.system_runner(settings, None)
    d = r.Deps(system_runner=run_one, system_settings=keyed, lifespan=lifespan)
    out = run(config(SYSTEM), d, r.Cache(tmp_path / "cache"))
    assert live["max"] == 2  # concurrency 2 really overlapped
    assert len(hubs) == 1 and hubs[0].mode == "vector"  # exactly one hub for the invocation
    assert len(seen) == 6 and all(h is hubs[0] for h in seen)
    assert hubs[0].closed and out["summary"]["status"] == "completed"
    with pytest.raises(RuntimeError, match="hub is not open"):  # never opened lazily by a worker
        asyncio.run(run_one(questions()[0], SYSTEM, False))


def _subprocess_lifespan(procs):
    """A real child process standing in for the MCP servers, closed by the runner."""
    import subprocess
    import sys
    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def lifespan(systems):
        proc = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(120)"])
        procs.append(proc)
        try:
            yield
        finally:
            proc.terminate()
            proc.wait(timeout=30)

    return lifespan


def _system_runner(fail_on=None):
    async def answer(question, system, handwritten):
        await asyncio.sleep(0.01)
        if question["id"] == fail_on:
            raise Boom("simulated abort")
        return _answer()

    return answer


def test_runner_closes_resources_and_finalizes_summary_after_completion_and_error(draft, tmp_path):
    procs = []
    d = r.Deps(system_runner=_system_runner(), lifespan=_subprocess_lifespan(procs))
    runner = r.Runner(config(SYSTEM), d, r.Cache(tmp_path / "ok"))
    asyncio.run(runner.run())
    assert procs[-1].poll() is not None  # no child process left behind
    assert runner.summary["status"] == "completed" and runner.summary["finished"]
    d = r.Deps(system_runner=_system_runner(fail_on="q_03"), lifespan=_subprocess_lifespan(procs))
    runner = r.Runner(config(SYSTEM), d, r.Cache(tmp_path / "boom"))
    with pytest.raises(Boom):
        asyncio.run(runner.run())
    assert procs[-1].poll() is not None
    summary = runner.summary
    assert summary["status"] == "error" and summary["error"]["type"] == "Boom"
    assert summary["finished"] and isinstance(summary["counts"], dict)


def test_main_exits_and_writes_its_summary_after_completion_and_error(draft, tmp_path, monkeypatch):
    path = tmp_path / "cfg.toml"
    path.write_text(
        'name = "t"\nsplit = "dev"\nquestions = "draft"\nspend_cap_usd = "5.00"\n'
        '[[systems]]\nid = "system"\nkind = "system"\n',
        encoding="utf-8",
    )
    procs, real_cache = [], r.Cache
    for case, fail_on in (("ok", None), ("boom", "q_03")):
        monkeypatch.setattr(r, "Cache", lambda c=case: real_cache(tmp_path / "cache" / c))
        monkeypatch.setattr(r, "RUNS_DIR", tmp_path / case)
        monkeypatch.setattr(
            r,
            "live_deps",
            lambda cfg, f=fail_on: r.Deps(
                system_runner=_system_runner(f), lifespan=_subprocess_lifespan(procs)
            ),
        )
        if fail_on:
            with pytest.raises(Boom):
                r.main([str(path)])
        else:
            assert r.main([str(path)]) == 0
        (written,) = list((tmp_path / case).glob("*.json"))
        status = json.loads(written.read_text(encoding="utf-8"))["status"]
        assert status == ("error" if fail_on else "completed")
        assert procs[-1].poll() is not None


def _mcp_server_descendants() -> list[int]:
    """PIDs of mcp_servers processes descended from this test process."""
    import os
    import subprocess

    if os.name == "nt":
        out = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                "Get-CimInstance Win32_Process | ForEach-Object "
                '{ "$($_.ProcessId) $($_.ParentProcessId) $($_.CommandLine)" }',
            ],
            capture_output=True,
            text=True,
            check=True,
        ).stdout
    else:
        out = subprocess.run(
            ["ps", "-eo", "pid=,ppid=,args="], capture_output=True, text=True, check=True
        ).stdout
    rows = [line.split(None, 2) for line in out.splitlines() if len(line.split(None, 2)) == 3]
    children: dict[int, list[tuple[int, str]]] = {}
    for pid, ppid, cmd in rows:
        if pid.isdigit() and ppid.isdigit():
            children.setdefault(int(ppid), []).append((int(pid), cmd))
    found, stack = [], [os.getpid()]
    while stack:
        for pid, cmd in children.get(stack.pop(), []):
            stack.append(pid)
            if "mcp_servers" in cmd:
                found.append(pid)
    return found


@pytest.mark.integration
@pytest.mark.skipif(
    __import__("os").environ.get("FILINGLENS_TEST_DB") != "1", reason="Set FILINGLENS_TEST_DB=1"
)
def test_real_mcp_servers_are_gone_after_the_lifespan_closes():
    from filinglens.agents.settings import RuntimeSettings
    from tests.agent_fakes import proactor_run

    _, _, lifespan = r.system_runner(RuntimeSettings(), None)

    async def exercise():
        async with lifespan([SYSTEM]) as hubs:
            assert set(hubs) == {"vector"}
            return _mcp_server_descendants()

    during = proactor_run(exercise())
    assert during  # the servers really ran as our descendants
    assert _mcp_server_descendants() == []


def test_replay_deps_hit_the_live_runs_cache_without_clients(draft, tmp_path, monkeypatch):
    from filinglens.agents import orchestrator

    monkeypatch.setattr(orchestrator, "load_prompts", lambda: {"planner": ("text", "sha-p")})
    monkeypatch.setattr(orchestrator, "resolve_models", lambda cfg, s: {"planner": "p"})
    settings = SimpleNamespace(
        max_run_tokens=200_000, snapshot_id="s", retrieval_corpus="c", baseline_models="m"
    )
    cache = r.Cache(tmp_path / "cache")
    live = r.Deps(system_runner=_system_runner(), system_settings=r.system_keyed(settings))
    run(config(SYSTEM), live, cache)
    replay = r.replay_deps(config(SYSTEM), settings)
    assert replay.anthropic_client is None and replay.lifespan is None
    out = run(config(SYSTEM), replay, cache, replay_only=True)
    assert all(rec["cached"] for rec in out["records"]["system"])  # same key as the live run
    assert r.replay_deps(config(B0), settings).models == {"BASELINE_MODELS[0]": "m"}
    with pytest.raises(r.ReplayMiss):  # an empty Deps cannot key the system's records
        run(config(SYSTEM), r.Deps(), cache, replay_only=True)

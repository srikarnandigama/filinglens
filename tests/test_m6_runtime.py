"""M6 runtime changes (D113-D117), offline with scripted providers and an in-memory hub.
Every flag defaults to the accepted M5 behavior (D118). Synthetic data only."""

from decimal import Decimal

import pytest

from evals.system_adapter import stopped_without_draft
from filinglens.agents.budget import BudgetExceeded, RunBudget
from filinglens.agents.context import LoopGuards
from filinglens.agents.ledger import Ledger
from filinglens.agents.loop import FINAL_STEP_GUARD, AgentOutputError, run_agent
from filinglens.agents.orchestrator import RunConfig, answer_sha256, run_question
from filinglens.agents.replay import replay_loaded
from filinglens.agents.schemas import Answer, DataWorkerOutput
from filinglens.agents.settings import RuntimeSettings
from filinglens.agents.toolbox import Toolbox
from filinglens.agents.tracing import MemoryTraceStore
from filinglens.agents.verifier import deterministic_checks
from filinglens.llm.anthropic_provider import AnthropicProvider
from filinglens.llm.base import LLMRequest, LLMResponse, Msg, Usage
from filinglens.llm.pricing import ModelPrice, PriceTable
from tests.agent_fakes import FakeHub, Script, ScriptedProvider, calls, final, make_context
from tests.test_budget_guards import FACT, analyst, hub, planner, verifier
from tests.test_llm_providers import SPEC, FakeAnthropicClient, anthropic_message

OK = {"subtask_id": "s1", "fact_ids": [], "notes": None}
QUESTION = "What was TEST revenue in FY2025 Q1?"


def prices() -> PriceTable:
    """Synthetic prices: fake-small costs 1/20 of fake-large, like Haiku vs Sonnet input."""
    return PriceTable(
        {
            "fake-large": ModelPrice(
                input_per_mtok=Decimal("2"),
                output_per_mtok=Decimal("10"),
                cache_read_per_mtok=Decimal("0.2"),
                cache_write_per_mtok=Decimal("2.5"),
            ),
            "fake-small": ModelPrice(input_per_mtok=Decimal("0.1"), output_per_mtok=Decimal("0.5")),
        }
    )


# ---------------------------------------------------------------- D113 budget weighting


def test_unweighted_budget_counts_exactly_as_before():
    budget = RunBudget(max_tokens=1000, prices=prices())
    budget.add("fake-small", Usage(input_tokens=300, output_tokens=100), "filings")
    assert budget.used_tokens == 400 and budget.max_call_tokens == {"filings": 400}


def test_weighted_budget_counts_large_model_tokens_at_one_and_small_at_their_price_ratio():
    budget = RunBudget(max_tokens=1000, prices=prices(), weight_reference="fake-large")
    budget.add("fake-large", Usage(input_tokens=300, output_tokens=100, cache_read_tokens=50))
    assert budget.used_tokens == 450  # the reference model counts every kind at weight 1
    budget.add("fake-small", Usage(input_tokens=4000, output_tokens=1000), "filings")
    assert budget.used_tokens == 450 + 250  # 5,000 tokens x 0.05
    assert budget.max_call_tokens["filings"] == 250  # D072 estimates use the same units
    assert budget.totals.input_tokens == 4300  # totals stay raw
    budget.add("fake-small", Usage(input_tokens=6000), "filings")
    with pytest.raises(BudgetExceeded, match="price-weighted tokens of MAX_RUN_TOKENS=1000"):
        budget.check_before_call()


def data_worker(step, messages, model):
    """The LLM data worker (fake-small) reads one metric, then answers with a large reply."""
    if step == 0:
        return calls(
            (
                "get_financial_metric",
                {
                    "ticker": "TEST",
                    "metric": "revenue",
                    "periods": [{"fiscal_year": 2025, "fiscal_period": "Q1"}],
                },
            )
        )
    return final(
        {"subtask_id": "s1", "fact_ids": ["1"], "notes": None},
        usage=Usage(input_tokens=10_000, output_tokens=50),
    )


async def ask(**flags):
    rounds: list[int] = []
    provider = ScriptedProvider(
        {
            "planner": planner,
            "data": data_worker,
            "analyst": analyst(rounds, Usage(input_tokens=100, output_tokens=50)),
            "verifier": verifier,
        }
    )
    store = MemoryTraceStore()
    result = await run_question(
        QUESTION,
        RunConfig(max_run_tokens=2000, data_worker="llm", **flags),
        RuntimeSettings(
            _env_file=None,
            sec_user_agent="FilingLens tests test@example.org",
            planner_model="fake-large",
            worker_model="fake-small",
            verifier_model="fake-large",
        ),
        providers={"anthropic": provider},
        store=store,
        prices=prices(),
        hub=hub(),
    )
    return result, store, store.events[result.run_id]


async def replays(result, store, events):
    meta = {**store.runs[result.run_id], "question": QUESTION}
    report = await replay_loaded(result.run_id, meta, events)
    assert report.identical, report.divergence
    return report


async def test_small_model_tokens_no_longer_exhaust_the_budget_before_a_draft():
    # Raw: planner 300 + data worker 10,200 > 2,000 before the analyst starts (M5: no answer).
    result, *_ = await ask()
    assert result.status == "error" and result.error["type"] == "BudgetExceeded"
    # Weighted: the data worker counts 510, so the draft and verification fit (D113).
    result, store, events = await ask(budget_weighting="input_price")
    assert result.status == "done" and result.answer.status in ("answered", "partially_answered")
    assert result.totals.input_tokens > 2000  # raw totals are still reported
    await replays(result, store, events)


async def test_budget_stop_before_a_draft_returns_an_explicit_answer_and_replays():
    result, store, events = await ask(finalize_without_draft=True)
    assert result.status == "done" and result.answer.claims == []
    assert result.answer.status == "not_available"
    assert "before an answer could be drafted" in result.answer.summary
    assert result.error["handled"] == "stopped_without_draft" and result.error["kind"] == "tokens"
    assert store.runs[result.run_id]["error"] == result.error
    assert stopped_without_draft(result.error)  # still scored as "no answer" (D114)
    assert [e for e in events if e.event_type == "budget_stopped_without_draft"]
    report = await replays(result, store, events)
    assert report.replay_answer_sha256 == answer_sha256(result.answer)


# ---------------------------------------------------------------- D115 loop guards


def guarded(ctx, **kw):
    ctx.guards = LoopGuards(**kw)
    return ctx


async def agent(ctx, tools, **kw):
    return await run_agent(
        ctx,
        instance="analyst:r0",
        system="You are the data worker for tests.",
        task="go",
        model="fake-large",
        provider="anthropic",
        output_model=DataWorkerOutput,
        toolbox=Toolbox(ctx, "analyst:r0", tools=tools),
        **kw,
    )


def stall_hub():
    return FakeHub(
        {
            "get_financial_metric": lambda a: {"error": {"code": "NOT_FOUND", "message": "x"}},
            "resolve_company": lambda a: {"data": {"ticker": "TEST"}},  # same for every spelling
            "search_filings": lambda a: {"data": {"hits": [], "query": a["query"]}},
        }
    )


def events_of(store, ctx, kind):
    return [e.payload for e in store.events[ctx.recorder.run_id] if e.event_type == kind]


async def test_two_no_progress_steps_force_the_final_step():
    def script():
        return Script(
            calls(("get_financial_metric", {"ticker": "A"})),
            calls(("get_financial_metric", {"ticker": "B"})),
            final(OK),
        )

    provider = script()
    ctx, store = make_context(stall_hub(), provider)
    await agent(guarded(ctx, stall_steps=2), ("get_financial_metric",))
    assert [r.get("tool_choice") for r in provider.requests] == [None, None, "none"]
    assert provider.seen[2][-1].text == FINAL_STEP_GUARD
    (event,) = events_of(store, ctx, "stall_guard")
    assert event == {
        "instance": "analyst:r0",
        "step": 1,
        "reason": "no_progress",
        "no_progress_steps": 2,
    }

    provider = script()  # M5 default: no guard until max_steps
    ctx, store = make_context(stall_hub(), provider)
    await agent(ctx, ("get_financial_metric",))
    assert [r.get("tool_choice") for r in provider.requests] == [None, None, None]
    assert not events_of(store, ctx, "stall_guard")


async def test_results_identical_to_earlier_ones_count_as_no_progress():
    provider = Script(
        calls(("resolve_company", {"query": "Test Inc"})),  # new information
        calls(("resolve_company", {"query": "TEST"})),  # same result: no progress
        calls(("resolve_company", {"query": "test"})),  # same result again
        final(OK),
    )
    ctx, _ = make_context(stall_hub(), provider)
    await agent(guarded(ctx, stall_steps=2), ("resolve_company",))
    assert [r.get("tool_choice") for r in provider.requests] == [None, None, None, "none"]


async def test_progress_resets_the_count_and_duplicates_do_not():
    provider = Script(
        calls(("get_financial_metric", {"ticker": "A"})),  # error
        calls(("search_filings", {"query": "X"})),  # new: resets
        calls(("get_financial_metric", {"ticker": "B"})),  # error
        calls(("search_filings", {"query": "X"})),  # D067 duplicate: no progress
        final(OK),
    )
    ctx, _ = make_context(stall_hub(), provider)
    await agent(guarded(ctx, stall_steps=2), ("get_financial_metric", "search_filings"))
    assert [r.get("tool_choice") for r in provider.requests] == [None, None, None, None, "none"]


async def test_an_invalid_output_after_a_forced_final_step_retries_with_tools():
    provider = Script(
        calls(("get_financial_metric", {"ticker": "A"})),
        calls(("get_financial_metric", {"ticker": "B"})),
        final("not json"),  # forced final step, invalid
        calls(("search_filings", {"query": "X"})),  # the retry may use tools
        final(OK),
    )
    ctx, _ = make_context(stall_hub(), provider)
    out = await agent(guarded(ctx, stall_steps=2), ("get_financial_metric", "search_filings"))
    assert out.subtask_id == "s1"
    assert [r.get("tool_choice") for r in provider.requests] == [None, None, "none", None, None]


def empty_reply() -> LLMResponse:
    return LLMResponse(
        text="",
        tool_calls=[],
        stop_reason="tool_use",
        raw_stop_reason="tool_use",
        usage=Usage(input_tokens=100, output_tokens=23),
        model="fake",
        provider_raw=[],
    )


async def test_an_empty_reply_gets_the_final_step_guard_without_spending_the_retry():
    provider = Script(empty_reply(), final("not json"), final(OK))
    ctx, store = make_context(stall_hub(), provider)
    assert (await agent(guarded(ctx, empty_reply=True), ("margin",))).subtask_id == "s1"
    assert [r.get("tool_choice") for r in provider.requests] == [None, "none", None]
    assert provider.seen[1][-1].text == FINAL_STEP_GUARD
    assert events_of(store, ctx, "stall_guard")[0]["reason"] == "empty_reply"

    provider = Script(empty_reply(), final("not json"), final(OK))  # M5: the retry is spent
    ctx, _ = make_context(stall_hub(), provider)
    with pytest.raises(AgentOutputError):
        await agent(ctx, ("margin",))


async def test_unknown_tool_names_get_a_hint_and_known_ones_keep_the_role_message():
    def run():
        return Script(
            calls(("json", {}), ("get_passage", {"chunk_id": "c"})),
            final(OK),
        )

    provider = run()
    ctx, _ = make_context(stall_hub(), provider)
    await agent(guarded(ctx, unknown_tool_hint=True), ("margin",))
    unknown, known = (p.content for p in provider.seen[1][-1].tool_results)
    assert 'There is no tool named \\"json\\"' in unknown and "plain text" in unknown
    assert "is not available to the analyst role" in known

    provider = run()  # M5 message for both
    ctx, _ = make_context(stall_hub(), provider)
    await agent(ctx, ("margin",))
    unknown, _ = (p.content for p in provider.seen[1][-1].tool_results)
    assert "json is not available to the analyst role" in unknown


# ---------------------------------------------------------------- D116 prompt caching


def test_cache_flag_leaves_old_fingerprints_unchanged():
    base = {"provider": "anthropic", "model": "m", "system": "s", "messages": [], "max_tokens": 9}
    plain = LLMRequest(**base)
    assert "cache" not in plain.model_dump(mode="json", exclude={"cache"})
    assert LLMRequest(**base, cache=False).fingerprint() == plain.fingerprint()
    assert LLMRequest(**base, cache=True).fingerprint() != plain.fingerprint()


async def test_only_cache_roles_request_caching():
    provider = Script(final(OK), final(OK))
    ctx, _ = make_context(stall_hub(), provider)
    guarded(ctx, cache_roles=frozenset({"analyst"}))
    await agent(ctx, ("margin",))
    await run_agent(
        ctx,
        instance="verifier:r0",
        system="You are the data worker for tests.",
        task="go",
        model="fake-large",
        provider="anthropic",
        output_model=DataWorkerOutput,
    )
    assert [r["cache"] for r in provider.requests] == [True, False]


async def test_anthropic_cache_breakpoints_on_system_and_automatic():
    client = FakeAnthropicClient(anthropic_message([{"type": "text", "text": "{}"}], "end_turn"))
    provider = AnthropicProvider(client)
    user = [Msg(role="user", text="q")]
    await provider.complete(system="s", messages=user, tools=[SPEC], model="m", max_tokens=9)
    assert client.params["system"] == "s" and "cache_control" not in client.params
    await provider.complete(
        system="s", messages=user, tools=[SPEC], model="m", max_tokens=9, cache=True
    )
    assert client.params["system"] == [
        {"type": "text", "text": "s", "cache_control": {"type": "ephemeral"}}
    ]
    assert client.params["cache_control"] == {"type": "ephemeral"}


def test_cache_tokens_are_priced_and_counted_in_the_budget():
    budget = RunBudget(max_tokens=10_000, prices=prices())
    cost = budget.add(
        "fake-large", Usage(input_tokens=100, cache_read_tokens=1000, cache_write_tokens=200)
    )
    assert cost == (100 * 2 + 1000 * Decimal("0.2") + 200 * Decimal("2.5")) / 1_000_000
    assert budget.used_tokens == 1300  # D060: every token kind counts
    with pytest.raises(Exception, match="cache_read_per_mtok"):
        prices().cost("fake-small", Usage(cache_read_tokens=1))


# ---------------------------------------------------------------- D117 summary rule


def summary_case(summary: str):
    ledger = Ledger()
    facts = [
        {**FACT, "fact_id": "1", "value": "14872000000"},
        {**FACT, "fact_id": "2", "value": "15390000000", "fiscal_period": "Q2"},
    ]
    ledger.register(
        "get_financial_metric",
        {},
        {"data": {"ticker": "TEST", "metric": "revenue", "facts": facts}},
        False,
        None,
    )
    ledger.register(
        "summary_stats",
        {"values": ["14872000000", "15390000000"]},
        {"data": {"values": ["14872000000", "15390000000"], "mean": "15131000000"}},
        False,
        "cmp_1",
    )
    answer = Answer.model_validate(
        {
            "status": "answered",
            "summary": summary,
            "claims": [
                {
                    "id": "c1",
                    "kind": "numeric",
                    "text": "The mean was $15.131 billion.",
                    "value": "15131000000",
                    "unit": "USD",
                    "value_basis": "computation",
                    "citations": [{"kind": "computation", "ref": "cmp_1", "field": "mean"}],
                }
            ],
            "final_value": "15131000000",
            "final_unit": "USD",
            "final_claim_id": "c1",
        }
    )
    return answer, ledger


@pytest.mark.parametrize(
    ("summary", "on_ok"),
    [
        ("The mean was $15.131 billion, from $14.87 billion and $15.39 billion.", True),
        (
            "The mean was $15.131 billion; the quarters were 14,872 million and 15,390 million.",
            True,
        ),
        ("The mean was $15.131 billion, from $14.88 billion.", False),  # wrong rounding
        ("The mean was $15.131 billion; a third quarter was $16.20 billion.", False),  # uncited
    ],
)
def test_summary_numbers_may_round_cited_values(summary, on_ok):
    answer, ledger = summary_case(summary)
    assert deterministic_checks(answer, ledger, True)["summary"].verdict == "needs_revision"
    on = deterministic_checks(answer, ledger, True, summary_cited_values=True)["summary"]
    assert (on.verdict == "supported") is on_ok


M6_FLAGS = {
    "budget_weighting": "input_price",
    "finalize_without_draft": True,
    "stall_guard_steps": 2,
    "empty_reply_guard": True,
    "unknown_tool_hint": True,
    "prompt_caching": True,
    "summary_cited_values": True,
}


async def test_a_full_m6_run_with_a_stalled_planner_replays_identically(monkeypatch):
    original = planner

    def stalling_planner(step, messages, model):
        if step in (1, 2):  # repeats its discovery call: D067 duplicates, no progress
            return calls(("list_available_metrics", {"ticker": "TEST"}))
        return original(0 if step == 0 else 1, messages, model)

    monkeypatch.setitem(globals(), "planner", stalling_planner)
    result, store, events = await ask(**M6_FLAGS)
    assert result.status == "done", result.error
    assert result.answer.status in ("answered", "partially_answered")
    guard = [e.payload for e in events if e.event_type == "stall_guard"]
    assert guard == [
        {"instance": "planner", "step": 2, "reason": "no_progress", "no_progress_steps": 2}
    ]
    planner_calls = [
        e.payload
        for e in events
        if e.event_type == "llm_call" and e.payload["instance"] == "planner"
    ]
    assert [p["tool_choice"] for p in planner_calls] == [None, None, None, "none"]
    await replays(result, store, events)

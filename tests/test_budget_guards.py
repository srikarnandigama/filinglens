"""Revision reservation, budget finalization, passage-read cap and derivation evidence
(D072-D075), offline with scripted providers and an in-memory hub. Synthetic data only."""

import json
from decimal import Decimal

from filinglens.agents.ledger import Ledger
from filinglens.agents.orchestrator import RunConfig, answer_sha256, run_question
from filinglens.agents.replay import replay_loaded
from filinglens.agents.schemas import FilingsWorkerOutput, Plan, SubTask
from filinglens.agents.settings import RuntimeSettings
from filinglens.agents.toolbox import Toolbox
from filinglens.agents.tracing import MemoryTraceStore
from filinglens.agents.verifier import sources_for
from filinglens.agents.workers import SubtaskResult, evidence_pack, run_filings
from filinglens.llm.base import Usage
from tests.agent_fakes import (
    FakeHub,
    Script,
    ScriptedProvider,
    calls,
    envelopes,
    fake_prices,
    final,
    make_context,
    requested_ids,
)
from tests.test_agent_units import discovery

FACT = {
    "fact_id": "1",
    "metric": "revenue",
    "fiscal_year": 2025,
    "fiscal_period": "Q1",
    "value": "400",
    "unit": "USD",
    "status": "available",
    "period_start": "2025-01-01",
    "period_end": "2025-03-31",
}
CLAIM = {
    "id": "c1",
    "kind": "numeric",
    "text": "TEST revenue was 400 USD in FY2025 Q1.",
    "value": "400",
    "unit": "USD",
    "value_basis": "fact",
    "ticker": "TEST",
    "period": {"fiscal_year": 2025, "fiscal_period": "Q1"},
    "citations": [{"kind": "fact", "ref": "1"}],
}
CAVEAT = "Only one quarter was requested."
BIG = Usage(input_tokens=1000, output_tokens=50)
SMALL = Usage(input_tokens=100, output_tokens=50)
WEAK = "Revenue grew strongly."


def hub() -> FakeHub:
    return FakeHub(
        {
            "list_available_metrics": lambda a: {"data": discovery()},
            "get_financial_metric": lambda a: {
                "data": {"ticker": "TEST", "metric": "revenue", "snapshot": {}, "facts": [FACT]}
            },
        }
    )


def planner(step, messages, model):
    if step == 0:
        return calls(("list_available_metrics", {"ticker": "TEST"}))
    return final(
        {
            "question_type": "lookup",
            "companies": ["TEST"],
            "period_resolutions": [
                {
                    "phrase": "FY2025 Q1",
                    "ticker": "TEST",
                    "resolved": [{"fiscal_year": 2025, "fiscal_period": "Q1"}],
                    "basis": "period calendar",
                }
            ],
            "answerability": "answerable",
            "subtasks": [
                {
                    "id": "s1",
                    "type": "metric_lookup",
                    "description": "revenue",
                    "params": {
                        "kind": "metric_lookup",
                        "ticker": "TEST",
                        "metric": "revenue",
                        "periods": [{"fiscal_year": 2025, "fiscal_period": "Q1"}],
                    },
                }
            ],
        }
    )


def analyst(rounds: list[int], revision_usage: Usage):
    """Round 0 drafts c1 and a weak c2; the revision rewrites c2 (with configurable usage)."""

    def handle(step, messages, model):
        rounds.append(1)
        revised = len(rounds) > 1
        weak = "TEST revenue was reported for FY2025 Q1." if revised else WEAK
        answer = {
            "status": "answered",
            "summary": "TEST revenue was 400 USD.",
            "claims": [
                CLAIM,
                {"id": "c2", "kind": "textual", "text": weak, "citations": CLAIM["citations"]},
            ],
            "final_value": "400",
            "final_unit": "USD",
            "final_claim_id": "c1",
            "caveats": [CAVEAT],
        }
        return final(answer, usage=revision_usage) if revised else final(answer)

    return handle


def verifier(step, messages, model):
    draft = next(body for tag, _, body in envelopes(messages[:1]) if tag == "evidence")
    claim_ids, caveat_ids = requested_ids(messages)
    texts = {c["id"]: c["text"] for c in draft["claims"]}
    return final(
        {
            "verdicts": [
                {
                    "claim_id": cid,
                    "verdict": "needs_revision" if texts[cid] == WEAK else "supported",
                    "reason": "overstates the evidence" if texts[cid] == WEAK else "ok",
                }
                for cid in claim_ids
            ],
            "summary_verdict": {"claim_id": "summary", "verdict": "supported", "reason": "ok"},
            "caveat_verdicts": [
                {"claim_id": cid, "verdict": "supported", "reason": "ok"} for cid in caveat_ids
            ],
        }
    )


async def ask(max_run_tokens: int, revision_usage: Usage = SMALL):
    rounds: list[int] = []
    provider = ScriptedProvider(
        {"planner": planner, "analyst": analyst(rounds, revision_usage), "verifier": verifier}
    )
    store = MemoryTraceStore()
    result = await run_question(
        "What was TEST revenue in FY2025 Q1?",
        RunConfig(max_run_tokens=max_run_tokens),
        RuntimeSettings(
            planner_model="fake-large", worker_model="fake-large", verifier_model="fake-large"
        ),
        providers={"anthropic": provider},
        store=store,
        prices=fake_prices("fake-large"),
        hub=hub(),
    )
    events = store.events[result.run_id]
    return result, store, events, rounds


def of_type(events, kind):
    return [e.payload for e in events if e.event_type == kind]


async def test_revision_is_skipped_when_the_budget_cannot_cover_it():
    # Each scripted call uses 150 tokens: planner x2, analyst r0 and verifier r0 = 600 used.
    # Estimate = (150 + 150) x 1.5 = 450 > 400 remaining, so no revision starts.
    result, _, events, rounds = await ask(max_run_tokens=1000)
    assert len(rounds) == 1 and result.status == "done" and result.error is None
    (skipped,) = of_type(events, "revision_skipped")
    assert skipped["estimated_tokens"] == 450 and skipped["remaining_tokens"] == 400
    assert set(skipped["dropped"]) == {"c2"}
    answer = result.answer
    assert [c.id for c in answer.claims] == ["c1"] and answer.status == "partially_answered"
    assert "1 claim could not be verified and was removed." in answer.caveats
    assert not any("Revenue grew strongly" in c or "overstates" in c for c in answer.caveats)
    assert skipped["removed"]["c2"] == {
        "text": "Revenue grew strongly.",
        "reasons": ["verifier (needs_revision): overstates the evidence"],
    }  # full text and verifier reason stay in the trace (D078)
    assert not of_type(events, "budget_finalized")

    # With room for the estimate the revision runs and is verified normally.
    result, _, events, rounds = await ask(max_run_tokens=200_000)
    assert len(rounds) == 2 and not of_type(events, "revision_skipped")
    assert result.answer.status == "answered" and len(result.answer.claims) == 2


async def test_budget_stop_after_a_draft_finalizes_only_verified_content_and_replays():
    # The revision is allowed (500 left >= 450) but uses 1,050 tokens, so the token check
    # before verifier:r1 raises BudgetExceeded with the revised draft unverified.
    result, store, events, rounds = await ask(max_run_tokens=1100, revision_usage=BIG)
    assert len(rounds) == 2
    assert result.status == "done"
    assert result.error == {
        "type": "BudgetExceeded",
        "kind": "tokens",
        "message": "Run used 1650 tokens of MAX_RUN_TOKENS=1100.",
        "handled": "budget_finalized",
    }
    assert store.runs[result.run_id]["error"] == result.error  # recorded in the runs row
    answer = result.answer
    assert answer.status == "partially_answered"
    assert [c.id for c in answer.claims] == ["c1"]  # exact form passed Stage 1 and Stage 2
    assert answer.final_value == "400" and answer.summary == "TEST revenue was 400 USD."
    assert answer.caveats[0] == CAVEAT  # verified in round 0, unchanged in the revision
    assert answer.caveats[1:] == [
        "1 claim could not be verified and was removed.",
        "Verification was cut short by the run's token budget (MAX_RUN_TOKENS); only claims "
        "verified in both stages were kept.",
    ]
    (event,) = of_type(events, "budget_finalized")
    assert event["kept"] == ["c1"] and set(event["dropped"]) == {"c2"}
    assert event["removed"]["c2"]["text"] == "TEST revenue was reported for FY2025 Q1."
    assert not [p for p in of_type(events, "llm_call") if p["instance"] == "verifier:r1"]

    meta = {**store.runs[result.run_id], "question": "What was TEST revenue in FY2025 Q1?"}
    report = await replay_loaded(result.run_id, meta, events)
    assert report.identical, report.divergence
    assert report.replay_answer_sha256 == answer_sha256(answer)


async def test_budget_stop_before_any_draft_is_still_a_run_error():
    result, store, events, _ = await ask(max_run_tokens=300)  # planner used it all
    assert result.status == "error" and result.answer is None
    assert result.error["type"] == "BudgetExceeded" and "handled" not in result.error
    assert not of_type(events, "budget_finalized")


def hit(i: int) -> dict:
    return {
        "chunk_id": f"chk_{i:064x}",
        "ticker": "TEST",
        "form": "10-K",
        "fiscal_year": 2024,
        "fiscal_period": "FY",
        "item": "7",
        "title": "MD&A",
        "accession": "0000000000-25-000001",
        "url": "https://www.sec.gov/test",
        "text": f"passage {i} text",
    }


async def test_filings_worker_reads_at_most_four_full_passages():
    fake = FakeHub({"get_passage": lambda a: {"data": hit(int(a["chunk_id"][4:], 16))}})
    ids = [hit(i)["chunk_id"] for i in range(6)]
    provider = Script(
        calls(*[("get_passage", {"chunk_id": c}) for c in ids[:5]]),
        calls(("get_passage", {"chunk_id": ids[5]}), ("get_passage", {"chunk_id": ids[0]})),
        final(
            {
                "subtask_id": "s1",
                "found": True,
                "passages": [{"chunk_id": ids[0], "relevance": "r", "quotes": ["passage 0"]}],
            }
        ),
    )
    ctx, _ = make_context(fake, provider)
    ctx.ledger.register(
        "search_filings", {}, {"data": {"hits": [hit(i) for i in range(6)]}}, False, None
    )
    subtask = SubTask.model_validate(
        {
            "id": "s1",
            "type": "filing_search",
            "description": "d",
            "params": {
                "kind": "filing_search",
                "ticker": "TEST",
                "fiscal_year": 2024,
                "fiscal_period": "FY",
                "items": ["7"],
                "query": "q",
            },
        }
    )
    result = await run_filings(
        ctx,
        RunConfig(),
        {"worker": "fake-large"},
        {"filings_worker": ("You are the filings worker for tests.", "x")},
        subtask,
        "question",
    )
    assert isinstance(result.filings, FilingsWorkerOutput) and result.filings.found
    assert [c[2]["chunk_id"] for c in fake.calls] == ids[:4]  # only four reads executed
    first, second = provider.seen[1][-1].tool_results, provider.seen[2][-1].tool_results
    assert [p.is_error for p in first] == [False, False, False, False, True]
    assert '"code": "CALL_LIMIT"' in first[4].content and "at most 4" in first[4].content
    assert '"code": "CALL_LIMIT"' in second[0].content  # still capped on later turns
    assert second[1].content.startswith("duplicate call")  # a repeat is not a new read
    assert Toolbox(ctx, "filings:s9", limits={"get_passage": 4}).limits == {"get_passage": 4}


def test_derived_facts_carry_their_derivation_into_analyst_and_verifier_evidence():
    annual = {
        **FACT,
        "fact_id": "7",
        "fiscal_period": "FY",
        "value": "1000",
        "period_start": "2024-04-01",
        "period_end": "2025-03-31",
    }
    q4 = {
        **FACT,
        "fact_id": "8",
        "fiscal_period": "Q4",
        "value": "300",
        "derived": True,
        "period_start": "2025-01-01",
        "period_end": "2025-03-31",
        "derivation_inputs": [
            {
                "value": "1000",
                "coefficient": 1,
                "concept": "Revenues",
                "start_date": "2024-04-01",
                "end_date": "2025-03-31",
                "source": {"accession": "0000000000-25-000002", "url": "u", "filed_date": "d"},
            },
            {
                "value": "700",
                "coefficient": -1,
                "concept": "Revenues",
                "start_date": "2024-04-01",
                "end_date": "2024-12-31",
                "source": {"accession": "0000000000-25-000001", "url": "u", "filed_date": "d"},
            },
        ],
    }
    ledger = Ledger()
    data = {"ticker": "TEST", "metric": "revenue", "snapshot": {}, "facts": [annual, q4]}
    ledger.register("get_financial_metric", {}, {"data": data}, False, None)
    derivation = ledger.facts["8"].derivation
    assert derivation["formula"] == (
        "300 = 1000 (2024-04-01 to 2025-03-31) - 700 (2024-04-01 to 2024-12-31)"
    )
    assert derivation["inputs_reproduce_value"] is True
    assert [i["fact_id"] for i in derivation["inputs"]] == ["7", None]  # 9M YTD is not a fact
    assert [i["source_accession"] for i in derivation["inputs"]] == [
        "0000000000-25-000002",
        "0000000000-25-000001",
    ]
    assert ledger.facts["7"].derivation is None  # reported values carry none

    class Ctx:
        pass

    ctx = Ctx()
    ctx.ledger = ledger
    plan = Plan.model_validate(json.loads(planner(1, [], "m").text))
    pack = evidence_pack(ctx, plan, {"s1": SubtaskResult(subtask_id="s1", fact_ids=["8"])})
    assert pack["facts"][0]["records"][0]["derivation"] == derivation
    claim = {**CLAIM, "value": "300", "citations": [{"kind": "fact", "ref": "8"}]}
    from filinglens.agents.schemas import Answer

    answer = Answer.model_validate({"status": "answered", "summary": "s", "claims": [claim]})
    assert sources_for(answer, {"c1"}, ledger)["facts"]["8"]["derivation"] == derivation
    assert Decimal(derivation["inputs"][1]["coefficient"]) == -1

"""Opt-in, cost-capped live smoke test: one real LLM run, then an offline replay.

Never runs by default. Enable only deliberately (Phase C):
  FILINGLENS_LIVE_LLM=1 FILINGLENS_TEST_DB=1 python -m pytest tests/live -q
Optional: FILINGLENS_LIVE_MAX_USD (default 0.50).
"""

import asyncio
import os
from decimal import Decimal

import pytest

from filinglens.agents.orchestrator import RunConfig, run_question
from filinglens.agents.replay import replay_run
from filinglens.agents.settings import RuntimeSettings

pytestmark = pytest.mark.skipif(
    os.environ.get("FILINGLENS_LIVE_LLM") != "1" or os.environ.get("FILINGLENS_TEST_DB") != "1",
    reason="Live LLM calls cost money; set FILINGLENS_LIVE_LLM=1 and FILINGLENS_TEST_DB=1",
)


def test_live_lookup_answer_is_cited_and_replays_identically():
    settings = RuntimeSettings()
    cfg = RunConfig(
        retrieval_mode=settings.retrieval_mode,
        max_run_tokens=60_000,
        max_cost_usd=Decimal(os.environ.get("FILINGLENS_LIVE_MAX_USD", "0.50")),
    )
    factory = asyncio.ProactorEventLoop if os.name == "nt" else asyncio.new_event_loop
    with asyncio.Runner(loop_factory=factory) as runner:
        result = runner.run(
            run_question("What was Apple's total revenue in fiscal Q2 2025?", cfg, settings)
        )
        assert result.status == "done", result.error
        assert result.answer.claims and all(c.citations for c in result.answer.claims)
        report = runner.run(replay_run(settings.database_url, result.run_id))
    assert report.identical, report.divergence

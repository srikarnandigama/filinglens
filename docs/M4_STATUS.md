# M4 status: accepted

The student accepted M4 on 2026-11-09 after the final acceptance run. SPEC §16's
criterion holds: all six §1 question types returned valid `Answer` objects with resolved
citations, and every run replayed `identical` from `trace_events`. The full record of
all four acceptance rounds (pre-fix, post-fix 1, post-fix 2, final), with per-question
plans, tool calls, citations, verifier rounds, tokens and replays, is in
[M4_ACCEPTANCE.md](M4_ACCEPTANCE.md). The design and its amendments are D051–D082 in
[DECISIONS.md](DECISIONS.md).

## Final acceptance run (2026-11-09)

| Question (SPEC §1) | Answer | Verification rounds | Tokens | Cost (USD) | Replay |
|---|---|---:|---:|---:|---|
| Lookup: Apple total revenue, fiscal Q2 2025 | answered ($95,359,000,000) | 1 | 27,384 | 0.063 | identical |
| Trend: Nvidia gross margin, last 8 quarters | answered (74.56% → 74.98%, trough 60.52%) | 1 | 129,763 | 0.309 | identical |
| Derived: Microsoft Q4 FY2025 operating income | answered ($34,323,000,000, derived) | 1 | 28,739 | 0.067 | identical |
| Comparison: Walmart vs Costco net margin | answered (3.07% vs 3.04%) | 1 | 65,634 | 0.156 | identical |
| Explanatory: Tesla operating income decline | partially_answered (10 claims) | 1 | 190,269 | 0.253 | identical |
| Diff (stretch): Meta new risk factors | partially_answered (3 claims, non-exhaustive) | 1 | 133,314 | 0.134 | identical |
| **Total** | **6 / 6** | | **575,103** | **0.982** | **6 / 6** |

Configuration: `PLANNER_MODEL=claude-sonnet-5-5` (planner and analyst), `WORKER_MODEL=claude-haiku-5-5`,
`VERIFIER_MODEL=claude-sonnet-5-5`, `MAX_RUN_TOKENS=200000`, `--max-cost-usd 0.50`,
snapshot `2026-10-19-v1`, corpus v2, `RETRIEVAL_MODE=vector`. Prices are read from
`filinglens/llm/pricing.toml`.

## What was built

| Area | Main files |
|---|---|
| Providers | `filinglens/llm/` (Anthropic adapter on `anthropic` 2.1.0, API version 2026-10-21, no sampling parameters; OpenAI-compatible adapter; TOML pricing) |
| MCP client | `filinglens/agents/mcp_client.py` (both stdio servers with an explicit environment and no API keys) |
| Runtime | `loop.py` (hand-written loop), `toolbox.py` (role tools, argument locks, duplicate memo, call limits, untraced-input check), `budget.py`, `ledger.py`, `views.py` |
| Roles | `planner.py`, `workers.py` (direct metric lookups, Haiku filings worker), `verifier.py` (Stage 1 deterministic checks, Stage 2 LLM verifier), `orchestrator.py` (scheduling, revisions, budget reservation and finalization), `prompts/*.md` |
| Tracing and replay | `tracing.py` (runs and `trace_events`), `replay.py` (offline replay, divergence report) |
| CLI | `python -m filinglens.cli ask "<question>" [--max-cost-usd …] [--json]` and `python -m filinglens.cli replay <run_id>` |
| Schema | Migration 004 (`runs` and `trace_events` columns and constraints only) |

**Main safeguards added during Phase C:**
- D067: duplicate tool calls are answered from the earlier result.
- D068: on an agent's last step, the loop sends `tool_choice: none`.
- D069: every period resolution must name its companies.
- D070, D076, D077: the verifier reviews caveats, treats unsupported hedging as
  unsupported, and sees every current claim.
- D072, D073: revisions reserve their own budget, and a budget stop finalizes the
  verified content instead of discarding the answer.
- D074: filings workers may read at most 4 full passages.
- D075: derived facts carry their derivation into the evidence.
- D078: user-facing caveats are neutral.
- D079: quant calls must use at least one value from the evidence.

## Tests

Ruff lint and format pass. Full pytest, run once after the D081 test-only fix, with
database integration enabled: **223 passed, 2 skipped** (160.31 s). The two skips are
the opt-in live LLM smoke test and the opt-in M2 full-corpus chunk replay.

- 57 tests added in M4 (225 collected, against 168 at M3) across the agent loop, units,
  providers, verifier checks, budget guards, orchestrator, tracing/replay and MCP
  client. The D081 change widened only the timing tolerance of the M1
  `test_concurrent_request_pacing` test; the SEC client is unchanged.
- The orchestrator and replay integration tests use the real MCP servers and
  PostgreSQL with scripted providers. No test calls a real LLM; the single live smoke
  test is opt-in with `FILINGLENS_LIVE_LLM=1`.

## Known limitations and deferred items

- **Token headroom:** the Tesla explanatory run used about 190K of 200K tokens. Budget
  design (prompt caching, reservation under concurrency, cost-weighted budgets) is to be
  decided at the start of M5 (D082).
- **Passage figures in quant tools:** figures quoted in filing passages cannot feed
  quant tools; D079 rejected a legitimate sum in the Tesla run. Accepting verified-quote
  values is an M6 candidate (D082).
- **Stall diagnosis:** the analyst's earlier no-op tool calls could not be explained from
  the trace, because thinking text is not returned by default (D080). The summarized
  thinking display is an M6 candidate (D082).
- **One calculation per step:** the analyst still issues dependent calculations one per
  step (extra steps, not failures).
- **Comparative-column sources:** cited facts can come from a later filing's comparative
  column (M1 latest-filed rule). Values are correct, but the citation points to the
  later filing.
- **First-search latency:** each run pays about 7 s on its first filing search for the
  lazy ML imports, and about 50 s after a venv rebuild or reboot (D071).
- **Carried over from M3:** adjacent-chunk navigation is an M6 candidate. CVX FY2024
  Item 7's boundary runs slightly into Item 8 (documented, not fixed).

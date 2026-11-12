# Project instructions

This project is specified in SPEC.md. Read it before doing anything.

## Rules
- Follow SPEC.md Section 0 ("Instructions to the coding agent") at all times.
- Work one milestone at a time (SPEC.md Section 16). Plan first and wait
  for my approval before writing code.
- Never start the next milestone until I confirm the current one's
  acceptance criteria pass.
- Record every non-obvious design choice in docs/DECISIONS.md.
- Never commit .env or API keys. ANTHROPIC_API_KEY is needed only for M4
  Phase C (live runs); Phases A and B make no real LLM calls.
- Ask before adding dependencies not listed in SPEC.md Section 3.
- Frozen, do not modify: corpus v1 and v2, facts snapshot 2026-10-19-v1,
  retrieval labels, retrieval code/parameters, and accepted milestone
  artifacts. Change the M3 MCP servers only with approval.
- MCP stdio clients start servers with a minimal environment: always pass
  env explicitly (PYTHONPATH, DATABASE_URL, SEC_USER_AGENT, SNAPSHOT_ID,
  RETRIEVAL_CORPUS, RETRIEVAL_MODE, HF_HUB_OFFLINE=1, TRANSFORMERS_OFFLINE=1).
- Model IDs come only from env vars; prices only from the pricing file the
  student fills in. Never print, log or commit secrets.
- Before reporting work done: ruff check, ruff format --check, full pytest.
- Report failures honestly; never rerun until results look good.

## Progress
- [x] M1 Foundation + data
- [x] M2 Parsing, chunking, embeddings, retrieval
- [x] M3 MCP servers
- [x] M4 Agent runtime
- [x] M5 Eval harness + baselines
- [ ] M6 Experiments + CI
- [ ] M7 API, frontend, docs
- [ ] M8 Deploy + publish (optional)

## Notes for the next session

M1, M2 (including corpus v2 and Phase C), M3 and M4 are accepted. M3 was
accepted on 2026-10-22 after Inspector and all five Claude Desktop checks passed;
the student independently confirmed the Apple FY2026 Q3 values in the source 10-Q.
M4 (built in Claude Code; M1-M3 were built with Codex) was accepted on 2026-11-09
after its final acceptance run. M5 was accepted on 2026-11-12 (see docs/M5_STATUS.md).
- NEXT SESSION, FIRST TURN: do not change, run or commit anything. Read CLAUDE.md,
  docs/M5_STATUS.md, evals/results/report.md and docs/DECISIONS.md D104-D110, summarize
  the M5 state, and wait for the student's instructions.
- M5 status: ACCEPTED 2026-11-12. $69.48 spent in total (dev $15.94,
  D105 test steps $40.05, D109 $13.47 of its $30 ceiling). Judge calibration done
  (D110): v2 shuffled sheet (seed 20261112) exact 95%, within 1 100%, κ 0.98 (primary);
  v1 (κ 1.00) kept as contaminated because its order cycled judge scores 2-5. M6 has
  not started. Shuffled neutral sheets are required for any calibration (D110).
  Regenerate the report with `python -m evals.report` and the 7 configs listed in
  docs/M5_STATUS.md. Headline (100 sample): system 99%, B2 (oracle context) 96%, B1
  90%, B0 Fable 69%, Opus 55%, Sonnet 42%. System vs B2 is significant only with 3
  Disney segment-operating-income questions (gold-definition ambiguity, M6 item D110;
  p 0.039 -> 0.22 without). 6/30 handwritten runs gave no answer (D108). Frozen:
  questions_v1 (4f270e35...), subset180 (242fbea0...), B2 meta (902e5a7a...,
  087724b6...). .env BASELINE_MODELS now has index 2 = claude-fable-5-2. No
  prompt/system changes in M5; M6 candidates in D106, D108 and D110. Test-run results
  committed in 7e76e6f; the D110 and acceptance updates are not committed. .gitignore
  exceptions now cover both label files, the v2 map and report_notes.md.
- M1 data: 20 companies, 275 filings, 2,715 facts (563 derived). Ingestion
  cutoff 2026-10-19, inclusive by filing date (America/New_York). Snapshot
  2026-10-19-v1 at data/raw/2026-10-19-v1/ (bodies keyed by URL SHA-256;
  ingestion_snapshots holds the manifest). Reuse this immutable snapshot;
  refresh only under a new snapshot ID.
- Window: three completed fiscal years with available annual reports, plus
  available subsequent quarters. An ended year without a filed annual report
  is not yet a complete annual dataset.
- Known gaps: missing standard-taxonomy metrics remain unavailable, never zero
  or automatically not_applicable. Custom-taxonomy facts are not extracted;
  EPS quarters are unavailable when no direct value exists (never derive EPS).
  Gross profit is not synthesized from revenue and costs. metric_availability
  records period-specific availability and reasons. Bank gross-profit
  not_applicable is a read-only applicability overlay (D042); M1 rows unchanged.
- Fiscal calendars use actual report dates, not XBRL fy/fp or fixed month/day
  arithmetic. Preserve 52/53-week behavior and Costco's 12/12/12/16-week quarters.
  XOM uses reporting CIK 0000034088 following the documented successor mapping.
  Year-end instant facts are stored once as Q4; FY resolves to that same instant.
- M2/corpus v2: the active frozen corpus is
  corpus_3f3c2a9affddcc6a29eca9e768c65bcbd3e2f131fb69595b24b9b92005738739
  (32,960 chunks across 275 filings), the default when RETRIEVAL_CORPUS is unset.
  Four retrieval modes: vector, keyword (OR over lexemes, D031), hybrid (RRF 60),
  hybrid_rerank. 30 labeled questions, 64 gold chunk IDs. Do not change chunk IDs,
  labels, corpora, or stored vectors. See docs/M2_STATUS.md and
  evals/results/retrieval_v2.md.
- M3: edgar-mcp (resolve_company, list_filings, get_financial_metric,
  list_available_metrics, search_filings, get_passage, filing:// resource) and
  quant-mcp (growth_rate, margin, cagr, yoy_series, summary_stats, evaluate) are
  stdio servers on MCP SDK 2.3.0 (MCPServer). They are read-only, return exact
  decimal strings, use Decimal quant math, and default to vector retrieval. Last
  full run: 167 passed, 1 skipped; Ruff clean. See docs/M3_STATUS.md and
  docs/M3_HANDOFF.md (Inspector needs explicit -e env flags; Desktop is MSIX and
  never reads .env).
- M4 agent runtime (accepted; see docs/M4_STATUS.md, docs/M4_ACCEPTANCE.md and
  D051-D082): hand-written provider-neutral loop on anthropic 2.1.0 (API
  2026-10-21, no sampling params), planner -> direct metric lookups + Haiku
  filings workers -> analyst (quant tools) -> two-stage verifier (deterministic
  Stage 1, LLM Stage 2 over all current claims, summary and caveats) with up to
  two revisions. Run `.venv/Scripts/python.exe -m filinglens.cli ask "<question>"
  --max-cost-usd 0.50` and `... -m filinglens.cli replay <run_id>` (prints
  identical/DIVERGED; no LLM, servers or network). Models come only from
  PLANNER_MODEL/WORKER_MODEL/VERIFIER_MODEL, prices only from
  filinglens/llm/pricing.toml; MAX_RUN_TOKENS=200000. Guards: argument locks and
  explicit fiscal-period search filters (the M3 cross-year lesson), duplicate-call
  memo, final-step tool_choice none, untraced quant inputs rejected, 4 passage
  reads per filings worker, revision budget reservation, and budget finalization
  that keeps only verified content. Final run: 6/6 answers, 6/6 replays
  identical, $0.98. Known limitations: Tesla explanatory run uses ~190K of 200K
  tokens; passage-quoted figures cannot feed quant tools (D079 false positive);
  cited facts may come from a later filing's comparative column (M1 rule); the
  analyst still issues dependent calculations one per step. Deferred: D082 (M5
  budget design; M6 quote-traced inputs and thinking display). Adjacent-chunk
  navigation from get_passage remains an M6 candidate; CVX FY2024 Item 7's
  boundary runs slightly late into Item 8 (documented, not fixed).
- Reuse the SEC client's cache, identifying User-Agent, shared rate limit, and
  retries; run one ingestion process at a time.
- Ask before schema changes or dependencies not listed in SPEC.md. YAML support
  remains deferred. Record new non-obvious decisions in DECISIONS.md.
- The repo lives at C:\dev\FilingLens (no spaces). It moved out of OneDrive
  on 2026-10-22; old OneDrive paths in frozen artifacts (e.g.
  evals/results/retrieval_analyses.json) are provenance only, never read as paths.
- Use project-local uv (.tools/uv/bin/uv.exe) and Python 3.12.15
  (.uv/python, used by .venv/Scripts/python.exe); system Python remains 3.14.0.
  On this machine uv needs `--link-mode=copy` (e.g. `uv sync --frozen
  --link-mode=copy`). The CLI uses the Windows selector event loop for Psycopg
  and an IPv4 hint for localhost.
- See docs/DECISIONS.md (D001-D110) for design history. docs/M1_STATUS.md and
  older pending-verification wording predate acceptance; the acceptances
  recorded here supersede them.

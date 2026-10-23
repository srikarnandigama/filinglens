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
- [ ] M4 Agent runtime
- [ ] M5 Eval harness + baselines
- [ ] M6 Experiments + CI
- [ ] M7 API, frontend, docs
- [ ] M8 Deploy + publish (optional)

## Notes for the next session

M1, M2 (including corpus v2 and Phase C), and M3 are accepted. M3 was accepted
on 2026-10-22 after Inspector and all five Claude Desktop checks passed; the
student independently confirmed the Apple FY2026 Q3 values in the source 10-Q.
M4 is being started in Claude Code (prior milestones were built with Codex).
Follow the student's M4 task: design first, then stop for approval.
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
- Open items for M4: the planner must resolve explicit fiscal periods into
  search filters (unfiltered cross-year search can miss the requested filing).
  Adjacent-chunk navigation from get_passage is an M4/M6 candidate only. CVX
  FY2024 Item 7's boundary runs slightly late into Item 8 (documented, not fixed).
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
- See docs/DECISIONS.md (D001-D066) for design history. docs/M1_STATUS.md and
  older pending-verification wording predate acceptance; the acceptances
  recorded here supersede them.

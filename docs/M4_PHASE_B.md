# M4 Phase B — offline implementation report

Status: **Phase B complete; awaiting Phase C configuration.** No real LLM API call was
made. Every agent test uses scripted providers; integration tests use the real
edgar-mcp/quant-mcp stdio servers and PostgreSQL. Phase A decisions D051–D064 are
approved (with the student's amendments); D065 records Phase B implementation details
for review.

## What was built

| Area | Files |
|---|---|
| Provider abstraction | `filinglens/llm/base.py` (normalized messages/tool calls/usage, request fingerprint), `tools.py` ($ref inlining, Anthropic/OpenAI tool formats), `anthropic_provider.py` (API 2026-10-21, no sampling parameters, verbatim content-block replay), `openai_compat_provider.py` (Chat Completions function calling), `pricing.py` + `pricing.toml` (empty) + `pricing.example.toml` |
| MCP client | `filinglens/agents/mcp_client.py` (`McpHub`: explicit server env, legacy stdio sessions, 6+6 tool check, spec hash, timeout/transport mapping, retrieval-mode assertion) |
| Runtime core | `context.py` (run context, live LLM gateway), `toolbox.py` (role tools, argument locks, envelopes, computation IDs), `loop.py` (hand-written loop), `budget.py`, `ledger.py`, `views.py` (compact discovery view), `settings.py` |
| Roles | `planner.py` (snapshot-checked plan validation), `workers.py` (direct and LLM data worker, filings worker, evidence pack), `verifier.py` (D1–D7 deterministic checks, LLM verifier), `orchestrator.py` (scheduling, revisions, live run wrapper), `prompts/*.md` (the five approved prompts verbatim, plus `analyst_no_quant.md`) |
| Tracing/replay | `tracing.py` (sync Psycopg store, recorder), `replay.py` (replay gateway/hub, divergence report) |
| CLI | `filinglens/cli.py` — `python -m filinglens.cli ask "<question>"` and `python -m filinglens.cli replay <run_id>` |
| Schema | `db/migrations/004_agent_runs.sql` (applied locally; `runs`/`trace_events` only) |
| Other | `pyproject.toml`/`uv.lock` (`anthropic==2.1.0`, `openai` 3.36.1), `.env.example`, `tests/test_database.py` (migration count 3→4), `scripts/m4_preservation.py`, `AGENTS.md` (points to CLAUDE.md), DECISIONS D051–D065 |

## Deviations from Phase A (accepted by the student)

1. **Per-call `max_tokens` is fixed at 16,000** rather than `min(role max, remaining
   budget)`, because the remaining budget depends on concurrent scheduling and would make
   replay request fingerprints nondeterministic. The budget is checked before every call,
   so a run can exceed MAX_RUN_TOKENS by at most one LLM call before `BudgetExceeded`.
   While workers run concurrently, each in-flight agent can finish one such call (at most
   four under the default concurrency cap) (D065).
2. **`python -m filinglens.cli` instead of a `filinglens` console command.** The uv
   project is virtual (no build backend), so `[project.scripts]` would not install a
   command. The console script is deferred to M7 packaging; no build backend is added
   (D066).
3. **The compact discovery view is 5.6–7.9 KB per company** (AAPL 5,637; NVDA 5,819; WMT
   6,063; COST 5,671; JPM 7,931 characters), not the 3–4 KB estimated. It is still about
   9× smaller than the raw 50–63 KB. The cost estimate below is updated.
4. **Ruff no longer formats `docs/`.** `ruff format` had reformatted the Python snippets
   inside `docs/M4_PHASE_A.md` (whitespace and line wrapping only). `pyproject.toml` now
   has `extend-exclude = ["docs"]` (D066), and `ruff format --check --force-exclude` on
   `docs/` finds no files. Those Python snippets stay in their reformatted form. All five
   prompt files were re-checked byte-for-byte against the approved Phase A §12 text and
   match: planner, data_worker, filings_worker, analyst, verifier.
   `analyst_no_quant.md` differs from `analyst.md` only in the approved Arithmetic section.

## Results

### Lint, format and tests

| Check | Result |
|---|---|
| `ruff check .` | All checks passed |
| `ruff format --check .` | 113 files already formatted (`docs/` excluded) |
| Full `pytest` with `FILINGLENS_TEST_DB=1` | **207 passed, 2 skipped, 130.83 s** (exit 0) |

Skips:
- `tests/live/test_live_smoke.py`: opt-in live LLM test. It needs `FILINGLENS_LIVE_LLM=1`
  and was deliberately not run.
- `tests/test_chunk_replay.py`: the existing M2 opt-in full-corpus replay, unchanged and
  not enabled, to keep the frozen data untouched.

The first full run had one failure, `tests/test_labeling_retrieval.py::
test_interactive_manual_mark_unmark_show_and_save` (M2 code, unchanged). The error was
`PermissionError: [WinError 5]` while atomically renaming `handwritten.draft.json.tmp`
inside pytest's temp directory under the OneDrive-synced `data/`. This looks like an
OneDrive file lock, not a code fault: `evals/` is unchanged against HEAD, and the test
passed 3/3 when run alone. The clean full rerun above passed with no failures. It may
recur because the repository lives inside OneDrive.

### New tests (41: 29 unit, 11 integration, 1 opt-in live)

| Kind | File | Tests | What it exercises |
|---|---|---:|---|
| Unit | `test_llm_providers.py` | 8 | Tool-schema conversion on the real MCP input models; Anthropic/OpenAI message building, normalization, stop reasons, usage (including cache fields), malformed arguments, error wrapping (429/400/503); no sampling parameters on Anthropic |
| Unit | `test_agent_loop.py` | 8 | Tool→final flow; concurrent parallel calls (barrier); step/token/cost budgets; single corrective retry; `max_tokens`; refusal; role filtering, argument locks, `INVALID_TOOL_ARGUMENTS`; envelope escaping |
| Unit | `test_verifier_checks.py` | 5 | D1–D7 on a synthetic ledger: exact Decimal equality, computation fields, lineage with small constants, status records, `model_arithmetic` handling, summary numbers, final value |
| Unit | `test_agent_units.py` | 8 | Decimal strings and claim/answer rules, structured subtasks, discovery-view completeness, plan validator, TOML pricing, prompt/schema loading, model env resolution, CLI parsing, rendering and preflight messages |
| DB + MCP integration | `test_mcp_client.py` | 3 | Real stdio servers started from a non-project cwd; explicit env (an API-key canary is not passed); 6+6 tools; error mapping; retrieval-mode propagation and assertion; compact view vs raw JPM discovery; role toolboxes |
| DB + MCP integration | `test_orchestrator.py` | 6 | All six question types over the real servers with scripted roles (lookup, trend over the last 8 quarters from discovery, derived Q4, comparison with different fiscal-year ends, explanatory, Meta diff); LLM data worker; revision that fixes or drops claims; `verifier=false`; `use_quant_tools=false`; not-available plan |
| DB + MCP integration | `test_tracing_replay.py` | 2 | Persisted runs/trace_events in an isolated schema; identical offline replay; prompt drift and tampered tool results detected; a `BudgetExceeded` run is persisted and replays identically |
| Live (opt-in, skipped) | `tests/live/test_live_smoke.py` | 1 | One cost-capped real question plus replay (Phase C only) |

The other 168 tests are the pre-existing M1–M3 suite (167 passed plus the opt-in chunk
replay skip, matching M3). The only edit to them is the migration count in
`test_database.py`, which changed from 3 to 4.

**How "no real LLM call" was enforced:**
- Every test that runs agents passes a scripted provider (`ScriptedProvider`/`Script`)
  or a fake SDK client object.
- `run_question` builds real providers only when none are passed, and no test omits them.
  The CLI preflight test fails on purpose before the provider step.
- The replay tests patch `build_providers` and `McpHub.__aenter__` to raise, and block
  name resolution to any non-local host.
- The live smoke test is skipped by default.
- `.env` currently has no `ANTHROPIC_API_KEY` and no model IDs, so a real provider could
  not have been built anyway (checked by key name only; no values read or printed).

### Frozen-artifact preservation (`scripts/m4_preservation.py`)

The "before" snapshot was recorded before any Phase B change. The "after" snapshot was
taken after the full rerun. Result: **`Preserved: 10 tables, 44 files, migrations 001-003`**,
with no differences. See [before](M4_PRESERVATION_BEFORE.json) and
[after](M4_PRESERVATION_AFTER.json).

| Protected | Rows / files (content md5 or sha256 identical) |
|---|---|
| Facts snapshot | `financial_facts` 2,715; `metric_availability` 3,565; `ingestion_snapshots` 1; `companies` 20; `filings` 275 |
| Both corpora (and all corpus rows) | `retrieval_corpora` 4; `corpus_documents` 1,100; `corpus_chunks` 103,003; `sections` 2,832; `chunks` 103,003 |
| Labels | `evals/handwritten.jsonl`, `evals/handwritten_v2.jsonl`, `evals/corpus_v2_migration.json`, retrieval result reports/JSON |
| Retrieval source | `filinglens/retrieval/*.py` (2 files), `filinglens/ingest/*.py`, `data/models/revisions.json` |
| M3 servers | all 10 `mcp_servers/**/*.py` files and `applicability.json` |
| Migrations / fixtures | checksums of 001–003 in `schema_migrations` and on disk; `tests/fixtures/*.json` |

`git diff HEAD` is also empty for `mcp_servers/`, `filinglens/retrieval/`,
`filinglens/ingest/`, `evals/` and migrations 001–003.

### Migration 004

Applied to the local database (`Applied 004_agent_runs.sql`). `schema_migrations` now lists
001–004. The migration contains only `ALTER TABLE runs` (adds `finished_at`, `error`,
`total_cache_read_tokens`, `total_cache_write_tokens` and the `runs_status_check`
constraint) and `ALTER TABLE trace_events` (adds the `trace_events_run_seq_key` unique
constraint). Both tables were empty before and remain empty (0 rows). The preservation
check confirms that no other table changed.

### Updated cost estimate (after the larger discovery view)

The planner sees each company's view once, which adds about 0.5–1.1K input tokens per
company over the Phase A figures. The illustration uses the same Anthropic list prices as
Phase A (cached 2026-10-06, ±50%). The runtime uses only your `pricing.toml`.

| Question | Large in / out | Small in / out | Sonnet 5.5 + Haiku 5.5 | Opus 5.5 + Haiku 5.5 |
|---|---:|---:|---:|---:|
| Lookup | 24K / 5K | – | ~$0.10 | ~$0.20 |
| Trend | 54K / 12K | – | ~$0.23 | ~$0.46 |
| Derived | 26K / 5K | – | ~$0.10 | ~$0.20 |
| Comparison | 52K / 10K | – | ~$0.20 | ~$0.41 |
| Explanatory | 40K / 10K | 47K / 3K | ~$0.19 | ~$0.37 |
| Diff | 55K / 11K | 100K / 6K | ~$0.23 | ~$0.45 |
| **Six questions** | | | **~$1.05 (≤ ~$1.5 with revisions)** | **~$2.1 (≤ ~$3 with revisions)** |

The diff run (~172K tokens) remains at risk of `BudgetExceeded` under
`MAX_RUN_TOKENS=200000`. As approved, it would be stopped, kept and reported.

## Phase C configuration

### 1. `.env` keys (names only)

Set or confirm in `.env` (never commit it):

| Key | Purpose |
|---|---|
| `ANTHROPIC_API_KEY` | Anthropic provider (read only by the runtime; never passed to MCP servers) |
| `PLANNER_MODEL` | Large-model slot: **planner and analyst** (the analyst reads `PLANNER_MODEL`; there is no `ANALYST_MODEL`) |
| `WORKER_MODEL` | Filings worker (and the LLM data worker only if `--data-worker llm`) |
| `VERIFIER_MODEL` | Verifier |
| `MAX_RUN_TOKENS` | Keep `200000` |
| `MAX_RUN_COST_USD` | Optional default dollar cap; `--max-cost-usd` overrides it per run |
| `DATABASE_URL`, `SEC_USER_AGENT`, `SNAPSHOT_ID`, `RETRIEVAL_CORPUS`, `RETRIEVAL_MODE` | Already set for M3; keep `SNAPSHOT_ID=2026-10-19-v1`, the v2 corpus and `RETRIEVAL_MODE=vector` |

Not needed for Phase C: `OPENAI_COMPAT_API_KEY`, `OPENAI_COMPAT_BASE_URL`, `OPEN_MODEL`.

Expected model values match the cost estimate. Use exact IDs from Anthropic's models page:
- `PLANNER_MODEL` and `VERIFIER_MODEL`: one large model, either `claude-opus-5-5` (higher
  quality, ~$2.1 for six questions) or `claude-sonnet-5-5` (~$1.05).
- `WORKER_MODEL`: `claude-haiku-5-5`.

The choice is yours. Whatever you set must match a `pricing.toml` key exactly.

### 2. `filinglens/llm/pricing.toml`

Add one block per distinct configured model ID. The prices come from the official page
<https://platform.claude.com/docs/en/about-claude/pricing>, as decimal strings in USD per
million tokens. Leave the cache fields empty, because caching is off in M4. For example,
if you choose Opus 5.5 + Haiku 5.5, add these two blocks (fill in the values):

```toml
[models."claude-opus-5-5"]
provider = "anthropic"
input_per_mtok = ""     # e.g. "4.00" — copy from the pricing page
output_per_mtok = ""
cache_read_per_mtok = ""
cache_write_per_mtok = ""
source = "https://platform.claude.com/docs/en/about-claude/pricing"
checked = 2026-10-22

[models."claude-haiku-5-5"]
provider = "anthropic"
input_per_mtok = ""
output_per_mtok = ""
cache_read_per_mtok = ""
cache_write_per_mtok = ""
source = "https://platform.claude.com/docs/en/about-claude/pricing"
checked = 2026-10-22
```

Preflight runs before any server starts, any run row is written or any LLM call is made.
It prints one line to stderr and exits with code 1:
- `preflight failed: pricing.toml has no prices for: <model ids>`: a configured model has
  no block.
- `preflight failed: pricing.toml: <model> needs input_per_mtok.`: a block has an empty or
  non-decimal required price.
- `preflight failed: Set PLANNER_MODEL in .env (model IDs come only from env vars).`
- `preflight failed: Set ANTHROPIC_API_KEY in .env for live runs.`

### 3. First single-question run (Phase C step 1; I run it after you confirm)

PowerShell, from the project root, with the database container up (`docker compose up -d db`):

```powershell
.venv/Scripts/python.exe -m filinglens.cli ask "What was Apple's total revenue in fiscal Q2 2025?" --max-cost-usd 0.50
```

The output gives the status, summary, claims with resolved citations, caveats, the
verifier outcome, `run_id`, tokens, `cost_usd` and `latency_ms`. Add `--json` for
machine-readable output. Server stderr logs are written to `data/runs/<run_id>/`.
Expect about 8.5 s of cold vector-model load on the first search.

View the run and its trace (replace `<run_id>`):

```powershell
docker compose exec -T db psql -U filinglens -d filinglens -c "SELECT status, total_input_tokens, total_output_tokens, cost_usd, latency_ms, error FROM runs WHERE id='<run_id>'"
docker compose exec -T db psql -U filinglens -d filinglens -c "SELECT seq, agent, event_type, input_tokens, output_tokens, latency_ms FROM trace_events WHERE run_id='<run_id>' ORDER BY seq"
```

Replay it offline. Replay makes no LLM call, starts no server and makes no network
request. It prints the report, then `identical` (exit 0) or `DIVERGED` (exit 2):

```powershell
.venv/Scripts/python.exe -m filinglens.cli replay <run_id>
```

**Stop: no real LLM call has been made, and none will be until you confirm configuration.**

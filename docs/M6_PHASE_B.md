# M6 Phase B — offline implementation

Status: **Phase B complete, offline. No LLM call was made and nothing was committed or pushed.**
Phase A was approved on 2026-11-12 (decisions D111-D124 in DECISIONS.md). Phase C (dev
validation, the first API spend) waits for the student's go-ahead and for two open items
below.

## Open items before Phase C

1. **D117 summary rule: your decision.** The dev-only offline result is in §4. The flag is
   implemented and tested but set in no config.
2. **Explanatory dev prompts.** Item 4 of the approval message still had its template text
   ("[approved as written / approved with these edits: ...]"). `evals/explanatory_dev_v1.jsonl`
   holds xd01-xd10 exactly as proposed in Phase A and is hash-pinned. If you meant to send edits,
   the file and its hash (`evals/m6.py`) are cheap to redo before Phase C.

## 1. What changed

### Runtime (every change behind a RunConfig flag whose default is M5 behavior; D118)

| Flag | Decision | Where |
|---|---|---|
| `budget_weighting = "input_price"` | D113: tokens × input price of the call's model ÷ the planner model's; Sonnet calls count exactly as before | `agents/budget.py`, `orchestrator.run_budget` |
| `finalize_without_draft` | D114: a budget stop before any draft → explicit not_available Answer, `handled: stopped_without_draft`, still "no answer" in evals | `orchestrator.orchestrate`/`_first_draft`, `evals/system_adapter.py` |
| `stall_guard_steps = 2` | D115: 2 consecutive no-progress tool steps → D068 final step; retry re-enables tools | `agents/loop.py`, `toolbox.last_progress` |
| `empty_reply_guard` | D115: an empty reply gets the final-step guard once, without spending the corrective retry | `agents/loop.py` |
| `unknown_tool_hint` | D115: "There is no tool named …; reply with the JSON as plain text" for nonexistent tools only | `agents/toolbox.py` |
| `prompt_caching` | D116: system-block breakpoint plus automatic caching for planner, analyst, filings and data workers (not the verifier); `LLMRequest.cache` excluded from fingerprints when off | `llm/base.py`, `llm/anthropic_provider.py`, `agents/context.LoopGuards` |
| `summary_cited_values` | D117 (pending): summary numbers may be rounded displays of cited values | `agents/verifier.py` |

- **Unchanged:** no prompt file and no MCP server changed. The OpenAI-compatible provider accepts
  and ignores `cache`.
- **Replay:** it rebuilds the budget and guards from the recorded flags.

### Evals

- **`evals/m6.py`.** The frozen 50-question test sample (`questions_v1.m6_sample50.json`, ID-list
  SHA-256 `54a3c724…`: 7 per template from the 100-question sample, plus the Costco miss; it
  refuses to overwrite). It also holds the C1 dev draw (5 per template from the dev pilot) and the
  explanatory dev loader, which is hash-checked on LF-normalized text (`8f25776f…`) so that any
  checkout verifies.
- **Runner.**
  - The `explanatory_dev` split is answered as free text and never numerically scored.
  - `sample = "m6_sample_50"` selects the frozen 50-question sample.
  - Preflight refuses a caching config whose models lack cache prices.
- **Configs** (`budget = "m6"`, concurrency 2, M6 flags listed explicitly):

  | Step | Config | Cap |
  |---|---|---:|
  | C1 | `m6_dev_numeric` | $6.50 |
  | C2 | `m6_dev_explanatory_m5` (the M5 system, M5 cache key) | $3.00 |
  | C3 | `m6_dev_explanatory` | $3.25 |
  | D1 | `m6_handwritten` | $6.00 |
  | D2 | `m6_test_sample` | $5.50 |
  | D3 | `m6_test_no_verifier` | $4.00 |
  | D4 | `m6_test_no_quant` | $4.25 |
  | D5 | `m6_handwritten_rerank` | $6.00 |
  | D6 | `m6_judges` (judge plan) | $1.50 |
  | | **Total** | **$40.00** |

  The conditional D7, `m6_handwritten_hybrid` ($6.25), carries `budget = "m6-conditional"`.
- **Judge.** `python -m evals.judge run --plan evals/configs/m6_judges.toml` judges every system
  in the plan's configs under the plan's cap. M5 judging and its item keys are unchanged.
- **Failure analysis.** `python -m evals.failures <configs> --out …` applies D112's deterministic
  rules (read-only traces). On the M5 runs it reproduces the Phase A counts, for example planner
  stalls 10 dev / 16 test / 1 handwritten, empty replies 28 / 45 / 1, and no-answers 6
  handwritten.
- **Smoke.** `python -m evals.smoke evals/configs/ci_smoke.toml`, plus the config itself: 10
  questions of the 50-question sample, M5 system records until Phase D, `min_accuracy = "1.0"`.
- **Summary-rule check.** `python -m evals.summary_rule_check --out
  evals/results/m6_summary_rule_dev.json` (dev pilot only; it raises on any non-dev record).
- **Report.** `build_report()` is factored out of `main` (same output). Explanatory dev records are
  collected but never scored. The new M6 report sections (failure analysis, before/after,
  ablations) are written in Phase D, when there are M6 records to render.

### CI

`.github/workflows/ci.yml`:
- Setup: ubuntu-latest, uv 0.13.1, Python 3.12.15, `uv sync --frozen` without `torch`, `triton`,
  `cuda-*` or `nvidia-*` (20 packages).
- Steps: ruff check, ruff format --check, `pytest -q -rs`, then the smoke test.
- Environment: no secrets. The model IDs (public, needed for the cache key) and a placeholder
  `SEC_USER_AGENT` are workflow env vars.

### Tests

- **New: `tests/test_m6_runtime.py`** (19 tests):
  - weighted and unweighted budgets;
  - a run whose small-model worker exceeds the raw budget reaches a draft only with weighting;
  - A2's explicit answer and replay;
  - every stall-guard scenario (errors, identical results under different arguments, duplicates,
    progress reset, retry after a forced final);
  - empty replies with and without the guard;
  - the unknown-tool hint vs the role message;
  - cache roles, breakpoints and fingerprints, and cache pricing;
  - 4 summary-rule cases;
  - a full run with every M6 flag and a stalled planner that replays identically.
- **New: `tests/test_m6_evals.py`** (13 tests):
  - pinned M5 cache keys (system, B0 ×3, B1, B2);
  - M6 keys differ, except C2, which is the M5 system;
  - frozen-file hashes;
  - the 50-question sample and the explanatory dev set (frozen, reproducible, no overlap);
  - the C1 dev draw;
  - caps = $40.00 and reservations covered;
  - the cache-price preflight;
  - the smoke pass and a miss;
  - failure rules on synthetic traces;
  - M5 report.md regenerating byte for byte.
- **Three existing tests changed (test-only; the dry run found them):**
  - The fingerprint test excludes the new `cache` field when rebuilding the legacy request.
  - The M5 caps test globs only `m5_*` configs; M6 caps have their own test.
  - The CLI preflight test clears the model env vars it assumes unset; CI sets them.

## 2. Test results

| Check | Result |
|---|---|
| `ruff check .`, `ruff format --check .` | clean (135 files) |
| Full pytest, `FILINGLENS_TEST_DB=1` (local PostgreSQL, real MCP servers) | **307 passed, 2 skipped** in 216 s. Skipped: live LLM smoke (`FILINGLENS_LIVE_LLM`) and full-corpus chunk replay (`FILINGLENS_TEST_CORPUS_REPLAY`), the same two as at M4/M5 |
| M5 runs replayed under the new code with default flags (`filinglens.cli replay`, DB, no LLM) | **20/20 identical**: Costco budget finalization, the Exxon/Pioneer and Exxon GHG no-answers, 3 dev revision runs, 2 planner-stall runs, 2 empty-reply/invalid-tool runs, a revision-skipped run, a handwritten answer, a probe and 7 seeded others |
| M5 report regenerated from the 7 M5 configs | byte-identical to `evals/results/report.md` (also a test) |
| Smoke test (local) | 10/10, threshold 1.0, pass |

### Clean-checkout CI dry run

- **Setup.** A copy of exactly the files a fresh clone would contain (tracked plus new, unignored;
  no `data/`, no `.env`). Its venv was built with the workflow's exclusions (torch absent,
  sentence-transformers present). The workflow's environment variables were set and
  `FILINGLENS_TEST_DB`, `DATABASE_URL` and `ANTHROPIC_API_KEY` were unset.
- **First run: 3 failures**, the three tests listed under §1 Tests. After the fixes:
  - ruff check and format: clean;
  - pytest: **237 passed, 72 skipped**;
  - smoke: 10/10, pass.
- **Remaining check:** CI on GitHub's Linux runner is confirmed in Phase D.

**Tests skipped in CI (72), by their existing gates:**

| Gate | Module | Skipped |
|---|---|---:|
| `FILINGLENS_TEST_DB=1` unset (PostgreSQL, real MCP servers) | test_mcp_edgar | 23 |
| | test_orchestrator | 7 |
| | test_database | 4 |
| | test_mcp_client | 3 |
| | test_retrieval_database | 2 |
| | test_tracing_replay | 2 |
| | test_chunk_rebuild, test_corpus_v2_database, test_embedding_resume, test_eval_generate, test_eval_runner | 1 each |
| Raw SEC snapshot (`data/raw`) absent | test_corpus_v2 | 21 |
| Pinned model tokenizers (`data/models`) absent | test_parsing_chunking | 3 |
| `FILINGLENS_TEST_CORPUS_REPLAY` unset | test_chunk_replay | 1 |
| `FILINGLENS_LIVE_LLM` unset | live/test_live_smoke | 1 |

## 3. Frozen artifacts

**No change to any frozen artifact:**
- questions_v1, its manifest, subset180 and the draft;
- M2 labels (`handwritten.jsonl`), handwritten_v2 and both B2 metadata files;
- `evals/results` (report.md, report_notes.md, retrieval results, calibration labels);
- prompt files, `mcp_servers/` and `db/`.

**Checks:**
- `git status` shows no tracked change in those paths.
- Hash tests: SHA-256 of LF-normalized text for questions_v1 `4f270e35…`, handwritten_v2
  `d71d60aa…`, B2 metadata `902e5a7a…` and `087724b6…`; manifest and subset180 checks pass.
- All **1,286 M5 cache files are unmodified and no cache file was added** (`git diff --quiet HEAD
  -- evals/cache`; no untracked files under `evals/cache`).
- The database still holds 344 runs and 2,715 snapshot facts; nothing was written outside the
  tests' isolated schemas.
- The only intended new or changed eval data files:
  - `evals/explanatory_dev_v1.jsonl` and `evals/questions_v1.m6_sample50.json` (new, frozen);
  - `evals/results/m6_summary_rule_dev.json` (new evidence; `.gitignore` exception added).

**`filinglens/llm/pricing.toml`** shows as modified because of your cache prices. Its `checked`
dates still read 2026-10-22; you may want to update them. Note that Sonnet's read price ($0.10)
is 0.05× input, so caching should save somewhat more than the Phase A estimate, which assumed
0.1×.

## 4. Summary rule (D117): offline result on DEV pilot drafts only

`python -m evals.summary_rule_check` rebuilds each dev-pilot run's first analyst draft and its
evidence ledger from the trace, then reruns Stage 1 with the rule off and on. No test draft is
read; the script raises on any non-dev record.

| | Count |
|---|---:|
| Dev-pilot runs / drafts rebuilt | 100 / 100 |
| First-round summary failures, rule off (equals the 17 recorded in M5: the rebuild is faithful) | 17 |
| Cleared with the rule on | **16** |
| Partly cleared | 1 (`q_3f343d61…`: "6.50" accepted; "22.343" and "28.844" still fail; they are the full-year and nine-month derivation inputs, which no claim cites, so rejecting them is correct) |
| Newly accepted numbers | 26 |
| False acceptances found | **0** |

**Review method.** I reviewed all 26 newly accepted numbers. Each is the rounded figure of the
cited quantity it describes in the summary, for example "about $5.48 billion" ↔ cited fact
5484000000, "Q1 $67.31 billion" ↔ 67307000000, and "sum is $35.56 billion" ↔ the cited
computation output 35562000000. The full list, with each matched value and its summary text, is
in `evals/results/m6_summary_rule_dev.json`.

**Against your criterion (≥ half cleared, no new false acceptances):** 16/17 cleared, 0 false
acceptances. The decision is yours. If you keep the rule, `summary_cited_values = true` is added
to every M6 config, which changes their cache keys (nothing has run yet).

## 5. Metric definition (D119)

`operating_income` is the company's `OperatingIncomeLoss` fact as tagged. For Disney, whose income
statement has no operating-income line, that tag is total segment operating income from its
segment disclosure. Questions and gold are unchanged and there is no v2 question set. Every M6
table with numeric questions reports results with and without the Disney segment-OI questions.

## 6. Next (Phase C, after your approval)

1. Fill in the D117 decision (and any prompt edits).
2. Run `--preflight` on C1-C3. It checks keys, prices including cache prices, and model access.
3. Run C1, C2 and C3 under their caps. Projections at M5 rates: $5.36, $1.79 and $1.90.
4. Report:
   - dev mechanics against the M5 system;
   - the failure categorization update;
   - measured costs, and how much of the change comes from caching;
   - the Phase D re-projection.

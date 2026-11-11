# M5 Phase A — eval harness and baselines: design

Status: **design for approval. No code, no LLM calls.** Proposed decisions D083–D096 are
at the end. The open choices for the student are collected in §12.

## 0. Current state (2026-11-09)

- **Data (M1, frozen):** snapshot `2026-10-19-v1`; 20 companies, 275 filings, 2,715 facts
  (563 derived). Facts are latest-filed within the snapshot (D008), Q4 is often derived
  as FY − 9M (D009), and EPS is never derived.
- **Corpus v2 (M2, frozen):** 32,960 chunks; Items 1/1A/7/7A/8 of 10-Ks and P1-2 (MD&A)
  and P2-1A of 10-Qs. **There are no 10-Q financial statements in the corpus.**
- **M2 retrieval eval (frozen):** 30 student-labeled questions, 64 gold chunks
  (`evals/handwritten_v2.jsonl`), capped recall@5/10 and MRR@30 per mode (D022/D027/D036);
  results in `evals/results/retrieval_v2.{json,md}`.
- **M3/M4 (accepted):** MCP servers and the agent runtime. The final M4 acceptance run
  answered 6/6 questions, replayed 6/6 identically and cost $0.98. Configuration: Sonnet 5.5
  planner/analyst/verifier, Haiku 5.5 workers, `MAX_RUN_TOKENS=200000`. D051–D082 are
  frozen as the "system" for M5.
- **`evals/` today:** only the M2 retrieval tooling. There is no generator, runner, scorer,
  baseline or report code yet, and no `configs/`.
- **Pricing (`pricing.toml`):** Sonnet 5.5 and Haiku 5.5 only, with no cache prices.
  Baseline models other than Sonnet need entries added by the student.

**Facts measured for this design (read-only):**

| Measure | Value |
|---|---|
| Candidate pools | lookup 2,152 direct facts; margin 531 quarter combinations; trend_avg 348 quarterly sets; derived_q4 345; multi_step 335; yoy_growth 280; 120 annual margins for comparison pairs |
| Coverage gaps | Gross profit for only 7 companies (AAPL, JNJ, KO, MSFT, NKE, NVDA, TSLA); operating income for 13; JPM has no quarterly revenue |
| Restatements (latest-filed ≠ value in the period's own first filing, from the frozen companyfacts JSON) | 44 of 2,152 direct facts (2.0%), e.g. NVDA EPS (stock split 2.48 → 0.25), TSLA FY2024 Q1 net income (1,129M → 1,390M), META capex |
| Facts first filed after 2026-06-30 | 143 (6.6%); first filed in June 2026: 7 |
| 10-K text size (raw snapshot, ~4 chars/token) | p50 106K tokens, p90 293K, max 367K |
| 10-Q text size | p50 45K, p90 154K, max 243K |
| Corpus Item 8 (10-K) | p50 34K, p90 85K, max 165K (JPM) |

**Official docs checked (2026-11-09):**
- **Training cutoffs** (models overview): Claude Opus 5.5, Sonnet 5.5 and Haiku 5.5, and
  the new **Claude Fable 5.2**, all list a reliable knowledge cutoff and training data
  cutoff of **Jun 2026**.
- **Fable versions:** Fable 5.2 (`claude-fable-5-2`, $8/$40) is the current top model;
  Fable 5.1 is legacy ($10/$50).
- **Pricing:** web search costs **$10 per 1,000 searches** plus result tokens as input.
  Code execution is free alongside `web_search_20260209`, so dynamic filtering adds only
  tokens. The Batch API is 50% off.
- **Prompt caching:** writes cost 1.25× (5-minute TTL) or 2× (1-hour TTL); reads 0.05×
  on Sonnet and Opus 5.5 ($0.10 and $0.20/MTok) and 0.1× on Haiku. The minimum cacheable
  prefix is 512 tokens.
- **Haiku 5.5 price tier:** prompts over 100K tokens cost $0.50/$2.50.
- **OpenAI-compatible endpoint:** not used in M5; open-model swaps are M6 (§13.5).

## 1. Question generation (`evals/generate.py`)

Every question is generated from `financial_facts` (snapshot `2026-10-19-v1`) with
**Decimal arithmetic in Python**: precision 80, ROUND_HALF_EVEN, exactly as quant-mcp does
(D040). The exact gold is stored as a fixed-point string; no LLM is involved.

### 1.1 Templates, wording and gold

Fiscal years are named by the calendar year in which they end (D006): "fiscal 2025".
Quarters are written "fiscal Q2 2025". The wording is fixed per template; only the slots
vary.

| Template | Wording | Metric/period selection | Gold (Decimal) | Unit | Tolerance |
|---|---|---|---|---|---|
| `lookup` | "What was {Company}'s {metric phrase} in fiscal {Qn} {FY}?" (or "in fiscal {FY}" for annual; for instants: "at the end of fiscal {Qn} {FY}") | Direct (non-derived) facts: revenue, net income, operating income, gross profit, R&D, operating cash flow, capex, diluted EPS, total assets, cash | fact value | USD, or USD/share for EPS | 0.5% relative (EPS: max of 0.5% relative and $0.005 absolute) |
| `yoy_growth` | "By what percent did {Company}'s {metric phrase} change from fiscal {FY-1} to fiscal {FY}?" | Annual flow metrics plus EPS; base must be > 0 | (new − old) / old × 100 | percent (signed) | 0.1 pp absolute |
| `margin` | "What was {Company}'s {gross/operating/net} margin in fiscal {Qn} {FY}?" | Quarters where numerator and revenue both exist; revenue > 0; Q4 allowed even if derived (flag recorded) | numerator / revenue × 100 | percent | 0.1 pp |
| `trend_avg` | "What was {Company}'s average quarterly {metric phrase} over fiscal {FY}?" | Flow metrics (not EPS, not instants) with all four quarters | (Q1+Q2+Q3+Q4) / 4 | USD | 0.5% relative |
| `derived_q4` | "What was {Company}'s {metric phrase} in fiscal Q4 {FY}?" | Only facts with `derived = TRUE` (Q4, flow metrics) | fact value (= FY − 9M) | USD | 0.5% relative |
| `comparison` | "Which had the higher {gross/operating/net} margin in fiscal {FY}, {A} or {B}, and by how many percentage points?" | Annual margins of two companies with the same fiscal-year number (each company's own year); skip pairs with \|diff\| < 0.2 pp as too close to call | choice = higher company; value = \|mA − mB\| | percentage_points | choice must match and 0.1 pp |
| `multi_step` | "By what percent did {Company}'s {metric phrase} change from fiscal Q1 {FY} to fiscal Q4 {FY}?" | Q1 direct and Q4 derived, same metric/FY, Q1 > 0 | (Q4 − Q1) / Q1 × 100 using the derived Q4 | percent (signed) | 0.1 pp |

**Selection rules:**
- **Metric phrases:** a fixed mapping, e.g. revenue → "total revenue", net_income →
  "net income", eps_diluted → "diluted earnings per share", capex → "capital
  expenditures".
- **Skipped (never asked):**
  - any period whose `metric_availability` status is `unavailable` or `not_applicable`;
  - banks' gross profit (JPM/BAC, D042) and any margin with a missing numerator;
  - any period with a non-positive growth base;
  - EPS in averages, derived questions or margins;
  - instants (total assets, cash) outside `lookup`.
- **Gross margin:** only the 7 companies that report gross profit.
- **Gold provenance:** every gold records `gold_fact_ids` (every fact read), the
  `computation` (formula and exact inputs), and, for derived facts, their
  `derivation_inputs`.

### 1.2 Size, balance, split

- **Target: 400 questions**: lookup 60, yoy_growth 60, margin 60, trend_avg 55,
  derived_q4 55, comparison 55, multi_step 55. All pools are 2–5× larger than needed.
- **Balancing:** within each template, a deterministic greedy pass over a seeded shuffle
  (seed `20261109`). It picks the candidate whose company has the fewest picks so far,
  breaking ties by metric count, then by period, so companies and metrics spread evenly
  where data exists. Companies with less data (JPM, BAC) are simply capped by
  availability.
- **Post-cutoff floor (choice for the student, §12):** facts first filed after the model
  cutoff are only ~7% of the data. I recommend a floor where **at least 20% of each
  template** comes from periods first filed after 2026-06-30, when the pool allows. This
  makes the "after cutoff" breakdown reportable; it is documented and does not change
  gold. Without the floor, about 25 test questions would fall after the cutoff.
- **Restated:** not oversampled; the expected ~8 questions are reported descriptively
  (§6).
- **Split:** 30% dev / 70% test, stratified by template. Within each template the
  selected questions are ordered by SHA-256(seed ‖ id), and the first round(0.3 · n) are
  dev. That gives about 120 dev and 280 test questions.
- **Rule:** all prompt and design tuning uses dev only; final numbers are test only
  (D084).

### 1.3 Record format and freezing

`evals/questions_v1.jsonl`, one JSON object per line, sorted by id:

```json
{"id": "q_<sha256 of template|tickers|metric|periods>[:16]", "template": "margin",
 "question": "...", "gold_value": "42.123456789012", "gold_unit": "percent",
 "gold_choice": null, "tolerance": {"kind": "absolute_pp", "value": "0.1"},
 "companies": ["AAPL"], "periods": [{"fiscal_year": 2025, "fiscal_period": "Q2"}],
 "metric": "gross_profit", "gold_fact_ids": ["12", "40"],
 "computation": {"formula": "gross_profit / revenue * 100", "inputs": {...}},
 "source_urls": ["https://www.sec.gov/Archives/..."],
 "fairness": {"period_end_max": "2025-03-29", "first_filed_max": "2025-05-02",
              "cutoff_bucket": {"claude-sonnet-5-5": "before", "...": "..."},
              "restated": false, "restated_detail": null, "derived_q4": false},
 "split": "test", "snapshot_id": "2026-10-19-v1", "generator_version": "gen-v1"}
```

- **Freezing:** after the student approves the Phase B sample, `questions_v1.manifest.json`
  records the file's SHA-256, the counts, the seed, the generator version and the
  snapshot.
- **Hash checks:** a test (and the runner at start-up) checks the hash, as for the M2
  labels.
- **No in-place regeneration:** the generator refuses to overwrite a frozen file. A
  changed set must be a new version (`questions_v2`).

**Handwritten set:** `evals/handwritten_v2.jsonl` (30 questions, frozen v2 labels) is
reused unchanged, for system-level retrieval_recall@k and the LLM judge (§5).

## 2. Fairness metadata

**(a) Before or after the training cutoff.** Public availability depends on filing, not
period end, so the bucket is based on `first_filed_max`: the latest *original* filing
date among everything the gold depends on, taken from the frozen companyfacts JSON. For
derived values, the dates of their inputs count.

| Bucket | Rule (cutoff "Jun 2026", month granularity) |
|---|---|
| `before` | first_filed_max ≤ 2026-05-31 |
| `june` | filed during June 2026 (ambiguous; reported separately, ~0.3% of facts) |
| `after` | ≥ 2026-07-01 |

`period_end_max` is also stored, so a period-end-based breakdown remains possible. The
bucket is stored per model (all candidates currently share "Jun 2026", from the official
models overview); a new model gets its own entry from its docs.

**(b) Restated.** `restated = true` when the gold differs from the same gold recomputed
from each input's earliest-filed observation (the period's own filing). For derived Q4,
that means the original FY − 9M. `restated_detail` keeps both values and accessions.
Baselines quoting the as-first-reported number are then distinguishable from simply
wrong ones.

**(c) Derived.** `derived_q4 = true` when any gold input is a derived fact. This covers
all derived_q4 and multi_step questions, plus margins and averages that use a derived Q4.

## 3. Baselines (`evals/baselines.py`)

**Common settings:**
- One request per question, on the official SDK and API version 2026-10-21.
- No sampling parameters (D064); thinking is left at each model's documented default
  (adaptive) and **default effort**, the same as the system. Recorded per run.
- `max_tokens` 16,000.
- Refusals and `max_tokens` stops are recorded and scored as incorrect.

### 3.1 Shared prompt and answer format

System prompt, identical for B0, B1 and B2 except for the one sentence noted below:

> You answer questions about US public companies' financial results as reported in their
> SEC 10-K and 10-Q filings. A fiscal year is named for the calendar year in which it
> ends; quarters are the company's fiscal quarters. Use the values as most recently
> reported (including any restatement). Report money in US dollars, per-share amounts in
> dollars per share, growth and margins in percent (negative for a decline), and
> differences between percentages in percentage points. If you are not certain, give
> your best estimate. Only if the value does not exist for this company and period (for
> example a bank's gross profit), answer "not_applicable"; if you believe it was not
> reported, answer "not_available".
> End your reply with one line of JSON only:
> `{"value": <number or null>, "unit": "<USD | USD millions | USD billions | USD/share | percent | percentage_points>", "choice": "<ticker, comparison questions only, else null>", "status": "<answered | not_available | not_applicable>"}`

B1 adds "You may search the web." B2 adds "Use only the filing excerpts provided below,
which are from the frozen SEC filings."

User message: the question. B2 inserts the context (§3.4) before it.

**Parsing (identical for every system):**
- The last JSON object in the text that has a `value` key is the answer.
- `value` may be a number or a numeric string with commas removed.
- A missing or unparseable JSON, or `status = answered` with a null value, is a
  **parse failure**: incorrect, and counted separately.

**System mapping:**
- `Answer.final_value`, `final_unit` (USD, USD/shares, percent, percentage_points) and
  `status` map directly.
- **Comparison `choice`:** taken from the system's two percent claims that carry tickers:
  the higher claimed margin wins. If that cannot be resolved, it is a parse failure. This
  is a documented asymmetry, because the M4 Answer schema has no `choice` field and
  changing the schema would be a runtime change.

### 3.2 B0 — closed-book

The shared prompt and the question, with no tools.

### 3.3 B1 — web search

- **Tool:** the server-side `web_search_20260209` with `max_uses: 5`, no domain
  restrictions (open web, so SEC EDGAR and press releases are allowed).
- **Pause handling:** if the response stops with `pause_turn`, the runner resends the
  conversation, up to 3 continuations.
- **Billing:** $10 per 1,000 searches, failed searches free, plus result tokens as input.
  Dynamic-filtering code execution is free with this tool. The runner reads the response's reported web-search request count (the exact usage
  field is confirmed against the installed SDK 2.1.0 types in Phase B) and adds
  `searches × $0.01` to `cost_usd`.
  Search prices go into `pricing.toml` under a new `[tools.web_search]` table.
- **Requirement:** B1 needs web search enabled for the organization (an admin setting).
  This is checked in Phase C preflight.

### 3.4 B2 — stuffed context

**What is stuffed.** The filings that contain the gold:
- the `source_accession` of every gold fact (the latest-filed filing, which is where the
  gold value appears, often as a comparative column);
- for derived facts, the accessions of their derivation inputs (10-K for FY, 10-Q for
  9M).

That is typically 1 filing (lookup, margin, yoy_growth, comparison per company) and up
to 3–4 (trend_avg, derived_q4, multi_step).

**Source: the frozen raw snapshot, not the corpus.** The corpus has no 10-Q financial
statements, and its Item 8 sections can be huge (JPM ~165K tokens). From each filing's
raw HTML (parsed with the existing `selectolax` dependency, as plain text with table
rows kept on one line), take the **financial statements window**:
- start at the first heading matching the income statement ("CONSOLIDATED STATEMENTS OF
  OPERATIONS / INCOME / EARNINGS", "CONDENSED CONSOLIDATED STATEMENTS OF …");
- continue through the balance sheet and cash-flow statements, up to the start of the
  notes ("NOTES TO …"), capped at **25K tokens per filing**;
- if no heading is found, take the first 25K tokens of the filing's Item 8 / Part I
  Item 1 text, and record that the fallback was used.

**Cap and overflow.** At most **80K tokens per question**. Phase B estimates this as
chars/4, since the SDK's token-counting endpoint makes no generation call but needs the
API key, and Phase B makes no API calls. The real input tokens are recorded per call in
Phase C. If the filings exceed it, the least recent filing's window is
truncated first, and the question records `context_truncated = true`.

**Fairness.** B2 is the "just give it the document" baseline. Two things are recorded
offline in Phase B:
- `gold_visible`: whether every gold input value appears in the stuffed text in the
  filing's printed scale (for example "95,359" for 95,359,000,000 in millions);
- `context_truncated`.

B2 accuracy is then reported overall and **restricted to `gold_visible` questions**. This
separates "the model could not compute or derive" from "the number was not in the
context". B2 sees only the statements, not MD&A; for numeric templates that is where
the numbers are.

### 3.5 Models and cost

All estimates are per question, from the official prices.

| Baseline | Assumed tokens (in / out incl. thinking) | Sonnet 5.5 ($2/$10) | Opus 5.5 ($4/$20) | Fable 5.2 ($8/$40) |
|---|---|---:|---:|---:|
| B0 closed-book | 0.6K / 1.5K | ~$0.016 | ~$0.032 | ~$0.065 |
| B1 web search (≤5 searches) | 40K / 2K + 3 searches | ~$0.13 | ~$0.23 | ~$0.43 |
| B2 stuffed (≤80K) | 40K / 1.5K | ~$0.10 | ~$0.19 | ~$0.38 |

The output and search counts are assumptions; the Phase C dev pilot measures them. Fable
5.1 (legacy, $10/$50) costs about 25% more than Fable 5.2 for the same work, so I
suggest 5.2 if Fable is wanted at all. Account access for either is checked in Phase C
preflight with `models.retrieve`, a metadata call that generates nothing.

**Recommended default:**
- **B0:** Sonnet 5.5 (the system's own model, so the comparison isolates the
  architecture) and Opus 5.5 (a bigger single model).
- **B1 and B2:** Sonnet 5.5.
- **Fable 5.2 B0:** optional.

The student chooses (§12).

## 4. Runner (`evals/runner.py`)

**Config format: TOML.** It uses stdlib `tomllib`, as `pricing.toml` does (D060), since
YAML is deferred. This replaces SPEC §13.3's YAML. Example
`evals/configs/m5_dev_pilot.toml`:

```toml
name = "m5-dev-pilot"
questions = "evals/questions_v1.jsonl"   # hash-checked against the manifest
split = "dev"
sample = 100                             # stratified by template, seed below; or "all"
seed = 20261109
concurrency = 4                          # EVAL_CONCURRENCY
spend_cap_usd = "20.00"                  # hard cap per invocation

[[systems]]
id = "system"
kind = "system"                          # FilingLens runtime, accepted M4 flags
max_cost_usd = "0.50"

[[systems]]
id = "b0-sonnet"
kind = "b0"
model_env = "PLANNER_MODEL"              # model IDs only via env vars
```

**Execution:**
- **Concurrency:** a semaphore (default 4) across questions; each system run gets its
  own `RunBudget`.
- **Retries:** the SDK's retries (4) plus runner backoff (2 → 4 → 8 s, max 3) on
  retryable `ProviderError`s, i.e. 429, 5xx and connection errors. A non-retryable error
  is recorded as `error`.
- **Ordering:** questions are scheduled in a seeded order, so a capped or interrupted run
  covers a stratified prefix.

**Response cache** (`evals/cache/<system_config_hash>/<question_id>.json`). It is the
resumability checkpoint, and is written atomically with a temp file and rename.

| Key part | Contents |
|---|---|
| `system_config_hash` | SHA-256 of the canonical JSON of: system kind; resolved model IDs; prompt hashes (system prompts, or baseline prompt text); tool-spec hash; flags (verifier, retrieval mode, quant, data worker, max_steps, max tokens, budgets); B1/B2 settings (max_uses, context cap, extractor version); snapshot and corpus IDs; runner version. **Pricing is not part of the key**, because it does not change outputs; costs are recomputed from stored usage. |
| `question_id` | plus the question-text SHA-256, checked on read (a mismatch is a miss) |

**Per-question record:**
- `question_id`, `system_id`, `system_config_hash`;
- `prediction` {value, unit, choice, status}, `raw_output` (the full text, or for the
  system the Answer JSON), `parse_ok`;
- `usage` {input, output, cache_read, cache_write, web_searches}, `cost_usd`,
  `latency_ms`;
- `run_id` (the system's `runs` row; trace in `trace_events`), `error`, `stop_reason`,
  `attempts`, `started_at`, `finished_at`, `cached: bool`.

The system's citation-validity inputs (Stage 1 results and claims) are derived from the
trace and stored in the record, so scoring and CI need no database.

**Resume and spend cap:**
- **Resume:** a rerun with the same config skips every cached question, at zero cost.
- **Spend cap:** cumulative `cost_usd` is checked before scheduling each question,
  reserving each in-flight question's per-question cap (`max_cost_usd`, or the baseline's
  estimate × 2). When spent + reserved ≥ cap, nothing new is scheduled; in-flight
  questions finish, and unscheduled ones are marked `skipped_spend_cap`. The run summary
  states the shortfall. Each invocation writes `evals/results/runs/<invocation_id>.json`
  (config, counts, spend, interruptions).

## 5. Scorers (`evals/scorers.py`)

**numeric_correct.**
- **Units:** the prediction is first normalized to the gold's base unit.
  - USD scales: "USD" ×1, "thousands"/"K" ×10³, "millions"/"M"/"mm" ×10⁶,
    "billions"/"B"/"bn" ×10⁹ (case- and symbol-insensitive, $ ignored).
  - "USD/share", "per share" ×1.
  - "percent"/"%" ×1; "fraction"/"ratio"/"decimal" ×100.
  - "percentage_points"/"pp"/"points" ×1; for comparison, "percent" is accepted as pp.
- **No unit guessing:** a value that matches only under a different scale is incorrect,
  but counted as a `unit_rescue` diagnostic.
- **Tolerances** (SPEC §13.4, plus the EPS rule in D085):
  - currency and averages: |pred − gold| ≤ 0.005 · |gold|;
  - percent and pp: |pred − gold| ≤ 0.1;
  - EPS: |pred − gold| ≤ max(0.005 · |gold|, 0.005);
  - comparison: choice must match the gold choice and |value − gold| ≤ 0.1 pp.
- **Signs:** they matter (a decline must be negative).

**not_available / not_applicable answers.** Every generated question has a gold value,
so such answers are **incorrect**. They are reported as an `abstention` rate, separately
from wrong values and parse failures.

**Optional abstention probe (choice, §12):** about 10 separate questions with
`not_applicable` gold (JPM/BAC gross margin) or `unavailable` gold. They would be
reported outside the headline, scored correct only on the matching status, and would
measure the system's "never invent" behavior against the baselines.

**citation_validity (system only):**
- **Numeric claims:** the fraction whose cited fact or computation matches the claimed
  value. This reruns M4's Stage 1 `check_claim` offline on the final Answer, against the
  ledger rebuilt from the trace's tool results; no LLM. It also reports the fraction of
  claims with any citation.
- **Text claims:**
  - *String match first:* supported if a verified quote of the cited chunk (whitespace-
    normalized, ≥ 8 words) occurs in the chunk and its key numbers or phrases appear in
    the claim.
  - *Then an LLM judge:* "does this passage support this claim? yes/no" on Opus 5.5.
  - Numeric templates rarely produce text claims; this mainly matters for the
    handwritten set.

**retrieval_recall@k (handwritten).**
- The frozen M2 v2 table is reused verbatim (per mode: capped recall@5/10, MRR@30).
- Plus **system-level recall**: of the gold chunks for each handwritten question, the
  fraction among the chunk IDs the system's filings workers saw in their first
  `search_filings` results (top k = 5 and 10, from the trace), and among all chunks they
  read in the run.

**llm_judge (handwritten explanatory only).**
- **Judge:** Opus 5.5, a different model from the system's Sonnet, to limit
  self-preference.
- **Inputs:** the question, the reference answer and the candidate answer. Citations are
  not shown, so the judge scores content.
- **Rubric 1–5:**
  - 5: all key points of the reference, nothing contradicted or invented;
  - 4: most key points, minor omissions;
  - 3: about half the key points, or one material error;
  - 2: few key points, or a material contradiction;
  - 1: wrong, invented or off-topic.
- **Output:** a JSON `{score, missing_points, errors}`.
- **Calibration:** 20 judge outputs, stratified across scores and systems, are given to
  the student blind (without the judge's score). Report exact agreement, within-1
  agreement and quadratic-weighted Cohen's κ. If κ < 0.6, the judge is reported as
  indicative only.

**Cost and latency.** `cost_usd` per question (and $/correct answer), and latency p50/p95
per system. Cached replays report the original latency.

## 6. Statistics

- **Accuracy CIs:** percentile bootstrap with 10,000 resamples and a fixed seed, per
  system overall and per subgroup.
- **Paired tests:**
  - **Test:** system vs each baseline on identical question sets, with an exact McNemar
    test (two-sided binomial on discordant pairs).
  - **Multiple comparisons:** Holm correction across the baselines.
  - **Reported:** the wins/losses table and the paired accuracy difference with a
    bootstrap CI.
- **Breakdowns:**
  - **Groups:** by template; by cutoff bucket (`before` / `june` / `after`); restated vs
    not; derived vs not; and B2 `gold_visible`.
  - **Small groups:** any group with n < 30 is labeled "descriptive; CI wide". The
    restated group (~2% of facts, about 8 questions) is reported only descriptively.

## 7. Budget decisions deferred in D082 (recommendations)

1. **Prompt caching: keep it off for the M5 headline; run it as an M6 cost experiment.**
   - *Savings:* planner and analyst prefixes (system prompt plus tool specs, ~6K tokens)
     and growing histories are re-sent every step. Sonnet cache reads at 0.05× would
     probably cut 30–50% of system input cost (about $8–12 on the test split).
   - *Replay and answers:* it changes request bodies, and therefore fingerprints, but
     replay stays identical for new runs, because `cache_control` is part of the recorded
     request. It does not change what the model is asked, but it is a runtime-behavior
     change.
   - *Accounting:* it needs cache prices in `pricing.toml`.
   - *Why not now:* M5 must measure the **accepted** system. Caching would make "system
     cost" a moving target.
2. **Budget reservation under concurrency: no change in M5.**
   - *Size of the issue:* overshoot is bounded at one call per in-flight agent (D065),
     and only filings workers run concurrently inside a run.
   - *What M5 does:* the runner reports any run whose tokens exceed MAX_RUN_TOKENS.
   - *If needed:* a fix is a runtime change for M6.
3. **Tesla-like headroom: keep MAX_RUN_TOKENS=200000.**
   - *Measured usage:* the numeric templates used 27K–130K tokens in M4; only
     explanatory questions approach 190K, and those are only in the 30-question
     handwritten set.
   - *Failure handling:* D072/D073 turn a budget stop into a finalized partial answer, and
     the eval counts it as answered or not like any other answer.
   - *What M5 reports:* the number of budget-finalized and revision-skipped runs.
4. **Cost-weighted budget: no.**
   - The token budget bounds context size and runaway loops; `max_cost_usd` (0.50 per
     run) already bounds money in dollars, and the runner's spend cap bounds the
     invocation.
   - Weighting tokens by price would merge two different limits.

## 8. Cost plan (updated for the approved choices; hard limit $100, ceiling $90)

**Approved scope:**
- system and B0 on Sonnet 5.5 and Opus 5.5 on the full test split (~280);
- B1 and B2 on Sonnet 5.5 on one frozen 100-question stratified test sample, run with
  the Batch API (50% off; latency "batch, not comparable");
- the handwritten set (30) with the Opus 5.5 judge;
- the abstention probe (~10).

**Caps:** dev pilot $20 and test run $70, for a $90 total ceiling. Each runner
invocation enforces its cap and stops cleanly, resumable from cache.

**Per-question estimates** (±50% until the dev pilot measures them):
- **System:** ≈ $0.11 (M4 per-type costs, +25% contingency).
- **B0:** Sonnet ≈ $0.016, Opus ≈ $0.032. Opus 5.5 and Sonnet 5.5 share a tokenizer, so
  Opus costs ≈ 2× Sonnet for the same work.
- **B1 (Sonnet, batch):** ≈ $0.065, including searches.
- **B2 (Sonnet, batch, 50K cap):** about 30K average input → ≈ $0.075 at standard rates,
  ≈ $0.038 batch.
- **Opus judge:** ≈ $0.02 per scored answer.

### Dev pilot (cap $20)

| Item | n | Expected | Range |
|---|---:|---:|---:|
| System | 100 dev | $11.0 | $5.5–16.5 |
| B0 Sonnet 5.5 | 100 dev | $1.6 | $0.8–2.4 |
| B0 Opus 5.5 | 100 dev | $3.2 | $1.6–4.8 |
| **Total as approved** | | **$15.8** | **$7.9–23.7** |

The high end ($23.7) exceeds the $20 cap.

**Recommendation:** run the dev pilot with **system + B0 Sonnet only**, which is SPEC
§16's "system + B0". B0 Opus is then measured on test. Its cost can be projected from
B0 Sonnet's measured tokens, because the tokenizer is the same.

| Dev pilot, recommended | Expected | Range |
|---|---:|---:|
| System + B0 Sonnet on 100 dev | **$12.6** | **$6.3–18.9** (within $20) |

### Test run (cap $70)

| Item | n | Expected | Range |
|---|---:|---:|---:|
| System, test split | ~280 | $30.8 | $15.4–46.2 |
| System, abstention probe | ~10 | $0.8 | $0.4–1.2 |
| System, handwritten (explanatory, ≈ $0.25) | 30 | $7.5 | $3.8–11.3 |
| B0 Sonnet 5.5 (test + probe + handwritten) | ~320 | $5.1 | $2.6–7.7 |
| B0 Opus 5.5 (test + probe + handwritten) | ~320 | $10.2 | $5.1–15.4 |
| B1 Sonnet 5.5, batch | 100 sample | $6.5 | $3.3–9.8 |
| B2 Sonnet 5.5, batch | 100 sample | $3.8 | $1.9–5.6 |
| Opus judge (system, B0 Sonnet, B0 Opus on handwritten) | 90 | $1.8 | $0.9–2.7 |
| Text-claim judge (system) | – | $1.0 | $0.5–1.5 |
| **Total as approved** | | **$67.5** | **$33.8–101.3** |

**Overall:** the recommended dev pilot ($12.6) plus the test run ($67.5) gives **$80.1
expected, range $40–120**. The expected total is under the $90 ceiling but **not well
under**, and the high end exceeds both the test cap and the ceiling. The cost is driven
by the system: 49% of the test run is its ~280 questions.

**Cut order**, decided now and applied before the test run if needed:
1. **(Already recommended)** B0 Opus is not run in the dev pilot: −$3.2.
2. **B0 Opus on the handwritten set** (and its judge scores) is not run: −$1.6. B0
   Sonnet remains the closed-book comparison on handwritten.
3. **B0 Opus on the test split** runs on the frozen 100-question sample instead of all
   ~280: −$5.8 (180 fewer questions × $0.032). The sample's paired tests still cover it, but the headline row for B0
   Opus is then sample-based.
4. **B1 `max_uses`** goes from 5 to 3: about −$2.

With cuts 2–4 the test run is ≈ **$58.1 expected (range $29–87)**, and M5 is ≈
**$71 expected**. Even then the high end of the test run exceeds $70. That is acceptable
only because the runner's caps stop cleanly. A capped run would leave the final part of
the seeded schedule unscored, so the gate below is used instead of running into the cap.

**Gate after the dev pilot** (the student decides):
- Phase C reports the **measured** system cost per question and B0 tokens.
- The test plan is re-projected as: measured system $/q × 320 + the other items at
  measured or estimated rates.
- If the projection exceeds **$60** (leaving $10 of headroom under the $70 cap), cuts
  2–4 are applied in order until it fits.
- If it still does not fit, the next option is to run the system on the 100-question
  test sample plus a stratified share of the rest. That is a change to the approved
  scope, so it needs the student's decision.
- The system's test run is otherwise never truncated by the cap mid-schedule.

## 9. Report (`evals/report.py` → `evals/results/report.md`)

**Headline table (test split), one row per system:**
- system and model;
- n;
- accuracy [95% CI], and per template (7 columns);
- accuracy before vs after cutoff;
- abstention %, parse-failure %;
- citation validity (system: numeric claims % and text claims %);
- $/question and $/correct;
- latency p50 and p95.

**Paired-test table:** system vs each baseline; wins, losses, Δ accuracy [CI], McNemar p
(Holm).

**Breakdown tables:**
- cutoff buckets;
- restated (descriptive);
- derived;
- B2 by `gold_visible` and `context_truncated`.

**Handwritten:** judge scores (mean [CI]), judge calibration (agreement, κ) and
system-level recall@5/10.

**Retrieval table (frozen M2 v2):** copied from `evals/results/retrieval_v2.json`:
per mode, capped recall@5/10, standard recall, hit rate, MRR@30 and n=30, with the D027
caveats.

**Failure analysis (structure only in M5; categorization is M6):** the SPEC categories
(wrong period, wrong concept, retrieval miss, planning error, arithmetic error,
hallucinated citation, refusal/parse failure). M5 lists the failed test questions per
system with automatic hints from traces and records (abstention, parse failure, budget
finalized, unit rescue, wrong sign). The counts are labeled "uncategorized".

**Ablation table:** empty placeholder for M6.

## 10. CI readiness (CI itself is M6)

- **Smoke set:** a fixed list of 10 **dev** questions (stratified, recorded in
  `evals/configs/smoke.toml`).
- **Cached records:** the system and B0 records for those questions are committed under
  `evals/cache/smoke/`. Each holds the prediction, usage, latency and precomputed
  citation inputs.
- **Replay-only mode:** `runner --replay-only` serves only from the cache and fails on
  any miss. It never constructs an SDK client and needs no API keys or database.
  Scoring is pure Python.
- **Threshold:** M6 records the smoke threshold.

## 11. Test plan (offline; fake providers only)

**Generation:**
- gold is recomputed independently from `financial_facts` for every template (Decimal
  equality);
- skip rules: banks' gross profit, unavailable periods, non-positive bases;
- `derived_q4` only where derived;
- comparison choice and |diff|;
- deterministic ids and split for a fixed seed (identical output twice);
- 30/70 per template;
- the frozen-hash check, and refusal to overwrite;
- fairness flags on fixtures (a restated EPS case, a derived Q4 restatement from inputs,
  cutoff buckets at the month boundaries).

**Scorers:**
- unit normalization (raw / K / M / B, "$95.36 billion" strings, percent vs fraction,
  pp);
- tolerance edges (exactly 0.5%, 0.1 pp), EPS small values, sign errors, comparison
  choice errors;
- abstention, parse failures, unit-rescue diagnostics;
- bootstrap and McNemar against known small cases.

**Runner:**
- cache hit, miss and question-text mismatch;
- atomic writes;
- resume after a simulated crash mid-run;
- spend cap: stops scheduling, in-flight questions finish, and the rest are marked
  skipped;
- retries and backoff with a fake 429/503;
- replay-only mode fails on a miss with no client constructed;
- config hashing stability.

**Baselines:**
- prompt rendering;
- JSON-answer parsing, including extra prose, code fences, multiple JSON objects and
  numeric strings;
- B1 `pause_turn` continuation and search-count cost;
- B2 statements-window extraction on fixture HTML (heading found, fallback, cap and
  truncation), and `gold_visible` computation.

**System adapter:** mapping the Answer to a prediction, comparison choice from claims,
and the citation-validity reconstruction from a recorded trace (using M4's replay
fixtures).

## 12. Choices for the student

1. **Baseline models:** recommended B0 = Sonnet 5.5 + Opus 5.5, B1 = Sonnet 5.5,
   B2 = Sonnet 5.5. Optional: Fable 5.2 (or legacy 5.1) B0.
2. **Full test or sample:** B1/B2 on the full test split (~$125 total) or on a
   100-question stratified test sample (~$80).
3. **Post-cutoff floor:** 20% per template (recommended) or the natural share (~7%).
4. **Abstention probe:** add ~10 not_applicable/unavailable questions, reported
   separately (recommended), or not.
5. **B2 context:** the statements window from raw filings at 25K tokens per filing and
   80K per question (recommended), or an alternative.
6. **Thinking and effort for baselines:** each model's default (recommended, the same as
   the system), or a fixed level.
7. **Batch API for baselines:** no (latency is reported; recommended), or yes (about half
   the cost, no latency).
8. **Spend caps:** dev pilot $25; test run $175.

## Proposed decisions (DECISIONS.md, on approval)

- **D083 — Generated benchmark v1:** 7 templates, Decimal gold from `financial_facts`
  only, ~400 questions balanced by template and company, the skip rules, and the record
  format.
- **D084 — Dev/test discipline and freezing:** 30/70 split stratified by template with
  a fixed seed. Tuning on dev only; final numbers on test only; hash-checked frozen
  question file; never regenerated in place.
- **D085 — Tolerances and units:** SPEC tolerances, plus the EPS rule max(0.5%, $0.005).
  Unit normalization without guessing; unit-rescue as a diagnostic only. Abstentions
  incorrect and reported separately.
- **D086 — Fairness metadata:** cutoff bucket by latest original filing date (period-end
  date also kept); restated against first-filed values from the frozen companyfacts
  JSON; derived flag.
- **D087 — Baseline protocol:** shared prompt and JSON answer format, identical parsing;
  model-default thinking and effort; no sampling parameters.
- **D088 — B1 web search:** `web_search_20260209`, max_uses 5, open web; per-search
  billing added to cost.
- **D089 — B2 stuffed context:** statements window from the frozen raw filings (the
  corpus lacks 10-Q statements), with the caps, truncation order and `gold_visible`
  fairness split.
- **D090 — Runner:** TOML configs (YAML deferred), cache key, atomic records as the
  resume checkpoint, spend cap with in-flight reservation, replay-only mode.
- **D091 — System adapter and comparison choice:** the documented asymmetry, with no
  change to the M4 schema.
- **D092 — Citation validity:** offline Stage 1 rerun from the trace; text claims by
  string match, then an LLM judge.
- **D093 — LLM judge and calibration:** Opus 5.5 judge, rubric, 20 student labels,
  weighted κ.
- **D094 — Statistics:** bootstrap CIs, exact McNemar with Holm, subgroup reporting
  rules.
- **D095 — D082 resolutions for M5:** no caching, no reservation change, MAX_RUN_TOKENS
  stays 200K, no cost-weighted budget (reasons in §7).
- **D096 — Model cutoffs and Fable versions:** cutoffs from the official models overview
  (all Jun 2026); Fable 5.2 preferred over legacy 5.1 if used.

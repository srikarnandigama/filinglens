# M6 Phase A — experiments, improvement and CI: design

Status: **design for approval. No code changed, no LLM calls, nothing committed.** All numbers
below come from the committed M5 cache (`evals/cache/2672337d…`, the system's 320 records) joined
read-only to their `trace_events` (7,346 step-level events). The analysis scripts are throwaway
scratch files. Phase B turns the categorizer into `evals/failures.py`. Proposed decisions
D111-D124 are at the end; they go into DECISIONS.md only on approval.

## 0. Current state (2026-11-12)

- M1-M5 accepted; tags `m2-v2-accepted`, `m3-accepted`, `m4-accepted`, `m5-accepted` (df6b37a,
  clean tree, in sync with origin). M6 has not started.
- M5 headline (frozen 100-question test sample): system 99%, B2 96%, B1 90%, B0 Fable 69%,
  Opus 55%, Sonnet 42%. 180 subset: system 99.4% (one miss: Costco trend_avg abstention).
  Handwritten 30: 6 no-answers; judge mean 3.23 with no-answer = 1, 3.79 over answered.
  System cost $0.157/question. M5 spend $69.48.
- Frozen: questions_v1 (+ manifest, sample_100, subset180), handwritten_v2, corpora, facts
  snapshot, M2 labels, B2 metadata, the M5 cache (1,286 committed files, about 6 MB) and the M5
  results.
- Evals: TOML configs (`evals/configs/m5_*.toml`), runner with a disk cache and spend caps,
  `--replay-only` (no keys, no DB), report generated from the cache. `EvalConfig.ids` and
  `SystemConfig.flags` (RunConfig overrides) already exist for a smoke set and ablations.
- **A cache-key finding that shapes the design.** The system's cache key covers the resolved model
  IDs, the prompt-file hashes, snapshot, corpus, MAX_RUN_TOKENS, `max_cost_usd`, the config's
  `flags` and the runner version. It does **not** cover runtime code. A behavior change that
  touched neither prompts nor flags would silently serve M5 records to M6 configs. A change to a
  prompt file would also change the M5 configs' keys and break the M5 report's replay. Hence D118:
  every M6 change sits behind a RunConfig flag whose default is M5 behavior, no prompt file
  changes, and a test pins the M5 config hashes.
- Not yet present: `.github/`, any M6 config, any failure categorization.

## 1. Failure categorization (offline, from M5 records and traces)

### 1.1 Method

Deterministic rules over each run's trace (rejected and duplicate tool calls, tool-result hashes,
agent steps, verification `failing` maps, budget events, corrective-retry messages) plus the
cached record (status, retrieval). No LLM was used to categorize. A run can fall into several
categories; counts are runs with at least one such event.

**Spot-check method.** For every category with ≤ 10 runs, I read the full step trace of every
run, or of every run up to 10. For larger categories I read 2-4 runs: the examples below, the 4
largest stall cases and 4 analyst cases flagged as possible false positives. Every rule matched
what the trace shows. In Phase B, `evals/failures.py` makes this reproducible. It writes every
categorized run with its evidence, and the report lists a seeded random 5 per category for your
spot check.

### 1.2 Outcome failures (the answer was wrong or missing)

| Category (SPEC §13.6 + new) | dev 100 | test 180 | handwritten 30 | probe 10 | Examples |
|---|---:|---:|---:|---:|---|
| Wrong period / wrong concept / arithmetic error | 0 | 0 | — | 0 | none in any system answer |
| Refusal / parse failure (final) | 0 | 0 | 0 | 0 | none |
| **Budget exhausted before a draft → no answer** (new) | 0 | 0 | **6** | 0 | `hq_4d5d9efc…` Exxon/Pioneer: 4 filings workers, 17 passages, 259K tokens, $0.09; `hq_efbdb0ea…` Exxon GHG: planner 8 calls, 121K tokens |
| **Budget stop after draft → wrong abstention** (new) | 0 | **1** | 0 | 0 | `q_7efc51f8…` Costco trend_avg: right mean computed, then planner `list_available_metrics` ×6 and analyst `json` tool ×5 → 203K tokens, D073 kept nothing |
| Partially answered (claims dropped) | 0 | 0 | 2 | 0 | `hq_19ea90a4…` Microsoft cloud margins; `hq_d2c0efbe…` Apple tariffs |
| Hallucinated citation, text claim (claim judge "unsupported") | — | — | 4 claims / 3 runs | — | `hq_395269fb…` BAC: "uninsured deposits more prone to leave" not in passage; `hq_8c86cd75…` Disney DTC: improvement attributed to causes the passage doesn't give |
| Hallucinated citation, numeric | 0 | 0 | 0 | 0 | citation validity 531/531 (test) |
| Explanatory answer judged 2 of 5 | — | — | 3 | — | `hq_ce980990…` Microsoft Copilot; `hq_bbeba329…` Pfizer cost program |
| Retrieval miss (no gold chunk among chunks seen) | — | — | 12 | — | `hq_24a3e4ca…`, `hq_395269fb…`; descriptive only: gold labels are pooled, not exhaustive (D028), so a miss can still find relevant text |
| Data definition (gold), not a system error | 0 | 3 questions | — | — | Disney segment operating income (D110); the system matches the gold, baselines do not |

### 1.3 Degraded runs (answered correctly, but with wasted steps or a revision)

| Category | dev | test | hw | Examples (dev first) |
|---|---:|---:|---:|---|
| **Planner stall**: ≥ 2 consecutive steps with no new information (every result an error, a D067 duplicate, or byte-identical to one already received) | 10 | 16 | 1 | dev `q_d452cb7e…` Apple gross profit (`list_available_metrics` ×4, 5 calls); test `q_8a1de8ad…` JPM (`resolve_company` 7× with spelling variants, then a valid plan on the forced last step) |
| **Analyst stall** (same rule) | 12 | 43 | 2 | dev `q_419ccfb8…`, `q_e3e4d331…`; test `q_7efc51f8…` (`json` ×5) |
| **Invalid final-answer tool** (`TOOL_NOT_ALLOWED`: `json`, `x`, `json_placeholder`, "```json", `bash`) | 9 | 21 | 0 | dev `q_d0059e5f…`, `q_419ccfb8…`; test `q_7efc51f8…`, `q_4fa166df…` |
| **Empty analyst reply → corrective retry**: the API returned `stop_reason: tool_use` with an empty content list (23-24 output tokens); the loop treats it as a final reply with no JSON and spends the single retry on it. 70 such replies, plus 2 prose replies without JSON | 28 | 43 | 1 | dev `q_03edb50e…`, `q_0734cc0c…` |
| Untraced quant call (D079 rejection) | 45 | 92 | 4 | dev `q_f8e25d97…`, `q_1c167361…`; the pattern, e.g. test Costco's `evaluate("15817000000/4")`, is arithmetic on a number the analyst produced itself |
| Revision: summary numbers not in any claim (Stage 1) | 17 | 21 | 1 | dev `q_3fa4b659…`, `q_3f343d61…`; trend_avg is 20 of the 38 dev+test cases (summary quotes rounded quarterly values such as "14.87" for $14.87B) |
| Revision: unsupported caveat (Stage 2) | 11 | 13 | 5 | dev `q_03edb50e…` (seasonality speculation), `q_46743110…` ("52-week year") |
| Revision: unsupported claim (Stage 2) | 0 | 1 | 3 (+2 probe) | test `q_957bc65c…`; hw `hq_9e6c0c0d…` |
| Planning error caught by validation (planner corrective retry) | 0 | 2 | 1 | test `q_128b9d1d…`, `q_c57e9ad0…` (a requested period not in discovery; a `depends_on` schema error) |
| Filings passage cap hit (D074) | — | — | 9 | `hq_af3da89e…`, `hq_cdeefd82…` |
| Revision skipped for budget (D072) | 0 | 0 | 2 | `hq_24a3e4ca…`, `hq_9244d7ed…` |
| Near budget (> 150K tokens, answered) | 0 | 3 | 9 | test `q_1256a4e5…` (planner 8 calls), `q_33294708…` |

Every revision converged: no run still had failures after its last round.

### 1.4 Meeting SPEC's "≥ 25 failures from dev" honestly

The system answered all 100 dev-pilot questions correctly, so there are **0 dev answer
failures**. The proposal:

1. Count **failure events on dev**: 133 events in 74 of the 100 dev-pilot runs (the
   degraded-run table above). This meets "≥ 25 categorized failures from dev" as failure
   *events*, not wrong answers. The report says exactly that.
2. Add the events from the explanatory dev prompts (§5) once they run in Phase C, both under the
   M5 system and the M6 system.
3. Keep the 18 never-run dev numeric questions **unused** as a fresh dev reserve. They are used
   only if Phase C leads to a further fix, which you approve and which must be validated on data
   that did not motivate it.
4. **Stated deviation:** the two budget outcome failures (handwritten no-answers and the Costco
   abstention) were found on **test** in M5 and are already reported there. The fixes are partly
   motivated by them. The same mechanisms appear on dev (planner stalls in 10, analyst
   stalls/invalid tools in 21, empty replies in 28 dev runs), but the explanatory budget failure
   had no dev evidence until §5 creates some. So the M6 test rerun is not a clean held-out test of
   *fix selection*. It measures fixes chosen partly from test failures. The report and D111 say so,
   and no test result is relabeled as dev.

## 2. The top two failure causes and their fixes

The data confirms your two expectations, and sharpens both.

### 2.1 Cause A: explanatory runs exhaust the token budget before a draft

**Evidence.** All 6 handwritten no-answers stopped on MAX_RUN_TOKENS before any analyst draft.
In five of them the Haiku filings workers used 150-234K tokens. Those five runs cost only
$0.092-0.152, far below the $0.50 per-run cost cap. A filings worker's context grows about
3K → 10K → 15K → 20K tokens per step, mostly because each search returns about 7K tokens of
snippets. One worker uses 33K (median) to 89K (max), and 4-5 workers run per question. The sixth
run was a planner stall (121K tokens, see cause B).

**Why a per-worker cap is not enough** (simulated on the traces). With a 200K raw budget, a ~25K
planner and a 60K answer reserve, 4-5 workers get 23-29K each, which is 2-3 steps. 9 runs would
still overshoot, and the workers would be starved. The root cause is the one D082 flagged and D095
declined for M5: MAX_RUN_TOKENS counts Haiku tokens 1:1 with Sonnet tokens, although Haiku's
input price is 1/20 of Sonnet's.

**Fix A1: price-weighted run token budget** (flag `budget_weighting = "input_price"`). The run
budget counts each call's tokens (all four kinds, as D060) multiplied by
`input_price(call model) / input_price(planner model)`, from pricing.toml. Sonnet calls weigh
exactly 1. **Every numeric run (planner/analyst/verifier only) counts exactly as in M5.** Haiku
weighs 0.05. D072's largest-call estimate uses the same weighted units. The weights come from the
run's price snapshot, so replay is identical. Effect on the six runs: at the point where they
failed, five had used **35K-64K** weighted tokens and would have continued to the analyst. The
sixth (planner 121K) is cause B. Bounds that remain: `max_cost_usd` ($0.50), `max_steps` (8),
D074's 4 passage reads per worker, and per-call context (unchanged per agent).

**Fix A2: no-draft budget stop becomes an explicit answer** (flag `finalize_without_draft`).
If BudgetExceeded is raised before the first analyst draft, the run returns
`Answer(status="not_available", claims=[], summary="The run stopped at its <limit> before an
answer could be drafted.")` with D073's caveat style. Run status is `done` and `runs.error` is
`{"type":"BudgetExceeded","handled":"stopped_without_draft"}`. This is a safety net. **Scoring is
unchanged:** such runs remain "no answer (budget)" in the report and score 1 for the judge, as in
M5 (D108).

- **Considered, not proposed:** a per-worker share with an answer reserve enforced by projected
  step cost (A3). It starves workers (above), and under concurrent workers it makes the stop
  depend on completion order, which risks replay identity. It is revisited only if dev shows A1
  is insufficient.
- **Offline tests:** weighted accounting (Sonnet-only usage identical to M5, Haiku 0.05, cache
  tokens weighted the same, the D072 estimate weighted); a fake-provider run whose workers exceed
  200K raw but not weighted reaches a draft; a planner-phase stop produces the A2 answer; flags off
  reproduce M5 behavior; replay identical.
- **Dev check (Phase C):** the 10 explanatory dev prompts under the M5 and M6 systems. Report
  answered vs no-answer, raw and weighted tokens, cost and latency.
- **Expected effect:** handwritten no-answers 6/30 → 0-1. If the six new answers score like the
  other 24 (mean 3.79), the judge mean with no-answer = 1 would rise from 3.23 toward ~3.8; that is
  a projection, not a result. Cost: about +$0.10 for each formerly failing run (analyst +
  verifier), roughly +$0.02/question before caching. Latency: +30-50 s on those runs. Raw tokens
  per explanatory run rise to roughly 250-300K. Numeric questions: no change at all.
- **DECISIONS:** D113 (A1), D114 (A2).

### 2.2 Cause B: agent stalls and invalid final-answer behavior

**Evidence.** The planner and analyst repeatedly issue cheap tool calls (49-71 output tokens)
that return nothing new, while the context grows by 3-4K tokens per step. Examples:
`list_available_metrics` ×6 (Costco), `resolve_company` ×7 under spelling variants (JPM), `json`
×5. Each time, the D068 final-step guard on step 8 makes the model write a complete, valid output
on its first try. So the guard works; it just fires 4-6 steps too late. Two related behaviors:
calls to nonexistent tools (`json`, `x`, …: 9 dev / 21 test runs), and 70 empty replies (an
empty content list with `stop_reason: tool_use`) that each spend the corrective retry plus a
Sonnet step.

**Fix B1: no-progress guard** (flag `stall_guard_steps = 2`). A step is *no-progress* if it
made tool calls and every result was an error (local rejection or server error), a D067
duplicate, or byte-identical (same model-view hash) to a result this agent instance already
received. That last condition catches the JPM spelling variants. After 2 consecutive no-progress
steps, the next step is a final step: D068's guard message and `tool_choice: none`. If that
output is invalid, the existing single corrective retry runs with tools re-enabled and the
counter reset. It applies to every role with tools. It is traced as a `stall_guard` event and is
deterministic (it depends only on the instance's own call order and results), so replay is
identical.

*Simulation on M5 traces (N = 2):* it fires in 18/100 dev, 52/180 test and 4/30 handwritten
runs. It would remove 1.05M tokens on test (**$0.012/question** at M5 prices) and 72K tokens from
the Costco run, which would then have reached verification with about 130K tokens left. False
positives (useful work after the guard point): **0 planner instances**; 2 dev, 6 test and 1
handwritten analyst instances. In those, the extra steps were follow-up `evaluate` calls after the
headline result already existed (trend_avg summary figures). N = 1 cuts too much (14 planner
false positives on test); N = 3 saves half as much.

**Fix B2: unknown-tool hint** (flag `unknown_tool_hint`). A call to a tool that does not exist
for any role gets "There is no tool named "json". Tools only fetch data or calculate. To give
your final answer, reply with the JSON object as plain text, not as a tool call." A real tool
that the role may not use keeps the current message. This is runtime text, not a prompt file.

**Fix B3: empty reply handling** (flag `empty_reply_guard`). A reply with no text and no tool
calls is answered with the final-step guard and `tool_choice: none`. It does not consume the
corrective retry and counts as a no-progress step.

- **Alternative considered, not proposed:** a `submit_answer` tool carrying the Answer schema.
  It would make the `json` attempts legitimate, but it changes every role's output path, the tool
  specs and the M5 cache key; D063 rejected it for M4.
- **Offline tests:** scripted fake-provider sequences for planner duplicates, spelling variants
  with identical results, analyst invalid tools, untraced calls, empty replies, progress resetting
  the counter, a forced final followed by an invalid output → retry with tools; the B2 message
  only for unknown names; flags off → M5 behavior; replay identical.
- **Dev check:** the 35 dev-pilot numeric questions and the 10 explanatory prompts. Report
  guard firings, steps per role, empty replies, invalid-tool calls, corrective retries,
  revision rounds (to catch analyst false positives that force a revision), cost and latency.
- **Expected effect:** numeric accuracy unchanged at ~99-100%; the Costco-type loss is
  prevented (a plausible +1 on the test sample, not guaranteed). Cost −$0.012 (stalls) − ~$0.005
  (empty replies) per question at uncached prices. Fewer steps on the slow tail, so p95 latency
  should drop. Handwritten: the Exxon GHG planner stall no longer exhausts the budget.
- **DECISIONS:** D115.

## 3. Cost improvements

### 3.1 Prompt caching (flag `prompt_caching`)

- **Mechanism.** Cache breakpoints on the tool list, the system prompt and the last message
  block of every request from the multi-step roles: planner, analyst, filings and data workers.
  Each step then reads the previous step's prefix and writes only the new tail. The verifier
  usually makes one call, so it is not cached (a write that is never read costs 1.25×). The
  planner's system prompt and tools are identical across runs, so they can also hit across
  questions within the cache lifetime. Phase B checks the current Anthropic docs first (SPEC rule
  7): breakpoint placement and count, minimum cacheable length per model, TTL and the usage fields.
- **Pricing.** `pricing.toml` has blank `cache_read_per_mtok` and `cache_write_per_mtok` for Sonnet
  5.5 and Haiku 5.5, and pricing.py already raises PricingError if cache tokens are billed without
  a price. **You fill these in from the official pricing page** (prices only come from you). The
  preflight gets a check for them. My estimates assume the usual read 0.1× / 5-minute write 1.25×
  of input; you confirm the actual numbers.
- **Estimated effect** (within-agent caching only, on M5 traces): numeric $0.157 → **$0.097
  (−38%)**; the analyst halves ($0.073 → $0.036), the planner falls by a third. Handwritten
  $0.179 → $0.134 (−25%). Probe −14%. Cross-run hits would add a little more.
- **Accounting and replay.** Usage already records cache read/write tokens (anthropic provider,
  migration 004 columns). `LLMRequest` gains `cache: bool`, excluded from the fingerprint when
  false (as `tool_choice` was in D068), so M4/M5 fingerprints are unchanged. Replay uses recorded
  usage and the run's price snapshot, so it stays identical even though live cache hits depend on
  timing.
- **Effect on budgets.** None by design. The token budget keeps counting cache tokens like input
  (D060), times A1's model weight. Caching changes dollars, not budget decisions, so budget
  behavior stays comparable before and after.
- **DECISIONS:** D116.

### 3.2 The trend_avg revision loop (flag `summary_cited_values`)

58 of the 280 numeric runs (21%) needed a revision. In 38 of them, the first-round failures
included summary numbers missing from claim texts. 20 of those 38 are trend_avg, whose summary
quotes rounded quarterly values that the mean claim cites but does not restate. **Proposed Stage 1 rule:** a summary number also passes if it is a rounded
display, at its shown precision and in raw/thousand/million/billion scale (percent for
`value_pct`), of a value cited by a claim of the same answer: a cited fact's value or a cited
computation's output field. Numbers still have to trace to cited evidence; nothing uncited
passes.

- **Offline evidence before you decide to keep it (Phase B, no API):** rerun Stage 1 with the new
  rule on every M5 first draft (all 280 numeric runs, drafts and ledgers rebuilt from the
  traces). Report how many first-round summary failures clear. Keep it only if it clears at least
  half, and list every newly accepted number with the cited value it matched.
- **Expected effect:** the share of numeric runs needing a revision falls from 21% to an
  estimated 12-15%, saving about $0.004-0.006/question (more for trend_avg). Accuracy is unaffected (the final value is checked
  separately). Unsupported-caveat revisions (24 dev+test) are correct rejections (D076) and are
  left alone.
- **DECISIONS:** D117.

### 3.3 Order and fairness

**Recommendation: apply all of these before Phase C** (A1, A2, B1-B3, caching, and the summary
rule if its offline evidence holds). Then Phase C, the test rerun and every ablation run one final
M6 system, and the ablations are cheaper.

- **Comparison.** Before/after compares the accepted M5 system (cached records) with the M6
  system on identical question IDs.
- **Caching's share of the cost change.** Caching's effect is separated exactly. Each M6 run's
  cost is recomputed from its recorded usage with cache tokens priced as input ("M6 without
  caching"), so the report shows M5 → M6 uncached (behavior fixes) → M6 actual (caching).
- **Tokens and steps.** These are unaffected by caching and are reported alongside.
- **Latency.** Latency varies with API load across days, so it is reported with that caveat.

## 4. Disney operating income (D110)

**Proposal: document the definition. Do not change questions or gold, and create no question set
v2 now.**

- **The definition** (D119, the report's methodology section and the `operating_income` row of
  the metric documentation in docs): "operating_income is the company's `OperatingIncomeLoss`
  fact as tagged; for Disney, whose income statement has no operating-income line, that tag is
  total segment operating income."
- **Reporting.** Every M6 table that involves numeric questions reports with/without the Disney
  segment-OI questions, as M5 does.
- **Effect on reported results: none.** The system reads the same fact before and after, so the
  numbers for system vs B2 do not change (+3.9 pp with, +2.3 pp without, p = 0.22).
- **Options not proposed:** a v2 question set (for future use only), or relabeling the metric in
  the edgar-mcp tool description (an M3 server change that needs your approval).

## 5. Explanatory dev set (my prompts, no references, mechanics only)

**Proposed prompts (for your review; nothing runs before you approve them):**

| id | Company / filing | Prompt | Shape |
|---|---|---|---|
| xd01 | META FY2025 10-K | How did Meta explain the growth in its advertising revenue in 2025? | MD&A why |
| xd02 | JPM FY2025 10-K | According to management, what drove the change in JPMorgan Chase's net interest income in 2025? | MD&A why + metric |
| xd03 | TSLA FY2025 10-K | What risks does Tesla's 2025 10-K describe about its dependence on Elon Musk? | risk factors |
| xd04 | GOOGL FY2025 10-K | What does Alphabet's 2025 10-K say about the antitrust cases against Google and their possible effects on its business? | risk / legal |
| xd05 | JNJ FY2025 10-K | How did Johnson & Johnson explain the change in its MedTech sales in fiscal 2025? | MD&A why |
| xd06 | NKE FY2027 Q1 10-Q | What did Nike say drove the change in its gross margin in the first quarter of fiscal 2027? | 10-Q MD&A, latest quarter |
| xd07 | WMT FY2026 10-K | How did Walmart describe the growth of its advertising business in fiscal 2026? | MD&A |
| xd08 | DIS FY2025 10-K | How did Disney explain the change in its Experiences segment operating income in fiscal 2025? | MD&A why |
| xd09 | PFE FY2024 + FY2025 10-Ks | How did Pfizer's risk factors about patent expirations and loss of exclusivity change between its fiscal 2024 and fiscal 2025 10-Ks? | two-filing diff (budget stress) |
| xd10 | XOM + CVX FY2025 10-Ks | How did Exxon Mobil and Chevron each explain the change in their upstream earnings in 2025? | two companies (budget stress) |

- **No overlap with handwritten_v2.** handwritten_v2 already covers all 20 companies, so overlap
  is avoided by (company, filing, topic). Every prompt uses a fiscal period that handwritten_v2
  does not use for that company, except xd09, which reads PFE's FY2024 10-K risk factors where
  the handwritten question reads its MD&A cost program. No topic repeats. Every period was checked
  to exist in the snapshot's filings.
- **File.** `evals/explanatory_dev_v1.jsonl` (`id`, `question`, `split = "explanatory_dev"`, no
  reference, no gold chunks), frozen by SHA-256 after your approval and loaded by the runner like
  the handwritten set.
- **Mechanical metrics only** (per prompt and in total, M5 system vs M6 system):
  - outcome: answered / partially_answered / not_available / no answer (error);
  - usage: raw and weighted tokens, cost, latency;
  - calls: LLM calls per role, filings workers, passages read, CALL_LIMIT hits;
  - guards and budget events: stall-guard firings, empty replies, invalid-tool calls, budget
    events (no-draft stop, budget_finalized, revision_skipped), corrective retries;
  - verification: verifier rounds, claims kept/dropped, caveats removed.
- **Never measured here:** no judge score, no retrieval recall, no accuracy.

## 6. Ablations (SPEC §13.5) on the final M6 system

All variants are M6 configs with one flag changed. Each is paired with the M6 system on the
same question IDs.

| Ablation | Flag change | Question set | n | Measures |
|---|---|---|---:|---|
| −verifier | `verifier = false` | numeric test sample (below) | 50 | accuracy, citation validity, $/q, latency |
| −quant tools | `use_quant_tools = false` (analyst_no_quant) | same 50 | 50 | accuracy by template (arithmetic-heavy: trend_avg, multi_step, comparison), $/q |
| +rerank | `retrieval_mode = "hybrid_rerank"` (SPEC's full system) | handwritten 30 | 30 | system recall@5/10 (D099), judge mean, no-answer, $/q, latency |
| −rerank | `retrieval_mode = "hybrid"` | handwritten 30 | 30 | same (conditional, see §10) |
| vector-only | M6 default (`vector`) | the M6 handwritten run itself | 30 | same |
| large worker | `worker_model_env = "PLANNER_MODEL"` | handwritten 30 | — | **deferred** (§10) |

- **Why these sets.** Numeric questions never start a filings worker: 0 filings tokens in all
  280 numeric runs. So retrieval ablations only make sense on the explanatory set, and the
  verifier and quant ablations on numeric templates. The only labeled explanatory set is the
  handwritten 30 (test). Ablation runs there are separate systems; the M6 system itself is still
  run on them exactly once.
- **Numeric test sample (frozen in Phase B).** 50 questions drawn seeded and stratified from the
  frozen 100-question sample (7 per template, plus the Costco miss `q_7efc51f8…` forced in). The
  ID list is saved with its SHA-256 like subset180. Every one of them has M5 system and baseline
  records.
- **Statistical caveats.** With M5 at 99%, the −verifier difference will likely be 0-2
  discordant pairs: no detectable accuracy effect at n = 50, so it is mainly a cost and latency
  result. −quant may show an arithmetic effect on large-number templates, but n ≈ 7 per template
  is descriptive. Retrieval ablations at n = 30: the M2 table already shows recall@10 differences of
  ≤ 0.03 between vector and hybrid_rerank, so end-to-end judge differences will likely be within
  noise. Rerank adds about 12 s per search (D047), so latency will differ. Everything is reported
  with CIs, and nothing is called a significant improvement without a paired test.
- **Large vs small worker.** Deferred for cost: Sonnet filings workers cost about 20× more, about
  $0.30/question and about $10 for 30 questions. Under A1 it would also be confounded, because
  Sonnet worker tokens weigh 1.0 and the run would hit the budget again; the ablation would
  measure the budget rule, not the model. It is recorded in D124 as deferred.

## 7. Test rerun plan (after the fixes are final; once)

| Run | Questions | Paired with | Tests |
|---|---|---|---|
| M6 system, numeric | the 50-question test sample (includes Costco) | M5 system records (and B0/B1/B2) on the same 50 | exact McNemar; paired bootstrap Δaccuracy, Δ$/q, Δlatency (10,000 resamples, fixed seed, D094) |
| M6 system, handwritten | all 30, including the 6 M5 no-answers, **exactly once** | M5 system on the same 30 | judge mean (no-answer = 1) and over answered, paired bootstrap CI on the mean difference; exact McNemar on answered/no-answer; system recall@5/10; $/q; latency |

- **Judging.** Opus judge with the same rubric and prompts (D093), via the Batch API, with the
  cache keyed as in M5.
- **Calibration.** Not redone: the D110 calibration covers the judge and is unchanged.
- **Disney.** Results are shown with and without the Disney questions.
- **Reporting.** Results that don't favor the fixes are reported as they are.

## 8. CI (SPEC §14)

- **`.github/workflows/ci.yml`.** Runs on push and pull_request, ubuntu-latest.
  - Setup: `actions/checkout` and `astral-sh/setup-uv` pinned to versions; `uv python install
    3.12.15`; `uv sync --frozen`.
  - Checks: `ruff check`, `ruff format --check`, `pytest -q`, then the smoke eval.
  - Environment: no secrets. The model IDs for the cache key are public IDs set as workflow env
    vars (`PLANNER_MODEL`, `WORKER_MODEL`, `VERIFIER_MODEL`), which satisfies "model IDs only from
    env vars". `HF_HUB_OFFLINE=1` and `TRANSFORMERS_OFFLINE=1` are set. There is no `.env`, no
    database and no `FILINGLENS_TEST_DB`.
- **Install size.** On Linux, `uv sync --frozen` would pull torch's CUDA wheels (several GB).
  Nothing imports torch, transformers or sentence-transformers at module level; models load
  lazily. Proposal: `--no-install-package` for torch and the CUDA/triton packages, verified in
  Phase B by a dry run in a clean git worktree (no `data/`, no `.env`, a venv built without
  them). If that dry run shows any test needs them, CI installs the full lock and caches it.
- **Which tests run.** 277 are collected today.
  - Skipped by existing gates: the 11 modules gated on `FILINGLENS_TEST_DB=1` (DB-backed
    tests, including real-MCP-server orchestrator tests); model-tokenizer tests (skip without
    `data/models`); raw-snapshot tests (skip without `data/raw`); the corpus replay
    (`FILINGLENS_TEST_CORPUS_REPLAY`); and the live LLM smoke test (`FILINGLENS_LIVE_LLM`).
  - Everything else runs: scorers, generator logic, runner and judge offline tests, agent loop
    with fake providers, verifier checks, budget guards, quant/MCP unit tests that need no DB,
    parsing on fixtures.
  - The exact pass/skip counts come from the Phase B clean-worktree run and are written into
    M6_STATUS.
- **Smoke eval.** `python -m evals.smoke evals/configs/ci_smoke.toml` replays the M6 system's
  committed records for 10 test questions (from the 50-sample, stratified, seeded) through the
  existing `--replay-only` path and the scorers.
  - It fails on any cache miss (for example a prompt edit that changes the key) or if accuracy
    falls below `min_accuracy`. That threshold is recorded in the config as the replayed accuracy
    at recording time.
  - Honest scope: a replay smoke test catches regressions in the question set, cache keys, the
    adapter, parsing and scoring. It cannot catch live behavior changes.
- **What gets committed for the smoke.** Nothing new: the 10 records are part of the M6 cache,
  committed like M5's (about 4-5 KB each). The whole M6 cache adds an estimated 1-2 MB.
- **Phase B check.** The mechanism is also tested offline against existing M5 records. The config
  switches to M6 records once they exist in Phase D. Pushing and getting CI green on GitHub is
  Phase D.

## 9. Report changes (M5 headline unchanged)

`python -m evals.report` keeps generating every M5 section from the same 7 M5 configs. A test
asserts that regenerating with only those configs reproduces the current report.md byte for
byte, so M5 numbers stay reproducible from the M5 cache. New sections, generated from M6
configs, appear only when M6 configs are passed:

1. **Failure analysis.** The §1 tables (counts by category and split, 2 examples each, the method
   and the seeded spot-check list). This replaces "Failures (uncategorized)".
2. **M6 fixes: before/after.** Numeric 50-sample and handwritten 30, paired tests, the cost
   decomposition (M5 → M6 uncached → M6 actual), steps and tokens per role, no-answer rate, and
   Disney with/without.
3. **Dev validation (mechanical only).** The stated limitation, and the explanatory dev mechanics
   table.
4. **Ablation table.** Rows: M6 system and each variant. Columns: question set, n, accuracy or
   judge mean [CI], Δ vs M6 with paired p, recall@5/10, $/q, $/correct, latency p50/p95,
   no-answer.
5. **Methodology additions.** The Disney definition (D119), the A1 budget weighting, and the
   deviation in §1.4.

## 10. Cost plan

- **Basis.** Projections are made before any spend, at measured M5 rates: numeric $0.153 (dev)
  and $0.1575 (test) per question; handwritten $0.179, or $0.19 for runs that reach an answer;
  judge $0.35 per 30-answer config. M6 estimates apply §3's caching and §2's savings: about $0.09
  numeric and $0.16 explanatory.
- **Rules.** Caps reserve in-flight runs (`max_cost_usd` $0.50 × concurrency). Phase C configs run
  at concurrency 2.
- **Stop rules.** Any config that hits its cap or runs more than 20% over its projection stops and
  is reported. Phase C is held to its M5-rate projection; Phase D to its re-projection after Phase
  C measured M6 rates.

| Step | What | n | Projection at M5 rates | M6 estimate | Cap |
|---|---|---:|---:|---:|---:|
| C1 | M6 system, dev numeric (5/template, seeded from the dev pilot; paired) | 35 | $5.36 | $3.15 | $6.50 |
| C2 | M5 system, explanatory dev prompts (before) | 10 | $1.79 | $1.79 | $3.00 |
| C3 | M6 system, explanatory dev prompts (after) | 10 | $1.90 | $1.60 | $3.25 |
| | **Phase C** | | **$9.05** | **$6.54** | **$12.75** |
| D1 | M6 system, handwritten 30 (once) | 30 | $5.70 | $4.80 | $6.00 |
| D2 | M6 system, numeric test sample | 50 | $7.88 | $4.50 | $5.50 |
| D3 | −verifier | 50 | $6.40 | $3.25 | $4.00 |
| D4 | −quant tools | 50 | $6.40 | $3.50 | $4.25 |
| D5 | +rerank (hybrid_rerank), handwritten | 30 | $5.70 | $4.80 | $6.00 |
| D6 | Judges (D1, D5) | | $0.70 | $0.70 | $1.50 |
| | **Phase D base** | | **$32.78** | **$21.55** | **$27.25** |
| | **M6 total (base)** | | | **≈ $28.1** | **$40.00** |
| D7 | −rerank (hybrid), handwritten + judge (conditional) | 30 | $6.05 | $5.15 | $6.25 |
| D8 | Large worker | — | ~$10 | ~$10 | deferred |

- **Caps.** The caps sum to exactly $40.00 for the base plan. The M6 estimate (~$28) meets the
  ~$30 target; at M5 rates (i.e. if caching and fixes saved nothing) Phase D could not fit, so
  the cut order applies.
- **D7 is conditional.** It runs only if, after Phase C, the re-projected total including it is
  ≤ $33. Its $6.25 cap must also fit under $40. For that, **I propose (for your approval) that a
  finished step counts at its actual spend, not its cap,** when the caps are re-summed.
- **Cut order if projections exceed the target:**
  1. D8, the large worker (already deferred).
  2. D7, hybrid.
  3. D3 and D4 from 50 to 30 questions each.
  4. D2 from 50 to 30 (keeping Costco).
  5. C1 from 35 to 21.

  C2 and C3 are not cut: they are the only dev evidence for fix A.

## 11. Test plan (Phase B, offline)

1. **Fix A:** weighted accounting units, Sonnet-only identity with M5, the D072 estimate, the
   A2 answer and run row, flags off → old error behavior, replay identical.
2. **Fix B:** the stall-guard scenarios listed in §2.2, the B2 message only for unknown names, B3
   not consuming the retry, flags off → M5 behavior, replay identical.
3. **Caching:**
   - breakpoint placement per role;
   - no cache for the verifier;
   - fingerprint unchanged when off;
   - cost with cache prices;
   - PricingError and preflight failure when cache prices are blank;
   - replay identical with recorded cache usage.
4. **Summary rule:** rounding and scale matches; uncited numbers still fail; plus the offline
   replay script over the M5 drafts.
5. **Default behavior unchanged:** under the new code with M5 flags, `filinglens.cli replay` on 20
   recorded M5 runs (including Costco, two handwritten no-answers and three revision runs) gives
   `identical` for all 20. This uses the DB but no LLM.
6. **Cache keys and frozen artifacts:**
   - the M5 configs' system and baseline hashes are pinned (e.g. `2672337d…`);
   - M6 configs hash differently;
   - SHA-256 checks of questions_v1, the manifest, subset180, handwritten_v2, both B2 metadata
     files, the new 50-sample and the explanatory dev file;
   - a before/after hash manifest of every M5 cache file.
7. **Report:** regenerating with the M5 configs reproduces report.md byte for byte; the new
   sections render from fixture records.
8. **Caps:** a test that the M6 configs (`budget = "m6"`) sum to ≤ $40 and each cap covers its
   reservations.
9. **Failure tooling:** `evals/failures.py` rules tested on synthetic trace fixtures. It
   reproduces the §1 counts from the DB (integration-gated).
10. **CI and smoke:**
    - smoke replay with no keys and no DB (env scrubbed), failing on a miss and below the
      threshold;
    - the clean-worktree dry run of the exact CI commands.
11. **Final checks:** ruff check, ruff format --check, full pytest with `FILINGLENS_TEST_DB=1`.

## 12. Choices for you

1. Approve fixes A1 + A2 and B1-B3, with **N = 2** for the stall guard.
2. Caching: fill in the cache read/write prices for `claude-sonnet-5-5` and `claude-haiku-5-5` in
   pricing.toml (with the source and date checked) before Phase C.
3. The summary rule (§3.2): keep it if the offline replay clears at least half the summary
   failures, or drop it now.
4. The explanatory dev prompts xd01-xd10: approve, or edit/replace any.
5. Cost plan: the base plan with caps summing to $40, the cut order, D7 as conditional, and
   counting finished steps at actual spend when re-summing caps.
6. CI install: without torch/CUDA (verified by the dry run), or the full lock.
7. Disney: a documented definition only (no v2 question set).

## Proposed decisions (DECISIONS.md, on approval)

- **D111 — M6 scope and dev/test discipline.** Fixes are mechanical and generic, behind flags,
  validated on dev for mechanics only. Explanatory dev validation is mechanical only (no
  references, no judge). The handwritten 30 are rerun once after the fixes are final, whatever
  the result. SPEC's "≥ 25 dev failures" is met as 133 failure events in 74 dev runs (0 wrong
  answers). Deviation stated: the budget and Costco failures behind fixes A/B were found on
  test in M5, so the test rerun measures fixes partly selected from test failures. The 18 unrun
  dev numeric questions are held as a fresh reserve for any further fix.
- **D112 — Failure taxonomy and method.** SPEC §13.6 categories plus: budget exhausted before a
  draft, budget stop after a draft, agent stall (≥ 2 no-progress steps), invalid final-answer
  tool, empty reply, untraced quant call, revision causes, passage cap, revision skipped, near
  budget, and data definition. Deterministic trace rules (no LLM). Spot checks: every run in
  categories ≤ 10, and a seeded 5 per larger category listed in the report.
- **D113 — Price-weighted run token budget.** Tokens × input price of the call's model ÷ input
  price of the planner model, all token kinds, from the run's price snapshot. Sonnet-only runs
  count exactly as before. Haiku workers weigh 0.05, so explanatory runs reach a draft. The cost
  cap, step limits and passage cap remain the bounds. Resolves the D082 question that D095
  deferred.
- **D114 — Budget stop before a draft gives an explicit answer.** Status not_available, no
  claims, a caveat naming the limit; runs.error records `stopped_without_draft`; still scored as
  "no answer (budget)".
- **D115 — No-progress guard, unknown-tool hint and empty replies.** After 2 consecutive steps
  whose results are all errors, duplicates or identical to earlier results, the next step is the
  D068 final step. Unknown tool names get a hint to answer as plain JSON. An empty reply gets the
  final-step guard without consuming the corrective retry. Deterministic and replayable.
- **D116 — Prompt caching.** Breakpoints on tools, system and the last message for multi-step
  roles; none for the verifier. Cache prices come from pricing.toml as filled in by the student.
  `LLMRequest.cache` is excluded from fingerprints when off. Token budgets count cache tokens as
  before (× model weight). Reports separate caching's dollar effect by repricing cache tokens as
  input.
- **D117 — Summary numbers may be rounded displays of cited values.** Stage 1 also accepts a
  summary number that rounds a cited fact value or a cited computation output, at its shown
  precision and scale. Adopted only if the offline replay over M5 drafts clears at least half the
  summary failures.
- **D118 — M6 changes behind RunConfig flags; M5 cache keys pinned.** Defaults reproduce M5
  behavior; no prompt file changes. M6 configs list their flags explicitly. Tests pin the M5
  config hashes and replay recorded M5 runs as identical.
- **D119 — Operating income definition.** `operating_income` is the tagged `OperatingIncomeLoss`
  fact; for Disney this is total segment operating income. Questions and gold are unchanged;
  reports show results with and without the Disney questions; no question set v2 now.
- **D120 — Explanatory dev set v1.** 10 prompts written by Claude, approved by the student, no
  references or gold chunks, no overlap of (company, filing, topic) with handwritten_v2. Frozen
  by SHA-256. Mechanical metrics only.
- **D121 — Ablation design.** −verifier and −quant on a frozen seeded 50-question test sample
  (7 per template + the Costco miss). +rerank (and conditionally −rerank) on the handwritten 30.
  Vector is the M6 default. All paired with the M6 system; statistical limits stated.
- **D122 — CI and replay smoke.** GitHub Actions: ruff check, ruff format --check, pytest (DB,
  model and live tests skipped by their gates), and a 10-question smoke that replays committed
  M6 records with no keys, DB or model downloads, failing on a cache miss or below the recorded
  accuracy. Public model IDs are set as workflow env vars. torch/CUDA are excluded if the
  clean-worktree dry run allows.
- **D123 — M6 cost plan.** $40 hard ceiling, ~$30 target. Caps as in §10, summing to $40; a
  finished step counts at its actual spend when re-summing. Projections are made at M5 rates
  before any spend. Stop at a cap or more than 20% over projection. The cut order is as in §10.
- **D124 — Deferred in M6.**
  - The open-model comparison (SPEC §13.5 item 3): skipped for now, with no key or account
    needed.
  - The large-vs-small worker swap: deferred for cost and confounded by D113.
  - The thinking-display diagnostic (D080/D082), adjacent-chunk IDs (D050/D061, an M3 server
    change), verified-quote numbers as quant inputs (D082), embedder preload (D071), real token
    counting for B2 contexts (D109), and the per-worker answer reserve (A3).

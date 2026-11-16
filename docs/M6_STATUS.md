# M6 status: experiments, improvement and CI

Status: **Phase D complete (2026-11-16); waiting for the student's acceptance.** M7 has not
started.

- **Plan and earlier phases:**
  [M6_PHASE_A.md](M6_PHASE_A.md), [M6_PHASE_B.md](M6_PHASE_B.md) and [M6_PHASE_C.md](M6_PHASE_C.md).
- **Decisions:** D111-D126.
- **Results:** the M6 sections at the end of
  [evals/results/report.md](../evals/results/report.md). The M5 sections above them are unchanged
  and still regenerate from the M5 cache alone (a test).

```
python -m evals.m6_report collect      # trace mechanics -> evals/results/m6_mechanics.json (DB)
python -m evals.report evals/configs/m5_test_subset.toml evals/configs/m5_test_opus.toml \
  evals/configs/m5_test_fable.toml evals/configs/m5_test_b2_subset.toml \
  evals/configs/m5_test_b1_subset.toml evals/configs/m5_probe.toml \
  evals/configs/m5_handwritten.toml --m6
```

## SPEC §16 M6 acceptance

| Criterion | Status |
|---|---|
| Ablations and model swaps run | −verifier, −quant tools, +rerank, −rerank (hybrid), with vector as the default. The large/small worker swap and the open-model comparison are deferred (D124) |
| ≥ 25 failures from dev categorized | 133 failure events in 74 of 100 dev-pilot runs (0 wrong answers on dev); categories, counts, 2 examples each and seeded spot-check lists in the report (D111, D112) |
| Top 2 failure causes fixed | (a) budget exhaustion before a draft: price-weighted budget plus an explicit no-draft answer (D113, D114); (b) agent stalls and invalid final-answer behavior: no-progress guard, unknown-tool hint, empty-reply guard (D115) |
| Test re-run; report shows before/after and the ablation table | Done; paired on identical questions; the M5 headline is unchanged |
| CI green | See "CI" below |

## Results

### Before/after on identical test questions (M5 accepted system vs final M6 system)

| | M5 | M6 | Paired test |
|---|---|---|---|
| Numeric test sample (50, frozen, includes the M5 Costco miss) | 98.0% (49/50) | **100.0% (50/50)** | +2.0 pp [+0.0, +6.0], exact McNemar p = 1.00 (1 discordant pair) |
| Costco trend_avg (the M5 test miss) | abstained, $0.425 | correct (exact gold), $0.093 | |
| $/question, numeric (50) | $0.159 | **$0.061** | −$0.098 [−$0.117, −$0.081] |
| Latency p50/p95, numeric | 17.5 s / 29.6 s | 19.3 s / 27.7 s | mean +1.1 s [+0.3, +1.8] |
| Handwritten 30 (run once): judge mean, no answer = 1 | 3.23 [2.73, 3.73] | **3.97 [3.63, 4.27]** | +0.73 [+0.27, +1.23]; higher on 12, lower on 2, exact sign test p = 0.013 |
| Handwritten: no-answers | 6/30 | **0/30** | exact McNemar p = 0.031 |
| Handwritten: mean over answered | 3.79 | 3.97 | |
| The 6 M5 no-answers under M6 | no answer | judged 4, 4, 4, 4, 5, 4 | |
| Handwritten $/question; latency p50/p95 | $0.179; 45 s / 80 s | $0.155; 61 s / 122 s | |
| System-level recall@5 / @10 (handwritten) | 0.500 / 0.552 | 0.486 / 0.523 | |

**Cost per question, separating caching** (cache tokens repriced as input give "M6 uncached"):

| Question set | M5 | M6 uncached | M6 (with caching) |
|---|---:|---:|---:|
| Numeric test (50) | $0.159 | $0.141 | $0.061 |
| Handwritten (30) | $0.179 | $0.229 | $0.155 |
| Dev numeric (35) | $0.138 | $0.140 | $0.062 |
| Dev explanatory (10) | $0.193 | $0.212 | $0.145 |

### Plain statements (as the student required)

- **(a) The cost saving is prompt caching; the other fixes were cost-neutral on dev.** On the 35
  dev numeric questions, M6 at uncached prices costs $0.140 vs M5's $0.138 (Δ +$0.002 [−0.007,
  +0.011]). On the handwritten set, M6 uncached costs more than M5, because the six formerly
  failing runs now finish with an analyst and verifier. With caching, M6 is cheaper on every set.
- **(b) The dev explanatory prompts did not reproduce the original budget failure.** The M5 system
  answered all 10, so the no-draft fix (A2, D114) and the budget fix's effect on no-answers are
  validated only by the handwritten test rerun: 6/30 → 0/30 no-answers. A2 itself never fired in
  the rerun, since no M6 run reached its budget before a draft. The price-weighted budget kept
  every run inside it; the formerly failing runs used up to 381K raw tokens.
- **(c) Dev validation for the explanatory fixes was mechanical only:** no references and no
  judge.
- **Selection caveat (D111):** the failures behind fixes A and B were found on test in M5, so this
  rerun measures fixes partly selected from test failures. The handwritten improvement is real on
  these 30 questions, but it is not a clean held-out estimate.
- **Latency:** M6 explanatory runs are slower (p50 61 s vs 45 s) because they now complete
  research that M5 cut off.

### Ablations (final M6 system, one flag changed, paired)

| Variant | Questions | Accuracy / judge | Δ vs M6 | Numeric citation validity | Text claims supported | Uncited model-arithmetic claims | $/question | Latency p50/p95 |
|---|---|---|---|---|---|---|---:|---|
| M6 system | numeric 50 | 100% | – | 100% (154/154) | no text claims | 0/154 | $0.061 | 19.3 s / 27.7 s |
| −verifier | numeric 50 | 100% | +0.0 pp, p = 1.00 | 100% (152/152) | no text claims | 0/152 | $0.039 | 16.1 s / 20.9 s |
| −quant tools | numeric 50 | 100% | +0.0 pp, p = 1.00 | 62.9% (88/140) | no text claims | **52/140** | $0.086 | 29.3 s / 40.7 s |
| M6 (vector) | handwritten 30 | judge 3.97; recall@10 0.52 | – | 100% (41/41) | 100% (145/145) | 0 | $0.155 | 61 s / 122 s |
| +rerank (hybrid_rerank) | handwritten 30 | judge 4.03; recall@10 0.60 | +0.07 [−0.23, +0.37] | 100% | 98.7% | 0 | $0.138 | 95 s / 147 s |
| −rerank (hybrid) | handwritten 30 | judge 4.00; recall@10 0.54 | +0.03 [−0.20, +0.30] | 100% | 97.2% | 0 | $0.157 | 59 s / 114 s |

**What the ablations show:**
- **−verifier and −quant matched the system's accuracy** on the 50 numeric questions (50/50 each).
  - Removing the verifier saves $0.021/question (35%) and 3 s at the median.
  - Removing the quant tools costs $0.026/question more (+43%) and 10 s at the median. The analyst
    writes about 65% more output tokens and caches less (D125), and 52 of its 140 numeric claims
    are model arithmetic with no computation citation, so Stage 1 cannot verify them.
- **What n = 50 can and can't show:** with the system at 100%, these ablations cannot show an
  accuracy effect. What they measure is cost, latency and verifiability.
- **Reranking:** it raised system-level recall@10 (0.52 → 0.60), but judge scores did not change
  beyond noise, and it adds about 34 s at the median. Vector stays the default (D044).

### Failure analysis

The report has category counts across M5 and M6, 2 examples per category and seeded spot-check
lists. Highlights:
- **Budget exhaustion before a draft:** 6 → 0.
- **Analyst corrective retries from empty replies:** M5 test subset 43 runs, M6 test sample 0.
  M6 still sees empty replies (10 of 50 runs), and the guard handles them.
- **Summary-number revisions:** 21 (M5 test, 180 runs) → 0 (M6 test sample, 50).
- **Stall guard:** fired in 20 of 50 M6 test runs; all of them ended correct.

## Spend

| Step | Projection | Spent | Cap |
|---|---:|---:|---:|
| C1 M6 dev numeric (35) | $5.36 (M5 rates) | $2.17 | $6.50 |
| C2 M5 system, explanatory dev (10) | $1.79 | $1.93 | $3.00 |
| C3 M6 system, explanatory dev (10) | $1.90 | $1.45 | $3.25 |
| D2 M6 numeric test sample (50) | $3.20 | $3.02 | $5.50 |
| D3 −verifier (50) | $2.30 | $1.97 | $4.00 |
| D4 −quant tools (50) | $3.00 | **$4.31** | $4.25, then $5.25 (D125) |
| D1 M6 handwritten 30 (once) | $5.25 | $4.64 | $8.50 |
| D1 judges | $0.35 | $0.40 | $1.00 |
| D5 +rerank, handwritten 30 | $5.25 | $4.15 | $6.00 |
| D7 −rerank (hybrid), handwritten 30 | $5.25 | $4.71 | $6.25 |
| D5 + D7 judges | $0.70 | **$0.84 (+21%)** | $1.90 |
| **M6 total** | | **$29.61** of $40 (target about $30) | |

**Two stop-rule events, both reported:**
1. **D4 hit its cap at 41/50.** Its re-projection ($0.06/question) was not grounded in a
   measured no-quant run. The student approved finishing it with a $5.25 total cap; the 41
   finished answers were served from cache (D125).
2. **The D5/D7 judge step ran 21% over its projection.** It was the last spending step, so there
   was nothing left to stop.

## Changes in M6 (code)

- **Runtime:** fixes behind RunConfig flags whose defaults are M5 behavior (D113-D117). No prompt
  file or MCP server changed. Twenty recorded M5 runs replay identically under the new code.
- **Evals:**
  - the explanatory dev split;
  - the frozen 50-question sample;
  - M6 configs with recorded actual spend;
  - judge plans;
  - the failure categorizer;
  - the summary-rule check;
  - the M6 report module;
  - the replay smoke test.
- **CI:** `.github/workflows/ci.yml`. Fixes found by the Linux reproduction are in D126.
- **Tests:** new M6 tests (runtime and evals). The M5 cache keys are pinned, and the M5 report
  regenerates byte for byte.

## CI

**Green on GitHub** for `cf4bb5b`:
[run 43973718784](https://github.com/srikarnandigama/filinglens/actions/runs/43973718784).
All steps passed: install (locked, without torch/CUDA), ruff check, ruff format --check, pytest
and the eval smoke test (10/10 M6 records replayed, threshold 1.0).

**History.** The Phase B and C commits had failed CI at pytest. Reproducing the run in a Linux
container found one real Linux-only failure, a hard-coded Windows interpreter path in a stdio
test, now fixed (D126).

**Local checks before the push:**
- full pytest with `FILINGLENS_TEST_DB=1`: 308 passed, 2 skipped (the opt-in live LLM and
  corpus-replay tests);
- the same CI commands in `python:3.12-slim`: 238 passed, 72 skipped (the gated DB, model, raw
  data, corpus-replay and live tests; per-module list in the workflow file); smoke test 10/10.

**One GitHub annotation, a warning, not a failure:** `actions/checkout@v4` and
`astral-sh/setup-uv@v6` target Node.js 20, which GitHub now runs on Node.js 24.

## Known limitations and what M6 does not show

- **Accuracy headroom on numeric questions is gone** (M5 99%, M6 100% on the 50-question sample).
  The numeric before/after and the ablations mostly measure cost, latency and verifiability.
  None of the accuracy differences is statistically significant.
- **The handwritten gain is a test result on fixes partly chosen from test failures** (D111),
  judged by the same Opus judge and rubric (calibration κ 0.98, D110). Calibration covered judge
  scores 2-5 only.
- **Explanatory runs now use more raw tokens and time:** up to 381K raw tokens and 2-4 minutes on
  multi-filing questions. The cost cap ($0.50) and step limits bound them.
- **Retrieval misses remain common** on the handwritten set (13/30 runs saw no gold chunk; the
  gold labels are not exhaustive). Reranking helps recall but not the judged answers.
- **Deferred (D124):**
  - the open-model comparison (no key or account needed until scheduled);
  - the large-vs-small worker swap;
  - the thinking display;
  - adjacent-chunk IDs (an M3 server change);
  - verified-quote quant inputs;
  - embedder preload;
  - real token counting for B2.

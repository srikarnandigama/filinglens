# M5 Phase B: offline build and question generation

Status: implemented, draft generated, **not frozen**. No LLM calls were made. The question
set is frozen (`python -m evals.generate freeze`) only after the student reviews
[M5_REVIEW_SAMPLE.md](M5_REVIEW_SAMPLE.md) and approves D097.

**Approved 2026-11-11:** the student verified all 20 review-sample golds against the linked
filings with no discrepancies, and approved D097 and D101. D101 is approved including comparison's 14.5%
after-cutoff share (8 of 55, pool-limited under D086) and JPM's absence from the
100-question sample; both are also stated in the report notes (`evals/report.py`).
`BASELINE_MODELS` now comes from `RuntimeSettings` (D102), not python-dotenv.

**Revised 2026-11-09 (D101):** comparison questions are now same-sector only (GICS). Only the
comparison records changed; the other six templates are byte-identical to the previous draft
(`9dac9d32...`), including their splits and sample membership. Figures below are for the revised draft.

## What was built

| File | Purpose |
|---|---|
| `evals/generate.py` | Gold generation from `financial_facts` with Decimal (prec 80, ROUND_HALF_EVEN), fairness metadata, balanced selection with a 20% post-cutoff floor, 30/70 split, frozen 100 sample, probes, freeze/manifest (D083-D086) |
| `evals/answers.py` | Shared answer contract and prompts; robust last-JSON parser (D087) |
| `evals/scorers.py` | Unit normalization, tolerances, outcome classes, bootstrap/McNemar/Holm/kappa (D085, D094) |
| `evals/b2_context.py` | B2 statements windows from the frozen raw snapshot, 25K/filing and 50K/question caps, gold-visible flag, hash-verified frozen loader (D089, D100) |
| `evals/baselines.py` | B0/B1/B2 request builders, real-time and Batch API paths, pause_turn continuation, cost (D087, D088) |
| `evals/system_adapter.py` | Runs the accepted M4 system unchanged and maps Answer → prediction, comparison choice, offline citation checks, trace retrieval recall (D091, D092, D095, D099) |
| `evals/runner.py` | TOML configs, seeded interleaved schedule, disk cache keyed by config hash + question (text-checked, atomic), per-invocation spend cap with reservations, retries, `--replay-only` (D090, D098) |
| `evals/judge.py` | Rubric and claim judges (prompt builders and parsers), calibration sample, blind export, agreement (D093) |
| `evals/report.py` | `report.md` from cached records only |
| `evals/configs/*.toml` | `m5_dev_pilot` ($20), `m5_test_full` ($46), `m5_test_sample` ($9), `m5_probe` ($2), `m5_handwritten` ($10); with $3 for the judge, $70 for the test run |

## Generated set (draft)

- `evals/questions_v1.draft.jsonl`: 410 records = 400 benchmark questions + 10 abstention probes.
  SHA-256 `4f270e35634a4fa3aa86e9bf75e40933bacfa14169188ecf2c4634cb69e6b1cb`. Generation was run
  twice with identical bytes.
- Seed 20261109; generator `gen-v1`; snapshot 2026-10-19-v1.
- Frozen 100 sample (test only) ID-list SHA-256
  `292582e3214ec807db85b9043020cfdb3360c47fe3c7019fd138a97c7e196049`.
- `evals/b2_contexts_v1.meta.jsonl` (100 rows) SHA-256
  `902e5a7a0c81e3f743e7c61e440dc7900eec11ef24b81fef3e06be28606f7846`.

### By template

| Template | Total | Dev | Test | Sample 100 | After cutoff | Restated | Uses derived quarter |
|---|---|---|---|---|---|---|---|
| lookup | 60 | 18 | 42 | 15 | 14 | 0 | 0 |
| yoy_growth | 60 | 18 | 42 | 15 | 12 | 3 | 0 |
| margin | 60 | 18 | 42 | 15 | 15 | 1 | 10 |
| trend_avg | 55 | 16 | 39 | 13 | 11 | 1 | 55 |
| derived_q4 | 55 | 16 | 39 | 14 | 11 | 0 | 55 |
| comparison | 55 | 16 | 39 | 14 | 8 | 4 | 0 |
| multi_step | 55 | 16 | 39 | 14 | 11 | 2 | 55 |
| **Total** | **400** | **118** | **282** | **100** | **82** | **11** | **175** |

- Cutoff buckets (both models have a Jun 2026 cutoff, D096): 318 before, 0 in June, 82 after.
  Every template except comparison meets the 20% after-cutoff floor (11/55 is exactly 20%).
  Comparison has 8 after-cutoff (14.5%): the same-sector pool holds only 8, all taken (the floor
  applies "where the pool allows", D086). After-cutoff: 59 test, 23 dev, 26 in the sample.
- As generated, the after-cutoff share is 20.5% (82/400). The report labels overall
  after-cutoff results "with the D086 floor".
- Units: 175 percent, 164 USD, 55 percentage points (comparison), 6 USD/share (EPS).
- 345 single-company questions; 55 two-company questions (comparison), all same-sector (D101).

### Comparison by sector (D101, GICS)

| Sector | Pool | Selected | Gross | Operating | Net | After cutoff (pool) |
|---|---|---|---|---|---|---|
| Information Technology (AAPL, MSFT, NVDA) | 21 | 10 | 7 | 2 | 1 | 3 |
| Communication Services (GOOGL, META, DIS) | 18 | 10 | 0 | 9 | 1 | 0 |
| Consumer Discretionary (AMZN, TSLA, NKE) | 12 | 10 | 2 | 3 | 5 | 0 |
| Consumer Staples (WMT, COST, KO, PG) | 28 | 11 | 0 | 9 | 2 | 5 |
| Health Care (JNJ, PFE, UNH) | 9 | 9 | 0 | 0 | 9 | 0 |
| Financials (JPM, BAC) | 3 | 3 | 0 | 0 | 3 | 0 |
| Energy (XOM, CVX) | 2 | 2 | 0 | 0 | 2 | 0 |
| **Total** | **93** | **55** | **9** | **23** | **23** | **8** |

Pools by margin type: gross 9 (IT 7, Consumer Discretionary 2), operating 43, net 50. The
sector-first greedy fills sectors evenly until a small pool runs out (Energy, Financials, Health
Care take everything); every gross-margin candidate is selected. JPM has no question in the frozen
100-question sample.

### By company (benchmark questions; comparison counts toward both companies)

| Company | Total | Dev | Test | Sample | After cutoff |
|---|---|---|---|---|---|
| AAPL | 23 | 6 | 17 | 10 | 2 |
| AMZN | 24 | 3 | 21 | 9 | 1 |
| BAC | 18 | 3 | 15 | 4 | 1 |
| COST | 24 | 5 | 19 | 8 | 16 |
| CVX | 19 | 5 | 14 | 3 | 0 |
| DIS | 23 | 8 | 15 | 5 | 2 |
| GOOGL | 23 | 13 | 10 | 3 | 2 |
| JNJ | 23 | 7 | 16 | 9 | 1 |
| JPM | 15 | 3 | 12 | 0 | 0 |
| KO | 21 | 6 | 15 | 8 | 0 |
| META | 25 | 9 | 16 | 5 | 1 |
| MSFT | 26 | 11 | 15 | 6 | 16 |
| NKE | 24 | 5 | 19 | 6 | 17 |
| NVDA | 27 | 7 | 20 | 7 | 6 |
| PFE | 23 | 7 | 16 | 5 | 0 |
| PG | 24 | 7 | 17 | 8 | 17 |
| TSLA | 25 | 4 | 21 | 7 | 1 |
| UNH | 23 | 8 | 15 | 3 | 1 |
| WMT | 25 | 9 | 16 | 4 | 6 |
| XOM | 20 | 8 | 12 | 4 | 0 |

**Caveat for the cutoff breakdown:** after-cutoff questions are concentrated in the companies
whose fiscal years end mid-year (NKE, MSFT, PG, COST, NVDA; FY2026 annual reports filed after
June 2026). The before/after comparison is therefore confounded with company and will be
reported as descriptive only, with this note.

### Fairness flags

- **Restated (11):** gold differs when recomputed from the earliest-filed observations; the
  record keeps `gold_as_first_reported`. Comparisons 4, yoy_growth 3, multi_step 2, margin 1, trend_avg 1. There are too few for inference,
  so this breakdown is descriptive.
- **Derived (175):** uses at least one M1 derived quarter (Q4 = FY − 9M, or Q2/Q3 from
  year-to-date differences).
- **Mixed vintage (proposed D097):** 13 derived facts subtract a restated FY from an original
  9M (BAC FY2024 revenue: 101,887M first reported, 105,856M in the 2026 10-K). These
  "quarters" were never reported in any filing, so they are excluded from generation behind
  `EXCLUDE_MIXED_VINTAGE`. This exclusion reduces restated questions from 18 to 11 (21 to 14 before D101).
  **Approval needed.**

### Abstention probe (10, outside the headline)

- 6 not_applicable: BAC/JPM gross profit and gross margin (the D042 bank overlay).
- 4 unavailable: BAC/JPM operating income, FY2025 and Q4 2025.
- Scored on status: not_applicable or not_available counts as a correct abstention.

### B2 contexts (frozen-sample metadata)

- 84 filings are read from the frozen raw snapshot, with 0 fallback windows.
- Gold is visible in 97 of 100 contexts:
  - DIS operating income is not printed on Disney's income statement.
  - A BAC cash-flow value lies beyond the 25K cap.
  - One MSFT R&D input is lost to truncation.
- 3 contexts were truncated at the 50K cap.
- Tokens (chars/4): p50 5.5K, p90 27.7K, max 50.0K, mean 12.0K.
- The mean is well under the Phase A cost assumption, so the B2 line in §8 is an upper bound.
  It will be re-projected from the dev pilot.
- Heading detection was fixed during Phase B (D100). Microsoft's markup splits
  "INC OME STATEMENTS", and an accounting-policy note titled "Income Statement - …" was being
  taken as the statements start.

## Defects found and fixed in Phase B

1. **Cache-key collision (D098):** indexed baselines hashed a blank model ID, so B0 Sonnet and
   B0 Opus would have shared cached answers. The runner now hashes the resolved ID and refuses a
   blank one. A regression test covers it.
2. **Recall over 1 (D099):** system recall@k with several workers could exceed 1. The
   denominator now scales with the number of workers.
3. **B2 heading detection (D100):** see above. Gold visibility went from 94 to 97.
4. **B2 ordering:** direct facts carry `source_filed`, so contexts list filings newest first.

## Review sample

[M5_REVIEW_SAMPLE.md](M5_REVIEW_SAMPLE.md) has 20 questions:
- 3 per template (2 for multi_step), across 13 companies, 12 from test and 8 from dev.
- Coverage: 7 after-cutoff, 2 restated, 1 EPS and 4 bank questions.
- Each lists the gold, tolerance, fact IDs, formula, every input (with derivation inputs),
  concept, accession, filed date and SEC URL.
- An independent Decimal recomputation from the listed inputs matches all 20 golds.

## Needs approval or input before Phase C

1. **D097**, the mixed-vintage exclusion (above), and **D101**, same-sector comparisons (GICS).
2. **python-dotenv:** `evals/runner.py` imports `dotenv_values` to read `BASELINE_MODELS` from
   `.env` when it is not in the process environment or Settings. It is already installed (a
   dependency of pydantic-settings, in `uv.lock`) but is not listed in SPEC §3. The alternative
   is to add `baseline_models` to Settings. Please approve one.
3. **pricing.toml** additions, filled in by the student:
   - Opus 5.5 prices;
   - `[tools.web_search] usd_per_1000`;
   - `[eval] batch_multiplier`.
   The runner's preflight refuses to start without them.
4. **.env:** `BASELINE_MODELS=claude-sonnet-5-5,claude-opus-5-5` (index 0 is Sonnet, 1 is Opus).
   The preflight checks key names only.

## Checks

See the final report for this phase: ruff check, ruff format --check and full pytest, with
`FILINGLENS_TEST_DB=1`.

# M6 Phase C — dev validation

Status: **Phase C complete (2026-11-15). Stopped for the student's Phase D go-ahead.**

- **Before any run:** D117's `summary_cited_values` was enabled in every M6 system config; the M6
  system's cache key is now `52a48e08…`, the same across all its splits.
- **Preflight:** passed (no cost).
- **No code changes** were made in Phase C.
- **Scope of the evidence:** dev only. For the explanatory prompts, the evidence is mechanical
  only (D111): no references, no judge, no quality claim.

## Spend

| Step | Run | Projection (M5 rates) | Spent | vs projection | Cap |
|---|---|---:|---:|---:|---:|
| C1 | M6 system, 35 dev numeric (paired with M5 dev pilot) | $5.36 | **$2.17** | −60% | $6.50 |
| C2 | M5 system, xd01-xd10 | $1.79 | **$1.93** | +7.8% | $3.00 |
| C3 | M6 system, xd01-xd10 | $1.90 | **$1.45** | −24% | $3.25 |
| | **Phase C** | $9.05 | **$5.55** | | $12.75 |

No step hit its cap or ran more than 20% over its projection. All 55 runs completed (`done`).

## 1. M6 vs M5 on the same 35 dev numeric questions

The questions are 5 per template, drawn seeded from the dev pilot. The M5 numbers are its cached
dev-pilot records.

| | M5 | M6 |
|---|---:|---:|
| Accuracy | 35/35 | 35/35 (exact McNemar: 0 discordant pairs) |
| $/question | $0.138 | **$0.062** |
| $/question if M6's cache tokens were billed as input | | $0.140 |
| Tokens per run (raw = price-weighted; no Haiku in numeric runs) | 58.8K | 60.4K |
| Cache read / write tokens per run | 0 / 0 | 43.3K / 7.8K |
| Latency p50 / p95 | 16.7 s / 30.9 s | 18.0 s / 31.6 s |
| Runs needing a revision | 6 | 5 (trend_avg 5 → 2) |
| Analyst corrective retries | 7 (in 7 runs) | 1 |
| Empty replies | 6 | 12 (all caught by the B3 guard; 11 runs) |
| Stall guard (no progress) | — | 5 (planner 2, analyst 3) |
| Invalid-tool calls | 1 | 1 |
| Untraced quant calls | 15 | 14 |

- **Cost.** The paired difference is −$0.076 [−0.089, −0.063]. M6 uncached vs M5 is +$0.002
  [−0.007, +0.011]. So **the whole cost reduction comes from prompt caching**; at uncached prices
  the fixes are cost-neutral on this sample.
- **Latency.** The paired difference is −0.2 s [−2.0, +1.1]: unchanged.
- **Template costs.** M6 vs M5 per question:

  | Template | M5 | M6 |
  |---|---:|---:|
  | trend_avg | $0.226 | $0.090 |
  | comparison | $0.165 | $0.084 |
  | multi_step | $0.152 | $0.062 |
  | margin | $0.132 | $0.053 |
  | yoy_growth | $0.129 | $0.057 |
  | derived_q4 | $0.085 | $0.050 |
  | lookup | $0.076 | $0.038 |
- **Guards.** Every run where a guard fired ended correct. Empty replies were more frequent in this
  M6 sample (12 vs 6); with n = 35 this is not distinguishable from run-to-run variation, and each
  one now costs a guarded final step instead of the single corrective retry.

## 2. Explanatory dev prompts xd01-xd10 (mechanical only)

| | M5 system | M6 system |
|---|---:|---:|
| Answered / no answer | 10 / 0 | 10 / 0 |
| answered / partially_answered | 6 / 4 | 9 / 1 |
| Raw tokens per run: mean, max | 140K, 185K | 148K, **259K** |
| Price-weighted tokens per run: mean, max | 72.9K, 112K | 79.1K, 157K |
| Runs over 200K raw tokens | 0 | 2 (xd04 201K, xd10 259K) |
| $/question | $0.193 | **$0.145** |
| $/question if cache tokens were billed as input | | $0.212 |
| Latency: mean, max | 66 s, 102 s | 63 s, 143 s |
| Cache read / write tokens per run | 0 / 0 | 84.4K / 36.2K |
| Filings workers; passages read (total) | 13; 51 | 12; 49 |
| Stall guard (no progress) | — | 2 (xd03 planner, xd10 analyst) |
| Empty-reply guard / empty replies | — / 1 | 0 / 0 |
| Invalid-tool calls (hint shown) | 0 | 0 |
| Corrective retries | 5 | 3 |
| Verifier rounds (per prompt) | 1,1,2,2,3,2,1,1,2,1 | 1,1,2,3,2,1,1,1,2,3 |
| Revisions skipped for budget (D072) | 2 (xd06, xd10) | 0 |
| Budget finalized / stopped without draft | 0 / 0 | 0 / 0 |

**What this shows, and what it does not:**
- **No dev evidence for the no-draft failure.** The M5 system answered all 10, so these prompts did
  not reproduce the handwritten budget exhaustion; they planned 1-2 filings workers, where the six
  M5 handwritten no-answers had 1-5.
- **Indirect evidence for fix A1.** Two M6 runs went past 200K raw tokens (xd04, xd10) and
  completed their revisions within the price-weighted budget. Under M5 counting they would have
  been cut short, and M5 skipped two revisions for budget on this set. Cost stayed under the
  per-run cap (max $0.31 of $0.50).
- **Why uncached cost is higher.** M6's uncached cost ($0.212) is above M5's ($0.193) because M6
  completed more revision rounds. Caching brings it to $0.145.
- **Answer quality was not measured** (no references, no judge).

## 3. Failure categorization update (D112 rules)

| Category | M5, same 35 dev numeric | M6, 35 dev numeric | M5, xd01-10 | M6, xd01-10 |
|---|---:|---:|---:|---:|
| Planner stall (≥ 2 no-progress steps) | 2 | 2 (guard fired) | 0 | 1 (guard fired) |
| Analyst stall | 0 | 3 (guard fired) | 0 | 1 (guard fired) |
| Invalid final-answer tool | 1 | 1 | 0 | 0 |
| Empty reply | 6 | 11 | 1 | 0 |
| Corrective retry: analyst | 6 | 0 | 1 | 1 |
| Corrective retry: planner / filings / verifier | 0 / 0 / 1 | 1 / 0 / 0 | 0 / 3 / 1 | 0 / 2 / 0 |
| Untraced quant call | 15 | 13 | 2 | 1 |
| Revision: summary numbers (Stage 1) | 5 | **1** | 0 | 0 |
| Revision: unsupported caveat | 2 | 4 | 1 | 2 |
| Revision: unsupported claim | 0 | 0 | 3 | 3 |
| Revision skipped for budget | 0 | 0 | 2 | 0 |
| Partially answered | 0 | 0 | 4 | 1 |
| Filings passage cap hit | — | — | 3 | 4 |
| Near budget (> 150K raw tokens) | 0 | 0 | 4 | 2 |

- **M6 dev totals:** 71 failure events in 33 of 45 runs. Most are guard events (expected, by
  design) and untraced quant calls.
- **M5 baseline:** the dev-pilot categorization (133 events in 74 of 100 runs, D111) stands.

## 4. Measured cost per question with caching vs M5

| Question type | M5 | M6 measured | M6 at uncached prices | Phase A estimate |
|---|---:|---:|---:|---:|
| Numeric (dev) | $0.138 (same 35) / $0.152 (dev pilot) | **$0.062** | $0.140 | ~$0.09 |
| Explanatory (dev) | $0.193 | **$0.145** | $0.212 | ~$0.16 |

Numeric caching beat the estimate. Sonnet's cache read price is 0.05× input, not the 0.1× assumed
in Phase A, and the analyst's many short steps re-read a cached prefix.

## 5. Phase D re-projection (measured M6 rates)

**Rates used:**
- Numeric: $0.064 (dev $0.062 × M5's test/dev ratio 1.04).
- −verifier: about $0.045 (no verifier calls or revisions).
- −quant: about $0.06, conservatively (one analyst call, no tool steps).
- Handwritten: 24 runs at the dev explanatory rate ($0.145, adjusted ≈ $0.143), plus the 6
  formerly failing multi-worker runs, which now continue, at about $0.30 each (xd10-like):
  ≈ $5.23 per config (~$0.174/q).
- Judges: about $0.35 per handwritten config.

| Step | n | Re-projection | Cap |
|---|---:|---:|---:|
| D1 M6 handwritten 30 (once) | 30 | $5.25 | $6.00 |
| D2 M6 numeric test sample | 50 | $3.20 | $5.50 |
| D3 −verifier | 50 | $2.30 | $4.00 |
| D4 −quant tools | 50 | $3.00 | $4.25 |
| D5 +rerank (hybrid_rerank), handwritten | 30 | $5.25 | $6.00 |
| D6 judges (D1, D5) | | $0.70 | $1.50 |
| **Phase D base** | | **$19.70** | $27.25 |
| D7 −rerank (hybrid) + its judge items (conditional) | 30 | $5.60 | $6.25 |

**Totals against the budget:**
- M6 spent: **$5.55** of the $40 ceiling. Remaining: $34.45.
- Base plan: spent + Phase D base = **$25.25** (target about $30).
- With D7: **$30.85**. That is under D123's $33 gate, and the re-summed caps (Phase C at actual
  spend $5.55 + $27.25 + $6.25) = **$39.05**, under $40. **D7 qualifies under the approved rule.**
  Running it is your decision with the Phase D go-ahead. If it runs, D6's judge plan gains its
  config; the $1.50 judge cap covers three configs at about $0.35 each.
- **Stop rules in Phase D:** a step stops if it hits its cap or runs more than 20% over the
  re-projection above.

## Notes

- **Cache records.** C2's 10 records were added to the M5 system's cache folder (`2672337d…`) as
  new files; no existing M5 record changed (D118). The M6 system's 45 records are in `52a48e08…`
  (280 KB).
- **pricing.toml.** The working copy still shows `checked = 2026-10-22` for `claude-sonnet-5-5`
  and `claude-haiku-5-5`. Your update may not have been saved. The cache prices themselves are
  present.
- **Not committed.** Phase C changes: the D117 flag in 7 configs, the D117 decision text, one
  test assertion, this file, and the new cache records.

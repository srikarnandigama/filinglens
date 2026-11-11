# M5 Phase C: preflight, dev pilot and the cost gate

Status (2026-11-11): question set frozen; dev pilot done; **test run not started**, waiting on
the student's gate decision (below). No prompt or system-behavior change has been made from dev
results.

## Frozen set

- `evals/questions_v1.jsonl` SHA-256 `4f270e35634a4fa3aa86e9bf75e40933bacfa14169188ecf2c4634cb69e6b1cb`
  (400 questions + 10 probes; 118 dev, 282 test), manifest `evals/questions_v1.manifest.json`.
- 100-question sample ID list SHA-256 `292582e3214ec807db85b9043020cfdb3360c47fe3c7019fd138a97c7e196049`.
- B2 metadata SHA-256 `902e5a7a0c81e3f743e7c61e440dc7900eec11ef24b81fef3e06be28606f7846`.
- Seed 20261109, generator gen-v1, snapshot 2026-10-19-v1. Review sample verified by the student
  with no discrepancies; D097 and D101 approved.

## Preflight (`python -m evals.runner <config> --preflight`, D102)

API key set; frozen hash OK; Sonnet 5.5, Haiku 5.5 and Opus 5.5 resolve from Settings, are
priced and accessible (`models.retrieve`, no generation); web-search and batch prices present;
2,715 facts for the snapshot. Web search enabled for the organization (student).

## Dev pilot (system + B0 Sonnet, 100 stratified dev questions, cap $20)

Spent **$15.94** (system $15.21, B0 Sonnet $0.72); 200/200 answered; no errors, no cap stop.
The run hung at shutdown and was stopped by hand; its summary was rebuilt from the cache
(`evals/results/runs/m5-dev-pilot-reconstructed.json`). Runner fixes: D103.

| | System | B0 Sonnet 5.5 |
|---|---|---|
| Accuracy [95% bootstrap CI] | 100.0% [100, 100] (100/100) | 44.0% [34.0, 53.0] (44/100) |
| lookup / yoy / margin | 15/15, 15/15, 15/15 | 6/15, 8/15, 6/15 |
| trend_avg / derived_q4 | 13/13, 14/14 | 7/13, 4/14 |
| comparison / multi_step | 14/14, 14/14 | 11/14, 2/14 |
| Before / after cutoff | 79/79, 21/21 | 41/79, 3/21 |
| Abstained / parse failures / unit rescues | 0 / 0 / 0 | 2 / 0 / 0 |
| $/question ($/correct) | $0.152 ($0.152) | $0.0072 ($0.0165) |
| Latency p50 / p95 | 18.7 s / 30.9 s | 4.5 s / 14.5 s |
| Budget-finalized / revision-skipped | 0 / 0 | – |

Paired: system-only correct 56, B0-only 0 (exact McNemar p = 2.8e-17). Per-template cells have
n = 13-15 and are descriptive. Numeric citation validity (Stage 1 rerun offline): 301/301.

**System cost by role** (from traces; the Haiku filings workers were never called on these
numeric questions): analyst 45% ($0.069/run, 3.6 calls, 29K input tokens), planner 40% ($0.062,
3.1 calls, 26K input), verifier 14% ($0.022, 1.2 calls). By template: lookup $0.081, derived_q4
$0.089, margin $0.135, yoy_growth $0.155, comparison $0.185, multi_step $0.207, trend_avg $0.224.
25 runs needed one verifier revision (1 needed two), 11 of them trend_avg: the analyst's summary
quotes figures (quarterly values, growth) that are not claims, which Stage 1 rejects. Other
revisions came from unsupported caveats (e.g. seasonality, "52-week year"). Input tokens averaged
63K per run (max 135K of 200K).

## Test-run projection and the §8 gate (measured rates)

System test split: $43.1 (bootstrap 95% $41.3-44.9, $0.153/q). Unmeasured items keep Phase A
estimates: system handwritten $7.5 (30 × $0.25), probe $0.8, B1 $6.5, judges $2.8. B0 Opus is
projected at 2 × B0 Sonnet's measured tokens (same tokenizer). B2 uses the measured 12.0K-token
mean context.

| Item | Expected |
|---|---:|
| System: test 282 / probe 10 / handwritten 30 | $43.1 / $0.8 / $7.5 |
| B0 Sonnet (test, probe, handwritten) | $2.6 |
| B0 Opus (test, probe, handwritten) | $5.1 |
| B1 Sonnet batch (100) / B2 Sonnet batch (100) | $6.5 / $1.7 |
| Opus judge (90) + text-claim judge | $1.8 + $1.0 |
| **Total** | **$70.1** (over the $60 gate) |
| After cut 2 (no B0 Opus on handwritten, −$1.5) | $68.6 |
| After cut 3 (B0 Opus on the 100 sample, −$2.6) | $66.0 |
| After cut 4 (B1 max_uses 3, ≈ −$2.0) | $64.0 (still over $60) |

Options needing the student's decision (system on the 100 sample plus a stratified share of the
other 182 test questions, with cuts 2-4):

| Option | System test n | System $ | Test-run total | B0-like CI half-width | System lower bound if all correct |
|---|---:|---:|---:|---:|---:|
| A | 254 (100 + 154) | $38.8 | $59.7 | ±6.1 pp | 98.6% |
| B | 220 (100 + 120) | $33.6 | $54.5 | ±6.6 pp | 98.3% |
| C | 180 (100 + 80) | $27.5 | $48.4 | ±7.3 pp | 98.0% |
| Full 282 (no gate) | 282 | $43.1 | $64.0 | ±5.8 pp | 98.7% |

Whatever is chosen, the per-config caps in `evals/configs/` must be re-split to match (the
current `m5_test_full` cap of $46 is below system + both B0s on the full split, ≈ $49).

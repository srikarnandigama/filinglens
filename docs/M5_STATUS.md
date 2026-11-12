# M5 status: eval harness and baselines

Status (2026-11-11): **all approved runs are done; waiting for the student's review and the 20
blind judge labels.** Nothing from M5 is committed yet. The report is
[evals/results/report.md](../evals/results/report.md) (generated from the cache with
`python -m evals.report <configs>`; analysis notes in `evals/results/report_notes.md`).

## Results (test split)

On the frozen 100-question sample (every system answers the same questions):

| System | Data access | Accuracy [95% CI] | $/question |
|---|---|---|---:|
| FilingLens system | XBRL facts + filing passages (MCP tools) | 99.0% [97.0, 100] | $0.157 |
| B2 Sonnet 5.5 | gold filings' statements in context | 96.0% [92.0, 99.0] | $0.024 (batch) |
| B1 Sonnet 5.5 | open web search | 90.0% [84.0, 95.0] | $0.047 (batch) |
| B0 Fable 5.2 | none (closed book) | 69.0% [60.0, 78.0] | $0.024 |
| B0 Opus 5.5 | none | 55.0% [45.0, 65.0] | $0.013 |
| B0 Sonnet 5.5 | none | 42.0% [32.0, 52.0] | $0.008 |

On the 180-question subset: system 99.4% [98.3, 100], B2 95.6%, B1 85.0%, B0 Sonnet 42.8%.

Paired tests (exact McNemar, Holm):

- **vs B1 and every B0:** the system is significantly better, p < 0.0001.
- **vs B2:** +3.9 pp, p = 0.039. This depends on 3 Disney operating-margin questions where the
  gold uses Disney's segment operating income. Without them: +2.3 pp, p = 0.22, not significant.

Other results:

- **Abstention probe:** system 10/10, B0 Sonnet 7/10, B0 Opus 7/10.
- **Handwritten set (Opus judge, 1-5):** system 3.79 over its 24 answers, 3.23 with the 6
  no-answer runs scored 1; B0 Sonnet 3.23 (0 no-answers).
- **System text claims:** 98 of 102 supported (80 by string match, 18 by the judge).
- **System-level retrieval:** recall@5 0.500, recall@10 0.552.

## What M5 shows, and what it does not

- **What system accuracy measures (D104).** It measures planning, period mapping, arithmetic and
  formatting over correct structured data, not extraction: the gold and the system read the same
  `financial_facts`. The student verified all 20 review-sample golds against the filings
  and/or earnings releases, with no discrepancies.
- **B2 is the fair comparison, and it is close.** Given the gold filings' statements, Sonnet 5.5
  answers 95.6-97.2% at about a sixth of the system's cost per question (batch prices).
- **Closed-book models know pre-cutoff figures surprisingly well** (Fable 90.5% before the cutoff)
  and almost nothing after it (0-8%).

## Failures and limitations found

- **6/30 handwritten system runs gave no answer (D108).** They used up MAX_RUN_TOKENS before any
  draft existed, so D073 finalization could not apply. The D095 assumption that budget stops
  always end as partial answers was wrong for this case.
- **The one test abstention (Costco trend_avg) was an error, not a data gap.** The run computed
  the exact gold. Then the planner repeated `list_available_metrics` 6 times and the analyst
  tried 5 times to answer through a nonexistent `json` tool, until the budget ran out.
- **The Disney operating-income definition is ambiguous** (segment measure, 3 questions).
- **"Gross margin" is ambiguous for Apple and Microsoft,** whose statements use it for the
  dollar line (2 B2 answers).
- **B1 quotes as-first-reported values** for restated facts (5/6 restated wrong, all matching the
  original values).
- **B2 contexts were sized in characters/4,** about 1.9x below real tokens, so the D089 limits
  were looser than stated and B2's first batch overran its cap ($2.42 against $2.00, D109).

## M6 candidates (D106, D108)

1. Prompt caching.
2. The trend_avg summary/claim revision loop.
3. Finalizing runs that hit the budget before a draft exists.
4. Capping filings-worker passage reading or tokens per worker.
5. Limiting planner calls.
6. The analyst answering through a tool instead of the Answer.

The 6 no-answer handwritten questions are to be rerun in M6 after the fixes.

## Spend

| Phase | Spent | Cap |
|---|---:|---:|
| Dev pilot (system + B0 Sonnet, 100 dev) | $15.94 | $20.00 |
| D105 test steps (subset, Opus, probe, handwritten, B2 sample) | $40.05 | $60.00 |
| D109 (Fable, B2 +80, B1 pilot + 165, judges) | $13.47 | $30.00 |
| **Total M5** | **$69.48** | |

Every step was checked against its projection; two stop rules fired and were resolved by the
student: the handwritten budget errors (D108) and B2's +39% overrun (D109).

## Artifacts

- **Question set:** `evals/questions_v1.jsonl` (`4f270e35...`, frozen) and the manifest.
- **Test subset:** `evals/questions_v1.subset180.json` (`242fbea0...`).
- **B2 metadata:** `evals/b2_contexts_v1.meta.jsonl` (`902e5a7a...`) and
  `evals/b2_contexts_v1.subset_extra.meta.jsonl` (`087724b6...`).
- **Configs:** `evals/configs/` (D105 and D109; caps enforced by tests).
- **Cache:** `evals/cache/` (all answers and judge results; the report replays it with no API
  calls). Run summaries are in `evals/results/runs/`.
- **Calibration sheet:** `docs/M5_JUDGE_CALIBRATION.md` and
  `evals/results/judge_calibration_blind.jsonl`. Enter a 1-5 `student_score` per key; the report
  then shows agreement and κ.
- **Decisions:** D083-D109.

## Next

1. The student reviews the report and labels the 20 calibration answers.
2. Regenerate the report to add judge agreement and κ.
3. Decide on M5 acceptance and the commit.

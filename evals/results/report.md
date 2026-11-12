# FilingLens benchmark report

Generated from cached run records only (`python -m evals.report`). Accuracy cells: accuracy [95% bootstrap CI] n; `*` marks n < 30 (descriptive).

## Methodology and limitations

- **What system accuracy measures (D104).** Gold values are computed from the same `financial_facts` table the system's `get_financial_metric` tool reads. System accuracy therefore measures planning, fiscal-period mapping, arithmetic and answer formatting given correct structured data. It does not measure extraction of numbers from filings.
- **How the gold was checked.** The student verified all 20 review-sample gold values against the original SEC filings and/or the companies' earnings releases, with no discrepancies. The other gold values rest on the same M1 extraction.
- **Comparisons with equal data access.** B2 (the gold filings' financial statements in context) and B1 (open web search) can reach the same numbers as the system. They are the fair comparisons and are listed first after the system. B0 (closed book) measures what the model knows without any data.
- **Scope (D105, D109).** The system, B0 Sonnet, B1 and B2 run on a frozen 180-question test subset (the 100-question sample plus 80 stratified questions). B0 Opus and B0 Fable 5.2 run on the 100-question sample, where every system answers the same questions and is paired with the system.
- **B2 context limit (D109).** B2 contexts were capped at 25K tokens per filing and 50K per question (D089), but those caps were measured as characters/4. Financial-statement tables tokenize about 1.9 times denser, so real contexts averaged about 23K tokens and the largest were near 95K.
- **Cutoff and sample notes.** The test split includes a 20% after-cutoff floor per template (D086), except comparison at 14.5% (8 of 55): the same-sector pool has only 8 after-cutoff pairs (D101). After-cutoff questions concentrate in companies whose fiscal year ends mid-year (NKE, MSFT, PG, COST), so the cutoff breakdown is descriptive. Comparisons pair same-sector companies only (GICS, D101). JPM has no question in the 100-question sample (seeded draw).

## Headline: every system on the same frozen 100-question test sample

B2 and B1 have data access comparable to the system's; B0 has none (D104).

| System | Data access | Accuracy | lookup | yoy_growth | margin | trend_avg | derived_q4 | comparison | multi_step | Before cutoff | After cutoff | Abstained | Parse fail | Citation validity (numeric) | $/question | $/correct | Latency p50/p95 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| system | XBRL facts + filing passages (MCP tools) | 99.0% [97.0%, 100.0%] n=100 | 100.0% | 100.0% | 100.0% | 92.3% | 100.0% | 100.0% | 100.0% | 100.0% | 96.2% | 1.0% | 0.0% | 100.0% (294/294) | $0.1574 | $0.1590 | 17.5s / 31.7s |
| b2-sonnet | gold filings' statements in context | 96.0% [92.0%, 99.0%] n=100 | 100.0% | 100.0% | 86.7% | 100.0% | 92.9% | 92.9% | 100.0% | 95.9% | 96.2% | 1.0% | 0.0% | – | $0.0242 | $0.0252 | batch, not comparable |
| b1-sonnet | open web search | 90.0% [84.0%, 95.0%] n=100 | 100.0% | 93.3% | 93.3% | 100.0% | 92.9% | 85.7% | 64.3% | 87.8% | 96.2% | 0.0% | 0.0% | – | $0.0467 | $0.0519 | batch, not comparable |
| b0-fable | none (closed book) | 69.0% [60.0%, 78.0%] n=100 | 60.0% | 66.7% | 60.0% | 84.6% | 57.1% | 85.7% | 71.4% | 90.5% | 7.7% | 0.0% | 0.0% | – | $0.0242 | $0.0350 | 6.2s / 10.7s |
| b0-opus | none (closed book) | 55.0% [45.0%, 65.0%] n=100 | 53.3% | 60.0% | 40.0% | 69.2% | 50.0% | 71.4% | 42.9% | 74.3% | 0.0% | 0.0% | 0.0% | – | $0.0126 | $0.0230 | 5.7s / 9.8s |
| b0-sonnet | none (closed book) | 42.0% [32.0%, 52.0%] n=100 | 33.3% | 53.3% | 20.0% | 61.5% | 42.9% | 71.4% | 14.3% | 55.4% | 3.8% | 2.0% | 0.0% | – | $0.0077 | $0.0184 | 4.8s / 10.1s |

## Larger test subset: every system run on all 180 questions (D105, D109)

| System | Data access | Accuracy | lookup | yoy_growth | margin | trend_avg | derived_q4 | comparison | multi_step | Before cutoff | After cutoff | Abstained | Parse fail | Citation validity (numeric) | $/question | $/correct | Latency p50/p95 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| system | XBRL facts + filing passages (MCP tools) | 99.4% [98.3%, 100.0%] n=180 | 100.0% | 100.0% | 100.0% | 96.0% | 100.0% | 100.0% | 100.0% | 100.0% | 97.8% | 0.6% | 0.0% | 100.0% (531/531) | $0.1575 | $0.1583 | 18.0s / 31.5s |
| b2-sonnet | gold filings' statements in context | 95.6% [92.2%, 98.3%] n=180 | 100.0% | 100.0% | 92.6% | 96.0% | 92.0% | 88.0% | 100.0% | 94.8% | 97.8% | 0.6% | 0.0% | – | $0.0253 | $0.0265 | batch, not comparable |
| b1-sonnet | open web search | 85.0% [79.4%, 90.0%] n=180 | 96.3% | 96.2% | 92.6% | 84.0% | 88.0% | 72.0% | 64.0% | 85.2% | 84.4% | 0.0% | 0.0% | – | $0.0462 | $0.0544 | batch, not comparable |
| b0-sonnet | none (closed book) | 42.8% [35.6%, 50.0%] n=180 | 33.3% | 50.0% | 37.0% | 56.0% | 36.0% | 60.0% | 28.0% | 55.6% | 4.4% | 2.2% | 0.0% | – | $0.0073 | $0.0170 | 4.7s / 10.9s |

## Paired tests vs the system

| vs | n | system only | other only | Δ accuracy [95% CI] | McNemar p | Holm p |
|---|---|---|---|---|---|---|
| b0-sonnet | 180 | 102 | 0 | +56.7 pp [+49.4, +63.9] | 0.0000 | 0.0000 |
| b0-opus | 100 | 44 | 0 | +44.0 pp [+34.0, +54.0] | 0.0000 | 0.0000 |
| b0-fable | 100 | 30 | 0 | +30.0 pp [+21.0, +39.0] | 0.0000 | 0.0000 |
| b2-sonnet | 180 | 8 | 1 | +3.9 pp [+1.1, +7.2] | 0.0391 | 0.0391 |
| b1-sonnet | 180 | 27 | 1 | +14.4 pp [+9.4, +20.0] | 0.0000 | 0.0000 |

## Breakdowns (test)

| System | Group | Accuracy |
|---|---|---|
| system | template comparison | 100.0% [100.0%, 100.0%] n=25* |
| system | template derived_q4 | 100.0% [100.0%, 100.0%] n=25* |
| system | template lookup | 100.0% [100.0%, 100.0%] n=27* |
| system | template margin | 100.0% [100.0%, 100.0%] n=27* |
| system | template multi_step | 100.0% [100.0%, 100.0%] n=25* |
| system | template trend_avg | 96.0% [88.0%, 100.0%] n=25* |
| system | template yoy_growth | 100.0% [100.0%, 100.0%] n=26* |
| system | cutoff after | 97.8% [93.3%, 100.0%] n=45 |
| system | cutoff before | 100.0% [100.0%, 100.0%] n=135 |
| system | restated False | 99.4% [98.3%, 100.0%] n=174 |
| system | restated True | 100.0% [100.0%, 100.0%] n=6* |
| system | derived False | 100.0% [100.0%, 100.0%] n=101 |
| system | derived True | 98.7% [96.2%, 100.0%] n=79 |
| b2-sonnet | template comparison | 88.0% [76.0%, 100.0%] n=25* |
| b2-sonnet | template derived_q4 | 92.0% [80.0%, 100.0%] n=25* |
| b2-sonnet | template lookup | 100.0% [100.0%, 100.0%] n=27* |
| b2-sonnet | template margin | 92.6% [81.5%, 100.0%] n=27* |
| b2-sonnet | template multi_step | 100.0% [100.0%, 100.0%] n=25* |
| b2-sonnet | template trend_avg | 96.0% [88.0%, 100.0%] n=25* |
| b2-sonnet | template yoy_growth | 100.0% [100.0%, 100.0%] n=26* |
| b2-sonnet | cutoff after | 97.8% [93.3%, 100.0%] n=45 |
| b2-sonnet | cutoff before | 94.8% [91.1%, 98.5%] n=135 |
| b2-sonnet | restated False | 96.0% [93.1%, 98.9%] n=174 |
| b2-sonnet | restated True | 83.3% [50.0%, 100.0%] n=6* |
| b2-sonnet | derived False | 96.0% [92.1%, 99.0%] n=101 |
| b2-sonnet | derived True | 94.9% [89.9%, 98.7%] n=79 |
| b2-sonnet | gold_visible False | 44.4% [11.1%, 77.8%] n=9* |
| b2-sonnet | gold_visible True | 98.2% [95.9%, 100.0%] n=171 |
| b1-sonnet | template comparison | 72.0% [52.0%, 88.0%] n=25* |
| b1-sonnet | template derived_q4 | 88.0% [76.0%, 100.0%] n=25* |
| b1-sonnet | template lookup | 96.3% [88.9%, 100.0%] n=27* |
| b1-sonnet | template margin | 92.6% [81.5%, 100.0%] n=27* |
| b1-sonnet | template multi_step | 64.0% [44.0%, 84.0%] n=25* |
| b1-sonnet | template trend_avg | 84.0% [68.0%, 96.0%] n=25* |
| b1-sonnet | template yoy_growth | 96.2% [88.5%, 100.0%] n=26* |
| b1-sonnet | cutoff after | 84.4% [73.3%, 93.3%] n=45 |
| b1-sonnet | cutoff before | 85.2% [78.5%, 91.1%] n=135 |
| b1-sonnet | restated False | 87.4% [82.2%, 92.0%] n=174 |
| b1-sonnet | restated True | 16.7% [0.0%, 50.0%] n=6* |
| b1-sonnet | derived False | 89.1% [83.2%, 95.0%] n=101 |
| b1-sonnet | derived True | 79.7% [70.9%, 88.6%] n=79 |
| b0-fable | template comparison | 85.7% [64.3%, 100.0%] n=14* |
| b0-fable | template derived_q4 | 57.1% [28.6%, 85.7%] n=14* |
| b0-fable | template lookup | 60.0% [33.3%, 86.7%] n=15* |
| b0-fable | template margin | 60.0% [33.3%, 86.7%] n=15* |
| b0-fable | template multi_step | 71.4% [50.0%, 92.9%] n=14* |
| b0-fable | template trend_avg | 84.6% [61.5%, 100.0%] n=13* |
| b0-fable | template yoy_growth | 66.7% [40.0%, 86.7%] n=15* |
| b0-fable | cutoff after | 7.7% [0.0%, 19.2%] n=26* |
| b0-fable | cutoff before | 90.5% [83.8%, 95.9%] n=74 |
| b0-fable | restated False | 69.1% [59.8%, 78.4%] n=97 |
| b0-fable | restated True | 66.7% [0.0%, 100.0%] n=3* |
| b0-fable | derived False | 68.4% [56.1%, 80.7%] n=57 |
| b0-fable | derived True | 69.8% [55.8%, 83.7%] n=43 |
| b0-opus | template comparison | 71.4% [42.9%, 92.9%] n=14* |
| b0-opus | template derived_q4 | 50.0% [21.4%, 78.6%] n=14* |
| b0-opus | template lookup | 53.3% [26.7%, 80.0%] n=15* |
| b0-opus | template margin | 40.0% [13.3%, 66.7%] n=15* |
| b0-opus | template multi_step | 42.9% [14.3%, 71.4%] n=14* |
| b0-opus | template trend_avg | 69.2% [46.2%, 92.3%] n=13* |
| b0-opus | template yoy_growth | 60.0% [33.3%, 86.7%] n=15* |
| b0-opus | cutoff after | 0.0% [0.0%, 0.0%] n=26* |
| b0-opus | cutoff before | 74.3% [64.9%, 83.8%] n=74 |
| b0-opus | restated False | 55.7% [45.4%, 66.0%] n=97 |
| b0-opus | restated True | 33.3% [0.0%, 100.0%] n=3* |
| b0-opus | derived False | 57.9% [45.6%, 70.2%] n=57 |
| b0-opus | derived True | 51.2% [34.9%, 65.1%] n=43 |
| b0-sonnet | template comparison | 60.0% [40.0%, 80.0%] n=25* |
| b0-sonnet | template derived_q4 | 36.0% [20.0%, 56.0%] n=25* |
| b0-sonnet | template lookup | 33.3% [14.8%, 51.9%] n=27* |
| b0-sonnet | template margin | 37.0% [18.5%, 55.6%] n=27* |
| b0-sonnet | template multi_step | 28.0% [12.0%, 48.0%] n=25* |
| b0-sonnet | template trend_avg | 56.0% [36.0%, 76.0%] n=25* |
| b0-sonnet | template yoy_growth | 50.0% [30.8%, 69.2%] n=26* |
| b0-sonnet | cutoff after | 4.4% [0.0%, 11.1%] n=45 |
| b0-sonnet | cutoff before | 55.6% [47.4%, 63.7%] n=135 |
| b0-sonnet | restated False | 43.7% [36.2%, 51.1%] n=174 |
| b0-sonnet | restated True | 16.7% [0.0%, 50.0%] n=6* |
| b0-sonnet | derived False | 45.5% [35.6%, 55.4%] n=101 |
| b0-sonnet | derived True | 39.2% [29.1%, 50.6%] n=79 |

## Abstention probe (outside the headline)

| System | Correct abstentions |
|---|---|
| system | 100.0% [100.0%, 100.0%] n=10* |
| b0-sonnet | 70.0% [40.0%, 100.0%] n=10* |
| b0-opus | 70.0% [40.0%, 100.0%] n=10* |

## Handwritten explanatory questions (30; Opus 5.5 judge, D093)

| System | Mean, no answer = 1 [95% CI] | Mean over answered [95% CI] | No answer | Judged scores 1/2/3/4/5 | Unparsed |
|---|---|---|---|---|---|
| b0-sonnet | 3.23 [3.00, 3.47] | 3.23 [3.00, 3.47] | 0/30 | 0 / 4 / 15 / 11 / 0 | 0 |
| system | 3.23 [2.73, 3.73] | 3.79 [3.42, 4.17] | 6/30 | 0 / 3 / 5 / 10 / 6 | 0 |

Judge calibration: pending the student's 20 blind labels.

System text claims: 102; supported by string match 80, by the claim judge 18 of 22 judged (96.1% supported).

System-level retrieval (filings workers' first search, D099): recall@5 0.500, recall@10 0.552 (n=30).

## Retrieval (frozen M2 v2, 30 handwritten questions)

| Mode | Capped recall@5 | Capped recall@10 | Recall@5 | Recall@10 | Hit@5 | Hit@10 | MRR@30 | n |
|---|---|---|---|---|---|---|---|---|
| vector | 0.6489 | 0.7333 | 0.6444 | 0.7333 | 0.8667 | 0.9000 | 0.6302 | 30 |
| keyword | 0.4800 | 0.5881 | 0.4770 | 0.5881 | 0.6667 | 0.7000 | 0.5275 | 30 |
| hybrid | 0.5867 | 0.7159 | 0.5833 | 0.7159 | 0.7667 | 0.8667 | 0.5965 | 30 |
| hybrid_rerank | 0.6322 | 0.7492 | 0.6278 | 0.7492 | 0.8333 | 0.9000 | 0.5670 | 30 |

## Failures (uncategorized; categorization is M6)

- **system**: 1 wrong — abstained 1
- **b0-sonnet**: 103 wrong — abstained 4, wrong 99
- **b0-opus**: 45 wrong — wrong 45
- **b0-fable**: 31 wrong — wrong 31
- **b2-sonnet**: 8 wrong — abstained 1, wrong 7
- **b1-sonnet**: 27 wrong — wrong 27

### System abstentions on test (1)

Every generated question has a gold value computed from stored facts, so the data never justifies an abstention here (D085).

- `q_7efc51f876d501c0` (trend_avg, COST): What was Costco's average quarterly net cash provided by operating activities over fiscal 2026? Gold 3954250000 USD; the system answered not_available. Stated reason: No verified claims remain. 2 caveats could not be verified and were removed. 5 claims could not be verified and were removed. Summary rewritten from verified claims. Verification was cut short by the run's token budget (MAX_RUN_TOKENS); only claims verified in both stages were kept.

## Analysis notes (M5, 2026-11-11)

Written by hand from the cached records and traces; the tables above are generated.

### The system's one abstention (Costco, trend_avg) was an error, not a data gap

`q_7efc51f876d501c0` asks for Costco's average quarterly net cash provided by operating
activities over fiscal 2026. All four quarters exist in `financial_facts` (Q1 reported directly;
Q2-Q4 derived from year-to-date figures), and the gold is 3,954,250,000.

The trace shows the run found the data. `get_financial_metric` returned all four quarters, and
`summary_stats` returned a mean of exactly 3,954,250,000. The budget was then used up in two ways:

- The planner called `list_available_metrics` 6 times with identical arguments (8 planner calls,
  126K tokens).
- The analyst called `evaluate("15817000000/4")`, which was rejected as untraced. It then tried
  5 times to return its answer through a nonexistent `json` tool (`TOOL_NOT_ALLOWED`).

The run passed 200K tokens before verification, so D073 kept no claims and the answer became
`not_available`. This is the same planner-loop pattern as D108 (c). The analyst's attempt to
answer through a tool is a further M6 candidate.

### Six handwritten runs gave no answer (D108)

Six handwritten system runs used up the 200K-token budget before the analyst wrote any draft. Five
were spent on filings-worker passage reads (150-234K tokens, 13-27 passages); in the sixth the
planner made 8 calls. They are counted as "no answer (token budget)" failures and score 1 in the
system's judge mean. Over the answered 24, the system's mean score (3.79) is above B0 Sonnet's
(3.23); with the six scored 1, the means are equal (3.23). Judge calibration is pending the
student's labels.

### Disney "operating income" is segment operating income (3 questions)

Disney's income statement has no operating-income line. The stored `OperatingIncomeLoss` fact
(FY2024: $15.601B) is Disney's total segment operating income from its segment disclosure. Gold
"operating margin" for Disney is therefore segment operating income divided by revenue. B1 and B2
both answered the three Disney operating-margin comparisons with a statement-based figure
instead, and gave the same wrong values. The system agrees with the gold because it reads the
same fact (D104).

Without those three questions:

| System | Accuracy without them (n=177 or 99) | With them |
|---|---:|---:|
| system | 99.4% | 99.4% |
| b2-sonnet | 97.2% | 95.6% |
| b1-sonnet | 86.4% | 85.0% |
| b0-sonnet | 43.5% | 42.8% |

The system's advantage over B2 depends on these questions: +3.9 pp, McNemar p = 0.039 with them;
+2.3 pp [+0.0, +5.1], p = 0.22 without them (5 system-only vs 1 B2-only correct). The advantage
over B1 holds either way (+13.0 pp [+7.9, +18.6] without them, p < 0.0001). **On this benchmark,
the system and B2 are not reliably distinguishable once the ambiguous Disney definition is set
aside.**

### "Gross margin" means a dollar line for Apple and Microsoft (2 B2 answers)

Apple and Microsoft label gross profit "Gross margin" on their income statements. B2 answered two
gross-margin questions (MSFT fiscal Q4 2026, AAPL fiscal Q3 2025) with the dollar amount, despite
the prompt asking for margins in percent. In the Apple answer, the model itself noted "≈ 46.5%",
which is the gold. These are scored wrong (a percent was required) but reflect a wording
ambiguity.

### B1 quotes as-first-reported figures for restated values

B1 got 5 of the 6 restated questions wrong, and all 5 wrong answers match the gold recomputed on
first-reported values (D086). The web sources quote the original figures, not the later
restatements. n = 6 is descriptive only.

### Closed-book knowledge stops at the training cutoff

Before vs after the cutoff, on the 100-question sample:

| Model | Before cutoff | After cutoff |
|---|---:|---:|
| B0 Fable 5.2 | 90.5% | 7.7% |
| B0 Opus 5.5 | 74.3% | 0.0% |
| B0 Sonnet 5.5 | 55.4% | 3.8% |

The cutoff buckets separate what the models remember from what they cannot know. After-cutoff
questions concentrate in companies whose fiscal year ends mid-year, so this is descriptive.

### Cost per question

System $0.157 (real time, $0.158 per correct answer). B2 $0.025 and B1 $0.046 per question are
Batch API prices (50% off); in real time they would be about twice that.

## Ablations

_M6._

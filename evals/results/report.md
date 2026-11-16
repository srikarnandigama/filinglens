# FilingLens benchmark report

Generated from cached run records only (`python -m evals.report`). Accuracy cells: accuracy [95% bootstrap CI] n; `*` marks n < 30 (descriptive).

## Methodology and limitations

- **What system accuracy measures (D104).** Gold values are computed from the same `financial_facts` table the system's `get_financial_metric` tool reads. System accuracy therefore measures planning, fiscal-period mapping, arithmetic and answer formatting given correct structured data. It does not measure extraction of numbers from filings.
- **How the gold was checked.** The student verified all 20 review-sample gold values against the original SEC filings and/or the companies' earnings releases, with no discrepancies. The other gold values rest on the same M1 extraction.
- **Comparisons with data access.** B2 and B1 can reach the same numbers as the system and are listed first after it. B2 is an oracle-context baseline: it is given the gold filings' financial statements, so it skips finding the company, filing and period, which the system does itself. B1 has open web search. B0 (closed book) measures what the model knows without any data.
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

## Interpretation

- **B2 is an oracle-context baseline.** It is handed the financial statements of the gold filings, so it never has to find the company, the filing or the fiscal period. The system starts from the question alone and locates the data itself (company resolution, filing and fiscal-period mapping, metric lookup, arithmetic). On the 180 questions both answered, the system scores 99.4% and B2 95.6%: the system matches the oracle-context baseline while locating the data itself. Cost per question: system $0.157 (real time); B2 $0.025 at Batch API prices, about $0.051 in real time, so the system costs 3.1x B2's real-time price.
- **Disney operating income is a gold-definition ambiguity.** Disney's income statement has no operating-income line; the stored `OperatingIncomeLoss` fact is its total segment operating income from the segment disclosure, and the gold uses it. A reader of the income statement can reasonably build a different figure. Results are shown with and without these questions; the definition is an M6 data-definition item (D110).

| System | Accuracy (all) | Disney segment-OI questions | Accuracy without |
|---|---|---|---|
| system | 99.4% [98.3%, 100.0%] n=180 | 3 | 99.4% [98.3%, 100.0%] n=177 |
| b2-sonnet | 95.6% [92.2%, 98.3%] n=180 | 3 | 97.2% [94.4%, 99.4%] n=177 |
| b1-sonnet | 85.0% [79.4%, 90.0%] n=180 | 3 | 86.4% [81.4%, 91.5%] n=177 |
| b0-fable | 69.0% [60.0%, 78.0%] n=100 | 1 | 69.7% [60.6%, 78.8%] n=99 |
| b0-opus | 55.0% [45.0%, 65.0%] n=100 | 1 | 55.6% [45.5%, 65.7%] n=99 |
| b0-sonnet | 42.8% [35.6%, 50.0%] n=180 | 3 | 43.5% [36.2%, 50.8%] n=177 |

Paired tests vs the system without the Disney segment-operating-income questions:

| vs | n | system only | other only | Δ accuracy [95% CI] | McNemar p | Holm p |
|---|---|---|---|---|---|---|
| b0-sonnet | 177 | 99 | 0 | +55.9 pp [+48.6, +63.3] | 0.0000 | 0.0000 |
| b0-opus | 99 | 43 | 0 | +43.4 pp [+33.3, +53.5] | 0.0000 | 0.0000 |
| b0-fable | 99 | 29 | 0 | +29.3 pp [+20.2, +38.4] | 0.0000 | 0.0000 |
| b2-sonnet | 177 | 5 | 1 | +2.3 pp [+0.0, +5.1] | 0.2188 | 0.2188 |
| b1-sonnet | 177 | 24 | 1 | +13.0 pp [+7.9, +18.6] | 0.0000 | 0.0000 |

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

Judge calibration (primary, v2: shuffled blind sheet, D110) n=20: exact 95.0%, within 1 100.0%, quadratic-weighted κ 0.98.

First attempt (v1, contaminated) n=20: exact 100.0%, within 1 100.0%, quadratic-weighted κ 1.00. The v1 sheet listed answers in a cycle of judge scores (2, 3, 4, 5 repeated), so position matched the judge's score; it is kept as provenance, not as the calibration result (D110).

The calibration sample covers judge scores 2-5 only: no answered output was judged 1, so agreement at the bottom of the scale is untested.

| v2 item | Key | System | Judge | Student v2 | Δ | Student v1 |
|---|---|---|---|---|---|---|
| 1 | `03b5618e` | b0-sonnet | 3 | 3 | +0 | 3 |
| 2 | `a086f1c3` | system | 5 | 5 | +0 | 5 |
| 3 | `53d36f66` | system | 5 | 5 | +0 | 5 |
| 4 | `68e09165` | system | 3 | 3 | +0 | 3 |
| 5 | `1402e208` | system | 5 | 5 | +0 | 5 |
| 6 | `a7b96b39` | system | 5 | 5 | +0 | 5 |
| 7 | `867d3a80` | b0-sonnet | 2 | 2 | +0 | 2 |
| 8 | `ca80c1c3` | b0-sonnet | 3 | 3 | +0 | 3 |
| 9 | `03c205ac` | system | 4 | 4 | +0 | 4 |
| 10 | `23d80aee` | b0-sonnet | 2 | 2 | +0 | 2 |
| 11 | `54b1195e` | system | 2 | 3 | +1 | 2 |
| 12 | `5a58fd86` | b0-sonnet | 3 | 3 | +0 | 3 |
| 13 | `a9d15407` | b0-sonnet | 3 | 3 | +0 | 3 |
| 14 | `e7eb2cfc` | system | 2 | 2 | +0 | 2 |
| 15 | `71ed8e0b` | b0-sonnet | 2 | 2 | +0 | 2 |
| 16 | `f559dab7` | b0-sonnet | 4 | 4 | +0 | 4 |
| 17 | `8d215a33` | b0-sonnet | 4 | 4 | +0 | 4 |
| 18 | `0494d6a9` | system | 4 | 4 | +0 | 4 |
| 19 | `91e41b09` | system | 5 | 5 | +0 | 5 |
| 20 | `84975b16` | b0-sonnet | 4 | 4 | +0 | 4 |

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
(3.23); with the six scored 1, the means are equal (3.23).

### Judge calibration: v1 was contaminated by its order; v2 is the calibration result

The student's first 20 blind labels (v1) match the judge on every item (exact 100%,
quadratic-weighted κ 1.00). But the v1 sheet listed the answers in the order
`calibration_sample` drew them, a round-robin over judge scores (2, 3, 4, 5, repeated five
times). Position therefore matched the judge's score exactly. Neither the judge score nor the
system was shown, but the agreement holds only to the extent the labels were made independently
of the order, so v1 is kept as a contaminated first attempt. The v2 sheet has the same 20
answers in a seeded random order under neutral item numbers (D110); its agreement is the
primary calibration result: exact 95% (19/20), within 1 100%, quadratic-weighted κ 0.98, so the
judge scores are not marked indicative. The one disagreement is a system answer the judge
scored 2 and the student 3. The student's v1 and v2 labels agree on 19 of 20 items. No answered
output was judged 1, so the sample covers judge scores 2-5 only.

### Disney "operating income" is a gold-definition ambiguity (3 questions)

Disney's income statement has no operating-income line. The stored `OperatingIncomeLoss` fact
(FY2024: $15.601B) is Disney's total segment operating income from its segment disclosure. Gold
"operating margin" for Disney is therefore segment operating income divided by revenue. B1 and B2
both answered the three Disney operating-margin comparisons with a statement-based figure
instead, and gave the same wrong values. The system agrees with the gold because it reads the
same fact (D104). This is a question of the gold's definition, not an extraction error, and it is
an M6 data-definition item (D110): define which figure "operating income" means for companies
without that income-statement line, and either relabel the metric or state it in the question.

The with/without results are in the Interpretation section above. The system's advantage over
B2 depends on these questions: +3.9 pp, McNemar p = 0.039 with them; +2.3 pp [+0.0, +5.1],
p = 0.22 without them (5 system-only vs 1 B2-only correct). The advantage over B1 holds either
way (+13.0 pp [+7.9, +18.6] without them, p < 0.0001). **On this benchmark, the system matches
the oracle-context B2 but is not reliably better than it once the ambiguous Disney definition is
set aside.**

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

## M6: improvement, ablations and failure analysis

Generated by `python -m evals.report ... --m6` from cached records, the judge cache and `evals/results/m6_mechanics.json` (trace mechanics, `python -m evals.m6_report collect`). The M5 sections above are unchanged and still regenerate from the M5 cache alone. Every before/after comparison uses identical questions with paired tests (exact McNemar or sign test, paired bootstrap CIs, 10,000 resamples, seed 20261109).

### What changed in M6, and what the evidence covers

- **Fixes (D113-D115), each behind a flag whose default is M5 behavior (D118):** a price-weighted run token budget (Haiku worker tokens count 1/20, Sonnet runs unchanged); an explicit answer instead of a run error when the budget stops a run before any draft (still scored as no answer); a guard that forces the final step after 2 no-progress tool steps; a hint for nonexistent tool names; and empty replies answered with the final-step guard. **Cost changes:** prompt caching (D116) and summary numbers that round cited values (D117).
- **(a) The cost saving is prompt caching; the other fixes were cost-neutral on dev.** On the 50 numeric test questions M6 costs $0.0605/question vs M5's $0.1586; at uncached prices M6 would cost $0.1413. On the 35 dev numeric questions M6 measured $0.062 vs $0.138, and $0.140 at uncached prices (Δ vs M5 +$0.002 [−0.007, +0.011]): the fixes changed steps and outcomes, not cost.
- **(b) The dev explanatory prompts did not reproduce the original budget failure.** The M5 system answered all 10 of them, so the no-draft fix (A2, D114) and the weighted budget's effect on no-answers are validated only by the handwritten test rerun below. On dev, two M6 runs went past 200K raw tokens and finished within the weighted budget, and M5 skipped two revisions for budget that M6 did not.
- **(c) Dev validation for the explanatory fixes was mechanical only** (D111, D120): no reference answers and no judge, so it says nothing about answer quality.
- **Selection caveat (D111):** the budget and loop failures behind the fixes were found on test in M5, so the test rerun measures fixes partly selected from test failures.

### Fixes: before/after on identical test questions

### Numeric test sample (50 questions, frozen, D121): M5 vs M6

| System | Accuracy [95% CI] |
|---|---|
| M5 system | 98.0% [94.0%, 100.0%] n=50 |
| M6 system | 100.0% [100.0%, 100.0%] n=50 |

Paired: M6 only correct 1, M5 only correct 0; Δ accuracy +2.0 pp [+0.0, +6.0], exact McNemar p = 1.000. Without the Disney segment-operating-income questions (D119): n = 49, M5 48/49, M6 49/49.

$/question: M5 $0.1586, M6 $0.0605 (Δ −$0.0981 [−$0.1169, −$0.0813]). Latency p50/p95: M5 17.5s / 29.6s, M6 19.3s / 27.7s (mean Δ +1.1s [+0.3, +1.8]).

The M5 test miss (`q_7efc51f876d501c0`, Costco trend_avg): M5 abstained at $0.4251; M6 correct at $0.0934.

### Handwritten explanatory questions (30, test, run once with the final M6 system)

| System | Judge mean, no answer = 1 [95% CI] | Mean over answered [95% CI] | No answer | Recall@5 / @10 (D099) | $/question | Latency p50/p95 |
|---|---|---|---|---|---|---|
| M5 system | 3.23 [2.73, 3.73] | 3.79 [3.42, 4.17] | 6/30 | 0.500 / 0.552 | $0.1794 | 44.8s / 79.7s |
| M6 system | 3.97 [3.63, 4.27] | 3.97 [3.63, 4.27] | 0/30 | 0.486 / 0.523 | $0.1548 | 61.2s / 121.8s |

Paired on the same 30: Δ judge mean (no answer = 1) +0.73 [+0.27, +1.23]; M6 scored higher on 12, lower on 2 (exact sign test p = 0.013). Answered: M6 only 6, M5 only 0 (exact McNemar p = 0.031). The 6 M5 no-answers scored 4, 4, 4, 4, 5, 4 under M6.

Cost per question, separating caching (cache tokens repriced as input for "M6 uncached"):

| Question set | M5 | M6 uncached | M6 (with caching) |
|---|---|---|---|
| Numeric test sample (50) | $0.1586 | $0.1413 | $0.0605 |
| Handwritten (30) | $0.1794 | $0.2285 | $0.1548 |
| Dev numeric (35, Phase C) | $0.1377 | $0.1402 | $0.0619 |
| Dev explanatory (10, Phase C) | $0.1930 | $0.2116 | $0.1451 |

### Dev validation (Phase C; mechanical only for explanatory prompts)

Dev numeric (35 dev-pilot questions, paired with M5): accuracy 35/35 for both; full tables in docs/M6_PHASE_C.md. Explanatory dev prompts xd01-xd10 (no references, no judge): both systems answered 10/10.

| Run | n | Mean price-weighted tokens | Runs revised | Revisions skipped (budget) | Stall guard | Empty replies / guarded |
|---|---|---|---|---|---|---|
| M5, xd01-xd10 | 10 | 72.9K | 5 | 2 | 0 | 1 / 0 |
| M6, xd01-xd10 | 10 | 79.1K | 5 | 0 | 2 | 0 / 0 |
| M6, 35 dev numeric | 35 | 60.4K | 5 | 0 | 5 | 12 / 12 |

### Ablations (SPEC §13.5, D121)

Each variant is the final M6 system with one flag changed, paired with it on the same questions. Numeric variants run on the frozen 50-question test sample; retrieval variants on the handwritten 30 (numeric questions never start a filings worker). Vector retrieval is the M6 default, so it is the vector-only arm.

| Variant | Questions | Accuracy or judge [95% CI] | Δ vs M6 [95% CI], paired p | Citation validity, numeric | Text claims supported | Numeric claims without fact/computation citation | $/question | $/correct | Latency p50/p95 |
|---|---|---|---|---|---|---|---|---|---|
| M6 system | numeric test sample | 100.0% [100.0%, 100.0%] n=50 | – | 100.0% (154/154) | no text claims | 0/154 | $0.0605 | $0.0605 | 19.3s / 27.7s |
| −verifier | numeric test sample | 100.0% [100.0%, 100.0%] n=50 | +0.0 pp [+0.0, +0.0], p = 1.00 | 100.0% (152/152) | no text claims | 0/152 | $0.0394 | $0.0394 | 16.1s / 20.9s |
| −quant tools | numeric test sample | 100.0% [100.0%, 100.0%] n=50 | +0.0 pp [+0.0, +0.0], p = 1.00 | 62.9% (88/140) | no text claims | 52/140 | $0.0862 | $0.0862 | 29.3s / 40.7s |
| M6 system (vector) | handwritten 30 | judge 3.97 [3.63, 4.27]; recall@5/10 0.49/0.52; no answer 0 | – | 100.0% (41/41) | 100.0% (122 string + 23 judge of 145; 0 unjudged) | 0/41 | $0.1548 | – | 61.2s / 121.8s |
| +rerank (hybrid_rerank) | handwritten 30 | judge 4.03 [3.70, 4.37]; recall@5/10 0.59/0.60; no answer 0 | +0.07 [-0.23, +0.37], sign p = 1.00 | 100.0% (35/35) | 98.7% (120 string + 27 judge of 149; 0 unjudged) | 0/35 | $0.1383 | – | 94.7s / 147.0s |
| −rerank (hybrid) | handwritten 30 | judge 4.00 [3.70, 4.30]; recall@5/10 0.51/0.54; no answer 0 | +0.03 [-0.20, +0.30], sign p = 1.00 | 100.0% (38/38) | 97.2% (116 string + 22 judge of 142; 0 unjudged) | 0/38 | $0.1571 | – | 59.2s / 114.4s |

**−verifier and −quant matched the M6 system's accuracy on the 50 numeric questions** (M6 50/50, −verifier 50/50, −quant 50/50). Removing the verifier saves $0.0211/question (34.9% of M6's cost); removing the quant tools costs $0.0257/question more (42.5%), because the analyst writes about 65% more output tokens working the arithmetic in text and benefits less from caching (D125). With the system near 100% on numeric questions, n = 50 cannot detect small accuracy differences; per-template and n = 30 results are descriptive. Without quant tools, numeric claims computed by the model carry no computation citation, so Stage 1 cannot verify them (D056): see the column above.

On the handwritten 30, reranking raised system-level recall@10 from 0.52 (vector) to 0.60 (hybrid_rerank; hybrid 0.54), but the judge means are within noise (vector 3.97, hybrid_rerank 4.03, hybrid 4.00; paired CIs include 0), and reranking costs latency (p50 61s vs 95s; cross-encoder on CPU). Vector stays the default (D044).

### Failure analysis (SPEC §13.6, D112)

Deterministic rules over each run's record and trace (`evals/failures.py`), no LLM; a run can fall into several categories and counts are runs. SPEC's wrong-period, wrong-concept and arithmetic categories had no system case in M5 or M6. The M5 dev pilot answered every question correctly, so SPEC's "≥ 25 failures from dev" is met as failure events (133 in 74 of 100 dev runs, D111). Guard events in M6 columns are the fixes acting, not new failures. Disney segment operating income (3 test questions) is a gold-definition item, not a system failure (D119). "Near budget" counts raw tokens: M6 runs are limited by the price-weighted budget (D113), so an M6 run above 150K raw tokens is not necessarily near its limit.

| Category | M5 dev pilot (100) | M5 test subset (180) | M5 handwritten (30) | M6 dev numeric (35) | M5 / M6 xd01-10 | M6 test sample (50) | M6 handwritten (30) |
|---|---|---|---|---|---|---|---|
| budget exhausted before a draft (no answer) | 0 | 0 | 6 | 0 | 0 / 0 | 0 | 0 |
| budget stop after a draft (D073 finalization) | 0 | 1 | 0 | 0 | 0 / 0 | 0 | 0 |
| run error (other) | 0 | 0 | 0 | 0 | 0 / 0 | 0 | 0 |
| partially answered | 0 | 0 | 2 | 0 | 4 / 1 | 0 | 1 |
| retrieval miss (no gold chunk seen) | 0 | 0 | 12 | 0 | 0 / 0 | 0 | 13 |
| planner stall (>=2 no-progress steps) | 10 | 16 | 1 | 2 | 0 / 1 | 4 | 0 |
| analyst stall (>=2 no-progress steps) | 12 | 43 | 2 | 3 | 0 / 1 | 9 | 2 |
| filings stall (>=2 no-progress steps) | 0 | 0 | 1 | 0 | 0 / 0 | 0 | 0 |
| verifier stall (>=2 no-progress steps) | 0 | 1 | 0 | 0 | 0 / 0 | 0 | 0 |
| invalid final-answer tool | 9 | 21 | 0 | 1 | 0 / 0 | 4 | 1 |
| empty reply | 28 | 45 | 1 | 11 | 1 / 0 | 10 | 1 |
| corrective retry: planner (planning error caught by validation) | 0 | 2 | 1 | 1 | 0 / 0 | 0 | 1 |
| corrective retry: analyst | 28 | 43 | 1 | 0 | 1 / 1 | 0 | 0 |
| corrective retry: filings | 0 | 0 | 3 | 0 | 3 / 2 | 0 | 4 |
| corrective retry: verifier | 1 | 5 | 1 | 0 | 1 / 0 | 2 | 3 |
| untraced quant call (D079) | 45 | 92 | 4 | 13 | 2 / 1 | 26 | 7 |
| filings passage cap hit (D074) | 0 | 0 | 9 | 0 | 3 / 4 | 0 | 13 |
| revision: summary numbers not in claims (Stage 1) | 17 | 21 | 1 | 1 | 0 / 0 | 0 | 0 |
| revision: unsupported caveat (Stage 2) | 11 | 13 | 5 | 4 | 1 / 2 | 2 | 7 |
| revision: unsupported claim | 0 | 1 | 3 | 0 | 3 / 3 | 0 | 6 |
| revision skipped for budget (D072) | 0 | 0 | 2 | 0 | 2 / 0 | 0 | 0 |
| stall guard fired (D115) | 0 | 0 | 0 | 15 | 0 / 2 | 20 | 3 |
| near budget (>150K tokens) | 0 | 4 | 9 | 0 | 4 / 2 | 0 | 15 |

Two examples per category and a seeded spot-check list of up to 5 runs, in one seeded order across the M5 and M6 runs (seed 20261112):

- **budget exhausted before a draft (no answer)** — `hq_9f2123ab9…` (m5_handwritten): Run used 259382 tokens of MAX_RUN_TOKENS=200000.; `hq_cdeefd822…` (m5_handwritten): Run used 220246 tokens of MAX_RUN_TOKENS=200000.. Spot-check: `hq_9f2123ab9…` (m5_handwritten), `hq_cdeefd822…` (m5_handwritten), `hq_74fd7fdce…` (m5_handwritten), `hq_efbdb0ea5…` (m5_handwritten), `hq_eead0b7f7…` (m5_handwritten).
- **budget stop after a draft (D073 finalization)** — `q_7efc51f876…` (m5_test_subset): Run used 202902 tokens of MAX_RUN_TOKENS=200000.. Spot-check: `q_7efc51f876…` (m5_test_subset).
- **partially answered** — `hq_19ea90a4e…` (m5_handwritten): status partially_answered; `hq_d2c0efbed…` (m5_handwritten): status partially_answered. Spot-check: `hq_19ea90a4e…` (m5_handwritten), `hq_d2c0efbed…` (m5_handwritten), `hq_9f2123ab9…` (m6_handwritten).
- **retrieval miss (no gold chunk seen)** — `hq_c65d45763…` (m6_handwritten): 23 chunks seen, none gold; `hq_c65d45763…` (m5_handwritten): 28 chunks seen, none gold. Spot-check: `hq_c65d45763…` (m6_handwritten), `hq_c65d45763…` (m5_handwritten), `hq_74fd7fdce…` (m6_handwritten), `hq_74fd7fdce…` (m5_handwritten), `hq_af3da89eb…` (m6_handwritten).
- **planner stall (>=2 no-progress steps)** — `q_904fca8ce7…` (m6_test_sample): planner reached 2 no-progress steps at step 2; `q_904fca8ce7…` (m5_test_subset): planner reached 2 no-progress steps at step 2. Spot-check: `q_904fca8ce7…` (m6_test_sample), `q_904fca8ce7…` (m5_test_subset), `q_70534645e9…` (m5_test_subset), `q_e493e29a4e…` (m5_dev_pilot), `q_3996fe54c6…` (m5_dev_pilot).
- **analyst stall (>=2 no-progress steps)** — `q_4fa166dff5…` (m5_test_subset): analyst:r0 reached 2 no-progress steps at step 3; `q_1256a4e50c…` (m5_test_subset): analyst:r0 reached 2 no-progress steps at step 2. Spot-check: `q_4fa166dff5…` (m5_test_subset), `q_1256a4e50c…` (m5_test_subset), `q_d16b147aaa…` (m5_test_subset), `hq_19ea90a4e…` (m5_handwritten), `q_adcded32d4…` (m5_test_subset).
- **filings stall (>=2 no-progress steps)** — `hq_f5d53183c…` (m5_handwritten): filings:s2 reached 2 no-progress steps at step 2. Spot-check: `hq_f5d53183c…` (m5_handwritten).
- **verifier stall (>=2 no-progress steps)** — `q_cbde504659…` (m5_test_subset): verifier:r0 reached 2 no-progress steps at step 2. Spot-check: `q_cbde504659…` (m5_test_subset).
- **invalid final-answer tool** — `q_f3ad0b47f4…` (m5_test_subset): analyst:r0 called 'json'; `q_e3e4d33105…` (m5_dev_pilot): analyst:r0 called 'json'. Spot-check: `q_f3ad0b47f4…` (m5_test_subset), `q_e3e4d33105…` (m5_dev_pilot), `q_860cad39f1…` (m5_dev_pilot), `q_c57e9ad06f…` (m5_test_subset), `q_8a1de8adfa…` (m5_test_subset).
- **empty reply** — `q_30101b9891…` (m5_test_subset): analyst:r0 step 2; `q_ebb237b5a4…` (m5_test_subset): analyst:r0 step 3. Spot-check: `q_30101b9891…` (m5_test_subset), `q_ebb237b5a4…` (m5_test_subset), `hq_19ea90a4e…` (m6_handwritten), `q_5875490e66…` (m5_dev_pilot), `q_3fa4b659e0…` (m5_dev_pilot).
- **corrective retry: planner (planning error caught by validation)** — `q_128b9d1dd0…` (m5_test_subset): planner step 3; `q_c4a25f7d0b…` (m6_dev_numeric): planner step 3. Spot-check: `q_128b9d1dd0…` (m5_test_subset), `q_c4a25f7d0b…` (m6_dev_numeric), `hq_3d27d3a6b…` (m6_handwritten), `hq_3d27d3a6b…` (m5_handwritten), `q_c57e9ad06f…` (m5_test_subset).
- **corrective retry: analyst** — `q_0dbdfea72a…` (m5_test_subset): analyst:r0 step 5; `q_670744f4c0…` (m5_dev_pilot): analyst:r0 step 3. Spot-check: `q_0dbdfea72a…` (m5_test_subset), `q_670744f4c0…` (m5_dev_pilot), `q_3e499ab6d5…` (m5_test_subset), `q_b5632fcdd2…` (m5_dev_pilot), `q_e16a585014…` (m5_test_subset).
- **corrective retry: filings** — `hq_804ee5491…` (m6_handwritten): filings:s3 step 3; `hq_9244d7ed5…` (m5_handwritten): filings:s3 step 4. Spot-check: `hq_804ee5491…` (m6_handwritten), `hq_9244d7ed5…` (m5_handwritten), `hq_24a3e4ca8…` (m6_handwritten), `hq_24a3e4ca8…` (m5_handwritten), `hq_af3e0e047…` (m6_handwritten).
- **corrective retry: verifier** — `hq_eead0b7f7…` (m6_handwritten): verifier:r1 step 1; `q_30101b9891…` (m5_test_subset): verifier:r0 step 1. Spot-check: `hq_eead0b7f7…` (m6_handwritten), `q_30101b9891…` (m5_test_subset), `hq_395269fb9…` (m6_handwritten), `q_d64fd9e255…` (m5_test_subset), `q_cbde504659…` (m5_test_subset).
- **untraced quant call (D079)** — `q_78ab03d3c0…` (m5_test_subset): analyst:r0 evaluate; `q_b5632fcdd2…` (m5_dev_pilot): analyst:r0 evaluate. Spot-check: `q_78ab03d3c0…` (m5_test_subset), `q_b5632fcdd2…` (m5_dev_pilot), `q_adcded32d4…` (m5_test_subset), `q_c8df389061…` (m5_dev_pilot), `q_1787a53177…` (m6_test_sample).
- **filings passage cap hit (D074)** — `hq_804ee5491…` (m6_handwritten): filings:s2 get_passage; `hq_24a3e4ca8…` (m6_handwritten): filings:s2 get_passage. Spot-check: `hq_804ee5491…` (m6_handwritten), `hq_24a3e4ca8…` (m6_handwritten), `hq_24a3e4ca8…` (m5_handwritten), `hq_9f2123ab9…` (m5_handwritten), `hq_ce9809903…` (m6_handwritten).
- **revision: summary numbers not in claims (Stage 1)** — `q_2e3b62ca92…` (m5_dev_pilot): summary numbers ['3.982'] do not appear in any claim; `q_1787a53177…` (m5_test_subset): summary numbers ['14.5', '27.4'] do not appear in any claim. Spot-check: `q_2e3b62ca92…` (m5_dev_pilot), `q_1787a53177…` (m5_test_subset), `q_b5632fcdd2…` (m5_dev_pilot), `q_606f76e0db…` (m5_test_subset), `q_43f5e699d4…` (m5_test_subset).
- **revision: unsupported caveat (Stage 2)** — `hq_74fd7fdce…` (m6_handwritten): verifier (needs_revision): The retrieved 10-Q material included a quantified Brent price sensitivity ($600 mil; `q_d64fd9e255…` (m5_test_subset): verifier (unsupported): The evidence supports the source filing (accession 0000093410-24-000021, a cvx-2024033. Spot-check: `hq_74fd7fdce…` (m6_handwritten), `q_d64fd9e255…` (m5_test_subset), `q_af551fb326…` (m6_dev_numeric), `q_af551fb326…` (m5_dev_pilot), `q_35ee3ca72d…` (m5_test_subset).
- **revision: unsupported claim** — `hq_ce9809903…` (m5_handwritten): verifier (needs_revision): The description of Microsoft 365 Commercial as an AI-powered platform that includes; `hq_3d27d3a6b…` (m6_handwritten): verifier (needs_revision): The 10-Q says most 2023 demand was met from supply delivered to governments and rec. Spot-check: `hq_ce9809903…` (m5_handwritten), `hq_3d27d3a6b…` (m6_handwritten), `hq_74fd7fdce…` (m6_handwritten), `hq_9e6c0c0db…` (m5_handwritten), `hq_4d5d9efc0…` (m6_handwritten).
- **revision skipped for budget (D072)** — `hq_24a3e4ca8…` (m5_handwritten): round 1; `hq_9244d7ed5…` (m5_handwritten): round 1. Spot-check: `hq_24a3e4ca8…` (m5_handwritten), `hq_9244d7ed5…` (m5_handwritten).
- **stall guard fired (D115)** — `hq_74fd7fdce…` (m6_handwritten): analyst:r0 no_progress at step 2; `q_3d4d24ff11…` (m6_dev_numeric): analyst:r0 empty_reply at step 3. Spot-check: `hq_74fd7fdce…` (m6_handwritten), `q_3d4d24ff11…` (m6_dev_numeric), `q_82eea7d929…` (m6_test_sample), `q_33294708d1…` (m6_test_sample), `q_1b5e88ee69…` (m6_dev_numeric).
- **near budget (>150K tokens)** — `hq_21f4a3b2e…` (m5_handwritten): 154941 tokens; `q_1256a4e50c…` (m5_test_subset): 165152 tokens. Spot-check: `hq_21f4a3b2e…` (m5_handwritten), `q_1256a4e50c…` (m5_test_subset), `hq_e9bf3b51f…` (m6_handwritten), `hq_9244d7ed5…` (m5_handwritten), `hq_69c1bbc69…` (m6_handwritten).

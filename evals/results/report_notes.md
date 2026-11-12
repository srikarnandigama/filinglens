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

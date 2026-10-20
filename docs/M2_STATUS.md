# M2 status: accepted; corpus v2 and Phase C accepted

## Current corpus-v2 handoff

The student completed review of all six affected questions. Only JPM cybersecurity
(two FY2024 Item 7 chunks) and Chevron/Hess (one FY2024 Item 8 chunk) gained gold;
none was removed. All 30 questions, saved filters and reference answers remain
unchanged. Validation passed for 64 gold IDs, the frozen v2 fingerprint and every
gold/filter match; attribution uses 28 unchanged-label questions and 2 changed-label
questions, plus a fixed-ranking bridge scored with the original migrated gold.

V2 is selected for M3 onward:
`corpus_3f3c2a9affddcc6a29eca9e768c65bcbd3e2f131fb69595b24b9b92005738739`.
It contains 32,960 chunks across 275 filings. Settings now selects v2 for an unset
or blank RETRIEVAL_CORPUS; explicit historical overrides remain supported. No
private .env file was changed. V1, its labels/results and Phase B reports remain
unchanged, as do both frozen corpora and M1 financial data.

See [retrieval_v2.md](../evals/results/retrieval_v2.md) for full/subset metrics,
v1-versus-v2 comparisons, per-question rank changes, label attribution, reranker
behavior and pooled-label limitations. Of 120 searches, 24 used existing caches
and 96 ran fresh. Recall@10 / MRR@30 are:

| Mode | Recall@10 | MRR@30 |
|---|---:|---:|
| vector | 0.7333 | 0.6302 |
| keyword | 0.5881 | 0.5275 |
| hybrid | 0.7159 | 0.5965 |
| hybrid_rerank | 0.7492 | 0.5670 |

Reranking raises recall@10 but lowers MRR; first-gold ranks are 8 better,
10 worse and 12 unchanged. All four reviewed-v2 recall@10 values are lower than
v1; these mixed corpus/label differences are separated in the report. The
exposure-proxy top-10 unjudged rates are 0%, 29%, 2.67% and 9.67%, respectively;
the current four-mode-union rates are zero by construction, not evidence that
all candidates were judged. Source-absent JNJ/XOM quarterly risk items remain
explicitly absent with provenance; no content was invented.

Ruff lint/format pass; full pytest passes **101 tests**, with the legacy opt-in
production replay skipped. See [Phase C checks](CORPUS_V2_PHASE_C_CHECKS.md).
The student's conditional Phase C/corpus-v2 acceptance is satisfied: the
[read-only verification](CORPUS_V2_TIE_VERIFICATION.md) checked all 24 unchanged-scope
group (a) questions. All 504 keyword passage movements are explained by exact
score ties; all 24 vector rankings are identical by passage text. No unexplained
change was found. The tie-breaking rule, rankings, labels and corpora are unchanged.
**Phase C and corpus v2 are accepted. No M3 work has started; wait for a separate task.**

## Historical corpus-v1 acceptance and readiness record

M1 remains accepted. The student completed 30 questions and relevance judgments;
the four-mode retrieval evaluation and read-only coverage audit are complete.
See [retrieval.md](../evals/results/retrieval.md) for all metrics, the six-question
cross-year split, per-question ranks, reranker regressions, coverage inventory,
labeling methodology and limitations. See [M2_EVALUATION_CHECKS.md](M2_EVALUATION_CHECKS.md)
for commands and checks. The student explicitly accepted M2, including the
documented coverage gaps, keyword fix (D031), pooled-label limitations and
reranker behavior. M3 has not started; wait for the student's separate next task.

The corrected JNJ FY2024/FY filters passed validation; six intentional ticker-only
records remain (XOM, COST, MSFT, AMZN, NVDA, CVX). Labels and all frozen chunk IDs,
text and stored vectors have unchanged hashes before/after evaluation and tests.
No parsing, chunking, corpus embedding, schema or dependency changes were made.

The keyword AND-semantics defect was corrected with one preselected OR-over-English-
lexemes variant (D031), keeping ts_rank_cd, filters and RRF 60 unchanged. All 120
post-fix searches ran fresh under retrieval-v2-keyword-or; keyword returns hits for
all 30 questions and hybrid differs from vector on all 30. Capped recall@10 is
0.7556 vector, 0.6325 keyword, 0.7603 hybrid and 0.7714 reranked hybrid. Reranking
reduces MRR@30 from hybrid's 0.6210 to 0.5683. The pre-fix tables remain in the report.
Top-10 unjudged rates relative to the reconstructed pre-fix pool plus known gold
are 0%, 37.33%, 3.67% and 12.67% respectively; no new judgments were assigned.
The cross-year text-overlap audit flags 5/60 vector and 7/60 reranked slots as
different-filing near-duplicates. XOM greenhouse-gas gold is now found at keyword
rank 8, hybrid 18 and reranked 5; vector still misses the top 30. Known corpus issues
extend beyond Chevron to other cross-reference stubs and quarterly TOC captures;
the full audit lists all 224 short/absent item slots without repairing them.
The final suite passes 62 tests with one opt-in full-corpus replay skipped, and
Ruff lint/format checks pass. The frozen production corpus was not replayed.

### Required coverage repair before M4

A new, separately approved corpus version must repair JPM/XOM/CVX annual MD&A
and financials and BAC/JPM quarterly MD&A before M4; M4 answers and the M5 B2
stuffed-context baseline depend on that content. Cached-only inspection of all
22 JNJ/XOM 10-Qs found no separate quarterly Item 1A risk sections: each has only
an annual 10-K risk reference. Future processing must record verified source
absence and reference provenance rather than fabricate quarterly sections.

Preserve the frozen corpus and current labels. For the future version, map old
gold IDs to unique exact-text matches in the same filing/item/filter scope;
list unmatched and ambiguous matches for student review and save approved new
labels separately. This repair and migration are proposals only, after M2
acceptance and before M4. No new corpus or M3 work is being performed now.

The remaining sections preserve the earlier ingestion and labeling-readiness
measurements as historical evidence.

### Final corpus

- Corpus ID: `corpus_2fb48958e274daed46c19e3fbf2583213e308b1eebaa16a04cfdc8052eea82e7`.
- Snapshot: `2026-10-19-v1`; 275 filings, 708 retained sections,
  23,441 deterministic chunks.
- All documents downloaded: 263 network requests and 12 existing cache hits in
  69.8 seconds. Completed raw responses were reused without refresh.
- Final parsing/chunking pass: 446.0 seconds (7.4 minutes), 275 cache hits,
  zero network requests and zero failures.
- Every chunk's identity, source-block coverage, and token budgets passed the
  exhaustive audit in `M2_CORPUS_AUDIT.json`.
- Maximum ordinary embedding input: 460 tokens including context and special tokens.
- Maximum pair with the typical test query: 478 reranker tokens.
- Reserving 48 reranker query tokens plus pair special tokens gives a maximum
  of 512 tokens. Longer queries are rejected, never silently truncated.
- No oversized single table rows occur in this corpus; the flagged/windowed
  exception is covered by regression tests.
- Intermediate development corpora remain unembedded and are not the corpus to
  use for labeling. Scope selection is excluded from passage identity.

### Measured CPU embedding preflight

| Measurement | Result |
|---|---:|
| CPU threads / batch size | 4 / 16 |
| Sample chunks | 192 |
| Companies / forms represented | 20 / 10-K and 10-Q |
| Sample / corpus mean input tokens | 346.5 / 344.2 |
| Model loading, excluded from throughput | 6.18 seconds |
| Warm-up, excluded from throughput | 0.14 seconds |
| Encoding and committed database writes | 22.87 seconds |
| Measured throughput | 8.40 chunks/second |
| Projected entire corpus | 46.5 minutes |
| Remaining after sample | 23,249 chunks |
| Projected remaining time | 46.2 minutes |

This historical preflight projected 46.2 minutes remaining and recommended a
60-minute budget. The approved full run has now completed; its actual measurements
are below. The 192 sample embeddings were reused. Original preflight measurements
remain in `M2_EMBED_BENCHMARK.json`.

### Completed full embedding run

| Measurement | Actual result |
|---|---:|
| Total embedded chunks | 23,441 |
| Newly embedded in the full run | 23,249 |
| Reused preflight embeddings | 192 |
| Failures / missing / invalid vectors | 0 / 0 / 0 |
| Wall runtime | 33 minutes 24 seconds |
| Encoding and committed writes | 1994.68 seconds |
| Encoding/write throughput | 11.66 chunks/second |
| HNSW index size | 48,021,504 bytes |

`chunks_embedding_hnsw` is valid and ready; an actual EXPLAIN ANALYZE plan used
that index. All embeddings have the expected model revision, input hash,
384 dimensions and unit norms within tolerance. IDs and text still match the
verified offline replay hash. Full timing data, including UTC start/end times
and measurement definitions, is in `M2_EMBED_FULL.json`.

The sample query was `cloud revenue growth`, filtered to MSFT, FY2025 Q3,
Part I Item 2 (MD&A), accession `0000950170-25-061046`. Every mode returned three
valid hits; an additional company/period/item-filtered vector search returned
all ten requested hits. The filing includes both quarterly and nine-month
comparisons; filing-period metadata does not imply every number is quarterly.

See `M2_LABELING_READINESS.md` for all twelve ranked results, full IDs, passages
and filing links; `M2_LABELING_READINESS.json` holds machine-readable evidence,
including the index definition and query plan. This smoke query is separate from
the handwritten retrieval set. The CLI opened and quit successfully without
creating questions, labels or a draft.

### Validation and remaining gates

The full normal suite passed **56 tests**, with the explicitly gated full-corpus
replay test skipped in that invocation. It covers the three hash-checked real SEC
HTML fixtures, model token budgets, complete row handling, empty-database identity
rebuilds, expanded ingestion scope, filtered HNSW underfill with an exact oracle,
embedding interruption/resumption and input-drift detection, and manual CLI flows.
Ruff lint and formatting checks pass.

The standalone forced offline full-corpus replay also passed: all 275 filings
were reparsed with network access blocked, all 23,441 chunk IDs and passage texts
were unchanged, and the before/after SHA-256 hashes match. See
`M2_CHUNK_REPLAY.json` (403.7 seconds, 275 cache hits, zero network requests).
The 192 benchmark embeddings survived replay and have unit norms within floating
point tolerance. M1 still contains 20 companies, 275 filings and 2,715 facts.
Final targeted resumption/labeling checks also passed (8 tests). At that earlier
readiness handoff, no questions, gold labels or reference answers had been created.

The smoke-search, labeling, evaluation and explicit student acceptance gates are
complete. M2 is closed; M3 must wait for the student's separate next task.

Start the labeling CLI from the project root:

```powershell
.venv/Scripts/python.exe -m evals.label_retrieval --corpus corpus_2fb48958e274daed46c19e3fbf2583213e308b1eebaa16a04cfdc8052eea82e7
```

Labeling instructions are in `M2_LABELING.md`. The corpus has passed the complete-embedding guard and is frozen for stable labels.

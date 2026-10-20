# M2 status: ready for student-written questions and labels

M1 remains accepted. The approved full embedding run is complete and the corpus
is frozen for labeling. All four retrieval modes and the real labeling CLI startup
have been verified. The next step belongs to the student: review the sample
results, write and label at least 30 questions. Retrieval evaluation and M2
acceptance remain pending. M3 has not started.

## Final corpus

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

## Measured CPU embedding preflight

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

## Completed full embedding run

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

## Validation and remaining gates

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
Final targeted resumption/labeling checks also passed (8 tests). No questions,
gold labels, or reference answers have been created.

1. Review the four-mode smoke-search results in `M2_LABELING_READINESS.md`.
2. The student writes and labels at least 30 questions with the CLI below.
3. Run retrieval evaluation only after the student reports labeling complete.
4. Wait for explicit M2 acceptance before any M3 work.

Start the labeling CLI from the project root:

```powershell
.venv/Scripts/python.exe -m evals.label_retrieval --corpus corpus_2fb48958e274daed46c19e3fbf2583213e308b1eebaa16a04cfdc8052eea82e7
```

Labeling instructions are in `M2_LABELING.md`. The corpus has passed the complete-embedding guard and is frozen for stable labels.

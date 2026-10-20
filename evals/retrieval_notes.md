### Interpretation and impact on evaluated questions

Chevron Items 7, 7A and 8 are one-chunk cross-references in **all three annual years, FY2023–FY2025**. Items 7 and 8 point to the Financial Table of Contents rather than containing the real MD&A/statements. Those Financial Section bodies are absent from this corpus. The Chevron Hess question (`hq_e9bf3b51fc6948de9eaa071fdbdb0e46`) was deliberately labeled from FY2024 Item 1A because of this gap. The other Chevron question (sustained low oil prices, `hq_74fd7fdce150403baad26a906223ba57`) also uses Item 1A. Their saved gold passages exist; the missing financial material limits available evidence and exhaustiveness, without invalidating their stored gold IDs.

The audit also finds JPMorgan and ExxonMobil annual financial-section cross-references, Disney and NVIDIA Item 8 cross-references, and Bank of America/JPMorgan quarterly MD&A table-of-contents captures. These are material limitations of the frozen corpus, rather than search-ranking failures. The JPMorgan cyber question uses retained Item 1A, the Exxon greenhouse-gas question uses retained Item 1A, and the Pioneer question uses retained Q2 MD&A; none requires the missing annual financial sections. The BAC rate-sensitivity question uses retained FY2024 MD&A, not its quarterly TOC captures. No evaluated gold passage is absent. These observations do not prove exhaustive answer coverage; pooled labels cannot measure missing passages that were never candidates.

Short substantive market-risk sections (for example Apple's two-chunk Item 7A) are not gaps simply because they have fewer than three chunks. Many quarterly risk items legitimately say there were no material changes or refer readers to the annual risk disclosures; some contain brief new risk updates. Cross-references into retained MD&A (such as BAC's market-risk item) differ from references into an unretained Financial Section. The original stored-corpus audit could not resolve the 22 zero-chunk JNJ/XOM quarterly risk slots. The follow-up cached-HTML audit establishes that these sources have no separate quarterly Item 1A: each contains only an annual 10-K risk reference, not a missed quarterly heading. The per-filing evidence appears below.

### Future parser correction (proposal only)

After explicit M2 acceptance, create a new corpus version: follow same-filing internal anchors and page references from Item 7/7A/8 into the Financial Section, resolve referenced annual-report exhibits when necessary, and collect the substantive MD&A/statements with document/anchor provenance. Detect TOC-only captures and cross-reference-only bodies as coverage warnings requiring resolution rather than successful substantive extraction. Add regression cases for every CVX annual year, JPM/XOM financial sections, BAC/JPM quarterly TOCs and legitimate short risk items; verify complete coverage and avoid duplicate content. Re-embed and review/migrate labels only for that new version. No such repair was performed here, since it could change chunk IDs and invalidate the frozen labels.

This corpus repair is **required before M4**, not an optional later improvement. M4 answers and the M5 B2 stuffed-context baseline depend on substantive JPM/XOM/CVX annual MD&A and financials and BAC/JPM quarterly MD&A. JNJ/XOM quarterly risk handling also needs a verified source-availability status and annual-reference provenance; since those quarterly sections are absent in the sources, the repair must not fabricate them. Verify availability and annual risk resolution before treating these companies as ready for M4/M5. No new corpus is created now and no M3 work is authorized by this note.

### Label migration for the future corpus (proposal only)

Keep this corpus, label file and pre/post-fix results immutable. Build a separate old-ID → new-ID manifest using exact stored-text equality, constrained to the same accession, item and saved fiscal/company filters. Propose an automatic mapping only for a unique exact match; duplicate identical passages require provenance checks and ambiguous one-to-many matches go to student review. List every unmatched old gold ID, old text/provenance and possible new passages for manual review, including chunks changed by corrected boundaries; overlap scores must never silently create replacement gold labels. Save any approved migrated labels separately under the new corpus ID/fingerprint, with student approval of unmatched/ambiguous cases, then rerun retrieval evaluation and disclose corpus/label changes. Do not overwrite `evals/handwritten.jsonl` or retire the current corpus during migration.

## Labeling methodology and limitations

- Gold means answering the question is a main point of the passage; passing mentions do not count.
- When an answer genuinely spans adjacent chunks, each part is gold. A chunk whose only relevant text is the approximately 50-token overlap tail of the previous chunk is not gold.
- Tables showing how much, without explaining why, are not gold for “why” questions.
- For cross-year questions, only the named filing is gold, even if other years contain relevant-looking passages.
- Questions requiring more than three chunks were narrowed, except the deliberately broad six- and seven-gold questions.
- Candidates were pooled across all four modes and supplemented with manual browsing. Judgments are not exhaustive (D022/D028), and the candidate pool comes from the same systems being evaluated. These results describe this frozen, pooled set rather than independently exhaustive retrieval relevance.
- Questions were drafted with AI assistance, then edited, narrowed and gold-labeled by the student, who made all relevance judgments. No questions, filters, labels or reference answers were edited by the evaluation run. Reference answers are retained for later work and are not scored in this retrieval-only evaluation.

For the XOM greenhouse-gas question, `hybrid_rerank` rank 10 (`chk_79f1a3b6352852180da6cca33808189769faa5f67121057bb70f4823b8c9e9db`) comes from the gold filing's FY2024 10-K Item 1A (accession `0000034088-25-000010`) but is unjudged. Labels were intentionally not edited after seeing results; this passage remains unjudged rather than being added to gold retrospectively.

Changes made by the student during labeling:

- JPMorgan cyber: narrowed to why it “cannot guarantee absolute security.”
- Bank of America: made specific to an instantaneous 100 bp rate drop.
- ExxonMobil: narrowed to the 2024 10-K's greenhouse-gas regulation risk; saved XOM-only for cross-year search.
- Walmart: originally asked about eCommerce and advertising. Advertising had no real answer in FY2025 MD&A; the eCommerce half spanned more than three chunks, so it was narrowed to eCommerce's contribution to Walmart U.S. comparable sales. Its two gold chunks contain the same sentence in separate comparable-sales and segment-results sections.
- Coca-Cola bottler relationships: too broad (six or more chunks), narrowed to how concentrate is priced.
- P&G: added “fiscal 2025.”
- Chevron Hess: labeled from Item 1A because the Financial Section is missing.
- J&J Medicare negotiation: the student corrected the initially ticker-only filters to FY2024/FY before this run; question and gold were unchanged, and validation confirms the correction.

## Deferred notes for M3/M4 and question generation

PG ends its fiscal year June 30. The repo search found the incomplete non-December list at **SPEC.md:199 (Section 5)** and **SPEC.md:645 (Section 17)**; no hard-coded copy of that exception list was found in runtime code. Both omit PG. D006 already uses actual report dates, so ingestion is unaffected. Future M3 interface/planner notes, M4 planner prompts and question generation must treat PG as non-December (D029).

Several questions omit a year, including Amazon currency exposure, Meta VR spending, Apple VaR, Microsoft Copilot and Coca-Cola concentrate pricing. M2 applies their saved filters, but an end-to-end agent receiving only question text lacks that temporal scope. Later stages must supply context or clarify the intended filing; do not silently assume these retrieval scores establish period resolution. Add calendar-year-phrased questions to later planner tests, especially for non-December companies. These are to-dos only; M3 has not started.

## Acceptance handoff

No dependencies, schema, parsing, chunking, corpus versions or stored embeddings changed. Results are descriptive; no quality threshold was invented, and the small pooled set is not an untouched independent test set. The student explicitly accepted M2, including the coverage gaps, keyword fix (D031), pooled-label limitations and reranker behavior. Do not begin M3; wait for the student's separate next task.

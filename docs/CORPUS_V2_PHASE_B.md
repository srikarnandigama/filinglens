# Corpus v2: Phase B handoff

Phase B is complete. The new corpus is frozen and ready for the student's labeling review. Phase C evaluation and M3 have not started. V1 remains available and unchanged; the default active corpus has not been switched during this handoff.

- V1: `corpus_2fb48958e274daed46c19e3fbf2583213e308b1eebaa16a04cfdc8052eea82e7` (23,441 chunks).
- V2: `corpus_3f3c2a9affddcc6a29eca9e768c65bcbd3e2f131fb69595b24b9b92005738739` (32,960 chunks, 275 filings, 708 sections).
- Processing fingerprint: `66d14d879f2c1df8a21fa6df2fcd3e39d01d510c3a06cf2a205b0ab2abcca579`.
- Corpus fingerprint: `d6e2dd9856cdf645873078c0505a690615b680346a95d4d591adcf0b3a18809a`.
- Snapshot: `2026-10-19-v1`; no network requests, new dependencies, model downloads or schema migrations.

## Build, embeddings and preservation

The first offline parse took 9.33 minutes. The complete offline ID replay took 10.85 minutes. All 32,960 IDs, text and chunk metadata have identical before/after hashes (`c4eead91afddcab2da5fd181028a0dce30adc35749ff54822c449218d34599a9`). The legacy AAPL/MSFT/NVIDIA fixtures remain unchanged.

Copied 23,395 compatible vectors into new v2 rows only; 9,565 inputs required encoding. The representative 196-chunk sample covered six companies, both forms and 4 oversized rows. It measured 12.76 chunks/second and projected 12.50 minutes for all new inputs (12.24 minutes remaining after the sample). The sample had zero failures/invalid vectors, so the student's <=45-minute pre-approval applied.

The remaining 9,369 new inputs took 11.59 minutes. New encoding totaled 11.84 minutes including benchmark encoding and database commits, or 12.07 minutes including both model loads and warm-ups. Failures: 0; invalid vectors: 0. All 32,960 v2 vectors have the expected model/input hashes, 384 dimensions and unit norms. The shared HNSW index is valid and ready and has been maintained for the new rows.

The preservation audit covers all 730 expected filing/item slots. All 675 slots outside the 55 approved repairs have byte-identical section text, identical serialized blocks, and identical chunk inputs/metadata (including the 22 absent slots). Of the 55 repair slots, 46 now have substantive replacement text; nine Item 7A stubs remain text-identical and point to the recovered Item 7. No substantive source span is owned by two sections; ordinary within-section chunk overlap is unchanged. V1/v2 section and chunk identities are disjoint. V1 rows, labels, reports, M1 facts, availability data and the shared snapshot manifest match their saved integrity hashes.

Coverage diagnostics: 46 resolved bodies; 641 unchanged extracted items; 21 references covered elsewhere; 22 source-absent items. Unresolved substantive references: zero. There are 178 slots with fewer than three chunks, down from 224; short counts alone are not failures.

## Item 7A ownership: all 15 affected annual filings

CVX/JPM/XOM present market risk within MD&A: retain it in Item 7 and retain only the distinct original reference in Item 7A. DIS/NVIDIA present separate market-risk sections: retain those Item 7A spans. BAC/JNJ/PFE/PG's existing MD&A references use the same diagnostic rule.

| Ticker | Fiscal year | Accession | Filing structure | Market-risk owner |
|---|---:|---|---|---|
| CVX | 2023 | 0000093410-24-000013 | MD&A subsection | Item 7 |
| CVX | 2024 | 0000093410-25-000009 | MD&A subsection | Item 7 |
| CVX | 2025 | 0000093410-26-000078 | MD&A subsection | Item 7 |
| DIS | 2023 | 0001744489-23-000216 | separate section outside MD&A | Item 7A |
| DIS | 2024 | 0001744489-24-000276 | separate section outside MD&A | Item 7A |
| DIS | 2025 | 0001744489-25-000155 | separate section outside MD&A | Item 7A |
| JPM | 2023 | 0000019617-24-000225 | MD&A subsection | Item 7 |
| JPM | 2024 | 0000019617-25-000270 | MD&A subsection | Item 7 |
| JPM | 2025 | 0001628280-26-008131 | MD&A subsection | Item 7 |
| NVDA | 2024 | 0001045810-24-000029 | separate section outside MD&A | Item 7A |
| NVDA | 2025 | 0001045810-25-000023 | separate section outside MD&A | Item 7A |
| NVDA | 2026 | 0001045810-26-000021 | separate section outside MD&A | Item 7A |
| XOM | 2023 | 0000034088-24-000018 | MD&A subsection | Item 7 |
| XOM | 2024 | 0000034088-25-000010 | MD&A subsection | Item 7 |
| XOM | 2025 | 0000034088-26-000045 | MD&A subsection | Item 7 |

## Repaired sections

All source content is in the already cached primary HTML. No exhibit download was needed. CVX/JPM/XOM financial chapters supply annual MD&A and financials. Disney's financial appendix is after signatures; NVIDIA's statements are under Part IV/Item 15. BAC's full Item 2 title in the TOC had been selected under the wrong Part state. JPM quarterly MD&A starts at Consolidated Financial Highlights and ends before the actual statements. XOM FY2023 uses the tested heading/page fallback. Anchor destinations, original references, body block boundaries, source URLs and SHA-256 values are in the JSON audit.

| Ticker | FY | Period | Accession | Item | V1 chunks | V2 chunks | Coverage |
|---|---:|---|---|---|---:|---:|---|
| BAC | 2023 | Q1 | 0000070858-23-000142 | P1-2 | 1 | 166 | resolved |
| BAC | 2023 | Q2 | 0000070858-23-000176 | P1-2 | 1 | 208 | resolved |
| BAC | 2023 | Q3 | 0000070858-23-000272 | P1-2 | 1 | 207 | resolved |
| BAC | 2024 | Q1 | 0000070858-24-000156 | P1-2 | 1 | 162 | resolved |
| BAC | 2024 | Q2 | 0000070858-24-000208 | P1-2 | 1 | 204 | resolved |
| BAC | 2024 | Q3 | 0000070858-24-000280 | P1-2 | 1 | 205 | resolved |
| BAC | 2025 | Q1 | 0000070858-25-000200 | P1-2 | 1 | 159 | resolved |
| BAC | 2025 | Q2 | 0000070858-25-000268 | P1-2 | 1 | 199 | resolved |
| BAC | 2025 | Q3 | 0000070858-25-000405 | P1-2 | 1 | 199 | resolved |
| BAC | 2026 | Q1 | 0000070858-26-000249 | P1-2 | 1 | 155 | resolved |
| BAC | 2026 | Q2 | 0000070858-26-000394 | P1-2 | 1 | 192 | resolved |
| CVX | 2023 | FY | 0000093410-24-000013 | 7 | 1 | 72 | resolved |
| CVX | 2023 | FY | 0000093410-24-000013 | 7A | 1 | 1 | reference covered elsewhere |
| CVX | 2023 | FY | 0000093410-24-000013 | 8 | 1 | 214 | resolved |
| CVX | 2024 | FY | 0000093410-25-000009 | 7 | 1 | 78 | resolved |
| CVX | 2024 | FY | 0000093410-25-000009 | 7A | 1 | 1 | reference covered elsewhere |
| CVX | 2024 | FY | 0000093410-25-000009 | 8 | 1 | 219 | resolved |
| CVX | 2025 | FY | 0000093410-26-000078 | 7 | 1 | 78 | resolved |
| CVX | 2025 | FY | 0000093410-26-000078 | 7A | 1 | 1 | reference covered elsewhere |
| CVX | 2025 | FY | 0000093410-26-000078 | 8 | 1 | 224 | resolved |
| DIS | 2023 | FY | 0001744489-23-000216 | 8 | 1 | 133 | resolved |
| DIS | 2024 | FY | 0001744489-24-000276 | 8 | 1 | 143 | resolved |
| DIS | 2025 | FY | 0001744489-25-000155 | 8 | 1 | 138 | resolved |
| JPM | 2023 | FY | 0000019617-24-000225 | 7 | 1 | 317 | resolved |
| JPM | 2023 | FY | 0000019617-24-000225 | 7A | 1 | 1 | reference covered elsewhere |
| JPM | 2023 | FY | 0000019617-24-000225 | 8 | 1 | 509 | resolved |
| JPM | 2023 | Q1 | 0000019617-23-000310 | P1-2 | 1 | 207 | resolved |
| JPM | 2023 | Q2 | 0000019617-23-000432 | P1-2 | 1 | 291 | resolved |
| JPM | 2023 | Q3 | 0000019617-23-000524 | P1-2 | 1 | 294 | resolved |
| JPM | 2024 | FY | 0000019617-25-000270 | 7 | 1 | 297 | resolved |
| JPM | 2024 | FY | 0000019617-25-000270 | 7A | 1 | 1 | reference covered elsewhere |
| JPM | 2024 | FY | 0000019617-25-000270 | 8 | 1 | 507 | resolved |
| JPM | 2024 | Q1 | 0000019617-24-000326 | P1-2 | 1 | 219 | resolved |
| JPM | 2024 | Q2 | 0000019617-24-000453 | P1-2 | 1 | 269 | resolved |
| JPM | 2024 | Q3 | 0000019617-24-000611 | P1-2 | 1 | 269 | resolved |
| JPM | 2025 | FY | 0001628280-26-008131 | 7 | 1 | 295 | resolved |
| JPM | 2025 | FY | 0001628280-26-008131 | 7A | 1 | 1 | reference covered elsewhere |
| JPM | 2025 | FY | 0001628280-26-008131 | 8 | 1 | 506 | resolved |
| JPM | 2025 | Q1 | 0000019617-25-000421 | P1-2 | 1 | 200 | resolved |
| JPM | 2025 | Q2 | 0000019617-25-000615 | P1-2 | 1 | 253 | resolved |
| JPM | 2025 | Q3 | 0001628280-25-048859 | P1-2 | 1 | 259 | resolved |
| JPM | 2026 | Q1 | 0001628280-26-029344 | P1-2 | 1 | 206 | resolved |
| JPM | 2026 | Q2 | 0001628280-26-054343 | P1-2 | 1 | 261 | resolved |
| NVDA | 2024 | FY | 0001045810-24-000029 | 8 | 1 | 81 | resolved |
| NVDA | 2025 | FY | 0001045810-25-000023 | 8 | 1 | 80 | resolved |
| NVDA | 2026 | FY | 0001045810-26-000021 | 8 | 1 | 76 | resolved |
| XOM | 2023 | FY | 0000034088-24-000018 | 7 | 1 | 82 | resolved |
| XOM | 2023 | FY | 0000034088-24-000018 | 7A | 1 | 1 | reference covered elsewhere |
| XOM | 2023 | FY | 0000034088-24-000018 | 8 | 1 | 190 | resolved |
| XOM | 2024 | FY | 0000034088-25-000010 | 7 | 1 | 83 | resolved |
| XOM | 2024 | FY | 0000034088-25-000010 | 7A | 1 | 1 | reference covered elsewhere |
| XOM | 2024 | FY | 0000034088-25-000010 | 8 | 1 | 202 | resolved |
| XOM | 2025 | FY | 0000034088-26-000045 | 7 | 1 | 83 | resolved |
| XOM | 2025 | FY | 0000034088-26-000045 | 7A | 1 | 1 | reference covered elsewhere |
| XOM | 2025 | FY | 0000034088-26-000045 | 8 | 1 | 174 | resolved |

## Source-absent quarterly risk items

All 11 JNJ and all 11 XOM quarterly filings lack a quarterly Item 1A heading/body. The only Item 1A mention is an annual-report prose reference (sometimes split across adjacent source blocks). No risk section or chunk was synthesized. Each row below has zero chunks in both corpora; the JSON audit includes its source URL, full SHA-256 and the verified annual-reference excerpt.

| Ticker | FY | Period | Accession | Source SHA-256 |
|---|---:|---|---|---|
| JNJ | 2023 | Q1 | 0000200406-23-000056 | `ea78856ad949cc92569960762ce2cab8acd426e16016ec947c482aa9432022ac` |
| JNJ | 2023 | Q2 | 0000200406-23-000082 | `9e421d548bc3b1483a64197db1be51e3a78a3abc00c59bf09100829da955bdd3` |
| JNJ | 2023 | Q3 | 0000200406-23-000102 | `75508a5148c159261d7e4463e0dfeb416d5269a81493e788fa9eaa9fbdd8094e` |
| JNJ | 2024 | Q1 | 0000200406-24-000049 | `a57604a996759a3443269f0d32062f96608a6eec60b14282ae9707e7bd9f7f87` |
| JNJ | 2024 | Q2 | 0000200406-24-000075 | `55ba13bc2c9cea28f9c6df9e56352695404120b5bb8133bd449a5dd4d21f4a5c` |
| JNJ | 2024 | Q3 | 0000200406-24-000096 | `c82c85144f20a54333a7232f9ca5deac1dfa97dd4595b00ad0f7dfe1a6cc7e7b` |
| JNJ | 2025 | Q1 | 0000200406-25-000119 | `d61143897847378898ca9573da2d3ef56e91e01a3f1529a6684a8610287b0943` |
| JNJ | 2025 | Q2 | 0000200406-25-000178 | `aab16d8108ee115904ccf437813b0f26f8c9e21a48f2c0c55b49689a36f8c1f6` |
| JNJ | 2025 | Q3 | 0000200406-25-000209 | `736f5d07c5ae26db30162993d62666b5c077ac941802fa09dd9f1bb4a2c291a8` |
| JNJ | 2026 | Q1 | 0000200406-26-000087 | `60712965f6f58103a391103f10a2c1577e7c2834342be8de11fa800f3973fbba` |
| JNJ | 2026 | Q2 | 0000200406-26-000153 | `f92ac3aa89b2c30ded4991b34513c257e9a440d3e7d9f867700c7b3bac3a2b41` |
| XOM | 2023 | Q1 | 0000034088-23-000030 | `e612b4dc12ed91b20c42ccdeb2bb9c0bb38497883c1aa7a5b25bf216c22907f7` |
| XOM | 2023 | Q2 | 0000034088-23-000048 | `ea27f6227dbe48ce4d8358766e15b0ddb80115489dd3f40a5c98767462813908` |
| XOM | 2023 | Q3 | 0000034088-23-000056 | `affed6107047a773f34034062fe59e4a006f15fc62ef619e19508e58256082b5` |
| XOM | 2024 | Q1 | 0000034088-24-000029 | `b04e0bdb6244f2401b134efca2e47d326b3a36d57a40f11eaeabb2cbe1d9cebe` |
| XOM | 2024 | Q2 | 0000034088-24-000050 | `be23287e4ce5579bda85e924b5b64b9ddbc3b69f7bfef65bd2a5f6fa3a56869e` |
| XOM | 2024 | Q3 | 0000034088-24-000068 | `678f419c38638ba8ca2784d7ae916bdab19c12655cc6e5d48000f1b24e0f40c6` |
| XOM | 2025 | Q1 | 0000034088-25-000024 | `b679836878a9aaeb4219718eb8cf6d692e0b6728268eb06a8042e14d2e36e0bd` |
| XOM | 2025 | Q2 | 0000034088-25-000042 | `9f5bf4c0a2ee90cedc7a7d1f1eb29fb137ae7bdb1624d0dfe1f6a87dde1edcf3` |
| XOM | 2025 | Q3 | 0000034088-25-000061 | `96d03c42e9619d74c3948f72837f2b42b879d864052958d5097052c0f7c9a8cd` |
| XOM | 2026 | Q1 | 0000034088-26-000067 | `aa46cd8d6f08e92202bec6a79b47adc6eee0bd1118cf0b196bffa7e1320b8719` |
| XOM | 2026 | Q2 | 0000034088-26-000093 | `516a7d936371c7c508978a6915b57577d02b33aad3cb4410158701725ae7d327` |

## Gold migration and six-question review list

All 30 records and 61 old gold IDs map uniquely by exact stored text within the same accession and item. Unmatched: 0; ambiguous: 0. Questions, filters, reference answers and all other non-corpus fields are unchanged. Only corpus identity/fingerprint and the corresponding chunk IDs changed. No relevance judgments were added or removed. The machine-readable [migration manifest](../evals/corpus_v2_migration.json) lists every old/new gold-ID pair. The separate [v2 labels](../evals/handwritten_v2.jsonl) are ready for `:edit`.

These six saved filter scopes include repaired sections. The other 24 do not. Review newly available passages without assuming they are relevant merely because they were recovered.

| Question ID | Existing question | Saved filters | Repaired scope |
|---|---|---|---|
| `hq_74fd7fdce150403baad26a906223ba57` | What happens to Chevron if oil prices stay low for a long time? | `{"fiscal_period": "FY", "fiscal_year": 2024, "ticker": "CVX"}` | FY2024: 7, 7A, 8 |
| `hq_8c86cd7564ba43deb72940f9fe800767` | How did Disney explain the improvement in Direct-to-Consumer operating income in fiscal 2024? | `{"fiscal_period": "FY", "fiscal_year": 2024, "ticker": "DIS"}` | FY2024: 8 |
| `hq_9e6c0c0dbb5941589c85ed5a923d944e` | In fiscal 2025, how did NVIDIA describe the risk of U.S. export controls on sales to China? | `{"ticker": "NVDA"}` | FY2024: 8; FY2025: 8; FY2026: 8 |
| `hq_af3e0e0473af430b83dd4dc7e4bb1eef` | Why does JPMorgan Chase say it cannot guarantee absolute security against cyberattacks? | `{"fiscal_period": "FY", "fiscal_year": 2024, "ticker": "JPM"}` | FY2024: 7, 7A, 8 |
| `hq_e9bf3b51fc6948de9eaa071fdbdb0e46` | As of its fiscal 2024 10-K, what was the status of Chevron's Hess acquisition and the Stabroek arbitration? | `{"ticker": "CVX"}` | FY2023: 7, 7A, 8; FY2024: 7, 7A, 8; FY2025: 7, 7A, 8 |
| `hq_efbdb0ea523543c699eddddde9b1e638` | How does ExxonMobil's 2024 10-K say greenhouse gas regulations could hurt its business? | `{"ticker": "XOM"}` | FY2023: 7, 7A, 8; FY2024: 7, 7A, 8; FY2025: 7, 7A, 8 |

Launch the existing CLI from PowerShell:

```powershell
.venv/Scripts/python.exe -m evals.label_retrieval --corpus corpus_3f3c2a9affddcc6a29eca9e768c65bcbd3e2f131fb69595b24b9b92005738739 --output evals/handwritten_v2.jsonl --depth 30
```

At the prompt, use `:edit QUESTION_ID` with an ID above. The smoke test opened an actual migrated record, searched all four modes at depth 30 and quit without saving; finalized label bytes stayed unchanged and its temporary draft was removed. See the completion JSON for the record and pool counts.

## Checks, artifacts and commands

Ruff lint and format checks pass. Full pytest: **89 passed, 1 skipped**. The skipped test is the opt-in legacy production replay. It was replaced for this build by the complete v2 replay above; v1 was not reparsed. Database regression tests use isolated schemas, including the M1 cache replay. The tests cover all 15 affected annuals, all three XOM years including FY2023 fallback, quarterly BAC/JPM boundaries, all 22 absent risk items, offline missing/tampered cache rejection, no HTTP-client construction, unchanged legacy fixtures, normal-stage NVIDIA expansion, deterministic replay and freeze-audit enforcement. Retrieval implementation, D031 keyword semantics, RRF 60 and model revisions were not changed.

Code changed: `filinglens/ingest/{corpus,pipeline,embed}.py`, new `resolve.py` and `offline.py`, `evals/label_retrieval.py`, new `evals/corpus_v2.py`, `tests/test_database.py`, and new `tests/test_corpus_v2{,_database}.py`. Decisions D033-D035 record the approved design. Existing unrelated working-tree edits were preserved.

Artifacts: [full 730-slot audit](CORPUS_V2_AUDIT.json), [integrity baseline](CORPUS_V2_BASELINE.json), [parse](CORPUS_V2_PARSE.json), [replay](CORPUS_V2_REPLAY.json), [vector reuse](CORPUS_V2_REUSE.json), [benchmark](CORPUS_V2_EMBED_BENCHMARK.json), [remaining embedding run](CORPUS_V2_EMBED_FULL.json), [completion/CLI/index checks](CORPUS_V2_COMPLETION.json), and the migration/label files linked above.

Commands run from the project root (each corpus action below used this literal v2 ID):

```powershell
.venv/Scripts/python.exe -m filinglens.ingest.pipeline --stage parse --offline
.venv/Scripts/python.exe -m filinglens.ingest.pipeline --stage parse --offline --force
.venv/Scripts/python.exe -m evals.corpus_v2 audit --corpus corpus_3f3c2a9affddcc6a29eca9e768c65bcbd3e2f131fb69595b24b9b92005738739
.venv/Scripts/python.exe -m evals.corpus_v2 reuse --corpus corpus_3f3c2a9affddcc6a29eca9e768c65bcbd3e2f131fb69595b24b9b92005738739
.venv/Scripts/python.exe -m evals.corpus_v2 migrate --corpus corpus_3f3c2a9affddcc6a29eca9e768c65bcbd3e2f131fb69595b24b9b92005738739
$env:HF_HUB_OFFLINE='1'
$env:TRANSFORMERS_OFFLINE='1'
.venv/Scripts/python.exe -u -m filinglens.ingest.embed --corpus corpus_3f3c2a9affddcc6a29eca9e768c65bcbd3e2f131fb69595b24b9b92005738739 --sample-size 192 --output docs/CORPUS_V2_EMBED_BENCHMARK.json
# Verified zero sample failures/invalid vectors and projected_new_seconds + load + warmup <= 2700.
.venv/Scripts/python.exe -u -m filinglens.ingest.embed --corpus corpus_3f3c2a9affddcc6a29eca9e768c65bcbd3e2f131fb69595b24b9b92005738739 --full --output docs/CORPUS_V2_EMBED_FULL.json
.venv/Scripts/python.exe -m evals.corpus_v2 freeze --corpus corpus_3f3c2a9affddcc6a29eca9e768c65bcbd3e2f131fb69595b24b9b92005738739
$env:FILINGLENS_TEST_DB='1'
$env:FILINGLENS_TEST_CORPUS_REPLAY='0'
.venv/Scripts/python.exe -m ruff check
.venv/Scripts/python.exe -m ruff format --check
.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider --basetemp=data/pytest-corpus-v2-complete
```

Additional read-only Python checks captured the baseline, compared replay hashes, validated migrated record fields, verified exact copied vectors/model/input hashes, checked the HNSW catalog and exercised the CLI with `:edit` followed by `quit`. Their results are saved in the linked JSON artifacts. No retrieval evaluation command was run.

## Full v1-versus-v2 filing/item inventory

All 730 expected slots are included. 'Same bytes' compares section text (including absence); the JSON also records serialized-block and complete chunk-input equality. Short extracted sections are visible below but are not automatically coverage failures.

| Ticker | FY | Period | Form | Accession | Item | V1 | V2 | Coverage / warning | Same bytes |
|---|---:|---|---|---|---|---:|---:|---|---|
| AAPL | 2023 | FY | 10-K | 0000320193-23-000106 | 1 | 8 | 8 | extracted | yes |
| AAPL | 2023 | FY | 10-K | 0000320193-23-000106 | 1A | 40 | 40 | extracted | yes |
| AAPL | 2023 | FY | 10-K | 0000320193-23-000106 | 7 | 11 | 11 | extracted | yes |
| AAPL | 2023 | FY | 10-K | 0000320193-23-000106 | 7A | 2 | 2 | extracted; short (no unresolved reference detected) | yes |
| AAPL | 2023 | FY | 10-K | 0000320193-23-000106 | 8 | 54 | 54 | extracted | yes |
| AAPL | 2023 | Q1 | 10-Q | 0000320193-23-000006 | P1-2 | 12 | 12 | extracted | yes |
| AAPL | 2023 | Q1 | 10-Q | 0000320193-23-000006 | P2-1A | 1 | 1 | extracted; short (no unresolved reference detected) | yes |
| AAPL | 2023 | Q2 | 10-Q | 0000320193-23-000064 | P1-2 | 14 | 14 | extracted | yes |
| AAPL | 2023 | Q2 | 10-Q | 0000320193-23-000064 | P2-1A | 1 | 1 | extracted; short (no unresolved reference detected) | yes |
| AAPL | 2023 | Q3 | 10-Q | 0000320193-23-000077 | P1-2 | 13 | 13 | extracted | yes |
| AAPL | 2023 | Q3 | 10-Q | 0000320193-23-000077 | P2-1A | 1 | 1 | extracted; short (no unresolved reference detected) | yes |
| AAPL | 2024 | FY | 10-K | 0000320193-24-000123 | 1 | 9 | 9 | extracted | yes |
| AAPL | 2024 | FY | 10-K | 0000320193-24-000123 | 1A | 39 | 39 | extracted | yes |
| AAPL | 2024 | FY | 10-K | 0000320193-24-000123 | 7 | 12 | 12 | extracted | yes |
| AAPL | 2024 | FY | 10-K | 0000320193-24-000123 | 7A | 2 | 2 | extracted; short (no unresolved reference detected) | yes |
| AAPL | 2024 | FY | 10-K | 0000320193-24-000123 | 8 | 52 | 52 | extracted | yes |
| AAPL | 2024 | Q1 | 10-Q | 0000320193-24-000006 | P1-2 | 11 | 11 | extracted | yes |
| AAPL | 2024 | Q1 | 10-Q | 0000320193-24-000006 | P2-1A | 3 | 3 | extracted | yes |
| AAPL | 2024 | Q2 | 10-Q | 0000320193-24-000069 | P1-2 | 13 | 13 | extracted | yes |
| AAPL | 2024 | Q2 | 10-Q | 0000320193-24-000069 | P2-1A | 3 | 3 | extracted | yes |
| AAPL | 2024 | Q3 | 10-Q | 0000320193-24-000081 | P1-2 | 13 | 13 | extracted | yes |
| AAPL | 2024 | Q3 | 10-Q | 0000320193-24-000081 | P2-1A | 1 | 1 | extracted; short (no unresolved reference detected) | yes |
| AAPL | 2025 | FY | 10-K | 0000320193-25-000079 | 1 | 9 | 9 | extracted | yes |
| AAPL | 2025 | FY | 10-K | 0000320193-25-000079 | 1A | 40 | 40 | extracted | yes |
| AAPL | 2025 | FY | 10-K | 0000320193-25-000079 | 7 | 14 | 14 | extracted | yes |
| AAPL | 2025 | FY | 10-K | 0000320193-25-000079 | 7A | 2 | 2 | extracted; short (no unresolved reference detected) | yes |
| AAPL | 2025 | FY | 10-K | 0000320193-25-000079 | 8 | 53 | 53 | extracted | yes |
| AAPL | 2025 | Q1 | 10-Q | 0000320193-25-000008 | P1-2 | 10 | 10 | extracted | yes |
| AAPL | 2025 | Q1 | 10-Q | 0000320193-25-000008 | P2-1A | 7 | 7 | extracted | yes |
| AAPL | 2025 | Q2 | 10-Q | 0000320193-25-000057 | P1-2 | 15 | 15 | extracted | yes |
| AAPL | 2025 | Q2 | 10-Q | 0000320193-25-000057 | P2-1A | 8 | 8 | extracted | yes |
| AAPL | 2025 | Q3 | 10-Q | 0000320193-25-000073 | P1-2 | 14 | 14 | extracted | yes |
| AAPL | 2025 | Q3 | 10-Q | 0000320193-25-000073 | P2-1A | 1 | 1 | extracted; short (no unresolved reference detected) | yes |
| AAPL | 2026 | Q1 | 10-Q | 0000320193-26-000006 | P1-2 | 12 | 12 | extracted | yes |
| AAPL | 2026 | Q1 | 10-Q | 0000320193-26-000006 | P2-1A | 1 | 1 | extracted; short (no unresolved reference detected) | yes |
| AAPL | 2026 | Q2 | 10-Q | 0000320193-26-000013 | P1-2 | 17 | 17 | extracted | yes |
| AAPL | 2026 | Q2 | 10-Q | 0000320193-26-000013 | P2-1A | 16 | 16 | extracted | yes |
| AAPL | 2026 | Q3 | 10-Q | 0000320193-26-000020 | P1-2 | 16 | 16 | extracted | yes |
| AAPL | 2026 | Q3 | 10-Q | 0000320193-26-000020 | P2-1A | 14 | 14 | extracted | yes |
| AMZN | 2023 | FY | 10-K | 0001018724-24-000008 | 1 | 8 | 8 | extracted | yes |
| AMZN | 2023 | FY | 10-K | 0001018724-24-000008 | 1A | 35 | 35 | extracted | yes |
| AMZN | 2023 | FY | 10-K | 0001018724-24-000008 | 7 | 32 | 32 | extracted | yes |
| AMZN | 2023 | FY | 10-K | 0001018724-24-000008 | 7A | 6 | 6 | extracted | yes |
| AMZN | 2023 | FY | 10-K | 0001018724-24-000008 | 8 | 95 | 95 | extracted | yes |
| AMZN | 2023 | Q1 | 10-Q | 0001018724-23-000008 | P1-2 | 27 | 27 | extracted | yes |
| AMZN | 2023 | Q1 | 10-Q | 0001018724-23-000008 | P2-1A | 35 | 35 | extracted | yes |
| AMZN | 2023 | Q2 | 10-Q | 0001018724-23-000012 | P1-2 | 31 | 31 | extracted | yes |
| AMZN | 2023 | Q2 | 10-Q | 0001018724-23-000012 | P2-1A | 35 | 35 | extracted | yes |
| AMZN | 2023 | Q3 | 10-Q | 0001018724-23-000018 | P1-2 | 33 | 33 | extracted | yes |
| AMZN | 2023 | Q3 | 10-Q | 0001018724-23-000018 | P2-1A | 35 | 35 | extracted | yes |
| AMZN | 2024 | FY | 10-K | 0001018724-25-000004 | 1 | 10 | 10 | extracted | yes |
| AMZN | 2024 | FY | 10-K | 0001018724-25-000004 | 1A | 35 | 35 | extracted | yes |
| AMZN | 2024 | FY | 10-K | 0001018724-25-000004 | 7 | 32 | 32 | extracted | yes |
| AMZN | 2024 | FY | 10-K | 0001018724-25-000004 | 7A | 6 | 6 | extracted | yes |
| AMZN | 2024 | FY | 10-K | 0001018724-25-000004 | 8 | 95 | 95 | extracted | yes |
| AMZN | 2024 | Q1 | 10-Q | 0001018724-24-000083 | P1-2 | 27 | 27 | extracted | yes |
| AMZN | 2024 | Q1 | 10-Q | 0001018724-24-000083 | P2-1A | 37 | 37 | extracted | yes |
| AMZN | 2024 | Q2 | 10-Q | 0001018724-24-000130 | P1-2 | 32 | 32 | extracted | yes |
| AMZN | 2024 | Q2 | 10-Q | 0001018724-24-000130 | P2-1A | 37 | 37 | extracted | yes |
| AMZN | 2024 | Q3 | 10-Q | 0001018724-24-000161 | P1-2 | 32 | 32 | extracted | yes |
| AMZN | 2024 | Q3 | 10-Q | 0001018724-24-000161 | P2-1A | 37 | 37 | extracted | yes |
| AMZN | 2025 | FY | 10-K | 0001018724-26-000004 | 1 | 10 | 10 | extracted | yes |
| AMZN | 2025 | FY | 10-K | 0001018724-26-000004 | 1A | 36 | 36 | extracted | yes |
| AMZN | 2025 | FY | 10-K | 0001018724-26-000004 | 7 | 29 | 29 | extracted | yes |
| AMZN | 2025 | FY | 10-K | 0001018724-26-000004 | 7A | 6 | 6 | extracted | yes |
| AMZN | 2025 | FY | 10-K | 0001018724-26-000004 | 8 | 98 | 98 | extracted | yes |
| AMZN | 2025 | Q1 | 10-Q | 0001018724-25-000036 | P1-2 | 25 | 25 | extracted | yes |
| AMZN | 2025 | Q1 | 10-Q | 0001018724-25-000036 | P2-1A | 35 | 35 | extracted | yes |
| AMZN | 2025 | Q2 | 10-Q | 0001018724-25-000086 | P1-2 | 29 | 29 | extracted | yes |
| AMZN | 2025 | Q2 | 10-Q | 0001018724-25-000086 | P2-1A | 35 | 35 | extracted | yes |
| AMZN | 2025 | Q3 | 10-Q | 0001018724-25-000123 | P1-2 | 30 | 30 | extracted | yes |
| AMZN | 2025 | Q3 | 10-Q | 0001018724-25-000123 | P2-1A | 35 | 35 | extracted | yes |
| AMZN | 2026 | Q1 | 10-Q | 0001018724-26-000014 | P1-2 | 25 | 25 | extracted | yes |
| AMZN | 2026 | Q1 | 10-Q | 0001018724-26-000014 | P2-1A | 36 | 36 | extracted | yes |
| AMZN | 2026 | Q2 | 10-Q | 0001018724-26-000026 | P1-2 | 30 | 30 | extracted | yes |
| AMZN | 2026 | Q2 | 10-Q | 0001018724-26-000026 | P2-1A | 36 | 36 | extracted | yes |
| BAC | 2023 | FY | 10-K | 0000070858-24-000122 | 1 | 25 | 25 | extracted | yes |
| BAC | 2023 | FY | 10-K | 0000070858-24-000122 | 1A | 74 | 74 | extracted | yes |
| BAC | 2023 | FY | 10-K | 0000070858-24-000122 | 7 | 246 | 246 | extracted | yes |
| BAC | 2023 | FY | 10-K | 0000070858-24-000122 | 7A | 1 | 1 | reference covered elsewhere | yes |
| BAC | 2023 | FY | 10-K | 0000070858-24-000122 | 8 | 380 | 380 | extracted | yes |
| BAC | 2023 | Q1 | 10-Q | 0000070858-23-000142 | P1-2 | 1 | 166 | resolved | approved repair |
| BAC | 2023 | Q1 | 10-Q | 0000070858-23-000142 | P2-1A | 1 | 1 | extracted; short (no unresolved reference detected) | yes |
| BAC | 2023 | Q2 | 10-Q | 0000070858-23-000176 | P1-2 | 1 | 208 | resolved | approved repair |
| BAC | 2023 | Q2 | 10-Q | 0000070858-23-000176 | P2-1A | 1 | 1 | extracted; short (no unresolved reference detected) | yes |
| BAC | 2023 | Q3 | 10-Q | 0000070858-23-000272 | P1-2 | 1 | 207 | resolved | approved repair |
| BAC | 2023 | Q3 | 10-Q | 0000070858-23-000272 | P2-1A | 1 | 1 | extracted; short (no unresolved reference detected) | yes |
| BAC | 2024 | FY | 10-K | 0000070858-25-000139 | 1 | 25 | 25 | extracted | yes |
| BAC | 2024 | FY | 10-K | 0000070858-25-000139 | 1A | 77 | 77 | extracted | yes |
| BAC | 2024 | FY | 10-K | 0000070858-25-000139 | 7 | 244 | 244 | extracted | yes |
| BAC | 2024 | FY | 10-K | 0000070858-25-000139 | 7A | 1 | 1 | reference covered elsewhere | yes |
| BAC | 2024 | FY | 10-K | 0000070858-25-000139 | 8 | 376 | 376 | extracted | yes |
| BAC | 2024 | Q1 | 10-Q | 0000070858-24-000156 | P1-2 | 1 | 162 | resolved | approved repair |
| BAC | 2024 | Q1 | 10-Q | 0000070858-24-000156 | P2-1A | 1 | 1 | extracted; short (no unresolved reference detected) | yes |
| BAC | 2024 | Q2 | 10-Q | 0000070858-24-000208 | P1-2 | 1 | 204 | resolved | approved repair |
| BAC | 2024 | Q2 | 10-Q | 0000070858-24-000208 | P2-1A | 1 | 1 | extracted; short (no unresolved reference detected) | yes |
| BAC | 2024 | Q3 | 10-Q | 0000070858-24-000280 | P1-2 | 1 | 205 | resolved | approved repair |
| BAC | 2024 | Q3 | 10-Q | 0000070858-24-000280 | P2-1A | 1 | 1 | extracted; short (no unresolved reference detected) | yes |
| BAC | 2025 | FY | 10-K | 0000070858-26-000157 | 1 | 25 | 25 | extracted | yes |
| BAC | 2025 | FY | 10-K | 0000070858-26-000157 | 1A | 77 | 77 | extracted | yes |
| BAC | 2025 | FY | 10-K | 0000070858-26-000157 | 7 | 242 | 242 | extracted | yes |
| BAC | 2025 | FY | 10-K | 0000070858-26-000157 | 7A | 1 | 1 | reference covered elsewhere | yes |
| BAC | 2025 | FY | 10-K | 0000070858-26-000157 | 8 | 378 | 378 | extracted | yes |
| BAC | 2025 | Q1 | 10-Q | 0000070858-25-000200 | P1-2 | 1 | 159 | resolved | approved repair |
| BAC | 2025 | Q1 | 10-Q | 0000070858-25-000200 | P2-1A | 1 | 1 | extracted; short (no unresolved reference detected) | yes |
| BAC | 2025 | Q2 | 10-Q | 0000070858-25-000268 | P1-2 | 1 | 199 | resolved | approved repair |
| BAC | 2025 | Q2 | 10-Q | 0000070858-25-000268 | P2-1A | 1 | 1 | extracted; short (no unresolved reference detected) | yes |
| BAC | 2025 | Q3 | 10-Q | 0000070858-25-000405 | P1-2 | 1 | 199 | resolved | approved repair |
| BAC | 2025 | Q3 | 10-Q | 0000070858-25-000405 | P2-1A | 1 | 1 | extracted; short (no unresolved reference detected) | yes |
| BAC | 2026 | Q1 | 10-Q | 0000070858-26-000249 | P1-2 | 1 | 155 | resolved | approved repair |
| BAC | 2026 | Q1 | 10-Q | 0000070858-26-000249 | P2-1A | 1 | 1 | extracted; short (no unresolved reference detected) | yes |
| BAC | 2026 | Q2 | 10-Q | 0000070858-26-000394 | P1-2 | 1 | 192 | resolved | approved repair |
| BAC | 2026 | Q2 | 10-Q | 0000070858-26-000394 | P2-1A | 1 | 1 | extracted; short (no unresolved reference detected) | yes |
| COST | 2024 | FY | 10-K | 0000909832-24-000049 | 1 | 14 | 14 | extracted | yes |
| COST | 2024 | FY | 10-K | 0000909832-24-000049 | 1A | 24 | 24 | extracted | yes |
| COST | 2024 | FY | 10-K | 0000909832-24-000049 | 7 | 20 | 20 | extracted | yes |
| COST | 2024 | FY | 10-K | 0000909832-24-000049 | 7A | 3 | 3 | extracted | yes |
| COST | 2024 | FY | 10-K | 0000909832-24-000049 | 8 | 70 | 70 | extracted | yes |
| COST | 2024 | Q1 | 10-Q | 0000909832-23-000065 | P1-2 | 19 | 19 | extracted | yes |
| COST | 2024 | Q1 | 10-Q | 0000909832-23-000065 | P2-1A | 1 | 1 | extracted; short (no unresolved reference detected) | yes |
| COST | 2024 | Q2 | 10-Q | 0000909832-24-000017 | P1-2 | 22 | 22 | extracted | yes |
| COST | 2024 | Q2 | 10-Q | 0000909832-24-000017 | P2-1A | 1 | 1 | extracted; short (no unresolved reference detected) | yes |
| COST | 2024 | Q3 | 10-Q | 0000909832-24-000029 | P1-2 | 23 | 23 | extracted | yes |
| COST | 2024 | Q3 | 10-Q | 0000909832-24-000029 | P2-1A | 1 | 1 | extracted; short (no unresolved reference detected) | yes |
| COST | 2025 | FY | 10-K | 0000909832-25-000101 | 1 | 13 | 13 | extracted | yes |
| COST | 2025 | FY | 10-K | 0000909832-25-000101 | 1A | 25 | 25 | extracted | yes |
| COST | 2025 | FY | 10-K | 0000909832-25-000101 | 7 | 20 | 20 | extracted | yes |
| COST | 2025 | FY | 10-K | 0000909832-25-000101 | 7A | 3 | 3 | extracted | yes |
| COST | 2025 | FY | 10-K | 0000909832-25-000101 | 8 | 67 | 67 | extracted | yes |
| COST | 2025 | Q1 | 10-Q | 0000909832-24-000079 | P1-2 | 19 | 19 | extracted | yes |
| COST | 2025 | Q1 | 10-Q | 0000909832-24-000079 | P2-1A | 1 | 1 | extracted; short (no unresolved reference detected) | yes |
| COST | 2025 | Q2 | 10-Q | 0000909832-25-000015 | P1-2 | 22 | 22 | extracted | yes |
| COST | 2025 | Q2 | 10-Q | 0000909832-25-000015 | P2-1A | 1 | 1 | extracted; short (no unresolved reference detected) | yes |
| COST | 2025 | Q3 | 10-Q | 0000909832-25-000033 | P1-2 | 23 | 23 | extracted | yes |
| COST | 2025 | Q3 | 10-Q | 0000909832-25-000033 | P2-1A | 1 | 1 | extracted; short (no unresolved reference detected) | yes |
| COST | 2026 | FY | 10-K | 0000909832-26-000093 | 1 | 13 | 13 | extracted | yes |
| COST | 2026 | FY | 10-K | 0000909832-26-000093 | 1A | 27 | 27 | extracted | yes |
| COST | 2026 | FY | 10-K | 0000909832-26-000093 | 7 | 20 | 20 | extracted | yes |
| COST | 2026 | FY | 10-K | 0000909832-26-000093 | 7A | 3 | 3 | extracted | yes |
| COST | 2026 | FY | 10-K | 0000909832-26-000093 | 8 | 69 | 69 | extracted | yes |
| COST | 2026 | Q1 | 10-Q | 0000909832-25-000169 | P1-2 | 18 | 18 | extracted | yes |
| COST | 2026 | Q1 | 10-Q | 0000909832-25-000169 | P2-1A | 1 | 1 | extracted; short (no unresolved reference detected) | yes |
| COST | 2026 | Q2 | 10-Q | 0000909832-26-000029 | P1-2 | 24 | 24 | extracted | yes |
| COST | 2026 | Q2 | 10-Q | 0000909832-26-000029 | P2-1A | 1 | 1 | extracted; short (no unresolved reference detected) | yes |
| COST | 2026 | Q3 | 10-Q | 0000909832-26-000051 | P1-2 | 25 | 25 | extracted | yes |
| COST | 2026 | Q3 | 10-Q | 0000909832-26-000051 | P2-1A | 1 | 1 | extracted; short (no unresolved reference detected) | yes |
| CVX | 2023 | FY | 10-K | 0000093410-24-000013 | 1 | 56 | 56 | extracted | yes |
| CVX | 2023 | FY | 10-K | 0000093410-24-000013 | 1A | 24 | 24 | extracted | yes |
| CVX | 2023 | FY | 10-K | 0000093410-24-000013 | 7 | 1 | 72 | resolved | approved repair |
| CVX | 2023 | FY | 10-K | 0000093410-24-000013 | 7A | 1 | 1 | reference covered elsewhere | yes |
| CVX | 2023 | FY | 10-K | 0000093410-24-000013 | 8 | 1 | 214 | resolved | approved repair |
| CVX | 2023 | Q1 | 10-Q | 0000093410-23-000066 | P1-2 | 30 | 30 | extracted | yes |
| CVX | 2023 | Q1 | 10-Q | 0000093410-23-000066 | P2-1A | 1 | 1 | extracted; short (no unresolved reference detected) | yes |
| CVX | 2023 | Q2 | 10-Q | 0000093410-23-000079 | P1-2 | 41 | 41 | extracted | yes |
| CVX | 2023 | Q2 | 10-Q | 0000093410-23-000079 | P2-1A | 2 | 2 | extracted; short (no unresolved reference detected) | yes |
| CVX | 2023 | Q3 | 10-Q | 0000093410-23-000088 | P1-2 | 41 | 41 | extracted | yes |
| CVX | 2023 | Q3 | 10-Q | 0000093410-23-000088 | P2-1A | 2 | 2 | extracted; short (no unresolved reference detected) | yes |
| CVX | 2024 | FY | 10-K | 0000093410-25-000009 | 1 | 57 | 57 | extracted | yes |
| CVX | 2024 | FY | 10-K | 0000093410-25-000009 | 1A | 25 | 25 | extracted | yes |
| CVX | 2024 | FY | 10-K | 0000093410-25-000009 | 7 | 1 | 78 | resolved | approved repair |
| CVX | 2024 | FY | 10-K | 0000093410-25-000009 | 7A | 1 | 1 | reference covered elsewhere | yes |
| CVX | 2024 | FY | 10-K | 0000093410-25-000009 | 8 | 1 | 219 | resolved | approved repair |
| CVX | 2024 | Q1 | 10-Q | 0000093410-24-000021 | P1-2 | 33 | 33 | extracted | yes |
| CVX | 2024 | Q1 | 10-Q | 0000093410-24-000021 | P2-1A | 3 | 3 | extracted | yes |
| CVX | 2024 | Q2 | 10-Q | 0000093410-24-000040 | P1-2 | 44 | 44 | extracted | yes |
| CVX | 2024 | Q2 | 10-Q | 0000093410-24-000040 | P2-1A | 2 | 2 | extracted; short (no unresolved reference detected) | yes |
| CVX | 2024 | Q3 | 10-Q | 0000093410-24-000059 | P1-2 | 48 | 48 | extracted | yes |
| CVX | 2024 | Q3 | 10-Q | 0000093410-24-000059 | P2-1A | 3 | 3 | extracted | yes |
| CVX | 2025 | FY | 10-K | 0000093410-26-000078 | 1 | 57 | 57 | extracted | yes |
| CVX | 2025 | FY | 10-K | 0000093410-26-000078 | 1A | 24 | 24 | extracted | yes |
| CVX | 2025 | FY | 10-K | 0000093410-26-000078 | 7 | 1 | 78 | resolved | approved repair |
| CVX | 2025 | FY | 10-K | 0000093410-26-000078 | 7A | 1 | 1 | reference covered elsewhere | yes |
| CVX | 2025 | FY | 10-K | 0000093410-26-000078 | 8 | 1 | 224 | resolved | approved repair |
| CVX | 2025 | Q1 | 10-Q | 0000093410-25-000019 | P1-2 | 36 | 36 | extracted | yes |
| CVX | 2025 | Q1 | 10-Q | 0000093410-25-000019 | P2-1A | 3 | 3 | extracted | yes |
| CVX | 2025 | Q2 | 10-Q | 0000093410-25-000062 | P1-2 | 46 | 46 | extracted | yes |
| CVX | 2025 | Q2 | 10-Q | 0000093410-25-000062 | P2-1A | 1 | 1 | extracted; short (no unresolved reference detected) | yes |
| CVX | 2025 | Q3 | 10-Q | 0000093410-25-000108 | P1-2 | 46 | 46 | extracted | yes |
| CVX | 2025 | Q3 | 10-Q | 0000093410-25-000108 | P2-1A | 1 | 1 | extracted; short (no unresolved reference detected) | yes |
| CVX | 2026 | Q1 | 10-Q | 0000093410-26-000113 | P1-2 | 35 | 35 | extracted | yes |
| CVX | 2026 | Q1 | 10-Q | 0000093410-26-000113 | P2-1A | 1 | 1 | extracted; short (no unresolved reference detected) | yes |
| CVX | 2026 | Q2 | 10-Q | 0000093410-26-000167 | P1-2 | 46 | 46 | extracted | yes |
| CVX | 2026 | Q2 | 10-Q | 0000093410-26-000167 | P2-1A | 1 | 1 | extracted; short (no unresolved reference detected) | yes |
| DIS | 2023 | FY | 10-K | 0001744489-23-000216 | 1 | 38 | 38 | extracted | yes |
| DIS | 2023 | FY | 10-K | 0001744489-23-000216 | 1A | 38 | 38 | extracted | yes |
| DIS | 2023 | FY | 10-K | 0001744489-23-000216 | 7 | 94 | 94 | extracted | yes |
| DIS | 2023 | FY | 10-K | 0001744489-23-000216 | 7A | 4 | 4 | extracted | yes |
| DIS | 2023 | FY | 10-K | 0001744489-23-000216 | 8 | 1 | 133 | resolved | approved repair |
| DIS | 2023 | Q1 | 10-Q | 0001744489-23-000049 | P1-2 | 54 | 54 | extracted | yes |
| DIS | 2023 | Q1 | 10-Q | 0001744489-23-000049 | P2-1A | 6 | 6 | extracted | yes |
| DIS | 2023 | Q2 | 10-Q | 0001744489-23-000099 | P1-2 | 82 | 82 | extracted | yes |
| DIS | 2023 | Q2 | 10-Q | 0001744489-23-000099 | P2-1A | 12 | 12 | extracted | yes |
| DIS | 2023 | Q3 | 10-Q | 0001744489-23-000171 | P1-2 | 86 | 86 | extracted | yes |
| DIS | 2023 | Q3 | 10-Q | 0001744489-23-000171 | P2-1A | 12 | 12 | extracted | yes |
| DIS | 2024 | FY | 10-K | 0001744489-24-000276 | 1 | 39 | 39 | extracted | yes |
| DIS | 2024 | FY | 10-K | 0001744489-24-000276 | 1A | 39 | 39 | extracted | yes |
| DIS | 2024 | FY | 10-K | 0001744489-24-000276 | 7 | 62 | 62 | extracted | yes |
| DIS | 2024 | FY | 10-K | 0001744489-24-000276 | 7A | 5 | 5 | extracted | yes |
| DIS | 2024 | FY | 10-K | 0001744489-24-000276 | 8 | 1 | 143 | resolved | approved repair |
| DIS | 2024 | Q1 | 10-Q | 0001744489-24-000081 | P1-2 | 60 | 60 | extracted | yes |
| DIS | 2024 | Q1 | 10-Q | 0001744489-24-000081 | P2-1A | 3 | 3 | extracted | yes |
| DIS | 2024 | Q2 | 10-Q | 0001744489-24-000152 | P1-2 | 89 | 89 | extracted | yes |
| DIS | 2024 | Q2 | 10-Q | 0001744489-24-000152 | P2-1A | 3 | 3 | extracted | yes |
| DIS | 2024 | Q3 | 10-Q | 0001744489-24-000232 | P1-2 | 89 | 89 | extracted | yes |
| DIS | 2024 | Q3 | 10-Q | 0001744489-24-000232 | P2-1A | 2 | 2 | extracted; short (no unresolved reference detected) | yes |
| DIS | 2025 | FY | 10-K | 0001744489-25-000155 | 1 | 37 | 37 | extracted | yes |
| DIS | 2025 | FY | 10-K | 0001744489-25-000155 | 1A | 40 | 40 | extracted | yes |
| DIS | 2025 | FY | 10-K | 0001744489-25-000155 | 7 | 59 | 59 | extracted | yes |
| DIS | 2025 | FY | 10-K | 0001744489-25-000155 | 7A | 4 | 4 | extracted | yes |
| DIS | 2025 | FY | 10-K | 0001744489-25-000155 | 8 | 1 | 138 | resolved | approved repair |
| DIS | 2025 | Q1 | 10-Q | 0001744489-25-000067 | P1-2 | 57 | 57 | extracted | yes |
| DIS | 2025 | Q1 | 10-Q | 0001744489-25-000067 | P2-1A | 1 | 1 | extracted; short (no unresolved reference detected) | yes |
| DIS | 2025 | Q2 | 10-Q | 0001744489-25-000098 | P1-2 | 85 | 85 | extracted | yes |
| DIS | 2025 | Q2 | 10-Q | 0001744489-25-000098 | P2-1A | 11 | 11 | extracted | yes |
| DIS | 2025 | Q3 | 10-Q | 0001744489-25-000136 | P1-2 | 88 | 88 | extracted | yes |
| DIS | 2025 | Q3 | 10-Q | 0001744489-25-000136 | P2-1A | 11 | 11 | extracted | yes |
| DIS | 2026 | Q1 | 10-Q | 0001744489-26-000019 | P1-2 | 31 | 31 | extracted | yes |
| DIS | 2026 | Q1 | 10-Q | 0001744489-26-000019 | P2-1A | 7 | 7 | extracted | yes |
| DIS | 2026 | Q2 | 10-Q | 0001744489-26-000037 | P1-2 | 51 | 51 | extracted | yes |
| DIS | 2026 | Q2 | 10-Q | 0001744489-26-000037 | P2-1A | 11 | 11 | extracted | yes |
| DIS | 2026 | Q3 | 10-Q | 0001744489-26-000057 | P1-2 | 54 | 54 | extracted | yes |
| DIS | 2026 | Q3 | 10-Q | 0001744489-26-000057 | P2-1A | 11 | 11 | extracted | yes |
| GOOGL | 2023 | FY | 10-K | 0001652044-24-000022 | 1 | 19 | 19 | extracted | yes |
| GOOGL | 2023 | FY | 10-K | 0001652044-24-000022 | 1A | 45 | 45 | extracted | yes |
| GOOGL | 2023 | FY | 10-K | 0001652044-24-000022 | 7 | 37 | 37 | extracted | yes |
| GOOGL | 2023 | FY | 10-K | 0001652044-24-000022 | 7A | 7 | 7 | extracted | yes |
| GOOGL | 2023 | FY | 10-K | 0001652044-24-000022 | 8 | 98 | 98 | extracted | yes |
| GOOGL | 2023 | Q1 | 10-Q | 0001652044-23-000045 | P1-2 | 28 | 28 | extracted | yes |
| GOOGL | 2023 | Q1 | 10-Q | 0001652044-23-000045 | P2-1A | 1 | 1 | extracted; short (no unresolved reference detected) | yes |
| GOOGL | 2023 | Q2 | 10-Q | 0001652044-23-000070 | P1-2 | 38 | 38 | extracted | yes |
| GOOGL | 2023 | Q2 | 10-Q | 0001652044-23-000070 | P2-1A | 1 | 1 | extracted; short (no unresolved reference detected) | yes |
| GOOGL | 2023 | Q3 | 10-Q | 0001652044-23-000094 | P1-2 | 39 | 39 | extracted | yes |
| GOOGL | 2023 | Q3 | 10-Q | 0001652044-23-000094 | P2-1A | 1 | 1 | extracted; short (no unresolved reference detected) | yes |
| GOOGL | 2024 | FY | 10-K | 0001652044-25-000014 | 1 | 17 | 17 | extracted | yes |
| GOOGL | 2024 | FY | 10-K | 0001652044-25-000014 | 1A | 53 | 53 | extracted | yes |
| GOOGL | 2024 | FY | 10-K | 0001652044-25-000014 | 7 | 36 | 36 | extracted | yes |
| GOOGL | 2024 | FY | 10-K | 0001652044-25-000014 | 7A | 6 | 6 | extracted | yes |
| GOOGL | 2024 | FY | 10-K | 0001652044-25-000014 | 8 | 101 | 101 | extracted | yes |
| GOOGL | 2024 | Q1 | 10-Q | 0001652044-24-000053 | P1-2 | 29 | 29 | extracted | yes |
| GOOGL | 2024 | Q1 | 10-Q | 0001652044-24-000053 | P2-1A | 3 | 3 | extracted | yes |
| GOOGL | 2024 | Q2 | 10-Q | 0001652044-24-000079 | P1-2 | 37 | 37 | extracted | yes |
| GOOGL | 2024 | Q2 | 10-Q | 0001652044-24-000079 | P2-1A | 2 | 2 | extracted; short (no unresolved reference detected) | yes |
| GOOGL | 2024 | Q3 | 10-Q | 0001652044-24-000118 | P1-2 | 38 | 38 | extracted | yes |
| GOOGL | 2024 | Q3 | 10-Q | 0001652044-24-000118 | P2-1A | 4 | 4 | extracted | yes |
| GOOGL | 2025 | FY | 10-K | 0001652044-26-000018 | 1 | 14 | 14 | extracted | yes |
| GOOGL | 2025 | FY | 10-K | 0001652044-26-000018 | 1A | 51 | 51 | extracted | yes |
| GOOGL | 2025 | FY | 10-K | 0001652044-26-000018 | 7 | 32 | 32 | extracted | yes |
| GOOGL | 2025 | FY | 10-K | 0001652044-26-000018 | 7A | 6 | 6 | extracted | yes |
| GOOGL | 2025 | FY | 10-K | 0001652044-26-000018 | 8 | 106 | 106 | extracted | yes |
| GOOGL | 2025 | Q1 | 10-Q | 0001652044-25-000043 | P1-2 | 29 | 29 | extracted | yes |
| GOOGL | 2025 | Q1 | 10-Q | 0001652044-25-000043 | P2-1A | 1 | 1 | extracted; short (no unresolved reference detected) | yes |
| GOOGL | 2025 | Q2 | 10-Q | 0001652044-25-000062 | P1-2 | 37 | 37 | extracted | yes |
| GOOGL | 2025 | Q2 | 10-Q | 0001652044-25-000062 | P2-1A | 1 | 1 | extracted; short (no unresolved reference detected) | yes |
| GOOGL | 2025 | Q3 | 10-Q | 0001652044-25-000091 | P1-2 | 37 | 37 | extracted | yes |
| GOOGL | 2025 | Q3 | 10-Q | 0001652044-25-000091 | P2-1A | 1 | 1 | extracted; short (no unresolved reference detected) | yes |
| GOOGL | 2026 | Q1 | 10-Q | 0001652044-26-000048 | P1-2 | 29 | 29 | extracted | yes |
| GOOGL | 2026 | Q1 | 10-Q | 0001652044-26-000048 | P2-1A | 4 | 4 | extracted | yes |
| GOOGL | 2026 | Q2 | 10-Q | 0001652044-26-000071 | P1-2 | 35 | 35 | extracted | yes |
| GOOGL | 2026 | Q2 | 10-Q | 0001652044-26-000071 | P2-1A | 11 | 11 | extracted | yes |
| JNJ | 2023 | FY | 10-K | 0000200406-24-000013 | 1 | 23 | 23 | extracted | yes |
| JNJ | 2023 | FY | 10-K | 0000200406-24-000013 | 1A | 25 | 25 | extracted | yes |
| JNJ | 2023 | FY | 10-K | 0000200406-24-000013 | 7 | 47 | 47 | extracted | yes |
| JNJ | 2023 | FY | 10-K | 0000200406-24-000013 | 7A | 1 | 1 | reference covered elsewhere | yes |
| JNJ | 2023 | FY | 10-K | 0000200406-24-000013 | 8 | 182 | 182 | extracted | yes |
| JNJ | 2023 | Q1 | 10-Q | 0000200406-23-000056 | P1-2 | 31 | 31 | extracted | yes |
| JNJ | 2023 | Q1 | 10-Q | 0000200406-23-000056 | P2-1A | 0 | 0 | source absent | yes |
| JNJ | 2023 | Q2 | 10-Q | 0000200406-23-000082 | P1-2 | 46 | 46 | extracted | yes |
| JNJ | 2023 | Q2 | 10-Q | 0000200406-23-000082 | P2-1A | 0 | 0 | source absent | yes |
| JNJ | 2023 | Q3 | 10-Q | 0000200406-23-000102 | P1-2 | 41 | 41 | extracted | yes |
| JNJ | 2023 | Q3 | 10-Q | 0000200406-23-000102 | P2-1A | 0 | 0 | source absent | yes |
| JNJ | 2024 | FY | 10-K | 0000200406-25-000038 | 1 | 22 | 22 | extracted | yes |
| JNJ | 2024 | FY | 10-K | 0000200406-25-000038 | 1A | 25 | 25 | extracted | yes |
| JNJ | 2024 | FY | 10-K | 0000200406-25-000038 | 7 | 50 | 50 | extracted | yes |
| JNJ | 2024 | FY | 10-K | 0000200406-25-000038 | 7A | 1 | 1 | reference covered elsewhere | yes |
| JNJ | 2024 | FY | 10-K | 0000200406-25-000038 | 8 | 181 | 181 | extracted | yes |
| JNJ | 2024 | Q1 | 10-Q | 0000200406-24-000049 | P1-2 | 26 | 26 | extracted | yes |
| JNJ | 2024 | Q1 | 10-Q | 0000200406-24-000049 | P2-1A | 0 | 0 | source absent | yes |
| JNJ | 2024 | Q2 | 10-Q | 0000200406-24-000075 | P1-2 | 39 | 39 | extracted | yes |
| JNJ | 2024 | Q2 | 10-Q | 0000200406-24-000075 | P2-1A | 0 | 0 | source absent | yes |
| JNJ | 2024 | Q3 | 10-Q | 0000200406-24-000096 | P1-2 | 40 | 40 | extracted | yes |
| JNJ | 2024 | Q3 | 10-Q | 0000200406-24-000096 | P2-1A | 0 | 0 | source absent | yes |
| JNJ | 2025 | FY | 10-K | 0000200406-26-000016 | 1 | 24 | 24 | extracted | yes |
| JNJ | 2025 | FY | 10-K | 0000200406-26-000016 | 1A | 27 | 27 | extracted | yes |
| JNJ | 2025 | FY | 10-K | 0000200406-26-000016 | 7 | 50 | 50 | extracted | yes |
| JNJ | 2025 | FY | 10-K | 0000200406-26-000016 | 7A | 1 | 1 | reference covered elsewhere | yes |
| JNJ | 2025 | FY | 10-K | 0000200406-26-000016 | 8 | 179 | 179 | extracted | yes |
| JNJ | 2025 | Q1 | 10-Q | 0000200406-25-000119 | P1-2 | 26 | 26 | extracted | yes |
| JNJ | 2025 | Q1 | 10-Q | 0000200406-25-000119 | P2-1A | 0 | 0 | source absent | yes |
| JNJ | 2025 | Q2 | 10-Q | 0000200406-25-000178 | P1-2 | 39 | 39 | extracted | yes |
| JNJ | 2025 | Q2 | 10-Q | 0000200406-25-000178 | P2-1A | 0 | 0 | source absent | yes |
| JNJ | 2025 | Q3 | 10-Q | 0000200406-25-000209 | P1-2 | 39 | 39 | extracted | yes |
| JNJ | 2025 | Q3 | 10-Q | 0000200406-25-000209 | P2-1A | 0 | 0 | source absent | yes |
| JNJ | 2026 | Q1 | 10-Q | 0000200406-26-000087 | P1-2 | 26 | 26 | extracted | yes |
| JNJ | 2026 | Q1 | 10-Q | 0000200406-26-000087 | P2-1A | 0 | 0 | source absent | yes |
| JNJ | 2026 | Q2 | 10-Q | 0000200406-26-000153 | P1-2 | 37 | 37 | extracted | yes |
| JNJ | 2026 | Q2 | 10-Q | 0000200406-26-000153 | P2-1A | 0 | 0 | source absent | yes |
| JPM | 2023 | FY | 10-K | 0000019617-24-000225 | 1 | 30 | 30 | extracted | yes |
| JPM | 2023 | FY | 10-K | 0000019617-24-000225 | 1A | 75 | 75 | extracted | yes |
| JPM | 2023 | FY | 10-K | 0000019617-24-000225 | 7 | 1 | 317 | resolved | approved repair |
| JPM | 2023 | FY | 10-K | 0000019617-24-000225 | 7A | 1 | 1 | reference covered elsewhere | yes |
| JPM | 2023 | FY | 10-K | 0000019617-24-000225 | 8 | 1 | 509 | resolved | approved repair |
| JPM | 2023 | Q1 | 10-Q | 0000019617-23-000310 | P1-2 | 1 | 207 | resolved | approved repair |
| JPM | 2023 | Q1 | 10-Q | 0000019617-23-000310 | P2-1A | 2 | 2 | extracted; short (no unresolved reference detected) | yes |
| JPM | 2023 | Q2 | 10-Q | 0000019617-23-000432 | P1-2 | 1 | 291 | resolved | approved repair |
| JPM | 2023 | Q2 | 10-Q | 0000019617-23-000432 | P2-1A | 2 | 2 | extracted; short (no unresolved reference detected) | yes |
| JPM | 2023 | Q3 | 10-Q | 0000019617-23-000524 | P1-2 | 1 | 294 | resolved | approved repair |
| JPM | 2023 | Q3 | 10-Q | 0000019617-23-000524 | P2-1A | 2 | 2 | extracted; short (no unresolved reference detected) | yes |
| JPM | 2024 | FY | 10-K | 0000019617-25-000270 | 1 | 27 | 27 | extracted | yes |
| JPM | 2024 | FY | 10-K | 0000019617-25-000270 | 1A | 74 | 74 | extracted | yes |
| JPM | 2024 | FY | 10-K | 0000019617-25-000270 | 7 | 1 | 297 | resolved | approved repair |
| JPM | 2024 | FY | 10-K | 0000019617-25-000270 | 7A | 1 | 1 | reference covered elsewhere | yes |
| JPM | 2024 | FY | 10-K | 0000019617-25-000270 | 8 | 1 | 507 | resolved | approved repair |
| JPM | 2024 | Q1 | 10-Q | 0000019617-24-000326 | P1-2 | 1 | 219 | resolved | approved repair |
| JPM | 2024 | Q1 | 10-Q | 0000019617-24-000326 | P2-1A | 1 | 1 | extracted; short (no unresolved reference detected) | yes |
| JPM | 2024 | Q2 | 10-Q | 0000019617-24-000453 | P1-2 | 1 | 269 | resolved | approved repair |
| JPM | 2024 | Q2 | 10-Q | 0000019617-24-000453 | P2-1A | 1 | 1 | extracted; short (no unresolved reference detected) | yes |
| JPM | 2024 | Q3 | 10-Q | 0000019617-24-000611 | P1-2 | 1 | 269 | resolved | approved repair |
| JPM | 2024 | Q3 | 10-Q | 0000019617-24-000611 | P2-1A | 1 | 1 | extracted; short (no unresolved reference detected) | yes |
| JPM | 2025 | FY | 10-K | 0001628280-26-008131 | 1 | 27 | 27 | extracted | yes |
| JPM | 2025 | FY | 10-K | 0001628280-26-008131 | 1A | 60 | 60 | extracted | yes |
| JPM | 2025 | FY | 10-K | 0001628280-26-008131 | 7 | 1 | 295 | resolved | approved repair |
| JPM | 2025 | FY | 10-K | 0001628280-26-008131 | 7A | 1 | 1 | reference covered elsewhere | yes |
| JPM | 2025 | FY | 10-K | 0001628280-26-008131 | 8 | 1 | 506 | resolved | approved repair |
| JPM | 2025 | Q1 | 10-Q | 0000019617-25-000421 | P1-2 | 1 | 200 | resolved | approved repair |
| JPM | 2025 | Q1 | 10-Q | 0000019617-25-000421 | P2-1A | 1 | 1 | extracted; short (no unresolved reference detected) | yes |
| JPM | 2025 | Q2 | 10-Q | 0000019617-25-000615 | P1-2 | 1 | 253 | resolved | approved repair |
| JPM | 2025 | Q2 | 10-Q | 0000019617-25-000615 | P2-1A | 1 | 1 | extracted; short (no unresolved reference detected) | yes |
| JPM | 2025 | Q3 | 10-Q | 0001628280-25-048859 | P1-2 | 1 | 259 | resolved | approved repair |
| JPM | 2025 | Q3 | 10-Q | 0001628280-25-048859 | P2-1A | 1 | 1 | extracted; short (no unresolved reference detected) | yes |
| JPM | 2026 | Q1 | 10-Q | 0001628280-26-029344 | P1-2 | 1 | 206 | resolved | approved repair |
| JPM | 2026 | Q1 | 10-Q | 0001628280-26-029344 | P2-1A | 1 | 1 | extracted; short (no unresolved reference detected) | yes |
| JPM | 2026 | Q2 | 10-Q | 0001628280-26-054343 | P1-2 | 1 | 261 | resolved | approved repair |
| JPM | 2026 | Q2 | 10-Q | 0001628280-26-054343 | P2-1A | 1 | 1 | extracted; short (no unresolved reference detected) | yes |
| KO | 2023 | FY | 10-K | 0000021344-24-000009 | 1 | 35 | 35 | extracted | yes |
| KO | 2023 | FY | 10-K | 0000021344-24-000009 | 1A | 55 | 55 | extracted | yes |
| KO | 2023 | FY | 10-K | 0000021344-24-000009 | 7 | 74 | 74 | extracted | yes |
| KO | 2023 | FY | 10-K | 0000021344-24-000009 | 7A | 4 | 4 | extracted | yes |
| KO | 2023 | FY | 10-K | 0000021344-24-000009 | 8 | 188 | 188 | extracted | yes |
| KO | 2023 | Q1 | 10-Q | 0000021344-23-000024 | P1-2 | 40 | 40 | extracted | yes |
| KO | 2023 | Q1 | 10-Q | 0000021344-23-000024 | P2-1A | 1 | 1 | extracted; short (no unresolved reference detected) | yes |
| KO | 2023 | Q2 | 10-Q | 0000021344-23-000048 | P1-2 | 51 | 51 | extracted | yes |
| KO | 2023 | Q2 | 10-Q | 0000021344-23-000048 | P2-1A | 1 | 1 | extracted; short (no unresolved reference detected) | yes |
| KO | 2023 | Q3 | 10-Q | 0000021344-23-000060 | P1-2 | 52 | 52 | extracted | yes |
| KO | 2023 | Q3 | 10-Q | 0000021344-23-000060 | P2-1A | 1 | 1 | extracted; short (no unresolved reference detected) | yes |
| KO | 2024 | FY | 10-K | 0000021344-25-000011 | 1 | 35 | 35 | extracted | yes |
| KO | 2024 | FY | 10-K | 0000021344-25-000011 | 1A | 57 | 57 | extracted | yes |
| KO | 2024 | FY | 10-K | 0000021344-25-000011 | 7 | 73 | 73 | extracted | yes |
| KO | 2024 | FY | 10-K | 0000021344-25-000011 | 7A | 4 | 4 | extracted | yes |
| KO | 2024 | FY | 10-K | 0000021344-25-000011 | 8 | 180 | 180 | extracted | yes |
| KO | 2024 | Q1 | 10-Q | 0000021344-24-000017 | P1-2 | 40 | 40 | extracted | yes |
| KO | 2024 | Q1 | 10-Q | 0000021344-24-000017 | P2-1A | 1 | 1 | extracted; short (no unresolved reference detected) | yes |
| KO | 2024 | Q2 | 10-Q | 0000021344-24-000044 | P1-2 | 54 | 54 | extracted | yes |
| KO | 2024 | Q2 | 10-Q | 0000021344-24-000044 | P2-1A | 1 | 1 | extracted; short (no unresolved reference detected) | yes |
| KO | 2024 | Q3 | 10-Q | 0000021344-24-000060 | P1-2 | 54 | 54 | extracted | yes |
| KO | 2024 | Q3 | 10-Q | 0000021344-24-000060 | P2-1A | 1 | 1 | extracted; short (no unresolved reference detected) | yes |
| KO | 2025 | FY | 10-K | 0001628280-26-010047 | 1 | 36 | 36 | extracted | yes |
| KO | 2025 | FY | 10-K | 0001628280-26-010047 | 1A | 57 | 57 | extracted | yes |
| KO | 2025 | FY | 10-K | 0001628280-26-010047 | 7 | 72 | 72 | extracted | yes |
| KO | 2025 | FY | 10-K | 0001628280-26-010047 | 7A | 4 | 4 | extracted | yes |
| KO | 2025 | FY | 10-K | 0001628280-26-010047 | 8 | 176 | 176 | extracted | yes |
| KO | 2025 | Q1 | 10-Q | 0000021344-25-000029 | P1-2 | 38 | 38 | extracted | yes |
| KO | 2025 | Q1 | 10-Q | 0000021344-25-000029 | P2-1A | 1 | 1 | extracted; short (no unresolved reference detected) | yes |
| KO | 2025 | Q2 | 10-Q | 0000021344-25-000061 | P1-2 | 51 | 51 | extracted | yes |
| KO | 2025 | Q2 | 10-Q | 0000021344-25-000061 | P2-1A | 1 | 1 | extracted; short (no unresolved reference detected) | yes |
| KO | 2025 | Q3 | 10-Q | 0001628280-25-046054 | P1-2 | 54 | 54 | extracted | yes |
| KO | 2025 | Q3 | 10-Q | 0001628280-25-046054 | P2-1A | 1 | 1 | extracted; short (no unresolved reference detected) | yes |
| KO | 2026 | Q1 | 10-Q | 0001628280-26-028802 | P1-2 | 36 | 36 | extracted | yes |
| KO | 2026 | Q1 | 10-Q | 0001628280-26-028802 | P2-1A | 1 | 1 | extracted; short (no unresolved reference detected) | yes |
| KO | 2026 | Q2 | 10-Q | 0001628280-26-050503 | P1-2 | 50 | 50 | extracted | yes |
| KO | 2026 | Q2 | 10-Q | 0001628280-26-050503 | P2-1A | 1 | 1 | extracted; short (no unresolved reference detected) | yes |
| META | 2023 | FY | 10-K | 0001326801-24-000012 | 1 | 23 | 23 | extracted | yes |
| META | 2023 | FY | 10-K | 0001326801-24-000012 | 1A | 112 | 112 | extracted | yes |
| META | 2023 | FY | 10-K | 0001326801-24-000012 | 7 | 49 | 49 | extracted | yes |
| META | 2023 | FY | 10-K | 0001326801-24-000012 | 7A | 3 | 3 | extracted | yes |
| META | 2023 | FY | 10-K | 0001326801-24-000012 | 8 | 93 | 93 | extracted | yes |
| META | 2023 | Q1 | 10-Q | 0001326801-23-000067 | P1-2 | 39 | 39 | extracted | yes |
| META | 2023 | Q1 | 10-Q | 0001326801-23-000067 | P2-1A | 106 | 106 | extracted | yes |
| META | 2023 | Q2 | 10-Q | 0001326801-23-000093 | P1-2 | 43 | 43 | extracted | yes |
| META | 2023 | Q2 | 10-Q | 0001326801-23-000093 | P2-1A | 106 | 106 | extracted | yes |
| META | 2023 | Q3 | 10-Q | 0001326801-23-000103 | P1-2 | 44 | 44 | extracted | yes |
| META | 2023 | Q3 | 10-Q | 0001326801-23-000103 | P2-1A | 109 | 109 | extracted | yes |
| META | 2024 | FY | 10-K | 0001326801-25-000017 | 1 | 26 | 26 | extracted | yes |
| META | 2024 | FY | 10-K | 0001326801-25-000017 | 1A | 118 | 118 | extracted | yes |
| META | 2024 | FY | 10-K | 0001326801-25-000017 | 7 | 42 | 42 | extracted | yes |
| META | 2024 | FY | 10-K | 0001326801-25-000017 | 7A | 4 | 4 | extracted | yes |
| META | 2024 | FY | 10-K | 0001326801-25-000017 | 8 | 95 | 95 | extracted | yes |
| META | 2024 | Q1 | 10-Q | 0001326801-24-000049 | P1-2 | 30 | 30 | extracted | yes |
| META | 2024 | Q1 | 10-Q | 0001326801-24-000049 | P2-1A | 112 | 112 | extracted | yes |
| META | 2024 | Q2 | 10-Q | 0001326801-24-000069 | P1-2 | 35 | 35 | extracted | yes |
| META | 2024 | Q2 | 10-Q | 0001326801-24-000069 | P2-1A | 116 | 116 | extracted | yes |
| META | 2024 | Q3 | 10-Q | 0001326801-24-000081 | P1-2 | 36 | 36 | extracted | yes |
| META | 2024 | Q3 | 10-Q | 0001326801-24-000081 | P2-1A | 120 | 120 | extracted | yes |
| META | 2025 | FY | 10-K | 0001628280-26-003942 | 1 | 15 | 15 | extracted | yes |
| META | 2025 | FY | 10-K | 0001628280-26-003942 | 1A | 123 | 123 | extracted | yes |
| META | 2025 | FY | 10-K | 0001628280-26-003942 | 7 | 43 | 43 | extracted | yes |
| META | 2025 | FY | 10-K | 0001628280-26-003942 | 7A | 4 | 4 | extracted | yes |
| META | 2025 | FY | 10-K | 0001628280-26-003942 | 8 | 110 | 110 | extracted | yes |
| META | 2025 | Q1 | 10-Q | 0001326801-25-000054 | P1-2 | 32 | 32 | extracted | yes |
| META | 2025 | Q1 | 10-Q | 0001326801-25-000054 | P2-1A | 120 | 120 | extracted | yes |
| META | 2025 | Q2 | 10-Q | 0001628280-25-036791 | P1-2 | 36 | 36 | extracted | yes |
| META | 2025 | Q2 | 10-Q | 0001628280-25-036791 | P2-1A | 123 | 123 | extracted | yes |
| META | 2025 | Q3 | 10-Q | 0001628280-25-047240 | P1-2 | 38 | 38 | extracted | yes |
| META | 2025 | Q3 | 10-Q | 0001628280-25-047240 | P2-1A | 122 | 122 | extracted | yes |
| META | 2026 | Q1 | 10-Q | 0001628280-26-028526 | P1-2 | 32 | 32 | extracted | yes |
| META | 2026 | Q1 | 10-Q | 0001628280-26-028526 | P2-1A | 125 | 125 | extracted | yes |
| META | 2026 | Q2 | 10-Q | 0001628280-26-050705 | P1-2 | 38 | 38 | extracted | yes |
| META | 2026 | Q2 | 10-Q | 0001628280-26-050705 | P2-1A | 126 | 126 | extracted | yes |
| MSFT | 2024 | FY | 10-K | 0000950170-24-087843 | 1 | 39 | 39 | extracted | yes |
| MSFT | 2024 | FY | 10-K | 0000950170-24-087843 | 1A | 45 | 45 | extracted | yes |
| MSFT | 2024 | FY | 10-K | 0000950170-24-087843 | 7 | 34 | 34 | extracted | yes |
| MSFT | 2024 | FY | 10-K | 0000950170-24-087843 | 7A | 2 | 2 | extracted; short (no unresolved reference detected) | yes |
| MSFT | 2024 | FY | 10-K | 0000950170-24-087843 | 8 | 107 | 107 | extracted | yes |
| MSFT | 2024 | Q1 | 10-Q | 0000950170-23-054855 | P1-2 | 29 | 29 | extracted | yes |
| MSFT | 2024 | Q1 | 10-Q | 0000950170-23-054855 | P2-1A | 41 | 41 | extracted | yes |
| MSFT | 2024 | Q2 | 10-Q | 0000950170-24-008814 | P1-2 | 41 | 41 | extracted | yes |
| MSFT | 2024 | Q2 | 10-Q | 0000950170-24-008814 | P2-1A | 43 | 43 | extracted | yes |
| MSFT | 2024 | Q3 | 10-Q | 0000950170-24-048288 | P1-2 | 41 | 41 | extracted | yes |
| MSFT | 2024 | Q3 | 10-Q | 0000950170-24-048288 | P2-1A | 45 | 45 | extracted | yes |
| MSFT | 2025 | FY | 10-K | 0000950170-25-100235 | 1 | 27 | 27 | extracted | yes |
| MSFT | 2025 | FY | 10-K | 0000950170-25-100235 | 1A | 41 | 41 | extracted | yes |
| MSFT | 2025 | FY | 10-K | 0000950170-25-100235 | 7 | 31 | 31 | extracted | yes |
| MSFT | 2025 | FY | 10-K | 0000950170-25-100235 | 7A | 2 | 2 | extracted; short (no unresolved reference detected) | yes |
| MSFT | 2025 | FY | 10-K | 0000950170-25-100235 | 8 | 101 | 101 | extracted | yes |
| MSFT | 2025 | Q1 | 10-Q | 0000950170-24-118967 | P1-2 | 30 | 30 | extracted | yes |
| MSFT | 2025 | Q1 | 10-Q | 0000950170-24-118967 | P2-1A | 45 | 45 | extracted | yes |
| MSFT | 2025 | Q2 | 10-Q | 0000950170-25-010491 | P1-2 | 35 | 35 | extracted | yes |
| MSFT | 2025 | Q2 | 10-Q | 0000950170-25-010491 | P2-1A | 45 | 45 | extracted | yes |
| MSFT | 2025 | Q3 | 10-Q | 0000950170-25-061046 | P1-2 | 36 | 36 | extracted | yes |
| MSFT | 2025 | Q3 | 10-Q | 0000950170-25-061046 | P2-1A | 44 | 44 | extracted | yes |
| MSFT | 2026 | FY | 10-K | 0001193125-26-323660 | 1 | 23 | 23 | extracted | yes |
| MSFT | 2026 | FY | 10-K | 0001193125-26-323660 | 1A | 52 | 52 | extracted | yes |
| MSFT | 2026 | FY | 10-K | 0001193125-26-323660 | 7 | 34 | 34 | extracted | yes |
| MSFT | 2026 | FY | 10-K | 0001193125-26-323660 | 7A | 2 | 2 | extracted; short (no unresolved reference detected) | yes |
| MSFT | 2026 | FY | 10-K | 0001193125-26-323660 | 8 | 106 | 106 | extracted | yes |
| MSFT | 2026 | Q1 | 10-Q | 0001193125-25-256321 | P1-2 | 31 | 31 | extracted | yes |
| MSFT | 2026 | Q1 | 10-Q | 0001193125-25-256321 | P2-1A | 41 | 41 | extracted | yes |
| MSFT | 2026 | Q2 | 10-Q | 0001193125-26-027207 | P1-2 | 41 | 41 | extracted | yes |
| MSFT | 2026 | Q2 | 10-Q | 0001193125-26-027207 | P2-1A | 42 | 42 | extracted | yes |
| MSFT | 2026 | Q3 | 10-Q | 0001193125-26-191507 | P1-2 | 40 | 40 | extracted | yes |
| MSFT | 2026 | Q3 | 10-Q | 0001193125-26-191507 | P2-1A | 42 | 42 | extracted | yes |
| NKE | 2024 | FY | 10-K | 0000320187-24-000044 | 1 | 23 | 23 | extracted | yes |
| NKE | 2024 | FY | 10-K | 0000320187-24-000044 | 1A | 59 | 59 | extracted | yes |
| NKE | 2024 | FY | 10-K | 0000320187-24-000044 | 7 | 56 | 56 | extracted | yes |
| NKE | 2024 | FY | 10-K | 0000320187-24-000044 | 7A | 5 | 5 | extracted | yes |
| NKE | 2024 | FY | 10-K | 0000320187-24-000044 | 8 | 93 | 93 | extracted | yes |
| NKE | 2024 | Q1 | 10-Q | 0000320187-23-000052 | P1-2 | 35 | 35 | extracted | yes |
| NKE | 2024 | Q1 | 10-Q | 0000320187-23-000052 | P2-1A | 1 | 1 | extracted; short (no unresolved reference detected) | yes |
| NKE | 2024 | Q2 | 10-Q | 0000320187-24-000004 | P1-2 | 55 | 55 | extracted | yes |
| NKE | 2024 | Q2 | 10-Q | 0000320187-24-000004 | P2-1A | 1 | 1 | extracted; short (no unresolved reference detected) | yes |
| NKE | 2024 | Q3 | 10-Q | 0000320187-24-000019 | P1-2 | 58 | 58 | extracted | yes |
| NKE | 2024 | Q3 | 10-Q | 0000320187-24-000019 | P2-1A | 1 | 1 | extracted; short (no unresolved reference detected) | yes |
| NKE | 2025 | FY | 10-K | 0000320187-25-000047 | 1 | 23 | 23 | extracted | yes |
| NKE | 2025 | FY | 10-K | 0000320187-25-000047 | 1A | 59 | 59 | extracted | yes |
| NKE | 2025 | FY | 10-K | 0000320187-25-000047 | 7 | 57 | 57 | extracted | yes |
| NKE | 2025 | FY | 10-K | 0000320187-25-000047 | 7A | 5 | 5 | extracted | yes |
| NKE | 2025 | FY | 10-K | 0000320187-25-000047 | 8 | 97 | 97 | extracted | yes |
| NKE | 2025 | Q1 | 10-Q | 0000320187-24-000065 | P1-2 | 33 | 33 | extracted | yes |
| NKE | 2025 | Q1 | 10-Q | 0000320187-24-000065 | P2-1A | 1 | 1 | extracted; short (no unresolved reference detected) | yes |
| NKE | 2025 | Q2 | 10-Q | 0000320187-25-000004 | P1-2 | 52 | 52 | extracted | yes |
| NKE | 2025 | Q2 | 10-Q | 0000320187-25-000004 | P2-1A | 1 | 1 | extracted; short (no unresolved reference detected) | yes |
| NKE | 2025 | Q3 | 10-Q | 0000320187-25-000016 | P1-2 | 53 | 53 | extracted | yes |
| NKE | 2025 | Q3 | 10-Q | 0000320187-25-000016 | P2-1A | 1 | 1 | extracted; short (no unresolved reference detected) | yes |
| NKE | 2026 | FY | 10-K | 0000320187-26-000088 | 1 | 22 | 22 | extracted | yes |
| NKE | 2026 | FY | 10-K | 0000320187-26-000088 | 1A | 62 | 62 | extracted | yes |
| NKE | 2026 | FY | 10-K | 0000320187-26-000088 | 7 | 55 | 55 | extracted | yes |
| NKE | 2026 | FY | 10-K | 0000320187-26-000088 | 7A | 5 | 5 | extracted | yes |
| NKE | 2026 | FY | 10-K | 0000320187-26-000088 | 8 | 97 | 97 | extracted | yes |
| NKE | 2026 | Q1 | 10-Q | 0000320187-25-000097 | P1-2 | 35 | 35 | extracted | yes |
| NKE | 2026 | Q1 | 10-Q | 0000320187-25-000097 | P2-1A | 1 | 1 | extracted; short (no unresolved reference detected) | yes |
| NKE | 2026 | Q2 | 10-Q | 0000320187-25-000151 | P1-2 | 55 | 55 | extracted | yes |
| NKE | 2026 | Q2 | 10-Q | 0000320187-25-000151 | P2-1A | 1 | 1 | extracted; short (no unresolved reference detected) | yes |
| NKE | 2026 | Q3 | 10-Q | 0000320187-26-000037 | P1-2 | 57 | 57 | extracted | yes |
| NKE | 2026 | Q3 | 10-Q | 0000320187-26-000037 | P2-1A | 1 | 1 | extracted; short (no unresolved reference detected) | yes |
| NKE | 2027 | Q1 | 10-Q | 0000320187-26-000193 | P1-2 | 31 | 31 | extracted | yes |
| NKE | 2027 | Q1 | 10-Q | 0000320187-26-000193 | P2-1A | 1 | 1 | extracted; short (no unresolved reference detected) | yes |
| NVDA | 2024 | FY | 10-K | 0001045810-24-000029 | 1 | 32 | 32 | extracted | yes |
| NVDA | 2024 | FY | 10-K | 0001045810-24-000029 | 1A | 68 | 68 | extracted | yes |
| NVDA | 2024 | FY | 10-K | 0001045810-24-000029 | 7 | 26 | 26 | extracted | yes |
| NVDA | 2024 | FY | 10-K | 0001045810-24-000029 | 7A | 2 | 2 | extracted; short (no unresolved reference detected) | yes |
| NVDA | 2024 | FY | 10-K | 0001045810-24-000029 | 8 | 1 | 81 | resolved | approved repair |
| NVDA | 2024 | Q1 | 10-Q | 0001045810-23-000093 | P1-2 | 19 | 19 | extracted | yes |
| NVDA | 2024 | Q1 | 10-Q | 0001045810-23-000093 | P2-1A | 33 | 33 | extracted | yes |
| NVDA | 2024 | Q2 | 10-Q | 0001045810-23-000175 | P1-2 | 25 | 25 | extracted | yes |
| NVDA | 2024 | Q2 | 10-Q | 0001045810-23-000175 | P2-1A | 31 | 31 | extracted | yes |
| NVDA | 2024 | Q3 | 10-Q | 0001045810-23-000227 | P1-2 | 28 | 28 | extracted | yes |
| NVDA | 2024 | Q3 | 10-Q | 0001045810-23-000227 | P2-1A | 31 | 31 | extracted | yes |
| NVDA | 2025 | FY | 10-K | 0001045810-25-000023 | 1 | 34 | 34 | extracted | yes |
| NVDA | 2025 | FY | 10-K | 0001045810-25-000023 | 1A | 70 | 70 | extracted | yes |
| NVDA | 2025 | FY | 10-K | 0001045810-25-000023 | 7 | 25 | 25 | extracted | yes |
| NVDA | 2025 | FY | 10-K | 0001045810-25-000023 | 7A | 2 | 2 | extracted; short (no unresolved reference detected) | yes |
| NVDA | 2025 | FY | 10-K | 0001045810-25-000023 | 8 | 1 | 80 | resolved | approved repair |
| NVDA | 2025 | Q1 | 10-Q | 0001045810-24-000124 | P1-2 | 22 | 22 | extracted | yes |
| NVDA | 2025 | Q1 | 10-Q | 0001045810-24-000124 | P2-1A | 25 | 25 | extracted | yes |
| NVDA | 2025 | Q2 | 10-Q | 0001045810-24-000264 | P1-2 | 27 | 27 | extracted | yes |
| NVDA | 2025 | Q2 | 10-Q | 0001045810-24-000264 | P2-1A | 25 | 25 | extracted | yes |
| NVDA | 2025 | Q3 | 10-Q | 0001045810-24-000316 | P1-2 | 26 | 26 | extracted | yes |
| NVDA | 2025 | Q3 | 10-Q | 0001045810-24-000316 | P2-1A | 24 | 24 | extracted | yes |
| NVDA | 2026 | FY | 10-K | 0001045810-26-000021 | 1 | 30 | 30 | extracted | yes |
| NVDA | 2026 | FY | 10-K | 0001045810-26-000021 | 1A | 72 | 72 | extracted | yes |
| NVDA | 2026 | FY | 10-K | 0001045810-26-000021 | 7 | 22 | 22 | extracted | yes |
| NVDA | 2026 | FY | 10-K | 0001045810-26-000021 | 7A | 3 | 3 | extracted | yes |
| NVDA | 2026 | FY | 10-K | 0001045810-26-000021 | 8 | 1 | 76 | resolved | approved repair |
| NVDA | 2026 | Q1 | 10-Q | 0001045810-25-000116 | P1-2 | 21 | 21 | extracted | yes |
| NVDA | 2026 | Q1 | 10-Q | 0001045810-25-000116 | P2-1A | 24 | 24 | extracted | yes |
| NVDA | 2026 | Q2 | 10-Q | 0001045810-25-000209 | P1-2 | 24 | 24 | extracted | yes |
| NVDA | 2026 | Q2 | 10-Q | 0001045810-25-000209 | P2-1A | 21 | 21 | extracted | yes |
| NVDA | 2026 | Q3 | 10-Q | 0001045810-25-000230 | P1-2 | 24 | 24 | extracted | yes |
| NVDA | 2026 | Q3 | 10-Q | 0001045810-25-000230 | P2-1A | 30 | 30 | extracted | yes |
| NVDA | 2027 | Q1 | 10-Q | 0001045810-26-000052 | P1-2 | 20 | 20 | extracted | yes |
| NVDA | 2027 | Q1 | 10-Q | 0001045810-26-000052 | P2-1A | 29 | 29 | extracted | yes |
| NVDA | 2027 | Q2 | 10-Q | 0001045810-26-000075 | P1-2 | 27 | 27 | extracted | yes |
| NVDA | 2027 | Q2 | 10-Q | 0001045810-26-000075 | P2-1A | 23 | 23 | extracted | yes |
| PFE | 2023 | FY | 10-K | 0000078003-24-000039 | 1 | 61 | 61 | extracted | yes |
| PFE | 2023 | FY | 10-K | 0000078003-24-000039 | 1A | 54 | 54 | extracted | yes |
| PFE | 2023 | FY | 10-K | 0000078003-24-000039 | 7 | 76 | 76 | extracted | yes |
| PFE | 2023 | FY | 10-K | 0000078003-24-000039 | 7A | 1 | 1 | reference covered elsewhere | yes |
| PFE | 2023 | FY | 10-K | 0000078003-24-000039 | 8 | 249 | 249 | extracted | yes |
| PFE | 2023 | Q1 | 10-Q | 0001628280-23-017196 | P1-2 | 66 | 66 | extracted | yes |
| PFE | 2023 | Q1 | 10-Q | 0001628280-23-017196 | P2-1A | 3 | 3 | extracted | yes |
| PFE | 2023 | Q2 | 10-Q | 0000078003-23-000088 | P1-2 | 81 | 81 | extracted | yes |
| PFE | 2023 | Q2 | 10-Q | 0000078003-23-000088 | P2-1A | 4 | 4 | extracted | yes |
| PFE | 2023 | Q3 | 10-Q | 0000078003-23-000115 | P1-2 | 83 | 83 | extracted | yes |
| PFE | 2023 | Q3 | 10-Q | 0000078003-23-000115 | P2-1A | 4 | 4 | extracted | yes |
| PFE | 2024 | FY | 10-K | 0000078003-25-000054 | 1 | 56 | 56 | extracted | yes |
| PFE | 2024 | FY | 10-K | 0000078003-25-000054 | 1A | 53 | 53 | extracted | yes |
| PFE | 2024 | FY | 10-K | 0000078003-25-000054 | 7 | 82 | 82 | extracted | yes |
| PFE | 2024 | FY | 10-K | 0000078003-25-000054 | 7A | 1 | 1 | reference covered elsewhere | yes |
| PFE | 2024 | FY | 10-K | 0000078003-25-000054 | 8 | 245 | 245 | extracted | yes |
| PFE | 2024 | Q1 | 10-Q | 0000078003-24-000107 | P1-2 | 59 | 59 | extracted | yes |
| PFE | 2024 | Q1 | 10-Q | 0000078003-24-000107 | P2-1A | 1 | 1 | extracted; short (no unresolved reference detected) | yes |
| PFE | 2024 | Q2 | 10-Q | 0000078003-24-000166 | P1-2 | 79 | 79 | extracted | yes |
| PFE | 2024 | Q2 | 10-Q | 0000078003-24-000166 | P2-1A | 1 | 1 | extracted; short (no unresolved reference detected) | yes |
| PFE | 2024 | Q3 | 10-Q | 0000078003-24-000191 | P1-2 | 80 | 80 | extracted | yes |
| PFE | 2024 | Q3 | 10-Q | 0000078003-24-000191 | P2-1A | 1 | 1 | extracted; short (no unresolved reference detected) | yes |
| PFE | 2025 | FY | 10-K | 0000078003-26-000026 | 1 | 60 | 60 | extracted | yes |
| PFE | 2025 | FY | 10-K | 0000078003-26-000026 | 1A | 58 | 58 | extracted | yes |
| PFE | 2025 | FY | 10-K | 0000078003-26-000026 | 7 | 80 | 80 | extracted | yes |
| PFE | 2025 | FY | 10-K | 0000078003-26-000026 | 7A | 1 | 1 | reference covered elsewhere | yes |
| PFE | 2025 | FY | 10-K | 0000078003-26-000026 | 8 | 232 | 232 | extracted | yes |
| PFE | 2025 | Q1 | 10-Q | 0000078003-25-000114 | P1-2 | 62 | 62 | extracted | yes |
| PFE | 2025 | Q1 | 10-Q | 0000078003-25-000114 | P2-1A | 1 | 1 | extracted; short (no unresolved reference detected) | yes |
| PFE | 2025 | Q2 | 10-Q | 0000078003-25-000138 | P1-2 | 78 | 78 | extracted | yes |
| PFE | 2025 | Q2 | 10-Q | 0000078003-25-000138 | P2-1A | 1 | 1 | extracted; short (no unresolved reference detected) | yes |
| PFE | 2025 | Q3 | 10-Q | 0000078003-25-000150 | P1-2 | 84 | 84 | extracted | yes |
| PFE | 2025 | Q3 | 10-Q | 0000078003-25-000150 | P2-1A | 1 | 1 | extracted; short (no unresolved reference detected) | yes |
| PFE | 2026 | Q1 | 10-Q | 0000078003-26-000054 | P1-2 | 51 | 51 | extracted | yes |
| PFE | 2026 | Q1 | 10-Q | 0000078003-26-000054 | P2-1A | 1 | 1 | extracted; short (no unresolved reference detected) | yes |
| PFE | 2026 | Q2 | 10-Q | 0000078003-26-000095 | P1-2 | 71 | 71 | extracted | yes |
| PFE | 2026 | Q2 | 10-Q | 0000078003-26-000095 | P2-1A | 1 | 1 | extracted; short (no unresolved reference detected) | yes |
| PG | 2024 | FY | 10-K | 0000080424-24-000083 | 1 | 8 | 8 | extracted | yes |
| PG | 2024 | FY | 10-K | 0000080424-24-000083 | 1A | 24 | 24 | extracted | yes |
| PG | 2024 | FY | 10-K | 0000080424-24-000083 | 7 | 61 | 61 | extracted | yes |
| PG | 2024 | FY | 10-K | 0000080424-24-000083 | 7A | 1 | 1 | reference covered elsewhere | yes |
| PG | 2024 | FY | 10-K | 0000080424-24-000083 | 8 | 93 | 93 | extracted | yes |
| PG | 2024 | Q1 | 10-Q | 0000080424-23-000103 | P1-2 | 33 | 33 | extracted | yes |
| PG | 2024 | Q1 | 10-Q | 0000080424-23-000103 | P2-1A | 1 | 1 | extracted; short (no unresolved reference detected) | yes |
| PG | 2024 | Q2 | 10-Q | 0000080424-24-000018 | P1-2 | 53 | 53 | extracted | yes |
| PG | 2024 | Q2 | 10-Q | 0000080424-24-000018 | P2-1A | 1 | 1 | extracted; short (no unresolved reference detected) | yes |
| PG | 2024 | Q3 | 10-Q | 0000080424-24-000051 | P1-2 | 53 | 53 | extracted | yes |
| PG | 2024 | Q3 | 10-Q | 0000080424-24-000051 | P2-1A | 1 | 1 | extracted; short (no unresolved reference detected) | yes |
| PG | 2025 | FY | 10-K | 0000080424-25-000076 | 1 | 8 | 8 | extracted | yes |
| PG | 2025 | FY | 10-K | 0000080424-25-000076 | 1A | 23 | 23 | extracted | yes |
| PG | 2025 | FY | 10-K | 0000080424-25-000076 | 7 | 61 | 61 | extracted | yes |
| PG | 2025 | FY | 10-K | 0000080424-25-000076 | 7A | 1 | 1 | reference covered elsewhere | yes |
| PG | 2025 | FY | 10-K | 0000080424-25-000076 | 8 | 95 | 95 | extracted | yes |
| PG | 2025 | Q1 | 10-Q | 0000080424-24-000113 | P1-2 | 34 | 34 | extracted | yes |
| PG | 2025 | Q1 | 10-Q | 0000080424-24-000113 | P2-1A | 1 | 1 | extracted; short (no unresolved reference detected) | yes |
| PG | 2025 | Q2 | 10-Q | 0000080424-25-000013 | P1-2 | 51 | 51 | extracted | yes |
| PG | 2025 | Q2 | 10-Q | 0000080424-25-000013 | P2-1A | 1 | 1 | extracted; short (no unresolved reference detected) | yes |
| PG | 2025 | Q3 | 10-Q | 0000080424-25-000037 | P1-2 | 51 | 51 | extracted | yes |
| PG | 2025 | Q3 | 10-Q | 0000080424-25-000037 | P2-1A | 1 | 1 | extracted; short (no unresolved reference detected) | yes |
| PG | 2026 | FY | 10-K | 0000080424-26-000103 | 1 | 8 | 8 | extracted | yes |
| PG | 2026 | FY | 10-K | 0000080424-26-000103 | 1A | 25 | 25 | extracted | yes |
| PG | 2026 | FY | 10-K | 0000080424-26-000103 | 7 | 59 | 59 | extracted | yes |
| PG | 2026 | FY | 10-K | 0000080424-26-000103 | 7A | 1 | 1 | reference covered elsewhere | yes |
| PG | 2026 | FY | 10-K | 0000080424-26-000103 | 8 | 98 | 98 | extracted | yes |
| PG | 2026 | Q1 | 10-Q | 0000080424-25-000245 | P1-2 | 34 | 34 | extracted | yes |
| PG | 2026 | Q1 | 10-Q | 0000080424-25-000245 | P2-1A | 1 | 1 | extracted; short (no unresolved reference detected) | yes |
| PG | 2026 | Q2 | 10-Q | 0000080424-26-000011 | P1-2 | 52 | 52 | extracted | yes |
| PG | 2026 | Q2 | 10-Q | 0000080424-26-000011 | P2-1A | 1 | 1 | extracted; short (no unresolved reference detected) | yes |
| PG | 2026 | Q3 | 10-Q | 0000080424-26-000060 | P1-2 | 53 | 53 | extracted | yes |
| PG | 2026 | Q3 | 10-Q | 0000080424-26-000060 | P2-1A | 1 | 1 | extracted; short (no unresolved reference detected) | yes |
| TSLA | 2023 | FY | 10-K | 0001628280-24-002390 | 1 | 26 | 26 | extracted | yes |
| TSLA | 2023 | FY | 10-K | 0001628280-24-002390 | 1A | 47 | 47 | extracted | yes |
| TSLA | 2023 | FY | 10-K | 0001628280-24-002390 | 7 | 34 | 34 | extracted | yes |
| TSLA | 2023 | FY | 10-K | 0001628280-24-002390 | 7A | 1 | 1 | extracted; short (no unresolved reference detected) | yes |
| TSLA | 2023 | FY | 10-K | 0001628280-24-002390 | 8 | 128 | 128 | extracted | yes |
| TSLA | 2023 | Q1 | 10-Q | 0000950170-23-013890 | P1-2 | 21 | 21 | extracted | yes |
| TSLA | 2023 | Q1 | 10-Q | 0000950170-23-013890 | P2-1A | 1 | 1 | extracted; short (no unresolved reference detected) | yes |
| TSLA | 2023 | Q2 | 10-Q | 0000950170-23-033872 | P1-2 | 28 | 28 | extracted | yes |
| TSLA | 2023 | Q2 | 10-Q | 0000950170-23-033872 | P2-1A | 1 | 1 | extracted; short (no unresolved reference detected) | yes |
| TSLA | 2023 | Q3 | 10-Q | 0001628280-23-034847 | P1-2 | 27 | 27 | extracted | yes |
| TSLA | 2023 | Q3 | 10-Q | 0001628280-23-034847 | P2-1A | 1 | 1 | extracted; short (no unresolved reference detected) | yes |
| TSLA | 2024 | FY | 10-K | 0001628280-25-003063 | 1 | 28 | 28 | extracted | yes |
| TSLA | 2024 | FY | 10-K | 0001628280-25-003063 | 1A | 49 | 49 | extracted | yes |
| TSLA | 2024 | FY | 10-K | 0001628280-25-003063 | 7 | 34 | 34 | extracted | yes |
| TSLA | 2024 | FY | 10-K | 0001628280-25-003063 | 7A | 1 | 1 | extracted; short (no unresolved reference detected) | yes |
| TSLA | 2024 | FY | 10-K | 0001628280-25-003063 | 8 | 117 | 117 | extracted | yes |
| TSLA | 2024 | Q1 | 10-Q | 0001628280-24-017503 | P1-2 | 19 | 19 | extracted | yes |
| TSLA | 2024 | Q1 | 10-Q | 0001628280-24-017503 | P2-1A | 1 | 1 | extracted; short (no unresolved reference detected) | yes |
| TSLA | 2024 | Q2 | 10-Q | 0001628280-24-032662 | P1-2 | 27 | 27 | extracted | yes |
| TSLA | 2024 | Q2 | 10-Q | 0001628280-24-032662 | P2-1A | 1 | 1 | extracted; short (no unresolved reference detected) | yes |
| TSLA | 2024 | Q3 | 10-Q | 0001628280-24-043486 | P1-2 | 28 | 28 | extracted | yes |
| TSLA | 2024 | Q3 | 10-Q | 0001628280-24-043486 | P2-1A | 1 | 1 | extracted; short (no unresolved reference detected) | yes |
| TSLA | 2025 | FY | 10-K | 0001628280-26-003952 | 1 | 27 | 27 | extracted | yes |
| TSLA | 2025 | FY | 10-K | 0001628280-26-003952 | 1A | 52 | 52 | extracted | yes |
| TSLA | 2025 | FY | 10-K | 0001628280-26-003952 | 7 | 40 | 40 | extracted | yes |
| TSLA | 2025 | FY | 10-K | 0001628280-26-003952 | 7A | 1 | 1 | extracted; short (no unresolved reference detected) | yes |
| TSLA | 2025 | FY | 10-K | 0001628280-26-003952 | 8 | 134 | 134 | extracted | yes |
| TSLA | 2025 | Q1 | 10-Q | 0001628280-25-018911 | P1-2 | 20 | 20 | extracted | yes |
| TSLA | 2025 | Q1 | 10-Q | 0001628280-25-018911 | P2-1A | 4 | 4 | extracted | yes |
| TSLA | 2025 | Q2 | 10-Q | 0001628280-25-035806 | P1-2 | 28 | 28 | extracted | yes |
| TSLA | 2025 | Q2 | 10-Q | 0001628280-25-035806 | P2-1A | 2 | 2 | extracted; short (no unresolved reference detected) | yes |
| TSLA | 2025 | Q3 | 10-Q | 0001628280-25-045968 | P1-2 | 30 | 30 | extracted | yes |
| TSLA | 2025 | Q3 | 10-Q | 0001628280-25-045968 | P2-1A | 1 | 1 | extracted; short (no unresolved reference detected) | yes |
| TSLA | 2026 | Q1 | 10-Q | 0001628280-26-026673 | P1-2 | 23 | 23 | extracted | yes |
| TSLA | 2026 | Q1 | 10-Q | 0001628280-26-026673 | P2-1A | 1 | 1 | extracted; short (no unresolved reference detected) | yes |
| TSLA | 2026 | Q2 | 10-Q | 0001628280-26-049270 | P1-2 | 30 | 30 | extracted | yes |
| TSLA | 2026 | Q2 | 10-Q | 0001628280-26-049270 | P2-1A | 1 | 1 | extracted; short (no unresolved reference detected) | yes |
| UNH | 2023 | FY | 10-K | 0000731766-24-000081 | 1 | 28 | 28 | extracted | yes |
| UNH | 2023 | FY | 10-K | 0000731766-24-000081 | 1A | 42 | 42 | extracted | yes |
| UNH | 2023 | FY | 10-K | 0000731766-24-000081 | 7 | 31 | 31 | extracted | yes |
| UNH | 2023 | FY | 10-K | 0000731766-24-000081 | 7A | 3 | 3 | extracted | yes |
| UNH | 2023 | FY | 10-K | 0000731766-24-000081 | 8 | 90 | 90 | extracted | yes |
| UNH | 2023 | Q1 | 10-Q | 0000731766-23-000029 | P1-2 | 21 | 21 | extracted | yes |
| UNH | 2023 | Q1 | 10-Q | 0000731766-23-000029 | P2-1A | 1 | 1 | extracted; short (no unresolved reference detected) | yes |
| UNH | 2023 | Q2 | 10-Q | 0000731766-23-000053 | P1-2 | 27 | 27 | extracted | yes |
| UNH | 2023 | Q2 | 10-Q | 0000731766-23-000053 | P2-1A | 1 | 1 | extracted; short (no unresolved reference detected) | yes |
| UNH | 2023 | Q3 | 10-Q | 0000731766-23-000064 | P1-2 | 28 | 28 | extracted | yes |
| UNH | 2023 | Q3 | 10-Q | 0000731766-23-000064 | P2-1A | 1 | 1 | extracted; short (no unresolved reference detected) | yes |
| UNH | 2024 | FY | 10-K | 0000731766-25-000063 | 1 | 27 | 27 | extracted | yes |
| UNH | 2024 | FY | 10-K | 0000731766-25-000063 | 1A | 41 | 41 | extracted | yes |
| UNH | 2024 | FY | 10-K | 0000731766-25-000063 | 7 | 34 | 34 | extracted | yes |
| UNH | 2024 | FY | 10-K | 0000731766-25-000063 | 7A | 3 | 3 | extracted | yes |
| UNH | 2024 | FY | 10-K | 0000731766-25-000063 | 8 | 94 | 94 | extracted | yes |
| UNH | 2024 | Q1 | 10-Q | 0000731766-24-000155 | P1-2 | 24 | 24 | extracted | yes |
| UNH | 2024 | Q1 | 10-Q | 0000731766-24-000155 | P2-1A | 1 | 1 | extracted; short (no unresolved reference detected) | yes |
| UNH | 2024 | Q2 | 10-Q | 0000731766-24-000262 | P1-2 | 30 | 30 | extracted | yes |
| UNH | 2024 | Q2 | 10-Q | 0000731766-24-000262 | P2-1A | 1 | 1 | extracted; short (no unresolved reference detected) | yes |
| UNH | 2024 | Q3 | 10-Q | 0000731766-24-000323 | P1-2 | 31 | 31 | extracted | yes |
| UNH | 2024 | Q3 | 10-Q | 0000731766-24-000323 | P2-1A | 1 | 1 | extracted; short (no unresolved reference detected) | yes |
| UNH | 2025 | FY | 10-K | 0000731766-26-000062 | 1 | 28 | 28 | extracted | yes |
| UNH | 2025 | FY | 10-K | 0000731766-26-000062 | 1A | 41 | 41 | extracted | yes |
| UNH | 2025 | FY | 10-K | 0000731766-26-000062 | 7 | 37 | 37 | extracted | yes |
| UNH | 2025 | FY | 10-K | 0000731766-26-000062 | 7A | 3 | 3 | extracted | yes |
| UNH | 2025 | FY | 10-K | 0000731766-26-000062 | 8 | 106 | 106 | extracted | yes |
| UNH | 2025 | Q1 | 10-Q | 0000731766-25-000131 | P1-2 | 23 | 23 | extracted | yes |
| UNH | 2025 | Q1 | 10-Q | 0000731766-25-000131 | P2-1A | 1 | 1 | extracted; short (no unresolved reference detected) | yes |
| UNH | 2025 | Q2 | 10-Q | 0000731766-25-000236 | P1-2 | 32 | 32 | extracted | yes |
| UNH | 2025 | Q2 | 10-Q | 0000731766-25-000236 | P2-1A | 1 | 1 | extracted; short (no unresolved reference detected) | yes |
| UNH | 2025 | Q3 | 10-Q | 0000731766-25-000305 | P1-2 | 32 | 32 | extracted | yes |
| UNH | 2025 | Q3 | 10-Q | 0000731766-25-000305 | P2-1A | 1 | 1 | extracted; short (no unresolved reference detected) | yes |
| UNH | 2026 | Q1 | 10-Q | 0000731766-26-000127 | P1-2 | 27 | 27 | extracted | yes |
| UNH | 2026 | Q1 | 10-Q | 0000731766-26-000127 | P2-1A | 1 | 1 | extracted; short (no unresolved reference detected) | yes |
| UNH | 2026 | Q2 | 10-Q | 0000731766-26-000197 | P1-2 | 34 | 34 | extracted | yes |
| UNH | 2026 | Q2 | 10-Q | 0000731766-26-000197 | P2-1A | 1 | 1 | extracted; short (no unresolved reference detected) | yes |
| WMT | 2024 | FY | 10-K | 0000104169-24-000056 | 1 | 29 | 29 | extracted | yes |
| WMT | 2024 | FY | 10-K | 0000104169-24-000056 | 1A | 56 | 56 | extracted | yes |
| WMT | 2024 | FY | 10-K | 0000104169-24-000056 | 7 | 43 | 43 | extracted | yes |
| WMT | 2024 | FY | 10-K | 0000104169-24-000056 | 7A | 5 | 5 | extracted | yes |
| WMT | 2024 | FY | 10-K | 0000104169-24-000056 | 8 | 94 | 94 | extracted | yes |
| WMT | 2024 | Q1 | 10-Q | 0000104169-23-000052 | P1-2 | 31 | 31 | extracted | yes |
| WMT | 2024 | Q1 | 10-Q | 0000104169-23-000052 | P2-1A | 1 | 1 | extracted; short (no unresolved reference detected) | yes |
| WMT | 2024 | Q2 | 10-Q | 0000104169-23-000097 | P1-2 | 37 | 37 | extracted | yes |
| WMT | 2024 | Q2 | 10-Q | 0000104169-23-000097 | P2-1A | 1 | 1 | extracted; short (no unresolved reference detected) | yes |
| WMT | 2024 | Q3 | 10-Q | 0000104169-23-000132 | P1-2 | 36 | 36 | extracted | yes |
| WMT | 2024 | Q3 | 10-Q | 0000104169-23-000132 | P2-1A | 1 | 1 | extracted; short (no unresolved reference detected) | yes |
| WMT | 2025 | FY | 10-K | 0000104169-25-000021 | 1 | 27 | 27 | extracted | yes |
| WMT | 2025 | FY | 10-K | 0000104169-25-000021 | 1A | 63 | 63 | extracted | yes |
| WMT | 2025 | FY | 10-K | 0000104169-25-000021 | 7 | 43 | 43 | extracted | yes |
| WMT | 2025 | FY | 10-K | 0000104169-25-000021 | 7A | 5 | 5 | extracted | yes |
| WMT | 2025 | FY | 10-K | 0000104169-25-000021 | 8 | 94 | 94 | extracted | yes |
| WMT | 2025 | Q1 | 10-Q | 0000104169-24-000105 | P1-2 | 32 | 32 | extracted | yes |
| WMT | 2025 | Q1 | 10-Q | 0000104169-24-000105 | P2-1A | 1 | 1 | extracted; short (no unresolved reference detected) | yes |
| WMT | 2025 | Q2 | 10-Q | 0000104169-24-000141 | P1-2 | 36 | 36 | extracted | yes |
| WMT | 2025 | Q2 | 10-Q | 0000104169-24-000141 | P2-1A | 1 | 1 | extracted; short (no unresolved reference detected) | yes |
| WMT | 2025 | Q3 | 10-Q | 0000104169-24-000178 | P1-2 | 36 | 36 | extracted | yes |
| WMT | 2025 | Q3 | 10-Q | 0000104169-24-000178 | P2-1A | 1 | 1 | extracted; short (no unresolved reference detected) | yes |
| WMT | 2026 | FY | 10-K | 0000104169-26-000055 | 1 | 23 | 23 | extracted | yes |
| WMT | 2026 | FY | 10-K | 0000104169-26-000055 | 1A | 58 | 58 | extracted | yes |
| WMT | 2026 | FY | 10-K | 0000104169-26-000055 | 7 | 43 | 43 | extracted | yes |
| WMT | 2026 | FY | 10-K | 0000104169-26-000055 | 7A | 5 | 5 | extracted | yes |
| WMT | 2026 | FY | 10-K | 0000104169-26-000055 | 8 | 90 | 90 | extracted | yes |
| WMT | 2026 | Q1 | 10-Q | 0000104169-25-000090 | P1-2 | 29 | 29 | extracted | yes |
| WMT | 2026 | Q1 | 10-Q | 0000104169-25-000090 | P2-1A | 1 | 1 | extracted; short (no unresolved reference detected) | yes |
| WMT | 2026 | Q2 | 10-Q | 0000104169-25-000137 | P1-2 | 35 | 35 | extracted | yes |
| WMT | 2026 | Q2 | 10-Q | 0000104169-25-000137 | P2-1A | 1 | 1 | extracted; short (no unresolved reference detected) | yes |
| WMT | 2026 | Q3 | 10-Q | 0000104169-25-000191 | P1-2 | 35 | 35 | extracted | yes |
| WMT | 2026 | Q3 | 10-Q | 0000104169-25-000191 | P2-1A | 1 | 1 | extracted; short (no unresolved reference detected) | yes |
| WMT | 2027 | Q1 | 10-Q | 0000104169-26-000102 | P1-2 | 30 | 30 | extracted | yes |
| WMT | 2027 | Q1 | 10-Q | 0000104169-26-000102 | P2-1A | 1 | 1 | extracted; short (no unresolved reference detected) | yes |
| WMT | 2027 | Q2 | 10-Q | 0000104169-26-000154 | P1-2 | 37 | 37 | extracted | yes |
| WMT | 2027 | Q2 | 10-Q | 0000104169-26-000154 | P2-1A | 1 | 1 | extracted; short (no unresolved reference detected) | yes |
| XOM | 2023 | FY | 10-K | 0000034088-24-000018 | 1 | 4 | 4 | extracted | yes |
| XOM | 2023 | FY | 10-K | 0000034088-24-000018 | 1A | 20 | 20 | extracted | yes |
| XOM | 2023 | FY | 10-K | 0000034088-24-000018 | 7 | 1 | 82 | resolved | approved repair |
| XOM | 2023 | FY | 10-K | 0000034088-24-000018 | 7A | 1 | 1 | reference covered elsewhere | yes |
| XOM | 2023 | FY | 10-K | 0000034088-24-000018 | 8 | 1 | 190 | resolved | approved repair |
| XOM | 2023 | Q1 | 10-Q | 0000034088-23-000030 | P1-2 | 20 | 20 | extracted | yes |
| XOM | 2023 | Q1 | 10-Q | 0000034088-23-000030 | P2-1A | 0 | 0 | source absent | yes |
| XOM | 2023 | Q2 | 10-Q | 0000034088-23-000048 | P1-2 | 32 | 32 | extracted | yes |
| XOM | 2023 | Q2 | 10-Q | 0000034088-23-000048 | P2-1A | 0 | 0 | source absent | yes |
| XOM | 2023 | Q3 | 10-Q | 0000034088-23-000056 | P1-2 | 38 | 38 | extracted | yes |
| XOM | 2023 | Q3 | 10-Q | 0000034088-23-000056 | P2-1A | 0 | 0 | source absent | yes |
| XOM | 2024 | FY | 10-K | 0000034088-25-000010 | 1 | 4 | 4 | extracted | yes |
| XOM | 2024 | FY | 10-K | 0000034088-25-000010 | 1A | 21 | 21 | extracted | yes |
| XOM | 2024 | FY | 10-K | 0000034088-25-000010 | 7 | 1 | 83 | resolved | approved repair |
| XOM | 2024 | FY | 10-K | 0000034088-25-000010 | 7A | 1 | 1 | reference covered elsewhere | yes |
| XOM | 2024 | FY | 10-K | 0000034088-25-000010 | 8 | 1 | 202 | resolved | approved repair |
| XOM | 2024 | Q1 | 10-Q | 0000034088-24-000029 | P1-2 | 27 | 27 | extracted | yes |
| XOM | 2024 | Q1 | 10-Q | 0000034088-24-000029 | P2-1A | 0 | 0 | source absent | yes |
| XOM | 2024 | Q2 | 10-Q | 0000034088-24-000050 | P1-2 | 36 | 36 | extracted | yes |
| XOM | 2024 | Q2 | 10-Q | 0000034088-24-000050 | P2-1A | 0 | 0 | source absent | yes |
| XOM | 2024 | Q3 | 10-Q | 0000034088-24-000068 | P1-2 | 35 | 35 | extracted | yes |
| XOM | 2024 | Q3 | 10-Q | 0000034088-24-000068 | P2-1A | 0 | 0 | source absent | yes |
| XOM | 2025 | FY | 10-K | 0000034088-26-000045 | 1 | 4 | 4 | extracted | yes |
| XOM | 2025 | FY | 10-K | 0000034088-26-000045 | 1A | 22 | 22 | extracted | yes |
| XOM | 2025 | FY | 10-K | 0000034088-26-000045 | 7 | 1 | 83 | resolved | approved repair |
| XOM | 2025 | FY | 10-K | 0000034088-26-000045 | 7A | 1 | 1 | reference covered elsewhere | yes |
| XOM | 2025 | FY | 10-K | 0000034088-26-000045 | 8 | 1 | 174 | resolved | approved repair |
| XOM | 2025 | Q1 | 10-Q | 0000034088-25-000024 | P1-2 | 26 | 26 | extracted | yes |
| XOM | 2025 | Q1 | 10-Q | 0000034088-25-000024 | P2-1A | 0 | 0 | source absent | yes |
| XOM | 2025 | Q2 | 10-Q | 0000034088-25-000042 | P1-2 | 34 | 34 | extracted | yes |
| XOM | 2025 | Q2 | 10-Q | 0000034088-25-000042 | P2-1A | 0 | 0 | source absent | yes |
| XOM | 2025 | Q3 | 10-Q | 0000034088-25-000061 | P1-2 | 35 | 35 | extracted | yes |
| XOM | 2025 | Q3 | 10-Q | 0000034088-25-000061 | P2-1A | 0 | 0 | source absent | yes |
| XOM | 2026 | Q1 | 10-Q | 0000034088-26-000067 | P1-2 | 20 | 20 | extracted | yes |
| XOM | 2026 | Q1 | 10-Q | 0000034088-26-000067 | P2-1A | 0 | 0 | source absent | yes |
| XOM | 2026 | Q2 | 10-Q | 0000034088-26-000093 | P1-2 | 25 | 25 | extracted | yes |
| XOM | 2026 | Q2 | 10-Q | 0000034088-26-000093 | P2-1A | 0 | 0 | source absent | yes |

# M2 corpus-v2 retrieval evaluation — Phase C

Phase C evaluation is complete and awaits the student's acceptance. M3 has not started. V2 is the active corpus selected for M3 onward; v1 and all historical results remain available.

Corpus: `corpus_3f3c2a9affddcc6a29eca9e768c65bcbd3e2f131fb69595b24b9b92005738739`; fingerprint `d6e2dd9856cdf645873078c0505a690615b680346a95d4d591adcf0b3a18809a`; snapshot `2026-10-19-v1`. 32,960 chunks, 275 filings. Evaluation made no corpus, embedding, schema, dependency or label changes.

## Pre-run validation

Validation passed before metrics: 30 records, 30 unique IDs/texts, 64 gold labels, matching v2 identity/fingerprint, every gold in v2 and consistent with its saved filters. Questions, filters and reference answers exactly match the original/migrated records. All 61 mapped golds were retained; only the student's three approved additions were present. No item filters; six ticker-only cross-year questions and 24 fully period-filtered questions. Gold-size distribution: `{'1': 11, '2': 11, '3': 6, '6': 1, '7': 1}`. Label SHA-256: `6d120892242bb97e9131a0ee4cc2316793f06b837d6149fc5a06a622baea9233`. Corpus content SHA-256 (including stored vectors): `2a877e4ef2ee5cadbcb812f0f592aebd9b3f9ec8f52555a9ffbe5bc74d4670e8`. The same validation and hashes passed after the run.

The two broad questions remain NVIDIA export controls (7 gold, also cross-year) and Microsoft Copilot overview (6 gold); every other question has at most 3 gold chunks.

Cross-year searches use ticker-only filters exactly as saved, but only their named filing is gold: XOM (`hq_efbdb0ea523543c699eddddde9b1e638`), COST (`hq_84c831be7d16420aae81eb2d9f98c8af`), MSFT (`hq_19ea90a4eeb84991845ef0f0a3c4d316`), AMZN (`hq_5404d74f74b4456e9c72c7def4c64227`), NVDA (`hq_9e6c0c0dbb5941589c85ed5a923d944e`), CVX (`hq_e9bf3b51fc6948de9eaa071fdbdb0e46`).

## Fixed protocol and metric definitions

Every mode returns depth 30 with saved filters unchanged. The reranker scores the complete hybrid top 30; candidate-ID sets are checked for equality. D031 OR-over-English-lexemes keyword search, ts_rank_cd, RRF 60, model revisions and the retrieval implementation `retrieval-v2-keyword-or` are unchanged. No variants, weights or thresholds were selected on these results.

For gold set G and the first k distinct results T_k, all metrics are macro-averaged over questions:

- **Primary capped recall@k:** `|G ∩ T_k| / min(k, |G|)` for k=5,10.
- **Standard recall@k:** `|G ∩ T_k| / |G|` for k=5,10.
- **Hit@k:** 1 if `G ∩ T_k` is nonempty, otherwise 0, for k=5,10.
- **MRR@30:** reciprocal rank of the first gold in the first 30, or 0 if absent. An underfilled eligible set is not padded. Capped recall was chosen before the original results (D027), to avoid an unavoidable ceiling for the 6/7-gold questions at k=5.

## V2 Full set (n=30)

| Mode | Capped recall@5 | Capped recall@10 | Recall@5 | Recall@10 | Hit@5 | Hit@10 | MRR@30 |
|---|---:|---:|---:|---:|---:|---:|---:|
| vector | 0.6489 | 0.7333 | 0.6444 | 0.7333 | 0.8667 | 0.9000 | 0.6302 |
| keyword | 0.4800 | 0.5881 | 0.4770 | 0.5881 | 0.6667 | 0.7000 | 0.5275 |
| hybrid | 0.5867 | 0.7159 | 0.5833 | 0.7159 | 0.7667 | 0.8667 | 0.5965 |
| hybrid_rerank | 0.6322 | 0.7492 | 0.6278 | 0.7492 | 0.8333 | 0.9000 | 0.5670 |

## V2 Cross-year (n=6)

| Mode | Capped recall@5 | Capped recall@10 | Recall@5 | Recall@10 | Hit@5 | Hit@10 | MRR@30 |
|---|---:|---:|---:|---:|---:|---:|---:|
| vector | 0.4444 | 0.4444 | 0.4444 | 0.4444 | 0.6667 | 0.6667 | 0.6806 |
| keyword | 0.3944 | 0.3849 | 0.3849 | 0.3849 | 0.6667 | 0.6667 | 0.5500 |
| hybrid | 0.3611 | 0.5238 | 0.3611 | 0.5238 | 0.5000 | 0.8333 | 0.5486 |
| hybrid_rerank | 0.5278 | 0.5516 | 0.5278 | 0.5516 | 0.6667 | 0.8333 | 0.4630 |

## V2 Period-filtered (n=24)

| Mode | Capped recall@5 | Capped recall@10 | Recall@5 | Recall@10 | Hit@5 | Hit@10 | MRR@30 |
|---|---:|---:|---:|---:|---:|---:|---:|
| vector | 0.7000 | 0.8056 | 0.6944 | 0.8056 | 0.9167 | 0.9583 | 0.6176 |
| keyword | 0.5014 | 0.6389 | 0.5000 | 0.6389 | 0.6667 | 0.7083 | 0.5219 |
| hybrid | 0.6431 | 0.7639 | 0.6389 | 0.7639 | 0.8333 | 0.8750 | 0.6085 |
| hybrid_rerank | 0.6583 | 0.7986 | 0.6528 | 0.7986 | 0.8750 | 0.9167 | 0.5930 |

### Main findings

Every mode's reviewed-v2 recall@10 is lower than the archived v1 value. The table below separates changed corpus/rankings from the gold-label effect; these are descriptive differences, not evidence that recovering source content improves this pooled benchmark. Group (a)'s aggregate vector recall@10 is unchanged, while its keyword, hybrid and reranked recall@10 decline.

| Mode | V1 recall@10 | V2 migrated gold | V2 reviewed gold | Corpus/ranking change (pp) | Label-only change (pp) |
|---|---:|---:|---:|---:|---:|
| vector | 0.7556 | 0.7389 | 0.7333 | -1.67 | -0.56 |
| keyword | 0.6325 | 0.5825 | 0.5881 | -5.00 | +0.56 |
| hybrid | 0.7603 | 0.7381 | 0.7159 | -2.22 | -2.22 |
| hybrid_rerank | 0.7714 | 0.7548 | 0.7492 | -1.67 | -0.56 |
## Cache and candidate checks

D026: 24 cached and 96 fresh question/mode searches (120 total). Rankings are independent of labels, so caches remain valid after gold additions. Exact paths/source are saved in retrieval_v2.json. The pre-evaluation cache inventory has four modes for each of the six reviewed questions and no caches for the other 24; it was saved before evaluation populated any new cache.

Hybrid differs from vector on 30/30 rankings. All 30 reranked pools preserve the full hybrid candidate set. The Apple FY2025 Q3 tariff question (`hq_d2c0efbeda48446e88c1160406bc4452`) has 15 eligible chunks, making it easier than the larger search scopes. Short output there is eligible-corpus size, not HNSW starvation.

## V1 versus V2

V1 numbers are the archived **post-keyword-fix** run in retrieval.json/retrieval.md. V1 used 61 gold labels; reviewed v2 uses 64. Overall differences therefore combine corpus/ranking changes and the two student label revisions; the attribution below separates them.

### V1 Full set (n=30)

| Mode | Capped recall@5 | Capped recall@10 | Recall@5 | Recall@10 | Hit@5 | Hit@10 | MRR@30 |
|---|---:|---:|---:|---:|---:|---:|---:|
| vector | 0.6656 | 0.7556 | 0.6611 | 0.7556 | 0.8667 | 0.9000 | 0.6306 |
| keyword | 0.5011 | 0.6325 | 0.5000 | 0.6325 | 0.6667 | 0.7667 | 0.5391 |
| hybrid | 0.6478 | 0.7603 | 0.6444 | 0.7603 | 0.8000 | 0.9000 | 0.6210 |
| hybrid_rerank | 0.6656 | 0.7714 | 0.6611 | 0.7714 | 0.8667 | 0.9333 | 0.5683 |

### V2 minus V1: Full set (n=30)

| Mode | Capped recall@5 | Capped recall@10 | Recall@5 | Recall@10 | Hit@5 | Hit@10 | MRR@30 |
|---|---:|---:|---:|---:|---:|---:|---:|
| vector | -0.0167 | -0.0222 | -0.0167 | -0.0222 | 0.0000 | 0.0000 | -0.0005 |
| keyword | -0.0211 | -0.0444 | -0.0230 | -0.0444 | 0.0000 | -0.0667 | -0.0116 |
| hybrid | -0.0611 | -0.0444 | -0.0611 | -0.0444 | -0.0333 | -0.0333 | -0.0245 |
| hybrid_rerank | -0.0333 | -0.0222 | -0.0333 | -0.0222 | -0.0333 | -0.0333 | -0.0012 |

### V1 Cross-year (n=6)

| Mode | Capped recall@5 | Capped recall@10 | Recall@5 | Recall@10 | Hit@5 | Hit@10 | MRR@30 |
|---|---:|---:|---:|---:|---:|---:|---:|
| vector | 0.4167 | 0.5000 | 0.4167 | 0.5000 | 0.6667 | 0.6667 | 0.6806 |
| keyword | 0.3333 | 0.4405 | 0.3333 | 0.4405 | 0.5000 | 0.8333 | 0.5486 |
| hybrid | 0.3333 | 0.5238 | 0.3333 | 0.5238 | 0.5000 | 0.8333 | 0.5497 |
| hybrid_rerank | 0.5833 | 0.6071 | 0.5833 | 0.6071 | 0.8333 | 1.0000 | 0.4963 |

### V2 minus V1: Cross-year (n=6)

| Mode | Capped recall@5 | Capped recall@10 | Recall@5 | Recall@10 | Hit@5 | Hit@10 | MRR@30 |
|---|---:|---:|---:|---:|---:|---:|---:|
| vector | 0.0278 | -0.0556 | 0.0278 | -0.0556 | 0.0000 | 0.0000 | 0.0000 |
| keyword | 0.0611 | -0.0556 | 0.0516 | -0.0556 | 0.1667 | -0.1667 | 0.0014 |
| hybrid | 0.0278 | 0.0000 | 0.0278 | 0.0000 | 0.0000 | 0.0000 | -0.0011 |
| hybrid_rerank | -0.0556 | -0.0556 | -0.0556 | -0.0556 | -0.1667 | -0.1667 | -0.0333 |

### V1 Period-filtered (n=24)

| Mode | Capped recall@5 | Capped recall@10 | Recall@5 | Recall@10 | Hit@5 | Hit@10 | MRR@30 |
|---|---:|---:|---:|---:|---:|---:|---:|
| vector | 0.7278 | 0.8194 | 0.7222 | 0.8194 | 0.9167 | 0.9583 | 0.6182 |
| keyword | 0.5431 | 0.6806 | 0.5417 | 0.6806 | 0.7083 | 0.7500 | 0.5368 |
| hybrid | 0.7264 | 0.8194 | 0.7222 | 0.8194 | 0.8750 | 0.9167 | 0.6389 |
| hybrid_rerank | 0.6861 | 0.8125 | 0.6806 | 0.8125 | 0.8750 | 0.9167 | 0.5863 |

### V2 minus V1: Period-filtered (n=24)

| Mode | Capped recall@5 | Capped recall@10 | Recall@5 | Recall@10 | Hit@5 | Hit@10 | MRR@30 |
|---|---:|---:|---:|---:|---:|---:|---:|
| vector | -0.0278 | -0.0139 | -0.0278 | -0.0139 | 0.0000 | 0.0000 | -0.0006 |
| keyword | -0.0417 | -0.0417 | -0.0417 | -0.0417 | -0.0417 | -0.0417 | -0.0149 |
| hybrid | -0.0833 | -0.0556 | -0.0833 | -0.0556 | -0.0417 | -0.0417 | -0.0304 |
| hybrid_rerank | -0.0278 | -0.0139 | -0.0278 | -0.0139 | 0.0000 | 0.0000 | 0.0068 |

## Label-change attribution

Group (a): 28 questions with identical semantic gold after exact-ID migration. This compares changed candidate corpus/rankings with fixed labels. All IDs changed, so ID-based tie-breaking can also change ranks, even where eligible passage text is identical. This is not a controlled estimate of the parser alone. Group (b): the two student-changed questions, JPM cybersecurity (+2 FY2024 Item 7) and Chevron/Hess (+1 FY2024 Item 8). No gold was removed. For group (b), score the same v2 rankings twice: first with the 61 original migrated golds (bridge), then with the 64 reviewed golds. The second difference is only the label effect, including changed denominators.

Read-only verification confirmed the tie explanation for all **24 group (a) questions whose saved filters cover no repaired section**. Eligible passage text and stored tsvectors are identical across versions, and vector top-30 rankings are identical by passage text for all 24. Keyword rankings differ in 467 rank slots: all 504 passage movements (including 37 entering and 37 leaving the top 30) cross only neighbors with exactly equal `ts_rank_cd` scores, verified using PostgreSQL float4 bytes and archived cache scores. There are zero unexplained changes. Keyword exact-score ties are broken by chunk ID; thus keyword and downstream hybrid differences within these unchanged scopes are tie noise rather than a retrieval-content change. This conclusion does not extend to scopes containing repaired sections. Across all 30 questions, 752/877 v1 keyword result slots (85.75%) and 750/877 v2 slots (85.52%) share an exact score with another slot in the same top-30 list. The tie-breaking rule is unchanged. See the [verification report](../../docs/CORPUS_V2_TIE_VERIFICATION.md) and [per-movement evidence](../../docs/CORPUS_V2_TIE_VERIFICATION.json). No retrieval evaluation was rerun and no rankings or labels changed.

### Group (a), n=28: V1 original gold

| Mode | Capped recall@5 | Capped recall@10 | Recall@5 | Recall@10 | Hit@5 | Hit@10 | MRR@30 |
|---|---:|---:|---:|---:|---:|---:|---:|
| vector | 0.6595 | 0.7381 | 0.6548 | 0.7381 | 0.8571 | 0.8929 | 0.6043 |
| keyword | 0.5190 | 0.6599 | 0.5179 | 0.6599 | 0.6786 | 0.7857 | 0.5392 |
| hybrid | 0.6405 | 0.7432 | 0.6369 | 0.7432 | 0.7857 | 0.8929 | 0.5940 |
| hybrid_rerank | 0.6595 | 0.7730 | 0.6548 | 0.7730 | 0.8571 | 0.9286 | 0.5374 |

### Group (a), n=28: V2 migrated gold (bridge)

| Mode | Capped recall@5 | Capped recall@10 | Recall@5 | Recall@10 | Hit@5 | Hit@10 | MRR@30 |
|---|---:|---:|---:|---:|---:|---:|---:|
| vector | 0.6595 | 0.7381 | 0.6548 | 0.7381 | 0.8571 | 0.8929 | 0.6038 |
| keyword | 0.4905 | 0.6063 | 0.4872 | 0.6063 | 0.6786 | 0.7143 | 0.5295 |
| hybrid | 0.5929 | 0.7194 | 0.5893 | 0.7194 | 0.7500 | 0.8571 | 0.5945 |
| hybrid_rerank | 0.6417 | 0.7551 | 0.6369 | 0.7551 | 0.8214 | 0.8929 | 0.5361 |

### Group (a), n=28: V2 reviewed gold

| Mode | Capped recall@5 | Capped recall@10 | Recall@5 | Recall@10 | Hit@5 | Hit@10 | MRR@30 |
|---|---:|---:|---:|---:|---:|---:|---:|
| vector | 0.6595 | 0.7381 | 0.6548 | 0.7381 | 0.8571 | 0.8929 | 0.6038 |
| keyword | 0.4905 | 0.6063 | 0.4872 | 0.6063 | 0.6786 | 0.7143 | 0.5295 |
| hybrid | 0.5929 | 0.7194 | 0.5893 | 0.7194 | 0.7500 | 0.8571 | 0.5945 |
| hybrid_rerank | 0.6417 | 0.7551 | 0.6369 | 0.7551 | 0.8214 | 0.8929 | 0.5361 |

### Group (b), n=2: V1 original gold

| Mode | Capped recall@5 | Capped recall@10 | Recall@5 | Recall@10 | Hit@5 | Hit@10 | MRR@30 |
|---|---:|---:|---:|---:|---:|---:|---:|
| vector | 0.7500 | 1.0000 | 0.7500 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| keyword | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 0.5000 | 0.5000 | 0.5385 |
| hybrid | 0.7500 | 1.0000 | 0.7500 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| hybrid_rerank | 0.7500 | 0.7500 | 0.7500 | 0.7500 | 1.0000 | 1.0000 | 1.0000 |

### Group (b), n=2: V2 migrated gold (bridge)

| Mode | Capped recall@5 | Capped recall@10 | Recall@5 | Recall@10 | Hit@5 | Hit@10 | MRR@30 |
|---|---:|---:|---:|---:|---:|---:|---:|
| vector | 0.7500 | 0.7500 | 0.7500 | 0.7500 | 1.0000 | 1.0000 | 0.7500 |
| keyword | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 0.5000 | 0.5000 | 0.1000 |
| hybrid | 0.7500 | 1.0000 | 0.7500 | 1.0000 | 1.0000 | 1.0000 | 0.3750 |
| hybrid_rerank | 0.7500 | 0.7500 | 0.7500 | 0.7500 | 1.0000 | 1.0000 | 1.0000 |

### Group (b), n=2: V2 reviewed gold

| Mode | Capped recall@5 | Capped recall@10 | Recall@5 | Recall@10 | Hit@5 | Hit@10 | MRR@30 |
|---|---:|---:|---:|---:|---:|---:|---:|
| vector | 0.5000 | 0.6667 | 0.5000 | 0.6667 | 1.0000 | 1.0000 | 1.0000 |
| keyword | 0.3333 | 0.3333 | 0.3333 | 0.3333 | 0.5000 | 0.5000 | 0.5000 |
| hybrid | 0.5000 | 0.6667 | 0.5000 | 0.6667 | 1.0000 | 1.0000 | 0.6250 |
| hybrid_rerank | 0.5000 | 0.6667 | 0.5000 | 0.6667 | 1.0000 | 1.0000 | 1.0000 |

### Group (b) added passages

| Question | Added gold ID | Item | Vector rank | Keyword rank | Hybrid rank | Reranked rank |
|---|---|---|---:|---:|---:|---:|
| hq_af3e0e0473af430b83dd4dc7e4bb1eef | chk_021110f70060ece24f43bb90853f0a55e0800ba742a560117bc473b4c7147e54 | 7 | 9 | >30 | 19 | 9 |
| hq_af3e0e0473af430b83dd4dc7e4bb1eef | chk_c322c2651975aa09a7091a8b8608aa632282a76a3365b282535563343eb0d813 | 7 | >30 | >30 | >30 | >30 |
| hq_e9bf3b51fc6948de9eaa071fdbdb0e46 | chk_ac40d0b888b22106ef53175cb5c3996f79aa6298dc5fb4cae00b326cb3709543 | 8 | 1 | 1 | 1 | 5 |

## Per-question first-gold rank changes

Each mode cell is **v1 original-gold rank → v2 reviewed-gold rank**; `>30` means no gold in the returned top 30. Group (b) also changes labels; its bridge results are preserved in retrieval_v2_analyses.json.

| ID | Short question | Ticker | Group | Gold v1→v2 | Vector | Keyword | Hybrid | Hybrid rerank |
|---|---|---|---|---|---|---|---|---|
| hq_05c3197fe2084357b5c9ca0582b713f2 | What restructuring plan did P&G announce in fiscal 2025, and why did it start it? | PG | a | 1→1 | 3 → 3 | 1 → 1 | 2 → 1 | 1 → 1 |
| hq_19ea90a4eeb84991845ef0f0a3c4d316 | Why did Microsoft's cloud profit margins shrink in fiscal 2025 while cloud sales grew | MSFT | a | 2→2 | 1 → 1 | >30 → >30 | 7 → 6 | 3 → 3 |
| hq_21f4a3b2e4e044129aee7a3fa547a79b | Why did Nike's sales fall in fiscal 2025? | NKE | a | 3→3 | 4 → 4 | 1 → 1 | 1 → 1 | 6 → 6 |
| hq_24a3e4ca8e144f708dc1df755db10222 | How exposed is Amazon to swings in currency exchange rates? | AMZN | a | 1→1 | 3 → 3 | 3 → 2 | 1 → 1 | 11 → 11 |
| hq_395269fb91c24e7aba645db4529fd483 | What liquidity risks does Bank of America describe related to deposit outflows? | BAC | a | 3→3 | 4 → 4 | >30 → >30 | 10 → 12 | 16 → 17 |
| hq_3bc57255183d4bdeabdba814d9c2f4a7 | What does Apple's value-at-risk model estimate for its foreign currency exposure? | AAPL | a | 1→1 | 1 → 1 | 1 → 1 | 1 → 1 | 1 → 1 |
| hq_3d27d3a6bc924f74ab4e2b4f2a914397 | Why did Pfizer's COVID vaccine and pill sales collapse in 2023? | PFE | a | 2→2 | 1 → 1 | >30 → >30 | 11 → 12 | 3 → 3 |
| hq_4d5d9efc06f34ddaa145f699ce2c2e4d | How could Meta's heavy spending on virtual and augmented reality go wrong? | META | a | 3→3 | 2 → 2 | 2 → 3 | 2 → 2 | 4 → 3 |
| hq_5404d74f74b4456e9c72c7def4c64227 | What factors drove the change in AWS segment operating income in 2024? | AMZN | a | 2→2 | 1 → 1 | 1 → 1 | 1 → 1 | 1 → 1 |
| hq_69c1bbc69ab243d29a5b85972d80828e | Why did Tesla make less profit on its cars in 2024? | TSLA | a | 2→2 | 1 → 1 | 15 → 15 | 1 → 1 | 1 → 1 |
| hq_74fd7fdce150403baad26a906223ba57 | What happens to Chevron if oil prices stay low for a long time? | CVX | a | 1→1 | 1 → 1 | 6 → 11 | 2 → 3 | 3 → 3 |
| hq_804ee5491dee4faaa512e49ecdfc1dd0 | Why did NVIDIA write off billions in chip inventory in early fiscal 2026? | NVDA | a | 3→3 | 2 → 2 | 3 → 4 | 2 → 2 | 3 → 3 |
| hq_84c831be7d16420aae81eb2d9f98c8af | How did the membership fee increase affect Costco's membership fee income in fiscal 2 | COST | a | 1→1 | 1 → 1 | 1 → 1 | 1 → 1 | 3 → 3 |
| hq_8c86cd7564ba43deb72940f9fe800767 | How did Disney explain the improvement in Direct-to-Consumer operating income in fisc | DIS | a | 1→1 | 19 → 26 | 3 → 4 | 4 → 8 | 2 → 2 |
| hq_9244d7ed50884988a8b0fcc969655431 | How did Alphabet explain the increase in capital expenditures for technical infrastru | GOOGL | a | 2→2 | 1 → 1 | 3 → 3 | 2 → 2 | 1 → 1 |
| hq_9e6c0c0dbb5941589c85ed5a923d944e | In fiscal 2025, how did NVIDIA describe the risk of U.S. export controls on sales to  | NVDA | a | 7→7 | 12 → 12 | 6 → 4 | 10 → 8 | 9 → 9 |
| hq_9f2123ab94e5409ba2375e444df03060 | How did buying Pioneer change Exxon's oil and gas production in 2024? | XOM | a | 1→1 | 2 → 2 | 1 → 1 | 1 → 1 | 1 → 1 |
| hq_af3da89ebdb6499f84b1103586988fcc | How does Coca-Cola price the concentrate it sells to its bottlers? | KO | a | 2→2 | 5 → 5 | 1 → 1 | 2 → 2 | 3 → 3 |
| hq_af3e0e0473af430b83dd4dc7e4bb1eef | Why does JPMorgan Chase say it cannot guarantee absolute security against cyberattack | JPM | b | 1→3 | 1 → 1 | 13 → >30 | 1 → 4 | 1 → 1 |
| hq_bbeba329b2724abcbbff1ea7869b3907 | What savings does Pfizer expect from its Cost Realignment Program? | PFE | a | 1→1 | 4 → 4 | 2 → 2 | 2 → 2 | 1 → 1 |
| hq_beb86dbbb9224fdcade1fe13bd690a88 | How much did eCommerce contribute to Walmart U.S. comparable sales in fiscal 2025? | WMT | a | 2→2 | 1 → 1 | 1 → 1 | 1 → 1 | 1 → 1 |
| hq_c65d4576350841669beea4c8dbea0a2b | How does Coke protect itself against currency and commodity price swings? | KO | a | 2→2 | 4 → 4 | 1 → 1 | 1 → 1 | 4 → 3 |
| hq_cdeefd822cd94dd98c915d26380f37ed | How did the 2024 hack of UnitedHealth's payment-processing unit affect the company? | UNH | a | 2→2 | 1 → 1 | 26 → 29 | 2 → 3 | 2 → 2 |
| hq_ce9809903d0b430eb90e3615603210f7 | How does Microsoft describe its Copilot and AI offerings in its business overview? | MSFT | a | 6→6 | 1 → 1 | 1 → 1 | 1 → 1 | 1 → 1 |
| hq_d2c0efbeda48446e88c1160406bc4452 | How were new tariffs hitting Apple's costs in mid-2025? | AAPL | a | 1→1 | 1 → 1 | 1 → 1 | 1 → 1 | 1 → 1 |
| hq_e3dfcc6ccd02482fb791dc34596565e7 | How would Bank of America's net interest income change if interest rates suddenly fel | BAC | a | 1→1 | 4 → 4 | >30 → >30 | 17 → 16 | 4 → 4 |
| hq_e9bf3b51fc6948de9eaa071fdbdb0e46 | As of its fiscal 2024 10-K, what was the status of Chevron's Hess acquisition and the | CVX | b | 2→3 | 1 → 1 | 1 → 1 | 1 → 1 | 1 → 1 |
| hq_eead0b7f7e3f430589800660cafe8cb1 | Why were UnitedHealth's medical costs higher than expected in 2025? | UNH | a | 2→2 | 6 → 6 | 1 → 1 | 2 → 2 | 3 → 3 |
| hq_efbdb0ea523543c699eddddde9b1e638 | How does ExxonMobil's 2024 10-K say greenhouse gas regulations could hurt its busines | XOM | a | 2→2 | >30 → >30 | 8 → 20 | 18 → >30 | 5 → >30 |
| hq_f5d53183cdd04505b02cde17b599d44f | What risks does Johnson & Johnson describe from Medicare drug price negotiation under | JNJ | a | 1→1 | 1 → 1 | 5 → 6 | 3 → 3 | 3 → 3 |

## Reranker check

First-gold ranks: 8 better / 10 worse / 12 same versus hybrid. Every demotion out of the top 5 or top 10:

| Question | Hybrid | Reranked | Pushed outside k |
|---|---:|---:|---|
| hq_21f4a3b2e4e044129aee7a3fa547a79b | 1 | 6 | 5 |
| hq_24a3e4ca8e144f708dc1df755db10222 | 1 | 11 | 5, 10 |

Full set (n=30): hybrid → reranked recall@10 0.7159 → 0.7492; capped recall@5 0.5867 → 0.6322; MRR@30 0.5965 → 0.5670.

Cross-year (n=6): hybrid → reranked recall@10 0.5238 → 0.5516; capped recall@5 0.3611 → 0.5278; MRR@30 0.5486 → 0.4630.

Period-filtered (n=24): hybrid → reranked recall@10 0.7639 → 0.7986; capped recall@5 0.6431 → 0.6583; MRR@30 0.6085 → 0.5930.

Overall, reranking raises recall@10 from 0.7159 to 0.7492, but lowers MRR@30 from 0.5965 to 0.5670. It improves recovery within ten while worsening first-gold ordering on average; the counts and individual demotions above describe the observed behavior.

### Paired comparisons

Wins use each question's primary capped recall@10. n=30 is small; differences of a few questions are not conclusive.

| Mode A | Mode B | A wins | B wins | Ties |
|---|---|---:|---:|---:|
| vector | keyword | 9 | 6 | 15 |
| vector | hybrid | 6 | 7 | 17 |
| vector | hybrid_rerank | 4 | 7 | 19 |
| keyword | hybrid | 2 | 8 | 20 |
| keyword | hybrid_rerank | 3 | 9 | 18 |
| hybrid | hybrid_rerank | 5 | 6 | 19 |

## Unjudged candidates and pooled-label limitations

The CLI did not save pool-membership/view history. We cannot assert which non-gold passages the student read. Two reconstructions are reported without assigning new labels:

1. **Labeling-exposure proxy (primary analysis):** uniquely exact-map the archived v1 labeling-pool IDs by accession/item/text into v2; add the pre-evaluation four-mode depth-30 v2 pools for the six reviewed questions and all 64 known golds (manual browsing evidence). Do not add evaluation-generated caches. Unmatched/ambiguous old non-gold candidates are excluded and listed in the JSON evidence. This remains a reconstruction, not a view log.
2. **V2 pooling-definition reconstruction:** union all four current v2 depth-30 rankings per question with its saved filters. Every mode's top 5/10 is necessarily in that union, so its unjudged rate is zero by construction. That does not show that all these passages were reviewed or are relevant; the other 24 questions were migrated without v2 rejudging.

For each mode/k, the fraction is unjudged returned slots / actual returned slots, pooled over questions. Known gold always counts as judged. Unjudged relevant chunks receive no credit under these labels, so keyword/hybrid and other modes may be under-credited. Golds are not exhaustive judgments, and the same systems supply the candidate pools.

| Mode | Exposure proxy top-5 | Exposure proxy top-10 | V2 definition top-5 | V2 definition top-10 |
|---|---:|---:|---:|---:|
| vector | 0/150 (0.00%) | 0/300 (0.00%) | 0/150 (0.00%) | 0/300 (0.00%) |
| keyword | 40/150 (26.67%) | 87/300 (29.00%) | 0/150 (0.00%) | 0/300 (0.00%) |
| hybrid | 0/150 (0.00%) | 8/300 (2.67%) | 0/150 (0.00%) | 0/300 (0.00%) |
| hybrid_rerank | 7/150 (4.67%) | 29/300 (9.67%) | 0/150 (0.00%) | 0/300 (0.00%) |

### Per-question unjudged rates

Each cell shows exposure-proxy top-5 / top-10 counts and rates. The separate v2-definition rates are 0% for every question/mode, as explained above.

| Question | Vector | Keyword | Hybrid | Hybrid rerank |
|---|---|---|---|---|
| hq_05c3197fe2084357b5c9ca0582b713f2 | 0/5 (0.0%) / 0/10 (0.0%) | 2/5 (40.0%) / 5/10 (50.0%) | 0/5 (0.0%) / 0/10 (0.0%) | 0/5 (0.0%) / 0/10 (0.0%) |
| hq_19ea90a4eeb84991845ef0f0a3c4d316 | 0/5 (0.0%) / 0/10 (0.0%) | 5/5 (100.0%) / 10/10 (100.0%) | 0/5 (0.0%) / 2/10 (20.0%) | 0/5 (0.0%) / 1/10 (10.0%) |
| hq_21f4a3b2e4e044129aee7a3fa547a79b | 0/5 (0.0%) / 0/10 (0.0%) | 1/5 (20.0%) / 4/10 (40.0%) | 0/5 (0.0%) / 0/10 (0.0%) | 0/5 (0.0%) / 0/10 (0.0%) |
| hq_24a3e4ca8e144f708dc1df755db10222 | 0/5 (0.0%) / 0/10 (0.0%) | 1/5 (20.0%) / 2/10 (20.0%) | 0/5 (0.0%) / 0/10 (0.0%) | 0/5 (0.0%) / 2/10 (20.0%) |
| hq_395269fb91c24e7aba645db4529fd483 | 0/5 (0.0%) / 0/10 (0.0%) | 3/5 (60.0%) / 7/10 (70.0%) | 0/5 (0.0%) / 1/10 (10.0%) | 2/5 (40.0%) / 3/10 (30.0%) |
| hq_3bc57255183d4bdeabdba814d9c2f4a7 | 0/5 (0.0%) / 0/10 (0.0%) | 1/5 (20.0%) / 4/10 (40.0%) | 0/5 (0.0%) / 0/10 (0.0%) | 0/5 (0.0%) / 1/10 (10.0%) |
| hq_3d27d3a6bc924f74ab4e2b4f2a914397 | 0/5 (0.0%) / 0/10 (0.0%) | 2/5 (40.0%) / 5/10 (50.0%) | 0/5 (0.0%) / 0/10 (0.0%) | 0/5 (0.0%) / 0/10 (0.0%) |
| hq_4d5d9efc06f34ddaa145f699ce2c2e4d | 0/5 (0.0%) / 0/10 (0.0%) | 3/5 (60.0%) / 5/10 (50.0%) | 0/5 (0.0%) / 0/10 (0.0%) | 2/5 (40.0%) / 4/10 (40.0%) |
| hq_5404d74f74b4456e9c72c7def4c64227 | 0/5 (0.0%) / 0/10 (0.0%) | 1/5 (20.0%) / 2/10 (20.0%) | 0/5 (0.0%) / 0/10 (0.0%) | 0/5 (0.0%) / 1/10 (10.0%) |
| hq_69c1bbc69ab243d29a5b85972d80828e | 0/5 (0.0%) / 0/10 (0.0%) | 4/5 (80.0%) / 7/10 (70.0%) | 0/5 (0.0%) / 0/10 (0.0%) | 0/5 (0.0%) / 3/10 (30.0%) |
| hq_74fd7fdce150403baad26a906223ba57 | 0/5 (0.0%) / 0/10 (0.0%) | 0/5 (0.0%) / 0/10 (0.0%) | 0/5 (0.0%) / 0/10 (0.0%) | 0/5 (0.0%) / 0/10 (0.0%) |
| hq_804ee5491dee4faaa512e49ecdfc1dd0 | 0/5 (0.0%) / 0/10 (0.0%) | 0/5 (0.0%) / 1/10 (10.0%) | 0/5 (0.0%) / 0/10 (0.0%) | 0/5 (0.0%) / 0/10 (0.0%) |
| hq_84c831be7d16420aae81eb2d9f98c8af | 0/5 (0.0%) / 0/10 (0.0%) | 1/5 (20.0%) / 2/10 (20.0%) | 0/5 (0.0%) / 0/10 (0.0%) | 0/5 (0.0%) / 2/10 (20.0%) |
| hq_8c86cd7564ba43deb72940f9fe800767 | 0/5 (0.0%) / 0/10 (0.0%) | 0/5 (0.0%) / 0/10 (0.0%) | 0/5 (0.0%) / 0/10 (0.0%) | 0/5 (0.0%) / 0/10 (0.0%) |
| hq_9244d7ed50884988a8b0fcc969655431 | 0/5 (0.0%) / 0/10 (0.0%) | 0/5 (0.0%) / 2/10 (20.0%) | 0/5 (0.0%) / 0/10 (0.0%) | 0/5 (0.0%) / 1/10 (10.0%) |
| hq_9e6c0c0dbb5941589c85ed5a923d944e | 0/5 (0.0%) / 0/10 (0.0%) | 0/5 (0.0%) / 0/10 (0.0%) | 0/5 (0.0%) / 0/10 (0.0%) | 0/5 (0.0%) / 0/10 (0.0%) |
| hq_9f2123ab94e5409ba2375e444df03060 | 0/5 (0.0%) / 0/10 (0.0%) | 0/5 (0.0%) / 1/10 (10.0%) | 0/5 (0.0%) / 0/10 (0.0%) | 0/5 (0.0%) / 0/10 (0.0%) |
| hq_af3da89ebdb6499f84b1103586988fcc | 0/5 (0.0%) / 0/10 (0.0%) | 2/5 (40.0%) / 3/10 (30.0%) | 0/5 (0.0%) / 0/10 (0.0%) | 0/5 (0.0%) / 0/10 (0.0%) |
| hq_af3e0e0473af430b83dd4dc7e4bb1eef | 0/5 (0.0%) / 0/10 (0.0%) | 0/5 (0.0%) / 0/10 (0.0%) | 0/5 (0.0%) / 0/10 (0.0%) | 0/5 (0.0%) / 0/10 (0.0%) |
| hq_bbeba329b2724abcbbff1ea7869b3907 | 0/5 (0.0%) / 0/10 (0.0%) | 0/5 (0.0%) / 2/10 (20.0%) | 0/5 (0.0%) / 0/10 (0.0%) | 0/5 (0.0%) / 0/10 (0.0%) |
| hq_beb86dbbb9224fdcade1fe13bd690a88 | 0/5 (0.0%) / 0/10 (0.0%) | 0/5 (0.0%) / 0/10 (0.0%) | 0/5 (0.0%) / 0/10 (0.0%) | 0/5 (0.0%) / 0/10 (0.0%) |
| hq_c65d4576350841669beea4c8dbea0a2b | 0/5 (0.0%) / 0/10 (0.0%) | 4/5 (80.0%) / 7/10 (70.0%) | 0/5 (0.0%) / 2/10 (20.0%) | 1/5 (20.0%) / 2/10 (20.0%) |
| hq_cdeefd822cd94dd98c915d26380f37ed | 0/5 (0.0%) / 0/10 (0.0%) | 4/5 (80.0%) / 9/10 (90.0%) | 0/5 (0.0%) / 3/10 (30.0%) | 1/5 (20.0%) / 6/10 (60.0%) |
| hq_ce9809903d0b430eb90e3615603210f7 | 0/5 (0.0%) / 0/10 (0.0%) | 1/5 (20.0%) / 1/10 (10.0%) | 0/5 (0.0%) / 0/10 (0.0%) | 0/5 (0.0%) / 0/10 (0.0%) |
| hq_d2c0efbeda48446e88c1160406bc4452 | 0/5 (0.0%) / 0/10 (0.0%) | 0/5 (0.0%) / 0/10 (0.0%) | 0/5 (0.0%) / 0/10 (0.0%) | 0/5 (0.0%) / 0/10 (0.0%) |
| hq_e3dfcc6ccd02482fb791dc34596565e7 | 0/5 (0.0%) / 0/10 (0.0%) | 2/5 (40.0%) / 4/10 (40.0%) | 0/5 (0.0%) / 0/10 (0.0%) | 1/5 (20.0%) / 2/10 (20.0%) |
| hq_e9bf3b51fc6948de9eaa071fdbdb0e46 | 0/5 (0.0%) / 0/10 (0.0%) | 0/5 (0.0%) / 0/10 (0.0%) | 0/5 (0.0%) / 0/10 (0.0%) | 0/5 (0.0%) / 0/10 (0.0%) |
| hq_eead0b7f7e3f430589800660cafe8cb1 | 0/5 (0.0%) / 0/10 (0.0%) | 0/5 (0.0%) / 0/10 (0.0%) | 0/5 (0.0%) / 0/10 (0.0%) | 0/5 (0.0%) / 0/10 (0.0%) |
| hq_efbdb0ea523543c699eddddde9b1e638 | 0/5 (0.0%) / 0/10 (0.0%) | 0/5 (0.0%) / 0/10 (0.0%) | 0/5 (0.0%) / 0/10 (0.0%) | 0/5 (0.0%) / 0/10 (0.0%) |
| hq_f5d53183cdd04505b02cde17b599d44f | 0/5 (0.0%) / 0/10 (0.0%) | 3/5 (60.0%) / 4/10 (40.0%) | 0/5 (0.0%) / 0/10 (0.0%) | 0/5 (0.0%) / 1/10 (10.0%) |

## Cross-year different-filing overlap

D032's unchanged heuristic flags five-word-shingle containment ≥0.70 with a gold from a different accession, requiring at least 20 shingles on each side. It is not a relevance label or proof of answer equivalence. The JSON lists all 120 top-10 vector/reranked slots with IDs, ticker, form, fiscal year, period, item, accession, overlap and closest gold.

| Question | Ticker | Vector near-duplicates / 10 | Reranked near-duplicates / 10 |
|---|---|---:|---:|
| hq_19ea90a4eeb84991845ef0f0a3c4d316 | MSFT | 0 | 0 |
| hq_5404d74f74b4456e9c72c7def4c64227 | AMZN | 0 | 0 |
| hq_84c831be7d16420aae81eb2d9f98c8af | COST | 0 | 0 |
| hq_9e6c0c0dbb5941589c85ed5a923d944e | NVDA | 4 | 3 |
| hq_e9bf3b51fc6948de9eaa071fdbdb0e46 | CVX | 1 | 1 |
| hq_efbdb0ea523543c699eddddde9b1e638 | XOM | 0 | 0 |

These measured overlaps do not establish that cross-year misses mostly reflect year disambiguation rather than topical retrieval failure. Unjudged passages cannot be classified from these labels alone. Period resolution is the M4 planner's responsibility.

## Coverage, methodology and remaining limits

The [Phase B report](../../docs/CORPUS_V2_PHASE_B.md) and [730-slot audit](../../docs/CORPUS_V2_AUDIT.json) document 46 resolved substantive sections, nine retained Item 7A reference stubs in the 55 repair slots, and byte-identical sections outside them. CVX/JPM/XOM market risk remains inside Item 7; DIS/NVIDIA retain separate Item 7A spans. All 22 JNJ/XOM quarterly risk items are absent from cached source, with provenance; no content was synthesized. Source absence and annual-reference availability still require explicit handling in later interfaces. No corpus repair ran in Phase C.

Gold means the passage answers the question as a main point. Passing mentions and an overlap-only tail do not count. Adjacent chunks are both gold when both are needed. A how-much table is not gold for a why question. Cross-year gold is confined to the named filing. Questions were narrowed to at most three chunks except the two intentional broad ones. Questions were AI-assisted drafts, then student-edited/narrowed and student-labeled; all new relevance judgments in this review were the student's. Original labeling edits and limitations remain documented in the unchanged [v1 report](retrieval.md).

Saved filters resolve yearless questions in M2; a future text-only agent must resolve that ambiguity. PG ends June 30 and joins the non-December fiscal-calendar cases; add calendar-year-phrased planner questions in a later milestone. There is no held-out relevance set here, and no prompt or retrieval tuning was performed in Phase C.

## Checks and handoff

See [Phase C checks](../../docs/CORPUS_V2_PHASE_C_CHECKS.md) for exact commands, Ruff/pytest results and preservation hashes. Machine-readable results: [rankings/metrics](retrieval_v2.json), [analyses](retrieval_v2_analyses.json), [pre-evaluation pool inventory](retrieval_v2_pool_inventory.json). The original retrieval.md/JSON, v1 labels, Phase B reports and both frozen corpora remain unchanged. Phase C and corpus v2 are accepted following the student's conditional acceptance and successful read-only tie verification. M3 remains unstarted pending a separate task.

# M2 retrieval evaluation

Corpus: `corpus_2fb48958e274daed46c19e3fbf2583213e308b1eebaa16a04cfdc8052eea82e7`; snapshot `2026-10-19-v1`.
23,441 chunks, 275 filings; corpus and labels unchanged throughout this run.

## Pre-run validation

Validation was reported to the student before metrics were computed: exactly 30 records, unique IDs and question texts; every corpus ID/fingerprint and gold ID/filter matches. No `items` filters. JNJ was re-saved by the student with FY2024/FY filters; verified. There are exactly six approved ticker-only searches and 24 company/year/period searches.

Corpus fingerprint: `048cd70c9ea01cf49cd50ea18b74e6738298597a7ab89026a3c6d04fb824f51f`.
Label SHA-256: `d7b364662b9aa97f5c8616079297ff81322a7179583e2cb663c3614640896f04`.
Chunk metadata/text/vector digest before and after: `c86236eab76aee9189cc3fb5d8ab1c3272a8d69b2299e12c4af03ffaf9bb4ca2`.

Gold sizes: 12 questions with 1, 12 with 2, 4 with 3, 1 with 6, and 1 with 7.

Questions with more than three gold chunks:

- `hq_9e6c0c0dbb5941589c85ed5a923d944e`: In fiscal 2025, how did NVIDIA describe the risk of U.S. export controls on sales to China? (7 gold).
- `hq_ce9809903d0b430eb90e3615603210f7`: How does Microsoft describe its Copilot and AI offerings in its business overview? (6 gold).

### Intentional cross-year subset (n=6)

These searches span all available periods; only the filing named in the question is gold. This is a harder search scope than period-filtered retrieval, although these small, different question groups are not a controlled difficulty comparison.

- `hq_19ea90a4eeb84991845ef0f0a3c4d316` (MSFT): Why did Microsoft's cloud profit margins shrink in fiscal 2025 while cloud sales grew?
- `hq_5404d74f74b4456e9c72c7def4c64227` (AMZN): What factors drove the change in AWS segment operating income in 2024?
- `hq_84c831be7d16420aae81eb2d9f98c8af` (COST): How did the membership fee increase affect Costco's membership fee income in fiscal 2025?
- `hq_9e6c0c0dbb5941589c85ed5a923d944e` (NVDA): In fiscal 2025, how did NVIDIA describe the risk of U.S. export controls on sales to China?
- `hq_e9bf3b51fc6948de9eaa071fdbdb0e46` (CVX): As of its fiscal 2024 10-K, what was the status of Chevron's Hess acquisition and the Stabroek arbitration?
- `hq_efbdb0ea523543c699eddddde9b1e638` (XOM): How does ExxonMobil's 2024 10-K say greenhouse gas regulations could hurt its business?

The NVIDIA export-control question is both broad (7 gold chunks) and cross-year.

## Metric definitions fixed before results

G is the question's saved gold-ID set; T_k is the first k unique retrieved IDs. All metrics are macro-averaged over questions, without weighting by gold-set size.

- **Primary capped recall@k** = |G ∩ T_k| / min(k, |G|), for k=5 and 10. Chosen before seeing results (D027), so 6- and 7-gold questions can reach 1 at k=5.
- **Standard recall@k** = |G ∩ T_k| / |G|, for k=5 and 10.
- **Hit@k** = 1 if G ∩ T_k is nonempty, otherwise 0, for k=5 and 10.
- **MRR@30** = mean of 1/r, where r is the first gold rank within the top 30; 0 if there is no gold in those 30.

Every search uses saved filters exactly and k=30. The existing service reranks the entire hybrid top 30 before returning 30; rankings are not truncated to 5/10 beforehand. Keyword search can return fewer than 30 actual matches.
The reranked ID set equals the complete hybrid candidate ID set for every question; all available candidates were retained for the MRR@30 calculation.
The Apple FY2025 Q3 tariff question has only 15 eligible frozen chunks, verified by a read-only count; vector/hybrid/rerank return all 15. Every other hybrid and reranked pool contains 30 candidates. This reflects eligible-corpus size; there is no HNSW underfill.
Its 15-chunk eligible set makes the Apple tariff question easier than questions with larger eligible sets; it is not directly comparable in search difficulty.

## Pre-fix (keyword AND-semantics defect)

### Full set (n=30)

| Mode | Capped recall@5 | Capped recall@10 | Recall@5 | Recall@10 | Hit@5 | Hit@10 | MRR@30 |
|---|---:|---:|---:|---:|---:|---:|---:|
| vector | 0.6656 | 0.7556 | 0.6611 | 0.7556 | 0.8667 | 0.9000 | 0.6306 |
| keyword | 0.0333 | 0.0333 | 0.0333 | 0.0333 | 0.0333 | 0.0333 | 0.0333 |
| hybrid | 0.6656 | 0.7556 | 0.6611 | 0.7556 | 0.8667 | 0.9000 | 0.6306 |
| hybrid_rerank | 0.6600 | 0.7659 | 0.6556 | 0.7659 | 0.8667 | 0.9333 | 0.6012 |

### Cross-year (n=6)

| Mode | Capped recall@5 | Capped recall@10 | Recall@5 | Recall@10 | Hit@5 | Hit@10 | MRR@30 |
|---|---:|---:|---:|---:|---:|---:|---:|
| vector | 0.4167 | 0.5000 | 0.4167 | 0.5000 | 0.6667 | 0.6667 | 0.6806 |
| keyword | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| hybrid | 0.4167 | 0.5000 | 0.4167 | 0.5000 | 0.6667 | 0.6667 | 0.6806 |
| hybrid_rerank | 0.5000 | 0.6071 | 0.5000 | 0.6071 | 0.6667 | 0.8333 | 0.4630 |

### Period-filtered (n=24)

| Mode | Capped recall@5 | Capped recall@10 | Recall@5 | Recall@10 | Hit@5 | Hit@10 | MRR@30 |
|---|---:|---:|---:|---:|---:|---:|---:|
| vector | 0.7278 | 0.8194 | 0.7222 | 0.8194 | 0.9167 | 0.9583 | 0.6182 |
| keyword | 0.0417 | 0.0417 | 0.0417 | 0.0417 | 0.0417 | 0.0417 | 0.0417 |
| hybrid | 0.7278 | 0.8194 | 0.7222 | 0.8194 | 0.9167 | 0.9583 | 0.6182 |
| hybrid_rerank | 0.7000 | 0.8056 | 0.6944 | 0.8056 | 0.9167 | 0.9583 | 0.6357 |

## Post-fix full set (n=30)

| Mode | Capped recall@5 | Capped recall@10 | Recall@5 | Recall@10 | Hit@5 | Hit@10 | MRR@30 |
|---|---:|---:|---:|---:|---:|---:|---:|
| vector | 0.6656 | 0.7556 | 0.6611 | 0.7556 | 0.8667 | 0.9000 | 0.6306 |
| keyword | 0.5011 | 0.6325 | 0.5000 | 0.6325 | 0.6667 | 0.7667 | 0.5391 |
| hybrid | 0.6478 | 0.7603 | 0.6444 | 0.7603 | 0.8000 | 0.9000 | 0.6210 |
| hybrid_rerank | 0.6656 | 0.7714 | 0.6611 | 0.7714 | 0.8667 | 0.9333 | 0.5683 |

## Post-fix Cross-year subset (n=6)

| Mode | Capped recall@5 | Capped recall@10 | Recall@5 | Recall@10 | Hit@5 | Hit@10 | MRR@30 |
|---|---:|---:|---:|---:|---:|---:|---:|
| vector | 0.4167 | 0.5000 | 0.4167 | 0.5000 | 0.6667 | 0.6667 | 0.6806 |
| keyword | 0.3333 | 0.4405 | 0.3333 | 0.4405 | 0.5000 | 0.8333 | 0.5486 |
| hybrid | 0.3333 | 0.5238 | 0.3333 | 0.5238 | 0.5000 | 0.8333 | 0.5497 |
| hybrid_rerank | 0.5833 | 0.6071 | 0.5833 | 0.6071 | 0.8333 | 1.0000 | 0.4963 |

## Post-fix Period-filtered subset (n=24)

| Mode | Capped recall@5 | Capped recall@10 | Recall@5 | Recall@10 | Hit@5 | Hit@10 | MRR@30 |
|---|---:|---:|---:|---:|---:|---:|---:|
| vector | 0.7278 | 0.8194 | 0.7222 | 0.8194 | 0.9167 | 0.9583 | 0.6182 |
| keyword | 0.5431 | 0.6806 | 0.5417 | 0.6806 | 0.7083 | 0.7500 | 0.5368 |
| hybrid | 0.7264 | 0.8194 | 0.7222 | 0.8194 | 0.8750 | 0.9167 | 0.6389 |
| hybrid_rerank | 0.6861 | 0.8125 | 0.6806 | 0.8125 | 0.8750 | 0.9167 | 0.5863 |

## Retrieval cache

D026: 0 searches reused valid frozen-corpus caches; 120 were fresh runs (120 question/mode combinations total). Keys include exact question, saved filters, depth 30, mode, corpus and model versions. Per-run source and exact cache path are saved in retrieval.json.

### Keyword and fusion limitation

Keyword result-count distribution (hits: questions): {11: 1, 26: 1, 30: 28}. Vector and hybrid ID rankings were identical for 0/30 questions. The single correctness fix chosen before this rerun derives distinct English stemmed, stopword-filtered lexemes with to_tsvector, ORs the quoted lexemes, and ranks by unchanged ts_rank_cd. RRF remains 60. No alternatives or weights were tried. Cache implementation version is `retrieval-v2-keyword-or`; v1 keyword and fusion rankings cannot populate this run. The pre-fix tables remain above for comparison.

## Post-fix per-question first-gold ranks

`>30` means no gold in the returned top 30, including empty keyword results.

| ID | Short question | Ticker | Gold | vector | keyword | hybrid | hybrid_rerank |
|---|---|---|---:|---:|---:|---:|---:|
| hq_05c3197fe2084357b5c9ca0582b713f2 | What restructuring plan did P&G announce in fiscal 2025, and why did it start it? | PG | 1 | 3 | 1 | 2 | 1 |
| hq_19ea90a4eeb84991845ef0f0a3c4d316 | Why did Microsoft's cloud profit margins shrink in fiscal 2025 while cloud sales grew? | MSFT | 2 | 1 | >30 | 7 | 3 |
| hq_21f4a3b2e4e044129aee7a3fa547a79b | Why did Nike's sales fall in fiscal 2025? | NKE | 3 | 4 | 1 | 1 | 6 |
| hq_24a3e4ca8e144f708dc1df755db10222 | How exposed is Amazon to swings in currency exchange rates? | AMZN | 1 | 3 | 3 | 1 | 11 |
| hq_395269fb91c24e7aba645db4529fd483 | What liquidity risks does Bank of America describe related to deposit outflows? | BAC | 3 | 4 | >30 | 10 | 16 |
| hq_3bc57255183d4bdeabdba814d9c2f4a7 | What does Apple's value-at-risk model estimate for its foreign currency exposure? | AAPL | 1 | 1 | 1 | 1 | 1 |
| hq_3d27d3a6bc924f74ab4e2b4f2a914397 | Why did Pfizer's COVID vaccine and pill sales collapse in 2023? | PFE | 2 | 1 | >30 | 11 | 3 |
| hq_4d5d9efc06f34ddaa145f699ce2c2e4d | How could Meta's heavy spending on virtual and augmented reality go wrong? | META | 3 | 2 | 2 | 2 | 4 |
| hq_5404d74f74b4456e9c72c7def4c64227 | What factors drove the change in AWS segment operating income in 2024? | AMZN | 2 | 1 | 1 | 1 | 1 |
| hq_69c1bbc69ab243d29a5b85972d80828e | Why did Tesla make less profit on its cars in 2024? | TSLA | 2 | 1 | 15 | 1 | 1 |
| hq_74fd7fdce150403baad26a906223ba57 | What happens to Chevron if oil prices stay low for a long time? | CVX | 1 | 1 | 6 | 2 | 3 |
| hq_804ee5491dee4faaa512e49ecdfc1dd0 | Why did NVIDIA write off billions in chip inventory in early fiscal 2026? | NVDA | 3 | 2 | 3 | 2 | 3 |
| hq_84c831be7d16420aae81eb2d9f98c8af | How did the membership fee increase affect Costco's membership fee income in fiscal 2025? | COST | 1 | 1 | 1 | 1 | 3 |
| hq_8c86cd7564ba43deb72940f9fe800767 | How did Disney explain the improvement in Direct-to-Consumer operating income in fiscal 2024? | DIS | 1 | 19 | 3 | 4 | 2 |
| hq_9244d7ed50884988a8b0fcc969655431 | How did Alphabet explain the increase in capital expenditures for technical infrastructure in 2 | GOOGL | 2 | 1 | 3 | 2 | 1 |
| hq_9e6c0c0dbb5941589c85ed5a923d944e | In fiscal 2025, how did NVIDIA describe the risk of U.S. export controls on sales to China? | NVDA | 7 | 12 | 6 | 10 | 9 |
| hq_9f2123ab94e5409ba2375e444df03060 | How did buying Pioneer change Exxon's oil and gas production in 2024? | XOM | 1 | 2 | 1 | 1 | 1 |
| hq_af3da89ebdb6499f84b1103586988fcc | How does Coca-Cola price the concentrate it sells to its bottlers? | KO | 2 | 5 | 1 | 2 | 3 |
| hq_af3e0e0473af430b83dd4dc7e4bb1eef | Why does JPMorgan Chase say it cannot guarantee absolute security against cyberattacks? | JPM | 1 | 1 | 13 | 1 | 1 |
| hq_bbeba329b2724abcbbff1ea7869b3907 | What savings does Pfizer expect from its Cost Realignment Program? | PFE | 1 | 4 | 2 | 2 | 1 |
| hq_beb86dbbb9224fdcade1fe13bd690a88 | How much did eCommerce contribute to Walmart U.S. comparable sales in fiscal 2025? | WMT | 2 | 1 | 1 | 1 | 1 |
| hq_c65d4576350841669beea4c8dbea0a2b | How does Coke protect itself against currency and commodity price swings? | KO | 2 | 4 | 1 | 1 | 4 |
| hq_cdeefd822cd94dd98c915d26380f37ed | How did the 2024 hack of UnitedHealth's payment-processing unit affect the company? | UNH | 2 | 1 | 26 | 2 | 2 |
| hq_ce9809903d0b430eb90e3615603210f7 | How does Microsoft describe its Copilot and AI offerings in its business overview? | MSFT | 6 | 1 | 1 | 1 | 1 |
| hq_d2c0efbeda48446e88c1160406bc4452 | How were new tariffs hitting Apple's costs in mid-2025? | AAPL | 1 | 1 | 1 | 1 | 1 |
| hq_e3dfcc6ccd02482fb791dc34596565e7 | How would Bank of America's net interest income change if interest rates suddenly fell 100 basi | BAC | 1 | 4 | >30 | 17 | 4 |
| hq_e9bf3b51fc6948de9eaa071fdbdb0e46 | As of its fiscal 2024 10-K, what was the status of Chevron's Hess acquisition and the Stabroek  | CVX | 2 | 1 | 1 | 1 | 1 |
| hq_eead0b7f7e3f430589800660cafe8cb1 | Why were UnitedHealth's medical costs higher than expected in 2025? | UNH | 2 | 6 | 1 | 2 | 3 |
| hq_efbdb0ea523543c699eddddde9b1e638 | How does ExxonMobil's 2024 10-K say greenhouse gas regulations could hurt its business? | XOM | 2 | >30 | 8 | 18 | 5 |
| hq_f5d53183cdd04505b02cde17b599d44f | What risks does Johnson & Johnson describe from Medicare drug price negotiation under the Infla | JNJ | 1 | 1 | 5 | 3 | 3 |

## Post-fix reranker check

First-gold rank versus hybrid: **9 better / 10 worse / 11 same**.

Every first-gold demotion out of the top 5 or top 10:

| ID | Ticker | Hybrid rank | Reranked rank | Pushed outside top-k |
|---|---|---:|---:|---|
| hq_21f4a3b2e4e044129aee7a3fa547a79b | NKE | 1 | 6 | 5 |
| hq_24a3e4ca8e144f708dc1df755db10222 | AMZN | 1 | 11 | 5, 10 |
| hq_395269fb91c24e7aba645db4529fd483 | BAC | 10 | 16 | 10 |

hybrid: standard and capped recall@10 = 0.7603; hit@10 = 27/30.

hybrid_rerank: standard and capped recall@10 = 0.7714; hit@10 = 28/30.

The two recall@10 definitions coincide here because every gold set has at most 7 chunks.
Reranking does not hurt overall recall@10: 0.7603 → 0.7714. Period-filtered recall@10: 0.8194 → 0.8125; cross-year recall@10: 0.5238 → 0.6071. Overall capped recall@5: 0.6478 → 0.6656; MRR@30: 0.6210 → 0.5683.

### Labeling observations checked against finalized gold

- `hq_4d5d9efc06f34ddaa145f699ce2c2e4d`: How could Meta's heavy spending on virtual and augmented reality go wrong? First-gold ranks: vector=2, keyword=2, hybrid=2, hybrid_rerank=4.

| Gold chunk ID | vector | hybrid | hybrid_rerank |
|---|---:|---:|---:|
| chk_0b97a8cd228c326b9c607a304da1815ca0ec2fddbc1d4688195d8d7fb966956a | 9 | 5 | 21 |
| chk_87b9bca2642099efc9f738d55f7b37a9224206a5bee9514b3d0dc3ea1aa717a8 | 2 | 2 | 4 |
| chk_b138d59360fcd026b0c18cc8aa36370800519fc33126fc4166d8e0dd3c0b9e89 | 5 | 8 | 15 |

- `hq_69c1bbc69ab243d29a5b85972d80828e`: Why did Tesla make less profit on its cars in 2024? First-gold ranks: vector=1, keyword=15, hybrid=1, hybrid_rerank=1.

| Gold chunk ID | vector | hybrid | hybrid_rerank |
|---|---:|---:|---:|
| chk_3780654474ba25103c3a48988d4413ca798bdcfcbe677d43b621d00cf7c78342 | 8 | 20 | 8 |
| chk_e1c5011471b69b1fbbbac50d061704a2061fe97848c6519251d309756cd651fe | 1 | 1 | 1 |

- `hq_cdeefd822cd94dd98c915d26380f37ed`: How did the 2024 hack of UnitedHealth's payment-processing unit affect the company? First-gold ranks: vector=1, keyword=26, hybrid=2, hybrid_rerank=2.

| Gold chunk ID | vector | hybrid | hybrid_rerank |
|---|---:|---:|---:|
| chk_107a4587bb0392263e4b2ed314f470f6000009dd2310f00c56639b921167d843 | 1 | 2 | 2 |
| chk_8f45230248a924379567099be9fc991d896c95ee610d310826a32aa996592ef3 | 3 | 7 | 28 |

These tables use post-fix candidate pools; earlier labeling positions need not match. First-gold rank alone can hide losses of additional relevant passages, which the recall metrics capture. No new relevance labels were assigned.

### Paired comparisons

Wins compare per-question primary capped recall@10, as specified before results. A win means strictly more gold recovered within 10; ties include equal zero scores. n=30 is small; differences of a few questions are not conclusive.

| Mode A | Mode B | A wins | B wins | Ties |
|---|---|---:|---:|---:|
| vector | keyword | 9 | 7 | 14 |
| vector | hybrid | 4 | 6 | 20 |
| vector | hybrid_rerank | 5 | 8 | 17 |
| keyword | hybrid | 3 | 8 | 19 |
| keyword | hybrid_rerank | 3 | 8 | 19 |
| hybrid | hybrid_rerank | 6 | 6 | 18 |

## Known coverage gaps

Read-only inventory: all 20 companies, all 275 frozen filings, 730 expected item slots. The tables below list every item with fewer than 3 chunks, including missing items. First line is the first nonblank stored line, including a heading when present. Counts alone do not establish a parsing error. The full inventory and short-section texts are saved in retrieval.json for inspection.

### Annual items 1, 1A, 7, 7A and 8

| Ticker | FY | Accession | Item | Chunks | First line | Assessment |
|---|---:|---|---|---:|---|---|
| AAPL | 2023 | 0000320193-23-000106 | 7A | 2 | Item 7A. Quantitative and Qualitative Disclosures About Market Risk | Substantive short market-risk disclosure |
| AAPL | 2024 | 0000320193-24-000123 | 7A | 2 | Item 7A. Quantitative and Qualitative Disclosures About Market Risk | Substantive short market-risk disclosure |
| AAPL | 2025 | 0000320193-25-000079 | 7A | 2 | Item 7A. Quantitative and Qualitative Disclosures About Market Risk | Substantive short market-risk disclosure |
| BAC | 2023 | 0000070858-24-000122 | 7A | 1 | Item 7A. Quantitative and Qualitative Disclosures about Market Risk | Cross-reference to retained MD&A; not a stand-alone disclosure |
| BAC | 2024 | 0000070858-25-000139 | 7A | 1 | Item 7A. Quantitative and Qualitative Disclosures about Market Risk | Cross-reference to retained MD&A; not a stand-alone disclosure |
| BAC | 2025 | 0000070858-26-000157 | 7A | 1 | Item 7A. Quantitative and Qualitative Disclosures about Market Risk | Cross-reference to retained MD&A; not a stand-alone disclosure |
| CVX | 2023 | 0000093410-24-000013 | 7 | 1 | Item 7. Management’s Discussion and Analysis of Financial Condition and Results of Operations | Cross-reference stub; referenced financial section not retained |
| CVX | 2023 | 0000093410-24-000013 | 7A | 1 | Item 7A. Quantitative and Qualitative Disclosures About Market Risk | Cross-reference stub; referenced financial section not retained |
| CVX | 2023 | 0000093410-24-000013 | 8 | 1 | Item 8. Financial Statements and Supplementary Data | Cross-reference stub; referenced financial section not retained |
| CVX | 2024 | 0000093410-25-000009 | 7 | 1 | Item 7. Management’s Discussion and Analysis of Financial Condition and Results of Operations | Cross-reference stub; referenced financial section not retained |
| CVX | 2024 | 0000093410-25-000009 | 7A | 1 | Item 7A. Quantitative and Qualitative Disclosures About Market Risk | Cross-reference stub; referenced financial section not retained |
| CVX | 2024 | 0000093410-25-000009 | 8 | 1 | Item 8. Financial Statements and Supplementary Data | Cross-reference stub; referenced financial section not retained |
| CVX | 2025 | 0000093410-26-000078 | 7 | 1 | Item 7. Management’s Discussion and Analysis of Financial Condition and Results of Operations | Cross-reference stub; referenced financial section not retained |
| CVX | 2025 | 0000093410-26-000078 | 7A | 1 | Item 7A. Quantitative and Qualitative Disclosures About Market Risk | Cross-reference stub; referenced financial section not retained |
| CVX | 2025 | 0000093410-26-000078 | 8 | 1 | Item 8. Financial Statements and Supplementary Data | Cross-reference stub; referenced financial section not retained |
| DIS | 2023 | 0001744489-23-000216 | 8 | 1 | ITEM 8. Financial Statements and Supplementary Data | Cross-reference stub; referenced content outside this item |
| DIS | 2024 | 0001744489-24-000276 | 8 | 1 | ITEM 8. Financial Statements and Supplementary Data | Cross-reference stub; referenced content outside this item |
| DIS | 2025 | 0001744489-25-000155 | 8 | 1 | ITEM 8. Financial Statements and Supplementary Data | Cross-reference stub; referenced content outside this item |
| JNJ | 2023 | 0000200406-24-000013 | 7A | 1 | Item 7A. Quantitative and qualitative disclosures about market risk | Cross-reference to retained MD&A; not a stand-alone disclosure |
| JNJ | 2024 | 0000200406-25-000038 | 7A | 1 | Item 7A. Quantitative and qualitative disclosures about market risk | Cross-reference to retained MD&A; not a stand-alone disclosure |
| JNJ | 2025 | 0000200406-26-000016 | 7A | 1 | Item 7A. Quantitative and qualitative disclosures about market risk | Cross-reference to retained MD&A; not a stand-alone disclosure |
| JPM | 2023 | 0000019617-24-000225 | 7 | 1 | Item 7. Management’s Discussion and Analysis of Financial Condition and Results of Operations. | Cross-reference stub; referenced financial section not retained |
| JPM | 2023 | 0000019617-24-000225 | 7A | 1 | Item 7A. Quantitative and Qualitative Disclosures About Market Risk. | Cross-reference stub; referenced financial section not retained |
| JPM | 2023 | 0000019617-24-000225 | 8 | 1 | Item 8. Financial Statements and Supplementary Data. | Cross-reference stub; referenced financial section not retained |
| JPM | 2024 | 0000019617-25-000270 | 7 | 1 | Item 7. Management’s Discussion and Analysis of Financial Condition and Results of Operations. | Cross-reference stub; referenced financial section not retained |
| JPM | 2024 | 0000019617-25-000270 | 7A | 1 | Item 7A. Quantitative and Qualitative Disclosures About Market Risk. | Cross-reference stub; referenced financial section not retained |
| JPM | 2024 | 0000019617-25-000270 | 8 | 1 | Item 8. Financial Statements and Supplementary Data. | Cross-reference stub; referenced financial section not retained |
| JPM | 2025 | 0001628280-26-008131 | 7 | 1 | Item 7. Management’s Discussion and Analysis of Financial Condition and Results of Operations. | Cross-reference stub; referenced financial section not retained |
| JPM | 2025 | 0001628280-26-008131 | 7A | 1 | Item 7A. Quantitative and Qualitative Disclosures About Market Risk. | Cross-reference stub; referenced financial section not retained |
| JPM | 2025 | 0001628280-26-008131 | 8 | 1 | Item 8. Financial Statements and Supplementary Data. | Cross-reference stub; referenced financial section not retained |
| MSFT | 2024 | 0000950170-24-087843 | 7A | 2 | Item 7A | Substantive short market-risk disclosure |
| MSFT | 2025 | 0000950170-25-100235 | 7A | 2 | Item 7A | Substantive short market-risk disclosure |
| MSFT | 2026 | 0001193125-26-323660 | 7A | 2 | Item 7A | Substantive short market-risk disclosure |
| NVDA | 2024 | 0001045810-24-000029 | 7A | 2 | Item 7A. Quantitative and Qualitative Disclosures about Market Risk | Substantive short market-risk disclosure |
| NVDA | 2024 | 0001045810-24-000029 | 8 | 1 | Item 8. Financial Statements and Supplementary Data | Cross-reference stub; referenced content outside this item |
| NVDA | 2025 | 0001045810-25-000023 | 7A | 2 | Item 7A. Quantitative and Qualitative Disclosures about Market Risk | Substantive short market-risk disclosure |
| NVDA | 2025 | 0001045810-25-000023 | 8 | 1 | Item 8. Financial Statements and Supplementary Data | Cross-reference stub; referenced content outside this item |
| NVDA | 2026 | 0001045810-26-000021 | 8 | 1 | Item 8. Financial Statements and Supplementary Data | Cross-reference stub; referenced content outside this item |
| PFE | 2023 | 0000078003-24-000039 | 7A | 1 | ITEM 7A. \| QUANTITATIVE AND QUALITATIVE DISCLOSURES ABOUT MARKET RISK | Cross-reference to retained MD&A; not a stand-alone disclosure |
| PFE | 2024 | 0000078003-25-000054 | 7A | 1 | ITEM 7A. \| QUANTITATIVE AND QUALITATIVE DISCLOSURES ABOUT MARKET RISK | Cross-reference to retained MD&A; not a stand-alone disclosure |
| PFE | 2025 | 0000078003-26-000026 | 7A | 1 | ITEM 7A. \| QUANTITATIVE AND QUALITATIVE DISCLOSURES ABOUT MARKET RISK | Cross-reference to retained MD&A; not a stand-alone disclosure |
| PG | 2024 | 0000080424-24-000083 | 7A | 1 | Item 7A. Quantitative and Qualitative Disclosures About Market Risk. | Cross-reference to retained MD&A; not a stand-alone disclosure |
| PG | 2025 | 0000080424-25-000076 | 7A | 1 | Item 7A. Quantitative and Qualitative Disclosures About Market Risk. | Cross-reference to retained MD&A; not a stand-alone disclosure |
| PG | 2026 | 0000080424-26-000103 | 7A | 1 | Item 7A. Quantitative and Qualitative Disclosures About Market Risk. | Cross-reference to retained MD&A; not a stand-alone disclosure |
| TSLA | 2023 | 0001628280-24-002390 | 7A | 1 | ITEM 7A. QUANTITATIVE AND QUALITATIVE DISCLOSURES ABOUT MARKET RISK | Substantive short market-risk disclosure |
| TSLA | 2024 | 0001628280-25-003063 | 7A | 1 | ITEM 7A. QUANTITATIVE AND QUALITATIVE DISCLOSURES ABOUT MARKET RISK | Substantive short market-risk disclosure |
| TSLA | 2025 | 0001628280-26-003952 | 7A | 1 | ITEM 7A. QUANTITATIVE AND QUALITATIVE DISCLOSURES ABOUT MARKET RISK | Substantive short market-risk disclosure |
| XOM | 2023 | 0000034088-24-000018 | 7 | 1 | ITEM 7. MANAGEMENT'S DISCUSSION AND ANALYSIS OF FINANCIAL CONDITION AND RESULTS OF OPERATIONS | Cross-reference stub; referenced financial section not retained |
| XOM | 2023 | 0000034088-24-000018 | 7A | 1 | ITEM 7A. QUANTITATIVE AND QUALITATIVE DISCLOSURES ABOUT MARKET RISK | Cross-reference stub; referenced financial section not retained |
| XOM | 2023 | 0000034088-24-000018 | 8 | 1 | ITEM 8. FINANCIAL STATEMENTS AND SUPPLEMENTARY DATA \|  \| | Cross-reference stub; referenced financial section not retained |
| XOM | 2024 | 0000034088-25-000010 | 7 | 1 | ITEM 7. MANAGEMENT'S DISCUSSION AND ANALYSIS OF FINANCIAL CONDITION AND RESULTS OF OPERATIONS | Cross-reference stub; referenced financial section not retained |
| XOM | 2024 | 0000034088-25-000010 | 7A | 1 | ITEM 7A. QUANTITATIVE AND QUALITATIVE DISCLOSURES ABOUT MARKET RISK | Cross-reference stub; referenced financial section not retained |
| XOM | 2024 | 0000034088-25-000010 | 8 | 1 | ITEM 8. FINANCIAL STATEMENTS AND SUPPLEMENTARY DATA \|  \| | Cross-reference stub; referenced financial section not retained |
| XOM | 2025 | 0000034088-26-000045 | 7 | 1 | ITEM 7. MANAGEMENT'S DISCUSSION AND ANALYSIS OF FINANCIAL CONDITION AND RESULTS OF OPERATIONS | Cross-reference stub; referenced financial section not retained |
| XOM | 2025 | 0000034088-26-000045 | 7A | 1 | ITEM 7A. QUANTITATIVE AND QUALITATIVE DISCLOSURES ABOUT MARKET RISK | Cross-reference stub; referenced financial section not retained |
| XOM | 2025 | 0000034088-26-000045 | 8 | 1 | ITEM 8. FINANCIAL STATEMENTS AND SUPPLEMENTARY DATA \|  \| | Cross-reference stub; referenced financial section not retained |
### Quarterly items P1-2 and P2-1A

| Ticker | FY | Accession | Item | Chunks | First line | Assessment |
|---|---:|---|---|---:|---|---|
| AAPL | 2023 | 0000320193-23-000006 | P2-1A | 1 | Item 1A. Risk Factors | Brief risk disclosure/reference; shortness alone is not a gap |
| AAPL | 2023 | 0000320193-23-000064 | P2-1A | 1 | Item 1A. Risk Factors | Brief risk disclosure/reference; shortness alone is not a gap |
| AAPL | 2023 | 0000320193-23-000077 | P2-1A | 1 | Item 1A. Risk Factors | Brief risk disclosure/reference; shortness alone is not a gap |
| AAPL | 2024 | 0000320193-24-000081 | P2-1A | 1 | Item 1A. Risk Factors | Brief risk disclosure/reference; shortness alone is not a gap |
| AAPL | 2025 | 0000320193-25-000073 | P2-1A | 1 | Item 1A. Risk Factors | Brief risk disclosure/reference; shortness alone is not a gap |
| AAPL | 2026 | 0000320193-26-000006 | P2-1A | 1 | Item 1A. Risk Factors | Brief risk disclosure/reference; shortness alone is not a gap |
| BAC | 2023 | 0000070858-23-000142 | P1-2 | 1 | Item 2. Management’s Discussion and Analysis of Financial Condition and Results of Operations \|  \| | TOC capture; substantive MD&A missing |
| BAC | 2023 | 0000070858-23-000142 | P2-1A | 1 | Item 1A. Risk Factors | Brief risk disclosure/reference; shortness alone is not a gap |
| BAC | 2023 | 0000070858-23-000176 | P1-2 | 1 | Item 2. Management’s Discussion and Analysis of Financial Condition and Results of Operations \|  \| | TOC capture; substantive MD&A missing |
| BAC | 2023 | 0000070858-23-000176 | P2-1A | 1 | Item 1A. Risk Factors | Brief risk disclosure/reference; shortness alone is not a gap |
| BAC | 2023 | 0000070858-23-000272 | P1-2 | 1 | Item 2. Management’s Discussion and Analysis of Financial Condition and Results of Operations \|  \| | TOC capture; substantive MD&A missing |
| BAC | 2023 | 0000070858-23-000272 | P2-1A | 1 | Item 1A. Risk Factors | Brief risk disclosure/reference; shortness alone is not a gap |
| BAC | 2024 | 0000070858-24-000156 | P1-2 | 1 | Item 2. Management’s Discussion and Analysis of Financial Condition and Results of Operations \|  \| | TOC capture; substantive MD&A missing |
| BAC | 2024 | 0000070858-24-000156 | P2-1A | 1 | Item 1A. Risk Factors | Brief risk disclosure/reference; shortness alone is not a gap |
| BAC | 2024 | 0000070858-24-000208 | P1-2 | 1 | Item 2. Management’s Discussion and Analysis of Financial Condition and Results of Operations \|  \| | TOC capture; substantive MD&A missing |
| BAC | 2024 | 0000070858-24-000208 | P2-1A | 1 | Item 1A. Risk Factors | Brief risk disclosure/reference; shortness alone is not a gap |
| BAC | 2024 | 0000070858-24-000280 | P1-2 | 1 | Item 2. Management’s Discussion and Analysis of Financial Condition and Results of Operations \|  \| | TOC capture; substantive MD&A missing |
| BAC | 2024 | 0000070858-24-000280 | P2-1A | 1 | Item 1A. Risk Factors | Brief risk disclosure/reference; shortness alone is not a gap |
| BAC | 2025 | 0000070858-25-000200 | P1-2 | 1 | Item 2. Management’s Discussion and Analysis of Financial Condition and Results of Operations \|  \| | TOC capture; substantive MD&A missing |
| BAC | 2025 | 0000070858-25-000200 | P2-1A | 1 | Item 1A. Risk Factors | Brief risk disclosure/reference; shortness alone is not a gap |
| BAC | 2025 | 0000070858-25-000268 | P1-2 | 1 | Item 2. Management’s Discussion and Analysis of Financial Condition and Results of Operations \|  \| | TOC capture; substantive MD&A missing |
| BAC | 2025 | 0000070858-25-000268 | P2-1A | 1 | Item 1A. Risk Factors | Brief risk disclosure/reference; shortness alone is not a gap |
| BAC | 2025 | 0000070858-25-000405 | P1-2 | 1 | Item 2. Management’s Discussion and Analysis of Financial Condition and Results of Operations \|  \| | TOC capture; substantive MD&A missing |
| BAC | 2025 | 0000070858-25-000405 | P2-1A | 1 | Item 1A. Risk Factors | Brief risk disclosure/reference; shortness alone is not a gap |
| BAC | 2026 | 0000070858-26-000249 | P1-2 | 1 | Item 2. Management’s Discussion and Analysis of Financial Condition and Results of Operations \|  \| | TOC capture; substantive MD&A missing |
| BAC | 2026 | 0000070858-26-000249 | P2-1A | 1 | Item 1A. Risk Factors | Brief risk disclosure/reference; shortness alone is not a gap |
| BAC | 2026 | 0000070858-26-000394 | P1-2 | 1 | Item 2. Management’s Discussion and Analysis of Financial Condition and Results of Operations \|  \| | TOC capture; substantive MD&A missing |
| BAC | 2026 | 0000070858-26-000394 | P2-1A | 1 | Item 1A. Risk Factors | Brief risk disclosure/reference; shortness alone is not a gap |
| COST | 2024 | 0000909832-23-000065 | P2-1A | 1 | Item 1A—Risk Factors | Brief risk disclosure/reference; shortness alone is not a gap |
| COST | 2024 | 0000909832-24-000017 | P2-1A | 1 | Item 1A—Risk Factors | Brief risk disclosure/reference; shortness alone is not a gap |
| COST | 2024 | 0000909832-24-000029 | P2-1A | 1 | Item 1A—Risk Factors | Brief risk disclosure/reference; shortness alone is not a gap |
| COST | 2025 | 0000909832-24-000079 | P2-1A | 1 | Item 1A—Risk Factors | Brief risk disclosure/reference; shortness alone is not a gap |
| COST | 2025 | 0000909832-25-000015 | P2-1A | 1 | Item 1A—Risk Factors | Brief risk disclosure/reference; shortness alone is not a gap |
| COST | 2025 | 0000909832-25-000033 | P2-1A | 1 | Item 1A—Risk Factors | Brief risk disclosure/reference; shortness alone is not a gap |
| COST | 2026 | 0000909832-25-000169 | P2-1A | 1 | Item 1A—Risk Factors | Brief risk disclosure/reference; shortness alone is not a gap |
| COST | 2026 | 0000909832-26-000029 | P2-1A | 1 | Item 1A—Risk Factors | Brief risk disclosure/reference; shortness alone is not a gap |
| COST | 2026 | 0000909832-26-000051 | P2-1A | 1 | Item 1A—Risk Factors | Brief risk disclosure/reference; shortness alone is not a gap |
| CVX | 2023 | 0000093410-23-000066 | P2-1A | 1 | Item 1A. Risk Factors | Brief risk disclosure/reference; shortness alone is not a gap |
| CVX | 2023 | 0000093410-23-000079 | P2-1A | 2 | Item 1A. Risk Factors | Brief risk update/cross-reference; substantive text present |
| CVX | 2023 | 0000093410-23-000088 | P2-1A | 2 | Item 1A. Risk Factors | Brief risk update/cross-reference; substantive text present |
| CVX | 2024 | 0000093410-24-000040 | P2-1A | 2 | Item 1A. Risk Factors | Brief risk update/cross-reference; substantive text present |
| CVX | 2025 | 0000093410-25-000062 | P2-1A | 1 | Item 1A. Risk Factors | Brief risk disclosure/reference; shortness alone is not a gap |
| CVX | 2025 | 0000093410-25-000108 | P2-1A | 1 | Item 1A. Risk Factors | Brief risk disclosure/reference; shortness alone is not a gap |
| CVX | 2026 | 0000093410-26-000113 | P2-1A | 1 | Item 1A. Risk Factors | Brief risk disclosure/reference; shortness alone is not a gap |
| CVX | 2026 | 0000093410-26-000167 | P2-1A | 1 | Item 1A. Risk Factors | Brief risk disclosure/reference; shortness alone is not a gap |
| DIS | 2024 | 0001744489-24-000232 | P2-1A | 2 | ITEM 1A. Risk Factors | Brief risk update/cross-reference; substantive text present |
| DIS | 2025 | 0001744489-25-000067 | P2-1A | 1 | ITEM 1A. Risk Factors | Brief risk disclosure/reference; shortness alone is not a gap |
| GOOGL | 2023 | 0001652044-23-000045 | P2-1A | 1 | ITEM 1A. RISK FACTORS | Brief risk disclosure/reference; shortness alone is not a gap |
| GOOGL | 2023 | 0001652044-23-000070 | P2-1A | 1 | ITEM 1A. RISK FACTORS | Brief risk disclosure/reference; shortness alone is not a gap |
| GOOGL | 2023 | 0001652044-23-000094 | P2-1A | 1 | ITEM 1A. RISK FACTORS | Brief risk disclosure/reference; shortness alone is not a gap |
| GOOGL | 2024 | 0001652044-24-000079 | P2-1A | 2 | ITEM 1A. RISK FACTORS | Brief risk update/cross-reference; substantive text present |
| GOOGL | 2025 | 0001652044-25-000043 | P2-1A | 1 | ITEM 1A. RISK FACTORS | Brief risk disclosure/reference; shortness alone is not a gap |
| GOOGL | 2025 | 0001652044-25-000062 | P2-1A | 1 | ITEM 1A. RISK FACTORS | Brief risk disclosure/reference; shortness alone is not a gap |
| GOOGL | 2025 | 0001652044-25-000091 | P2-1A | 1 | ITEM 1A. RISK FACTORS | Brief risk disclosure/reference; shortness alone is not a gap |
| JNJ | 2023 | 0000200406-23-000056 | P2-1A | 0 | [missing] | Absent in cached source: annual risk reference only; see source audit |
| JNJ | 2023 | 0000200406-23-000082 | P2-1A | 0 | [missing] | Absent in cached source: annual risk reference only; see source audit |
| JNJ | 2023 | 0000200406-23-000102 | P2-1A | 0 | [missing] | Absent in cached source: annual risk reference only; see source audit |
| JNJ | 2024 | 0000200406-24-000049 | P2-1A | 0 | [missing] | Absent in cached source: annual risk reference only; see source audit |
| JNJ | 2024 | 0000200406-24-000075 | P2-1A | 0 | [missing] | Absent in cached source: annual risk reference only; see source audit |
| JNJ | 2024 | 0000200406-24-000096 | P2-1A | 0 | [missing] | Absent in cached source: annual risk reference only; see source audit |
| JNJ | 2025 | 0000200406-25-000119 | P2-1A | 0 | [missing] | Absent in cached source: annual risk reference only; see source audit |
| JNJ | 2025 | 0000200406-25-000178 | P2-1A | 0 | [missing] | Absent in cached source: annual risk reference only; see source audit |
| JNJ | 2025 | 0000200406-25-000209 | P2-1A | 0 | [missing] | Absent in cached source: annual risk reference only; see source audit |
| JNJ | 2026 | 0000200406-26-000087 | P2-1A | 0 | [missing] | Absent in cached source: annual risk reference only; see source audit |
| JNJ | 2026 | 0000200406-26-000153 | P2-1A | 0 | [missing] | Absent in cached source: annual risk reference only; see source audit |
| JPM | 2023 | 0000019617-23-000310 | P1-2 | 1 | Item 2. \| Management’s Discussion and Analysis of Financial Condition and Results of Operations. \| | TOC capture; substantive MD&A missing |
| JPM | 2023 | 0000019617-23-000310 | P2-1A | 2 | Item 1A. Risk Factors. | Brief risk update/cross-reference; substantive text present |
| JPM | 2023 | 0000019617-23-000432 | P1-2 | 1 | Item 2. \| Management’s Discussion and Analysis of Financial Condition and Results of Operations. \| | TOC capture; substantive MD&A missing |
| JPM | 2023 | 0000019617-23-000432 | P2-1A | 2 | Item 1A. Risk Factors. | Brief risk update/cross-reference; substantive text present |
| JPM | 2023 | 0000019617-23-000524 | P1-2 | 1 | Item 2. \| Management’s Discussion and Analysis of Financial Condition and Results of Operations. \| | TOC capture; substantive MD&A missing |
| JPM | 2023 | 0000019617-23-000524 | P2-1A | 2 | Item 1A. Risk Factors. | Brief risk update/cross-reference; substantive text present |
| JPM | 2024 | 0000019617-24-000326 | P1-2 | 1 | Item 2. \| Management’s Discussion and Analysis of Financial Condition and Results of Operations. \| | TOC capture; substantive MD&A missing |
| JPM | 2024 | 0000019617-24-000326 | P2-1A | 1 | Item 1A. Risk Factors. | Brief risk disclosure/reference; shortness alone is not a gap |
| JPM | 2024 | 0000019617-24-000453 | P1-2 | 1 | Item 2. \| Management’s Discussion and Analysis of Financial Condition and Results of Operations. \| | TOC capture; substantive MD&A missing |
| JPM | 2024 | 0000019617-24-000453 | P2-1A | 1 | Item 1A. Risk Factors. | Brief risk disclosure/reference; shortness alone is not a gap |
| JPM | 2024 | 0000019617-24-000611 | P1-2 | 1 | Item 2. \| Management’s Discussion and Analysis of Financial Condition and Results of Operations. \| | TOC capture; substantive MD&A missing |
| JPM | 2024 | 0000019617-24-000611 | P2-1A | 1 | Item 1A. Risk Factors. | Brief risk disclosure/reference; shortness alone is not a gap |
| JPM | 2025 | 0000019617-25-000421 | P1-2 | 1 | \|  \| Page | TOC capture; substantive MD&A missing |
| JPM | 2025 | 0000019617-25-000421 | P2-1A | 1 | Item 1A. Risk Factors. | Brief risk disclosure/reference; shortness alone is not a gap |
| JPM | 2025 | 0000019617-25-000615 | P1-2 | 1 | \|  \| Page | TOC capture; substantive MD&A missing |
| JPM | 2025 | 0000019617-25-000615 | P2-1A | 1 | Item 1A. Risk Factors. | Brief risk disclosure/reference; shortness alone is not a gap |
| JPM | 2025 | 0001628280-25-048859 | P1-2 | 1 | \|  \| Page | TOC capture; substantive MD&A missing |
| JPM | 2025 | 0001628280-25-048859 | P2-1A | 1 | Item 1A. Risk Factors. | Brief risk disclosure/reference; shortness alone is not a gap |
| JPM | 2026 | 0001628280-26-029344 | P1-2 | 1 | \|  \| Page | TOC capture; substantive MD&A missing |
| JPM | 2026 | 0001628280-26-029344 | P2-1A | 1 | Item 1A. Risk Factors. | Brief risk disclosure/reference; shortness alone is not a gap |
| JPM | 2026 | 0001628280-26-054343 | P1-2 | 1 | \|  \| Page | TOC capture; substantive MD&A missing |
| JPM | 2026 | 0001628280-26-054343 | P2-1A | 1 | Item 1A. Risk Factors. | Brief risk disclosure/reference; shortness alone is not a gap |
| KO | 2023 | 0000021344-23-000024 | P2-1A | 1 | Item 1A. Risk Factors | Brief risk disclosure/reference; shortness alone is not a gap |
| KO | 2023 | 0000021344-23-000048 | P2-1A | 1 | Item 1A. Risk Factors | Brief risk disclosure/reference; shortness alone is not a gap |
| KO | 2023 | 0000021344-23-000060 | P2-1A | 1 | Item 1A. Risk Factors | Brief risk disclosure/reference; shortness alone is not a gap |
| KO | 2024 | 0000021344-24-000017 | P2-1A | 1 | Item 1A. Risk Factors | Brief risk disclosure/reference; shortness alone is not a gap |
| KO | 2024 | 0000021344-24-000044 | P2-1A | 1 | Item 1A. Risk Factors | Brief risk disclosure/reference; shortness alone is not a gap |
| KO | 2024 | 0000021344-24-000060 | P2-1A | 1 | Item 1A. Risk Factors | Brief risk disclosure/reference; shortness alone is not a gap |
| KO | 2025 | 0000021344-25-000029 | P2-1A | 1 | Item 1A. Risk Factors | Brief risk disclosure/reference; shortness alone is not a gap |
| KO | 2025 | 0000021344-25-000061 | P2-1A | 1 | Item 1A. Risk Factors | Brief risk disclosure/reference; shortness alone is not a gap |
| KO | 2025 | 0001628280-25-046054 | P2-1A | 1 | Item 1A. Risk Factors | Brief risk disclosure/reference; shortness alone is not a gap |
| KO | 2026 | 0001628280-26-028802 | P2-1A | 1 | Item 1A. Risk Factors | Brief risk disclosure/reference; shortness alone is not a gap |
| KO | 2026 | 0001628280-26-050503 | P2-1A | 1 | Item 1A. Risk Factors | Brief risk disclosure/reference; shortness alone is not a gap |
| NKE | 2024 | 0000320187-23-000052 | P2-1A | 1 | ITEM 1A. RISK FACTORS | Brief risk disclosure/reference; shortness alone is not a gap |
| NKE | 2024 | 0000320187-24-000004 | P2-1A | 1 | ITEM 1A. RISK FACTORS | Brief risk disclosure/reference; shortness alone is not a gap |
| NKE | 2024 | 0000320187-24-000019 | P2-1A | 1 | ITEM 1A. RISK FACTORS | Brief risk disclosure/reference; shortness alone is not a gap |
| NKE | 2025 | 0000320187-24-000065 | P2-1A | 1 | ITEM 1A. RISK FACTORS | Brief risk disclosure/reference; shortness alone is not a gap |
| NKE | 2025 | 0000320187-25-000004 | P2-1A | 1 | ITEM 1A. RISK FACTORS | Brief risk disclosure/reference; shortness alone is not a gap |
| NKE | 2025 | 0000320187-25-000016 | P2-1A | 1 | ITEM 1A. RISK FACTORS | Brief risk disclosure/reference; shortness alone is not a gap |
| NKE | 2026 | 0000320187-25-000097 | P2-1A | 1 | ITEM 1A. RISK FACTORS | Brief risk disclosure/reference; shortness alone is not a gap |
| NKE | 2026 | 0000320187-25-000151 | P2-1A | 1 | ITEM 1A. RISK FACTORS | Brief risk disclosure/reference; shortness alone is not a gap |
| NKE | 2026 | 0000320187-26-000037 | P2-1A | 1 | ITEM 1A. RISK FACTORS | Brief risk disclosure/reference; shortness alone is not a gap |
| NKE | 2027 | 0000320187-26-000193 | P2-1A | 1 | ITEM 1A. RISK FACTORS | Brief risk disclosure/reference; shortness alone is not a gap |
| PFE | 2024 | 0000078003-24-000107 | P2-1A | 1 | ITEM 1A. RISK FACTORS | Brief risk disclosure/reference; shortness alone is not a gap |
| PFE | 2024 | 0000078003-24-000166 | P2-1A | 1 | ITEM 1A. RISK FACTORS | Brief risk disclosure/reference; shortness alone is not a gap |
| PFE | 2024 | 0000078003-24-000191 | P2-1A | 1 | ITEM 1A. RISK FACTORS | Brief risk disclosure/reference; shortness alone is not a gap |
| PFE | 2025 | 0000078003-25-000114 | P2-1A | 1 | ITEM 1A. RISK FACTORS | Brief risk disclosure/reference; shortness alone is not a gap |
| PFE | 2025 | 0000078003-25-000138 | P2-1A | 1 | ITEM 1A. RISK FACTORS | Brief risk disclosure/reference; shortness alone is not a gap |
| PFE | 2025 | 0000078003-25-000150 | P2-1A | 1 | ITEM 1A. RISK FACTORS | Brief risk disclosure/reference; shortness alone is not a gap |
| PFE | 2026 | 0000078003-26-000054 | P2-1A | 1 | ITEM 1A. RISK FACTORS | Brief risk disclosure/reference; shortness alone is not a gap |
| PFE | 2026 | 0000078003-26-000095 | P2-1A | 1 | ITEM 1A. RISK FACTORS | Brief risk disclosure/reference; shortness alone is not a gap |
| PG | 2024 | 0000080424-23-000103 | P2-1A | 1 | Item 1A. \| Risk Factors | Brief risk disclosure/reference; shortness alone is not a gap |
| PG | 2024 | 0000080424-24-000018 | P2-1A | 1 | Item 1A. \| Risk Factors | Brief risk disclosure/reference; shortness alone is not a gap |
| PG | 2024 | 0000080424-24-000051 | P2-1A | 1 | Item 1A. \| Risk Factors | Brief risk disclosure/reference; shortness alone is not a gap |
| PG | 2025 | 0000080424-24-000113 | P2-1A | 1 | Item 1A. \| Risk Factors | Brief risk disclosure/reference; shortness alone is not a gap |
| PG | 2025 | 0000080424-25-000013 | P2-1A | 1 | Item 1A. \| Risk Factors | Brief risk disclosure/reference; shortness alone is not a gap |
| PG | 2025 | 0000080424-25-000037 | P2-1A | 1 | Item 1A. \| Risk Factors | Brief risk disclosure/reference; shortness alone is not a gap |
| PG | 2026 | 0000080424-25-000245 | P2-1A | 1 | Item 1A. \| Risk Factors | Brief risk disclosure/reference; shortness alone is not a gap |
| PG | 2026 | 0000080424-26-000011 | P2-1A | 1 | Item 1A. \| Risk Factors | Brief risk disclosure/reference; shortness alone is not a gap |
| PG | 2026 | 0000080424-26-000060 | P2-1A | 1 | Item 1A. \| Risk Factors | Brief risk disclosure/reference; shortness alone is not a gap |
| TSLA | 2023 | 0000950170-23-013890 | P2-1A | 1 | ITEM 1A. RISK FACTORS | Brief risk disclosure/reference; shortness alone is not a gap |
| TSLA | 2023 | 0000950170-23-033872 | P2-1A | 1 | ITEM 1A. RISK FACTORS | Brief risk disclosure/reference; shortness alone is not a gap |
| TSLA | 2023 | 0001628280-23-034847 | P2-1A | 1 | ITEM 1A. RISK FACTORS | Brief risk disclosure/reference; shortness alone is not a gap |
| TSLA | 2024 | 0001628280-24-017503 | P2-1A | 1 | ITEM 1A. RISK FACTORS | Brief risk disclosure/reference; shortness alone is not a gap |
| TSLA | 2024 | 0001628280-24-032662 | P2-1A | 1 | ITEM 1A. RISK FACTORS | Brief risk disclosure/reference; shortness alone is not a gap |
| TSLA | 2024 | 0001628280-24-043486 | P2-1A | 1 | ITEM 1A. RISK FACTORS | Brief risk disclosure/reference; shortness alone is not a gap |
| TSLA | 2025 | 0001628280-25-035806 | P2-1A | 2 | ITEM 1A. RISK FACTORS | Brief risk update/cross-reference; substantive text present |
| TSLA | 2025 | 0001628280-25-045968 | P2-1A | 1 | ITEM 1A. RISK FACTORS | Brief risk disclosure/reference; shortness alone is not a gap |
| TSLA | 2026 | 0001628280-26-026673 | P2-1A | 1 | ITEM 1A. RISK FACTORS | Brief risk disclosure/reference; shortness alone is not a gap |
| TSLA | 2026 | 0001628280-26-049270 | P2-1A | 1 | ITEM 1A. RISK FACTORS | Brief risk disclosure/reference; shortness alone is not a gap |
| UNH | 2023 | 0000731766-23-000029 | P2-1A | 1 | ITEM 1A. RISK FACTORS | Brief risk disclosure/reference; shortness alone is not a gap |
| UNH | 2023 | 0000731766-23-000053 | P2-1A | 1 | ITEM 1A. RISK FACTORS | Brief risk disclosure/reference; shortness alone is not a gap |
| UNH | 2023 | 0000731766-23-000064 | P2-1A | 1 | ITEM 1A. RISK FACTORS | Brief risk disclosure/reference; shortness alone is not a gap |
| UNH | 2024 | 0000731766-24-000155 | P2-1A | 1 | ITEM 1A. RISK FACTORS | Brief risk disclosure/reference; shortness alone is not a gap |
| UNH | 2024 | 0000731766-24-000262 | P2-1A | 1 | ITEM 1A. RISK FACTORS | Brief risk disclosure/reference; shortness alone is not a gap |
| UNH | 2024 | 0000731766-24-000323 | P2-1A | 1 | ITEM 1A. RISK FACTORS | Brief risk disclosure/reference; shortness alone is not a gap |
| UNH | 2025 | 0000731766-25-000131 | P2-1A | 1 | ITEM 1A. RISK FACTORS | Brief risk disclosure/reference; shortness alone is not a gap |
| UNH | 2025 | 0000731766-25-000236 | P2-1A | 1 | ITEM 1A. RISK FACTORS | Brief risk disclosure/reference; shortness alone is not a gap |
| UNH | 2025 | 0000731766-25-000305 | P2-1A | 1 | ITEM 1A. RISK FACTORS | Brief risk disclosure/reference; shortness alone is not a gap |
| UNH | 2026 | 0000731766-26-000127 | P2-1A | 1 | ITEM 1A. RISK FACTORS | Brief risk disclosure/reference; shortness alone is not a gap |
| UNH | 2026 | 0000731766-26-000197 | P2-1A | 1 | ITEM 1A. RISK FACTORS | Brief risk disclosure/reference; shortness alone is not a gap |
| WMT | 2024 | 0000104169-23-000052 | P2-1A | 1 | Item 1A. Risk Factors | Brief risk disclosure/reference; shortness alone is not a gap |
| WMT | 2024 | 0000104169-23-000097 | P2-1A | 1 | Item 1A. Risk Factors | Brief risk disclosure/reference; shortness alone is not a gap |
| WMT | 2024 | 0000104169-23-000132 | P2-1A | 1 | Item 1A. Risk Factors | Brief risk disclosure/reference; shortness alone is not a gap |
| WMT | 2025 | 0000104169-24-000105 | P2-1A | 1 | Item 1A. Risk Factors | Brief risk disclosure/reference; shortness alone is not a gap |
| WMT | 2025 | 0000104169-24-000141 | P2-1A | 1 | Item 1A. Risk Factors | Brief risk disclosure/reference; shortness alone is not a gap |
| WMT | 2025 | 0000104169-24-000178 | P2-1A | 1 | Item 1A. Risk Factors | Brief risk disclosure/reference; shortness alone is not a gap |
| WMT | 2026 | 0000104169-25-000090 | P2-1A | 1 | Item 1A. Risk Factors | Brief risk disclosure/reference; shortness alone is not a gap |
| WMT | 2026 | 0000104169-25-000137 | P2-1A | 1 | Item 1A. Risk Factors | Brief risk disclosure/reference; shortness alone is not a gap |
| WMT | 2026 | 0000104169-25-000191 | P2-1A | 1 | Item 1A. Risk Factors | Brief risk disclosure/reference; shortness alone is not a gap |
| WMT | 2027 | 0000104169-26-000102 | P2-1A | 1 | Item 1A. Risk Factors | Brief risk disclosure/reference; shortness alone is not a gap |
| WMT | 2027 | 0000104169-26-000154 | P2-1A | 1 | Item 1A. Risk Factors | Brief risk disclosure/reference; shortness alone is not a gap |
| XOM | 2023 | 0000034088-23-000030 | P2-1A | 0 | [missing] | Absent in cached source: annual risk reference only; see source audit |
| XOM | 2023 | 0000034088-23-000048 | P2-1A | 0 | [missing] | Absent in cached source: annual risk reference only; see source audit |
| XOM | 2023 | 0000034088-23-000056 | P2-1A | 0 | [missing] | Absent in cached source: annual risk reference only; see source audit |
| XOM | 2024 | 0000034088-24-000029 | P2-1A | 0 | [missing] | Absent in cached source: annual risk reference only; see source audit |
| XOM | 2024 | 0000034088-24-000050 | P2-1A | 0 | [missing] | Absent in cached source: annual risk reference only; see source audit |
| XOM | 2024 | 0000034088-24-000068 | P2-1A | 0 | [missing] | Absent in cached source: annual risk reference only; see source audit |
| XOM | 2025 | 0000034088-25-000024 | P2-1A | 0 | [missing] | Absent in cached source: annual risk reference only; see source audit |
| XOM | 2025 | 0000034088-25-000042 | P2-1A | 0 | [missing] | Absent in cached source: annual risk reference only; see source audit |
| XOM | 2025 | 0000034088-25-000061 | P2-1A | 0 | [missing] | Absent in cached source: annual risk reference only; see source audit |
| XOM | 2026 | 0000034088-26-000067 | P2-1A | 0 | [missing] | Absent in cached source: annual risk reference only; see source audit |
| XOM | 2026 | 0000034088-26-000093 | P2-1A | 0 | [missing] | Absent in cached source: annual risk reference only; see source audit |

KO FY2024 Item 7A: 4 chunks; not a short-section finding.

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


## Follow-up analyses

### Pre/post comparison

The pre-fix tables retain the keyword AND-semantics defect. The single OR fix was chosen in D031 before rerunning; it is not a selection among tuned variants.

| Mode | Change capped recall@5 | Change capped recall@10 | Change MRR@30 |
|---|---:|---:|---:|
| vector | +0.0000 | +0.0000 | +0.0000 |
| keyword | +0.4678 | +0.5992 | +0.5058 |
| hybrid | -0.0178 | +0.0048 | -0.0096 |
| hybrid_rerank | +0.0056 | +0.0056 | -0.0329 |

### Unjudged candidate exposure

The CLI did not record candidate-pool membership. Reconstruction reran its four-mode × depth-30 pooling definition with each record's exact saved filters, replaying all 120 valid pre-fix v1 caches (including keyword AND semantics), and checked the union against archived rankings. This is a reconstruction, not the complete history of earlier query edits, deeper pools or manual browsing. Known gold from browsing is judged even outside this reconstructed pool. Pool membership also does not prove every displayed candidate was explicitly judged; the CLI saved positives only.

Unjudged here = a retrieved ID outside that question's reconstructed union and outside its saved gold. The fraction divides by actual returned top-k slots. Overall rates below are slot-weighted (micro), not fractions of the whole corpus. Outside-pool counts are also retained in retrieval_analyses.json. No new relevance labels are assigned. Unjudged relevant chunks count as misses under the frozen gold scoring, so keyword and hybrid receive lower-bound relevance credit; the candidate pool was biased toward the vector family. Their recall scores are not formal numerical lower bounds on exhaustive recall: completing gold judgments also changes the unknown denominator. This does not establish which unjudged passages are relevant.

| Mode | Unjudged top-5 slots | Fraction | Unjudged top-10 slots | Fraction | Outside reconstructed pool @5 | Outside reconstructed pool @10 |
|---|---:|---:|---:|---:|---:|---:|
| vector | 0/150 | 0.0000 | 0/300 | 0.0000 | 0/150 (0.0000) | 0/300 (0.0000) |
| keyword | 51/150 | 0.3400 | 112/300 | 0.3733 | 52/150 (0.3467) | 114/300 (0.3800) |
| hybrid | 0/150 | 0.0000 | 11/300 | 0.0367 | 0/150 (0.0000) | 11/300 (0.0367) |
| hybrid_rerank | 10/150 | 0.0667 | 38/300 | 0.1267 | 11/150 (0.0733) | 39/300 (0.1300) |

Per question (unjudged/returned, fraction):

| ID | Mode | Unjudged top 5 | Unjudged top 10 | Outside pool top 5 | Outside pool top 10 |
|---|---|---:|---:|---:|---:|
| hq_05c3197fe2084357b5c9ca0582b713f2 | vector | 0/5 (0.0000) | 0/10 (0.0000) | 0/5 (0.0000) | 0/10 (0.0000) |
| hq_05c3197fe2084357b5c9ca0582b713f2 | keyword | 3/5 (0.6000) | 5/10 (0.5000) | 3/5 (0.6000) | 5/10 (0.5000) |
| hq_05c3197fe2084357b5c9ca0582b713f2 | hybrid | 0/5 (0.0000) | 0/10 (0.0000) | 0/5 (0.0000) | 0/10 (0.0000) |
| hq_05c3197fe2084357b5c9ca0582b713f2 | hybrid_rerank | 0/5 (0.0000) | 1/10 (0.1000) | 0/5 (0.0000) | 1/10 (0.1000) |
| hq_19ea90a4eeb84991845ef0f0a3c4d316 | vector | 0/5 (0.0000) | 0/10 (0.0000) | 0/5 (0.0000) | 0/10 (0.0000) |
| hq_19ea90a4eeb84991845ef0f0a3c4d316 | keyword | 5/5 (1.0000) | 10/10 (1.0000) | 5/5 (1.0000) | 10/10 (1.0000) |
| hq_19ea90a4eeb84991845ef0f0a3c4d316 | hybrid | 0/5 (0.0000) | 3/10 (0.3000) | 0/5 (0.0000) | 3/10 (0.3000) |
| hq_19ea90a4eeb84991845ef0f0a3c4d316 | hybrid_rerank | 0/5 (0.0000) | 1/10 (0.1000) | 0/5 (0.0000) | 1/10 (0.1000) |
| hq_21f4a3b2e4e044129aee7a3fa547a79b | vector | 0/5 (0.0000) | 0/10 (0.0000) | 0/5 (0.0000) | 0/10 (0.0000) |
| hq_21f4a3b2e4e044129aee7a3fa547a79b | keyword | 1/5 (0.2000) | 4/10 (0.4000) | 2/5 (0.4000) | 5/10 (0.5000) |
| hq_21f4a3b2e4e044129aee7a3fa547a79b | hybrid | 0/5 (0.0000) | 0/10 (0.0000) | 0/5 (0.0000) | 0/10 (0.0000) |
| hq_21f4a3b2e4e044129aee7a3fa547a79b | hybrid_rerank | 0/5 (0.0000) | 0/10 (0.0000) | 0/5 (0.0000) | 0/10 (0.0000) |
| hq_24a3e4ca8e144f708dc1df755db10222 | vector | 0/5 (0.0000) | 0/10 (0.0000) | 0/5 (0.0000) | 0/10 (0.0000) |
| hq_24a3e4ca8e144f708dc1df755db10222 | keyword | 1/5 (0.2000) | 2/10 (0.2000) | 1/5 (0.2000) | 2/10 (0.2000) |
| hq_24a3e4ca8e144f708dc1df755db10222 | hybrid | 0/5 (0.0000) | 0/10 (0.0000) | 0/5 (0.0000) | 0/10 (0.0000) |
| hq_24a3e4ca8e144f708dc1df755db10222 | hybrid_rerank | 0/5 (0.0000) | 2/10 (0.2000) | 0/5 (0.0000) | 2/10 (0.2000) |
| hq_395269fb91c24e7aba645db4529fd483 | vector | 0/5 (0.0000) | 0/10 (0.0000) | 0/5 (0.0000) | 0/10 (0.0000) |
| hq_395269fb91c24e7aba645db4529fd483 | keyword | 3/5 (0.6000) | 7/10 (0.7000) | 3/5 (0.6000) | 7/10 (0.7000) |
| hq_395269fb91c24e7aba645db4529fd483 | hybrid | 0/5 (0.0000) | 1/10 (0.1000) | 0/5 (0.0000) | 1/10 (0.1000) |
| hq_395269fb91c24e7aba645db4529fd483 | hybrid_rerank | 2/5 (0.4000) | 4/10 (0.4000) | 2/5 (0.4000) | 4/10 (0.4000) |
| hq_3bc57255183d4bdeabdba814d9c2f4a7 | vector | 0/5 (0.0000) | 0/10 (0.0000) | 0/5 (0.0000) | 0/10 (0.0000) |
| hq_3bc57255183d4bdeabdba814d9c2f4a7 | keyword | 1/5 (0.2000) | 4/10 (0.4000) | 1/5 (0.2000) | 4/10 (0.4000) |
| hq_3bc57255183d4bdeabdba814d9c2f4a7 | hybrid | 0/5 (0.0000) | 0/10 (0.0000) | 0/5 (0.0000) | 0/10 (0.0000) |
| hq_3bc57255183d4bdeabdba814d9c2f4a7 | hybrid_rerank | 0/5 (0.0000) | 1/10 (0.1000) | 0/5 (0.0000) | 1/10 (0.1000) |
| hq_3d27d3a6bc924f74ab4e2b4f2a914397 | vector | 0/5 (0.0000) | 0/10 (0.0000) | 0/5 (0.0000) | 0/10 (0.0000) |
| hq_3d27d3a6bc924f74ab4e2b4f2a914397 | keyword | 2/5 (0.4000) | 5/10 (0.5000) | 2/5 (0.4000) | 5/10 (0.5000) |
| hq_3d27d3a6bc924f74ab4e2b4f2a914397 | hybrid | 0/5 (0.0000) | 0/10 (0.0000) | 0/5 (0.0000) | 0/10 (0.0000) |
| hq_3d27d3a6bc924f74ab4e2b4f2a914397 | hybrid_rerank | 0/5 (0.0000) | 0/10 (0.0000) | 0/5 (0.0000) | 0/10 (0.0000) |
| hq_4d5d9efc06f34ddaa145f699ce2c2e4d | vector | 0/5 (0.0000) | 0/10 (0.0000) | 0/5 (0.0000) | 0/10 (0.0000) |
| hq_4d5d9efc06f34ddaa145f699ce2c2e4d | keyword | 3/5 (0.6000) | 6/10 (0.6000) | 3/5 (0.6000) | 6/10 (0.6000) |
| hq_4d5d9efc06f34ddaa145f699ce2c2e4d | hybrid | 0/5 (0.0000) | 0/10 (0.0000) | 0/5 (0.0000) | 0/10 (0.0000) |
| hq_4d5d9efc06f34ddaa145f699ce2c2e4d | hybrid_rerank | 2/5 (0.4000) | 4/10 (0.4000) | 2/5 (0.4000) | 4/10 (0.4000) |
| hq_5404d74f74b4456e9c72c7def4c64227 | vector | 0/5 (0.0000) | 0/10 (0.0000) | 0/5 (0.0000) | 0/10 (0.0000) |
| hq_5404d74f74b4456e9c72c7def4c64227 | keyword | 1/5 (0.2000) | 3/10 (0.3000) | 1/5 (0.2000) | 3/10 (0.3000) |
| hq_5404d74f74b4456e9c72c7def4c64227 | hybrid | 0/5 (0.0000) | 0/10 (0.0000) | 0/5 (0.0000) | 0/10 (0.0000) |
| hq_5404d74f74b4456e9c72c7def4c64227 | hybrid_rerank | 0/5 (0.0000) | 1/10 (0.1000) | 0/5 (0.0000) | 1/10 (0.1000) |
| hq_69c1bbc69ab243d29a5b85972d80828e | vector | 0/5 (0.0000) | 0/10 (0.0000) | 0/5 (0.0000) | 0/10 (0.0000) |
| hq_69c1bbc69ab243d29a5b85972d80828e | keyword | 4/5 (0.8000) | 7/10 (0.7000) | 4/5 (0.8000) | 7/10 (0.7000) |
| hq_69c1bbc69ab243d29a5b85972d80828e | hybrid | 0/5 (0.0000) | 1/10 (0.1000) | 0/5 (0.0000) | 1/10 (0.1000) |
| hq_69c1bbc69ab243d29a5b85972d80828e | hybrid_rerank | 0/5 (0.0000) | 3/10 (0.3000) | 0/5 (0.0000) | 3/10 (0.3000) |
| hq_74fd7fdce150403baad26a906223ba57 | vector | 0/5 (0.0000) | 0/10 (0.0000) | 0/5 (0.0000) | 0/10 (0.0000) |
| hq_74fd7fdce150403baad26a906223ba57 | keyword | 2/5 (0.4000) | 4/10 (0.4000) | 2/5 (0.4000) | 4/10 (0.4000) |
| hq_74fd7fdce150403baad26a906223ba57 | hybrid | 0/5 (0.0000) | 0/10 (0.0000) | 0/5 (0.0000) | 0/10 (0.0000) |
| hq_74fd7fdce150403baad26a906223ba57 | hybrid_rerank | 0/5 (0.0000) | 0/10 (0.0000) | 0/5 (0.0000) | 0/10 (0.0000) |
| hq_804ee5491dee4faaa512e49ecdfc1dd0 | vector | 0/5 (0.0000) | 0/10 (0.0000) | 0/5 (0.0000) | 0/10 (0.0000) |
| hq_804ee5491dee4faaa512e49ecdfc1dd0 | keyword | 0/5 (0.0000) | 1/10 (0.1000) | 0/5 (0.0000) | 1/10 (0.1000) |
| hq_804ee5491dee4faaa512e49ecdfc1dd0 | hybrid | 0/5 (0.0000) | 0/10 (0.0000) | 0/5 (0.0000) | 0/10 (0.0000) |
| hq_804ee5491dee4faaa512e49ecdfc1dd0 | hybrid_rerank | 0/5 (0.0000) | 0/10 (0.0000) | 0/5 (0.0000) | 0/10 (0.0000) |
| hq_84c831be7d16420aae81eb2d9f98c8af | vector | 0/5 (0.0000) | 0/10 (0.0000) | 0/5 (0.0000) | 0/10 (0.0000) |
| hq_84c831be7d16420aae81eb2d9f98c8af | keyword | 1/5 (0.2000) | 2/10 (0.2000) | 1/5 (0.2000) | 2/10 (0.2000) |
| hq_84c831be7d16420aae81eb2d9f98c8af | hybrid | 0/5 (0.0000) | 0/10 (0.0000) | 0/5 (0.0000) | 0/10 (0.0000) |
| hq_84c831be7d16420aae81eb2d9f98c8af | hybrid_rerank | 0/5 (0.0000) | 1/10 (0.1000) | 0/5 (0.0000) | 1/10 (0.1000) |
| hq_8c86cd7564ba43deb72940f9fe800767 | vector | 0/5 (0.0000) | 0/10 (0.0000) | 0/5 (0.0000) | 0/10 (0.0000) |
| hq_8c86cd7564ba43deb72940f9fe800767 | keyword | 3/5 (0.6000) | 4/10 (0.4000) | 3/5 (0.6000) | 4/10 (0.4000) |
| hq_8c86cd7564ba43deb72940f9fe800767 | hybrid | 0/5 (0.0000) | 0/10 (0.0000) | 0/5 (0.0000) | 0/10 (0.0000) |
| hq_8c86cd7564ba43deb72940f9fe800767 | hybrid_rerank | 0/5 (0.0000) | 1/10 (0.1000) | 0/5 (0.0000) | 1/10 (0.1000) |
| hq_9244d7ed50884988a8b0fcc969655431 | vector | 0/5 (0.0000) | 0/10 (0.0000) | 0/5 (0.0000) | 0/10 (0.0000) |
| hq_9244d7ed50884988a8b0fcc969655431 | keyword | 0/5 (0.0000) | 1/10 (0.1000) | 0/5 (0.0000) | 1/10 (0.1000) |
| hq_9244d7ed50884988a8b0fcc969655431 | hybrid | 0/5 (0.0000) | 0/10 (0.0000) | 0/5 (0.0000) | 0/10 (0.0000) |
| hq_9244d7ed50884988a8b0fcc969655431 | hybrid_rerank | 0/5 (0.0000) | 1/10 (0.1000) | 0/5 (0.0000) | 1/10 (0.1000) |
| hq_9e6c0c0dbb5941589c85ed5a923d944e | vector | 0/5 (0.0000) | 0/10 (0.0000) | 0/5 (0.0000) | 0/10 (0.0000) |
| hq_9e6c0c0dbb5941589c85ed5a923d944e | keyword | 0/5 (0.0000) | 0/10 (0.0000) | 0/5 (0.0000) | 0/10 (0.0000) |
| hq_9e6c0c0dbb5941589c85ed5a923d944e | hybrid | 0/5 (0.0000) | 0/10 (0.0000) | 0/5 (0.0000) | 0/10 (0.0000) |
| hq_9e6c0c0dbb5941589c85ed5a923d944e | hybrid_rerank | 0/5 (0.0000) | 0/10 (0.0000) | 0/5 (0.0000) | 0/10 (0.0000) |
| hq_9f2123ab94e5409ba2375e444df03060 | vector | 0/5 (0.0000) | 0/10 (0.0000) | 0/5 (0.0000) | 0/10 (0.0000) |
| hq_9f2123ab94e5409ba2375e444df03060 | keyword | 0/5 (0.0000) | 1/10 (0.1000) | 0/5 (0.0000) | 1/10 (0.1000) |
| hq_9f2123ab94e5409ba2375e444df03060 | hybrid | 0/5 (0.0000) | 0/10 (0.0000) | 0/5 (0.0000) | 0/10 (0.0000) |
| hq_9f2123ab94e5409ba2375e444df03060 | hybrid_rerank | 0/5 (0.0000) | 0/10 (0.0000) | 0/5 (0.0000) | 0/10 (0.0000) |
| hq_af3da89ebdb6499f84b1103586988fcc | vector | 0/5 (0.0000) | 0/10 (0.0000) | 0/5 (0.0000) | 0/10 (0.0000) |
| hq_af3da89ebdb6499f84b1103586988fcc | keyword | 2/5 (0.4000) | 3/10 (0.3000) | 2/5 (0.4000) | 3/10 (0.3000) |
| hq_af3da89ebdb6499f84b1103586988fcc | hybrid | 0/5 (0.0000) | 0/10 (0.0000) | 0/5 (0.0000) | 0/10 (0.0000) |
| hq_af3da89ebdb6499f84b1103586988fcc | hybrid_rerank | 0/5 (0.0000) | 1/10 (0.1000) | 0/5 (0.0000) | 1/10 (0.1000) |
| hq_af3e0e0473af430b83dd4dc7e4bb1eef | vector | 0/5 (0.0000) | 0/10 (0.0000) | 0/5 (0.0000) | 0/10 (0.0000) |
| hq_af3e0e0473af430b83dd4dc7e4bb1eef | keyword | 3/5 (0.6000) | 8/10 (0.8000) | 3/5 (0.6000) | 8/10 (0.8000) |
| hq_af3e0e0473af430b83dd4dc7e4bb1eef | hybrid | 0/5 (0.0000) | 1/10 (0.1000) | 0/5 (0.0000) | 1/10 (0.1000) |
| hq_af3e0e0473af430b83dd4dc7e4bb1eef | hybrid_rerank | 0/5 (0.0000) | 0/10 (0.0000) | 0/5 (0.0000) | 0/10 (0.0000) |
| hq_bbeba329b2724abcbbff1ea7869b3907 | vector | 0/5 (0.0000) | 0/10 (0.0000) | 0/5 (0.0000) | 0/10 (0.0000) |
| hq_bbeba329b2724abcbbff1ea7869b3907 | keyword | 0/5 (0.0000) | 2/10 (0.2000) | 0/5 (0.0000) | 2/10 (0.2000) |
| hq_bbeba329b2724abcbbff1ea7869b3907 | hybrid | 0/5 (0.0000) | 0/10 (0.0000) | 0/5 (0.0000) | 0/10 (0.0000) |
| hq_bbeba329b2724abcbbff1ea7869b3907 | hybrid_rerank | 0/5 (0.0000) | 0/10 (0.0000) | 0/5 (0.0000) | 0/10 (0.0000) |
| hq_beb86dbbb9224fdcade1fe13bd690a88 | vector | 0/5 (0.0000) | 0/10 (0.0000) | 0/5 (0.0000) | 0/10 (0.0000) |
| hq_beb86dbbb9224fdcade1fe13bd690a88 | keyword | 0/5 (0.0000) | 0/10 (0.0000) | 0/5 (0.0000) | 0/10 (0.0000) |
| hq_beb86dbbb9224fdcade1fe13bd690a88 | hybrid | 0/5 (0.0000) | 0/10 (0.0000) | 0/5 (0.0000) | 0/10 (0.0000) |
| hq_beb86dbbb9224fdcade1fe13bd690a88 | hybrid_rerank | 0/5 (0.0000) | 0/10 (0.0000) | 0/5 (0.0000) | 0/10 (0.0000) |
| hq_c65d4576350841669beea4c8dbea0a2b | vector | 0/5 (0.0000) | 0/10 (0.0000) | 0/5 (0.0000) | 0/10 (0.0000) |
| hq_c65d4576350841669beea4c8dbea0a2b | keyword | 4/5 (0.8000) | 7/10 (0.7000) | 4/5 (0.8000) | 7/10 (0.7000) |
| hq_c65d4576350841669beea4c8dbea0a2b | hybrid | 0/5 (0.0000) | 1/10 (0.1000) | 0/5 (0.0000) | 1/10 (0.1000) |
| hq_c65d4576350841669beea4c8dbea0a2b | hybrid_rerank | 2/5 (0.4000) | 2/10 (0.2000) | 2/5 (0.4000) | 2/10 (0.2000) |
| hq_cdeefd822cd94dd98c915d26380f37ed | vector | 0/5 (0.0000) | 0/10 (0.0000) | 0/5 (0.0000) | 0/10 (0.0000) |
| hq_cdeefd822cd94dd98c915d26380f37ed | keyword | 4/5 (0.8000) | 9/10 (0.9000) | 4/5 (0.8000) | 9/10 (0.9000) |
| hq_cdeefd822cd94dd98c915d26380f37ed | hybrid | 0/5 (0.0000) | 3/10 (0.3000) | 0/5 (0.0000) | 3/10 (0.3000) |
| hq_cdeefd822cd94dd98c915d26380f37ed | hybrid_rerank | 1/5 (0.2000) | 6/10 (0.6000) | 1/5 (0.2000) | 6/10 (0.6000) |
| hq_ce9809903d0b430eb90e3615603210f7 | vector | 0/5 (0.0000) | 0/10 (0.0000) | 0/5 (0.0000) | 0/10 (0.0000) |
| hq_ce9809903d0b430eb90e3615603210f7 | keyword | 1/5 (0.2000) | 1/10 (0.1000) | 1/5 (0.2000) | 1/10 (0.1000) |
| hq_ce9809903d0b430eb90e3615603210f7 | hybrid | 0/5 (0.0000) | 0/10 (0.0000) | 0/5 (0.0000) | 0/10 (0.0000) |
| hq_ce9809903d0b430eb90e3615603210f7 | hybrid_rerank | 0/5 (0.0000) | 0/10 (0.0000) | 0/5 (0.0000) | 0/10 (0.0000) |
| hq_d2c0efbeda48446e88c1160406bc4452 | vector | 0/5 (0.0000) | 0/10 (0.0000) | 0/5 (0.0000) | 0/10 (0.0000) |
| hq_d2c0efbeda48446e88c1160406bc4452 | keyword | 0/5 (0.0000) | 0/10 (0.0000) | 0/5 (0.0000) | 0/10 (0.0000) |
| hq_d2c0efbeda48446e88c1160406bc4452 | hybrid | 0/5 (0.0000) | 0/10 (0.0000) | 0/5 (0.0000) | 0/10 (0.0000) |
| hq_d2c0efbeda48446e88c1160406bc4452 | hybrid_rerank | 0/5 (0.0000) | 0/10 (0.0000) | 0/5 (0.0000) | 0/10 (0.0000) |
| hq_e3dfcc6ccd02482fb791dc34596565e7 | vector | 0/5 (0.0000) | 0/10 (0.0000) | 0/5 (0.0000) | 0/10 (0.0000) |
| hq_e3dfcc6ccd02482fb791dc34596565e7 | keyword | 2/5 (0.4000) | 4/10 (0.4000) | 2/5 (0.4000) | 4/10 (0.4000) |
| hq_e3dfcc6ccd02482fb791dc34596565e7 | hybrid | 0/5 (0.0000) | 0/10 (0.0000) | 0/5 (0.0000) | 0/10 (0.0000) |
| hq_e3dfcc6ccd02482fb791dc34596565e7 | hybrid_rerank | 1/5 (0.2000) | 2/10 (0.2000) | 1/5 (0.2000) | 2/10 (0.2000) |
| hq_e9bf3b51fc6948de9eaa071fdbdb0e46 | vector | 0/5 (0.0000) | 0/10 (0.0000) | 0/5 (0.0000) | 0/10 (0.0000) |
| hq_e9bf3b51fc6948de9eaa071fdbdb0e46 | keyword | 1/5 (0.2000) | 3/10 (0.3000) | 1/5 (0.2000) | 3/10 (0.3000) |
| hq_e9bf3b51fc6948de9eaa071fdbdb0e46 | hybrid | 0/5 (0.0000) | 0/10 (0.0000) | 0/5 (0.0000) | 0/10 (0.0000) |
| hq_e9bf3b51fc6948de9eaa071fdbdb0e46 | hybrid_rerank | 0/5 (0.0000) | 2/10 (0.2000) | 0/5 (0.0000) | 2/10 (0.2000) |
| hq_eead0b7f7e3f430589800660cafe8cb1 | vector | 0/5 (0.0000) | 0/10 (0.0000) | 0/5 (0.0000) | 0/10 (0.0000) |
| hq_eead0b7f7e3f430589800660cafe8cb1 | keyword | 0/5 (0.0000) | 0/10 (0.0000) | 0/5 (0.0000) | 0/10 (0.0000) |
| hq_eead0b7f7e3f430589800660cafe8cb1 | hybrid | 0/5 (0.0000) | 0/10 (0.0000) | 0/5 (0.0000) | 0/10 (0.0000) |
| hq_eead0b7f7e3f430589800660cafe8cb1 | hybrid_rerank | 0/5 (0.0000) | 0/10 (0.0000) | 0/5 (0.0000) | 0/10 (0.0000) |
| hq_efbdb0ea523543c699eddddde9b1e638 | vector | 0/5 (0.0000) | 0/10 (0.0000) | 0/5 (0.0000) | 0/10 (0.0000) |
| hq_efbdb0ea523543c699eddddde9b1e638 | keyword | 2/5 (0.4000) | 5/10 (0.5000) | 2/5 (0.4000) | 6/10 (0.6000) |
| hq_efbdb0ea523543c699eddddde9b1e638 | hybrid | 0/5 (0.0000) | 1/10 (0.1000) | 0/5 (0.0000) | 1/10 (0.1000) |
| hq_efbdb0ea523543c699eddddde9b1e638 | hybrid_rerank | 2/5 (0.4000) | 4/10 (0.4000) | 3/5 (0.6000) | 5/10 (0.5000) |
| hq_f5d53183cdd04505b02cde17b599d44f | vector | 0/5 (0.0000) | 0/10 (0.0000) | 0/5 (0.0000) | 0/10 (0.0000) |
| hq_f5d53183cdd04505b02cde17b599d44f | keyword | 2/5 (0.4000) | 4/10 (0.4000) | 2/5 (0.4000) | 4/10 (0.4000) |
| hq_f5d53183cdd04505b02cde17b599d44f | hybrid | 0/5 (0.0000) | 0/10 (0.0000) | 0/5 (0.0000) | 0/10 (0.0000) |
| hq_f5d53183cdd04505b02cde17b599d44f | hybrid_rerank | 0/5 (0.0000) | 1/10 (0.1000) | 0/5 (0.0000) | 1/10 (0.1000) |

### Cross-year near-duplicates

Before analysis, D032 fixed this heuristic: normalize Unicode/case, form five-word shingle sets, require at least 20 shingles on each side, and flag overlap ≥0.70 (intersection divided by the smaller set) with a gold passage from a different accession. Containment permits shifted chunk boundaries; shared boilerplate can also trigger it. This is text overlap, not a new relevance judgment. Each slot below shows its largest different-filing gold overlap.

#### MSFT: Why did Microsoft's cloud profit margins shrink in fiscal 2025 while cloud sales grew?

ID: `hq_19ea90a4eeb84991845ef0f0a3c4d316`.

| Mode | Rank | Chunk ID | Ticker | Form | FY | Period | Item | Accession | Gold | Near-duplicate | Overlap | Closest gold ID (FY) |
|---|---:|---|---|---|---:|---|---|---|---|---|---:|---|
| vector | 1 | chk_6f7f4c81eb063f7262b7975e7d40e982e24e6b8b9255163ae88a5eb3fc51c116 | MSFT | 10-K | 2025 | FY | 7 | 0000950170-25-100235 | yes |  | 0.000 | — |
| vector | 2 | chk_1104f73e99f239fcc875ad804ffcfc753644cdf18939155674dc76d46b32412a | MSFT | 10-Q | 2026 | Q3 | P1-2 | 0001193125-26-191507 |  |  | 0.200 | chk_6f7f4c81eb063f7262b7975e7d40e982e24e6b8b9255163ae88a5eb3fc51c116 (2025) |
| vector | 3 | chk_79734e3040b0321af6386655a1b47eb740c50d0bd46d68482abb934cd40dda7c | MSFT | 10-Q | 2025 | Q1 | P1-2 | 0000950170-24-118967 |  |  | 0.205 | chk_e0355c67ed705f969ab8854f5b548a92ec2553db383579a14c1c0f439cce3f09 (2025) |
| vector | 4 | chk_a9740c9129053cc894d4ef5dce94d9623064b96647f58c34012ff51a2cdc14e6 | MSFT | 10-K | 2024 | FY | 7 | 0000950170-24-087843 |  |  | 0.101 | chk_6f7f4c81eb063f7262b7975e7d40e982e24e6b8b9255163ae88a5eb3fc51c116 (2025) |
| vector | 5 | chk_4b90f70217fd80706a670d4d3aad6e8a304678d2109a5edbd3a1e5929538ce0f | MSFT | 10-K | 2025 | FY | 7 | 0000950170-25-100235 |  |  | 0.000 | — |
| vector | 6 | chk_8af6e3ec6235806588ddcb6255810e1544afefcf41b40f6234b0bc48e77d363d | MSFT | 10-Q | 2025 | Q2 | P1-2 | 0000950170-25-010491 |  |  | 0.297 | chk_e0355c67ed705f969ab8854f5b548a92ec2553db383579a14c1c0f439cce3f09 (2025) |
| vector | 7 | chk_b5ffaa29a361638c723cad2627f13cc27581012ddc3c7c73fda295e04293872c | MSFT | 10-Q | 2024 | Q1 | P1-2 | 0000950170-23-054855 |  |  | 0.107 | chk_6f7f4c81eb063f7262b7975e7d40e982e24e6b8b9255163ae88a5eb3fc51c116 (2025) |
| vector | 8 | chk_d284a3f16b628ffe64e73304ff6f7c1f747bb596e9155765d48dffdd9de1b6e6 | MSFT | 10-K | 2026 | FY | 7 | 0001193125-26-323660 |  |  | 0.033 | chk_e0355c67ed705f969ab8854f5b548a92ec2553db383579a14c1c0f439cce3f09 (2025) |
| vector | 9 | chk_477292f9ee5e559bf6d4c5525c2aaed9e1f0f226481f287aabd641b8dfbfa271 | MSFT | 10-Q | 2026 | Q2 | P1-2 | 0001193125-26-027207 |  |  | 0.084 | chk_e0355c67ed705f969ab8854f5b548a92ec2553db383579a14c1c0f439cce3f09 (2025) |
| vector | 10 | chk_3d2c2326075e81631bab4f2aa75307d1fe6aa4c71f997c4f8fc6755a6c8c7674 | MSFT | 10-Q | 2025 | Q2 | P1-2 | 0000950170-25-010491 |  |  | 0.376 | chk_6f7f4c81eb063f7262b7975e7d40e982e24e6b8b9255163ae88a5eb3fc51c116 (2025) |
| hybrid_rerank | 1 | chk_66acab74b1b43e379f8bca9d4204f0e80c246234eb3a87a1d1c89ebf04831ce0 | MSFT | 10-Q | 2026 | Q2 | P1-2 | 0001193125-26-027207 |  |  | 0.251 | chk_6f7f4c81eb063f7262b7975e7d40e982e24e6b8b9255163ae88a5eb3fc51c116 (2025) |
| hybrid_rerank | 2 | chk_1104f73e99f239fcc875ad804ffcfc753644cdf18939155674dc76d46b32412a | MSFT | 10-Q | 2026 | Q3 | P1-2 | 0001193125-26-191507 |  |  | 0.200 | chk_6f7f4c81eb063f7262b7975e7d40e982e24e6b8b9255163ae88a5eb3fc51c116 (2025) |
| hybrid_rerank | 3 | chk_6f7f4c81eb063f7262b7975e7d40e982e24e6b8b9255163ae88a5eb3fc51c116 | MSFT | 10-K | 2025 | FY | 7 | 0000950170-25-100235 | yes |  | 0.000 | — |
| hybrid_rerank | 4 | chk_a9740c9129053cc894d4ef5dce94d9623064b96647f58c34012ff51a2cdc14e6 | MSFT | 10-K | 2024 | FY | 7 | 0000950170-24-087843 |  |  | 0.101 | chk_6f7f4c81eb063f7262b7975e7d40e982e24e6b8b9255163ae88a5eb3fc51c116 (2025) |
| hybrid_rerank | 5 | chk_477292f9ee5e559bf6d4c5525c2aaed9e1f0f226481f287aabd641b8dfbfa271 | MSFT | 10-Q | 2026 | Q2 | P1-2 | 0001193125-26-027207 |  |  | 0.084 | chk_e0355c67ed705f969ab8854f5b548a92ec2553db383579a14c1c0f439cce3f09 (2025) |
| hybrid_rerank | 6 | chk_79734e3040b0321af6386655a1b47eb740c50d0bd46d68482abb934cd40dda7c | MSFT | 10-Q | 2025 | Q1 | P1-2 | 0000950170-24-118967 |  |  | 0.205 | chk_e0355c67ed705f969ab8854f5b548a92ec2553db383579a14c1c0f439cce3f09 (2025) |
| hybrid_rerank | 7 | chk_59acfa6de0035a0f7a355ec87c8e4159a1556c1891a74689bdc86f76f80dacf8 | MSFT | 10-Q | 2026 | Q2 | P1-2 | 0001193125-26-027207 |  |  | 0.072 | chk_e0355c67ed705f969ab8854f5b548a92ec2553db383579a14c1c0f439cce3f09 (2025) |
| hybrid_rerank | 8 | chk_4b90f70217fd80706a670d4d3aad6e8a304678d2109a5edbd3a1e5929538ce0f | MSFT | 10-K | 2025 | FY | 7 | 0000950170-25-100235 |  |  | 0.000 | — |
| hybrid_rerank | 9 | chk_974f0756f4cd259ae7ed56dbdfa332b5c1587510801968c53b06c48db6171a47 | MSFT | 10-Q | 2026 | Q3 | P1-2 | 0001193125-26-191507 |  |  | 0.023 | chk_6f7f4c81eb063f7262b7975e7d40e982e24e6b8b9255163ae88a5eb3fc51c116 (2025) |
| hybrid_rerank | 10 | chk_7aa0ddee17fe30b7f381c43f3fcb668ab9181842be8158ff41545c5db3c7baf2 | MSFT | 10-K | 2026 | FY | 7 | 0001193125-26-323660 |  |  | 0.195 | chk_6f7f4c81eb063f7262b7975e7d40e982e24e6b8b9255163ae88a5eb3fc51c116 (2025) |

vector: 0/10 different-filing near-duplicate slots; 1/10 exact gold slots.
hybrid_rerank: 0/10 different-filing near-duplicate slots; 1/10 exact gold slots.

#### AMZN: What factors drove the change in AWS segment operating income in 2024?

ID: `hq_5404d74f74b4456e9c72c7def4c64227`.

| Mode | Rank | Chunk ID | Ticker | Form | FY | Period | Item | Accession | Gold | Near-duplicate | Overlap | Closest gold ID (FY) |
|---|---:|---|---|---|---:|---|---|---|---|---|---:|---|
| vector | 1 | chk_05580082e3efad88ff066a2624c7d922941ac0c210a730ca19c0265427916d00 | AMZN | 10-K | 2024 | FY | 7 | 0001018724-25-000004 | yes |  | 0.000 | — |
| vector | 2 | chk_789685d5115cafe3a1cc94c899a65073be2143bec21c8e479acc0828b736e904 | AMZN | 10-Q | 2025 | Q2 | P1-2 | 0001018724-25-000086 |  |  | 0.403 | chk_05580082e3efad88ff066a2624c7d922941ac0c210a730ca19c0265427916d00 (2024) |
| vector | 3 | chk_efd33b1838a5bcee2397be9e88ecd5d5be04b9956f727edc20b89867a3e76234 | AMZN | 10-Q | 2024 | Q1 | P1-2 | 0001018724-24-000083 |  |  | 0.336 | chk_05580082e3efad88ff066a2624c7d922941ac0c210a730ca19c0265427916d00 (2024) |
| vector | 4 | chk_2a798b57c00bbe549361e1efb1dea55a857c7483fabdb4cd05400f4053ce1f3e | AMZN | 10-Q | 2026 | Q1 | P1-2 | 0001018724-26-000014 |  |  | 0.495 | chk_05580082e3efad88ff066a2624c7d922941ac0c210a730ca19c0265427916d00 (2024) |
| vector | 5 | chk_23683dda281731d1c88efb6f0adbd1a8b8429c2043f35ad782703a675ba8fcde | AMZN | 10-Q | 2026 | Q2 | P1-2 | 0001018724-26-000026 |  |  | 0.462 | chk_05580082e3efad88ff066a2624c7d922941ac0c210a730ca19c0265427916d00 (2024) |
| vector | 6 | chk_17d1e23b476171e195889dde9a4638bf27f4ec868e9f242d16f01164e581c64f | AMZN | 10-K | 2025 | FY | 7 | 0001018724-26-000004 |  |  | 0.435 | chk_bc4b98afde024b83b09036b24d4d3fb537897e56fafcd269d00a92d164d63ce1 (2024) |
| vector | 7 | chk_0c55488b1f0cdbeca3dac570101bab59df748182495309c05b35af64189e79c7 | AMZN | 10-Q | 2024 | Q3 | P1-2 | 0001018724-24-000161 |  |  | 0.538 | chk_05580082e3efad88ff066a2624c7d922941ac0c210a730ca19c0265427916d00 (2024) |
| vector | 8 | chk_5955b0521e85b065331ea7d01fa4d32f6514b5e1ee10224ed91e990a277da9cc | AMZN | 10-Q | 2025 | Q1 | P1-2 | 0001018724-25-000036 |  |  | 0.512 | chk_05580082e3efad88ff066a2624c7d922941ac0c210a730ca19c0265427916d00 (2024) |
| vector | 9 | chk_c49ad1e7c69ecaae2521e633c3c3bc57a684668c1dc36c1532b538335b2a0b80 | AMZN | 10-K | 2024 | FY | 8 | 0001018724-25-000004 |  |  | 0.000 | — |
| vector | 10 | chk_6eafc122b5748bebba7970c3bc71dbbb94cb172d70b9c836aa86fa7eabdb36d2 | AMZN | 10-Q | 2024 | Q2 | P1-2 | 0001018724-24-000130 |  |  | 0.418 | chk_05580082e3efad88ff066a2624c7d922941ac0c210a730ca19c0265427916d00 (2024) |
| hybrid_rerank | 1 | chk_05580082e3efad88ff066a2624c7d922941ac0c210a730ca19c0265427916d00 | AMZN | 10-K | 2024 | FY | 7 | 0001018724-25-000004 | yes |  | 0.000 | — |
| hybrid_rerank | 2 | chk_efd33b1838a5bcee2397be9e88ecd5d5be04b9956f727edc20b89867a3e76234 | AMZN | 10-Q | 2024 | Q1 | P1-2 | 0001018724-24-000083 |  |  | 0.336 | chk_05580082e3efad88ff066a2624c7d922941ac0c210a730ca19c0265427916d00 (2024) |
| hybrid_rerank | 3 | chk_bc4b98afde024b83b09036b24d4d3fb537897e56fafcd269d00a92d164d63ce1 | AMZN | 10-K | 2024 | FY | 7 | 0001018724-25-000004 | yes |  | 0.000 | — |
| hybrid_rerank | 4 | chk_c3689cd1dbd711fbd32227fa922636175b58fa381623f5b09c05e964fd7d2894 | AMZN | 10-Q | 2024 | Q1 | P1-2 | 0001018724-24-000083 |  |  | 0.004 | chk_05580082e3efad88ff066a2624c7d922941ac0c210a730ca19c0265427916d00 (2024) |
| hybrid_rerank | 5 | chk_cd37cf74cddc415627c65b0e54f098f4baffaa830230e454380d87e91e0905f6 | AMZN | 10-Q | 2024 | Q1 | P1-2 | 0001018724-24-000083 |  |  | 0.439 | chk_05580082e3efad88ff066a2624c7d922941ac0c210a730ca19c0265427916d00 (2024) |
| hybrid_rerank | 6 | chk_6eafc122b5748bebba7970c3bc71dbbb94cb172d70b9c836aa86fa7eabdb36d2 | AMZN | 10-Q | 2024 | Q2 | P1-2 | 0001018724-24-000130 |  |  | 0.418 | chk_05580082e3efad88ff066a2624c7d922941ac0c210a730ca19c0265427916d00 (2024) |
| hybrid_rerank | 7 | chk_5955b0521e85b065331ea7d01fa4d32f6514b5e1ee10224ed91e990a277da9cc | AMZN | 10-Q | 2025 | Q1 | P1-2 | 0001018724-25-000036 |  |  | 0.512 | chk_05580082e3efad88ff066a2624c7d922941ac0c210a730ca19c0265427916d00 (2024) |
| hybrid_rerank | 8 | chk_64d408c95e1b2ccdfd7001e0752b38347c11581cf930dc26de29ebfcb2b2f9ca | AMZN | 10-Q | 2024 | Q2 | P1-2 | 0001018724-24-000130 |  |  | 0.055 | chk_05580082e3efad88ff066a2624c7d922941ac0c210a730ca19c0265427916d00 (2024) |
| hybrid_rerank | 9 | chk_789685d5115cafe3a1cc94c899a65073be2143bec21c8e479acc0828b736e904 | AMZN | 10-Q | 2025 | Q2 | P1-2 | 0001018724-25-000086 |  |  | 0.403 | chk_05580082e3efad88ff066a2624c7d922941ac0c210a730ca19c0265427916d00 (2024) |
| hybrid_rerank | 10 | chk_17d1e23b476171e195889dde9a4638bf27f4ec868e9f242d16f01164e581c64f | AMZN | 10-K | 2025 | FY | 7 | 0001018724-26-000004 |  |  | 0.435 | chk_bc4b98afde024b83b09036b24d4d3fb537897e56fafcd269d00a92d164d63ce1 (2024) |

vector: 0/10 different-filing near-duplicate slots; 1/10 exact gold slots.
hybrid_rerank: 0/10 different-filing near-duplicate slots; 2/10 exact gold slots.

#### COST: How did the membership fee increase affect Costco's membership fee income in fiscal 2025?

ID: `hq_84c831be7d16420aae81eb2d9f98c8af`.

| Mode | Rank | Chunk ID | Ticker | Form | FY | Period | Item | Accession | Gold | Near-duplicate | Overlap | Closest gold ID (FY) |
|---|---:|---|---|---|---:|---|---|---|---|---|---:|---|
| vector | 1 | chk_ed87945ab4a025d36a72a98dbebcc9274bc4a7558a9311337815edfaac4c8d56 | COST | 10-K | 2025 | FY | 7 | 0000909832-25-000101 | yes |  | 0.000 | — |
| vector | 2 | chk_dfd92e9bf9de2a5b2e5d79d24807ad9bb5c9d35436d5b0543534d1acd65f8e41 | COST | 10-K | 2026 | FY | 1 | 0000909832-26-000093 |  |  | 0.027 | chk_ed87945ab4a025d36a72a98dbebcc9274bc4a7558a9311337815edfaac4c8d56 (2025) |
| vector | 3 | chk_fc6f21f5c80f1eb3a90747a6cb87f5160a23d1cc7f655e63116d3f432ff11864 | COST | 10-Q | 2025 | Q1 | P1-2 | 0000909832-24-000079 |  |  | 0.154 | chk_ed87945ab4a025d36a72a98dbebcc9274bc4a7558a9311337815edfaac4c8d56 (2025) |
| vector | 4 | chk_433ccddd5a6dc4e31d0f201ee7a8d7fc9397e7896aba534449a47727ef77cc5d | COST | 10-Q | 2026 | Q1 | P1-2 | 0000909832-25-000169 |  |  | 0.271 | chk_ed87945ab4a025d36a72a98dbebcc9274bc4a7558a9311337815edfaac4c8d56 (2025) |
| vector | 5 | chk_9dbfee0bc503403b3afb302d55505512d328c64fb5980724dbdf4f6861b8a059 | COST | 10-K | 2025 | FY | 7 | 0000909832-25-000101 |  |  | 0.000 | — |
| vector | 6 | chk_3ff24915c2965e9d80bf13957056053b31de6769f1735a4c30d279694245713c | COST | 10-Q | 2025 | Q3 | P1-2 | 0000909832-25-000033 |  |  | 0.221 | chk_ed87945ab4a025d36a72a98dbebcc9274bc4a7558a9311337815edfaac4c8d56 (2025) |
| vector | 7 | chk_71a66339febe63aaf7ad2eec282f22d2f919145c21dc8b18bfea4f1a4607b1ce | COST | 10-Q | 2026 | Q3 | P1-2 | 0000909832-26-000051 |  |  | 0.343 | chk_ed87945ab4a025d36a72a98dbebcc9274bc4a7558a9311337815edfaac4c8d56 (2025) |
| vector | 8 | chk_7d547548a550096250537b75e8049d61c67a4b887b570b7f2dd533b374e6bcce | COST | 10-Q | 2026 | Q2 | P1-2 | 0000909832-26-000029 |  |  | 0.427 | chk_ed87945ab4a025d36a72a98dbebcc9274bc4a7558a9311337815edfaac4c8d56 (2025) |
| vector | 9 | chk_07c1fd70c49b3ea44a4418bc644ab55a829a2d7e743d56de610ff2dc9a3abfb2 | COST | 10-Q | 2025 | Q2 | P1-2 | 0000909832-25-000015 |  |  | 0.233 | chk_ed87945ab4a025d36a72a98dbebcc9274bc4a7558a9311337815edfaac4c8d56 (2025) |
| vector | 10 | chk_7178639c77fbec93543fc72a2f660df297fc13827b22bdbe54bf370925806131 | COST | 10-K | 2026 | FY | 7 | 0000909832-26-000093 |  |  | 0.343 | chk_ed87945ab4a025d36a72a98dbebcc9274bc4a7558a9311337815edfaac4c8d56 (2025) |
| hybrid_rerank | 1 | chk_71a66339febe63aaf7ad2eec282f22d2f919145c21dc8b18bfea4f1a4607b1ce | COST | 10-Q | 2026 | Q3 | P1-2 | 0000909832-26-000051 |  |  | 0.343 | chk_ed87945ab4a025d36a72a98dbebcc9274bc4a7558a9311337815edfaac4c8d56 (2025) |
| hybrid_rerank | 2 | chk_3ff24915c2965e9d80bf13957056053b31de6769f1735a4c30d279694245713c | COST | 10-Q | 2025 | Q3 | P1-2 | 0000909832-25-000033 |  |  | 0.221 | chk_ed87945ab4a025d36a72a98dbebcc9274bc4a7558a9311337815edfaac4c8d56 (2025) |
| hybrid_rerank | 3 | chk_ed87945ab4a025d36a72a98dbebcc9274bc4a7558a9311337815edfaac4c8d56 | COST | 10-K | 2025 | FY | 7 | 0000909832-25-000101 | yes |  | 0.000 | — |
| hybrid_rerank | 4 | chk_433ccddd5a6dc4e31d0f201ee7a8d7fc9397e7896aba534449a47727ef77cc5d | COST | 10-Q | 2026 | Q1 | P1-2 | 0000909832-25-000169 |  |  | 0.271 | chk_ed87945ab4a025d36a72a98dbebcc9274bc4a7558a9311337815edfaac4c8d56 (2025) |
| hybrid_rerank | 5 | chk_fc6f21f5c80f1eb3a90747a6cb87f5160a23d1cc7f655e63116d3f432ff11864 | COST | 10-Q | 2025 | Q1 | P1-2 | 0000909832-24-000079 |  |  | 0.154 | chk_ed87945ab4a025d36a72a98dbebcc9274bc4a7558a9311337815edfaac4c8d56 (2025) |
| hybrid_rerank | 6 | chk_9dbfee0bc503403b3afb302d55505512d328c64fb5980724dbdf4f6861b8a059 | COST | 10-K | 2025 | FY | 7 | 0000909832-25-000101 |  |  | 0.000 | — |
| hybrid_rerank | 7 | chk_07c1fd70c49b3ea44a4418bc644ab55a829a2d7e743d56de610ff2dc9a3abfb2 | COST | 10-Q | 2025 | Q2 | P1-2 | 0000909832-25-000015 |  |  | 0.233 | chk_ed87945ab4a025d36a72a98dbebcc9274bc4a7558a9311337815edfaac4c8d56 (2025) |
| hybrid_rerank | 8 | chk_7d547548a550096250537b75e8049d61c67a4b887b570b7f2dd533b374e6bcce | COST | 10-Q | 2026 | Q2 | P1-2 | 0000909832-26-000029 |  |  | 0.427 | chk_ed87945ab4a025d36a72a98dbebcc9274bc4a7558a9311337815edfaac4c8d56 (2025) |
| hybrid_rerank | 9 | chk_738f306a98075141b66d24990ba3c698e1a295ac6e15588e2f20dc85dd95b119 | COST | 10-Q | 2025 | Q2 | P1-2 | 0000909832-25-000015 |  |  | 0.119 | chk_ed87945ab4a025d36a72a98dbebcc9274bc4a7558a9311337815edfaac4c8d56 (2025) |
| hybrid_rerank | 10 | chk_7178639c77fbec93543fc72a2f660df297fc13827b22bdbe54bf370925806131 | COST | 10-K | 2026 | FY | 7 | 0000909832-26-000093 |  |  | 0.343 | chk_ed87945ab4a025d36a72a98dbebcc9274bc4a7558a9311337815edfaac4c8d56 (2025) |

vector: 0/10 different-filing near-duplicate slots; 1/10 exact gold slots.
hybrid_rerank: 0/10 different-filing near-duplicate slots; 1/10 exact gold slots.

#### NVDA: In fiscal 2025, how did NVIDIA describe the risk of U.S. export controls on sales to China?

ID: `hq_9e6c0c0dbb5941589c85ed5a923d944e`.

| Mode | Rank | Chunk ID | Ticker | Form | FY | Period | Item | Accession | Gold | Near-duplicate | Overlap | Closest gold ID (FY) |
|---|---:|---|---|---|---:|---|---|---|---|---|---:|---|
| vector | 1 | chk_7c1b076c968a4d1745d5437c36772c8378094c4644c627811ef639314d8a574a | NVDA | 10-Q | 2027 | Q2 | P2-1A | 0001045810-26-000075 |  |  | 0.658 | chk_c721eead2c55d84c74ae4e3b239bb9c0c86a79b18af0e87adb35ae8c99001840 (2025) |
| vector | 2 | chk_0c9afdde7f4d9729d334084b1bd253db8817ec395c3de1461e6913cf05023fd5 | NVDA | 10-Q | 2026 | Q2 | P2-1A | 0001045810-25-000209 |  | yes | 0.814 | chk_c721eead2c55d84c74ae4e3b239bb9c0c86a79b18af0e87adb35ae8c99001840 (2025) |
| vector | 3 | chk_51efb73eb1717fe99cd22990881454e84288891e7dec2f016ed77d3a204ac036 | NVDA | 10-Q | 2026 | Q3 | P2-1A | 0001045810-25-000230 |  |  | 0.696 | chk_c721eead2c55d84c74ae4e3b239bb9c0c86a79b18af0e87adb35ae8c99001840 (2025) |
| vector | 4 | chk_88c31a16c35e4630300eff6dd835c362a7b48a56226847d12eb7f00983a9f742 | NVDA | 10-Q | 2026 | Q1 | P2-1A | 0001045810-25-000116 |  | yes | 0.851 | chk_c721eead2c55d84c74ae4e3b239bb9c0c86a79b18af0e87adb35ae8c99001840 (2025) |
| vector | 5 | chk_1564a5d998bcee742230974031d9200138cdcef86291747a78ec27688f65cf0f | NVDA | 10-Q | 2024 | Q3 | P2-1A | 0001045810-23-000227 |  |  | 0.625 | chk_c721eead2c55d84c74ae4e3b239bb9c0c86a79b18af0e87adb35ae8c99001840 (2025) |
| vector | 6 | chk_e9233fa310f7ba38cd3b9c8968c4d518a89c1d8c409d9bd5eeb455267f9e1937 | NVDA | 10-K | 2026 | FY | 1A | 0001045810-26-000021 |  | yes | 0.709 | chk_c721eead2c55d84c74ae4e3b239bb9c0c86a79b18af0e87adb35ae8c99001840 (2025) |
| vector | 7 | chk_718580b25a7c64f26736bca3813d320c81a37d00b415ea8c989121b63053f5c9 | NVDA | 10-Q | 2025 | Q1 | P2-1A | 0001045810-24-000124 |  | yes | 0.936 | chk_c721eead2c55d84c74ae4e3b239bb9c0c86a79b18af0e87adb35ae8c99001840 (2025) |
| vector | 8 | chk_86e496a45032f13f6429a576e70d3921739c42e77d3950c59a1ff5c54e763435 | NVDA | 10-Q | 2024 | Q1 | P2-1A | 0001045810-23-000093 |  |  | 0.136 | chk_5e5d13f68679b38681add415ee5493219b030598121446c7e94141056aa5e31c (2025) |
| vector | 9 | chk_39532a693ec000fbccfa9d09d22cd357ac0bd25d8a7ed3328820d05434fbca18 | NVDA | 10-K | 2026 | FY | 1A | 0001045810-26-000021 |  |  | 0.262 | chk_5e5d13f68679b38681add415ee5493219b030598121446c7e94141056aa5e31c (2025) |
| vector | 10 | chk_9b89f51446f4ecba7276d46e7fb6f18e2a74231fbf20e99b79d86f67f0a396df | NVDA | 10-Q | 2027 | Q1 | P2-1A | 0001045810-26-000052 |  |  | 0.037 | chk_d19430599838d968bc9fad6310f844a7e594d763f6f30410a5ebb57c3b6994a1 (2025) |
| hybrid_rerank | 1 | chk_fadcb80459d0e59cc265d08342f149356edac695ae68b6b802bcee032a9025af | NVDA | 10-Q | 2024 | Q2 | P2-1A | 0001045810-23-000175 |  |  | 0.651 | chk_c721eead2c55d84c74ae4e3b239bb9c0c86a79b18af0e87adb35ae8c99001840 (2025) |
| hybrid_rerank | 2 | chk_f7698e67c0e1639fe24f53f29dbd20795696be7b221988cc9ceb727e2965db0f | NVDA | 10-Q | 2026 | Q2 | P2-1A | 0001045810-25-000209 |  |  | 0.359 | chk_c721eead2c55d84c74ae4e3b239bb9c0c86a79b18af0e87adb35ae8c99001840 (2025) |
| hybrid_rerank | 3 | chk_d9d9904b884f0144760acfcfcfcbd432cf6d284aed2624fea9677cebdb88806b | NVDA | 10-Q | 2026 | Q3 | P2-1A | 0001045810-25-000230 |  |  | 0.329 | chk_c721eead2c55d84c74ae4e3b239bb9c0c86a79b18af0e87adb35ae8c99001840 (2025) |
| hybrid_rerank | 4 | chk_123a0423f0ef027bc39f579b868718f3c8396be2b6e6cd1cf23be8e4e4421dda | NVDA | 10-K | 2026 | FY | 1A | 0001045810-26-000021 |  |  | 0.329 | chk_c721eead2c55d84c74ae4e3b239bb9c0c86a79b18af0e87adb35ae8c99001840 (2025) |
| hybrid_rerank | 5 | chk_7f865ffbaa9c9f2b057708591fefe8d37090e6b73aec3c2e7306b083d2eaad12 | NVDA | 10-Q | 2024 | Q1 | P1-2 | 0001045810-23-000093 |  |  | 0.210 | chk_18eba3a38d39530b629a0c57b33dd4969f659cba453388db66a7923d1c9f09a8 (2025) |
| hybrid_rerank | 6 | chk_88c31a16c35e4630300eff6dd835c362a7b48a56226847d12eb7f00983a9f742 | NVDA | 10-Q | 2026 | Q1 | P2-1A | 0001045810-25-000116 |  | yes | 0.851 | chk_c721eead2c55d84c74ae4e3b239bb9c0c86a79b18af0e87adb35ae8c99001840 (2025) |
| hybrid_rerank | 7 | chk_718580b25a7c64f26736bca3813d320c81a37d00b415ea8c989121b63053f5c9 | NVDA | 10-Q | 2025 | Q1 | P2-1A | 0001045810-24-000124 |  | yes | 0.936 | chk_c721eead2c55d84c74ae4e3b239bb9c0c86a79b18af0e87adb35ae8c99001840 (2025) |
| hybrid_rerank | 8 | chk_81a39a4c3a008a6e91c2b8e4d73151fc45bec50c145cb2cf6c77d4ce89a7d126 | NVDA | 10-Q | 2025 | Q3 | P2-1A | 0001045810-24-000316 |  |  | 0.655 | chk_c721eead2c55d84c74ae4e3b239bb9c0c86a79b18af0e87adb35ae8c99001840 (2025) |
| hybrid_rerank | 9 | chk_c721eead2c55d84c74ae4e3b239bb9c0c86a79b18af0e87adb35ae8c99001840 | NVDA | 10-K | 2025 | FY | 1A | 0001045810-25-000023 | yes |  | 0.000 | — |
| hybrid_rerank | 10 | chk_e9233fa310f7ba38cd3b9c8968c4d518a89c1d8c409d9bd5eeb455267f9e1937 | NVDA | 10-K | 2026 | FY | 1A | 0001045810-26-000021 |  | yes | 0.709 | chk_c721eead2c55d84c74ae4e3b239bb9c0c86a79b18af0e87adb35ae8c99001840 (2025) |

vector: 4/10 different-filing near-duplicate slots; 0/10 exact gold slots.
hybrid_rerank: 3/10 different-filing near-duplicate slots; 1/10 exact gold slots.

#### CVX: As of its fiscal 2024 10-K, what was the status of Chevron's Hess acquisition and the Stabroek arbitration?

ID: `hq_e9bf3b51fc6948de9eaa071fdbdb0e46`.

| Mode | Rank | Chunk ID | Ticker | Form | FY | Period | Item | Accession | Gold | Near-duplicate | Overlap | Closest gold ID (FY) |
|---|---:|---|---|---|---:|---|---|---|---|---|---:|---|
| vector | 1 | chk_2e42a141227b8454615289e6151bda550c82b80567b9409f9d3a4ce109038a6b | CVX | 10-K | 2024 | FY | 1A | 0000093410-25-000009 | yes |  | 0.000 | — |
| vector | 2 | chk_859d61ee7c9379d7e35848b5078f09a2a3b23c7c9c8faede3f50470201e37aaa | CVX | 10-Q | 2025 | Q1 | P2-1A | 0000093410-25-000019 |  | yes | 0.769 | chk_2e42a141227b8454615289e6151bda550c82b80567b9409f9d3a4ce109038a6b (2024) |
| vector | 3 | chk_398ec6f2d9b3cacd24a05c01fa6cfbc85afba31dfefd2555d660495dc55a315e | CVX | 10-Q | 2024 | Q2 | P2-1A | 0000093410-24-000040 |  |  | 0.646 | chk_2e42a141227b8454615289e6151bda550c82b80567b9409f9d3a4ce109038a6b (2024) |
| vector | 4 | chk_97919e24436ebe0bb6abdbd2573f6c245015772badce73e50855e7b1b901b9d6 | CVX | 10-Q | 2024 | Q3 | P2-1A | 0000093410-24-000059 |  |  | 0.658 | chk_2e42a141227b8454615289e6151bda550c82b80567b9409f9d3a4ce109038a6b (2024) |
| vector | 5 | chk_7b196f2a1bb3de83e990718ad5da80dca1f369bdb8fb59b0c2f1203abe5c6d9e | CVX | 10-K | 2023 | FY | 1A | 0000093410-24-000013 |  |  | 0.415 | chk_2e42a141227b8454615289e6151bda550c82b80567b9409f9d3a4ce109038a6b (2024) |
| vector | 6 | chk_66ab8d8451bcf3ed7170c79193e14abb0a17d86a37641a6fff3cf7aa1651eb93 | CVX | 10-Q | 2024 | Q1 | P2-1A | 0000093410-24-000021 |  |  | 0.504 | chk_2e42a141227b8454615289e6151bda550c82b80567b9409f9d3a4ce109038a6b (2024) |
| vector | 7 | chk_0aad5c24956ce4e7d85cbc4a646e74e5ee7220931ec3e123ce62a296cc914915 | CVX | 10-Q | 2024 | Q3 | P2-1A | 0000093410-24-000059 |  |  | 0.629 | chk_ca165e98459a98074fcde33a1be6e4db5d9de086cb750596b4ccb301d0ea2fbd (2024) |
| vector | 8 | chk_b4a369d4370a05dc89ef86e5806945a8b1c2de2a7cbe22fe4f29aec22cbbd156 | CVX | 10-Q | 2025 | Q1 | P1-2 | 0000093410-25-000019 |  |  | 0.000 | chk_ca165e98459a98074fcde33a1be6e4db5d9de086cb750596b4ccb301d0ea2fbd (2024) |
| vector | 9 | chk_0ad15cb4301b459e76146756ce20e3efd2111bd0d73fead2148b9ca37b9acfec | CVX | 10-Q | 2024 | Q3 | P1-2 | 0000093410-24-000059 |  |  | 0.000 | chk_ca165e98459a98074fcde33a1be6e4db5d9de086cb750596b4ccb301d0ea2fbd (2024) |
| vector | 10 | chk_ca165e98459a98074fcde33a1be6e4db5d9de086cb750596b4ccb301d0ea2fbd | CVX | 10-K | 2024 | FY | 1A | 0000093410-25-000009 | yes |  | 0.000 | — |
| hybrid_rerank | 1 | chk_2e42a141227b8454615289e6151bda550c82b80567b9409f9d3a4ce109038a6b | CVX | 10-K | 2024 | FY | 1A | 0000093410-25-000009 | yes |  | 0.000 | — |
| hybrid_rerank | 2 | chk_859d61ee7c9379d7e35848b5078f09a2a3b23c7c9c8faede3f50470201e37aaa | CVX | 10-Q | 2025 | Q1 | P2-1A | 0000093410-25-000019 |  | yes | 0.769 | chk_2e42a141227b8454615289e6151bda550c82b80567b9409f9d3a4ce109038a6b (2024) |
| hybrid_rerank | 3 | chk_66ab8d8451bcf3ed7170c79193e14abb0a17d86a37641a6fff3cf7aa1651eb93 | CVX | 10-Q | 2024 | Q1 | P2-1A | 0000093410-24-000021 |  |  | 0.504 | chk_2e42a141227b8454615289e6151bda550c82b80567b9409f9d3a4ce109038a6b (2024) |
| hybrid_rerank | 4 | chk_398ec6f2d9b3cacd24a05c01fa6cfbc85afba31dfefd2555d660495dc55a315e | CVX | 10-Q | 2024 | Q2 | P2-1A | 0000093410-24-000040 |  |  | 0.646 | chk_2e42a141227b8454615289e6151bda550c82b80567b9409f9d3a4ce109038a6b (2024) |
| hybrid_rerank | 5 | chk_97919e24436ebe0bb6abdbd2573f6c245015772badce73e50855e7b1b901b9d6 | CVX | 10-Q | 2024 | Q3 | P2-1A | 0000093410-24-000059 |  |  | 0.658 | chk_2e42a141227b8454615289e6151bda550c82b80567b9409f9d3a4ce109038a6b (2024) |
| hybrid_rerank | 6 | chk_b4a369d4370a05dc89ef86e5806945a8b1c2de2a7cbe22fe4f29aec22cbbd156 | CVX | 10-Q | 2025 | Q1 | P1-2 | 0000093410-25-000019 |  |  | 0.000 | chk_ca165e98459a98074fcde33a1be6e4db5d9de086cb750596b4ccb301d0ea2fbd (2024) |
| hybrid_rerank | 7 | chk_fc8572b73b2d8a0f9874d08e117d26edf3ef04e16f4afa62bd27323a273bd9b7 | CVX | 10-Q | 2025 | Q3 | P2-1A | 0000093410-25-000108 |  |  | 0.022 | chk_2e42a141227b8454615289e6151bda550c82b80567b9409f9d3a4ce109038a6b (2024) |
| hybrid_rerank | 8 | chk_eb09d6e1083115ad1e148625002beb492975de58bc09b80cb026ebdabe54a0cc | CVX | 10-Q | 2025 | Q2 | P2-1A | 0000093410-25-000062 |  |  | 0.022 | chk_2e42a141227b8454615289e6151bda550c82b80567b9409f9d3a4ce109038a6b (2024) |
| hybrid_rerank | 9 | chk_7f8869659e299bd9a91b72aabb5f7c1396916de63da6d475af019600752071ef | CVX | 10-Q | 2025 | Q1 | P2-1A | 0000093410-25-000019 |  |  | 0.615 | chk_ca165e98459a98074fcde33a1be6e4db5d9de086cb750596b4ccb301d0ea2fbd (2024) |
| hybrid_rerank | 10 | chk_7b196f2a1bb3de83e990718ad5da80dca1f369bdb8fb59b0c2f1203abe5c6d9e | CVX | 10-K | 2023 | FY | 1A | 0000093410-24-000013 |  |  | 0.415 | chk_2e42a141227b8454615289e6151bda550c82b80567b9409f9d3a4ce109038a6b (2024) |

vector: 1/10 different-filing near-duplicate slots; 2/10 exact gold slots.
hybrid_rerank: 1/10 different-filing near-duplicate slots; 1/10 exact gold slots.

#### XOM: How does ExxonMobil's 2024 10-K say greenhouse gas regulations could hurt its business?

ID: `hq_efbdb0ea523543c699eddddde9b1e638`.

| Mode | Rank | Chunk ID | Ticker | Form | FY | Period | Item | Accession | Gold | Near-duplicate | Overlap | Closest gold ID (FY) |
|---|---:|---|---|---|---:|---|---|---|---|---|---:|---|
| vector | 1 | chk_eea70ba0be2090b21c722ac487fb0b38efc7a9d9099114ee1c5153e0cab0f1ba | XOM | 10-Q | 2026 | Q1 | P1-2 | 0000034088-26-000067 |  |  | 0.000 | chk_812e34aefe833a28bedff5421948f44e74b61ca900c4e6358a1015c3c3c67472 (2024) |
| vector | 2 | chk_9f13b4edaf750b4780b8d96532d539568031f21ae2134c723ef862e1728d7499 | XOM | 10-Q | 2024 | Q3 | P1-2 | 0000034088-24-000068 |  |  | 0.000 | chk_812e34aefe833a28bedff5421948f44e74b61ca900c4e6358a1015c3c3c67472 (2024) |
| vector | 3 | chk_31fbf94a4240e0669e13bf4336b361ff7ec5807a349d510207c1e7e7e9827f49 | XOM | 10-Q | 2023 | Q3 | P1-2 | 0000034088-23-000056 |  |  | 0.000 | chk_812e34aefe833a28bedff5421948f44e74b61ca900c4e6358a1015c3c3c67472 (2024) |
| vector | 4 | chk_6970eb1f962972b11aaaf5ef77560bed7e8f590cd391bc4600f54e22a9e103e1 | XOM | 10-Q | 2024 | Q2 | P1-2 | 0000034088-24-000050 |  |  | 0.000 | chk_812e34aefe833a28bedff5421948f44e74b61ca900c4e6358a1015c3c3c67472 (2024) |
| vector | 5 | chk_d711a9ba0413452211503b233eaadb715b5ac5400f1b3d8a6e153dc1edfe4d6e | XOM | 10-Q | 2023 | Q1 | P1-2 | 0000034088-23-000030 |  |  | 0.000 | chk_812e34aefe833a28bedff5421948f44e74b61ca900c4e6358a1015c3c3c67472 (2024) |
| vector | 6 | chk_51634eab6851091e38cae9fc52bc8f3484b70f9fcc4659a0653a1a27aaf089d3 | XOM | 10-Q | 2026 | Q2 | P1-2 | 0000034088-26-000093 |  |  | 0.000 | chk_812e34aefe833a28bedff5421948f44e74b61ca900c4e6358a1015c3c3c67472 (2024) |
| vector | 7 | chk_729b354107df0251aa52b7d7a563289d73a276efc608c5462ef984baba38de80 | XOM | 10-Q | 2024 | Q1 | P1-2 | 0000034088-24-000029 |  |  | 0.000 | chk_812e34aefe833a28bedff5421948f44e74b61ca900c4e6358a1015c3c3c67472 (2024) |
| vector | 8 | chk_2ad95fd8c6c87831b3e0ca16d9cda538888fcda9f410e7298b8465f952e12395 | XOM | 10-Q | 2024 | Q1 | P1-2 | 0000034088-24-000029 |  |  | 0.000 | chk_812e34aefe833a28bedff5421948f44e74b61ca900c4e6358a1015c3c3c67472 (2024) |
| vector | 9 | chk_29ec7eeaee73372754dc1fbc549336ccddb8e78fc7026d58cad03d809d01608d | XOM | 10-Q | 2025 | Q2 | P1-2 | 0000034088-25-000042 |  |  | 0.000 | chk_812e34aefe833a28bedff5421948f44e74b61ca900c4e6358a1015c3c3c67472 (2024) |
| vector | 10 | chk_45a7a4f2b62d3a45d39c39acca1f86425502bbbb4875669e33fd9f60f9005517 | XOM | 10-Q | 2024 | Q2 | P1-2 | 0000034088-24-000050 |  |  | 0.000 | chk_812e34aefe833a28bedff5421948f44e74b61ca900c4e6358a1015c3c3c67472 (2024) |
| hybrid_rerank | 1 | chk_31fbf94a4240e0669e13bf4336b361ff7ec5807a349d510207c1e7e7e9827f49 | XOM | 10-Q | 2023 | Q3 | P1-2 | 0000034088-23-000056 |  |  | 0.000 | chk_812e34aefe833a28bedff5421948f44e74b61ca900c4e6358a1015c3c3c67472 (2024) |
| hybrid_rerank | 2 | chk_0def04fd41c886cd0ad994d0f35b39d6784e80a8adbe54e82f3d6e3ca28ac35d | XOM | 10-K | 2023 | FY | 1A | 0000034088-24-000018 |  | yes | 0.895 | chk_812e34aefe833a28bedff5421948f44e74b61ca900c4e6358a1015c3c3c67472 (2024) |
| hybrid_rerank | 3 | chk_45c8a9823ca49e2843ba1865a3be4afc9ad02d963696a77cf7c160684735e84a | XOM | 10-K | 2025 | FY | 1A | 0000034088-26-000045 |  | yes | 0.803 | chk_812e34aefe833a28bedff5421948f44e74b61ca900c4e6358a1015c3c3c67472 (2024) |
| hybrid_rerank | 4 | chk_51634eab6851091e38cae9fc52bc8f3484b70f9fcc4659a0653a1a27aaf089d3 | XOM | 10-Q | 2026 | Q2 | P1-2 | 0000034088-26-000093 |  |  | 0.000 | chk_812e34aefe833a28bedff5421948f44e74b61ca900c4e6358a1015c3c3c67472 (2024) |
| hybrid_rerank | 5 | chk_812e34aefe833a28bedff5421948f44e74b61ca900c4e6358a1015c3c3c67472 | XOM | 10-K | 2024 | FY | 1A | 0000034088-25-000010 | yes |  | 0.000 | — |
| hybrid_rerank | 6 | chk_eea70ba0be2090b21c722ac487fb0b38efc7a9d9099114ee1c5153e0cab0f1ba | XOM | 10-Q | 2026 | Q1 | P1-2 | 0000034088-26-000067 |  |  | 0.000 | chk_812e34aefe833a28bedff5421948f44e74b61ca900c4e6358a1015c3c3c67472 (2024) |
| hybrid_rerank | 7 | chk_b193eb369b4e482dc493f325e124a79d06760431d3bda658d98d0617d5152a91 | XOM | 10-K | 2023 | FY | 1 | 0000034088-24-000018 |  |  | 0.000 | chk_812e34aefe833a28bedff5421948f44e74b61ca900c4e6358a1015c3c3c67472 (2024) |
| hybrid_rerank | 8 | chk_20e5c1a19ed034a5bef820b3a8a1a1b24b1288b68667dc3685862e47da068f6e | XOM | 10-K | 2025 | FY | 1A | 0000034088-26-000045 |  | yes | 0.860 | chk_1ea144a75680dadeb996edae28f608ef198c4ae2083cb74d96392b12b51d6726 (2024) |
| hybrid_rerank | 9 | chk_cec1bcd97752e52d24c80a4bebafb0c14f00f6db7f531243b0cd52a42c86d99a | XOM | 10-K | 2023 | FY | 1 | 0000034088-24-000018 |  |  | 0.009 | chk_1ea144a75680dadeb996edae28f608ef198c4ae2083cb74d96392b12b51d6726 (2024) |
| hybrid_rerank | 10 | chk_79f1a3b6352852180da6cca33808189769faa5f67121057bb70f4823b8c9e9db | XOM | 10-K | 2024 | FY | 1A | 0000034088-25-000010 |  |  | 0.000 | — |

vector: 0/10 different-filing near-duplicate slots; 0/10 exact gold slots.
hybrid_rerank: 3/10 different-filing near-duplicate slots; 1/10 exact gold slots.

vector: 5/60 top-10 slots are different-filing near-duplicates. 2 cross-year questions have no exact gold in the top 10; 0 of those have at least five near-duplicate slots.

hybrid_rerank: 7/60 top-10 slots are different-filing near-duplicates. 0 cross-year questions have no exact gold in the top 10; 0 of those have at least five near-duplicate slots.

XOM greenhouse-gas first-gold ranks after the fix: vector=>30, keyword=8, hybrid=18, hybrid_rerank=5. It is no longer a miss in every mode. The overlap heuristic flags no different-filing near-duplicates in its vector top 10; wrong-year near-duplicates therefore do not explain that vector miss under this rule. Across the six questions, the measured near-duplicate counts do not support attributing most cross-year misses to near-duplicates. This does not classify the relevance of unjudged passages.

These counts show the measured extent of wrong-filing overlap, not that every cross-year miss is a year-disambiguation error. Unflagged results can still be topically relevant; high overlap does not prove answer equivalence. Period resolution is the **M4 planner's responsibility**.

### JNJ/XOM quarterly risk source check (cached HTML only)

All 22 raw bodies were read locally and SHA-256 checked against the frozen document provenance. No SEC client/network call or ingestion parser was invoked. Every file has one Item 1A mention, inside a prose reference to the annual 10-K's risk factors; none contains a separate quarterly Item 1A risk section. Thus these 22 empty corpus slots reflect source absence, not missed quarterly risk headings. The annual references need explicit availability/provenance handling in a future corpus rather than invented quarterly text.

| Ticker | FY | Quarter | Accession | Cached-source finding |
|---|---:|---|---|---|
| JNJ | 2023 | Q1 | 0000200406-23-000056 | No quarterly Item 1A; annual 10-K reference only |
| JNJ | 2023 | Q2 | 0000200406-23-000082 | No quarterly Item 1A; annual 10-K reference only |
| JNJ | 2023 | Q3 | 0000200406-23-000102 | No quarterly Item 1A; annual 10-K reference only |
| JNJ | 2024 | Q1 | 0000200406-24-000049 | No quarterly Item 1A; annual 10-K reference only |
| JNJ | 2024 | Q2 | 0000200406-24-000075 | No quarterly Item 1A; annual 10-K reference only |
| JNJ | 2024 | Q3 | 0000200406-24-000096 | No quarterly Item 1A; annual 10-K reference only |
| JNJ | 2025 | Q1 | 0000200406-25-000119 | No quarterly Item 1A; annual 10-K reference only |
| JNJ | 2025 | Q2 | 0000200406-25-000178 | No quarterly Item 1A; annual 10-K reference only |
| JNJ | 2025 | Q3 | 0000200406-25-000209 | No quarterly Item 1A; annual 10-K reference only |
| JNJ | 2026 | Q1 | 0000200406-26-000087 | No quarterly Item 1A; annual 10-K reference only |
| JNJ | 2026 | Q2 | 0000200406-26-000153 | No quarterly Item 1A; annual 10-K reference only |
| XOM | 2023 | Q1 | 0000034088-23-000030 | No quarterly Item 1A; annual 10-K reference only |
| XOM | 2023 | Q2 | 0000034088-23-000048 | No quarterly Item 1A; annual 10-K reference only |
| XOM | 2023 | Q3 | 0000034088-23-000056 | No quarterly Item 1A; annual 10-K reference only |
| XOM | 2024 | Q1 | 0000034088-24-000029 | No quarterly Item 1A; annual 10-K reference only |
| XOM | 2024 | Q2 | 0000034088-24-000050 | No quarterly Item 1A; annual 10-K reference only |
| XOM | 2024 | Q3 | 0000034088-24-000068 | No quarterly Item 1A; annual 10-K reference only |
| XOM | 2025 | Q1 | 0000034088-25-000024 | No quarterly Item 1A; annual 10-K reference only |
| XOM | 2025 | Q2 | 0000034088-25-000042 | No quarterly Item 1A; annual 10-K reference only |
| XOM | 2025 | Q3 | 0000034088-25-000061 | No quarterly Item 1A; annual 10-K reference only |
| XOM | 2026 | Q1 | 0000034088-26-000067 | No quarterly Item 1A; annual 10-K reference only |
| XOM | 2026 | Q2 | 0000034088-26-000093 | No quarterly Item 1A; annual 10-K reference only |

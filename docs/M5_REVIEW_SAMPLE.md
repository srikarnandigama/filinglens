# M5 Phase B: gold review sample (20 draft questions)

Draft `evals/questions_v1.draft.jsonl` (not frozen). Picked by SHA-256 of `review-20261109|<id>`, 3 per template (2 for multi_step), with swaps so the sample covers ≥4 after-cutoff, ≥2 restated, ≥1 EPS and ≥2 bank questions. Each gold was recomputed here independently from its listed inputs with Decimal; the *Check* line shows the result. Values are raw XBRL units (USD, not millions).

Items 16-18 were replaced on 2026-11-09 after comparisons became same-sector only (D101); the
other 17 items are unchanged. The new three, again in `review-20261109` hash order, are the first
after-cutoff comparison and the first two restated comparisons (one of them the bank pair).

Please verify each gold against the SEC filing linked beside each input. The linked filing is
the M1 source of the stored fact, which is often a later filing's prior-period column (e.g.
JPM FY2024 net income comes from the FY2025 10-K). *First filed* in the fairness line is the
earliest filing that reported each input (from the frozen companyfacts JSON). For restated
questions, `gold_as_first_reported` is what the gold would be on the originally filed values.
The gold always uses the stored (latest) values.

## 1. lookup · `q_50b3a95c094c89e8` · test · sample_100

**Q:** What was Disney's total revenue in fiscal Q3 2026?

**Gold:** 25248000000 USD · tolerance {"kind": "relative", "value": "0.005"}

**Fact IDs:** 3875 · **Formula:** `fact value`

**Fairness:** cutoff after (first filed 2026-08-05)

| Fact | Ticker | Metric | Period | Value | Concept | Filing |
|---|---|---|---|---|---|---|
| 3875 | DIS | revenue | Q3 2026 (2026-03-29 to 2026-06-27) | 25,248,000,000 | Revenues | [0001744489-26-000057](https://www.sec.gov/Archives/edgar/data/1744489/000174448926000057/dis-20260627.htm) filed 2026-08-05 |

**Check:** 25248000000 = 25,248,000,000 → matches gold

## 2. lookup · `q_ec5863361bd969ec` · dev

**Q:** What was JPMorgan Chase's net income in fiscal 2024?

**Gold:** 58471000000 USD · tolerance {"kind": "relative", "value": "0.005"}

**Fact IDs:** 1146 · **Formula:** `fact value`

**Fairness:** cutoff before (first filed 2025-02-14)

| Fact | Ticker | Metric | Period | Value | Concept | Filing |
|---|---|---|---|---|---|---|
| 1146 | JPM | net_income | FY 2024 (2024-01-01 to 2024-12-31) | 58,471,000,000 | NetIncomeLoss | [0001628280-26-008131](https://www.sec.gov/Archives/edgar/data/19617/000162828026008131/jpm-20251231.htm) filed 2026-02-13 |

**Check:** 58471000000 = 58,471,000,000 → matches gold

## 3. lookup · `q_55a4f1bc7a9dd8c1` · test

**Q:** What was Disney's diluted earnings per share in fiscal Q1 2026?

**Gold:** 1.34 USD/shares · tolerance {"absolute": "0.005", "kind": "eps", "relative": "0.005"}

**Fact IDs:** 3924 · **Formula:** `fact value`

**Fairness:** cutoff before (first filed 2026-02-02)

| Fact | Ticker | Metric | Period | Value | Concept | Filing |
|---|---|---|---|---|---|---|
| 3924 | DIS | eps_diluted | Q1 2026 (2025-09-28 to 2025-12-27) | 1.34 | EarningsPerShareDiluted | [0001744489-26-000019](https://www.sec.gov/Archives/edgar/data/1744489/000174448926000019/dis-20251227.htm) filed 2026-02-02 |

**Check:** 1.34 = 1.340000000000 → matches gold

## 4. yoy_growth · `q_719c211db302d547` · dev

**Q:** By what percent did Alphabet's capital expenditures change from fiscal 2024 to fiscal 2025?

**Gold:** 74.068716094033 percent · tolerance {"kind": "absolute", "value": "0.1"}

**Fact IDs:** 632, 637 · **Formula:** `(FY - FY_prev) / FY_prev * 100`

**Fairness:** cutoff before (first filed 2026-02-05)

| Fact | Ticker | Metric | Period | Value | Concept | Filing |
|---|---|---|---|---|---|---|
| 632 | GOOGL | capex | FY 2024 (2024-01-01 to 2024-12-31) | 52,535,000,000 | PaymentsToAcquirePropertyPlantAndEquipment | [0001652044-26-000018](https://www.sec.gov/Archives/edgar/data/1652044/000165204426000018/goog-20251231.htm) filed 2026-02-05 |
| 637 | GOOGL | capex | FY 2025 (2025-01-01 to 2025-12-31) | 91,447,000,000 | PaymentsToAcquirePropertyPlantAndEquipment | [0001652044-26-000018](https://www.sec.gov/Archives/edgar/data/1652044/000165204426000018/goog-20251231.htm) filed 2026-02-05 |

**Check:** (91447000000 − 52535000000) / 52535000000 × 100 = 74.068716094033 → matches gold

## 5. yoy_growth · `q_a3e48fcf36b41d1f` · dev

**Q:** By what percent did Alphabet's operating income change from fiscal 2023 to fiscal 2024?

**Gold:** 33.332542441247 percent · tolerance {"kind": "absolute", "value": "0.1"}

**Fact IDs:** 545, 550 · **Formula:** `(FY - FY_prev) / FY_prev * 100`

**Fairness:** cutoff before (first filed 2025-02-05)

| Fact | Ticker | Metric | Period | Value | Concept | Filing |
|---|---|---|---|---|---|---|
| 545 | GOOGL | operating_income | FY 2023 (2023-01-01 to 2023-12-31) | 84,293,000,000 | OperatingIncomeLoss | [0001652044-26-000018](https://www.sec.gov/Archives/edgar/data/1652044/000165204426000018/goog-20251231.htm) filed 2026-02-05 |
| 550 | GOOGL | operating_income | FY 2024 (2024-01-01 to 2024-12-31) | 112,390,000,000 | OperatingIncomeLoss | [0001652044-26-000018](https://www.sec.gov/Archives/edgar/data/1652044/000165204426000018/goog-20251231.htm) filed 2026-02-05 |

**Check:** (112390000000 − 84293000000) / 84293000000 × 100 = 33.332542441247 → matches gold

## 6. yoy_growth · `q_07f498bc944afa95` · dev

**Q:** By what percent did ExxonMobil's capital expenditures change from fiscal 2024 to fiscal 2025?

**Gold:** 16.67078087715 percent · tolerance {"kind": "absolute", "value": "0.1"}

**Fact IDs:** 2628, 2633 · **Formula:** `(FY - FY_prev) / FY_prev * 100`

**Fairness:** cutoff before (first filed 2026-02-18)

| Fact | Ticker | Metric | Period | Value | Concept | Filing |
|---|---|---|---|---|---|---|
| 2628 | XOM | capex | FY 2024 (2024-01-01 to 2024-12-31) | 24,306,000,000 | PaymentsToAcquirePropertyPlantAndEquipment | [0000034088-26-000045](https://www.sec.gov/Archives/edgar/data/34088/000003408826000045/xom-20251231.htm) filed 2026-02-18 |
| 2633 | XOM | capex | FY 2025 (2025-01-01 to 2025-12-31) | 28,358,000,000 | PaymentsToAcquirePropertyPlantAndEquipment | [0000034088-26-000045](https://www.sec.gov/Archives/edgar/data/34088/000003408826000045/xom-20251231.htm) filed 2026-02-18 |

**Check:** (28358000000 − 24306000000) / 24306000000 × 100 = 16.670780877150 → matches gold

## 7. margin · `q_ebb237b5a45f0463` · test · sample_100

**Q:** What was Nvidia's operating margin in fiscal Q2 2027?

**Gold:** 66.237100009353 percent · tolerance {"kind": "absolute", "value": "0.1"}

**Fact IDs:** 413, 362 · **Formula:** `operating_income / revenue * 100`

**Fairness:** cutoff after (first filed 2026-08-26)

| Fact | Ticker | Metric | Period | Value | Concept | Filing |
|---|---|---|---|---|---|---|
| 413 | NVDA | operating_income | Q2 2027 (2026-04-27 to 2026-07-26) | 63,734,000,000 | OperatingIncomeLoss | [0001045810-26-000075](https://www.sec.gov/Archives/edgar/data/1045810/000104581026000075/nvda-20260726.htm) filed 2026-08-26 |
| 362 | NVDA | revenue | Q2 2027 (2026-04-27 to 2026-07-26) | 96,221,000,000 | Revenues | [0001045810-26-000075](https://www.sec.gov/Archives/edgar/data/1045810/000104581026000075/nvda-20260726.htm) filed 2026-08-26 |

**Check:** 63734000000 / 96221000000 × 100 = 66.237100009353 → matches gold

## 8. margin · `q_b69515396d29fd65` · dev

**Q:** What was Apple's gross margin in fiscal Q2 2024?

**Gold:** 46.578074554009 percent · tolerance {"kind": "absolute", "value": "0.1"}

**Fact IDs:** 43, 7 · **Formula:** `gross_profit / revenue * 100`

**Fairness:** cutoff before (first filed 2024-05-03)

| Fact | Ticker | Metric | Period | Value | Concept | Filing |
|---|---|---|---|---|---|---|
| 43 | AAPL | gross_profit | Q2 2024 (2023-12-31 to 2024-03-30) | 42,271,000,000 | GrossProfit | [0000320193-25-000057](https://www.sec.gov/Archives/edgar/data/320193/000032019325000057/aapl-20250329.htm) filed 2025-05-02 |
| 7 | AAPL | revenue | Q2 2024 (2023-12-31 to 2024-03-30) | 90,753,000,000 | RevenueFromContractWithCustomerExcludingAssessedTax | [0000320193-25-000057](https://www.sec.gov/Archives/edgar/data/320193/000032019325000057/aapl-20250329.htm) filed 2025-05-02 |

**Check:** 42271000000 / 90753000000 × 100 = 46.578074554009 → matches gold

## 9. margin · `q_99055888c1ea59a9` · test

**Q:** What was Costco's net margin in fiscal Q3 2025?

**Gold:** 3.010837750178 percent · tolerance {"kind": "absolute", "value": "0.1"}

**Fact IDs:** 3381, 3336 · **Formula:** `net_income / revenue * 100`

**Fairness:** cutoff before (first filed 2025-06-05)

| Fact | Ticker | Metric | Period | Value | Concept | Filing |
|---|---|---|---|---|---|---|
| 3381 | COST | net_income | Q3 2025 (2025-02-17 to 2025-05-11) | 1,903,000,000 | NetIncomeLoss | [0000909832-26-000051](https://www.sec.gov/Archives/edgar/data/909832/000090983226000051/cost-20260510.htm) filed 2026-06-03 |
| 3336 | COST | revenue | Q3 2025 (2025-02-17 to 2025-05-11) | 63,205,000,000 | Revenues | [0000909832-25-000033](https://www.sec.gov/Archives/edgar/data/909832/000090983225000033/cost-20250511.htm) filed 2025-06-05 |

**Check:** 1903000000 / 63205000000 × 100 = 3.010837750178 → matches gold

## 10. trend_avg · `q_7e6a29205402ddfc` · test

**Q:** What was Procter & Gamble's average quarterly operating income over fiscal 2026?

**Gold:** 4937000000 USD · tolerance {"kind": "relative", "value": "0.005"}

**Fact IDs:** 3646, 3647, 3648, 3649 · **Formula:** `(Q1 + Q2 + Q3 + Q4) / 4`

**Fairness:** cutoff after (first filed 2026-08-04); uses a derived quarter

| Fact | Ticker | Metric | Period | Value | Concept | Filing |
|---|---|---|---|---|---|---|
| 3646 | PG | operating_income | Q1 2026 (2025-07-01 to 2025-09-30) | 5,856,000,000 | OperatingIncomeLoss | [0000080424-25-000245](https://www.sec.gov/Archives/edgar/data/80424/000008042425000245/pg-20250930.htm) filed 2025-10-24 |
| 3647 | PG | operating_income | Q2 2026 (2025-10-01 to 2025-12-31) | 5,366,000,000 | OperatingIncomeLoss | [0000080424-26-000011](https://www.sec.gov/Archives/edgar/data/80424/000008042426000011/pg-20251231.htm) filed 2026-01-23 |
| 3648 | PG | operating_income | Q3 2026 (2026-01-01 to 2026-03-31) | 4,576,000,000 | OperatingIncomeLoss | [0000080424-26-000060](https://www.sec.gov/Archives/edgar/data/80424/000008042426000060/pg-20260331.htm) filed 2026-04-24 |
| 3649 (derived) | PG | operating_income | Q4 2026 (2026-04-01 to 2026-06-30) | 3,950,000,000 | OperatingIncomeLoss | [0000080424-26-000103](https://www.sec.gov/Archives/edgar/data/80424/000008042426000103/pg-20260630.htm) filed 2026-08-04 |
| ↳ + | | | 2025-07-01 to 2026-06-30 | 19,748,000,000 | OperatingIncomeLoss | [0000080424-26-000103](https://www.sec.gov/Archives/edgar/data/80424/000008042426000103/pg-20260630.htm) filed 2026-08-04 |
| ↳ − | | | 2025-07-01 to 2026-03-31 | 15,798,000,000 | OperatingIncomeLoss | [0000080424-26-000060](https://www.sec.gov/Archives/edgar/data/80424/000008042426000060/pg-20260331.htm) filed 2026-04-24 |

**Check:** (5856000000 + 5366000000 + 4576000000 + 3950000000) / 4 = 4,937,000,000 → matches gold

## 11. trend_avg · `q_9b611ababa06a3f4` · test

**Q:** What was JPMorgan Chase's average quarterly net income over fiscal 2023?

**Gold:** 12388000000 USD · tolerance {"kind": "relative", "value": "0.005"}

**Fact IDs:** 1137, 1138, 1139, 1140 · **Formula:** `(Q1 + Q2 + Q3 + Q4) / 4`

**Fairness:** cutoff before (first filed 2024-02-16); uses a derived quarter

| Fact | Ticker | Metric | Period | Value | Concept | Filing |
|---|---|---|---|---|---|---|
| 1137 | JPM | net_income | Q1 2023 (2023-01-01 to 2023-03-31) | 12,622,000,000 | NetIncomeLoss | [0000019617-24-000326](https://www.sec.gov/Archives/edgar/data/19617/000001961724000326/jpm-20240331.htm) filed 2024-05-01 |
| 1138 | JPM | net_income | Q2 2023 (2023-04-01 to 2023-06-30) | 14,472,000,000 | NetIncomeLoss | [0000019617-24-000453](https://www.sec.gov/Archives/edgar/data/19617/000001961724000453/jpm-20240630.htm) filed 2024-08-02 |
| 1139 | JPM | net_income | Q3 2023 (2023-07-01 to 2023-09-30) | 13,151,000,000 | NetIncomeLoss | [0000019617-24-000611](https://www.sec.gov/Archives/edgar/data/19617/000001961724000611/jpm-20240930.htm) filed 2024-10-30 |
| 1140 (derived) | JPM | net_income | Q4 2023 (2023-10-01 to 2023-12-31) | 9,307,000,000 | NetIncomeLoss | [0001628280-26-008131](https://www.sec.gov/Archives/edgar/data/19617/000162828026008131/jpm-20251231.htm) filed 2026-02-13 |
| ↳ + | | | 2023-01-01 to 2023-12-31 | 49,552,000,000 | NetIncomeLoss | [0001628280-26-008131](https://www.sec.gov/Archives/edgar/data/19617/000162828026008131/jpm-20251231.htm) filed 2026-02-13 |
| ↳ − | | | 2023-01-01 to 2023-09-30 | 40,245,000,000 | NetIncomeLoss | [0000019617-24-000611](https://www.sec.gov/Archives/edgar/data/19617/000001961724000611/jpm-20240930.htm) filed 2024-10-30 |

**Check:** (12622000000 + 14472000000 + 13151000000 + 9307000000) / 4 = 12,388,000,000 → matches gold

## 12. trend_avg · `q_06c343659e5d6150` · test

**Q:** What was Nvidia's average quarterly gross profit over fiscal 2024?

**Gold:** 11075250000 USD · tolerance {"kind": "relative", "value": "0.005"}

**Fact IDs:** 380, 381, 382, 383 · **Formula:** `(Q1 + Q2 + Q3 + Q4) / 4`

**Fairness:** cutoff before (first filed 2024-02-21); uses a derived quarter

| Fact | Ticker | Metric | Period | Value | Concept | Filing |
|---|---|---|---|---|---|---|
| 380 | NVDA | gross_profit | Q1 2024 (2023-01-30 to 2023-04-30) | 4,648,000,000 | GrossProfit | [0001045810-24-000124](https://www.sec.gov/Archives/edgar/data/1045810/000104581024000124/nvda-20240428.htm) filed 2024-05-29 |
| 381 | NVDA | gross_profit | Q2 2024 (2023-05-01 to 2023-07-30) | 9,462,000,000 | GrossProfit | [0001045810-24-000264](https://www.sec.gov/Archives/edgar/data/1045810/000104581024000264/nvda-20240728.htm) filed 2024-08-28 |
| 382 | NVDA | gross_profit | Q3 2024 (2023-07-31 to 2023-10-29) | 13,400,000,000 | GrossProfit | [0001045810-24-000316](https://www.sec.gov/Archives/edgar/data/1045810/000104581024000316/nvda-20241027.htm) filed 2024-11-20 |
| 383 (derived) | NVDA | gross_profit | Q4 2024 (2023-10-30 to 2024-01-28) | 16,791,000,000 | GrossProfit | [0001045810-26-000021](https://www.sec.gov/Archives/edgar/data/1045810/000104581026000021/nvda-20260125.htm) filed 2026-02-25 |
| ↳ + | | | 2023-01-30 to 2024-01-28 | 44,301,000,000 | GrossProfit | [0001045810-26-000021](https://www.sec.gov/Archives/edgar/data/1045810/000104581026000021/nvda-20260125.htm) filed 2026-02-25 |
| ↳ − | | | 2023-01-30 to 2023-10-29 | 27,510,000,000 | GrossProfit | [0001045810-24-000316](https://www.sec.gov/Archives/edgar/data/1045810/000104581024000316/nvda-20241027.htm) filed 2024-11-20 |

**Check:** (4648000000 + 9462000000 + 13400000000 + 16791000000) / 4 = 11,075,250,000 → matches gold

## 13. derived_q4 · `q_9ddf5aa99143fa50` · dev

**Q:** What was Procter & Gamble's capital expenditures in fiscal Q4 2026?

**Gold:** 1023000000 USD · tolerance {"kind": "relative", "value": "0.005"}

**Fact IDs:** 3709 · **Formula:** `derived Q4 = FY - 9M (stored derivation)`

**Fairness:** cutoff after (first filed 2026-08-04); uses a derived quarter

| Fact | Ticker | Metric | Period | Value | Concept | Filing |
|---|---|---|---|---|---|---|
| 3709 (derived) | PG | capex | Q4 2026 (2026-04-01 to 2026-06-30) | 1,023,000,000 | PaymentsToAcquirePropertyPlantAndEquipment | [0000080424-26-000103](https://www.sec.gov/Archives/edgar/data/80424/000008042426000103/pg-20260630.htm) filed 2026-08-04 |
| ↳ + | | | 2025-07-01 to 2026-06-30 | 4,409,000,000 | PaymentsToAcquirePropertyPlantAndEquipment | [0000080424-26-000103](https://www.sec.gov/Archives/edgar/data/80424/000008042426000103/pg-20260630.htm) filed 2026-08-04 |
| ↳ − | | | 2025-07-01 to 2026-03-31 | 3,386,000,000 | PaymentsToAcquirePropertyPlantAndEquipment | [0000080424-26-000060](https://www.sec.gov/Archives/edgar/data/80424/000008042426000060/pg-20260331.htm) filed 2026-04-24 |

**Check:** 1023000000 = 1,023,000,000 → matches gold

## 14. derived_q4 · `q_bc98a60bc7ccfd6a` · test · sample_100

**Q:** What was Nike's cost of revenue in fiscal Q4 2026?

**Gold:** 5579000000 USD · tolerance {"kind": "relative", "value": "0.005"}

**Fact IDs:** 3752 · **Formula:** `derived Q4 = FY - 9M (stored derivation)`

**Fairness:** cutoff after (first filed 2026-07-15); uses a derived quarter

| Fact | Ticker | Metric | Period | Value | Concept | Filing |
|---|---|---|---|---|---|---|
| 3752 (derived) | NKE | cost_of_revenue | Q4 2026 (2026-03-01 to 2026-05-31) | 5,579,000,000 | CostOfGoodsAndServicesSold | [0000320187-26-000088](https://www.sec.gov/Archives/edgar/data/320187/000032018726000088/nke-20260531.htm) filed 2026-07-15 |
| ↳ + | | | 2025-06-01 to 2026-05-31 | 26,487,000,000 | CostOfGoodsAndServicesSold | [0000320187-26-000088](https://www.sec.gov/Archives/edgar/data/320187/000032018726000088/nke-20260531.htm) filed 2026-07-15 |
| ↳ − | | | 2025-06-01 to 2026-02-28 | 20,908,000,000 | CostOfGoodsAndServicesSold | [0000320187-26-000037](https://www.sec.gov/Archives/edgar/data/320187/000032018726000037/nke-20260228.htm) filed 2026-04-01 |

**Check:** 5579000000 = 5,579,000,000 → matches gold

## 15. derived_q4 · `q_86d025b5a2decba6` · dev

**Q:** What was Nvidia's net income in fiscal Q4 2024?

**Gold:** 12285000000 USD · tolerance {"kind": "relative", "value": "0.005"}

**Fact IDs:** 417 · **Formula:** `derived Q4 = FY - 9M (stored derivation)`

**Fairness:** cutoff before (first filed 2024-02-21); uses a derived quarter

| Fact | Ticker | Metric | Period | Value | Concept | Filing |
|---|---|---|---|---|---|---|
| 417 (derived) | NVDA | net_income | Q4 2024 (2023-10-30 to 2024-01-28) | 12,285,000,000 | NetIncomeLoss | [0001045810-26-000021](https://www.sec.gov/Archives/edgar/data/1045810/000104581026000021/nvda-20260125.htm) filed 2026-02-25 |
| ↳ + | | | 2023-01-30 to 2024-01-28 | 29,760,000,000 | NetIncomeLoss | [0001045810-26-000021](https://www.sec.gov/Archives/edgar/data/1045810/000104581026000021/nvda-20260125.htm) filed 2026-02-25 |
| ↳ − | | | 2023-01-30 to 2023-10-29 | 17,475,000,000 | NetIncomeLoss | [0001045810-24-000316](https://www.sec.gov/Archives/edgar/data/1045810/000104581024000316/nvda-20241027.htm) filed 2024-11-20 |

**Check:** 12285000000 = 12,285,000,000 → matches gold

## 16. comparison · `q_7b7fc1c8e8167d73` · test · sample_100

**Q:** Which had the higher net margin in fiscal 2026, Procter & Gamble or Costco, and by how many percentage points?

**Gold:** 15.393559064054 percentage_points · choice **PG** · tolerance {"kind": "absolute", "value": "0.1"}

**Fact IDs:** 3665, 3620, 3388, 3343 · **Formula:** `|net_income_A / revenue_A - net_income_B / revenue_B| * 100`

**Fairness:** cutoff after (first filed 2026-10-07)

| Fact | Ticker | Metric | Period | Value | Concept | Filing |
|---|---|---|---|---|---|---|
| 3665 | PG | net_income | FY 2026 (2025-07-01 to 2026-06-30) | 16,046,000,000 | NetIncomeLoss | [0000080424-26-000103](https://www.sec.gov/Archives/edgar/data/80424/000008042426000103/pg-20260630.htm) filed 2026-08-04 |
| 3620 | PG | revenue | FY 2026 (2025-07-01 to 2026-06-30) | 87,032,000,000 | Revenues | [0000080424-26-000103](https://www.sec.gov/Archives/edgar/data/80424/000008042426000103/pg-20260630.htm) filed 2026-08-04 |
| 3388 | COST | net_income | FY 2026 (2025-09-01 to 2026-08-30) | 9,226,000,000 | NetIncomeLoss | [0000909832-26-000093](https://www.sec.gov/Archives/edgar/data/909832/000090983226000093/cost-20260830.htm) filed 2026-10-07 |
| 3343 | COST | revenue | FY 2026 (2025-09-01 to 2026-08-30) | 303,154,000,000 | RevenueFromContractWithCustomerExcludingAssessedTax | [0000909832-26-000093](https://www.sec.gov/Archives/edgar/data/909832/000090983226000093/cost-20260830.htm) filed 2026-10-07 |

**Check:** |16046000000/87032000000 − 9226000000/303154000000| × 100 = |18.436897 − 3.043338| = 15.393559064054 → matches gold

## 17. comparison · `q_2f159af05209d800` · test

**Q:** Which had the higher net margin in fiscal 2023, JPMorgan Chase or Bank of America, and by how many percentage points?

**Gold:** 5.745155425797 percentage_points · choice **JPM** · tolerance {"kind": "absolute", "value": "0.1"}

**Fact IDs:** 1141, 1134, 1220, 1203 · **Formula:** `|net_income_A / revenue_A - net_income_B / revenue_B| * 100`

**Fairness:** cutoff before (first filed 2024-02-20); restated: {'changed_inputs': {'1203': {'first_reported': '98581000000', 'latest': '102769000000'}, '1220': {'first_reported': '26515000000', 'latest': '26305000000'}}, 'gold_as_first_reported': '4.444731879818'}

| Fact | Ticker | Metric | Period | Value | Concept | Filing |
|---|---|---|---|---|---|---|
| 1141 | JPM | net_income | FY 2023 (2023-01-01 to 2023-12-31) | 49,552,000,000 | NetIncomeLoss | [0001628280-26-008131](https://www.sec.gov/Archives/edgar/data/19617/000162828026008131/jpm-20251231.htm) filed 2026-02-13 |
| 1134 | JPM | revenue | FY 2023 (2023-01-01 to 2023-12-31) | 158,104,000,000 | Revenues | [0001628280-26-008131](https://www.sec.gov/Archives/edgar/data/19617/000162828026008131/jpm-20251231.htm) filed 2026-02-13 |
| 1220 | BAC | net_income | FY 2023 (2023-01-01 to 2023-12-31) | 26,305,000,000 | NetIncomeLoss | [0000070858-26-000157](https://www.sec.gov/Archives/edgar/data/70858/000007085826000157/bac-20251231.htm) filed 2026-02-25 |
| 1203 | BAC | revenue | FY 2023 (2023-01-01 to 2023-12-31) | 102,769,000,000 | Revenues | [0000070858-26-000157](https://www.sec.gov/Archives/edgar/data/70858/000007085826000157/bac-20251231.htm) filed 2026-02-25 |

**Check:** |49552000000/158104000000 − 26305000000/102769000000| × 100 = |31.341396 − 25.596240| = 5.745155425797 → matches gold

## 18. comparison · `q_c1ec0e6d4e01f775` · test

**Q:** Which had the higher net margin in fiscal 2023, UnitedHealth or Pfizer, and by how many percentage points?

**Gold:** 2.464342433401 percentage_points · choice **UNH** · tolerance {"kind": "absolute", "value": "0.1"}

**Fact IDs:** 3096, 3045, 2952, 2918 · **Formula:** `|net_income_A / revenue_A - net_income_B / revenue_B| * 100`

**Fairness:** cutoff before (first filed 2024-02-28); restated: {'changed_inputs': {'2918': {'first_reported': '58496000000', 'latest': '59553000000'}}, 'gold_as_first_reported': '2.400047591873'}

| Fact | Ticker | Metric | Period | Value | Concept | Filing |
|---|---|---|---|---|---|---|
| 3096 | UNH | net_income | FY 2023 (2023-01-01 to 2023-12-31) | 22,381,000,000 | NetIncomeLoss | [0000731766-26-000062](https://www.sec.gov/Archives/edgar/data/731766/000073176626000062/unh-20251231.htm) filed 2026-03-02 |
| 3045 | UNH | revenue | FY 2023 (2023-01-01 to 2023-12-31) | 371,622,000,000 | Revenues | [0000731766-26-000062](https://www.sec.gov/Archives/edgar/data/731766/000073176626000062/unh-20251231.htm) filed 2026-03-02 |
| 2952 | PFE | net_income | FY 2023 (2023-01-01 to 2023-12-31) | 2,119,000,000 | NetIncomeLoss | [0000078003-26-000026](https://www.sec.gov/Archives/edgar/data/78003/000007800326000026/pfe-20251231.htm) filed 2026-02-26 |
| 2918 | PFE | revenue | FY 2023 (2023-01-01 to 2023-12-31) | 59,553,000,000 | Revenues | [0000078003-26-000026](https://www.sec.gov/Archives/edgar/data/78003/000007800326000026/pfe-20251231.htm) filed 2026-02-26 |

**Check:** |22381000000/371622000000 − 2119000000/59553000000| × 100 = |6.022518 − 3.558175| = 2.464342433401 → matches gold

## 19. multi_step · `q_f9718b59d1a8f543` · test

**Q:** By what percent did Nike's gross profit change from fiscal Q1 2026 to fiscal Q4 2026?

**Gold:** 9.103783127655 percent · tolerance {"kind": "absolute", "value": "0.1"}

**Fact IDs:** 3765, 3768 · **Formula:** `(Q4_derived - Q1) / Q1 * 100`

**Fairness:** cutoff after (first filed 2026-07-15); uses a derived quarter

| Fact | Ticker | Metric | Period | Value | Concept | Filing |
|---|---|---|---|---|---|---|
| 3765 | NKE | gross_profit | Q1 2026 (2025-06-01 to 2025-08-31) | 4,943,000,000 | GrossProfit | [0000320187-26-000193](https://www.sec.gov/Archives/edgar/data/320187/000032018726000193/nke-20260831.htm) filed 2026-10-02 |
| 3768 (derived) | NKE | gross_profit | Q4 2026 (2026-03-01 to 2026-05-31) | 5,393,000,000 | GrossProfit | [0000320187-26-000088](https://www.sec.gov/Archives/edgar/data/320187/000032018726000088/nke-20260531.htm) filed 2026-07-15 |
| ↳ + | | | 2025-06-01 to 2026-05-31 | 19,911,000,000 | GrossProfit | [0000320187-26-000088](https://www.sec.gov/Archives/edgar/data/320187/000032018726000088/nke-20260531.htm) filed 2026-07-15 |
| ↳ − | | | 2025-06-01 to 2026-02-28 | 14,518,000,000 | GrossProfit | [0000320187-26-000037](https://www.sec.gov/Archives/edgar/data/320187/000032018726000037/nke-20260228.htm) filed 2026-04-01 |

**Check:** (5393000000 − 4943000000) / 4943000000 × 100 = 9.103783127655 → matches gold

## 20. multi_step · `q_3996fe54c6e8acb4` · dev

**Q:** By what percent did Disney's capital expenditures change from fiscal Q1 2023 to fiscal Q4 2023?

**Gold:** 16.342082980525 percent · tolerance {"kind": "absolute", "value": "0.1"}

**Fact IDs:** 3945, 3948 · **Formula:** `(Q4_derived - Q1) / Q1 * 100`

**Fairness:** cutoff before (first filed 2023-11-21); uses a derived quarter

| Fact | Ticker | Metric | Period | Value | Concept | Filing |
|---|---|---|---|---|---|---|
| 3945 | DIS | capex | Q1 2023 (2022-10-02 to 2022-12-31) | 1,181,000,000 | PaymentsToAcquirePropertyPlantAndEquipment | [0001744489-24-000081](https://www.sec.gov/Archives/edgar/data/1744489/000174448924000081/dis-20231230.htm) filed 2024-02-07 |
| 3948 (derived) | DIS | capex | Q4 2023 (2023-07-02 to 2023-09-30) | 1,374,000,000 | PaymentsToAcquirePropertyPlantAndEquipment | [0001744489-25-000155](https://www.sec.gov/Archives/edgar/data/1744489/000174448925000155/dis-20250927.htm) filed 2025-11-13 |
| ↳ + | | | 2022-10-02 to 2023-09-30 | 4,969,000,000 | PaymentsToAcquirePropertyPlantAndEquipment | [0001744489-25-000155](https://www.sec.gov/Archives/edgar/data/1744489/000174448925000155/dis-20250927.htm) filed 2025-11-13 |
| ↳ − | | | 2022-10-02 to 2023-07-01 | 3,595,000,000 | PaymentsToAcquirePropertyPlantAndEquipment | [0001744489-24-000232](https://www.sec.gov/Archives/edgar/data/1744489/000174448924000232/dis-20240629.htm) filed 2024-08-07 |

**Check:** (1374000000 − 1181000000) / 1181000000 × 100 = 16.342082980525 → matches gold

# Corpus v2: read-only ranking tie verification

The student's conditional acceptance check passed: zero unexplained changes.

Compared archived v1 and v2 rankings without calling retrieval, generating rankings, loading models or recomputing evaluation metrics. All SQL ran inside a repeatable-read, READ ONLY transaction. Stored passage text was compared exactly; accession, item and ordinal distinguish repeated text. The complete eligible passage/tsvector multiset is identical for each checked scope.

For every moved keyword passage, every intervening neighbor in both archived lists has the same exact PostgreSQL float4 score bytes. All 536 reversed passage pairs are exact ties. All 37 entering and 37 leaving passages share the cutoff tie score. Every archived keyword score matches a read-only ts_rank_cd recomputation, and each saved list follows score descending, chunk ID ascending. No tie-breaking change was made.

Of group (a)'s 28 questions, four have repaired sections in scope and are excluded (Chevron low prices, Disney DTC, NVIDIA export controls, ExxonMobil GHG). The other 24 are listed below. The two changed-label group (b) questions are also excluded.

| Checked questions | Changed keyword questions | Different text slots | Moved passages | Fully explained moves | Exceptions | Identical vector lists |
|---:|---:|---:|---:|---:|---:|---:|
| 24 | 24 | 467 | 504 | 504 | 0 | 24 |

A moved passage counts once per question, including each entrant and each departure separately; a changed slot counts once for a rank whose stored text differs. Entry/departure ranks in the JSON are null for outside the saved top 30. Thus 430 shared passages changed rank, plus 37 entrants and 37 departures = 504 movements; 430 + 37 = 467 changed slots.

| Version | Slots sharing an exact score in their list | Returned keyword slots | Fraction |
|---|---:|---:|---:|
| v1 | 752 | 877 | 85.75% |
| v2 | 750 | 877 | 85.52% |

Tie prevalence includes all 30 questions, counted within each list, using exact float4 bytes. Denominators use actual returned slots: Apple FY2025 Q3 tariff has 11 keyword matches (15 eligible chunks); question hq_eead0b7f7e3f430589800660cafe8cb1 has 26 keyword matches; the other 28 have 30. This is a tie prevalence statistic, not a new retrieval evaluation.

| Question ID | Question | Changed slots | Moved passages | Entering / leaving | Exact ties explain all | Vector text identical |
|---|---|---:|---:|---:|---|---|
| hq_05c3197fe2084357b5c9ca0582b713f2 | What restructuring plan did P&G announce in fiscal 2025, and why did it start it? | 19 | 22 | 3 / 3 | Yes | Yes |
| hq_19ea90a4eeb84991845ef0f0a3c4d316 | Why did Microsoft's cloud profit margins shrink in fiscal 2025 while cloud sales grew? | 19 | 19 | 0 / 0 | Yes | Yes |
| hq_21f4a3b2e4e044129aee7a3fa547a79b | Why did Nike's sales fall in fiscal 2025? | 19 | 20 | 1 / 1 | Yes | Yes |
| hq_24a3e4ca8e144f708dc1df755db10222 | How exposed is Amazon to swings in currency exchange rates? | 23 | 25 | 2 / 2 | Yes | Yes |
| hq_395269fb91c24e7aba645db4529fd483 | What liquidity risks does Bank of America describe related to deposit outflows? | 22 | 24 | 2 / 2 | Yes | Yes |
| hq_3bc57255183d4bdeabdba814d9c2f4a7 | What does Apple's value-at-risk model estimate for its foreign currency exposure? | 19 | 23 | 4 / 4 | Yes | Yes |
| hq_3d27d3a6bc924f74ab4e2b4f2a914397 | Why did Pfizer's COVID vaccine and pill sales collapse in 2023? | 23 | 26 | 3 / 3 | Yes | Yes |
| hq_4d5d9efc06f34ddaa145f699ce2c2e4d | How could Meta's heavy spending on virtual and augmented reality go wrong? | 29 | 31 | 2 / 2 | Yes | Yes |
| hq_5404d74f74b4456e9c72c7def4c64227 | What factors drove the change in AWS segment operating income in 2024? | 15 | 16 | 1 / 1 | Yes | Yes |
| hq_69c1bbc69ab243d29a5b85972d80828e | Why did Tesla make less profit on its cars in 2024? | 18 | 22 | 4 / 4 | Yes | Yes |
| hq_804ee5491dee4faaa512e49ecdfc1dd0 | Why did NVIDIA write off billions in chip inventory in early fiscal 2026? | 21 | 23 | 2 / 2 | Yes | Yes |
| hq_84c831be7d16420aae81eb2d9f98c8af | How did the membership fee increase affect Costco's membership fee income in fiscal 2025? | 19 | 20 | 1 / 1 | Yes | Yes |
| hq_9244d7ed50884988a8b0fcc969655431 | How did Alphabet explain the increase in capital expenditures for technical infrastructure in 2024? | 20 | 21 | 1 / 1 | Yes | Yes |
| hq_9f2123ab94e5409ba2375e444df03060 | How did buying Pioneer change Exxon's oil and gas production in 2024? | 20 | 20 | 0 / 0 | Yes | Yes |
| hq_af3da89ebdb6499f84b1103586988fcc | How does Coca-Cola price the concentrate it sells to its bottlers? | 20 | 22 | 2 / 2 | Yes | Yes |
| hq_bbeba329b2724abcbbff1ea7869b3907 | What savings does Pfizer expect from its Cost Realignment Program? | 19 | 20 | 1 / 1 | Yes | Yes |
| hq_beb86dbbb9224fdcade1fe13bd690a88 | How much did eCommerce contribute to Walmart U.S. comparable sales in fiscal 2025? | 18 | 19 | 1 / 1 | Yes | Yes |
| hq_c65d4576350841669beea4c8dbea0a2b | How does Coke protect itself against currency and commodity price swings? | 21 | 23 | 2 / 2 | Yes | Yes |
| hq_cdeefd822cd94dd98c915d26380f37ed | How did the 2024 hack of UnitedHealth's payment-processing unit affect the company? | 19 | 21 | 2 / 2 | Yes | Yes |
| hq_ce9809903d0b430eb90e3615603210f7 | How does Microsoft describe its Copilot and AI offerings in its business overview? | 22 | 23 | 1 / 1 | Yes | Yes |
| hq_d2c0efbeda48446e88c1160406bc4452 | How were new tariffs hitting Apple's costs in mid-2025? | 6 | 6 | 0 / 0 | Yes | Yes |
| hq_e3dfcc6ccd02482fb791dc34596565e7 | How would Bank of America's net interest income change if interest rates suddenly fell 100 basis points? | 23 | 23 | 0 / 0 | Yes | Yes |
| hq_eead0b7f7e3f430589800660cafe8cb1 | Why were UnitedHealth's medical costs higher than expected in 2025? | 11 | 11 | 0 / 0 | Yes | Yes |
| hq_f5d53183cdd04505b02cde17b599d44f | What risks does Johnson & Johnson describe from Medicare drug price negotiation under the Inflation Reduction Act? | 22 | 24 | 2 / 2 | Yes | Yes |

Detailed per-passage ranks, text hashes, exact score bytes and neighbor checks: [verification JSON](CORPUS_V2_TIE_VERIFICATION.json). Input label and archived ranking SHA-256 hashes were checked before and after and are recorded there. Both corpora were accessed read-only. Small keyword/hybrid differences in these unchanged scopes reflect ID-based exact-score tie-breaking; this finding does not attribute changes in repaired scopes to ties.

Commands:

```powershell
.venv/Scripts/python.exe -m evals.verify_v2_ties
.venv/Scripts/python.exe -m ruff check evals/verify_v2_ties.py
.venv/Scripts/python.exe -m ruff format --check evals/verify_v2_ties.py
```

Lint and format checks pass. No retrieval evaluation or test suite that accesses writable corpus fixtures was run for this read-only verification. Phase C and corpus v2 are accepted under the student's stated condition. No M3 work started.

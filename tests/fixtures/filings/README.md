# Real SEC HTML fixtures

These deterministic gzip files contain the exact source filing bodies already
downloaded and checksummed during M1; they are not synthesized HTML excerpts.
URLs, filing dates, report dates, accessions and decompressed SHA-256 checksums
are recorded in `../revenue_expected.json`:

| Accession | Filing |
|---|---|
| 0000320193-25-000079 | Apple FY2025 10-K |
| 0000950170-25-061046 | Microsoft FY2025 Q3 10-Q |
| 0001045810-25-000023 | NVIDIA FY2025 10-K |

The parsing regression tests decompress each fixture and verify its SHA-256
before checking section boundaries. Tokenizer/model integration tests separately
require the pinned local model artifacts.

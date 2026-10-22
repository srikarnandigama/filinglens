# FilingLens

FilingLens is a source-grounded SEC research assistant whose main deliverable is
a reproducible comparison against single-prompt model baselines. M1 provides
the database and audited facts ingestion; M2 provides frozen filing corpora,
four retrieval modes and a student-labeled retrieval evaluation. M3's two MCP
servers are accepted following Inspector/Desktop verification; the agent runtime
and UI remain later milestones. See [M3 handoff](docs/M3_HANDOFF.md).

## M2 retrieval results: corpus v2

The active corpus for M3 onward is
`corpus_3f3c2a9affddcc6a29eca9e768c65bcbd3e2f131fb69595b24b9b92005738739`
(32,960 chunks, 275 filings). Settings uses it when RETRIEVAL_CORPUS is unset or
blank; explicit corpus selection remains available for historical v1 work.
V1 and its results are preserved. Corpus v2 and Phase C are accepted;
M3 is accepted after the student's Inspector and all five Desktop checks.

The 30 student-reviewed questions have 64 pooled gold labels. Primary capped
recall and MRR@30 are:

| Mode | Capped recall@5 | Capped recall@10 | MRR@30 |
|---|---:|---:|---:|
| vector | 0.6489 | 0.7333 | 0.6302 |
| keyword | 0.4800 | 0.5881 | 0.5275 |
| hybrid | 0.5867 | 0.7159 | 0.5965 |
| hybrid_rerank | 0.6322 | 0.7492 | 0.5670 |

See [the v2 report](evals/results/retrieval_v2.md) for metric definitions,
cross-year/period-filtered subsets, comparisons with v1, label-change attribution
and limitations. These are pooled, non-exhaustive judgments on a small set;
they do not establish end-to-end answer quality. Reranking improves recall@10
over hybrid but reduces MRR. Labels are in `evals/handwritten_v2.jsonl`.

## M1 setup (Windows PowerShell)

Docker Desktop must be running. The project uses an isolated Python 3.12 and
does not change system Python. If `uv` is already installed, use it directly;
this workspace has a project-local installation at `.tools/uv/bin/uv.exe`.

```powershell
# Bootstrap uv locally if needed:
python -m pip install --target .tools/uv uv
$env:UV_PYTHON_INSTALL_DIR = Join-Path (Get-Location) '.uv/python'
$env:UV_CACHE_DIR = Join-Path (Get-Location) '.uv/cache'
& .tools/uv/bin/uv.exe python install 3.12 --no-bin --no-registry
& .tools/uv/bin/uv.exe sync --locked
```

Create `.env` from `.env.example` if it does not exist. Supply a real contact
email in `SEC_USER_AGENT`; M1 requires no LLM keys. Do not overwrite an existing
`.env`. With the virtual environment activated, the spec's plain `python`
commands work. PowerShell execution policies may block activation, so explicit
interpreter paths are also supported:

```powershell
docker compose up -d --wait db
.venv/Scripts/python.exe db/migrate.py
.venv/Scripts/python.exe -m filinglens.ingest.pipeline --stage facts
.venv/Scripts/python.exe -m pytest -q
$env:FILINGLENS_TEST_DB = '1'
.venv/Scripts/python.exe -m pytest -q
.venv/Scripts/ruff.exe check .
.venv/Scripts/ruff.exe format --check .
```

Integration tests require the populated local database. They create and remove
isolated test schemas; the fixture check reads the real ingested facts.

## Snapshot and resume semantics

The default snapshot is `2026-10-19-v1`, with filing cutoff **2026-10-19**.
Each company receives the latest three completed fiscal years with available
annual reports plus available subsequent quarterly reports. Snapshots are
immutable collections of successful responses, keyed by URL SHA-256 under
`data/raw/<snapshot>/`; each response records its URL, retrieval time, and hash.
Repeated runs reuse responses and preserve fact IDs. A failed company transaction
rolls back; rerunning safely resumes using already cached downloads.

Create a new snapshot to refresh SEC data:

```powershell
.venv/Scripts/python.exe -m filinglens.ingest.pipeline --stage facts --snapshot NEW-ID --cutoff YYYY-MM-DD
```

A cutoff filters filing dates; it is not a promise to reconstruct what the SEC
served at a historical instant. Never edit an old snapshot to refresh it.
Only one ingestion process should use this project's SEC client at a time.
Use `--tickers AAPL,MSFT,NVDA` for a smaller run and `--years 3` to set window length.

## Revenue acceptance fixture

`tests/fixtures/revenue_expected.json` contains 12 FY2025 quarterly revenues,
independently extracted from downloaded filing inline-XBRL tags. Q4 expectations
use annual revenue minus nine-month revenue. It records source URLs, accessions,
context IDs, displayed values, scale, document hashes, and local cached paths.
Companyfacts excerpts provide separate offline normalization inputs.

```powershell
.venv/Scripts/python.exe -m scripts.prepare_revenue_fixture
```

**Manual verification is pending.** Passing tests establishes agreement between
the source-tag expectations and normalized/database values; it does not replace
the student's review of the 12 figures. See `docs/M1_REVENUE_REVIEW.md`.

## Decisions and limitations

See [design decisions](docs/DECISIONS.md). In particular, the fiscal-year label
is the calendar year in which the fiscal year ends, missing data remains
unavailable, and XOM uses its documented historical reporting CIK following a
2026 holding-company reorganization. Year-end instant facts are stored once as
Q4; a later metric interface must treat FY as an alias for that same instant.

Database metadata is shared between snapshots; facts and availability records
are snapshot-specific. This M1 snapshot stores canonical latest-filed facts,
not every historical revision. It cannot establish that every possible metric
is applicable, and it does not extract custom-taxonomy facts.

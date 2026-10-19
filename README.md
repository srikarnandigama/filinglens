# FilingLens

FilingLens is a source-grounded SEC research assistant whose main deliverable is
a reproducible comparison against single-prompt model baselines. M1 provides
the database and audited facts ingestion; retrieval, agents, evaluations, and UI
are later milestones and are not implemented yet.

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

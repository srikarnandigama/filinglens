# M1 implementation and acceptance status

**Implementation finished; acceptance pending the student's fixture verification.**
Milestone 2 has not started.

## Built

- Project-local uv 0.13.1, Python 3.12.15, locked M1 dependencies, configuration,
  README setup commands, and ignored secrets/downloads/environments.
- Healthy PostgreSQL 16 + pgvector 0.8.7 Docker Compose service, the Section 6
  schema with approved M1 extensions, transactional/checksummed migrations,
  and explicit database pool lifecycle.
- SEC client with identifying User-Agent, shared eight-request/second pacing,
  versioned checksummed cache, bounded retries, and same-URL request deduplication.
- Historical submission traversal, reporting-date calendars, per-period concept
  fallback, latest-filed observations, exact Decimal/NUMERIC facts, compatible
  Q2/Q3/Q4 derivations with complete input provenance, and availability reasons.
- Independently prepared filing-tag revenue expectations and downloaded source
  documents for the student's 12-value review.

## Verified

Final local verification on 2026-10-19:

- Docker database starts and is healthy; migration applies on an isolated empty
  schema and reruns without changes. Failed SQL rolls back; modified applied
  migrations are rejected.
- Full ingestion: **20 companies, 275 filings, 2,715 stored financial facts**,
  including **563 derived facts**.
- **37 tests passed in 10.51 seconds**, including database integration tests.
- The full-universe replay test blocks all HTTP requests and verifies **zero
  network requests** and unchanged stored fact values, provenance, and IDs.
- Ruff lint and format checks pass; `git diff --check` passes.
- System `python --version` remains **3.14.0**; the project interpreter is **3.12.15**.
- `.env`, `.venv`, `.tools`, `.uv`, and `data` are ignored. No commit was created.

Commands used for the final checks:

```powershell
.venv/Scripts/ruff.exe check .
.venv/Scripts/ruff.exe format --check .
$env:FILINGLENS_TEST_DB = '1'
.venv/Scripts/python.exe -m pytest -q
.venv/Scripts/python.exe db/migrate.py
```

Earlier live acceptance runs used `docker compose up -d --wait db` and
`.venv/Scripts/python.exe -m filinglens.ingest.pipeline --stage facts`.

## Remaining acceptance step

Review all 12 FY2025 revenue values in [M1_REVENUE_REVIEW.md](M1_REVENUE_REVIEW.md)
against their linked filings, then explicitly confirm M1 acceptance. The fixture
currently records `pending_user_verification`; automated agreement with source
tags and database values does not imply manual verification.

## Decisions and limitations

[DECISIONS.md](DECISIONS.md) contains D001–D016. Significant discoveries include
Costco's 12/12/12/16-week calendar and XOM's successor-versus-historical reporting
CIK; both have regression tests and documented treatment. Year-end instant facts
are stored once as Q4 and need an FY alias in the future metric interface.

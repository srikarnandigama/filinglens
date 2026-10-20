# Project instructions

This project is specified in SPEC.md. Read it before doing anything.

## Rules
- Follow SPEC.md Section 0 ("Instructions to the coding agent") at all times.
- Work one milestone at a time (SPEC.md Section 16). Plan first and wait
  for my approval before writing code.
- Never start the next milestone until I confirm the current one's
  acceptance criteria pass.
- Record every non-obvious design choice in docs/DECISIONS.md.
- Never commit .env or API keys. ANTHROPIC_API_KEY is not set yet;
  don't block on it before Milestone 4.
- Ask before adding dependencies not listed in SPEC.md Section 3.

## Progress
- [x] M1 Foundation + data
- [ ] M2 Parsing, chunking, embeddings, retrieval
- [ ] M3 MCP servers
- [ ] M4 Agent runtime
- [ ] M5 Eval harness + baselines
- [ ] M6 Experiments + CI
- [ ] M7 API, frontend, docs
- [ ] M8 Deploy + publish (optional)

## Notes for the next session

M1 is accepted: the student manually verified all 12 FY2025 revenue fixture
values against the source filings and confirmed they match. The last M1 checks
passed: 37 tests, Ruff lint/format, and a network-blocked full cache replay that
preserves fact values, provenance, and IDs. The database contains 20 companies,
275 filings, and 2,715 facts (563 derived).

- Ingestion cutoff: 2026-10-19, inclusive by filing date (America/New_York).
- Snapshot: 2026-10-19-v1, stored at data/raw/2026-10-19-v1/. Bodies are keyed
  by URL SHA-256 with companion metadata; ingestion_snapshots holds the manifest.
  Reuse this immutable snapshot; refresh only under a new snapshot ID.
- Window: three completed fiscal years with available annual reports, plus
  available subsequent quarters. An ended year without a filed annual report
  is not yet a complete annual dataset.
- Known gaps: missing standard-taxonomy metrics remain unavailable, never zero
  or automatically not_applicable. Custom-taxonomy facts are not extracted;
  EPS quarters are unavailable when no direct value exists (never derive EPS).
  Gross profit is not synthesized from revenue and costs. metric_availability
  records period-specific availability and reasons.
- Fiscal calendars use actual report dates, not XBRL fy/fp or fixed month/day
  arithmetic. Preserve 52/53-week behavior and Costco's 12/12/12/16-week quarters.
  XOM uses reporting CIK 0000034088 following the documented successor mapping.
  Year-end instant facts are stored once as Q4; the future metric interface
  must resolve FY to that same instant.
- M2 has not started. Its scope is filing downloads/parsing, section splitting,
  chunking, embeddings, four retrieval modes, and retrieval evaluation (SPEC.md
  Sections 7.2-8 and 16). Only the fixture source filings have been downloaded;
  the full filing-document corpus still needs downloading. sections and chunks
  tables/indexes exist but parsing, embeddings, and retrieval are not implemented.
- Reuse the SEC client's cache, identifying User-Agent, shared rate limit, and
  retries; run one ingestion process at a time. Retain stable chunk IDs once
  gold retrieval labels are assigned. Test table-of-contents heading ambiguity,
  preserve table rows when chunking, and evaluate filtered HNSW recall with
  pgvector 0.8.7 (iterative scans or exact search as appropriate).
- Schema is finalized for M1: ask before subsequent schema changes or unlisted
  dependencies. M2 dependencies listed in SPEC.md are not installed yet; YAML
  support remains deferred. Record new non-obvious decisions in DECISIONS.md.
- Use project-local uv (.tools/uv/bin/uv.exe) and Python 3.12.15
  (.venv/Scripts/python.exe); system Python remains 3.14.0. The CLI uses the
  Windows selector event loop for Psycopg and an IPv4 hint for localhost.
- See docs/DECISIONS.md (D001-D016), docs/M1_REVENUE_REVIEW.md, and
  tests/fixtures/revenue_expected.json for provenance. Their earlier pending
  verification wording and docs/M1_STATUS.md predate the student's acceptance;
  the acceptance recorded here supersedes those pending labels.

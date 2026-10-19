# Design decisions

## D001 — Milestone boundaries and approved specification interpretations
Milestones are in Section 16; Section 0 now points there. M1 ends after foundation and facts ingestion, and acceptance remains pending until the student verifies the revenue fixture and confirms the milestone. Quant tools are required for production LLM arithmetic, while deterministic ingestion/evaluation calculations and the explicit no-quant ablation are allowed; diff is optional in M4, and improvements are selected on dev before final test reporting.

## D002 — Isolated Python and dependencies
Use uv 0.13.1 with project-local Python 3.12.15, `.venv`, and `uv.lock`; system Python 3.14 is unchanged. Only M1 dependencies are installed, including explicitly approved `pydantic-settings`, with YAML support deferred. Explicit virtual-environment executable paths avoid changing PowerShell execution policy.

## D003 — Window and cutoff
The initial snapshot ID is `2026-10-19-v1`, with an inclusive filing-date cutoff of **2026-10-19**, interpreted in the user's America/New_York calendar. Ingest three completed fiscal years for which annual reports are available, plus available subsequent quarters; a fiscal year whose annual report has not yet been filed cannot supply a complete annual dataset. Historical submissions are traversed over a conservatively broader window so recent-list truncation does not omit required filings or prior annual boundaries.

## D004 — Immutable versioned snapshots
Store successful response bodies under `data/raw/<snapshot_id>/<sha256(url)>.body`, with URL, retrieval timestamp, content type, and body hash in companion metadata. Completed cache entries are never refreshed, corruption fails explicitly, and changing the cutoff requires a new snapshot ID. A snapshot captures responses acquired during its construction, filtered by filing date, rather than reconstructing the SEC's exact historical state; the database records a manifest of acquired responses.

## D005 — SEC fairness and retry behavior
Use one shared client per ingestion, spaced at least 1/8 second between network attempts, including retries; cache hits make no network request. Retry 429, 5xx, and transport failures with bounded exponential backoff and jitter, honoring Retry-After up to a 120-second bound, while other HTTP failures remain explicit. A descriptive User-Agent is required; error pages and invalid JSON are never cached as successful data, and only one ingestion process should run against this project at a time.

## D006 — Reporting-date fiscal calendars
Anchor each completed fiscal year to actual 10-K report dates and its observed annual duration start, with the previous annual end plus one day as fallback. Actual 10-Q report dates define quarter boundaries, handling 52/53-week years without approximating quarters from months; `fiscalYearEnd` is retained as supporting metadata. Observed boundaries take precedence over Section 7.1's approximate day bands: Costco's 12/12/12/16-week calendar has a 16-week Q4 and shorter YTD durations that those bands would incorrectly reject. Completed fiscal years are labeled by their ending calendar year, a partially reported subsequent year is provisionally labeled the next fiscal year, and ambiguous or incomplete boundary sets fail instead of guessing.

## D007 — Concept selection and missing metrics
Choose one direct fact per metric/period using the specified concept priority, falling back to later concepts only when earlier concepts lack that period; direct reported quarters take precedence over derived alternatives. Retain the actual concept on every fact and never sum overlapping concepts. Missing standard-taxonomy facts are marked unavailable with a reason; `not_applicable` is a distinct supported status that requires positive evidence and is never inferred solely from absence.

## D008 — Revisions and exact values
For each concept, unit, start, and end context, choose the latest filed observation within the cutoff, with accession as a deterministic tie-breaker; conflicting values in the same filing/context fail explicitly. Decode financial values into Decimal and store NUMERIC, preserving raw USD and USD/shares units rather than converting to display millions. This is latest-filed-within-snapshot data, not an as-originally-reported historical time series.

## D009 — YTD derivations and provenance
For additive duration metrics, derive missing Q2 as 6M minus Q1, Q3 as 9M minus 6M, and Q4 as FY minus 9M, with FY minus three direct quarters as Q4 fallback. Inputs must share the exact fiscal-year start, compatible adjacent boundaries, concept, and unit; EPS is never derived, and gross profit is never synthesized from revenue and costs. Every derived fact retains signed input values, concepts, dates, units, filing dates, and accessions in `derivation_inputs`, including YTD observations that are not standalone stored facts.

## D010 — M1 schema finalization
Extend the supplied schema with `ingestion_snapshots`, snapshot-aware facts, `source_filed`, derivation-input JSONB, and `metric_availability`; retain the later-stage tables and indexes specified in Section 6 without implementing those stages. The fact uniqueness key includes snapshot, company, metric, period type, start date, end date, and unit, using PostgreSQL 16 `NULLS NOT DISTINCT` so instant facts also deduplicate. Schema changes after M1 require approval; migrations have checksums and run transactionally under an advisory lock.

## D011 — Stable fact IDs and resumption
Upserts preserve company/filing identity and fact conflicts do not replace existing canonical rows within an immutable snapshot. Each company is one database transaction, so failures roll back that company while prior companies and cached downloads remain reusable. Snapshot-specific facts coexist across refreshes, while company and filing metadata are shared; raw snapshot manifests preserve their original sources.

## D012 — Instant facts at fiscal year end
Store year-end balance-sheet instants once under Q4, rather than duplicating one observation as both Q4 and FY. The future metric interface must resolve FY to the same year-end instant; no summation of balance-sheet values is valid. This avoids fighting the approved uniqueness key, which identifies an instant by its company, metric, end date, unit, and snapshot.

## D013 — Windows database compatibility
The CLI selects Windows' selector event loop because Psycopg asynchronous connections do not support the default Proactor loop. For a configured `localhost` database, supply IPv4 `hostaddr=127.0.0.1` to avoid the observed IPv6 connection delay while preserving the configured hostname and credentials. Pools open, wait for readiness, and close explicitly with bounded connection timeouts.

## D014 — XOM reporting-entity continuity
The downloaded SEC ticker map resolves XOM to holding-company CIK 0002115436 after its July 2026 reorganization, but the required historical and continuing joint reporting series is under CIK 0000034088. Resolve this specific, guarded mapping to the historical reporting CIK, leaving every filing accession and SEC URL intact rather than pretending the successor has three years of annual reports. The documented primary source is the [successor's 8-K12B](https://www.sec.gov/Archives/edgar/data/2115436/000119312526291990/d71068d8k12b.htm); the research company retains the operating registrant's name and CIK, and no general merger-history inference is attempted.

## D015 — Independently prepared revenue fixture
Use FY2025 quarterly revenue for AAPL, MSFT, and NVDA: three different fiscal year ends, including a week-based calendar. Expectations come from consolidated revenue tags in downloaded filing HTML, independently of the companyfacts normalization implementation; Q4 expectations explicitly subtract filing-tag annual and nine-month totals. Preserve source URLs, accession numbers, context IDs, displayed figures/scales, hashes, and downloaded source files, and mark all 12 values **pending user verification** until the student reviews them.

## D016 — Documentation checks and deferred integrations
Reviewed official [SEC APIs](https://www.sec.gov/search-filings/edgar-application-programming-interfaces), [SEC access policy](https://www.sec.gov/about/webmaster-frequently-asked-questions), [Psycopg pools](https://www.psycopg.org/psycopg3/docs/advanced/pool.html), [Psycopg async compatibility](https://www.psycopg.org/psycopg3/docs/advanced/async.html), [Pydantic migration](https://github.com/pydantic/pydantic/blob/main/docs/migration.md), [HTTPX timeouts](https://www.python-httpx.org/advanced/timeouts/), and [uv Python provisioning](https://docs.astral.sh/uv/guides/install-python/). The [pgvector documentation](https://github.com/pgvector/pgvector) supports the PostgreSQL 16/HNSW foundation, but filtered-recall handling remains M2. Official [MCP Python](https://github.com/modelcontextprotocol/python-sdk) and [Anthropic SDK](https://platform.claude.com/docs/en/cli-sdks-libraries/overview) documentation was checked during planning and will be rechecked at their integration milestones; no agent/RAG frameworks are introduced.

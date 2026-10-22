"""Snapshot/corpus-scoped SELECTs; no ingestion or financial synthesis."""

import asyncio
import hashlib
import json
import os
from dataclasses import asdict
from pathlib import Path

import anyio

from filinglens.edgar.xbrl import INSTANT, METRICS
from mcp_servers.decimal_math import ToolFailure, fixed
from mcp_servers.models import (
    AvailablePeriod,
    CompanyData,
    CorpusInfo,
    CoverageDiagnostic,
    DerivationInput,
    Evidence,
    FactsData,
    FilingsData,
    MetricAvailability,
    MetricFact,
    MetricsData,
    PassageData,
    PassageHit,
    Period,
    PeriodStatus,
    SearchData,
    SectionData,
    SectionSpan,
    SnapshotInfo,
    Source,
)
from mcp_servers.runtime import ServerSettings, readonly_pool


class EdgarRepository:
    def __init__(self, settings: ServerSettings, pool) -> None:
        self.settings = settings
        self.pool = pool
        self.snapshot: SnapshotInfo | None = None
        self.corpus: CorpusInfo | None = None
        self._search_slots = anyio.Semaphore(1)
        self._policies = json.loads(
            Path(__file__).with_name("applicability.json").read_text(encoding="utf-8")
        )

    async def rows(self, sql: str, params=()) -> list[dict]:
        async with self.pool.connection() as conn:
            return await (await conn.execute(sql, params)).fetchall()

    async def initialize(self) -> None:
        snapshots = await self.rows(
            "SELECT * FROM ingestion_snapshots WHERE id=%s", (self.settings.snapshot_id,)
        )
        if not snapshots:
            raise ToolFailure("SNAPSHOT_UNAVAILABLE", "Unknown facts snapshot.")
        corpora = await self.rows(
            "SELECT * FROM retrieval_corpora WHERE id=%s", (self.settings.retrieval_corpus,)
        )
        if not corpora or not corpora[0]["frozen"]:
            raise ToolFailure("CORPUS_UNAVAILABLE", "Select an existing frozen retrieval corpus.")
        if corpora[0]["snapshot_id"] != self.settings.snapshot_id:
            raise ToolFailure("DATA_INTEGRITY", "Corpus and facts snapshot identities differ.")
        self.snapshot = SnapshotInfo(
            snapshot_id=self.settings.snapshot_id, cutoff_date=snapshots[0]["cutoff_date"]
        )
        self.corpus = CorpusInfo(**self.snapshot.model_dump(), corpus_id=corpora[0]["id"])

    async def company(self, ticker: str) -> dict:
        rows = await self.rows("SELECT * FROM companies WHERE ticker=%s", (ticker.upper(),))
        if not rows:
            raise ToolFailure("COMPANY_NOT_FOUND", "Ticker is outside the stored company universe.")
        return rows[0]

    async def resolve_company(self, query: str) -> CompanyData:
        query = " ".join(query.split())
        if not query:
            raise ToolFailure("INVALID_INPUT", "Company query must not be blank.")
        companies = await self.rows("SELECT * FROM companies ORDER BY ticker")
        exact = [c for c in companies if c["ticker"].casefold() == query.casefold()]
        exact = exact or [c for c in companies if c["name"].casefold() == query.casefold()]
        matches = exact or [c for c in companies if query.casefold() in c["name"].casefold()]
        if not matches:
            raise ToolFailure("COMPANY_NOT_FOUND", "No stored company matches this ticker/name.")
        if len(matches) > 1:
            raise ToolFailure(
                "AMBIGUOUS_COMPANY",
                "Choose a ticker: "
                + ", ".join(c["ticker"] + " (" + c["name"] + ")" for c in matches),
            )
        return CompanyData(**matches[0], snapshot=self.snapshot)

    async def documents(self, *, ticker=None, fiscal_year=None, fiscal_period=None) -> list[dict]:
        where = ["d.corpus_id=%s", "f.filing_date<=%s"]
        params = [self.settings.retrieval_corpus, self.snapshot.cutoff_date]
        for key, value in [
            ("co.ticker", ticker),
            ("f.fiscal_year", fiscal_year),
            ("f.fiscal_period", fiscal_period),
        ]:
            if value is not None:
                where.append(key + "=%s")
                params.append(value.upper() if key == "co.ticker" else value)
        return await self.rows(
            "SELECT d.*,f.form,f.fiscal_year,f.fiscal_period,f.filing_date,f.report_date,"
            "f.url,co.ticker FROM corpus_documents d JOIN filings f USING(accession) "
            "JOIN companies co USING(cik) WHERE "
            + " AND ".join(where)
            + " ORDER BY f.report_date DESC,f.filing_date DESC,f.accession ASC",
            params,
        )

    async def list_filings(self, ticker: str, form=None, fiscal_year=None) -> FilingsData:
        company = await self.company(ticker)
        rows = await self.documents(ticker=company["ticker"], fiscal_year=fiscal_year)
        keys = (
            "accession",
            "form",
            "fiscal_year",
            "fiscal_period",
            "filing_date",
            "report_date",
            "url",
        )
        return FilingsData(
            ticker=company["ticker"],
            corpus=self.corpus,
            filings=[{k: r[k] for k in keys} for r in rows if form is None or r["form"] == form],
        )

    async def applicability(self, ticker: str) -> list[Evidence]:
        policy = self._policies.get(ticker)
        if not policy:
            return []
        ids = [r["chunk_id"] for r in policy["passages"]]
        rows = await self.rows(
            "SELECT c.id,c.text,c.accession,co.ticker,f.url,f.filing_date FROM chunks c "
            "JOIN corpus_chunks cc ON cc.chunk_id=c.id JOIN companies co ON co.cik=c.cik "
            "JOIN filings f ON f.accession=c.accession WHERE cc.corpus_id=%s AND c.id=ANY(%s)",
            (self.settings.retrieval_corpus, ids),
        )
        if len(rows) != len(ids):
            return []
        by_id = {r["id"]: r for r in rows}
        for passage in policy["passages"]:
            row = by_id[passage["chunk_id"]]
            if (
                row["ticker"] != ticker
                or row["accession"] != policy["accession"]
                or hashlib.sha256(row["text"].encode()).hexdigest() != passage["text_sha256"]
            ):
                raise ToolFailure("DATA_INTEGRITY", "Bank applicability evidence does not match.")
        row = rows[0]
        return [
            Evidence(
                policy_id=policy["policy_id"],
                chunk_ids=ids,
                source=Source(
                    accession=row["accession"], filed_date=row["filing_date"], url=row["url"]
                ),
                explanation=policy["explanation"],
            )
        ]

    async def effective_status(self, ticker, metric, availability, *, fact_exists=False):
        evidence = await self.applicability(ticker) if metric == "gross_profit" else []
        if availability and availability["status"] == "available" and not fact_exists:
            raise ToolFailure(
                "DATA_INTEGRITY", "Availability claims an observation that is absent."
            )
        if evidence and fact_exists:
            raise ToolFailure(
                "DATA_INTEGRITY", "A fact conflicts with the bank applicability rule."
            )
        if availability and availability["status"] == "not_applicable" and fact_exists:
            raise ToolFailure("DATA_INTEGRITY", "A fact conflicts with stored non-applicability.")
        if evidence and availability and not fact_exists:
            return "not_applicable", evidence[0].explanation, evidence
        if availability:
            return availability["status"], availability["reason"], []
        return "unavailable", "No availability record in the configured snapshot.", []

    async def get_financial_metric(
        self, ticker: str, metric: str, periods: list[Period]
    ) -> FactsData:
        company = await self.company(ticker)
        results = []
        for period in periods:
            stored_period = (
                "Q4" if metric in INSTANT and period.fiscal_period == "FY" else period.fiscal_period
            )
            params = (
                self.settings.snapshot_id,
                company["cik"],
                metric,
                period.fiscal_year,
                stored_period,
            )
            facts = await self.rows(
                "SELECT f.*,fi.url AS source_url,fi.filing_date AS source_filing_date "
                "FROM financial_facts f LEFT JOIN filings fi ON fi.accession=f.source_accession "
                "WHERE f.snapshot_id=%s AND f.cik=%s AND f.metric=%s AND f.fiscal_year=%s "
                "AND f.fiscal_period=%s",
                params,
            )
            availability = await self.rows(
                "SELECT * FROM metric_availability WHERE snapshot_id=%s AND cik=%s AND metric=%s "
                "AND fiscal_year=%s AND fiscal_period=%s",
                params,
            )
            availability = availability[0] if availability else None
            if len(facts) > 1:
                raise ToolFailure(
                    "DATA_INTEGRITY", "Metric period has multiple stored observations."
                )
            status, reason, evidence = await self.effective_status(
                company["ticker"], metric, availability, fact_exists=bool(facts)
            )
            common = dict(
                metric=metric,
                fiscal_year=period.fiscal_year,
                fiscal_period=period.fiscal_period,
                unit="USD/shares" if metric == "eps_diluted" else "USD",
                stored_availability_status=availability["status"] if availability else None,
            )
            if not facts:
                if status == "available":
                    raise ToolFailure(
                        "DATA_INTEGRITY", "Availability claims a missing fact is available."
                    )
                results.append(
                    MetricFact(
                        **common, status=status, reason=reason, applicability_evidence=evidence
                    )
                )
                continue
            fact = facts[0]
            if fact["unit"] != common["unit"]:
                raise ToolFailure("DATA_INTEGRITY", "Stored fact unit conflicts with its metric.")
            if fact["source_filed"] > self.snapshot.cutoff_date:
                raise ToolFailure("DATA_INTEGRITY", "Fact observation exceeds the snapshot cutoff.")
            inputs = []
            for source in fact["derivation_inputs"]:
                filings = await self.rows(
                    "SELECT url FROM filings WHERE accession=%s", (source["accession"],)
                )
                inputs.append(
                    DerivationInput(
                        coefficient=source["coefficient"],
                        value=source["value"],
                        unit=source["unit"],
                        concept=source["concept"],
                        start_date=source["start"],
                        end_date=source["end"],
                        source=Source(
                            accession=source["accession"],
                            filed_date=source["filed"],
                            url=filings[0]["url"] if filings else None,
                        ),
                    )
                )
            results.append(
                MetricFact(
                    **common,
                    fact_id=str(fact["id"]),
                    stored_fiscal_period=fact["fiscal_period"],
                    period_type=fact["period_type"],
                    period_start=fact["start_date"],
                    period_end=fact["end_date"],
                    value=fixed(fact["value"]),
                    status="available",
                    derived=fact["derived"],
                    concept=fact["concept"],
                    source_accession=fact["source_accession"],
                    source_filed=fact["source_filed"],
                    source_filing_date=fact["source_filing_date"],
                    source_url=fact["source_url"],
                    derivation_inputs=inputs,
                )
            )
        return FactsData(
            ticker=company["ticker"], metric=metric, snapshot=self.snapshot, facts=results
        )

    async def list_available_metrics(self, ticker: str) -> MetricsData:
        company = await self.company(ticker)
        params = (self.settings.snapshot_id, company["cik"])
        facts = await self.rows(
            "SELECT metric,period_type,start_date,end_date,fiscal_year,fiscal_period "
            "FROM financial_facts WHERE snapshot_id=%s AND cik=%s "
            "ORDER BY end_date,fiscal_year,fiscal_period",
            params,
        )
        statuses = await self.rows(
            "SELECT * FROM metric_availability WHERE snapshot_id=%s AND cik=%s "
            "ORDER BY fiscal_year,fiscal_period",
            params,
        )
        metrics = []
        quarters = {}
        for metric in METRICS:
            selected = [f for f in facts if f["metric"] == metric]
            periods = [
                AvailablePeriod(
                    fiscal_year=f["fiscal_year"],
                    fiscal_period=f["fiscal_period"],
                    stored_fiscal_period=f["fiscal_period"],
                    period_start=f["start_date"],
                    period_end=f["end_date"],
                    period_type=f["period_type"],
                )
                for f in selected
            ]
            quarter = [p for p in periods if p.period_type == "quarter"]
            annual = [p for p in periods if p.period_type == "annual"]
            year_end = [
                p for p in periods if p.period_type == "instant" and p.fiscal_period == "Q4"
            ]
            quarters[metric] = {(p.fiscal_year, p.fiscal_period): p for p in quarter}
            states = []
            all_evidence = []
            for record in [s for s in statuses if s["metric"] == metric]:
                has_fact = any(
                    p.fiscal_year == record["fiscal_year"]
                    and p.fiscal_period == record["fiscal_period"]
                    for p in periods
                )
                # Availability may advertise FY for the same Q4 instant.
                if metric in INSTANT and record["fiscal_period"] == "FY":
                    has_fact = any(p.fiscal_year == record["fiscal_year"] for p in year_end)
                state, reason, evidence = await self.effective_status(
                    company["ticker"], metric, record, fact_exists=has_fact
                )
                all_evidence = evidence or all_evidence
                states.append(
                    PeriodStatus(
                        fiscal_year=record["fiscal_year"],
                        fiscal_period=record["fiscal_period"],
                        status=state,
                        stored_status=record["status"],
                        reason=reason,
                    )
                )
            status = (
                "available"
                if periods
                else "not_applicable"
                if states and all(s.status == "not_applicable" for s in states)
                else "unavailable"
            )
            metrics.append(
                MetricAvailability(
                    metric=metric,
                    unit="USD/shares" if metric == "eps_diluted" else "USD",
                    status=status,
                    reason=None
                    if periods
                    else (
                        states[0].reason
                        if states
                        else "No periods available in the configured snapshot."
                    ),
                    available_periods=periods,
                    earliest=periods[0] if periods else None,
                    latest=periods[-1] if periods else None,
                    latest_quarter=quarter[-1] if quarter else None,
                    latest_annual=annual[-1] if annual else None,
                    latest_year_end=year_end[-1] if year_end else None,
                    year_end_alias="FY_to_Q4" if metric in INSTANT else None,
                    period_statuses=states,
                    applicability_evidence=all_evidence,
                )
            )
        common = quarters["revenue"].keys() & quarters["gross_profit"].keys()
        latest = max(
            (quarters["revenue"][p] for p in common), key=lambda p: p.period_end, default=None
        )
        return MetricsData(
            ticker=company["ticker"],
            snapshot=self.snapshot,
            metrics=metrics,
            latest_common_quarter=latest,
            latest_common_quarter_reason=None
            if latest
            else "No common available revenue/gross_profit quarter in this snapshot.",
        )

    def diagnostic(self, doc: dict, item: str) -> CoverageDiagnostic:
        entry = doc["details"].get("coverage", {}).get(item, {})
        code = {
            "extracted": "EXTRACTED",
            "resolved": "RESOLVED",
            "reference covered elsewhere": "REFERENCE_COVERED_ELSEWHERE",
            "source absent": "SOURCE_ABSENT",
        }.get(entry.get("status"), "NOT_PARSED")
        return CoverageDiagnostic(
            code=code,
            accession=doc["accession"],
            item=item,
            reason=entry.get("reason") or entry.get("status") or "No parsed coverage recorded.",
            target_resource=f"filing://{doc['accession']}/{entry['target_item']}"
            if entry.get("target_item")
            else None,
            source_url=doc["url"],
            source_hash=doc["source_hash"],
            method=entry.get("method"),
            evidence_text="\n".join(entry.get("evidence", [])) or None,
        )

    async def get_passage(self, chunk_id: str) -> PassageData:
        rows = await self.rows(
            "SELECT c.*,co.ticker,s.title,f.report_date,f.url FROM chunks c "
            "JOIN corpus_chunks cc ON cc.chunk_id=c.id JOIN companies co ON co.cik=c.cik "
            "JOIN sections s ON s.id=c.section_id JOIN filings f ON f.accession=c.accession "
            "WHERE cc.corpus_id=%s AND c.id=%s AND f.filing_date<=%s",
            (self.settings.retrieval_corpus, chunk_id, self.snapshot.cutoff_date),
        )
        if not rows:
            raise ToolFailure("PASSAGE_NOT_FOUND", "No such chunk in the configured corpus.")
        row = rows[0]
        doc = next(
            d
            for d in await self.documents(
                ticker=row["ticker"],
                fiscal_year=row["fiscal_year"],
                fiscal_period=row["fiscal_period"],
            )
            if d["accession"] == row["accession"]
        )
        keys = (
            "ticker",
            "form",
            "fiscal_year",
            "fiscal_period",
            "item",
            "text",
            "accession",
            "title",
            "report_date",
            "url",
            "oversized_row",
            "section_id",
            "ordinal",
            "token_count",
        )
        return PassageData(
            **{k: row[k] for k in keys},
            chunk_id=row["id"],
            score=None,
            corpus=self.corpus,
            text_truncated=False,
            full_text_characters=len(row["text"]),
            coverage_diagnostics=[self.diagnostic(doc, row["item"])],
        )

    async def section(self, accession: str, item: str) -> SectionData:
        docs = [d for d in await self.documents() if d["accession"] == accession]
        if not docs:
            raise ToolFailure(
                "FILING_NOT_FOUND", "Filing is outside the configured corpus/snapshot."
            )
        doc = docs[0]
        rows = await self.rows(
            "SELECT s.* FROM sections s WHERE s.accession=%s AND s.item=%s AND EXISTS "
            "(SELECT 1 FROM chunks c JOIN corpus_chunks cc ON cc.chunk_id=c.id "
            "WHERE c.section_id=s.id AND cc.corpus_id=%s) ORDER BY s.occurrence,s.id",
            (accession, item, self.settings.retrieval_corpus),
        )
        diagnostic = self.diagnostic(doc, item)
        if not rows and diagnostic.code != "SOURCE_ABSENT":
            raise ToolFailure("SECTION_NOT_FOUND", "No section or verified source-absence record.")
        return SectionData(
            corpus=self.corpus,
            accession=accession,
            ticker=doc["ticker"],
            form=doc["form"],
            fiscal_year=doc["fiscal_year"],
            fiscal_period=doc["fiscal_period"],
            item=item,
            sections=[
                SectionSpan(
                    section_id=r["id"],
                    occurrence=r["occurrence"],
                    title=r["title"],
                    text=r["text"],
                    source_hash=r["source_hash"],
                )
                for r in rows
            ],
            coverage_diagnostics=[diagnostic],
        )

    async def search_filings(
        self, query: str, ticker=None, fiscal_year=None, fiscal_period=None, items=None, k=8
    ) -> SearchData:
        if not query.strip():
            raise ToolFailure("INVALID_INPUT", "Search query must not be blank.")
        if ticker:
            ticker = (await self.company(ticker))["ticker"]
        annual = {"1", "1A", "7", "7A", "8"}
        if items and (
            len(set(items)) != len(items)
            or fiscal_period == "FY"
            and any(i not in annual for i in items)
            or fiscal_period in {"Q1", "Q2", "Q3"}
            and any(i in annual for i in items)
        ):
            raise ToolFailure("INVALID_FILTER", "Items contradict period/form or repeat.")
        if fiscal_period == "Q4":
            return SearchData(
                corpus=self.corpus,
                retrieval_mode=self.settings.retrieval_mode,
                hits=[],
                coverage_diagnostics=[
                    CoverageDiagnostic(
                        code="NO_Q4_FILING", reason="No standalone Q4 10-Q; use FY explicitly."
                    )
                ],
            )
        filters = dict(
            ticker=ticker, fiscal_year=fiscal_year, fiscal_period=fiscal_period, items=items, k=k
        )
        async with self._search_slots:
            hits = await anyio.to_thread.run_sync(self._retrieve, query, filters)
        docs = {
            d["accession"]: d
            for d in await self.documents(
                ticker=ticker, fiscal_year=fiscal_year, fiscal_period=fiscal_period
            )
        }
        snippets = []
        for hit in hits:
            data = asdict(hit)
            data.update(
                text=hit.text[:1200],
                text_truncated=len(hit.text) > 1200,
                full_text_characters=len(hit.text),
                coverage_diagnostics=[self.diagnostic(docs[hit.accession], hit.item)],
            )
            snippets.append(PassageHit(**data))
        coverage = []
        if items:
            coverage = [
                self.diagnostic(doc, item)
                for doc in docs.values()
                for item in items
                if self.diagnostic(doc, item).code
                in {"SOURCE_ABSENT", "REFERENCE_COVERED_ELSEWHERE"}
            ]
        return SearchData(
            corpus=self.corpus,
            retrieval_mode=self.settings.retrieval_mode,
            hits=snippets,
            coverage_diagnostics=coverage,
        )

    def _retrieve(self, query: str, filters: dict):
        # Imports/loading stay out of startup and financial metadata calls.
        from filinglens.ingest.models import QUERY_PREFIX, tokenizer
        from filinglens.retrieval.service import SearchService

        async def retrieve():
            mode = self.settings.retrieval_mode
            try:
                if mode != "keyword" and len(tokenizer("embed").encode(QUERY_PREFIX + query)) > 512:
                    raise ToolFailure("QUERY_TOO_LONG", "Query exceeds the embedding token budget.")
                if (
                    mode == "hybrid_rerank"
                    and len(tokenizer("rerank").encode(query, add_special_tokens=False)) > 48
                ):
                    raise ToolFailure("QUERY_TOO_LONG", "Shorten the query to 48 reranker tokens.")
                async with readonly_pool(self.settings.database_url) as pool:
                    return await SearchService(pool, self.settings.retrieval_corpus).search(
                        query, mode=mode, **filters
                    )
            except (OSError, RuntimeError) as exc:
                raise ToolFailure(
                    "MODEL_UNAVAILABLE", "Check the pinned offline model files."
                ) from exc

        loop = asyncio.SelectorEventLoop if os.name == "nt" else asyncio.new_event_loop
        with asyncio.Runner(loop_factory=loop) as runner:
            return runner.run(retrieve())

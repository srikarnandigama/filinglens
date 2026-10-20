"""M1 facts pipeline: python -m filinglens.ingest.pipeline --stage facts."""

import argparse
import asyncio
import json
import sys
from dataclasses import asdict
from datetime import date

from psycopg.types.json import Jsonb

from filinglens.config import Settings
from filinglens.db import INGESTION_LOCK, INGESTION_UNLOCK, pool_for
from filinglens.edgar.client import EdgarClient
from filinglens.edgar.filings import fiscal_calendar, selected_filings, submission_history
from filinglens.edgar.tickers import UNIVERSE, resolve_tickers
from filinglens.edgar.xbrl import INSTANT, METRICS, normalized_facts


async def _ingest(settings: Settings, tickers: list[str], years: int = 3) -> dict[str, int]:
    totals = {"companies": 0, "filings": 0, "facts": 0}
    async with EdgarClient(settings) as client, pool_for(settings.database_url) as pool:
        companies = await resolve_tickers(client, tickers)
        async with pool.connection() as conn:
            await conn.execute(
                "INSERT INTO ingestion_snapshots(id,cutoff_date) VALUES (%s,%s) "
                "ON CONFLICT DO NOTHING",
                (settings.snapshot_id, settings.ingestion_cutoff),
            )
            row = await (
                await conn.execute(
                    "SELECT cutoff_date FROM ingestion_snapshots WHERE id=%s",
                    (settings.snapshot_id,),
                )
            ).fetchone()
            if row[0] != settings.ingestion_cutoff:
                raise ValueError("Snapshot cutoff mismatch in database")
        for company in companies:
            cik = company["cik"]
            submission, history = await submission_history(client, cik, years)
            xbrl = await client.json(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json")
            # Calendar observations must also respect the ingestion cutoff.
            for concept in xbrl.get("facts", {}).get("us-gaap", {}).values():
                for unit, values in concept.get("units", {}).items():
                    concept["units"][unit] = [
                        value
                        for value in values
                        if value["filed"] <= str(settings.ingestion_cutoff)
                    ]
            calendar = fiscal_calendar(history, xbrl, years)
            filings = selected_filings(cik, history, calendar)
            facts = normalized_facts(xbrl, calendar, settings.ingestion_cutoff)
            async with pool.connection() as conn:
                await conn.execute(
                    """INSERT INTO companies(cik,ticker,name,fiscal_year_end) VALUES (%s,%s,%s,%s)
                    ON CONFLICT(cik) DO UPDATE SET ticker=excluded.ticker,
                    name=excluded.name,fiscal_year_end=excluded.fiscal_year_end""",
                    (
                        cik,
                        company["ticker"],
                        submission.get("name", company["name"]),
                        submission["fiscalYearEnd"],
                    ),
                )
                for filing in filings:
                    await conn.execute(
                        """INSERT INTO filings(accession,cik,form,filing_date,report_date,
                        fiscal_year,fiscal_period,url)
                        VALUES (%(accession)s,%(cik)s,%(form)s,%(filing_date)s,%(report_date)s,
                        %(fiscal_year)s,%(fiscal_period)s,%(url)s)
                        ON CONFLICT(accession) DO UPDATE SET fiscal_year=excluded.fiscal_year,
                        fiscal_period=excluded.fiscal_period,url=excluded.url""",
                        filing,
                    )
                for fact in facts:
                    parameters = asdict(fact) | {"cik": cik, "snapshot_id": settings.snapshot_id}
                    parameters["derivation_inputs"] = Jsonb(fact.derivation_inputs)
                    await conn.execute(
                        """INSERT INTO financial_facts(cik,metric,concept,period_type,
                        start_date,end_date,
                        fiscal_year,fiscal_period,value,unit,derived,source_accession,
                        source_filed,snapshot_id,derivation_inputs)
                        VALUES (%(cik)s,%(metric)s,%(concept)s,%(period_type)s,
                        %(start_date)s,%(end_date)s,
                        %(fiscal_year)s,%(fiscal_period)s,%(value)s,%(unit)s,%(derived)s,
                        %(source_accession)s,
                        %(source_filed)s,%(snapshot_id)s,%(derivation_inputs)s)
                        ON CONFLICT(snapshot_id,cik,metric,period_type,start_date,end_date,unit)
                        DO NOTHING""",
                        parameters,
                    )
                available = {(fact.metric, fact.fiscal_year, fact.fiscal_period) for fact in facts}
                for year in calendar:
                    for metric in METRICS:
                        periods = [f"Q{i + 1}" for i in range(len(year.quarter_ends))]
                        if year.end and metric not in INSTANT:
                            periods.append("FY")
                        for period in periods:
                            found = (metric, year.year, period) in available
                            await conn.execute(
                                """INSERT INTO metric_availability VALUES (%s,%s,%s,%s,%s,%s,%s)
                                ON CONFLICT(snapshot_id,cik,metric,fiscal_year,fiscal_period)
                                DO UPDATE SET status=excluded.status,reason=excluded.reason""",
                                (
                                    settings.snapshot_id,
                                    cik,
                                    metric,
                                    year.year,
                                    period,
                                    "available" if found else "unavailable",
                                    "SEC fact or compatible derivation"
                                    if found
                                    else "No compatible standard-taxonomy fact; "
                                    "absence alone does not establish non-applicability",
                                ),
                            )
                await conn.execute(
                    "UPDATE ingestion_snapshots SET manifest=%s WHERE id=%s",
                    (Jsonb(client.manifest()), settings.snapshot_id),
                )
            totals["companies"] += 1
            totals["filings"] += len(filings)
            totals["facts"] += len(facts)
            print(f"{company['ticker']}: {len(filings)} filings, {len(facts)} facts", flush=True)
        totals |= {"network_requests": client.network_requests, "cache_hits": client.cache_hits}
    return totals


async def ingest(settings: Settings, tickers: list[str], years: int = 3) -> dict[str, int]:
    async with pool_for(settings.database_url) as pool, pool.connection() as conn:
        if not (await (await conn.execute(INGESTION_LOCK)).fetchone())[0]:
            raise RuntimeError("Another ingestion process is active")
        try:
            return await _ingest(settings, tickers, years)
        finally:
            await conn.execute(INGESTION_UNLOCK)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--stage", choices=["facts", "filings", "parse", "embed", "all"], default="facts"
    )
    parser.add_argument("--corpus", help="Explicit corpus for --stage embed")
    parser.add_argument(
        "--full-embed",
        action="store_true",
        help="Full embeddings only after approval of measured sample runtime",
    )
    parser.add_argument(
        "--force", action="store_true", help="Recompute cached parsing to verify IDs"
    )
    parser.add_argument("--tickers", default="all", help="all or comma-separated tickers")
    parser.add_argument("--years", type=int, default=3)
    parser.add_argument(
        "--snapshot", help="New immutable snapshot ID (must match its original cutoff)"
    )
    parser.add_argument("--cutoff", type=date.fromisoformat)
    args = parser.parse_args()
    if args.years < 1:
        parser.error("--years must be positive")
    overrides = {}
    if args.snapshot:
        overrides["snapshot_id"] = args.snapshot
    if args.cutoff:
        overrides["ingestion_cutoff"] = args.cutoff
    tickers = (
        list(UNIVERSE) if args.tickers == "all" else sorted(set(args.tickers.upper().split(",")))
    )
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    async def m2_stages() -> dict:
        from filinglens.ingest.corpus import prepare_corpus
        from filinglens.ingest.embed import run_embeddings

        settings = Settings(**overrides)
        if args.stage in {"filings", "parse"}:
            return await prepare_corpus(settings, tickers, stage=args.stage, force=args.force)
        if args.stage == "embed":
            if not args.corpus:
                parser.error("--stage embed requires --corpus")
            return await run_embeddings(settings, args.corpus, benchmark=not args.full_embed)
        results = {"facts": await ingest(settings, tickers, args.years)}
        for stage in ("filings", "parse"):
            results[stage] = await prepare_corpus(settings, tickers, stage=stage, force=args.force)
            if results[stage]["failed"]:
                raise RuntimeError(f"{stage} incomplete: {results[stage]['failed']}")
        results["embed"] = await run_embeddings(
            settings, results["parse"]["corpus_id"], benchmark=not args.full_embed
        )
        return results

    if args.stage == "facts":
        result = asyncio.run(ingest(Settings(**overrides), tickers, args.years))
    else:
        result = asyncio.run(m2_stages())
    print(json.dumps(result, indent=2))
    if result.get("failed"):
        raise SystemExit(1)


if __name__ == "__main__":
    main()

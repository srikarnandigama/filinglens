"""Preserve real Costco inputs for its 12/12/12/16-week fiscal calendar."""

import asyncio
import json
from dataclasses import asdict

from filinglens.config import ROOT, Settings
from filinglens.edgar.client import EdgarClient
from filinglens.edgar.filings import fiscal_calendar, submission_history
from filinglens.edgar.xbrl import METRICS


async def main() -> None:
    async with EdgarClient(Settings()) as client:
        cik = "0000909832"
        _, history = await submission_history(client, cik, 3)
        url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
        data = await client.json(url)
        year = next(year for year in fiscal_calendar(history, data, 3) if year.year == 2025)
        revenue = {
            concept: value
            for concept, value in data["facts"]["us-gaap"].items()
            if concept in METRICS["revenue"]
        }
        fixture = {
            "source_url": url,
            "snapshot": client.settings.snapshot_id,
            "calendar": asdict(year),
            "facts": {"us-gaap": revenue},
        }
        path = ROOT / "tests/fixtures/cost_revenue_calendar.json"
        path.write_text(json.dumps(fixture, default=str, indent=2), encoding="utf-8")
        print(asdict(year))


if __name__ == "__main__":
    asyncio.run(main())

"""Download fixture filings and independently read their inline-XBRL revenue tags.

This is a fixture preparation utility, not the M2 filing parser. Expectations
remain pending the student's review of the source filings.
"""

import asyncio
import hashlib
import json
from datetime import date
from decimal import Decimal
from html.parser import HTMLParser

from filinglens.config import ROOT, Settings
from filinglens.edgar.client import EdgarClient
from filinglens.edgar.filings import fiscal_calendar, selected_filings, submission_history
from filinglens.edgar.tickers import resolve_tickers
from filinglens.edgar.xbrl import METRICS


class RevenueTags(HTMLParser):
    """Read only consolidated inline revenue facts and their date contexts."""

    def __init__(self, text: str) -> None:
        super().__init__()
        self.contexts: dict[str, dict[str, str]] = {}
        self.tags: list[dict] = []
        self.context: str | None = None
        self.field: str | None = None
        self.fact: dict | None = None
        self.feed(text)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr = dict(attrs)
        local = tag.split(":")[-1]
        if local == "context":
            self.context = attr["id"]
            self.contexts[self.context] = {}
        if self.context and local in {"startdate", "enddate", "instant"}:
            self.field = local
        if self.context and local in {"explicitmember", "typedmember"}:
            self.contexts[self.context]["dimensional"] = "true"
        if tag == "ix:nonfraction" and attr.get("name", "").lower() in {
            f"us-gaap:{concept}".lower() for concept in METRICS["revenue"]
        }:
            self.fact = attr | {"text": ""}

    def handle_data(self, data: str) -> None:
        if self.context and self.field:
            context = self.contexts[self.context]
            context[self.field] = context.get(self.field, "") + data
        if self.fact is not None:
            self.fact["text"] += data

    def handle_endtag(self, tag: str) -> None:
        local = tag.split(":")[-1]
        if local == "context":
            self.context = None
        if local in {"startdate", "enddate", "instant"}:
            self.field = None
        if tag == "ix:nonfraction" and self.fact is not None:
            self.tags.append(self.fact)
            self.fact = None

    def value(self, start: date, end: date) -> dict:
        matches = []
        for tag in self.tags:
            context = self.contexts[tag["contextref"]]
            if (
                context.get("dimensional")
                or context.get("startdate") != str(start)
                or context.get("enddate") != str(end)
            ):
                continue
            raw = tag["text"].replace(",", "").replace("\xa0", "").strip()
            value = Decimal(raw) * (Decimal(10) ** int(tag.get("scale", "0")))
            if tag.get("sign") == "-":
                value = -value
            matches.append(
                {
                    "value": str(value),
                    "concept": tag["name"],
                    "context": tag["contextref"],
                    "displayed": tag["text"],
                    "scale": tag.get("scale", "0"),
                }
            )
        if not matches or len({match["value"] for match in matches}) != 1:
            raise ValueError(f"No unambiguous consolidated revenue for {start}..{end}: {matches}")
        return matches[0]


async def main() -> None:
    settings = Settings()
    directory = ROOT / "tests" / "fixtures"
    directory.mkdir(parents=True, exist_ok=True)
    result = {
        "verification_status": "pending_user_verification",
        "snapshot": settings.snapshot_id,
        "cutoff": str(settings.ingestion_cutoff),
        "companies": [],
    }
    async with EdgarClient(settings) as client:
        for company in await resolve_tickers(client, ["AAPL", "MSFT", "NVDA"]):
            cik = company["cik"]
            submission, history = await submission_history(client, cik, 3)
            facts_url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
            data = await client.json(facts_url)
            year = next(year for year in fiscal_calendar(history, data, 3) if year.year == 2025)
            filings = selected_filings(cik, history, [year])
            tags: dict[str, RevenueTags] = {}
            sources = {}
            for period in ["Q1", "Q2", "Q3", "FY"]:
                filing = min(
                    (filing for filing in filings if filing["fiscal_period"] == period),
                    key=lambda filing: filing["filing_date"],
                )
                body = await client.get(filing["url"])
                tags[period] = RevenueTags(body.decode("utf-8"))
                sources[period] = filing | {
                    "sha256": hashlib.sha256(body).hexdigest(),
                    "cached_file": str(client.paths(filing["url"])[0].relative_to(ROOT)),
                }
            expected = []
            from datetime import timedelta

            for index, end in enumerate(year.quarter_ends):
                period = f"Q{index + 1}"
                start = (
                    year.start if index == 0 else year.quarter_ends[index - 1] + timedelta(days=1)
                )
                if index < 3:
                    extracted = tags[period].value(start, end)
                    inputs = [extracted | {"url": sources[period]["url"]}]
                    value = extracted["value"]
                else:
                    annual = tags["FY"].value(year.start, year.end)
                    ytd = tags["Q3"].value(year.start, year.quarter_ends[2])
                    value = str(Decimal(annual["value"]) - Decimal(ytd["value"]))
                    inputs = [
                        annual | {"url": sources["FY"]["url"], "coefficient": 1},
                        ytd | {"url": sources["Q3"]["url"], "coefficient": -1},
                    ]
                expected.append(
                    {
                        "fiscal_year": 2025,
                        "fiscal_period": period,
                        "start_date": str(start),
                        "end_date": str(end),
                        "value": value,
                        "unit": "USD",
                        "inputs": inputs,
                    }
                )
            # Preserve original downloaded facts, restricted to revenue concepts,
            # for offline normalization tests. Expectations came from HTML above.
            excerpt = {
                "facts": {
                    "us-gaap": {
                        concept: data["facts"]["us-gaap"][concept]
                        for concept in METRICS["revenue"]
                        if concept in data["facts"]["us-gaap"]
                    }
                }
            }
            excerpt_file = directory / f"{company['ticker'].lower()}_revenue_companyfacts.json"
            excerpt_file.write_text(
                json.dumps(
                    {"source_url": facts_url, "snapshot": settings.snapshot_id, **excerpt}, indent=2
                ),
                encoding="utf-8",
            )
            if company["ticker"] == "AAPL":
                names = {name for candidates in METRICS.values() for name in candidates}
                extra = {"source_url": facts_url, "facts": {"us-gaap": {}}}
                for name, concept in data["facts"]["us-gaap"].items():
                    if name in names:
                        extra["facts"]["us-gaap"][name] = {
                            "units": {
                                unit: [
                                    row
                                    for row in values
                                    if str(year.start) <= row["end"] <= str(year.end)
                                ]
                                for unit, values in concept["units"].items()
                            }
                        }
                (directory / "aapl_normalization_inputs.json").write_text(
                    json.dumps(extra, indent=2), encoding="utf-8"
                )
            result["companies"].append(
                {
                    **company,
                    "fiscal_year_end": submission["fiscalYearEnd"],
                    "calendar": {
                        "year": year.year,
                        "start": str(year.start),
                        "end": str(year.end),
                        "quarter_ends": [str(end) for end in year.quarter_ends],
                    },
                    "sources": sources,
                    "companyfacts_fixture": excerpt_file.name,
                    "expected": expected,
                }
            )
            print(
                company["ticker"],
                [(row["fiscal_period"], row["value"]) for row in expected],
                flush=True,
            )
    (directory / "revenue_expected.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    lines = [
        "# M1 revenue review — pending user verification",
        "",
        f"Snapshot: `{settings.snapshot_id}`. Filing cutoff: **{settings.ingestion_cutoff}**.",
        "",
        "These are exact USD values extracted from downloaded filing tags. "
        "They have not been manually verified by the student. "
        "Q4 is FY minus nine-month revenue; both source filings are linked.",
        "",
        "| Company | Fiscal period | Period end | Revenue (USD) | Source filings |",
        "|---|---|---|---:|---|",
    ]
    for company in result["companies"]:
        for row in company["expected"]:
            links = ", ".join(
                f"[{'FY' if i == 0 else '9M'}]({source['url']})"
                if len(row["inputs"]) > 1
                else f"[10-Q]({source['url']})"
                for i, source in enumerate(row["inputs"])
            )
            lines.append(
                f"| {company['ticker']} | FY2025 {row['fiscal_period']} | "
                f"{row['end_date']} | {int(Decimal(row['value'])):,} | {links} |"
            )
    lines += ["", "## Downloaded source documents", ""]
    for company in result["companies"]:
        for period, source in company["sources"].items():
            lines.append(
                f"- {company['ticker']} {period}: [{source['accession']}]({source['url']}); "
                f"local `{source['cached_file']}`; SHA-256 `{source['sha256']}`."
            )
    lines += ["", "Record verification here after reviewing all 12 values: **pending**.", ""]
    (ROOT / "docs/M1_REVENUE_REVIEW.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    asyncio.run(main())

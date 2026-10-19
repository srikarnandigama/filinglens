"""Submission history and reporting-date fiscal calendars."""

from collections import Counter
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

from filinglens.edgar.client import EdgarClient


def filing_url(cik: str, accession: str, document: str) -> str:
    directory = accession.replace("-", "")
    return f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{directory}/{document}"


def rows_from_columns(columns: dict[str, list[Any]]) -> list[dict[str, Any]]:
    if not columns:
        return []
    lengths = {len(values) for values in columns.values()}
    if len(lengths) != 1:
        raise ValueError("SEC submission columns have inconsistent lengths")
    return [
        dict(zip(columns, values, strict=True)) for values in zip(*columns.values(), strict=True)
    ]


async def submission_history(
    client: EdgarClient, cik: str, years: int
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    submission = await client.json(f"https://data.sec.gov/submissions/CIK{cik}.json")
    recent = rows_from_columns(submission["filings"]["recent"])
    # One extra annual boundary anchors the first requested fiscal year's start.
    earliest = date(client.settings.ingestion_cutoff.year - years - 2, 1, 1)
    for file in submission["filings"].get("files", []):
        if date.fromisoformat(file["filingTo"]) >= earliest:
            historical = await client.json(f"https://data.sec.gov/submissions/{file['name']}")
            recent.extend(rows_from_columns(historical))
    unique = {row["accessionNumber"]: row for row in recent}
    rows = sorted(unique.values(), key=lambda row: (row["filingDate"], row["accessionNumber"]))
    return submission, [
        row
        for row in rows
        if row["form"] in {"10-K", "10-Q"}
        and row.get("reportDate")
        and row["filingDate"] <= str(client.settings.ingestion_cutoff)
    ]


@dataclass(frozen=True)
class FiscalYear:
    year: int
    start: date
    end: date | None
    quarter_ends: tuple[date, ...]

    def period(self, end: date) -> str | None:
        try:
            return f"Q{self.quarter_ends.index(end) + 1}"
        except ValueError:
            return None


def fiscal_calendar(
    filings: list[dict[str, Any]], companyfacts: dict[str, Any], years: int
) -> list[FiscalYear]:
    annual_ends = sorted(
        {date.fromisoformat(row["reportDate"]) for row in filings if row["form"] == "10-K"}
    )
    if len(annual_ends) < years:
        raise ValueError(f"Need {years} completed fiscal years, found {len(annual_ends)}")
    starts: dict[date, Counter[date]] = {}
    for concept in companyfacts.get("facts", {}).get("us-gaap", {}).values():
        for unit in concept.get("units", {}).values():
            for fact in unit:
                if fact.get("start") and fact["form"] in {"10-K", "10-Q"}:
                    start, end = date.fromisoformat(fact["start"]), date.fromisoformat(fact["end"])
                    if 350 <= (end - start).days <= 380:
                        starts.setdefault(end, Counter())[start] += 1
    quarter_ends = sorted(
        {date.fromisoformat(row["reportDate"]) for row in filings if row["form"] == "10-Q"}
    )
    result = []
    for end in annual_ends[-years:]:
        if end in starts:
            start = starts[end].most_common(1)[0][0]
        else:
            previous = [value for value in annual_ends if value < end]
            if not previous:
                raise ValueError(f"No observed start boundary for fiscal year ending {end}")
            start = previous[-1] + timedelta(days=1)
        quarters = tuple(value for value in quarter_ends if start <= value < end) + (end,)
        if len(quarters) != 4:
            raise ValueError(
                f"Expected three 10-Q boundaries for fiscal year ending {end}, found {quarters}"
            )
        result.append(FiscalYear(end.year, start, end, quarters))
    last = annual_ends[-1]
    current_ends = tuple(value for value in quarter_ends if value > last)
    if current_ends:
        if len(current_ends) > 3:
            raise ValueError(
                "More than three current-year quarter boundaries; annual report missing"
            )
        result.append(FiscalYear(last.year + 1, last + timedelta(days=1), None, current_ends))
    return result


def selected_filings(
    cik: str, filings: list[dict[str, Any]], calendar: list[FiscalYear]
) -> list[dict[str, Any]]:
    result = []
    for row in filings:
        end = date.fromisoformat(row["reportDate"])
        for year in calendar:
            period = year.period(end)
            if period and ((row["form"] == "10-K") == (period == "Q4")):
                result.append(
                    {
                        "accession": row["accessionNumber"],
                        "cik": cik,
                        "form": row["form"],
                        "filing_date": row["filingDate"],
                        "report_date": row["reportDate"],
                        "fiscal_year": year.year,
                        "fiscal_period": "FY" if period == "Q4" else period,
                        "url": filing_url(cik, row["accessionNumber"], row["primaryDocument"]),
                    }
                )
    return result

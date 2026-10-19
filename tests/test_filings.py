import json
from datetime import date
from pathlib import Path

import httpx
import pytest
import respx

from filinglens.edgar.client import EdgarClient
from filinglens.edgar.filings import fiscal_calendar, rows_from_columns, submission_history
from filinglens.edgar.tickers import resolve_tickers

FIXTURES = Path(__file__).parent / "fixtures"


@respx.mock
async def test_historical_submission_traversal(settings):
    fixture = json.loads((FIXTURES / "revenue_expected.json").read_text())
    source = fixture["companies"][0]["sources"]["FY"]
    columns = {
        "accessionNumber": [source["accession"]],
        "form": [source["form"]],
        "filingDate": [source["filing_date"]],
        "reportDate": [source["report_date"]],
        "primaryDocument": [source["url"].rsplit("/", 1)[-1]],
    }
    respx.get("https://data.sec.gov/submissions/CIK0000320193.json").mock(
        return_value=httpx.Response(
            200,
            json={
                "filings": {
                    "recent": {key: [] for key in columns},
                    "files": [
                        {"name": "history.json", "filingTo": source["filing_date"]},
                        {"name": "old.json", "filingTo": "2000-01-01"},
                    ],
                }
            },
        )
    )
    history_route = respx.get("https://data.sec.gov/submissions/history.json").mock(
        return_value=httpx.Response(200, json=columns)
    )
    async with EdgarClient(settings) as client:
        _, history = await submission_history(client, "0000320193", 3)
    assert history_route.call_count == 1
    assert history[0]["accessionNumber"] == source["accession"]


def test_invalid_column_lengths():
    with pytest.raises(ValueError, match="inconsistent"):
        rows_from_columns({"form": ["10-K"], "reportDate": []})


@respx.mock
async def test_ticker_padding_and_documented_xom_mapping(settings):
    respx.get("https://www.sec.gov/files/company_tickers.json").mock(
        return_value=httpx.Response(
            200,
            json={
                "0": {"ticker": "AAPL", "cik_str": 320193, "title": "Apple Inc."},
                "1": {"ticker": "XOM", "cik_str": 2115436, "title": "ExxonMobil Holdings Corp"},
            },
        )
    )
    async with EdgarClient(settings) as client:
        companies = await resolve_tickers(client, ["AAPL", "XOM"])
        assert [company["cik"] for company in companies] == ["0000320193", "0000034088"]
        with pytest.raises(ValueError, match="not found"):
            await resolve_tickers(client, ["UNKNOWN"])


def test_actual_53_week_year():
    raw = json.loads((FIXTURES / "aapl_revenue_companyfacts.json").read_text())
    values = [
        row
        for concept in raw["facts"]["us-gaap"].values()
        for row in concept["units"].get("USD", [])
        if row.get("start")
    ]
    annual = next(
        row for row in values if row["start"] == "2022-09-25" and row["end"] == "2023-09-30"
    )
    assert (date.fromisoformat(annual["end"]) - date.fromisoformat(annual["start"])).days == 370
    ends = sorted(
        {
            row["end"]
            for row in values
            if annual["start"] <= row["start"] <= row["end"] <= annual["end"]
            and 80
            <= (date.fromisoformat(row["end"]) - date.fromisoformat(row["start"])).days
            <= 100
        }
    )
    filings = [{"form": "10-Q", "reportDate": end} for end in ends if end != annual["end"]]
    filings.append({"form": "10-K", "reportDate": annual["end"]})
    year = fiscal_calendar(filings, raw, 1)[0]
    assert year.start == date(2022, 9, 25)
    assert year.quarter_ends == (
        date(2022, 12, 31),
        date(2023, 4, 1),
        date(2023, 7, 1),
        date(2023, 9, 30),
    )
    assert year.year == 2023

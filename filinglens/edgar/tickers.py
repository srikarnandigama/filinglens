"""Resolve the fixed research universe from SEC's ticker map."""

from typing import Any

from filinglens.edgar.client import EdgarClient

UNIVERSE = tuple(
    "AAPL MSFT NVDA GOOGL AMZN META TSLA JPM BAC XOM CVX JNJ PFE UNH WMT COST KO PG NKE DIS".split()
)


async def resolve_tickers(client: EdgarClient, tickers: list[str]) -> list[dict[str, Any]]:
    mapping = await client.json("https://www.sec.gov/files/company_tickers.json")
    by_ticker = {row["ticker"].upper(): row for row in mapping.values()}
    result = []
    for ticker in tickers:
        if ticker not in by_ticker:
            raise ValueError(f"Ticker not found in SEC map: {ticker}")
        row = by_ticker[ticker]
        # XOM's July 2026 holding-company reorganization retains the operating
        # registrant's joint reports. Keep that reporting history as the series.
        # Source: SEC 8-K12B 0001193125-26-291990; see docs/DECISIONS.md.
        if ticker == "XOM" and str(row["cik_str"]) == "2115436":
            row = row | {"cik_str": 34088}
        result.append(
            {"cik": str(row["cik_str"]).zfill(10), "ticker": ticker, "name": row["title"]}
        )
    return result

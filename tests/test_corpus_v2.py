"""Real-cache resolver regressions; no downloads and no production DB writes."""

import asyncio
import gzip
import hashlib
import json
from contextlib import asynccontextmanager
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from filinglens.config import Settings
from filinglens.ingest.offline import OfflineSnapshot
from filinglens.ingest.parse import parse_filing
from filinglens.ingest.resolve import normalized, resolve_filing

ANNUALS = [
    ("CVX", "0000093410-24-000013"),
    ("CVX", "0000093410-25-000009"),
    ("CVX", "0000093410-26-000078"),
    ("JPM", "0000019617-24-000225"),
    ("JPM", "0000019617-25-000270"),
    ("JPM", "0001628280-26-008131"),
    ("XOM", "0000034088-24-000018"),
    ("XOM", "0000034088-25-000010"),
    ("XOM", "0000034088-26-000045"),
    ("DIS", "0001744489-23-000216"),
    ("DIS", "0001744489-24-000276"),
    ("DIS", "0001744489-25-000155"),
    ("NVDA", "0001045810-24-000029"),
    ("NVDA", "0001045810-25-000023"),
    ("NVDA", "0001045810-26-000021"),
]


def cached_body(accession):
    settings = Settings()
    directory = settings.raw_dir / settings.snapshot_id
    for path in directory.glob("*.json"):
        metadata = json.loads(path.read_text())
        if accession.replace("-", "") in metadata.get("url", ""):
            with asyncio.Runner(loop_factory=asyncio.SelectorEventLoop) as runner:
                return runner.run(OfflineSnapshot(settings).get(metadata["url"]))
    pytest.skip("Real immutable filing cache is not available")


@pytest.mark.parametrize("ticker,accession", ANNUALS)
def test_all_affected_annuals_substantive_financials_and_market_ownership(ticker, accession):
    body = cached_body(accession)
    legacy, _ = parse_filing(body, "10-K")
    sections, diagnostics = resolve_filing(body, "10-K", ticker)
    assert not diagnostics["unresolved_substantive"]
    old = {s.item: s for s in legacy}
    new = {s.item: s for s in sections}
    assert len(new["8"].text) > 50000
    assert "report of independent registered public accounting firm" in normalized(new["8"].text)
    if accession == "0000034088-24-000018":
        assert "heading/page fallback" in diagnostics["coverage"]["7"]["method"]
        assert "heading/page fallback" in diagnostics["coverage"]["8"]["method"]
    if ticker in {"CVX", "JPM", "XOM"}:
        assert len(new["7"].text) > 50000
        assert diagnostics["coverage"]["7A"]["target_item"] == "7"
        assert diagnostics["coverage"]["7A"]["ownership"] == "MD&A subsection"
        assert new["7A"].text == old["7A"].text
        assert new["7"].end <= new["8"].start
        assert new["7A"].end <= new["7"].start  # Distinct original reference stub.
        assert new["1"].text == old["1"].text
        assert new["1A"].text == old["1A"].text
    else:
        for item in {"1", "1A", "7", "7A"}:
            assert new[item].text == old[item].text
        assert diagnostics["coverage"]["7A"]["status"] == "extracted"


@pytest.mark.parametrize(
    "ticker,accession",
    [
        ("BAC", "0000070858-23-000142"),
        ("BAC", "0000070858-26-000394"),
        ("JPM", "0000019617-24-000453"),
        ("JPM", "0001628280-26-054343"),
    ],
)
def test_quarterly_toc_is_replaced_by_body_without_statements(ticker, accession):
    body = cached_body(accession)
    old, _ = parse_filing(body, "10-Q")
    sections, diagnostics = resolve_filing(body, "10-Q", ticker)
    by_item = {s.item: s for s in sections}
    mda = by_item["P1-2"]
    assert len(mda.text) > 100000
    assert len(mda.text) > len(next(s.text for s in old if s.item == "P1-2")) * 20
    assert not diagnostics["unresolved_substantive"]
    assert by_item["P2-1A"].text == next(s.text for s in old if s.item == "P2-1A")
    if ticker == "JPM":
        assert not any(
            normalized(b.text) == "consolidated statements of income" for b in mda.blocks
        )


def test_legacy_nvidia_fixture_stays_small_but_v2_resolves_same_filing():
    accession = "0001045810-25-000023"
    path = Path("tests/fixtures/filings") / (accession + ".html.gz")
    body = gzip.decompress(path.read_bytes())
    old, _ = parse_filing(body, "10-K")
    new, _ = resolve_filing(body, "10-K", "NVDA")
    assert len(next(s.text for s in old if s.item == "8")) < 1000
    assert len(next(s.text for s in new if s.item == "8")) > 50000


def test_all_22_absent_quarterly_risk_items_keep_source_evidence():
    path = Path("evals/results/retrieval_analyses.json")
    if not path.exists():
        pytest.skip("Requires immutable v1 source audit")
    sources = json.loads(path.read_text())["source_audit"]
    assert len(sources) == 22
    for row in sources:
        body = cached_body(row["accession"])
        assert hashlib.sha256(body).hexdigest() == row["sha256"]
        sections, diagnostics = resolve_filing(body, "10-Q", row["ticker"])
        assert "P2-1A" not in {s.item for s in sections}
        assert diagnostics["coverage"]["P2-1A"]["status"] == "source absent"
        assert diagnostics["coverage"]["P2-1A"]["evidence"]


def test_genuinely_short_market_risk_is_not_misclassified_as_a_reference():
    body = cached_body("0001628280-25-003063")
    sections, diagnostics = resolve_filing(body, "10-K", "TSLA")
    assert "Foreign Currency Risk" in next(s.text for s in sections if s.item == "7A")
    assert diagnostics["coverage"]["7A"]["status"] == "extracted"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "reason",
    ["unresolved substantive reference", "unexpected byte change", "ambiguous gold migration"],
)
async def test_labeling_cannot_bypass_v2_freeze_audit(monkeypatch, reason):
    from evals import corpus_v2
    from evals.label_retrieval import freeze_ready_corpus

    conn = AsyncMock()
    cursor = AsyncMock()
    cursor.fetchone.return_value = ({"resolver": "financial-references-v1"},)
    conn.execute.return_value = cursor

    class Pool:
        @asynccontextmanager
        async def connection(self):
            yield conn

    guard = AsyncMock(side_effect=ValueError(reason))
    monkeypatch.setattr(corpus_v2, "audit", guard)
    with pytest.raises(ValueError, match=reason):
        await freeze_ready_corpus(Pool(), "v2")
    guard.assert_awaited_once()
    assert not any(
        call.args[0].lstrip().startswith("UPDATE ") for call in conn.execute.await_args_list
    )


def test_offline_cache_rejects_missing_and_tampered_bodies_without_client(tmp_path, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("No HTTP client is allowed")

    monkeypatch.setattr("filinglens.edgar.client.EdgarClient.__init__", forbidden)
    directory = tmp_path / "offline"
    directory.mkdir()
    (directory / "snapshot.json").write_text(
        json.dumps({"snapshot_id": "offline", "cutoff": "2026-10-19"})
    )
    settings = Settings(raw_dir=tmp_path, snapshot_id="offline")
    cache = OfflineSnapshot(settings)
    url = "https://www.sec.gov/Archives/test.htm"
    key = hashlib.sha256(url.encode()).hexdigest()
    with asyncio.Runner(loop_factory=asyncio.SelectorEventLoop) as runner:
        with pytest.raises(FileNotFoundError):
            runner.run(cache.get(url))
        (directory / (key + ".json")).write_text(json.dumps({"url": url, "sha256": "bad"}))
        (directory / (key + ".body")).write_bytes(b"<html><body>tampered</body></html>")
        with pytest.raises(ValueError, match="verification failed"):
            runner.run(cache.get(url))
    assert cache.network_requests == 0

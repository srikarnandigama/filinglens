import asyncio
import hashlib
import json
import time

import httpx
import pytest
import respx

from filinglens.edgar.client import EdgarClient

URL = "https://data.sec.gov/submissions/CIK0000320193.json"


@respx.mock
async def test_success_status_sec_block_page_is_not_cached(settings):
    url = "https://www.sec.gov/Archives/edgar/data/test.htm"
    route = respx.get(url).mock(
        return_value=httpx.Response(
            200, text="<html>Your request originates from an undeclared automated tool</html>"
        )
    )
    async with EdgarClient(settings) as client:
        with pytest.raises(ValueError, match="valid filing"):
            await client.get(url, expect_filing=True)
        assert not client.paths(url)[0].exists()
        route.mock(return_value=httpx.Response(200, text="<html><p>Source text</p></html>"))
        await client.get(url, expect_filing=True)
        await client.get(url, expect_filing=True)
        assert route.call_count == 2


@respx.mock
async def test_headers_immutable_cache_and_integrity(settings):
    route = respx.get(URL).mock(return_value=httpx.Response(200, json={"ok": True}))
    async with EdgarClient(settings) as client:
        assert await client.json(URL) == {"ok": True}
        assert await client.json(URL) == {"ok": True}
        assert route.call_count == 1
        assert route.calls[0].request.headers["User-Agent"] == settings.sec_user_agent
        body, metadata = client.paths(URL)
        assert body.stem == hashlib.sha256(URL.encode()).hexdigest()
        assert json.loads(metadata.read_text())["url"] == URL
        body.write_bytes(b"corrupted")
        with pytest.raises(ValueError, match="Corrupt"):
            await client.get(URL)


@pytest.mark.parametrize("status", [429, 500, 503])
@respx.mock
async def test_retry_then_success(settings, monkeypatch, status):
    route = respx.get(URL).mock(side_effect=[httpx.Response(status), httpx.Response(200, json={})])
    monkeypatch.setattr(EdgarClient, "retry_delay", staticmethod(lambda *_: 0))
    async with EdgarClient(settings) as client:
        assert await client.json(URL) == {}
    assert route.call_count == 2


@respx.mock
async def test_nonretryable_and_invalid_json_never_cached(settings):
    route = respx.get(URL).mock(return_value=httpx.Response(403))
    async with EdgarClient(settings) as client:
        with pytest.raises(httpx.HTTPStatusError):
            await client.json(URL)
        assert not client.paths(URL)[1].exists()
        assert route.call_count == 1
        route.mock(return_value=httpx.Response(200, text="not JSON"))
        with pytest.raises(ValueError):
            await client.json(URL)
        assert not client.paths(URL)[0].exists()


@respx.mock
async def test_retry_exhaustion(settings, monkeypatch):
    route = respx.get(URL).mock(return_value=httpx.Response(503))
    monkeypatch.setattr(EdgarClient, "retry_delay", staticmethod(lambda *_: 0))
    async with EdgarClient(settings) as client:
        with pytest.raises(httpx.HTTPStatusError):
            await client.json(URL)
        assert not client.paths(URL)[1].exists()
    assert route.call_count == settings.sec_max_attempts


@respx.mock
async def test_concurrent_request_pacing(settings):
    calls = []

    def response(request):
        calls.append(time.monotonic())
        return httpx.Response(200, json={})

    respx.get(url__startswith=URL).mock(side_effect=response)
    async with EdgarClient(settings) as client:
        await asyncio.gather(*(client.json(f"{URL}?i={i}") for i in range(4)))
    assert all(b - a >= 0.115 for a, b in zip(calls, calls[1:], strict=False))


def test_retry_after():
    assert EdgarClient.retry_delay(httpx.Response(429, headers={"Retry-After": "15"}), 0) >= 15


async def test_snapshot_cutoff_cannot_change(settings):
    async with EdgarClient(settings):
        pass
    from datetime import date

    with pytest.raises(ValueError, match="different cutoff"):
        EdgarClient(settings.model_copy(update={"ingestion_cutoff": date(2026, 1, 1)}))


@respx.mock
async def test_same_url_concurrent_calls_download_once(settings):
    route = respx.get(URL).mock(return_value=httpx.Response(200, json={"ok": True}))
    async with EdgarClient(settings) as client:
        results = await asyncio.gather(*(client.json(URL) for _ in range(4)))
        assert results == [{"ok": True}] * 4
        assert route.call_count == 1


@respx.mock
async def test_transport_failure_retried(settings, monkeypatch):
    route = respx.get(URL).mock(
        side_effect=[httpx.ConnectError("connection unavailable"), httpx.Response(200, json={})]
    )
    monkeypatch.setattr(EdgarClient, "retry_delay", staticmethod(lambda *_: 0))
    async with EdgarClient(settings) as client:
        assert await client.json(URL) == {}
    assert route.call_count == 2

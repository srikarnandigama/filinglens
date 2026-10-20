"""Polite SEC access backed by immutable, checksummed response snapshots."""

import asyncio
import hashlib
import json
import random
import time
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any

import httpx

from filinglens.config import Settings


class EdgarClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.directory = settings.raw_dir / settings.snapshot_id
        self.directory.mkdir(parents=True, exist_ok=True)
        metadata = {"snapshot_id": settings.snapshot_id, "cutoff": str(settings.ingestion_cutoff)}
        marker = self.directory / "snapshot.json"
        if marker.exists():
            if json.loads(marker.read_text()) != metadata:
                raise ValueError("Snapshot ID already belongs to a different cutoff")
        else:
            with marker.open("x", encoding="utf-8") as file:
                json.dump(metadata, file)
        self.http = httpx.AsyncClient(
            headers={"User-Agent": settings.sec_user_agent, "Accept-Encoding": "gzip, deflate"},
            timeout=httpx.Timeout(60, connect=20),
            follow_redirects=True,
        )
        self._lock = asyncio.Lock()
        self._url_locks: dict[str, asyncio.Lock] = {}
        self._last_request = 0.0
        self.network_requests = 0
        self.cache_hits = 0

    async def __aenter__(self) -> "EdgarClient":
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.http.aclose()

    def paths(self, url: str) -> tuple[Path, Path]:
        key = hashlib.sha256(url.encode()).hexdigest()
        return self.directory / f"{key}.body", self.directory / f"{key}.json"

    async def _pace(self) -> None:
        async with self._lock:
            delay = 1 / self.settings.sec_requests_per_second - (
                time.monotonic() - self._last_request
            )
            if delay > 0:
                await asyncio.sleep(delay)
            self._last_request = time.monotonic()

    @staticmethod
    def retry_delay(response: httpx.Response | None, attempt: int) -> float:
        delay = min(2**attempt + random.random(), 30)
        if response is not None and (header := response.headers.get("Retry-After")):
            try:
                delay = max(delay, float(header))
            except ValueError:
                try:
                    delay = max(
                        delay, (parsedate_to_datetime(header) - datetime.now(UTC)).total_seconds()
                    )
                except (ValueError, TypeError):
                    pass
        return min(delay, 120)

    @staticmethod
    def validate_filing(body: bytes) -> None:
        lower = body.lower()
        if b"<html" not in lower or any(
            marker in lower
            for marker in (
                b"your request originates from an undeclared automated tool",
                b"request rate threshold exceeded",
                b"sec.gov | request blocked",
            )
        ):
            raise ValueError("Response is not a valid filing HTML document")

    async def get(
        self, url: str, *, expect_json: bool = False, expect_filing: bool = False
    ) -> bytes:
        async with self._url_locks.setdefault(url, asyncio.Lock()):
            return await self._get_locked(url, expect_json=expect_json, expect_filing=expect_filing)

    async def _get_locked(
        self, url: str, *, expect_json: bool = False, expect_filing: bool = False
    ) -> bytes:
        parsed = httpx.URL(url)
        if parsed.scheme != "https" or parsed.host not in {"www.sec.gov", "data.sec.gov"}:
            raise ValueError("Only HTTPS SEC URLs are allowed")
        body_path, meta_path = self.paths(url)
        if body_path.exists() and meta_path.exists():
            body = body_path.read_bytes()
            meta = json.loads(meta_path.read_text())
            if meta["url"] != url or meta["sha256"] != hashlib.sha256(body).hexdigest():
                raise ValueError(f"Corrupt snapshot response for {url}; create a new snapshot")
            self.cache_hits += 1
            if expect_filing:
                self.validate_filing(body)
            return body
        for attempt in range(self.settings.sec_max_attempts):
            await self._pace()
            response = None
            try:
                self.network_requests += 1
                response = await self.http.get(url)
                response.raise_for_status()
                if expect_json:
                    json.loads(response.content)
                body = response.content
                if expect_filing:
                    self.validate_filing(body)
                meta = {
                    "url": url,
                    "sha256": hashlib.sha256(body).hexdigest(),
                    "retrieved_at": datetime.now(UTC).isoformat(),
                    "content_type": response.headers.get("content-type", ""),
                }
                # Atomic replacement of incomplete writes; completed entries are never replaced.
                temporary = body_path.with_suffix(".tmp")
                temporary.write_bytes(body)
                temporary.replace(body_path)
                meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
                return body
            except httpx.HTTPStatusError as error:
                if error.response.status_code != 429 and error.response.status_code < 500:
                    raise
                if attempt + 1 == self.settings.sec_max_attempts:
                    raise
            except httpx.TransportError:
                if attempt + 1 == self.settings.sec_max_attempts:
                    raise
            await asyncio.sleep(self.retry_delay(response, attempt))
        raise RuntimeError("Unreachable retry state")

    async def json(self, url: str) -> Any:
        return json.loads(await self.get(url, expect_json=True))

    def manifest(self) -> dict[str, Any]:
        return {
            path.stem: json.loads(path.read_text())
            for path in sorted(self.directory.glob("*.json"))
            if path.name != "snapshot.json"
        }

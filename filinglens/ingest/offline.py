"""Read-only, verified SEC snapshot access with no HTTP client or fallback."""

import hashlib
import json

from filinglens.config import Settings
from filinglens.edgar.client import EdgarClient


class OfflineSnapshot:
    network_requests = 0

    def __init__(self, settings: Settings):
        self.directory = settings.raw_dir / settings.snapshot_id
        self.cache_hits = 0
        marker = json.loads((self.directory / "snapshot.json").read_text())
        if marker != {
            "snapshot_id": settings.snapshot_id,
            "cutoff": str(settings.ingestion_cutoff),
        }:
            raise ValueError("Snapshot identity mismatch")

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass

    async def get(self, url: str, *, expect_filing: bool = True) -> bytes:
        key = hashlib.sha256(url.encode()).hexdigest()
        metadata = json.loads((self.directory / f"{key}.json").read_text())
        body = (self.directory / f"{key}.body").read_bytes()
        if metadata["url"] != url or metadata["sha256"] != hashlib.sha256(body).hexdigest():
            raise ValueError("Cached body verification failed")
        if expect_filing:
            EdgarClient.validate_filing(body)
        self.cache_hits += 1
        return body

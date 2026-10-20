"""Canonical identities independent of insertion order and database sequences."""

import hashlib
import json
import unicodedata
from typing import Any


def canonical(text: str) -> str:
    return unicodedata.normalize("NFC", text.replace("\r\n", "\n").replace("\r", "\n"))


def digest(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical(raw).encode("utf-8")).hexdigest()


def identity(prefix: str, *parts: Any) -> str:
    return prefix + "_" + digest(["identity-v1", *parts])

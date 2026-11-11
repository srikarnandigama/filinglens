"""B2 stuffed context: the financial statements of the filings that hold a question's gold (D089).

Corpus v2 has no 10-Q financial statements and its 10-K Item 8 sections can be very large, so the
text comes from the frozen raw snapshot. The M2 HTML block parser is reused read-only. Token counts
are estimated as characters / 4 (no API calls in this module).
"""

import re
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import Any

from filinglens.ingest.parse import Block, html_blocks

CHARS_PER_TOKEN = 4
FILING_CAP_TOKENS = 25_000
QUESTION_CAP_TOKENS = 50_000
EXTRACTOR_VERSION = "b2-statements-v1"
# Matched with whitespace removed: some filings split heading words ("INC OME STATEMENTS").
STATEMENT = re.compile(
    r"(?:statements?of(?:consolidated)?(?:operations|income|earnings)|incomestatements?)", re.I
)
# A contents entry ends in a 1-3 digit page number; statement headings may end in years.
TOC_PAGE = re.compile(r"(?<![\d,.])\d{1,3}\s*$")
NOTES = re.compile(
    r"^notes\s+to\s+(?:the\s+)?(?:condensed\s+)?consolidated\s+financial\s+statements", re.I
)
NUMBER = re.compile(r"\d[\d,]{2,}")
PROSE_CHARS = 200  # statement headings are followed by a units line and rows, not paragraphs


@dataclass
class FilingWindow:
    accession: str
    text: str
    fallback: bool
    tokens: int


@dataclass
class B2Context:
    question_id: str
    text: str
    filings: list[str]
    tokens: int
    truncated: bool
    fallback: list[str]
    gold_visible: bool
    missing_values: list[str] = field(default_factory=list)

    def meta(self) -> dict[str, Any]:
        return {
            "question_id": self.question_id,
            "filings": self.filings,
            "tokens_est": self.tokens,
            "context_truncated": self.truncated,
            "fallback_filings": self.fallback,
            "gold_visible": self.gold_visible,
            "missing_values": self.missing_values,
            "extractor_version": EXTRACTOR_VERSION,
        }


def tokens(text: str) -> int:
    return -(-len(text) // CHARS_PER_TOKEN)


def statements_window(blocks: list[Block], cap_tokens: int = FILING_CAP_TOKENS) -> tuple[str, bool]:
    """Income statement through the cash-flow statement, up to the notes; capped.

    The start is a heading block (not a table-of-contents row) followed within a few blocks by
    numeric table rows. Without one, the first cap_tokens of the filing are used (fallback).
    """
    start = None
    for i, block in enumerate(blocks):
        heading = block.text.replace("|", " ").strip()
        if (
            len(heading) > 160
            or not STATEMENT.search(re.sub(r"\s+", "", heading))
            or TOC_PAGE.search(heading)
        ):
            continue  # long prose, or a table-of-contents entry ending in a page number
        numeric = 0
        for b in blocks[i + 1 : i + 12]:
            if b.kind != "row" and len(b.text) > PROSE_CHARS:
                break  # a policy note titled "Income Statement - ...", not a statement heading
            numeric += b.kind == "row" and bool(NUMBER.search(b.text))
            if numeric >= 4:
                start = i
                break
        if start is not None:
            break
    fallback = start is None
    begin = 0 if fallback else start
    lines: list[str] = []
    for block in blocks[begin:]:
        if not fallback and lines and block.kind != "row" and NOTES.match(block.text):
            break
        lines.append(block.text)
    text = "\n".join(lines)
    limit = cap_tokens * CHARS_PER_TOKEN
    return (text[:limit], fallback)


def printed_forms(value: Decimal) -> list[str]:
    """How a stored raw value can appear in a filing table: raw, thousands or millions."""
    forms = []
    negative = value < 0
    magnitude = abs(value)
    for scale in (Decimal(1), Decimal(1000), Decimal(1_000_000)):
        scaled = magnitude / scale
        if scaled != scaled.to_integral_value():
            continue
        text = f"{int(scaled):,}"
        forms.append(f"({text})" if negative else text)
    if magnitude != magnitude.to_integral_value():  # per-share amounts
        forms.append(format(magnitude.normalize(), "f"))
    return forms


def visible(value: Decimal, text: str) -> bool:
    for form in printed_forms(value):
        if re.search(rf"(?<![\d.,]){re.escape(form)}(?![\d,]|\.\d)", text):
            return True
        if form.startswith("("):
            plain = form[1:-1]
            if re.search(rf"\(\s*{re.escape(plain)}\s*\)", text):
                return True
    return False


def printed_inputs(question: dict[str, Any]) -> list[Decimal]:
    """Values that a filing actually prints for this gold: direct facts and derivation inputs."""
    values = []
    for item in question["computation"]["inputs"]:
        if item["derived"]:
            values.extend(Decimal(d["value"]) for d in item["derivation_inputs"])
        else:
            values.append(Decimal(item["value"]))
    return values


def filings_for(question: dict[str, Any]) -> list[tuple[str, str]]:
    """(accession, filed) of every filing holding a printed gold input, newest first."""
    found: dict[str, str] = {}
    for item in question["computation"]["inputs"]:
        if item["derived"]:
            for d in item["derivation_inputs"]:
                found[d["accession"]] = d.get("filed") or ""
        elif item.get("source_accession"):
            found.setdefault(item["source_accession"], item.get("source_filed") or "")
    return sorted(found.items(), key=lambda kv: (kv[1], kv[0]), reverse=True)


def build_context(
    question: dict[str, Any],
    windows: dict[str, FilingWindow],
    cap_tokens: int = QUESTION_CAP_TOKENS,
) -> B2Context:
    """Concatenate the windows newest first; if over the cap, trim the oldest filing first."""
    order = [acc for acc, _ in filings_for(question)]
    parts = [[acc, windows[acc].text] for acc in order if acc in windows]
    truncated = False
    while parts and sum(tokens(t) for _, t in parts) > cap_tokens:
        truncated = True
        over = sum(tokens(t) for _, t in parts) - cap_tokens
        last = parts[-1]
        keep = max(0, len(last[1]) - over * CHARS_PER_TOKEN)
        if keep == 0:
            parts.pop()
        else:
            last[1] = last[1][:keep]
    text = "\n\n".join(f"=== Filing {acc} ===\n{body}" for acc, body in parts)
    missing = [format(v, "f") for v in printed_inputs(question) if not visible(v, text)]
    return B2Context(
        question_id=question["id"],
        text=text,
        filings=[acc for acc, _ in parts],
        tokens=tokens(text),
        truncated=truncated,
        fallback=[acc for acc in order if acc in windows and windows[acc].fallback],
        gold_visible=not missing,
        missing_values=missing,
    )


def load_windows(
    accessions: set[str], database_url: str, raw_dir: Path, snapshot_id: str
) -> dict[str, FilingWindow]:
    """Statements windows for the given filings, read from the frozen raw snapshot."""
    import gzip
    import hashlib

    import psycopg

    from filinglens.db import connection_options

    with psycopg.connect(database_url, **connection_options(database_url)) as conn:
        conn.execute("SET default_transaction_read_only = on")
        urls = dict(
            conn.execute(
                "SELECT accession, url FROM filings WHERE accession = ANY(%s)",
                (sorted(accessions),),
            ).fetchall()
        )
    out = {}
    for accession, url in urls.items():
        path = raw_dir / snapshot_id / (hashlib.sha256(url.encode()).hexdigest() + ".body")
        body = path.read_bytes()
        try:
            body = gzip.decompress(body)
        except OSError:
            pass
        text, fallback = statements_window(html_blocks(body))
        out[accession] = FilingWindow(accession, text, fallback, tokens(text))
    return out


# ---------------------------------------------------------------- frozen metadata (D089)


def meta_path() -> Path:
    from filinglens.config import ROOT

    return ROOT / "evals" / "b2_contexts_v1.meta.jsonl"


def text_sha256(text: str) -> str:
    import hashlib

    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def build_meta(
    questions: list[dict[str, Any]], database_url: str, raw_dir: Path, snapshot_id: str
) -> list[dict[str, Any]]:
    """B2 context metadata for the frozen sample: visibility, truncation and the text hash."""
    sample = [q for q in questions if q.get("sample_100")]
    accessions = {acc for q in sample for acc, _ in filings_for(q)}
    windows = load_windows(accessions, database_url, raw_dir, snapshot_id)
    rows = []
    for q in sorted(sample, key=lambda q: q["id"]):
        context = build_context(q, windows)
        rows.append(context.meta() | {"text_sha256": text_sha256(context.text)})
    return rows


def write_meta(rows: list[dict[str, Any]], path: Path | None = None) -> Path:
    import json

    path = path or meta_path()
    path.write_text(
        "".join(json.dumps(r, sort_keys=True) + "\n" for r in rows), encoding="utf-8", newline="\n"
    )
    return path


def frozen_context_loader(settings: Any, path: Path | None = None):
    """(question) -> (text, meta): rebuilt from the frozen snapshot, verified against the meta."""
    import json

    rows = {
        r["question_id"]: r
        for r in map(json.loads, (path or meta_path()).read_text(encoding="utf-8").splitlines())
    }
    windows: dict[str, FilingWindow] = {}

    def load(question: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        meta = rows.get(question["id"])
        if meta is None:
            raise KeyError(f"{question['id']} is not in the frozen B2 sample")
        missing = {acc for acc, _ in filings_for(question)} - set(windows)
        if missing:
            windows.update(
                load_windows(missing, settings.database_url, settings.raw_dir, settings.snapshot_id)
            )
        context = build_context(question, windows)
        if text_sha256(context.text) != meta["text_sha256"]:
            raise ValueError(f"B2 context for {question['id']} differs from its frozen hash")
        return context.text, meta

    return load

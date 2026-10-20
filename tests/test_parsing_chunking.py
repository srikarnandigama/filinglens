"""Real SEC regression fixtures plus boundary and coverage checks."""

import gzip
import hashlib
import json
from pathlib import Path

import pytest

from filinglens.ingest.chunk import QUERY_BUDGET, chunk_section, count, model_windows
from filinglens.ingest.identity import identity
from filinglens.ingest.models import MODEL_DIR, tokenizer
from filinglens.ingest.parse import Block, Section, html_blocks, parse_filing

FIXTURE = json.loads((Path(__file__).parent / "fixtures/revenue_expected.json").read_text())


@pytest.fixture(scope="module")
def tokenizers():
    if not (MODEL_DIR / "revisions.json").exists():
        pytest.skip("Prepare the pinned model tokenizers for model integration tests")
    return tokenizer("embed"), tokenizer("rerank")


@pytest.mark.parametrize(
    "ticker,period,expected,phrase",
    [
        ("AAPL", "FY", {"1", "1A", "7", "7A", "8"}, "Company Background"),
        ("MSFT", "Q3", {"P1-2", "P2-1A"}, "Note About Forward-Looking Statements"),
        ("NVDA", "FY", {"1", "1A", "7", "7A", "8"}, "Our Company"),
    ],
)
def test_three_real_filings_choose_body_not_toc(ticker, period, expected, phrase):
    company = next(c for c in FIXTURE["companies"] if c["ticker"] == ticker)
    source = company["sources"][period]
    path = Path(__file__).parent / "fixtures/filings" / (source["accession"] + ".html.gz")
    body = gzip.decompress(path.read_bytes())
    assert hashlib.sha256(body).hexdigest() == source["sha256"]
    sections, diagnostic = parse_filing(body, source["form"])
    assert {s.item for s in sections} == expected
    assert not diagnostic["missing"] and not diagnostic["ambiguous"]
    assert diagnostic["candidate_count"] > len(expected)
    assert any(phrase in s.text for s in sections)
    for section in sections:
        assert section.start < section.end
        assert len(section.text) >= 100
    if ticker == "MSFT":
        mda = next(s for s in sections if s.item == "P1-2")
        risks = next(s for s in sections if s.item == "P2-1A")
        assert len(mda.text) > 50000  # Running headers must not truncate MD&A.
        assert "LIQUIDITY AND CAPITAL RESOURCES" in mda.text
        assert "Impairment of Investment Securities" in mda.text
        assert "GENERAL RISKS" in risks.text
        assert "SHARE REPURCHASES AND DIVIDENDS" not in risks.text
    if ticker == "NVDA":
        # The actual Item 8 incorporates statements by reference; do not swallow Part IV.
        item8 = next(s for s in sections if s.item == "8")
        assert "Notes thereto included in this Annual Report" in item8.text
        assert len(item8.text) < 1000


def test_visible_text_tables_hidden_metadata_and_missing_sections():
    blocks = html_blocks(b"""<html><body><script>bad()</script><style>bad</style>
    <div style='display:none'>secret</div><ix:hidden>metadata</ix:hidden>
    <p>Visible <ix:nonfraction>reported text</ix:nonfraction>.</p>
    <table><tr><th>Name</th><th>Value</th></tr><tr><td>row</td><td>value</td></tr></table>
    </body></html>""")
    text = "\n".join(b.text for b in blocks)
    assert "secret" not in text and "metadata" not in text and "bad" not in text
    assert "reported text" in text and "row | value" in text
    assert next(b for b in blocks if b.text == "row | value").header == "Name | Value"
    sections, diag = parse_filing(b"<p>No item headings</p>", "10-K")
    assert not sections and diag["missing"]


def test_sec_style_td_headers_are_repeated_without_changing_source_rows(tokenizers):
    embed, rerank = tokenizers
    body = (
        "<html><body><table><tr><td>Description</td><td>Period</td></tr>"
        + "".join(
            f"<tr><td>Source row {i}</td><td>{'description ' * 100}</td></tr>" for i in range(5)
        )
        + "</table></body></html>"
    ).encode()
    blocks = html_blocks(body)
    assert all(b.header == "Description | Period" for b in blocks)
    section = Section("8", "Statements", blocks, 0, len(blocks))
    chunks = chunk_section(
        section, section_id="s", header="TEST 10-K 2025 FY", embed_tok=embed, rerank_tok=rerank
    )
    assert len(chunks) > 1
    assert all("Description | Period" in c.text for c in chunks)
    assert all(any(b.text in c.text for c in chunks) for b in blocks)


def test_long_prose_coverage_overlap_and_pair_budgets(tokenizers):
    embed, rerank = tokenizers
    text = " ".join(f"sourceword{i}" for i in range(1200))
    section = Section("7", "MD&A", [Block(text)], 0, 1)
    kwargs = dict(
        section_id="section", header="TEST 10-K 2025 FY — MD&A", embed_tok=embed, rerank_tok=rerank
    )
    first = chunk_section(section, **kwargs)
    assert len(first) > 3
    assert first == chunk_section(section, **kwargs)
    assert all(word in " ".join(c.text for c in first) for word in text.split())
    for chunk in first:
        assert not chunk.oversized_row
        assert chunk.token_count <= 460
        passage_tokens = len(rerank.encode(chunk.text, add_special_tokens=False))
        assert passage_tokens + QUERY_BUDGET + rerank.num_special_tokens_to_add(pair=True) <= 512
    assert any(
        set(a.text.split()[-15:]) & set(b.text.split()[:20])
        for a, b in zip(first, first[1:], strict=False)
    )


def test_table_headers_rows_and_only_oversized_exception(tokenizers):
    embed, rerank = tokenizers
    header = "Column | Description"
    rows = [Block(header, "row", 1, header)] + [
        Block(f"row{i} | " + "descriptive content " * 75, "row", 1, header) for i in range(6)
    ]
    huge = "oversized | " + "longcell " * 1800
    rows.append(Block(huge, "row", 1, header))
    section = Section("8", "Statements", rows, 0, len(rows))
    chunks = chunk_section(
        section,
        section_id="s",
        header="TEST 10-K 2025 FY — Statements",
        embed_tok=embed,
        rerank_tok=rerank,
    )
    assert all(any(row.text in c.text for c in chunks) for row in rows)
    oversized = [c for c in chunks if c.oversized_row]
    assert len(oversized) == 1 and huge in oversized[0].text
    assert all(header in c.text for c in chunks)
    windows = model_windows(huge, embed, prefix="TEST\n")
    assert len(windows) > 1
    assert all(count(embed, "TEST\n" + w) <= 512 for w in windows)


def test_hash_identity_is_order_independent_and_content_sensitive():
    assert identity("chk", {"a": 1, "b": 2}) == identity("chk", {"b": 2, "a": 1})
    assert identity("chk", "same", 0) != identity("chk", "same", 1)
    assert identity("chk", "text") != identity("chk", "changed")

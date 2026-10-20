"""Tokenizer-budgeted chunks; original table rows are indivisible citation units."""

from dataclasses import dataclass
from functools import lru_cache
from typing import Any

from filinglens.ingest.identity import identity
from filinglens.ingest.parse import Block, Section

CHUNKER_VERSION = "bge-budget-v2"
TARGET = 380
MAXIMUM = 460
OVERLAP = 50
QUERY_BUDGET = 48
TYPICAL_QUERY = "Why did management report a decline in operating income during this fiscal period?"


@dataclass(frozen=True)
class Chunk:
    id: str
    ordinal: int
    text: str
    token_count: int
    source_start: int
    source_end: int
    oversized_row: bool


@lru_cache(maxsize=4096)
def count(tok: Any, text: str) -> int:
    return len(tok.encode(text, add_special_tokens=True))


@lru_cache(maxsize=4096)
def fits(text: str, header: str, embed_tok: Any, rerank_tok: Any) -> bool:
    return (
        count(embed_tok, header + "\n" + text) <= MAXIMUM
        and len(rerank_tok.encode(text, add_special_tokens=False))
        + QUERY_BUDGET
        + rerank_tok.num_special_tokens_to_add(pair=True)
        <= 512
        and len(rerank_tok.encode(TYPICAL_QUERY, text_pair=text, add_special_tokens=True)) <= 512
    )


def split_paragraph(text: str, header: str, embed_tok: Any, rerank_tok: Any) -> list[str]:
    """Split at whitespace without decode/re-encode text loss; hard-split long single words."""
    parts = []

    def fragment_fits(value: str) -> bool:
        return (
            fits(value, header, embed_tok, rerank_tok)
            and count(embed_tok, header + "\n" + value) <= TARGET - OVERLAP
        )

    while text:
        if fragment_fits(text):
            parts.append(text)
            break
        low, high = 1, len(text)
        while low < high:
            mid = (low + high + 1) // 2
            if fragment_fits(text[:mid]):
                low = mid
            else:
                high = mid - 1
        end = text.rfind(" ", 0, low + 1)
        if end < low // 2:
            end = low
        parts.append(text[:end])
        text = text[end:].lstrip()
    return parts


def chunk_section(
    section: Section, *, section_id: str, header: str, embed_tok: Any, rerank_tok: Any
) -> list[Chunk]:
    units: list[tuple[Block, int]] = []
    for index, block in enumerate(section.blocks):
        fragments = (
            [block.text]
            if block.kind == "row"
            else split_paragraph(block.text, header, embed_tok, rerank_tok)
        )
        units.extend((Block(t, block.kind, block.table, block.header), index) for t in fragments)
    output: list[Chunk] = []
    start = 0
    carry = ""
    while start < len(units):
        end = start
        texts: list[str] = [carry] if carry else []
        first = units[start][0]
        if first.kind == "row" and first.header and first.text != first.header:
            texts.append(first.header)
        oversized = False
        while end < len(units):
            block = units[end][0]
            candidate = "\n\n".join([*texts, block.text])
            if not fits(candidate, header, embed_tok, rerank_tok):
                if end == start:
                    if carry:
                        texts = []
                        carry = ""
                        continue
                    # Only an indivisible table row can exceed the budget.
                    if block.kind != "row":
                        raise ValueError("Non-table fragment exceeds token budget")
                    texts.append(block.text)
                    end += 1
                    oversized = True
                break
            texts.append(block.text)
            end += 1
            if count(embed_tok, header + "\n" + candidate) >= TARGET:
                break
        text = "\n\n".join(texts)
        ordinal = len(output)
        output.append(
            Chunk(
                identity("chk", section_id, ordinal, text),
                ordinal,
                text,
                count(embed_tok, header + "\n" + text),
                units[start][1],
                units[end - 1][1] + 1,
                oversized,
            )
        )
        if end == len(units):
            break
        carry = ""
        if units[end - 1][0].kind != "row" and units[end][0].kind != "row":
            previous = units[end - 1][0].text
            offsets = embed_tok(previous, add_special_tokens=False, return_offsets_mapping=True)[
                "offset_mapping"
            ]
            if len(offsets) > OVERLAP:
                carry = previous[offsets[-OVERLAP][0] :]
        start = end
    return output


def model_windows(text: str, tok: Any, *, prefix: str = "", query: str | None = None) -> list[str]:
    """Used only for flagged rows (or query-time reranker budget differences)."""
    offsets = tok(text, add_special_tokens=False, return_offsets_mapping=True)["offset_mapping"]
    special = tok.num_special_tokens_to_add(pair=query is not None)
    reserve = len(tok.encode(query or prefix, add_special_tokens=False))
    width = 512 - reserve - special - 8
    if width < 32:
        raise ValueError("Query/header too long for a useful model input")
    result = []
    start = 0
    while start < len(offsets):
        end = min(start + width, len(offsets))
        result.append(text[offsets[start][0] : offsets[end - 1][1]])
        if end == len(offsets):
            break
        start = end - min(50, width // 4)
    return result or [""]

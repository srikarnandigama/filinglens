"""DOM blocks and deterministic SEC Item boundaries; filing text is only data."""

import re
from dataclasses import asdict, dataclass

from selectolax.lexbor import LexborHTMLParser as HTMLParser
from selectolax.lexbor import LexborNode as Node

from filinglens.ingest.identity import canonical

PARSER_VERSION = "sec-dom-v2"
TITLES = {
    "1": "Business",
    "1A": "Risk Factors",
    "7": "Management's Discussion and Analysis",
    "7A": "Market Risk",
    "8": "Financial Statements",
    "P1-2": "Management's Discussion and Analysis",
    "P2-1A": "Risk Factors",
}
ITEM = re.compile(r"^ITEM\s+(\d{1,2}[A-C]?)\s*[.::\-–—]?\s*(.*)$", re.I)
PART = re.compile(r"^PART\s+(II|I)\b[.\s:—–-]*(.*)$", re.I)
BLOCK_TAGS = {"div", "p", "table", "h1", "h2", "h3", "h4", "li", "section", "article"}


@dataclass(frozen=True)
class Block:
    text: str
    kind: str = "paragraph"
    table: int | None = None
    header: str | None = None


@dataclass(frozen=True)
class Section:
    item: str
    title: str
    blocks: list[Block]
    start: int
    end: int
    occurrence: int = 0

    @property
    def text(self) -> str:
        return "\n\n".join(b.text for b in self.blocks)

    def serialized_blocks(self) -> list[dict]:
        return [asdict(b) for b in self.blocks]


def clean(value: str) -> str:
    return canonical(re.sub(r"\s+", " ", value.replace("\xa0", " ")).strip())


def html_blocks(body: bytes) -> list[Block]:
    try:
        decoded = body.decode("utf-8")
    except UnicodeDecodeError:
        decoded = body.decode("windows-1252")
    tree = HTMLParser(decoded)
    for node in tree.css("script, style, noscript, ix\\:hidden, ix\\:header, [hidden]"):
        node.decompose()
    for node in tree.css("[style]"):
        if re.search(
            r"(?:display\s*:\s*none|visibility\s*:\s*hidden)",
            node.attributes.get("style", ""),
            re.I,
        ):
            node.decompose()
    output: list[Block] = []
    tables = 0

    def walk(node: Node) -> None:
        nonlocal tables
        if node.tag == "table":
            tables += 1
            number = tables
            header = None
            table_rows = []
            for row in node.css("tr"):
                # Nested tables are emitted only once by their own traversal.
                parent = row.parent
                while parent is not None and parent.tag != "table":
                    parent = parent.parent
                if parent != node:
                    continue
                cells = [clean(c.text(separator=" ")) for c in row.css("th, td")]
                if not any(cells):
                    continue
                text = " | ".join(cells)
                if header is None and row.css_first("th") is not None:
                    header = text
                table_rows.append((text, len(cells)))
            # SEC financial tables commonly use styled td cells for every header.
            # Infer only a short leading row of a multi-column, multi-row table.
            if header is None and len(table_rows) > 1:
                leading = table_rows[0][0]
                if (
                    max(size for _, size in table_rows) > 1
                    and len(leading) <= 400
                    and not ITEM.match(clean(leading.replace("|", " ")))
                    and not PART.match(clean(leading.replace("|", " ")))
                ):
                    header = leading
            output.extend(Block(text, "row", number, header) for text, _ in table_rows)
            return
        children = []
        child = node.child
        while child is not None:
            children.append(child)
            child = child.next
        if node.tag in BLOCK_TAGS and not any(
            node.css_first(tag) is not None for tag in BLOCK_TAGS
        ):
            value = clean(node.text(separator=" "))
            if value:
                output.append(Block(value))
            return
        pending: list[str] = []

        def flush() -> None:
            value = clean(" ".join(pending))
            if value:
                output.append(Block(value))
            pending.clear()

        for child in children:
            if child.tag in BLOCK_TAGS or any(child.css_first(t) for t in BLOCK_TAGS):
                flush()
                walk(child)
            else:
                pending.append(child.text(separator=" "))
        flush()

    walk(tree.body or tree.root)
    return output


def split_sections(blocks: list[Block], form: str) -> tuple[list[Section], dict]:
    candidates: list[tuple[int, str]] = []
    part = "1"
    for i, block in enumerate(blocks):
        value = clean(block.text.replace("|", " "))
        if len(value) > 240:
            continue
        if match := PART.match(value):
            new_part = "2" if match[1].upper() == "II" else "1"
            if new_part != part:
                candidates.append((i, "PART" + new_part))
            part = new_part
            # Some filers combine Part and Item in the same block.
            value = match[2]
        if match := ITEM.match(value):
            if match[2].startswith(","):
                continue  # Running page header such as "Item 3, 4".
            item = match[1].upper()
            if form == "10-Q":
                item = f"P{part}-{item}"
            candidates.append((i, item))
    wanted = {"1", "1A", "7", "7A", "8"} if form == "10-K" else {"P1-2", "P2-1A"}
    selected: list[Section] = []
    diagnostics: dict = {"candidate_count": len(candidates), "missing": [], "ambiguous": []}
    for item in sorted(wanted):
        spans = []
        for pos, (start, key) in enumerate(candidates):
            if key != item:
                continue
            end = next(
                (index for index, other in candidates[pos + 1 :] if other != key), len(blocks)
            )
            content = blocks[start:end]
            # TOC entries have tiny spans. Body spans win by substantive text length.
            size = sum(len(b.text) for b in content)
            spans.append((size, start, end))
        if not spans:
            diagnostics["missing"].append(item)
            continue
        spans.sort(reverse=True)
        size, start, end = spans[0]
        if size < 80:
            diagnostics["ambiguous"].append(item)
            continue
        selected.append(Section(item, TITLES[item], blocks[start:end], start, end))
    return sorted(selected, key=lambda s: s.start), diagnostics


def parse_filing(body: bytes, form: str) -> tuple[list[Section], dict]:
    return split_sections(html_blocks(body), form)

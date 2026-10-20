"""Resolve primary-document financial references without changing legacy splitting.

Caption boundaries are matched against visible source blocks, never generated text.
Market risk follows the source's ownership: a subsection of MD&A stays in Item 7.
"""

import re

from selectolax.lexbor import LexborHTMLParser

from filinglens.ingest.parse import TITLES, Section, clean, html_blocks, split_sections

RESOLVER_VERSION = "financial-references-v1"


def normalized(text: str) -> str:
    return clean(text.replace("|", " ")).casefold().replace("\u2019", "'")


def resolve_filing(body: bytes, form: str, ticker: str) -> tuple[list[Section], dict]:
    blocks = html_blocks(body)
    sections, diagnostics = split_sections(blocks, form)
    values = [normalized(b.text) for b in blocks]
    coverage = {}
    replacements = {}

    def find(pattern, after=0, *, body_caption=False):
        matches = [
            i
            for i in range(after, len(values))
            if re.search(pattern, values[i]) and (not body_caption or blocks[i].kind != "row")
        ]
        if not matches:
            raise ValueError(f"Unresolved substantive reference: {ticker} {form}: {pattern}")
        return matches[0]

    def span(item, start, end, method="source-caption boundaries"):
        if end <= start or sum(len(b.text) for b in blocks[start:end]) < 2000:
            raise ValueError(f"Non-substantive resolved span: {ticker} {item}")
        replacements[item] = Section(item, TITLES[item], blocks[start:end], start, end)
        coverage[item] = {
            "status": "resolved",
            "method": method,
            "source": "primary document",
            "start_block": start,
            "end_block_exclusive": end,
            "first_line": blocks[start].text,
            "last_line": blocks[end - 1].text,
        }

    if form == "10-K" and ticker in {"CVX", "JPM", "XOM"}:
        if ticker == "CVX":
            start = find(r"^management's discussion.*financial table of contents")
            market_pattern = r"^financial and derivative instrument market risk$"
            end_pattern = r"^item 15\b"
        elif ticker == "JPM":
            start = find(r"^management's discussion and analysis$")
            market_pattern = r"^market risk management$"
            end_pattern = r"^signatures$"
        else:
            financial = find(r"^financial section$")
            # TOC captions can omit their page number, but remain table rows.
            start = find(
                r"^management's discussion and analysis of financial condition "
                r"and results of operations$",
                financial + 1,
                body_caption=True,
            )
            market_pattern = r"^market risks$"
            end_pattern = r"^signatures$"
        end = find(r"^management's report on internal control", start + 1)
        market = find(market_pattern, start + 1)
        if not start < market < end:
            raise ValueError("Market-risk ownership cannot be established")
        span("7", start, end)
        coverage["7A"] = {
            "status": "reference covered elsewhere",
            "target_item": "7",
            "ownership": "MD&A subsection",
            "market_risk_start_block": market,
            "source": "primary document",
            "first_line": blocks[market].text,
        }
        # Retain the distinct Item 7A cross-reference, not a second market-risk span.
        audit = find(r"^report of independent registered public accounting firm$", end + 1)
        span("8", audit, find(end_pattern, audit + 1))
    elif form == "10-K" and ticker in {"DIS", "NVDA"}:
        if ticker == "DIS":
            index = find(r"^index to financial statements and supplemental data$")
            start = find(r"^report of independent registered public accounting firm$", index + 1)
            end = len(blocks)
        else:
            index = find(r"^item 15\..*financial statement schedules$")
            start = find(r"^report of independent registered public accounting firm$", index + 1)
            end = find(r"^(schedule ii|exhibit index)\b", start + 1)
        span("8", start, end)
    elif form == "10-Q" and ticker in {"BAC", "JPM"}:
        if ticker == "BAC":
            start = find(r"^item 2\..*management", body_caption=True)
            end = find(r"^item 3\.", start + 1)
        else:
            start = find(r"^consolidated financial highlights(?:\s*\(unaudited\))?$")
            end = find(r"^consolidated statements of income(?:\s*\(unaudited\))?$", start + 1)
        span("P1-2", start, end)
    if replacements:
        # Retain the source's reference and verified internal destinations as
        # provenance. Body captions, not TOC labels, determine the actual spans.
        try:
            decoded = body.decode("utf-8")
        except UnicodeDecodeError:
            decoded = body.decode("windows-1252")
        tree = LexborHTMLParser(decoded)
        destinations = {n.attributes["id"] for n in tree.css("[id]")}
        links = [
            {"href": n.attributes["href"], "label": clean(n.text(separator=" "))}
            for n in tree.css("a[href]")
            if n.attributes["href"].startswith("#") and n.attributes["href"][1:] in destinations
        ]
        for item, replacement in replacements.items():
            original = next((s for s in sections if s.item == item), None)
            pattern = (
                r"financial statements|consolidated|independent registered"
                if item == "8"
                else r"discussion and analysis|financial highlights"
            )
            anchors = [link for link in links if re.search(pattern, normalized(link["label"]))]
            coverage[item]["internal_reference_destinations"] = anchors[:20]
            coverage[item]["original_reference"] = original.text if original else None
            coverage[item]["method"] = (
                "verified same-primary internal references and body-caption boundaries"
                if anchors
                else "heading/page fallback in the same primary document"
            )
            if replacement.end > len(blocks):
                raise ValueError("Source span exceeds primary document")
    sections = [replacements.pop(s.item, s) for s in sections] + list(replacements.values())
    for section in sections:
        if section.item in coverage:
            continue
        text = normalized(section.text)
        if (
            section.item == "7A"
            and len(text) < 2000
            and re.search(r"(item 7\b|discussion and analysis|md&a)", text)
        ):
            coverage[section.item] = {
                "status": "reference covered elsewhere",
                "target_item": "7",
                "ownership": "MD&A subsection",
                "source": "primary document",
            }
        else:
            unresolved = (
                section.item in {"7", "8"}
                and len(text) < 2000
                and re.search(r"incorporated.*reference|presented.*table of contents", text)
            )
            coverage[section.item] = {
                "status": "unresolved" if unresolved else "extracted",
                "source": "primary document",
            }
    for item in diagnostics["missing"]:
        if form == "10-Q" and ticker in {"JNJ", "XOM"} and item == "P2-1A":
            mentions = [
                " ".join(b.text for b in blocks[max(0, i - 1) : i + 3])
                for i, b in enumerate(blocks)
                if re.search(r"item\s*1a", b.text, re.I)
            ]
            # Only prose references to annual reports are present, not a quarterly item.
            if len(mentions) != 1 or not re.search(r"10.?k|annual report", mentions[0], re.I):
                raise ValueError("Quarterly risk absence requires source review")
            coverage[item] = {
                "status": "source absent",
                "source": "primary document",
                "evidence": mentions,
                "reason": "Only an annual-report prose reference; no quarterly Item 1A heading",
            }
        else:
            coverage[item] = {"status": "unresolved", "source": "primary document"}
    for item in replacements:
        if item in diagnostics["missing"]:
            diagnostics["missing"].remove(item)
    diagnostics["coverage"] = coverage
    diagnostics["resolver"] = RESOLVER_VERSION
    by_item = {s.item: s for s in sections}
    for item, detail in coverage.items():
        if detail["status"] == "reference covered elsewhere":
            target = by_item.get(detail["target_item"])
            if target is None or len(target.text) < 2000:
                raise ValueError(f"Unresolved reference target: {item}")
    diagnostics["unresolved_substantive"] = [
        item for item, value in coverage.items() if value["status"] == "unresolved"
    ]
    ordered = sorted(sections, key=lambda s: s.start)
    for left, right in zip(ordered, ordered[1:], strict=False):
        if left.end > right.start:
            raise ValueError(f"Duplicate source ownership: {left.item} and {right.item}")
    return ordered, diagnostics

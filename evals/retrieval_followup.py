"""Read-only post-fix pool, overlap and cached-source analyses; never assigns labels."""

import asyncio
import hashlib
import json
import re
import sys
import unicodedata
from collections import Counter
from unittest.mock import patch

from psycopg.rows import dict_row
from selectolax.lexbor import LexborHTMLParser

from evals.label_retrieval import candidates
from evals.retrieval_audit import CORPUS_ID, CROSS_YEAR, validate
from evals.retrieval_eval import cache_path, cell, check_reranker_pool, report
from filinglens.config import ROOT, Settings
from filinglens.db import pool_for
from filinglens.retrieval.service import MODES, RETRIEVAL_VERSION, SearchService

RESULTS = ROOT / "evals/results"


def shingles(text: str) -> set[tuple[str, ...]]:
    words = re.findall(r"\w+", unicodedata.normalize("NFKC", text).casefold())
    return {tuple(words[i : i + 5]) for i in range(len(words) - 4)}


def containment(a: set, b: set) -> float:
    """Five-word overlap of the smaller text; threshold fixed in D032 before analysis."""
    return len(a & b) / min(len(a), len(b)) if min(len(a), len(b)) >= 20 else 0.0


def unjudged(ranked: list[str], pool: set[str], gold: set[str], k: int) -> dict:
    top = ranked[:k]
    unseen = [key for key in top if key not in pool]
    unknown = [key for key in unseen if key not in gold]
    return {
        "k": k,
        "returned": len(top),
        "outside_pool": len(unseen),
        "unjudged": len(unknown),
        "fraction": len(unknown) / len(top) if top else 0.0,
        "unjudged_ids": unknown,
    }


async def reconstruct_pools(pool, records: list[dict], pre: dict) -> dict[str, set[str]]:
    """Replay the exact old definition from valid v1 caches; fail rather than call v2."""

    class CacheOnlySearch(SearchService):
        async def _search(self, *args, **kwargs):
            raise ValueError("Required v1 cache missing; cannot reconstruct from v2 rankings")

    by_key = {(d["question_id"], d["mode"]): d["ranked_ids"] for d in pre["details"]}
    service = CacheOnlySearch(pool, CORPUS_ID)
    result = {}
    with patch("filinglens.retrieval.service.RETRIEVAL_VERSION", "retrieval-v1"):
        for record in records:
            values, ranks = await candidates(service, record["question"], record["filters"], 30)
            expected = set().union(*(set(by_key[record["id"], m]) for m in MODES))
            if {v.chunk_id for v in values} != expected:
                raise ValueError("Reconstructed v1 pool disagrees with archived pre-fix evidence")
            if any(
                len([r for r in ranks.values() if m in r]) != len(by_key[record["id"], m])
                for m in MODES
            ):
                raise ValueError("Incomplete reconstructed pool")
            result[record["id"]] = expected
    return result


async def source_audit(pool) -> list[dict]:
    settings = Settings()
    async with pool.connection() as conn:
        await conn.execute("SET TRANSACTION READ ONLY")
        rows = await (
            await conn.execute(
                "SELECT co.ticker,f.fiscal_year,f.fiscal_period,f.accession,f.url,cd.source_hash "
                "FROM filings f JOIN companies co ON co.cik=f.cik JOIN corpus_documents cd "
                "ON cd.accession=f.accession WHERE cd.corpus_id=%s "
                "AND co.ticker IN ('JNJ','XOM') AND f.form='10-Q' ORDER BY co.ticker,f.report_date",
                (CORPUS_ID,),
            )
        ).fetchall()
    result = []
    for ticker, year, period, accession, url, source_hash in rows:
        key = hashlib.sha256(url.encode()).hexdigest()
        path = settings.raw_dir / settings.snapshot_id / f"{key}.body"
        body = path.read_bytes()
        if hashlib.sha256(body).hexdigest() != source_hash:
            raise ValueError(f"Cached source hash mismatch: {accession}")
        # DOM inspection for auditing only; no ingestion parser/chunker or DB writes.
        doc = LexborHTMLParser(body)
        for node in doc.css("script,style,head"):
            node.decompose()
        text = re.sub(r"\s+", " ", doc.text(separator=" ", strip=True))
        matches = list(re.finditer(r"\bitem\s*1\s*a\b", text, re.I))
        risk_mentions = len(re.findall(r"risk\s*factors", text, re.I))
        contexts = [text[max(0, m.start() - 80) : m.end() + 600] for m in matches]
        if len(matches) != 1 or risk_mentions != 1 or "10-K" not in contexts[0]:
            raise ValueError(f"Source needs manual inspection: {accession}")
        result.append(
            {
                "ticker": ticker,
                "fiscal_year": year,
                "period": period,
                "accession": accession,
                "path": str(path),
                "sha256": source_hash,
                "item_1a_occurrences": len(matches),
                "risk_factors_occurrences": risk_mentions,
                "context": contexts[0],
                "finding": "No quarterly Item 1A; annual 10-K reference only",
            }
        )
    return result


async def analyze() -> None:
    pre = json.loads((RESULTS / "retrieval_pre_fix.json").read_text(encoding="utf-8"))
    post = json.loads((RESULTS / "retrieval.json").read_text(encoding="utf-8"))
    settings = Settings()
    async with pool_for(settings.database_url) as pool:
        records, before = await validate(pool, ROOT / "evals/handwritten.jsonl")
        if json.loads(json.dumps(before)) != post["validation"]:
            raise ValueError("Current labels/corpus differ from evaluation evidence")
        record_by_id = {r["id"]: r for r in records}
        for d in post["details"]:
            expected = cache_path(record_by_id[d["question_id"]], d["mode"])
            if d["cache_path"] != expected.relative_to(ROOT).as_posix():
                raise ValueError("Post-fix evidence contains a pre-fix cache key")
        check_reranker_pool(post["details"])
        pools = await reconstruct_pools(pool, records, pre)
        sources = await source_audit(pool)
        ids = set().union(
            *(set(d["ranked_ids"]) for d in post["details"]),
            *(set(r["gold_chunk_ids"]) for r in records),
        )
        async with pool.connection() as conn:
            await conn.execute("SET TRANSACTION READ ONLY")
            conn.row_factory = dict_row
            rows = await (
                await conn.execute(
                    "SELECT c.id,c.text,co.ticker,c.form,c.fiscal_year,c.fiscal_period,c.item,"
                    "c.accession FROM chunks c JOIN corpus_chunks cc ON cc.chunk_id=c.id "
                    "JOIN companies co ON co.cik=c.cik WHERE cc.corpus_id=%s AND c.id=ANY(%s)",
                    (CORPUS_ID, sorted(ids)),
                )
            ).fetchall()
        lookup = {r["id"]: r for r in rows}
        _, after = await validate(pool, ROOT / "evals/handwritten.jsonl")
        if before != after:
            raise ValueError("Corpus/labels changed during read-only analyses")
    by_id = {r["id"]: r for r in records}
    judgments = []
    for d in post["details"]:
        record = by_id[d["question_id"]]
        for k in (5, 10):
            judgments.append(
                {
                    "question_id": record["id"],
                    "mode": d["mode"],
                    **unjudged(
                        d["ranked_ids"], pools[record["id"]], set(record["gold_chunk_ids"]), k
                    ),
                }
            )
    overlaps = []
    for d in post["details"]:
        if d["question_id"] not in CROSS_YEAR or d["mode"] not in {"vector", "hybrid_rerank"}:
            continue
        record = by_id[d["question_id"]]
        gold = [lookup[g] for g in record["gold_chunk_ids"]]
        gold_shingles = [(g, shingles(g["text"])) for g in gold]
        for rank, key in enumerate(d["ranked_ids"][:10], 1):
            value = lookup[key]
            comparisons = [
                (containment(shingles(value["text"]), gs), g)
                for g, gs in gold_shingles
                if g["accession"] != value["accession"]
            ]
            overlap, closest = (
                max(comparisons, key=lambda p: (p[0], p[1]["id"])) if comparisons else (0.0, None)
            )
            overlaps.append(
                {
                    "question_id": record["id"],
                    "mode": d["mode"],
                    "rank": rank,
                    **{k: v for k, v in value.items() if k != "text"},
                    "gold": key in record["gold_chunk_ids"],
                    "near_duplicate": overlap >= 0.70,
                    "overlap": overlap,
                    "closest_gold_id": closest["id"] if closest else None,
                    "closest_gold_year": closest["fiscal_year"] if closest else None,
                }
            )
    evidence = {
        "retrieval_version": RETRIEVAL_VERSION,
        "validation": before,
        "pool_reconstruction": {k: sorted(v) for k, v in pools.items()},
        "unjudged": judgments,
        "near_duplicates": overlaps,
        "source_audit": sources,
    }
    (RESULTS / "retrieval_analyses.json").write_text(
        json.dumps(evidence, indent=2), encoding="utf-8"
    )
    lines = render(records, pre, post, evidence)
    output = RESULTS / "retrieval.md"
    body = report(records, before, post["details"], post["coverage"])
    output.write_text(body + "\n" + "\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines[:30]), flush=True)
    print("SOURCES", Counter(r["finding"] for r in sources), flush=True)


def render(records: list[dict], pre: dict, post: dict, evidence: dict) -> list[str]:
    lines = [
        "## Follow-up analyses",
        "",
        "### Pre/post comparison",
        "",
        "The pre-fix tables retain the keyword AND-semantics defect. The single OR fix was "
        "chosen in D031 before rerunning; it is not a selection among tuned variants.",
        "",
    ]
    lines += [
        "| Mode | Change capped recall@5 | Change capped recall@10 | Change MRR@30 |",
        "|---|---:|---:|---:|",
    ]
    for mode in MODES:
        changes = []
        for metric in ("capped_recall@5", "capped_recall@10", "MRR@30"):
            means = [
                sum(d[metric] for d in p["details"] if d["mode"] == mode) / 30 for p in (pre, post)
            ]
            changes.append(f"{means[1] - means[0]:+.4f}")
        lines.append(f"| {mode} | " + " | ".join(changes) + " |")
    lines.append("")
    lines += [
        "### Unjudged candidate exposure",
        "",
        "The CLI did not record candidate-pool membership. Reconstruction reran its "
        "four-mode × depth-30 pooling definition with each record's exact saved filters, "
        "replaying all 120 valid pre-fix v1 caches (including keyword AND semantics), "
        "and checked the union against archived rankings. This is a reconstruction, "
        "not the complete history of earlier query edits, deeper pools or manual browsing. "
        "Known gold from browsing is judged even outside this reconstructed pool. "
        "Pool membership also does not prove every displayed candidate was explicitly "
        "judged; the CLI saved positives only.",
        "",
        "Unjudged here = a retrieved ID outside that question's reconstructed union and "
        "outside its saved gold. The fraction divides by actual returned top-k slots. "
        "Overall rates below are slot-weighted (micro), not fractions of the whole corpus. "
        "Outside-pool counts are also retained in retrieval_analyses.json. No new relevance "
        "labels are assigned. Unjudged relevant chunks count as misses under the frozen "
        "gold scoring, so keyword and hybrid receive lower-bound relevance credit; the "
        "candidate pool was biased toward the vector family. Their recall scores are not "
        "formal numerical lower bounds on exhaustive recall: completing gold judgments "
        "also changes the unknown denominator. This does not establish which unjudged "
        "passages are relevant.",
        "",
        "| Mode | Unjudged top-5 slots | Fraction | Unjudged top-10 slots | Fraction "
        "| Outside reconstructed pool @5 | Outside reconstructed pool @10 |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for mode in MODES:
        vals = []
        outside = []
        for k in (5, 10):
            subset = [d for d in evidence["unjudged"] if d["mode"] == mode and d["k"] == k]
            n, total = sum(d["unjudged"] for d in subset), sum(d["returned"] for d in subset)
            vals += [f"{n}/{total}", f"{n / total:.4f}" if total else "n/a"]
            count = sum(d["outside_pool"] for d in subset)
            outside.append(f"{count}/{total} ({count / total:.4f})" if total else "n/a")
        lines.append(f"| {mode} | " + " | ".join(vals + outside) + " |")
    lines += [
        "",
        "Per question (unjudged/returned, fraction):",
        "",
        "| ID | Mode | Unjudged top 5 | Unjudged top 10 "
        "| Outside pool top 5 | Outside pool top 10 |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for record in records:
        for mode in MODES:
            values = [
                d
                for d in evidence["unjudged"]
                if d["question_id"] == record["id"] and d["mode"] == mode
            ]
            cells = [f"{v['unjudged']}/{v['returned']} ({v['fraction']:.4f})" for v in values]
            cells += [
                f"{v['outside_pool']}/{v['returned']} ({v['outside_pool'] / v['returned']:.4f})"
                if v["returned"]
                else "n/a"
                for v in values
            ]
            lines.append(f"| {record['id']} | {mode} | " + " | ".join(cells) + " |")
    lines += [
        "",
        "### Cross-year near-duplicates",
        "",
        "Before analysis, D032 fixed this heuristic: normalize Unicode/case, form "
        "five-word shingle sets, require at least 20 shingles on each side, and flag "
        "overlap ≥0.70 (intersection divided by the smaller set) with a gold passage "
        "from a different accession. Containment permits shifted chunk boundaries; "
        "shared boilerplate can also trigger it. This is text overlap, not a new "
        "relevance judgment. Each slot below shows its largest different-filing gold overlap.",
        "",
    ]
    for record in records:
        if record["id"] not in CROSS_YEAR:
            continue
        lines += [
            f"#### {record['filters']['ticker']}: {record['question']}",
            "",
            f"ID: `{record['id']}`.",
            "",
            "| Mode | Rank | Chunk ID | Ticker | Form | FY | Period | Item | Accession "
            "| Gold | Near-duplicate | Overlap | Closest gold ID (FY) |",
            "|---|---:|---|---|---|---:|---|---|---|---|---|---:|---|",
        ]
        subset = [d for d in evidence["near_duplicates"] if d["question_id"] == record["id"]]
        for d in subset:
            closest = (
                f"{d['closest_gold_id']} ({d['closest_gold_year']})"
                if d["closest_gold_id"]
                else "—"
            )
            vals = [
                d[k]
                for k in (
                    "mode",
                    "rank",
                    "id",
                    "ticker",
                    "form",
                    "fiscal_year",
                    "fiscal_period",
                    "item",
                    "accession",
                )
            ]
            vals += [
                "yes" if d["gold"] else "",
                "yes" if d["near_duplicate"] else "",
                f"{d['overlap']:.3f}",
                closest,
            ]
            lines.append("| " + " | ".join(map(cell, vals)) + " |")
        lines.append("")
        for mode in ("vector", "hybrid_rerank"):
            values = [d for d in subset if d["mode"] == mode]
            lines.append(
                f"{mode}: {sum(d['near_duplicate'] for d in values)}/10 different-filing "
                f"near-duplicate slots; {sum(d['gold'] for d in values)}/10 exact gold slots."
            )
        lines.append("")
    for mode in ("vector", "hybrid_rerank"):
        vals = [d for d in evidence["near_duplicates"] if d["mode"] == mode]
        misses = [
            r for r in CROSS_YEAR if not any(d["gold"] for d in vals if d["question_id"] == r)
        ]
        dominated = sum(
            sum(d["near_duplicate"] for d in vals if d["question_id"] == r) >= 5 for r in misses
        )
        lines += [
            f"{mode}: {sum(d['near_duplicate'] for d in vals)}/{len(vals)} top-10 slots "
            f"are different-filing near-duplicates. {len(misses)} cross-year questions "
            f"have no exact gold in the top 10; {dominated} of those have at least "
            "five near-duplicate slots.",
            "",
        ]
    xom = "hq_efbdb0ea523543c699eddddde9b1e638"
    xom_ranks = ", ".join(
        f"{d['mode']}={d['first_gold_rank'] or '>30'}"
        for d in post["details"]
        if d["question_id"] == xom
    )
    lines += [
        f"XOM greenhouse-gas first-gold ranks after the fix: {xom_ranks}. "
        "It is no longer a miss in every mode. The overlap heuristic flags no different-filing "
        "near-duplicates in its vector top 10; wrong-year near-duplicates therefore do not "
        "explain that vector miss under this rule. Across the six questions, the measured "
        "near-duplicate counts do not support attributing most cross-year misses to "
        "near-duplicates. This does not classify the relevance of unjudged passages.",
        "",
    ]
    lines += [
        "These counts show the measured extent of wrong-filing overlap, not that every "
        "cross-year miss is a year-disambiguation error. Unflagged results can still be "
        "topically relevant; high overlap does not prove answer equivalence. "
        "Period resolution is the **M4 planner's responsibility**.",
        "",
        "### JNJ/XOM quarterly risk source check (cached HTML only)",
        "",
        "All 22 raw bodies were read locally and SHA-256 checked against the frozen "
        "document provenance. No SEC client/network call or ingestion parser was invoked. "
        "Every file has one Item 1A mention, inside a prose reference to the annual "
        "10-K's risk factors; none contains a separate quarterly Item 1A risk section. "
        "Thus these 22 empty corpus slots reflect source absence, not missed quarterly "
        "risk headings. The annual references need explicit availability/provenance "
        "handling in a future corpus rather than invented quarterly text.",
        "",
        "| Ticker | FY | Quarter | Accession | Cached-source finding |",
        "|---|---:|---|---|---|",
    ]
    for d in evidence["source_audit"]:
        lines.append(
            f"| {d['ticker']} | {d['fiscal_year']} | {d['period']} | {d['accession']} "
            f"| {d['finding']} |"
        )
    return lines


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(analyze())

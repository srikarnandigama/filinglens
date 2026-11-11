"""Run the accepted M4 system on a benchmark question and map its Answer to a prediction.

The runtime is used unchanged (D095); everything here reads its result: the Answer, the run's
evidence ledger and the recorded trace. Citation validity reruns M4's Stage 1 checks offline
(D092), and the comparison choice is read from the system's claims (D091).
"""

import re
from decimal import Decimal
from typing import Any

from filinglens.agents.ledger import Ledger
from filinglens.agents.schemas import Answer
from filinglens.agents.verifier import check_claim

MIN_MATCH_WORDS = 8
WORD = re.compile(r"[a-z0-9$%.,'-]+")


def _claim_ticker(claim, ledger: Ledger) -> str | None:
    """A claim's company: its own ticker, else the facts behind its cited computation."""
    if claim.ticker:
        return claim.ticker
    tickers = set()
    for cit in claim.citations:
        if cit.kind == "fact" and cit.ref in ledger.facts:
            tickers.add(ledger.facts[cit.ref].ticker)
        elif cit.kind == "computation" and cit.ref in ledger.computations:
            record = ledger.computations[cit.ref]
            used = {
                Decimal(str(v))
                for v in (record.arguments or {}).values()
                if isinstance(v, int | float | str) and _is_number(v)
            }
            for fact in ledger.facts.values():
                if fact.value is not None and Decimal(fact.value) in used:
                    tickers.add(fact.ticker)
    return tickers.pop() if len(tickers) == 1 else None


def _is_number(value: Any) -> bool:
    try:
        Decimal(str(value))
    except ArithmeticError:
        return False
    return not isinstance(value, bool)


def comparison_choice(answer: Answer, ledger: Ledger, companies: list[str]) -> str | None:
    """The ticker of the higher of the system's percent claims for the two companies (D091)."""
    best: dict[str, Decimal] = {}
    for claim in answer.claims:
        if claim.unit != "percent" or claim.value is None:
            continue
        ticker = _claim_ticker(claim, ledger)
        if ticker in companies:
            best[ticker] = Decimal(claim.value)  # the last percent claim per company wins
    if len(best) != 2:
        return None
    a, b = companies
    if best[a] == best[b]:
        return None
    return a if best[a] > best[b] else b


def prediction_of(
    answer: Answer | None, question: dict[str, Any], ledger: Ledger
) -> dict[str, Any]:
    if answer is None:
        return {
            "value": None,
            "unit": None,
            "choice": None,
            "status": None,
            "parse_ok": False,
            "parse_error": "run produced no Answer",
        }
    status = "answered" if answer.status in ("answered", "partially_answered") else answer.status
    status = {"not_available": "not_available", "not_applicable": "not_applicable"}.get(
        status, status
    )
    if status in ("not_available", "not_applicable"):
        return {
            "value": None,
            "unit": None,
            "choice": None,
            "status": status,
            "parse_ok": True,
            "parse_error": None,
        }
    if answer.final_value is None:
        return {
            "value": None,
            "unit": answer.final_unit,
            "choice": None,
            "status": "answered",
            "parse_ok": False,
            "parse_error": "Answer has no final_value",
        }
    choice = None
    if question["template"] == "comparison":
        choice = comparison_choice(answer, ledger, question["companies"])
        if choice is None:
            return {
                "value": answer.final_value,
                "unit": answer.final_unit,
                "choice": None,
                "status": "answered",
                "parse_ok": False,
                "parse_error": "comparison choice not resolvable from claims (D091)",
            }
    return {
        "value": answer.final_value,
        "unit": answer.final_unit,
        "choice": choice,
        "status": "answered",
        "parse_ok": True,
        "parse_error": None,
    }


def _words(text: str) -> list[str]:
    return WORD.findall(text.lower())


def string_supported(claim_text: str, passages: list[str]) -> bool:
    """True when an 8-word run of the claim appears verbatim (normalized) in a cited passage."""
    words = _words(claim_text)
    if len(words) < MIN_MATCH_WORDS:
        return False
    targets = [" ".join(_words(p)) for p in passages if p]
    for i in range(len(words) - MIN_MATCH_WORDS + 1):
        span = " ".join(words[i : i + MIN_MATCH_WORDS])
        if any(span in t for t in targets):
            return True
    return False


def citation_summary(
    answer: Answer | None, ledger: Ledger, use_quant_tools: bool = True
) -> dict[str, Any]:
    """Numeric claims via M4 Stage 1 (offline); text claims by string match, else pending judge."""
    if answer is None:
        return {
            "numeric_total": 0,
            "numeric_valid": 0,
            "text_total": 0,
            "text_string_supported": 0,
            "text_pending_judge": [],
            "uncited": 0,
        }
    numeric_total = numeric_valid = text_total = text_ok = uncited = 0
    pending = []
    for claim in answer.claims:
        if not claim.citations:
            uncited += 1
        if claim.kind == "numeric":
            numeric_total += 1
            numeric_valid += check_claim(claim, ledger, use_quant_tools).verdict == "supported"
            continue
        text_total += 1
        chunks = [c.ref for c in claim.citations if c.kind == "chunk"]
        passages = [
            (ledger.passages[c].full_text or ledger.passages[c].snippet or "")
            for c in chunks
            if c in ledger.passages
        ]
        if string_supported(claim.text, passages):
            text_ok += 1
        else:
            pending.append({"claim_id": claim.id, "text": claim.text, "chunk_ids": chunks})
    return {
        "numeric_total": numeric_total,
        "numeric_valid": numeric_valid,
        "text_total": text_total,
        "text_string_supported": text_ok,
        "text_pending_judge": pending,
        "uncited": uncited,
    }


def retrieval_from_trace(events: list[Any]) -> dict[str, Any]:
    """Chunk IDs each filings worker's first search returned (in rank order) and all seen."""
    first: dict[str, list[str]] = {}
    seen: list[str] = []
    for e in events:
        if e.event_type != "tool_result" or e.payload.get("tool") not in (
            "search_filings",
            "get_passage",
        ):
            continue
        data = (e.payload.get("structured") or {}).get("data") or {}
        hits = data.get("hits") if e.payload["tool"] == "search_filings" else [data]
        ids = [h["chunk_id"] for h in hits or [] if h.get("chunk_id")]
        if e.payload["tool"] == "search_filings":
            first.setdefault(e.payload["instance"], ids)
        seen += [i for i in ids if i not in seen]
    return {"first_search": first, "seen": seen}


def recall_at(gold: list[str], retrieval: dict[str, Any], k: int) -> float:
    """Gold chunks found in any worker's first-search top k.

    The D027 denominator min(k, |gold|) is per search; with several workers their top-k lists
    hold up to k x workers chunks, so the cap is min(k x workers, |gold|) and recall stays <= 1.
    """
    searches = retrieval["first_search"]
    top = {c for ids in searches.values() for c in ids[:k]}
    found = len(set(gold) & top)
    return found / min(k * max(1, len(searches)), len(gold)) if gold else float("nan")


async def run_system(
    question: dict[str, Any],
    cfg: Any,
    settings: Any,
    hub: Any,
    prices: Any,
    handwritten: bool = False,
) -> dict[str, Any]:
    """One live system run (D095: the accepted runtime, unchanged)."""
    from filinglens.agents.orchestrator import run_question
    from filinglens.agents.tracing import load_run

    result = await run_question(question["question"], cfg, settings, hub=hub, prices=prices)
    out: dict[str, Any] = {
        "run_id": str(result.run_id),
        "run_status": result.status,
        "error": result.error,
        "usage": {
            "input_tokens": result.totals.input_tokens,
            "output_tokens": result.totals.output_tokens,
            "cache_read_tokens": result.totals.cache_read_tokens,
            "cache_write_tokens": result.totals.cache_write_tokens,
        },
        "cost_usd": str(result.totals.cost_usd),
        "latency_ms": result.totals.latency_ms,
        "raw_output": result.answer.model_dump(mode="json") if result.answer else None,
        "citations": citation_summary(result.answer, result.ledger, cfg.use_quant_tools),
    }
    if handwritten:
        _, events = load_run(settings.database_url, result.run_id)
        out["prediction"] = {
            "text": (result.answer.summary + "\n" + "\n".join(c.text for c in result.answer.claims))
            if result.answer
            else "",
            "parse_ok": result.answer is not None,
        }
        out["retrieval"] = retrieval_from_trace(events)
    else:
        out["prediction"] = prediction_of(result.answer, question, result.ledger)
    return out

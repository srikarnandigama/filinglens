"""LLM judges (D092, D093): rubric scoring for handwritten answers and text-claim support.

The judge sees content, not citations. Calibration: the student labels 20 judge outputs blind;
agreement, within-1 agreement and quadratic-weighted kappa are reported. No calls at import time.
"""

import hashlib
import json
from pathlib import Path
from typing import Any

from evals.answers import OBJECT
from evals.scorers import weighted_kappa

RUBRIC = """You grade an answer to a question about a company's SEC filings against a reference
answer written by an analyst. Score 1-5:
5: covers all key points of the reference; nothing contradicted or invented.
4: covers most key points; minor omissions only.
3: covers about half of the key points, or makes one material error.
2: covers few key points, or materially contradicts the reference.
1: wrong, invented, or off-topic.
Judge only content against the reference; ignore style, length and citations. End with one line
of JSON: {"score": <1-5>, "missing_points": ["..."], "errors": ["..."]}"""

CLAIM_JUDGE = """You check whether a passage from an SEC filing supports a claim. Paraphrase is
fine; added causes, wrong periods, wrong companies or numbers not in the passage are not. End with
one line of JSON: {"supported": true | false, "reason": "..."}"""


def rubric_params(model: str, question: str, reference: str, answer: str) -> dict[str, Any]:
    text = f"Question: {question}\n\nReference answer:\n{reference}\n\nAnswer to grade:\n{answer}"
    return {
        "model": model,
        "max_tokens": 4000,
        "system": RUBRIC,
        "messages": [{"role": "user", "content": text}],
    }


def claim_params(model: str, claim: str, passages: list[str]) -> dict[str, Any]:
    joined = "\n\n".join(f"<passage>\n{p}\n</passage>" for p in passages)
    return {
        "model": model,
        "max_tokens": 2000,
        "system": CLAIM_JUDGE,
        "messages": [{"role": "user", "content": f"Claim: {claim}\n\n{joined}"}],
    }


def _last_json(text: str, key: str) -> dict[str, Any] | None:
    found = None
    for match in OBJECT.finditer(text or ""):
        try:
            obj = json.loads(match.group(0))
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict) and key in obj:
            found = obj
    return found


def parse_rubric(text: str) -> dict[str, Any]:
    obj = _last_json(text, "score")
    if obj is None or obj.get("score") not in (1, 2, 3, 4, 5):
        return {"score": None, "parse_ok": False}
    return {
        "score": obj["score"],
        "missing_points": obj.get("missing_points", []),
        "errors": obj.get("errors", []),
        "parse_ok": True,
    }


def parse_claim(text: str) -> dict[str, Any]:
    obj = _last_json(text, "supported")
    if obj is None or not isinstance(obj.get("supported"), bool):
        return {"supported": None, "parse_ok": False}
    return {"supported": obj["supported"], "reason": obj.get("reason"), "parse_ok": True}


def calibration_sample(
    judged: list[dict[str, Any]], n: int = 20, seed: int = 20261109
) -> list[dict[str, Any]]:
    """n judged answers stratified across judge scores and systems, for blind student labels."""
    ranked = sorted(judged, key=lambda r: hashlib.sha256(f"{seed}|{r['key']}".encode()).hexdigest())
    by_score: dict[Any, list[dict[str, Any]]] = {}
    for r in ranked:
        by_score.setdefault(r["score"], []).append(r)
    out: list[dict[str, Any]] = []
    while len(out) < min(n, len(ranked)):
        for score in sorted(by_score, key=str):
            if by_score[score] and len(out) < n:
                out.append(by_score[score].pop(0))
    return out


def blind_export(sample: list[dict[str, Any]], path: Path) -> Path:
    """The labeling file for the student: question, reference, answer; no judge score."""
    rows = [
        {
            "key": r["key"],
            "question": r["question"],
            "reference": r["reference"],
            "answer": r["answer"],
            "student_score": None,
        }
        for r in sample
    ]
    path.write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8"
    )
    return path


def agreement(judge: dict[str, int], student: dict[str, int]) -> dict[str, Any]:
    keys = sorted(set(judge) & set(student))
    a = [judge[k] for k in keys]
    b = [student[k] for k in keys]
    n = len(keys)
    exact = sum(x == y for x, y in zip(a, b, strict=True)) / n if n else float("nan")
    within1 = sum(abs(x - y) <= 1 for x, y in zip(a, b, strict=True)) / n if n else float("nan")
    kappa = weighted_kappa(a, b)
    return {
        "n": n,
        "exact": exact,
        "within_1": within1,
        "quadratic_kappa": kappa,
        "indicative_only": not (kappa >= 0.6),
    }

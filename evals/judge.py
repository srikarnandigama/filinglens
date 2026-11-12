"""LLM judges (D092, D093): rubric scoring for handwritten answers and text-claim support.

The judge sees content, not citations. Calibration: the student labels 20 judge outputs blind;
agreement, within-1 agreement and quadratic-weighted kappa are reported. No calls at import time.
"""

import hashlib
import json
import os
from decimal import Decimal
from pathlib import Path
from typing import Any

from evals.answers import OBJECT
from evals.scorers import weighted_kappa
from filinglens.config import ROOT

# The judges' share of the $60 test-run ceiling (D105): rubric scoring of system and B0 Sonnet on
# the 30 handwritten questions, plus text-claim support checks.
JUDGE_SPEND_CAP_USD = Decimal("2.50")

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


# ---------------------------------------------------------------- judge runner (D093, D107)

JUDGE_VERSION = "judge-v1"
JUDGE_CACHE_DIR = ROOT / "evals" / "cache" / "judge"
CALIBRATION_JSONL = ROOT / "evals" / "results" / "judge_calibration_blind.jsonl"
CALIBRATION_MD = ROOT / "docs" / "M5_JUDGE_CALIBRATION.md"
# v2 (D110): the same 20 answers in a seeded random order under neutral item numbers; v1's
# order cycled judge scores 2-5. The item -> key map is kept beside the labels.
CALIBRATION_V2_JSONL = ROOT / "evals" / "results" / "judge_calibration_blind_v2.jsonl"
CALIBRATION_V2_MD = ROOT / "docs" / "M5_JUDGE_CALIBRATION_v2.md"
CALIBRATION_V2_MAP = ROOT / "evals" / "results" / "judge_calibration_v2_map.json"
CALIBRATION_V2_SEED = 20261112
HANDWRITTEN_CONFIG = ROOT / "evals" / "configs" / "m5_handwritten.toml"
JUDGED_SYSTEMS = ("system", "b0-sonnet")  # D105: no B0 Opus on the handwritten set
JUDGE_MODEL_ENV, JUDGE_MODEL_INDEX = "BASELINE_MODELS", 1  # Opus 5.5 (D093)
# Per-item reservations against the cap; batch expected ~$0.010 (rubric) and ~$0.005 (claim).
RESERVE = {"rubric": Decimal("0.02"), "claim": Decimal("0.01")}


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def judge_settings(model: str) -> dict[str, Any]:
    """Everything that changes a judge output; part of the cache key."""
    return {
        "model": model,
        "rubric": _sha(RUBRIC),
        "claim": _sha(CLAIM_JUDGE),
        "rubric_max_tokens": rubric_params(model, "", "", "")["max_tokens"],
        "claim_max_tokens": claim_params(model, "", [])["max_tokens"],
        "batch": True,
        "version": JUDGE_VERSION,
    }


def judge_items(
    questions: list[dict[str, Any]],
    records: dict[str, list[dict[str, Any]]],
    passages: dict[str, str],
    model: str,
) -> list[dict[str, Any]]:
    """Rubric items for each judged system's handwritten answers, then one claim item per system
    text claim that string matching did not already support (D092). Runs without an answer are
    not judged; the report scores them 1 (D108)."""
    by_q = {q["id"]: q for q in questions}
    items = []
    for sid in JUDGED_SYSTEMS:
        for rec in records.get(sid, []):
            q = by_q[rec["question_id"]]
            answer = (rec.get("prediction") or {}).get("text") or ""
            if rec.get("status") == "error" or not answer.strip():
                continue
            items.append(
                {
                    "key": _sha(f"rubric|{sid}|{q['id']}|{_sha(answer)}")[:32],
                    "kind": "rubric",
                    "system_id": sid,
                    "question_id": q["id"],
                    "question": q["question"],
                    "reference": q["reference_answer"],
                    "answer": answer,
                    "params": rubric_params(model, q["question"], q["reference_answer"], answer),
                }
            )
    for rec in records.get("system", []):
        for claim in (rec.get("citations") or {}).get("text_pending_judge", []):
            texts = [passages[c] for c in claim["chunk_ids"] if c in passages]
            if not texts:
                continue  # nothing to judge against; stays unsupported by string match
            key = f"claim|{rec['question_id']}|{claim['claim_id']}|{claim['text']}|"
            items.append(
                {
                    "key": _sha(key + ",".join(claim["chunk_ids"]))[:32],
                    "kind": "claim",
                    "system_id": "system",
                    "question_id": rec["question_id"],
                    "claim_id": claim["claim_id"],
                    "params": claim_params(model, claim["text"], texts),
                }
            )
    return items


def _put(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(record, sort_keys=True, default=str), encoding="utf-8")
    os.replace(temporary, path)


async def run_judges(
    items: list[dict[str, Any]],
    *,
    client: Any,
    model_price: Any,
    batch_multiplier: Decimal,
    model: str,
    cap: Decimal = JUDGE_SPEND_CAP_USD,
    cache_dir: Path = JUDGE_CACHE_DIR,
    sleep: Any = None,
) -> dict[str, Any]:
    """Judge every uncached item in one batch, reserving each against the cap first (rubric
    items before claim items); cached items cost nothing."""
    from evals.baselines import cost_usd, run_batch
    from evals.runner import SpendCap, config_hash

    folder = cache_dir / config_hash(judge_settings(model))
    spend = SpendCap(cap)
    out, todo, skipped = [], [], []
    for item in sorted(items, key=lambda i: (i["kind"] != "rubric", i["key"])):
        path = folder / f"{item['key']}.json"
        if path.exists():
            out.append(json.loads(path.read_text(encoding="utf-8")) | {"cached": True})
        elif spend.try_reserve(RESERVE[item["kind"]]):
            todo.append(item)
        else:
            skipped.append(item["key"])
    if todo:
        kwargs = {"sleep": sleep} if sleep else {}
        results = await run_batch(client, {i["key"]: i["params"] for i in todo}, **kwargs)
        for item in todo:
            result = results[item["key"]]
            ok = result.stop_reason is not None and not result.stop_reason.startswith("batch_")
            cost = (
                cost_usd(result.usage, model_price, None, batch_multiplier)
                if result.usage
                else Decimal(0)
            )
            spend.settle(RESERVE[item["kind"]], cost)
            parse = parse_rubric if item["kind"] == "rubric" else parse_claim
            record = {k: v for k, v in item.items() if k != "params"} | {
                "status": "done" if ok else "error",
                "result": parse(result.text) if ok else None,
                "raw_output": result.text,
                "stop_reason": result.stop_reason,
                "usage": result.usage,
                "cost_usd": str(cost),
            }
            if ok:
                _put(folder / f"{item['key']}.json", record)
            out.append(record | {"cached": False})
    return {
        "records": out,
        "summary": {
            "items": len(items),
            "judged": len(todo),
            "cached": len(items) - len(todo) - len(skipped),
            "skipped_spend_cap": skipped,
            "spent_usd": str(spend.spent),
            "spend_cap_usd": str(cap),
            "errors": sum(r["status"] == "error" for r in out),
        },
    }


def load_judged(model: str, cache_dir: Path = JUDGE_CACHE_DIR) -> list[dict[str, Any]]:
    from evals.runner import config_hash

    folder = cache_dir / config_hash(judge_settings(model))
    return [json.loads(p.read_text(encoding="utf-8")) for p in sorted(folder.glob("*.json"))]


def calibration_rows(judged: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Rubric records in the shape calibration_sample and blind_export expect."""
    return [
        {
            "key": r["key"],
            "score": r["result"]["score"],
            "system_id": r["system_id"],
            "question": r["question"],
            "reference": r["reference"],
            "answer": r["answer"],
        }
        for r in judged
        if r["kind"] == "rubric" and r.get("result") and r["result"].get("parse_ok")
    ]


def shuffled_sheet(
    rows: list[dict[str, Any]], seed: int = CALIBRATION_V2_SEED
) -> tuple[list[dict[str, Any]], dict[str, str]]:
    """The v1 rows in a seeded order independent of any score, numbered 1..n without keys."""
    ranked = sorted(rows, key=lambda r: _sha(f"{seed}|calibration-v2|{r['key']}"))
    sheet = [
        {
            "item": n,
            "question": r["question"],
            "reference": r["reference"],
            "answer": r["answer"],
            "student_score": None,
        }
        for n, r in enumerate(ranked, 1)
    ]
    return sheet, {str(n): r["key"] for n, r in enumerate(ranked, 1)}


def export_v2(
    v1: Path = CALIBRATION_JSONL,
    jsonl: Path = CALIBRATION_V2_JSONL,
    md: Path = CALIBRATION_V2_MD,
    map_path: Path = CALIBRATION_V2_MAP,
    seed: int = CALIBRATION_V2_SEED,
) -> list[dict[str, Any]]:
    """Write the v2 sheet, labels file and item map; never overwrites a v2 labels file."""
    if jsonl.exists():
        raise FileExistsError(f"{jsonl} exists; refusing to overwrite labels")
    rows = [json.loads(line) for line in v1.read_text(encoding="utf-8").splitlines()]
    sheet, items = shuffled_sheet(rows, seed)
    jsonl.write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in sheet), encoding="utf-8"
    )
    map_path.write_text(
        json.dumps({"seed": seed, "source": v1.name, "items": items}, indent=2, ensure_ascii=False)
        + "\n",
        encoding="utf-8",
    )
    calibration_markdown(
        sheet,
        md,
        title="# M5 judge calibration v2: blind labeling sheet",
        labels_file="evals/results/judge_calibration_blind_v2.jsonl",
        order_note=(
            "The items are the same 20 answers as the first sheet, in a seeded random order "
            f"(seed {seed}, D110) that carries no information about any score."
        ),
    )
    return sheet


def load_labels(path: Path, map_path: Path | None = None) -> tuple[list[str], dict[str, int]]:
    """Sheet order (as keys) and the 1-5 labels entered so far; v2 items map to keys."""
    if not path.exists():
        return [], {}
    items = json.loads(map_path.read_text(encoding="utf-8"))["items"] if map_path else None
    order: list[str] = []
    labels: dict[str, int] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        key = items[str(row["item"])] if items is not None else row["key"]
        order.append(key)
        if row.get("student_score") in (1, 2, 3, 4, 5):
            labels[key] = row["student_score"]
    return order, labels


def calibration_markdown(
    sample: list[dict[str, Any]],
    path: Path,
    title: str = "# M5 judge calibration: blind labeling sheet",
    labels_file: str = "evals/results/judge_calibration_blind.jsonl",
    order_note: str = "",
) -> Path:
    """A readable blind sheet: question, reference and answer; no judge score or system."""
    match = "same item numbers" if sample and "item" in sample[0] else "same keys"
    lines = [
        title,
        "",
        f"Score each of the {len(sample)} answers 1-5 against its reference with the rubric "
        "below, without looking at the judge's scores. Enter each score as `student_score` in "
        f"`{labels_file}` ({match}).",
        "",
        *([order_note, ""] if order_note else []),
        "```",
        RUBRIC.split("Judge only content")[0].strip(),
        "```",
        "",
    ]
    for n, r in enumerate(sample, 1):
        lines += [
            f"## Item {r['item']}" if "item" in r else f"## {n}. `{r['key']}`",
            "",
            f"**Question:** {r['question']}",
            "",
            f"**Reference:** {r['reference']}",
            "",
            "**Answer:**",
            "",
            *[f"> {line}" if line else ">" for line in r["answer"].splitlines()],
            "",
            "**Your score (1-5):** ___",
            "",
        ]
    path.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    return path


def _passages(chunk_ids: set[str], database_url: str) -> dict[str, str]:
    import psycopg

    from filinglens.db import connection_options

    if not chunk_ids:
        return {}
    with psycopg.connect(database_url, **connection_options(database_url)) as conn:
        conn.execute("SET default_transaction_read_only = on")
        rows = conn.execute(
            "SELECT id, text FROM chunks WHERE id = ANY(%s)", (sorted(chunk_ids),)
        ).fetchall()
    return dict(rows)


def main(argv: list[str] | None = None) -> int:
    import argparse
    import asyncio
    import tomllib

    from evals import runner as r
    from filinglens.agents.settings import RuntimeSettings

    parser = argparse.ArgumentParser(description="Run the M5 judges or write the blind sheet.")
    parser.add_argument("command", choices=["run", "calibrate", "calibrate-v2"])
    args = parser.parse_args(argv)
    if args.command == "calibrate-v2":  # no judge scores or API involved (D110)
        sheet = export_v2()
        print(f"wrote {CALIBRATION_V2_JSONL} and {CALIBRATION_V2_MD} ({len(sheet)} items)")
        return 0
    if args.command == "calibrate" and CALIBRATION_JSONL.exists():
        raise SystemExit(f"{CALIBRATION_JSONL} exists; refusing to overwrite labels")
    settings = RuntimeSettings()
    judge = r.SystemConfig(
        id="judge", kind="b0", model_env=JUDGE_MODEL_ENV, model_index=JUDGE_MODEL_INDEX
    )
    model = r.resolve_model(judge, settings)
    if args.command == "calibrate":
        sample = calibration_sample(calibration_rows(load_judged(model)))
        blind_export(sample, CALIBRATION_JSONL)
        calibration_markdown(sample, CALIBRATION_MD)
        print(f"wrote {CALIBRATION_JSONL} and {CALIBRATION_MD} ({len(sample)} answers)")
        return 0
    import anthropic

    from filinglens.llm.pricing import PRICING_PATH, PriceTable

    cfg = r.load_config(HANDWRITTEN_CONFIG)
    questions = r.load_questions(cfg)
    replayed = asyncio.run(r.Runner(cfg, r.replay_deps(cfg, settings), replay_only=True).run())
    records = replayed["records"]
    chunk_ids = {
        c
        for rec in records.get("system", [])
        for claim in (rec.get("citations") or {}).get("text_pending_judge", [])
        for c in claim["chunk_ids"]
    }
    items = judge_items(questions, records, _passages(chunk_ids, settings.database_url), model)
    prices = PriceTable.load()
    prices.require({model})
    extra = tomllib.loads(PRICING_PATH.read_text(encoding="utf-8"))
    client = anthropic.AsyncAnthropic(
        api_key=settings.anthropic_api_key.get_secret_value(), max_retries=4, timeout=300.0
    )
    out = asyncio.run(
        run_judges(
            items,
            client=client,
            model_price=prices.prices[model],
            batch_multiplier=Decimal(extra["eval"]["batch_multiplier"]),
            model=model,
        )
    )
    summary = {"name": "m5-judges"} | out["summary"]
    r.write_summary({"summary": summary})
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

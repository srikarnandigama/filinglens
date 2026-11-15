"""M6 question sets (D120, D121): the explanatory dev prompts, the frozen 50-question test sample
and the dev-numeric draw for Phase C. Every set is drawn from frozen files with a fixed seed and
hash-checked when loaded; nothing here regenerates questions_v1."""

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from evals.generate import ids_sha256, load_frozen
from filinglens.config import ROOT

SEED = 20261109
EXPLANATORY_DEV = ROOT / "evals" / "explanatory_dev_v1.jsonl"
EXPLANATORY_DEV_SHA256 = "8f25776f53fa519196dbb42341d4c6eafbef42d11eac0052062cfb214dd745a0"
SAMPLE_50 = ROOT / "evals" / "questions_v1.m6_sample50.json"
SAMPLE_50_SHA256 = "54a3c7249f59d2df27cebba34d12e70ff01f967e14f00136acf2fbb742d41b55"
COSTCO_MISS = "q_7efc51f876d501c0"  # the M5 test abstention (trend_avg), forced into the sample
PER_TEMPLATE = 7
DEV_PER_TEMPLATE = 5


def _rank(salt: str, qid: str) -> str:
    return hashlib.sha256(f"{SEED}|{salt}|{qid}".encode()).hexdigest()


def sample_50_ids(records: list[dict[str, Any]]) -> list[str]:
    """7 per template from the frozen 100-question test sample, seeded; trend_avg also gets the
    Costco miss, so it has 8 (D121)."""
    pool = [r for r in records if r["split"] == "test" and r["sample_100"]]
    ids: list[str] = []
    for template in sorted({r["template"] for r in pool}):
        items = sorted(
            (r for r in pool if r["template"] == template and r["id"] != COSTCO_MISS),
            key=lambda r: _rank("m6-sample50", r["id"]),
        )
        ids += [r["id"] for r in items[:PER_TEMPLATE]]
    return sorted([*ids, COSTCO_MISS])


def dev_numeric_ids(pilot: list[dict[str, Any]]) -> list[str]:
    """5 per template, seeded, from the 100 dev-pilot questions (paired with M5's records)."""
    ids: list[str] = []
    for template in sorted({r["template"] for r in pilot}):
        items = sorted(
            (r for r in pilot if r["template"] == template),
            key=lambda r: _rank("m6-dev", r["id"]),
        )
        ids += [r["id"] for r in items[:DEV_PER_TEMPLATE]]
    return sorted(ids)


def load_sample_50(path: Path = SAMPLE_50, expected: str | None = None) -> set[str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if ids_sha256(data["ids"]) != (expected or SAMPLE_50_SHA256):
        raise ValueError("questions_v1.m6_sample50.json does not match its frozen hash (D121)")
    return set(data["ids"])


def load_explanatory_dev(path: Path = EXPLANATORY_DEV, expected: str | None = None) -> list[dict]:
    text = path.read_bytes().decode("utf-8").replace("\r\n", "\n")  # checkout-independent
    if text_sha256(text) != (expected or EXPLANATORY_DEV_SHA256):
        raise ValueError("explanatory_dev_v1.jsonl does not match its frozen hash (D120)")
    return [json.loads(line) for line in text.splitlines() if line.strip()]


def text_sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def freeze_sample_50(path: Path = SAMPLE_50) -> str:
    """Write the sample once; never overwrite a frozen file."""
    if path.exists():
        raise FileExistsError(f"{path} is frozen; a change is a new version")
    from evals.generate import FROZEN_PATH, MANIFEST_PATH

    ids = sample_50_ids(load_frozen(FROZEN_PATH, MANIFEST_PATH))
    body = {
        "description": "M6 numeric test sample (D121): 7 per template from the frozen 100-"
        "question sample, seeded, plus the M5 Costco miss in trend_avg.",
        "seed": SEED,
        "ids": ids,
    }
    path.write_text(json.dumps(body, indent=1) + "\n", encoding="utf-8")
    return ids_sha256(ids)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="M6 question sets")
    parser.add_argument("command", choices=["freeze-sample", "dev-ids"])
    args = parser.parse_args(argv)
    if args.command == "freeze-sample":
        print(freeze_sample_50())
        return 0
    from evals.runner import load_config, load_questions

    pilot = load_questions(load_config(ROOT / "evals" / "configs" / "m5_dev_pilot.toml"))
    print(json.dumps(dev_numeric_ids(pilot)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

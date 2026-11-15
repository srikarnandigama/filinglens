"""CI eval smoke test (SPEC §14, D122): replay committed cached records, score them, and fail if
any record is missing from the cache or accuracy falls below the config's recorded threshold.

No API key, database or model download is needed: the runner's replay-only path builds no SDK
client or MCP server, and the cache key is computed from Settings (public model IDs from the
environment) and the committed prompt files. A miss means something that keys the cache changed
(a prompt, a flag, a model ID or the question set); it fails rather than silently re-scoring.
"""

import argparse
import asyncio
import tomllib
from decimal import Decimal
from pathlib import Path
from typing import Any

from evals.report import scored
from evals.runner import ReplayMiss, Runner, load_config, load_questions, replay_deps


def run_smoke(path: Path, cache: Any = None) -> dict[str, Any]:
    cfg = load_config(path)
    threshold = Decimal(tomllib.loads(path.read_text(encoding="utf-8"))["min_accuracy"])
    questions = load_questions(cfg)
    result = asyncio.run(Runner(cfg, replay_deps(cfg), cache=cache, replay_only=True).run())
    systems = {}
    for system_id, records in result["records"].items():
        rows = scored(questions, records)
        correct = sum(row["score"].correct for row in rows.values())
        accuracy = Decimal(correct) / Decimal(len(questions))
        systems[system_id] = {
            "n": len(questions),
            "scored": len(rows),
            "correct": correct,
            "accuracy": str(accuracy),
            "passed": len(rows) == len(questions) and accuracy >= threshold,
        }
    return {"threshold": str(threshold), "systems": systems}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Replay-only eval smoke test (D122).")
    parser.add_argument("config", type=Path)
    args = parser.parse_args(argv)
    try:
        out = run_smoke(args.config)
    except ReplayMiss as exc:
        print(f"FAIL: replay miss ({exc}); something that keys the cache changed")
        return 1
    for system_id, row in out["systems"].items():
        print(
            f"{system_id}: {row['correct']}/{row['n']} correct, accuracy {row['accuracy']} "
            f"(threshold {out['threshold']}) -> {'pass' if row['passed'] else 'FAIL'}"
        )
    return 0 if all(row["passed"] for row in out["systems"].values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())

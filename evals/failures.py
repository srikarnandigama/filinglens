"""Failure categorization (SPEC §13.6, D112): deterministic rules over a cached run record and its
trace, no LLM. A run can fall into several categories; counts are runs with at least one event.

    python -m evals.failures evals/configs/m5_dev_pilot.toml ... --out evals/results/failures.json

The CLI replays the configs' cached records (no API calls) and reads each run's trace from
PostgreSQL read-only. It writes every categorized run with its evidence, per-split counts, two
examples per category and a seeded spot-check list of up to five runs per category.
"""

import argparse
import asyncio
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from filinglens.agents.toolbox import ROLE_TOOLS

SPOT_CHECK_SEED = 20261112
SPOT_CHECK_N = 5
NEAR_BUDGET_TOKENS = 150_000
RETRY_TEXT = "Your final reply was not valid"
KNOWN_TOOLS = {t for tools in ROLE_TOOLS.values() for t in tools}

# Category labels, in report order: outcome failures first, then degraded runs.
OUTCOME = (
    "budget exhausted before a draft (no answer)",
    "budget stop after a draft (D073 finalization)",
    "run error (other)",
    "partially answered",
    "retrieval miss (no gold chunk seen)",
)
DEGRADED = (
    "planner stall (>=2 no-progress steps)",
    "analyst stall (>=2 no-progress steps)",
    "filings stall (>=2 no-progress steps)",
    "verifier stall (>=2 no-progress steps)",
    "invalid final-answer tool",
    "empty reply",
    "corrective retry: planner (planning error caught by validation)",
    "corrective retry: analyst",
    "corrective retry: filings",
    "corrective retry: verifier",
    "untraced quant call (D079)",
    "filings passage cap hit (D074)",
    "revision: summary numbers not in claims (Stage 1)",
    "revision: unsupported caveat (Stage 2)",
    "revision: unsupported claim",
    "revision skipped for budget (D072)",
    "stall guard fired (D115)",
    "near budget (>150K tokens)",
)
CATEGORIES = OUTCOME + DEGRADED


def _instance_steps(events: list[Any]) -> dict[str, list[dict[str, Any]]]:
    """Per agent instance, each LLM step with the tool results that followed it."""
    steps: dict[str, list[dict[str, Any]]] = defaultdict(list)
    current: dict[str, dict[str, Any]] = {}
    for e in events:
        if e.event_type == "llm_call":
            step = {"payload": e.payload, "results": []}
            steps[e.payload["instance"]].append(step)
            current[e.payload["instance"]] = step
        elif e.event_type == "tool_result":
            instance = e.payload.get("instance")
            if instance in current:
                current[instance]["results"].append(e.payload)
    return steps


def stalled_instances(events: list[Any], n: int = 2) -> list[tuple[str, int]]:
    """Instances with n consecutive tool steps whose every result was an error, a duplicate or
    identical to a result the instance already had (the D115 rule), with the step it reached n."""
    out = []
    for instance, steps in _instance_steps(events).items():
        seen: set[str] = set()
        streak = 0
        for index, step in enumerate(steps):
            calls = step["payload"]["response"].get("tool_calls") or []
            if not calls:
                streak = 0
                continue
            results = step["results"]
            no_info = bool(results) and all(
                r.get("is_error") or r.get("duplicate_of") or r.get("raw_sha256") in seen
                for r in results
            )
            seen |= {r["raw_sha256"] for r in results if "raw_sha256" in r and not r["is_error"]}
            streak = streak + 1 if no_info else 0
            if streak >= n:
                out.append((instance, index))
                break
    return out


def categorize(
    record: dict[str, Any], events: list[Any], gold_chunks: list[str] | None = None
) -> dict[str, str]:
    """{category: evidence} for one run."""
    found: dict[str, str] = {}

    def add(category: str, evidence: str) -> None:
        found.setdefault(category, evidence)

    error = record.get("error") or {}
    if error.get("handled") == "stopped_without_draft" or (
        record.get("status") == "error" and error.get("type") == "BudgetExceeded"
    ):
        add(CATEGORIES[0], error.get("message", ""))
    elif error.get("handled") == "budget_finalized":
        add(CATEGORIES[1], error.get("message", ""))
    elif record.get("status") == "error":
        add(CATEGORIES[2], f"{error.get('type')}: {error.get('message', '')[:200]}")
    if (record.get("raw_output") or {}).get("status") == "partially_answered":
        add("partially answered", "status partially_answered")
    if gold_chunks:
        seen = set((record.get("retrieval") or {}).get("seen") or [])
        if not seen & set(gold_chunks):
            add("retrieval miss (no gold chunk seen)", f"{len(seen)} chunks seen, none gold")

    for instance, step in stalled_instances(events):
        role = instance.split(":")[0]
        label = f"{role} stall (>=2 no-progress steps)"
        if label in CATEGORIES:
            add(label, f"{instance} reached 2 no-progress steps at step {step}")
    first_verification = None
    for e in events:
        p = e.payload
        if e.event_type == "tool_call":
            rejected = p.get("rejected")
            if rejected == "TOOL_NOT_ALLOWED" and p.get("tool") not in KNOWN_TOOLS:
                add("invalid final-answer tool", f"{p['instance']} called {p.get('tool')!r}")
            elif rejected == "UNTRACED_INPUTS":
                add("untraced quant call (D079)", f"{p['instance']} {p.get('tool')}")
            elif rejected == "CALL_LIMIT":
                add("filings passage cap hit (D074)", f"{p['instance']} {p.get('tool')}")
        elif e.event_type == "llm_call":
            response = p.get("response") or {}
            if not response.get("tool_calls") and not (response.get("text") or "").strip():
                add("empty reply", f"{p['instance']} step {p['step']}")
            for msg in p.get("new_messages") or []:
                if (msg.get("text") or "").startswith(RETRY_TEXT):
                    label = f"corrective retry: {p['instance'].split(':')[0]}"
                    label = next((c for c in CATEGORIES if c.startswith(label)), None)
                    if label:
                        add(label, f"{p['instance']} step {p['step']}")
        elif e.event_type == "verification" and "failing" in p and first_verification is None:
            first_verification = p["failing"] or {}
        elif e.event_type == "revision_skipped":
            add("revision skipped for budget (D072)", f"round {p.get('round')}")
        elif e.event_type == "stall_guard":
            add("stall guard fired (D115)", f"{p['instance']} {p['reason']} at step {p['step']}")
    for key, reasons in (first_verification or {}).items():
        if key == "summary" and any(not r.startswith("verifier") for r in reasons):
            add("revision: summary numbers not in claims (Stage 1)", reasons[0][:200])
        elif key.startswith("caveat"):
            add("revision: unsupported caveat (Stage 2)", reasons[0][:200])
        elif key not in ("summary", "answer"):
            add("revision: unsupported claim", reasons[0][:200])
    usage = record.get("usage") or {}
    if sum(usage.values()) > NEAR_BUDGET_TOKENS and CATEGORIES[0] not in found:
        add("near budget (>150K tokens)", f"{sum(usage.values())} tokens")
    return found


def _rank(category: str, qid: str) -> str:
    return hashlib.sha256(f"{SPOT_CHECK_SEED}|{category}|{qid}".encode()).hexdigest()


def summarize(runs: list[dict[str, Any]]) -> dict[str, Any]:
    """Counts by category and split, 2 examples and a seeded spot-check list per category."""
    counts: dict[str, dict[str, int]] = {c: {} for c in CATEGORIES}
    members: dict[str, list[dict[str, Any]]] = {c: [] for c in CATEGORIES}
    for run in runs:
        for category in run["categories"]:
            counts[category][run["split"]] = counts[category].get(run["split"], 0) + 1
            members[category].append(run)
    out = {}
    for category in CATEGORIES:
        ranked = sorted(members[category], key=lambda r: _rank(category, r["question_id"]))
        out[category] = {
            "counts": counts[category],
            "examples": [
                {"question_id": r["question_id"], "split": r["split"]}
                | {"evidence": r["categories"][category]}
                for r in ranked[:2]
            ],
            "spot_check": [r["question_id"] for r in ranked[:SPOT_CHECK_N]],
        }
    return out


def main(argv: list[str] | None = None) -> int:
    from uuid import UUID

    from evals.runner import HANDWRITTEN, Runner, load_config, replay_deps
    from filinglens.agents.settings import RuntimeSettings
    from filinglens.agents.tracing import load_run

    parser = argparse.ArgumentParser(description="Categorize failures from cached runs (D112).")
    parser.add_argument("configs", nargs="+", type=Path)
    parser.add_argument("--system", action="append", help="system ids to include (default all)")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    settings = RuntimeSettings()
    gold = {
        row["id"]: row["gold_chunk_ids"]
        for row in map(json.loads, HANDWRITTEN.read_text(encoding="utf-8").splitlines())
    }
    runs = []
    for path in args.configs:
        cfg = load_config(path)
        result = asyncio.run(Runner(cfg, replay_deps(cfg, settings), replay_only=True).run())
        for system_id, records in result["records"].items():
            kinds = {s.id: s.kind for s in cfg.systems}
            if kinds[system_id] != "system" or (args.system and system_id not in args.system):
                continue
            for record in records:
                events = []
                if record.get("run_id"):
                    _, events = load_run(settings.database_url, UUID(record["run_id"]))
                categories = categorize(record, events, gold.get(record["question_id"]))
                runs.append(
                    {
                        "config": cfg.name,
                        "system_id": system_id,
                        "question_id": record["question_id"],
                        "split": record["split"],
                        "categories": categories,
                    }
                )
    out = {"runs": runs, "summary": summarize(runs)}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, indent=1, sort_keys=True), encoding="utf-8")
    for category, row in out["summary"].items():
        if row["counts"]:
            print(f"{category}: {row['counts']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Offline check of the D117 summary rule on DEV pilot first drafts only (no API calls).

For every M5 dev-pilot system run, the analyst's first draft (analyst:r0's final JSON) and the
evidence ledger as it stood then are rebuilt from the recorded trace. Stage 1 runs on the draft
with the rule off (M5) and on. The rule is kept only if it clears at least half of the dev
first-round summary failures with no false acceptance; every newly accepted number is listed
with the cited value it matched and the summary text around it, for review. Test drafts are
never read here.

    python -m evals.summary_rule_check --out evals/results/m6_summary_rule_dev.json
"""

import argparse
import asyncio
import json
import re
from pathlib import Path
from typing import Any
from uuid import UUID

from filinglens.agents.ledger import Ledger
from filinglens.agents.loop import extract_json
from filinglens.agents.schemas import Answer
from filinglens.agents.verifier import (
    _summary_numbers,
    cited_values,
    deterministic_checks,
    rounded_display_of,
)
from filinglens.config import ROOT

DEV_PILOT = ROOT / "evals" / "configs" / "m5_dev_pilot.toml"


def first_draft(events: list[Any]) -> tuple[Answer, Ledger] | None:
    """analyst:r0's accepted draft and the ledger built from every tool result before it."""
    ledger = Ledger()
    calls: dict[str, dict] = {}
    draft = None
    for e in events:
        p = e.payload
        if e.event_type == "tool_call":
            calls[p["call_id"]] = p
        elif e.event_type == "tool_result" and draft is None:
            call = calls.get(p["call_id"], {})
            if p.get("duplicate_of"):
                continue  # a duplicate is never registered twice (D067)
            ledger.register(
                p["tool"],
                call.get("arguments") or {},
                p.get("structured"),
                p["is_error"],
                p.get("computation_id"),
            )
        elif e.event_type == "llm_call" and p["instance"] == "analyst:r0" and draft is None:
            response = p["response"]
            if response.get("tool_calls"):
                continue
            try:
                draft = Answer.model_validate(extract_json(response.get("text") or ""))
            except ValueError:
                continue  # an invalid reply that got the corrective retry
    return (draft, ledger) if draft is not None else None


def context(text: str, token: str, width: int = 60) -> str:
    match = re.search(re.escape(token).replace(r"\.", r"\.?"), text.replace(",", ""))
    if not match:
        return text[:120]
    plain = text.replace(",", "")
    return plain[max(0, match.start() - width) : match.end() + width]


def check(records: list[dict[str, Any]], load_events) -> dict[str, Any]:
    rows, failing_off, cleared, partial, accepted = [], 0, 0, 0, []
    for record in records:
        if record["split"] != "dev":
            raise ValueError(f"{record['question_id']} is not a dev record; test is never read")
        rebuilt = first_draft(load_events(record["run_id"]))
        if rebuilt is None:
            rows.append({"question_id": record["question_id"], "draft": False})
            continue
        draft, ledger = rebuilt
        off = deterministic_checks(draft, ledger, True)["summary"]
        on = deterministic_checks(draft, ledger, True, summary_cited_values=True)["summary"]
        row = {"question_id": record["question_id"], "draft": True, "off": off.reasons}
        if off.verdict != "supported":
            failing_off += 1
            row["on"] = on.reasons
            if on.verdict == "supported":
                cleared += 1
            elif len(on.reasons[0]) < len(off.reasons[0]):
                partial += 1
            claimed = set().union(*(_summary_numbers(c.text) for c in draft.claims))
            values = cited_values(draft, ledger)
            for token in sorted(_summary_numbers(draft.summary) - claimed):
                match = rounded_display_of(token, values)
                if match is not None:
                    accepted.append(
                        {
                            "question_id": record["question_id"],
                            "number": token,
                            "matched_cited_value": str(match),
                            "summary_context": context(draft.summary, token),
                        }
                    )
        rows.append(row)
    return {
        "dev_runs": len(records),
        "drafts_rebuilt": sum(r["draft"] for r in rows),
        "summary_failures_off": failing_off,
        "cleared_on": cleared,
        "partly_cleared_on": partial,
        "newly_accepted_numbers": accepted,
        "rows": rows,
    }


def main(argv: list[str] | None = None) -> int:
    from evals.runner import Runner, load_config, replay_deps
    from filinglens.agents.settings import RuntimeSettings
    from filinglens.agents.tracing import load_run

    parser = argparse.ArgumentParser(description="D117 summary rule, dev pilot drafts only")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    settings = RuntimeSettings()
    cfg = load_config(DEV_PILOT)
    assert cfg.split == "dev"
    result = asyncio.run(Runner(cfg, replay_deps(cfg, settings), replay_only=True).run())
    records = result["records"]["system"]
    out = check(records, lambda rid: load_run(settings.database_url, UUID(rid))[1])
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in out.items() if k not in ("rows", "newly_accepted_numbers")}))
    for row in out["newly_accepted_numbers"]:
        print(row)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

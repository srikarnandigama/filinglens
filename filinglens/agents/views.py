"""Deterministic model-facing views of large tool results (raw results stay in the trace)."""

from collections import defaultdict
from typing import Any

DISCOVERY_VIEW_VERSION = "discovery_view_v1"
ORDER = {"Q1": 0, "Q2": 1, "Q3": 2, "Q4": 3, "FY": 4}


def _period(p: dict | None) -> str | None:
    return None if p is None else f"FY{p['fiscal_year']} {p['fiscal_period']}"


def discovery_view(data: dict[str, Any]) -> dict[str, Any]:
    """Compact list_available_metrics: every period, status, latest field and reason is kept."""
    calendar: dict[tuple[int, str, str], dict] = {}
    metrics = []
    for metric in data["metrics"]:
        available: dict[str, list[str]] = defaultdict(list)
        for p in metric["available_periods"]:
            available[str(p["fiscal_year"])].append(p["fiscal_period"])
            key = (p["fiscal_year"], p["fiscal_period"], p["period_type"])
            calendar[key] = p
        statuses: dict[tuple[str, str | None, str], list[str]] = defaultdict(list)
        for s in metric["period_statuses"]:
            if s["status"] != "available":
                statuses[(s["status"], s.get("stored_status"), s["reason"])].append(
                    f"FY{s['fiscal_year']} {s['fiscal_period']}"
                )
        entry = {
            "metric": metric["metric"],
            "unit": metric["unit"],
            "status": metric["status"],
            "reason": metric["reason"],
            "latest_quarter": _period(metric["latest_quarter"]),
            "latest_annual": _period(metric["latest_annual"]),
            "latest_year_end": _period(metric["latest_year_end"]),
            "year_end_alias": metric["year_end_alias"],
            "available": {
                year: sorted(periods, key=ORDER.__getitem__)
                for year, periods in sorted(available.items())
            },
            "not_available": [
                {"periods": periods, "status": status, "stored_status": stored, "reason": reason}
                for (status, stored, reason), periods in statuses.items()
            ],
        }
        evidence = sorted(
            {c for e in metric.get("applicability_evidence", []) for c in e["chunk_ids"]}
        )
        if evidence:
            entry["applicability_evidence_chunk_ids"] = evidence
        metrics.append(entry)
    period_calendar = [
        f"FY{p['fiscal_year']} {p['fiscal_period']} ({p['period_type']}): "
        f"{p['period_start'] or '-'} to {p['period_end']}"
        for (_, _, _), p in sorted(
            calendar.items(), key=lambda kv: (kv[1]["period_end"], ORDER[kv[1]["fiscal_period"]])
        )
    ]
    return {
        "view": DISCOVERY_VIEW_VERSION,
        "ticker": data["ticker"],
        "snapshot": data["snapshot"],
        "latest_common_quarter": data["latest_common_quarter"],
        "latest_common_quarter_reason": data["latest_common_quarter_reason"],
        "period_calendar": period_calendar,
        "metrics": metrics,
    }

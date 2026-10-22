"""Planner role: question → explicit, snapshot-checked Plan (SPEC §10.5, lessons from M3)."""

from collections.abc import Callable

from filinglens.agents.ledger import Ledger
from filinglens.agents.loop import SemanticError
from filinglens.agents.schemas import Plan


def _known_periods(discovery: dict, metric: str) -> set[tuple[int, str]]:
    for entry in discovery["metrics"]:
        if entry["metric"] != metric:
            continue
        known = {(p["fiscal_year"], p["fiscal_period"]) for p in entry["available_periods"]}
        known |= {(s["fiscal_year"], s["fiscal_period"]) for s in entry["period_statuses"]}
        if entry.get("year_end_alias") == "FY_to_Q4":
            known |= {(year, "FY") for year, period in known if period == "Q4"}
        return known
    return set()


def _filing_periods(discovery: dict) -> set[tuple[int, str]]:
    periods = set()
    for entry in discovery["metrics"]:
        for p in entry["available_periods"]:
            if p["period_type"] == "annual":
                periods.add((p["fiscal_year"], "FY"))
            elif p["fiscal_period"] in {"Q1", "Q2", "Q3"}:
                periods.add((p["fiscal_year"], p["fiscal_period"]))
    return periods


def plan_validator(ledger: Ledger) -> Callable[[Plan], None]:
    def validate(plan: Plan) -> None:
        errors: list[str] = []
        ids = {s.id for s in plan.subtasks}
        tickers = set(plan.companies) | {
            s.params.ticker for s in plan.subtasks if s.type != "computation"
        }
        for ticker in sorted(tickers):
            if ticker not in ledger.discovery:
                errors.append(f"Call list_available_metrics for {ticker} before planning.")
        for s in plan.subtasks:
            for dep in s.depends_on:
                if dep not in ids:
                    errors.append(f"{s.id} depends on unknown subtask {dep}.")
            p = s.params
            if p.kind == "metric_lookup" and p.ticker in ledger.discovery:
                known = _known_periods(ledger.discovery[p.ticker], p.metric)
                for period in p.periods:
                    if (period.fiscal_year, period.fiscal_period) not in known:
                        errors.append(
                            f"{s.id}: {p.ticker} {p.metric} {period.label()} is not in the "
                            "snapshot's discovery result; choose periods from "
                            "list_available_metrics or mark the plan not_available."
                        )
            elif p.kind == "filing_search" and p.ticker in ledger.discovery:
                if (p.fiscal_year, p.fiscal_period) not in _filing_periods(
                    ledger.discovery[p.ticker]
                ):
                    errors.append(
                        f"{s.id}: no {p.ticker} filing period FY{p.fiscal_year} "
                        f"{p.fiscal_period} appears in the snapshot's discovery result."
                    )
            elif p.kind == "computation":
                for ref in p.inputs:
                    if ref.subtask_id not in ids:
                        errors.append(f"{s.id} uses unknown subtask {ref.subtask_id}.")
        errors.extend(_cycles(plan))
        if errors:
            raise SemanticError("\n".join(errors))

    return validate


def _cycles(plan: Plan) -> list[str]:
    graph = {s.id: list(s.depends_on) for s in plan.subtasks}
    state: dict[str, int] = {}

    def visit(node: str) -> bool:
        if state.get(node) == 1:
            return True
        if state.get(node) == 2 or node not in graph:
            return False
        state[node] = 1
        if any(visit(dep) for dep in graph[node]):
            return True
        state[node] = 2
        return False

    return ["depends_on contains a cycle."] if any(visit(n) for n in graph) else []

"""Schemas, pricing, plan validation, discovery view and CLI rendering (offline, synthetic)."""

from decimal import Decimal
from uuid import uuid4

import pytest
from pydantic import ValidationError

from filinglens.agents.ledger import Ledger
from filinglens.agents.loop import SemanticError
from filinglens.agents.orchestrator import RunConfig, RunResult, resolve_models
from filinglens.agents.planner import plan_validator
from filinglens.agents.prompts import load_prompt
from filinglens.agents.schemas import Answer, Claim, FilingSearchParams, Plan, SubTask
from filinglens.agents.settings import RuntimeSettings
from filinglens.agents.tracing import RunTotals
from filinglens.agents.views import discovery_view
from filinglens.cli import config_from_args, parser, render
from filinglens.llm.base import Usage
from filinglens.llm.pricing import PriceTable, PricingError


def test_decimal_strings_and_claim_rules():
    base = {
        "id": "c1",
        "kind": "numeric",
        "text": "t",
        "unit": "USD",
        "value_basis": "fact",
        "citations": [{"kind": "fact", "ref": "1"}],
    }
    for good in ["0", "-12", "1234567890123.000001"]:
        Claim.model_validate({**base, "value": good})
    for bad in ["1e5", "01", "1.", "+3", "NaN", 1.5]:
        with pytest.raises(ValidationError):
            Claim.model_validate({**base, "value": bad})
    with pytest.raises(ValidationError):
        Claim.model_validate({**base, "value": None})
    with pytest.raises(ValidationError):
        Claim.model_validate({**base, "value": "1", "citations": []})
    with pytest.raises(ValidationError, match="final_value"):
        Answer.model_validate(
            {
                "status": "answered",
                "summary": "s",
                "claims": [{**base, "value": "1"}],
                "final_value": "1",
            }
        )
    with pytest.raises(ValidationError):
        Answer.model_validate({"status": "answered", "summary": "s", "claims": []})
    Answer.model_validate({"status": "not_available", "summary": "s", "claims": []})


def test_structured_subtasks_require_filters_and_matching_kinds():
    with pytest.raises(ValidationError):
        FilingSearchParams(
            kind="filing_search",
            ticker="MSFT",
            fiscal_year=2025,
            fiscal_period="Q4",
            items=["7"],
            query="q",
        )
    with pytest.raises(ValidationError, match="items"):
        FilingSearchParams(
            kind="filing_search",
            ticker="MSFT",
            fiscal_year=2025,
            fiscal_period="Q1",
            items=["7"],
            query="q",
        )
    with pytest.raises(ValidationError, match="params.kind"):
        SubTask.model_validate(
            {
                "id": "s1",
                "type": "filing_search",
                "description": "d",
                "params": {
                    "kind": "metric_lookup",
                    "ticker": "A",
                    "metric": "revenue",
                    "periods": [{"fiscal_year": 2025, "fiscal_period": "FY"}],
                },
            }
        )
    with pytest.raises(ValidationError, match="at least one subtask"):
        Plan.model_validate(
            {"question_type": "lookup", "companies": ["A"], "answerability": "answerable"}
        )


def discovery():
    """Synthetic list_available_metrics payload shaped like edgar-mcp's MetricsData."""

    def period(fy, fp, ptype="quarter", end="2025-03-31"):
        return {
            "fiscal_year": fy,
            "fiscal_period": fp,
            "period_start": "2025-01-01",
            "period_end": end,
            "period_type": ptype,
            "stored_fiscal_period": fp,
        }

    return {
        "ticker": "TEST",
        "snapshot": {"snapshot_id": "x", "cutoff_date": "2026-10-19"},
        "latest_common_quarter": period(2025, "Q1"),
        "latest_common_quarter_reason": None,
        "metrics": [
            {
                "metric": "revenue",
                "unit": "USD",
                "status": "available",
                "reason": None,
                "available_periods": [
                    period(2025, "Q1"),
                    period(2024, "FY", "annual", "2024-12-31"),
                ],
                "earliest": None,
                "latest": None,
                "latest_quarter": period(2025, "Q1"),
                "latest_annual": period(2024, "FY", "annual"),
                "latest_year_end": None,
                "year_end_alias": None,
                "period_statuses": [
                    {
                        "fiscal_year": 2025,
                        "fiscal_period": "Q1",
                        "status": "available",
                        "stored_status": "available",
                        "reason": "ok",
                    },
                    {
                        "fiscal_year": 2024,
                        "fiscal_period": "Q4",
                        "status": "unavailable",
                        "stored_status": "unavailable",
                        "reason": "not filed",
                    },
                ],
                "applicability_evidence": [],
            },
            {
                "metric": "total_assets",
                "unit": "USD",
                "status": "available",
                "reason": None,
                "available_periods": [period(2024, "Q4", "instant")],
                "earliest": None,
                "latest": None,
                "latest_quarter": None,
                "latest_annual": None,
                "latest_year_end": period(2024, "Q4", "instant"),
                "year_end_alias": "FY_to_Q4",
                "period_statuses": [],
                "applicability_evidence": [
                    {
                        "policy_id": "p",
                        "source": {"accession": None, "filed_date": None, "url": None},
                        "chunk_ids": ["chk_" + "b" * 64],
                        "explanation": "e",
                    }
                ],
            },
        ],
    }


def test_discovery_view_keeps_every_period_status_and_latest_field():
    view = discovery_view(discovery())
    revenue, assets = view["metrics"]
    assert revenue["available"] == {"2024": ["FY"], "2025": ["Q1"]}
    assert revenue["not_available"] == [
        {
            "periods": ["FY2024 Q4"],
            "status": "unavailable",
            "stored_status": "unavailable",
            "reason": "not filed",
        }
    ]
    assert revenue["latest_quarter"] == "FY2025 Q1" and revenue["latest_annual"] == "FY2024 FY"
    assert assets["year_end_alias"] == "FY_to_Q4"
    assert assets["applicability_evidence_chunk_ids"] == ["chk_" + "b" * 64]
    assert any(line.startswith("FY2024 FY (annual)") for line in view["period_calendar"])


def plan(subtasks, companies=("TEST",)):
    return Plan.model_validate(
        {
            "question_type": "lookup",
            "companies": list(companies),
            "answerability": "answerable",
            "subtasks": subtasks,
        }
    )


def lookup(sid, fy, fp, metric="revenue", deps=()):
    return {
        "id": sid,
        "type": "metric_lookup",
        "description": "d",
        "depends_on": list(deps),
        "params": {
            "kind": "metric_lookup",
            "ticker": "TEST",
            "metric": metric,
            "periods": [{"fiscal_year": fy, "fiscal_period": fp}],
        },
    }


def test_plan_validator_uses_discovery_periods_and_rejects_cycles():
    led = Ledger()
    validate = plan_validator(led)
    with pytest.raises(SemanticError, match="list_available_metrics for TEST"):
        validate(plan([lookup("s1", 2025, "Q1")]))
    led.discovery["TEST"] = discovery()
    validate(
        plan(
            [
                lookup("s1", 2025, "Q1"),
                lookup("s2", 2024, "Q4"),
                lookup("s3", 2024, "FY", "total_assets"),
            ]
        )
    )  # status-only period and FY alias
    with pytest.raises(SemanticError, match="FY2030 Q1"):
        validate(plan([lookup("s1", 2030, "Q1")]))
    with pytest.raises(SemanticError, match="cycle"):
        validate(
            plan([lookup("s1", 2025, "Q1", deps=["s2"]), lookup("s2", 2025, "Q1", deps=["s1"])])
        )
    search = {
        "id": "s9",
        "type": "filing_search",
        "description": "d",
        "params": {
            "kind": "filing_search",
            "ticker": "TEST",
            "fiscal_year": 2023,
            "fiscal_period": "FY",
            "items": ["7"],
            "query": "q",
        },
    }
    with pytest.raises(SemanticError, match="FY2023 FY"):
        validate(plan([search]))


def test_pricing_toml_decimal_costs_and_preflight(tmp_path):
    path = tmp_path / "pricing.toml"
    path.write_text(
        '[models."m-1"]\ninput_per_mtok = "3.00"\noutput_per_mtok = "15"\n', encoding="utf-8"
    )
    table = PriceTable.load(path)
    assert table.cost("m-1", Usage(input_tokens=1000, output_tokens=100)) == Decimal("0.0045")
    with pytest.raises(PricingError, match="m-2"):
        table.require({"m-1", "m-2"})
    with pytest.raises(PricingError, match="cache"):
        table.cost("m-1", Usage(cache_read_tokens=5))
    snapshot = table.snapshot({"m-1"})
    assert PriceTable.from_snapshot(snapshot).cost("m-1", Usage(input_tokens=10)) == Decimal(
        "0.00003"
    )
    path.write_text(
        '[models."m-1"]\ninput_per_mtok = 3.0\noutput_per_mtok = "1"\n', encoding="utf-8"
    )
    with pytest.raises(PricingError, match="decimal string"):
        PriceTable.load(path)
    with pytest.raises(PricingError, match="Missing"):
        PriceTable.load(tmp_path / "absent.toml")


def test_prompts_append_schema_and_models_come_from_env():
    system, sha = load_prompt("planner", Plan)
    assert "You are the planner" in system and '"period_resolutions"' in system and len(sha) == 64
    settings = RuntimeSettings(
        _env_file=None,
        sec_user_agent="FilingLens tests test@example.org",
        planner_model="big",
        worker_model="small",
        verifier_model="big",
    )
    assert resolve_models(RunConfig(), settings) == {
        "planner": "big",
        "worker": "small",
        "verifier": "big",
    }
    swapped = RunConfig(worker_model_env="PLANNER_MODEL")
    assert resolve_models(swapped, settings)["worker"] == "big"
    with pytest.raises(ValueError, match="WORKER_MODEL"):
        resolve_models(RunConfig(), settings.model_copy(update={"worker_model": None}))


def test_cli_parsing_and_rendering():
    settings = RuntimeSettings(_env_file=None, sec_user_agent="FilingLens tests test@example.org")
    args = parser().parse_args(
        [
            "ask",
            "q?",
            "--no-verifier",
            "--no-quant",
            "--retrieval-mode",
            "keyword",
            "--max-cost-usd",
            "0.25",
        ]
    )
    cfg = config_from_args(args, settings)
    assert (cfg.verifier, cfg.use_quant_tools, cfg.retrieval_mode, cfg.max_cost_usd) == (
        False,
        False,
        "keyword",
        Decimal("0.25"),
    )
    led = Ledger()
    led.register(
        "get_financial_metric",
        {},
        {
            "data": {
                "ticker": "TEST",
                "metric": "revenue",
                "snapshot": {},
                "facts": [
                    {
                        "fact_id": "7",
                        "metric": "revenue",
                        "fiscal_year": 2025,
                        "fiscal_period": "Q1",
                        "value": "400",
                        "unit": "USD",
                        "status": "available",
                        "source_accession": "0000000000-25-000001",
                        "source_url": "https://www.sec.gov/x",
                    }
                ],
            }
        },
        False,
        None,
    )
    answer = Answer.model_validate(
        {
            "status": "answered",
            "summary": "Revenue was 400.",
            "claims": [
                {
                    "id": "c1",
                    "kind": "numeric",
                    "text": "Revenue was 400.",
                    "value": "400",
                    "unit": "USD",
                    "value_basis": "fact",
                    "citations": [{"kind": "fact", "ref": "7"}],
                }
            ],
            "final_value": "400",
            "final_unit": "USD",
            "final_claim_id": "c1",
        }
    )
    text = render(
        RunResult(
            run_id=uuid4(),
            status="done",
            answer=answer,
            error=None,
            totals=RunTotals(input_tokens=5, cost_usd=Decimal("0.01")),
            ledger=led,
        )
    )
    assert "fact 7: TEST revenue FY2025 Q1 = 400 USD" in text and "https://www.sec.gov/x" in text
    assert "cost_usd: 0.010000" in text


def test_cli_preflight_reports_missing_models_and_prices(monkeypatch, capsys):
    import filinglens.agents.settings as settings_module
    from filinglens.cli import main

    base = RuntimeSettings(_env_file=None, sec_user_agent="FilingLens tests test@example.org")
    monkeypatch.setattr(settings_module, "RuntimeSettings", lambda: base)
    assert main(["ask", "q?"]) == 1
    assert "preflight failed: Set PLANNER_MODEL" in capsys.readouterr().err
    configured = base.model_copy(
        update={"planner_model": "m-big", "worker_model": "m-small", "verifier_model": "m-big"}
    )
    monkeypatch.setattr(settings_module, "RuntimeSettings", lambda: configured)
    monkeypatch.setattr(PriceTable, "load", classmethod(lambda cls: PriceTable({})))
    assert main(["ask", "q?"]) == 1
    assert "pricing.toml has no prices for: m-big, m-small" in capsys.readouterr().err

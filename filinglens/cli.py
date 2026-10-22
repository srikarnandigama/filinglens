"""`filinglens ask "<question>"` and `filinglens replay <run_id>` (SPEC §10, D059)."""

import argparse
import asyncio
import json
import sys
from decimal import Decimal
from uuid import UUID

from filinglens.agents.ledger import Ledger
from filinglens.agents.orchestrator import RunConfig, RunResult, run_question
from filinglens.agents.schemas import Answer
from filinglens.llm.pricing import PricingError


def describe_citation(kind: str, ref: str, field: str | None, ledger: Ledger) -> str:
    if kind == "fact" and ref in ledger.facts:
        f = ledger.facts[ref]
        value = f"{f.value} {f.unit}" if f.value is not None else f"{f.status}: {f.reason}"
        derived = " (derived)" if f.derived else ""
        return (
            f"fact {ref}: {f.ticker} {f.metric} FY{f.fiscal_year} {f.fiscal_period} = {value}"
            f"{derived}; accession {f.source_accession}; {f.source_url}"
        )
    if kind == "chunk":
        p = ledger.passages.get(ref)
        if p:
            return (
                f"chunk {ref}: {p.ticker} {p.form} FY{p.fiscal_year} {p.fiscal_period} "
                f"Item {p.item}; {p.url}"
            )
        return f"chunk {ref} (applicability evidence)"
    if kind == "computation" and ref in ledger.computations:
        c = ledger.computations[ref]
        args = json.dumps(c.arguments, sort_keys=True)
        output = {k: v for k, v in (c.output or {}).items() if k != "precision"}
        shown = json.dumps(output)
        return f"computation {ref}: {c.tool}({args}) -> {shown} [field {field or 'default'}]"
    return f"{kind} {ref}"


def render(result: RunResult) -> str:
    lines = [f"run_id: {result.run_id}", f"status: {result.status}"]
    answer: Answer | None = result.answer
    if result.error:
        lines.append(f"error: {result.error['type']}: {result.error['message']}")
    if answer:
        lines += ["", f"[{answer.status}] {answer.summary}", ""]
        if answer.final_value is not None:
            lines.append(f"final value: {answer.final_value} {answer.final_unit}")
        for claim in answer.claims:
            value = f"  value={claim.value} {claim.unit}" if claim.value is not None else ""
            lines.append(f"- {claim.id}: {claim.text}{value}")
            for cit in claim.citations:
                lines.append(
                    "    " + describe_citation(cit.kind, cit.ref, cit.field, result.ledger)
                )
        if answer.caveats:
            lines += ["", "caveats:"] + [f"- {c}" for c in answer.caveats]
    if result.verification:
        last = result.verification[-1]
        lines += [
            "",
            f"verification: rounds={len(result.verification)} applied={last['applied']} "
            f"still_failing={sorted(last['failing'])}",
        ]
    t = result.totals
    lines += [
        "",
        f"tokens: input={t.input_tokens} output={t.output_tokens} "
        f"cache_read={t.cache_read_tokens} cache_write={t.cache_write_tokens}",
        f"cost_usd: {t.cost_usd.quantize(Decimal('0.000001'))}",
        f"latency_ms: {t.latency_ms}",
    ]
    return "\n".join(lines)


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="filinglens")
    sub = root.add_subparsers(dest="command", required=True)
    ask = sub.add_parser("ask", help="Answer a question with the agent runtime.")
    ask.add_argument("question")
    ask.add_argument("--provider", choices=["anthropic", "openai_compat"], default="anthropic")
    ask.add_argument("--no-verifier", action="store_true")
    ask.add_argument(
        "--retrieval-mode", choices=["vector", "keyword", "hybrid", "hybrid_rerank"], default=None
    )
    ask.add_argument("--no-quant", action="store_true")
    ask.add_argument("--data-worker", choices=["direct", "llm"], default="direct")
    ask.add_argument("--max-cost-usd", type=Decimal, default=None)
    ask.add_argument("--json", action="store_true")
    replay = sub.add_parser("replay", help="Replay a recorded run offline and compare.")
    replay.add_argument("run_id", type=UUID)
    return root


def config_from_args(args, settings) -> RunConfig:
    return RunConfig(
        provider=args.provider,
        verifier=not args.no_verifier,
        retrieval_mode=args.retrieval_mode or settings.retrieval_mode,
        use_quant_tools=not args.no_quant,
        data_worker=args.data_worker,
        max_run_tokens=settings.max_run_tokens,
        max_cost_usd=args.max_cost_usd
        if args.max_cost_usd is not None
        else settings.max_run_cost_usd,
    )


def main(argv: list[str] | None = None) -> int:
    from filinglens.agents.settings import RuntimeSettings

    args = parser().parse_args(argv)
    settings = RuntimeSettings()
    if args.command == "replay":
        from filinglens.agents.replay import replay_run

        report = asyncio.run(replay_run(settings.database_url, args.run_id))
        print(report.model_dump_json(indent=2))
        print("identical" if report.identical else "DIVERGED")
        return 0 if report.identical else 2
    try:
        result = asyncio.run(
            run_question(args.question, config_from_args(args, settings), settings)
        )
    except (PricingError, ValueError) as exc:  # preflight: models, prices, keys
        print(f"preflight failed: {exc}", file=sys.stderr)
        return 1
    if args.json:
        payload = {
            "run_id": str(result.run_id),
            "status": result.status,
            "answer": result.answer.model_dump(mode="json") if result.answer else None,
            "error": result.error,
            "totals": result.totals.model_dump(mode="json"),
        }
        print(json.dumps(payload, indent=2))
    else:
        print(render(result))
    return 0 if result.status == "done" else 1


if __name__ == "__main__":
    sys.exit(main())

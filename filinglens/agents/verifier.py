"""Deterministic claim checks (D056) followed by the LLM verifier for textual support."""

import re
from decimal import Decimal, InvalidOperation
from typing import Any

from pydantic import BaseModel, Field

from filinglens.agents.context import RunContext
from filinglens.agents.ledger import ComputationRecord, Ledger
from filinglens.agents.loop import SemanticError, run_agent
from filinglens.agents.schemas import Answer, Claim, VerifierOutput
from filinglens.agents.toolbox import Toolbox, wrap_evidence

FIELD_PATH = re.compile(r"([A-Za-z_]+)(?:\[(\d+)\])?")
LITERAL = re.compile(r"\d+(?:\.\d+)?")
SUMMARY_NUMBER = re.compile(r"(?<![A-Za-z0-9])\d[\d,]*(?:\.\d+)?")
PERCENT_FIELDS = {"value_pct", "change_pct"}
MAX_CONSTANT = Decimal(100)


class CheckResult(BaseModel):
    claim_id: str
    verdict: str  # supported | unsupported | needs_revision | unverifiable_model_arithmetic
    reasons: list[str] = Field(default_factory=list)


def _dec(value: Any) -> Decimal | None:
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
    return number if number.is_finite() else None


def resolve_field(output: dict | None, field: str | None) -> Any:
    if output is None:
        return None
    if field is None:
        field = "value_pct" if "value_pct" in output else "value" if "value" in output else None
        if field is None:
            return None
    node: Any = output
    for part in field.split("."):
        match = FIELD_PATH.fullmatch(part)
        if not match or not isinstance(node, dict) or match.group(1) not in node:
            return None
        node = node[match.group(1)]
        if match.group(2) is not None:
            index = int(match.group(2))
            if not isinstance(node, list) or index >= len(node):
                return None
            node = node[index]
    return node


def _leaf(field: str | None, output: dict | None) -> str:
    if field:
        return field.split(".")[-1].split("[")[0]
    return "value_pct" if output and "value_pct" in output else "value"


def computation_inputs(record: ComputationRecord) -> list[tuple[Decimal, bool]]:
    """(number, may_be_small_constant) pairs consumed by a quant call."""
    out = record.output or {}
    pairs: list[tuple[Decimal, bool]] = []

    def add(value: Any, constant: bool = False) -> None:
        number = _dec(value)
        if number is not None:
            pairs.append((number, constant))

    if record.tool == "margin":
        add(out.get("numerator")), add(out.get("denominator"))
    elif record.tool == "growth_rate":
        add(out.get("old")), add(out.get("new"))
    elif record.tool == "cagr":
        add(out.get("start_value")), add(out.get("end_value")), add(out.get("years"), True)
    elif record.tool == "yoy_series":
        for point in out.get("points", []):
            add(point.get("value"))
    elif record.tool == "summary_stats":
        for value in out.get("values", []):
            add(value)
    elif record.tool == "evaluate":
        expression = out.get("normalized_expression") or record.arguments.get("expression", "")
        for literal in LITERAL.findall(str(expression)):
            add(literal, True)
    return pairs


def _lineage_values(ledger: Ledger, before: str) -> set[Decimal]:
    limit = int(before.removeprefix("cmp_"))
    values = {abs(Decimal(f.value)) for f in ledger.facts.values() if f.value is not None}
    for cid, record in ledger.computations.items():
        if int(cid.removeprefix("cmp_")) < limit and record.output:
            values |= {abs(v) for v in _numbers(record.output)}
    return values


def _numbers(node: Any) -> list[Decimal]:
    if isinstance(node, dict):
        return [n for k, v in node.items() if k != "precision" for n in _numbers(v)]
    if isinstance(node, list):
        return [n for v in node for n in _numbers(v)]
    number = _dec(node) if isinstance(node, str) else None
    return [number] if number is not None else []


def check_lineage(ledger: Ledger, record: ComputationRecord) -> list[str]:
    allowed = _lineage_values(ledger, record.computation_id)
    problems = []
    for number, constant in computation_inputs(record):
        if abs(number) in allowed:
            continue
        if constant and number == number.to_integral_value() and abs(number) <= MAX_CONSTANT:
            continue
        problems.append(
            f"{record.computation_id} ({record.tool}) input {number} is not a fact value or an "
            "earlier computation output from this run."
        )
    return problems


def check_claim(claim: Claim, ledger: Ledger, use_quant_tools: bool) -> CheckResult:
    reasons: list[str] = []
    for cit in claim.citations:
        if cit.kind == "fact" and cit.ref not in ledger.facts:
            reasons.append(f"fact {cit.ref} was not returned in this run")
        elif cit.kind == "chunk" and not ledger.known_chunk(cit.ref):
            reasons.append(f"chunk {cit.ref} was not returned in this run")
        elif cit.kind == "computation":
            record = ledger.computations.get(cit.ref)
            if record is None or record.is_error:
                reasons.append(f"computation {cit.ref} does not exist or failed")
    if reasons:
        return CheckResult(claim_id=claim.id, verdict="unsupported", reasons=reasons)
    if claim.kind != "numeric":
        return CheckResult(claim_id=claim.id, verdict="supported")
    if claim.value_basis == "model_arithmetic":
        if use_quant_tools:
            return CheckResult(
                claim_id=claim.id,
                verdict="needs_revision",
                reasons=["Arithmetic must be done with quant tools and cite a computation."],
            )
        return CheckResult(claim_id=claim.id, verdict="unverifiable_model_arithmetic")
    value = Decimal(claim.value)
    seen: list[str] = []
    for cit in claim.citations:
        if cit.kind == "fact":
            fact = ledger.facts[cit.ref]
            seen.append(f"fact {cit.ref}={fact.value} ({fact.status})")
            if fact.value is None or Decimal(fact.value) != value:
                continue
            problems = []
            if claim.value_basis != "fact":
                problems.append("value_basis must be fact")
            if claim.unit != fact.unit:
                problems.append(f"unit must be {fact.unit}")
            if claim.ticker and claim.ticker != fact.ticker:
                problems.append(f"ticker must be {fact.ticker}")
            if claim.period and (claim.period.fiscal_year, claim.period.fiscal_period) != (
                fact.fiscal_year,
                fact.fiscal_period,
            ):
                problems.append(f"period must be FY{fact.fiscal_year} {fact.fiscal_period}")
            return _verdict(claim, problems)
        if cit.kind == "computation":
            record = ledger.computations[cit.ref]
            resolved = resolve_field(record.output, cit.field)
            seen.append(f"{cit.ref}.{cit.field or 'default'}={resolved}")
            number = _dec(resolved) if resolved is not None else None
            if number is None or number != value:
                continue
            problems = check_lineage(ledger, record)
            if claim.value_basis != "computation":
                problems.append("value_basis must be computation")
            if _leaf(cit.field, record.output) in PERCENT_FIELDS and claim.unit != "percent":
                problems.append("a value_pct/change_pct output has unit percent")
            return _verdict(claim, problems)
    return CheckResult(
        claim_id=claim.id,
        verdict="needs_revision",
        reasons=[
            f"value {claim.value} does not equal any cited fact value or computation output "
            f"({'; '.join(seen) or 'no fact or computation cited'}); copy the exact value."
        ],
    )


def _verdict(claim: Claim, problems: list[str]) -> CheckResult:
    if problems:
        return CheckResult(claim_id=claim.id, verdict="needs_revision", reasons=problems)
    return CheckResult(claim_id=claim.id, verdict="supported")


def _summary_numbers(text: str) -> set[str]:
    numbers = set()
    for token in SUMMARY_NUMBER.findall(text):
        plain = token.replace(",", "")
        if "." not in plain and (
            len(plain) == 4 and 1900 <= int(plain) <= 2100 or int(plain) < 100
        ):
            continue  # years and small counts ("8 quarters") are not claimed figures
        numbers.add(plain)
    return numbers


def deterministic_checks(
    answer: Answer, ledger: Ledger, use_quant_tools: bool
) -> dict[str, CheckResult]:
    results = {c.id: check_claim(c, ledger, use_quant_tools) for c in answer.claims}
    claimed = (
        set().union(*(_summary_numbers(c.text) for c in answer.claims)) if answer.claims else set()
    )
    missing = sorted(_summary_numbers(answer.summary) - claimed)
    results["summary"] = CheckResult(
        claim_id="summary",
        verdict="needs_revision" if missing else "supported",
        reasons=[f"summary numbers {missing} do not appear in any claim"] if missing else [],
    )
    if answer.final_claim_id:
        final = next(c for c in answer.claims if c.id == answer.final_claim_id)
        if final.value != answer.final_value or final.unit != answer.final_unit:
            results["answer"] = CheckResult(
                claim_id="answer",
                verdict="needs_revision",
                reasons=["final_value/final_unit must equal the final claim's value/unit"],
            )
    return results


def sources_for(answer: Answer, claim_ids: set[str], ledger: Ledger) -> dict[str, Any]:
    facts, chunks, computations = {}, {}, {}
    for claim in answer.claims:
        if claim.id not in claim_ids:
            continue
        for cit in claim.citations:
            if cit.kind == "fact":
                facts[cit.ref] = ledger.facts[cit.ref].model_dump(mode="json")
            elif cit.kind == "computation":
                computations[cit.ref] = ledger.computations[cit.ref].model_dump(mode="json")
            elif cit.ref in ledger.passages:
                p = ledger.passages[cit.ref]
                chunks[cit.ref] = {**p.model_dump(mode="json", exclude={"snippet"})}
    return {"facts": facts, "computations": computations, "passages": chunks}


async def run_verifier(
    ctx: RunContext,
    cfg,
    models,
    prompts,
    *,
    question: str,
    answer: Answer,
    claim_ids: set[str],
    round_no: int,
) -> VerifierOutput:
    instance = f"verifier:r{round_no}"
    prefetch = Toolbox(ctx, instance, tools=("get_passage",))
    for claim in answer.claims:
        if claim.id in claim_ids:
            for cit in claim.citations:
                record = ctx.ledger.passages.get(cit.ref)
                if cit.kind == "chunk" and (record is None or record.full_text is None):
                    await prefetch.call("get_passage", {"chunk_id": cit.ref})
    draft = answer.model_dump(mode="json")
    draft["claims"] = [c for c in draft["claims"] if c["id"] in claim_ids]
    sources = wrap_evidence(sources_for(answer, claim_ids, ctx.ledger))
    task = (
        f"Question: {question}\n\nClaims to verify (and the summary):\n"
        f"{wrap_evidence(draft)}\n\nCited sources:\n{sources}"
    )

    def validate(out: VerifierOutput) -> None:
        got = {v.claim_id for v in out.verdicts}
        if got != claim_ids:
            raise SemanticError(
                f"Give exactly one verdict per claim id {sorted(claim_ids)}; got {sorted(got)}."
            )
        if out.summary_verdict.claim_id != "summary":
            raise SemanticError('summary_verdict.claim_id must be "summary".')

    return await run_agent(
        ctx,
        instance=instance,
        system=prompts["verifier"][0],
        task=task,
        model=models["verifier"],
        provider=cfg.provider,
        output_model=VerifierOutput,
        toolbox=Toolbox(ctx, instance, known_chunks_only=True),
        validator=validate,
        max_steps=cfg.max_steps,
        max_tokens=cfg.max_tokens_per_call,
        effort=cfg.effort.get("verifier"),
        temperature=cfg.temperature,
    )

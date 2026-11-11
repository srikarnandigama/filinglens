"""The shared answer contract: one prompt and one parser for every baseline (D087)."""

import json
import re
from dataclasses import asdict, dataclass
from decimal import Decimal, InvalidOperation
from typing import Any

BASE_PROMPT = (
    "You answer questions about US public companies' financial results as reported in their "
    "SEC 10-K and 10-Q filings. A fiscal year is named for the calendar year in which it ends; "
    "quarters are the company's fiscal quarters. Use the values as most recently reported "
    "(including any restatement). Report money in US dollars, per-share amounts in dollars per "
    "share, growth and margins in percent (negative for a decline), and differences between "
    "percentages in percentage points. If you are not certain, give your best estimate. Only if "
    "the value does not exist for this company and period (for example a bank's gross profit), "
    'answer "not_applicable"; if you believe it was not reported, answer "not_available".'
)
ANSWER_FORMAT = (
    "End your reply with one line of JSON only:\n"
    '{"value": <number or null>, "unit": "<USD | USD millions | USD billions | USD/share | '
    'percent | percentage_points>", "choice": "<ticker, comparison questions only, else null>", '
    '"status": "<answered | not_available | not_applicable>"}'
)
EXTRA = {
    "b0": "",
    "b1": "You may search the web.",
    "b2": "Use only the filing excerpts provided below, which are from the frozen SEC filings.",
}
STATUSES = {"answered", "not_available", "not_applicable"}
OBJECT = re.compile(r"\{[^{}]*\}")


def system_prompt(kind: str) -> str:
    extra = EXTRA[kind]
    return f"{BASE_PROMPT}{' ' + extra if extra else ''}\n{ANSWER_FORMAT}"


@dataclass
class Prediction:
    value: str | None  # decimal string as given (unit not yet normalized)
    unit: str | None
    choice: str | None
    status: str | None
    parse_ok: bool
    parse_error: str | None = None

    def to_json(self) -> dict[str, Any]:
        return asdict(self)


def _number(raw: Any) -> str | None:
    if raw is None:
        return None
    if isinstance(raw, bool):
        raise ValueError("value must be a number, not a boolean")
    text = str(raw).strip().replace(",", "").replace("$", "")
    try:
        number = Decimal(text)
    except InvalidOperation as exc:
        raise ValueError(f"value {raw!r} is not a number") from exc
    if not number.is_finite():
        raise ValueError("value must be finite")
    return format(number, "f")


def parse_answer(text: str) -> Prediction:
    """The last JSON object with a "value" key wins; anything else is a parse failure."""
    found = None
    for match in OBJECT.finditer(text or ""):
        try:
            obj = json.loads(match.group(0))
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict) and "value" in obj:
            found = obj
    if found is None:
        return Prediction(None, None, None, None, False, "no JSON answer object")
    status = str(found.get("status") or "answered").strip().lower()
    if status not in STATUSES:
        return Prediction(None, None, None, None, False, f"unknown status {status!r}")
    try:
        value = _number(found.get("value"))
    except ValueError as exc:
        return Prediction(None, None, None, status, False, str(exc))
    if status == "answered" and value is None:
        return Prediction(None, None, None, status, False, "answered with a null value")
    choice = found.get("choice")
    return Prediction(
        value=value,
        unit=str(found["unit"]) if found.get("unit") is not None else None,
        choice=str(choice).strip().upper() if choice not in (None, "", "null") else None,
        status=status,
        parse_ok=True,
    )

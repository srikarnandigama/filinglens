"""Bounded Decimal inputs, fixed-point serialization and expression parsing."""

import re
from decimal import ROUND_HALF_EVEN, Decimal, DecimalException, localcontext


class ToolFailure(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


PRECISION = {"context_precision": 80, "decimal_places": 12, "rounding": "ROUND_HALF_EVEN"}
LIMIT = Decimal("1e50")
DECIMAL = re.compile(r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)\Z")


def number(value: str | int | float) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, (str, int, float)):
        raise ToolFailure("INVALID_INPUT", "Use a decimal string or JSON number, not a boolean.")
    text = str(value)
    if len(text) > 128:
        raise ToolFailure("NUMERIC_RANGE", "Numeric input exceeds 128 characters.")
    # JSON floats may stringify in exponent form. Decimal handles that conversion;
    # exponent notation in a caller's decimal string remains outside the grammar.
    if isinstance(value, str) and not DECIMAL.fullmatch(text):
        raise ToolFailure("INVALID_INPUT", "Use a finite fixed-point decimal string.")
    try:
        result = Decimal(text)
    except DecimalException as exc:
        raise ToolFailure("INVALID_INPUT", "Use a finite decimal value.") from exc
    if not result.is_finite():
        raise ToolFailure("INVALID_INPUT", "NaN and infinity are not allowed.")
    digits = list(result.as_tuple().digits)
    while digits and digits[-1] == 0:
        digits.pop()
    if len(digits) > 50 or result.copy_abs() > LIMIT:
        raise ToolFailure("NUMERIC_RANGE", "Use at most 50 significant digits and magnitude 10^50.")
    return result


def fixed(value: Decimal) -> str:
    text = format(value, "f")
    return (text.rstrip("0").rstrip(".") if "." in text else text) if value else "0"


def computed(value: Decimal) -> str:
    if not value.is_finite() or abs(value) > LIMIT:
        raise ToolFailure("NUMERIC_RANGE", "Computed value exceeds magnitude 10^50.")
    with localcontext() as ctx:
        ctx.prec = 80
        ctx.rounding = ROUND_HALF_EVEN
        return fixed(value.quantize(Decimal("0.000000000001")))


def change(old: Decimal, new: Decimal) -> Decimal:
    if not old:
        raise ToolFailure("DIVISION_BY_ZERO", "Percentage change needs a nonzero prior value.")
    return (new - old) / abs(old) * 100


class Expression:
    """Recursive descent: sum -> product -> signed atom. No executable Python."""

    def __init__(self, text: str) -> None:
        if not text or len(text) > 512:
            raise ToolFailure("EXPRESSION_LIMIT", "Use 1..512 expression characters.")
        self.normalized = text.translate(str.maketrans({"−": "-", "×": "*", "÷": "/"}))
        self.tokens: list[str] = []
        position = 0
        while position < len(self.normalized):
            char = self.normalized[position]
            if char.isspace():
                position += 1
                continue
            token = re.match(
                r"(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)|[+*/()-]", self.normalized[position:]
            )
            if not token:
                raise ToolFailure(
                    "INVALID_EXPRESSION", "Only decimal literals and + - * / () allowed."
                )
            self.tokens.append(token[0])
            position += len(token[0])
        if len(self.tokens) > 128:
            raise ToolFailure("EXPRESSION_LIMIT", "Use at most 128 tokens.")
        self.position = 0

    def peek(self) -> str | None:
        return self.tokens[self.position] if self.position < len(self.tokens) else None

    def atom(self, depth: int) -> Decimal:
        if depth > 32:
            raise ToolFailure("EXPRESSION_LIMIT", "Nesting/unary depth exceeds 32.")
        token = self.peek()
        self.position += 1
        if token in {"+", "-"}:
            value = self.atom(depth + 1)
            return -value if token == "-" else value
        if token == "(":
            value = self.sum(depth + 1)
            if self.peek() != ")":
                raise ToolFailure("INVALID_EXPRESSION", "A closing parenthesis is required.")
            self.position += 1
            return value
        if token is None or not DECIMAL.fullmatch(token):
            raise ToolFailure("INVALID_EXPRESSION", "A decimal literal is required.")
        return number(token)

    def product(self, depth: int) -> Decimal:
        value = self.atom(depth)
        while self.peek() in {"*", "/"}:
            operator = self.peek()
            self.position += 1
            right = self.atom(depth)
            if operator == "/" and not right:
                raise ToolFailure("DIVISION_BY_ZERO", "Expression denominator is zero.")
            value = value * right if operator == "*" else value / right
            if abs(value) > LIMIT:
                raise ToolFailure("NUMERIC_RANGE", "Intermediate value exceeds magnitude 10^50.")
        return value

    def sum(self, depth: int = 0) -> Decimal:
        value = self.product(depth)
        while self.peek() in {"+", "-"}:
            operator = self.peek()
            self.position += 1
            right = self.product(depth)
            value = value + right if operator == "+" else value - right
            if abs(value) > LIMIT:
                raise ToolFailure("NUMERIC_RANGE", "Intermediate value exceeds magnitude 10^50.")
        return value

    def calculate(self) -> Decimal:
        value = self.sum()
        if self.peek() is not None:
            raise ToolFailure("INVALID_EXPRESSION", "Unexpected token or implicit multiplication.")
        return value

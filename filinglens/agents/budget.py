"""Run-wide token, cost and step limits shared by every agent instance (D060)."""

from decimal import Decimal

from filinglens.agents.tracing import RunTotals
from filinglens.llm.base import Usage
from filinglens.llm.pricing import PriceTable


class BudgetExceeded(RuntimeError):
    def __init__(self, kind: str, message: str) -> None:
        super().__init__(message)
        self.kind = kind


class RunBudget:
    """Checked before every LLM call and updated after it; overshoot is at most one call."""

    def __init__(
        self, *, max_tokens: int, prices: PriceTable, max_cost_usd: Decimal | None = None
    ) -> None:
        self.max_tokens = max_tokens
        self.max_cost_usd = max_cost_usd
        self.prices = prices
        self.totals = RunTotals()

    @property
    def used_tokens(self) -> int:
        t = self.totals
        return t.input_tokens + t.output_tokens + t.cache_read_tokens + t.cache_write_tokens

    def check_before_call(self) -> None:
        if self.used_tokens >= self.max_tokens:
            raise BudgetExceeded(
                "tokens", f"Run used {self.used_tokens} tokens of MAX_RUN_TOKENS={self.max_tokens}."
            )
        if self.max_cost_usd is not None and self.totals.cost_usd >= self.max_cost_usd:
            raise BudgetExceeded(
                "cost", f"Run cost ${self.totals.cost_usd} reached the ${self.max_cost_usd} cap."
            )

    def add(self, model: str, usage: Usage) -> Decimal:
        cost = self.prices.cost(model, usage)
        t = self.totals
        t.input_tokens += usage.input_tokens
        t.output_tokens += usage.output_tokens
        t.cache_read_tokens += usage.cache_read_tokens
        t.cache_write_tokens += usage.cache_write_tokens
        t.cost_usd += cost
        return cost

"""Per-model prices from the student-maintained pricing.toml (D060); never hardcoded."""

import hashlib
import tomllib
from decimal import Decimal, InvalidOperation
from pathlib import Path

from pydantic import BaseModel

from filinglens.llm.base import Usage

PRICING_PATH = Path(__file__).with_name("pricing.toml")
MILLION = Decimal(1_000_000)


class PricingError(RuntimeError):
    pass


class ModelPrice(BaseModel):
    input_per_mtok: Decimal
    output_per_mtok: Decimal
    cache_read_per_mtok: Decimal | None = None
    cache_write_per_mtok: Decimal | None = None

    def cost(self, usage: Usage) -> Decimal:
        if usage.cache_read_tokens and self.cache_read_per_mtok is None:
            raise PricingError("Cache-read tokens were billed but no cache_read_per_mtok is set.")
        if usage.cache_write_tokens and self.cache_write_per_mtok is None:
            raise PricingError("Cache-write tokens were billed but no cache_write_per_mtok is set.")
        total = (
            usage.input_tokens * self.input_per_mtok
            + usage.output_tokens * self.output_per_mtok
            + usage.cache_read_tokens * (self.cache_read_per_mtok or 0)
            + usage.cache_write_tokens * (self.cache_write_per_mtok or 0)
        )
        return total / MILLION


def _decimal(model: str, field: str, value: object, *, required: bool) -> Decimal | None:
    if value in (None, ""):
        if required:
            raise PricingError(f"pricing.toml: {model} needs {field}.")
        return None
    if not isinstance(value, str):
        raise PricingError(f"pricing.toml: {model}.{field} must be a decimal string.")
    try:
        number = Decimal(value)
    except InvalidOperation as exc:
        raise PricingError(f"pricing.toml: {model}.{field} is not a decimal.") from exc
    if not number.is_finite() or number < 0:
        raise PricingError(f"pricing.toml: {model}.{field} must be finite and non-negative.")
    return number


class PriceTable:
    def __init__(self, prices: dict[str, ModelPrice], sha256: str | None = None) -> None:
        self.prices = prices
        self.sha256 = sha256

    @classmethod
    def load(cls, path: Path = PRICING_PATH) -> "PriceTable":
        if not path.exists():
            raise PricingError(f"Missing {path}; copy pricing.example.toml and fill in prices.")
        data = path.read_bytes()
        models = tomllib.loads(data.decode("utf-8")).get("models", {})
        prices = {
            name: ModelPrice(
                input_per_mtok=_decimal(
                    name, "input_per_mtok", entry.get("input_per_mtok"), required=True
                ),
                output_per_mtok=_decimal(
                    name, "output_per_mtok", entry.get("output_per_mtok"), required=True
                ),
                cache_read_per_mtok=_decimal(
                    name, "cache_read_per_mtok", entry.get("cache_read_per_mtok"), required=False
                ),
                cache_write_per_mtok=_decimal(
                    name, "cache_write_per_mtok", entry.get("cache_write_per_mtok"), required=False
                ),
            )
            for name, entry in models.items()
        }
        return cls(prices, hashlib.sha256(data).hexdigest())

    @classmethod
    def from_snapshot(cls, snapshot: dict) -> "PriceTable":
        prices = {name: ModelPrice.model_validate(p) for name, p in snapshot["models"].items()}
        return cls(prices, snapshot.get("sha256"))

    def require(self, models: set[str]) -> None:
        missing = sorted(m for m in models if m not in self.prices)
        if missing:
            raise PricingError(f"pricing.toml has no prices for: {', '.join(missing)}")

    def snapshot(self, models: set[str]) -> dict:
        return {
            "sha256": self.sha256,
            "models": {m: self.prices[m].model_dump(mode="json") for m in sorted(models)},
        }

    def cost(self, model: str, usage: Usage) -> Decimal:
        if model not in self.prices:
            raise PricingError(f"pricing.toml has no prices for: {model}")
        return self.prices[model].cost(usage)

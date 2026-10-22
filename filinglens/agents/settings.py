"""Agent-runtime settings; kept separate so MCP server processes never load LLM keys."""

from decimal import Decimal

from pydantic import Field, SecretStr, field_validator

from filinglens.config import Settings


def _blank_to_none(value):
    return None if isinstance(value, str) and not value.strip() else value


class RuntimeSettings(Settings):
    anthropic_api_key: SecretStr | None = None
    openai_compat_api_key: SecretStr | None = None
    openai_compat_base_url: str | None = None
    planner_model: str | None = None
    worker_model: str | None = None
    verifier_model: str | None = None
    open_model: str | None = None
    max_run_tokens: int = Field(default=200_000, gt=0)
    max_run_cost_usd: Decimal | None = None
    retrieval_mode: str = "vector"

    @field_validator(
        "anthropic_api_key",
        "openai_compat_api_key",
        "openai_compat_base_url",
        "planner_model",
        "worker_model",
        "verifier_model",
        "open_model",
        "max_run_cost_usd",
        mode="before",
    )
    @classmethod
    def blanks_are_unset(cls, value):
        return _blank_to_none(value)

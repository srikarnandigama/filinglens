"""Normalized messages, tool calls and responses shared by every provider."""

import hashlib
import json
from typing import Any, Literal, Protocol

from pydantic import BaseModel, Field

StopReason = Literal["end_turn", "tool_use", "max_tokens", "refusal", "other"]


class ToolSpec(BaseModel):
    name: str
    description: str
    input_schema: dict[str, Any]


class ToolCall(BaseModel):
    id: str
    name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    arguments_error: str | None = None


class ToolResultPart(BaseModel):
    tool_call_id: str
    content: str
    is_error: bool = False


class Msg(BaseModel):
    role: Literal["user", "assistant", "tool_results"]
    text: str | None = None
    tool_calls: list[ToolCall] = Field(default_factory=list)
    tool_results: list[ToolResultPart] = Field(default_factory=list)
    # Assistant turns are replayed from the provider's exact content blocks.
    provider_raw: list[dict[str, Any]] | None = None


class Usage(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0

    @property
    def total(self) -> int:
        return (
            self.input_tokens
            + self.output_tokens
            + self.cache_read_tokens
            + self.cache_write_tokens
        )


class LLMResponse(BaseModel):
    text: str
    tool_calls: list[ToolCall]
    stop_reason: StopReason
    raw_stop_reason: str | None
    usage: Usage
    model: str
    request_id: str | None = None
    provider_raw: list[dict[str, Any]]
    latency_ms: int = 0


class LLMRequest(BaseModel):
    provider: str
    model: str
    system: str
    messages: list[Msg]
    tools: list[ToolSpec] = Field(default_factory=list)
    max_tokens: int
    effort: str | None = None
    temperature: float | None = None

    def fingerprint(self) -> str:
        return canonical_sha256(self.model_dump(mode="json"))


class Provider(Protocol):
    name: str

    async def complete(
        self,
        *,
        system: str,
        messages: list[Msg],
        tools: list[ToolSpec] | None,
        model: str,
        max_tokens: int,
        temperature: float | None = None,
        effort: str | None = None,
    ) -> LLMResponse: ...


class ProviderError(RuntimeError):
    """A provider call failed after the SDK's own retries."""

    def __init__(
        self, provider: str, message: str, *, status: int | None, retryable: bool, request_id=None
    ):
        super().__init__(f"{provider} request failed ({status}): {message}")
        self.provider = provider
        self.status = status
        self.retryable = retryable
        self.request_id = request_id


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode()).hexdigest()


def parse_arguments(raw: str | None) -> tuple[dict[str, Any], str | None]:
    """Parse provider tool arguments; malformed JSON becomes an error, not a crash."""
    try:
        value = json.loads(raw or "{}")
    except json.JSONDecodeError as exc:
        return {}, f"Tool arguments were not valid JSON: {exc.msg}"
    if not isinstance(value, dict):
        return {}, "Tool arguments must be a JSON object."
    return value, None

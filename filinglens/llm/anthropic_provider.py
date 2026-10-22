"""Anthropic Messages API adapter (API version 2026-10-21; no sampling parameters)."""

import time
from typing import Any

import anthropic

from filinglens.llm.base import (
    LLMResponse,
    Msg,
    ProviderError,
    StopReason,
    ToolCall,
    ToolSpec,
    Usage,
)
from filinglens.llm.tools import anthropic_tool

STOP_REASONS: dict[str, StopReason] = {
    "end_turn": "end_turn",
    "stop_sequence": "end_turn",
    "tool_use": "tool_use",
    "max_tokens": "max_tokens",
    "refusal": "refusal",
}


def to_anthropic_messages(messages: list[Msg]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for msg in messages:
        if msg.role == "user":
            out.append({"role": "user", "content": msg.text or ""})
        elif msg.role == "assistant":
            if msg.provider_raw is None:
                raise ValueError("Assistant turns must carry the provider's exact content blocks.")
            out.append({"role": "assistant", "content": msg.provider_raw})
        else:
            out.append(
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": part.tool_call_id,
                            "content": part.content,
                            "is_error": part.is_error,
                        }
                        for part in msg.tool_results
                    ],
                }
            )
    return out


def normalize_message(message: Any, latency_ms: int) -> LLMResponse:
    raw = [block.model_dump(mode="json", exclude_none=True) for block in message.content]
    texts = [block.text for block in message.content if block.type == "text"]
    calls = [
        ToolCall(id=block.id, name=block.name, arguments=dict(block.input or {}))
        for block in message.content
        if block.type == "tool_use"
    ]
    usage = message.usage
    return LLMResponse(
        text="".join(texts),
        tool_calls=calls,
        stop_reason=STOP_REASONS.get(message.stop_reason or "", "other"),
        raw_stop_reason=message.stop_reason,
        usage=Usage(
            input_tokens=usage.input_tokens or 0,
            output_tokens=usage.output_tokens or 0,
            cache_read_tokens=usage.cache_read_input_tokens or 0,
            cache_write_tokens=usage.cache_creation_input_tokens or 0,
        ),
        model=message.model,
        request_id=getattr(message, "_request_id", None),
        provider_raw=raw,
        latency_ms=latency_ms,
    )


class AnthropicProvider:
    name = "anthropic"

    def __init__(self, client: Any | None = None, *, api_key: str | None = None) -> None:
        self.client = client or anthropic.AsyncAnthropic(
            api_key=api_key, max_retries=4, timeout=300.0
        )

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
    ) -> LLMResponse:
        if temperature is not None:
            raise ValueError("API version 2026-10-21 rejects temperature; leave it unset.")
        params: dict[str, Any] = {
            "model": model,
            "system": system,
            "messages": to_anthropic_messages(messages),
            "max_tokens": max_tokens,
        }
        if tools:
            params["tools"] = [anthropic_tool(t) for t in tools]
        if effort:
            params["output_config"] = {"effort": effort}
        started = time.perf_counter()
        try:
            message = await self.client.messages.create(**params)
        except anthropic.APIStatusError as exc:
            raise ProviderError(
                self.name,
                type(exc).__name__,
                status=exc.status_code,
                retryable=exc.status_code in {408, 409, 429} or exc.status_code >= 500,
                request_id=getattr(exc, "request_id", None),
            ) from exc
        except anthropic.APIConnectionError as exc:
            raise ProviderError(self.name, type(exc).__name__, status=None, retryable=True) from exc
        return normalize_message(message, int((time.perf_counter() - started) * 1000))

"""OpenAI-compatible Chat Completions adapter (e.g. Together AI) with function calling."""

import json
import time
from typing import Any

import openai

from filinglens.llm.base import (
    LLMResponse,
    Msg,
    ProviderError,
    StopReason,
    ToolCall,
    ToolSpec,
    Usage,
    parse_arguments,
)
from filinglens.llm.tools import openai_tool

STOP_REASONS: dict[str, StopReason] = {
    "stop": "end_turn",
    "tool_calls": "tool_use",
    "length": "max_tokens",
    "content_filter": "refusal",
}


def to_openai_messages(system: str, messages: list[Msg]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = [{"role": "system", "content": system}]
    for msg in messages:
        if msg.role == "user":
            out.append({"role": "user", "content": msg.text or ""})
        elif msg.role == "assistant":
            if not msg.provider_raw:
                raise ValueError("Assistant turns must carry the provider's exact message.")
            out.append(msg.provider_raw[0])
        else:
            out.extend(
                {"role": "tool", "tool_call_id": part.tool_call_id, "content": part.content}
                for part in msg.tool_results
            )
    return out


def normalize_completion(completion: Any, latency_ms: int) -> LLMResponse:
    choice = completion.choices[0]
    message = choice.message
    calls = []
    raw_calls = []
    for call in message.tool_calls or []:
        arguments, error = parse_arguments(call.function.arguments)
        calls.append(
            ToolCall(
                id=call.id, name=call.function.name, arguments=arguments, arguments_error=error
            )
        )
        raw_calls.append(
            {
                "id": call.id,
                "type": "function",
                "function": {"name": call.function.name, "arguments": call.function.arguments},
            }
        )
    raw: dict[str, Any] = {"role": "assistant", "content": message.content}
    if raw_calls:
        raw["tool_calls"] = raw_calls
    usage = completion.usage
    details = getattr(usage, "prompt_tokens_details", None) if usage else None
    cached = (getattr(details, "cached_tokens", None) or 0) if details else 0
    prompt = (usage.prompt_tokens or 0) if usage else 0
    return LLMResponse(
        text=message.content or "",
        tool_calls=calls,
        stop_reason=STOP_REASONS.get(choice.finish_reason or "", "other"),
        raw_stop_reason=choice.finish_reason,
        usage=Usage(
            input_tokens=prompt - cached,
            output_tokens=(usage.completion_tokens or 0) if usage else 0,
            cache_read_tokens=cached,
        ),
        model=completion.model,
        request_id=getattr(completion, "_request_id", None),
        provider_raw=[json.loads(json.dumps(raw))],
        latency_ms=latency_ms,
    )


class OpenAICompatProvider:
    name = "openai_compat"

    def __init__(
        self, client: Any | None = None, *, api_key: str | None = None, base_url: str | None = None
    ) -> None:
        self.client = client or openai.AsyncOpenAI(
            api_key=api_key, base_url=base_url, max_retries=4, timeout=300.0
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
        effort: str | None = None,  # Anthropic-only; ignored here.
    ) -> LLMResponse:
        params: dict[str, Any] = {
            "model": model,
            "messages": to_openai_messages(system, messages),
            "max_tokens": max_tokens,
        }
        if tools:
            params["tools"] = [openai_tool(t) for t in tools]
        if temperature is not None:
            params["temperature"] = temperature
        started = time.perf_counter()
        try:
            completion = await self.client.chat.completions.create(**params)
        except openai.APIStatusError as exc:
            raise ProviderError(
                self.name,
                type(exc).__name__,
                status=exc.status_code,
                retryable=exc.status_code in {408, 409, 429} or exc.status_code >= 500,
                request_id=getattr(exc, "request_id", None),
            ) from exc
        except openai.APIConnectionError as exc:
            raise ProviderError(self.name, type(exc).__name__, status=None, retryable=True) from exc
        return normalize_completion(completion, int((time.perf_counter() - started) * 1000))

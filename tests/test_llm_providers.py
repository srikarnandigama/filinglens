"""Provider adapters: schema conversion, message building and normalization, without HTTP."""

import anthropic
import httpx
import httpx2
import openai
import pytest
from anthropic.types import Message
from openai.types.chat import ChatCompletion

from filinglens.llm.anthropic_provider import (
    AnthropicProvider,
    normalize_message,
    to_anthropic_messages,
)
from filinglens.llm.base import Msg, ProviderError, ToolCall, ToolResultPart, ToolSpec
from filinglens.llm.openai_compat_provider import (
    OpenAICompatProvider,
    normalize_completion,
    to_openai_messages,
)
from filinglens.llm.tools import anthropic_tool, inline_refs, openai_tool
from mcp_servers.models import GetFinancialMetricInput, SearchFilingsInput

SPEC = ToolSpec(name="get_passage", description="Fetch.", input_schema={"type": "object"})


def anthropic_message(content, stop="tool_use", **usage):
    return Message.model_validate(
        {
            "id": "msg_1",
            "type": "message",
            "role": "assistant",
            "model": "fake-model",
            "content": content,
            "stop_reason": stop,
            "stop_sequence": None,
            "usage": {"input_tokens": 10, "output_tokens": 5, **usage},
        }
    )


def test_inline_refs_removes_defs_and_titles_from_real_mcp_schemas():
    for model in (GetFinancialMetricInput, SearchFilingsInput):
        schema = inline_refs(model.model_json_schema())
        text = str(schema)
        assert "$ref" not in text and "$defs" not in text and "'title'" not in text
    periods = inline_refs(GetFinancialMetricInput.model_json_schema())["properties"]["periods"]
    assert set(periods["items"]["properties"]) == {"fiscal_year", "fiscal_period"}
    assert anthropic_tool(SPEC) == {
        "name": "get_passage",
        "description": "Fetch.",
        "input_schema": {"type": "object"},
    }
    assert openai_tool(SPEC)["function"]["parameters"] == {"type": "object"}


def test_anthropic_messages_replay_raw_blocks_and_group_tool_results():
    raw = [
        {"type": "thinking", "thinking": "", "signature": "sig"},
        {"type": "tool_use", "id": "t1", "name": "a", "input": {}},
        {"type": "tool_use", "id": "t2", "name": "b", "input": {}},
    ]
    msgs = [
        Msg(role="user", text="q"),
        Msg(role="assistant", provider_raw=raw),
        Msg(
            role="tool_results",
            tool_results=[
                ToolResultPart(tool_call_id="t1", content="x"),
                ToolResultPart(tool_call_id="t2", content="y", is_error=True),
            ],
        ),
    ]
    out = to_anthropic_messages(msgs)
    assert out[1] == {"role": "assistant", "content": raw}
    assert [b["tool_use_id"] for b in out[2]["content"]] == ["t1", "t2"]
    assert out[2]["content"][1]["is_error"] is True
    with pytest.raises(ValueError):
        to_anthropic_messages([Msg(role="assistant", text="no raw")])


def test_anthropic_normalization_keeps_thinking_and_cache_usage():
    message = anthropic_message(
        [
            {"type": "thinking", "thinking": "", "signature": "sig"},
            {"type": "text", "text": "Calling."},
            {"type": "tool_use", "id": "t1", "name": "margin", "input": {"numerator": "1"}},
        ],
        cache_read_input_tokens=7,
        cache_creation_input_tokens=3,
    )
    resp = normalize_message(message, 12)
    assert resp.stop_reason == "tool_use" and resp.text == "Calling."
    assert resp.tool_calls[0].arguments == {"numerator": "1"}
    assert resp.provider_raw[0]["type"] == "thinking" and resp.provider_raw[0]["signature"] == "sig"
    assert (resp.usage.cache_read_tokens, resp.usage.cache_write_tokens) == (7, 3)
    for raw_stop, mapped in [
        ("end_turn", "end_turn"),
        ("stop_sequence", "end_turn"),
        ("max_tokens", "max_tokens"),
        ("refusal", "refusal"),
        ("pause_turn", "other"),
    ]:
        msg = anthropic_message([{"type": "text", "text": "x"}], stop=raw_stop)
        assert normalize_message(msg, 0).stop_reason == mapped


class FakeAnthropicClient:
    def __init__(self, result=None, error=None):
        self.params = None
        self.result, self.error = result, error
        self.messages = self

    async def create(self, **params):
        self.params = params
        if self.error:
            raise self.error
        return self.result


async def test_anthropic_request_has_no_sampling_parameters_and_wraps_errors():
    client = FakeAnthropicClient(anthropic_message([{"type": "text", "text": "{}"}], "end_turn"))
    provider = AnthropicProvider(client)
    await provider.complete(
        system="s", messages=[Msg(role="user", text="q")], tools=[SPEC], model="m", max_tokens=9
    )
    assert set(client.params) == {"model", "system", "messages", "max_tokens", "tools"}
    await provider.complete(
        system="s",
        messages=[Msg(role="user", text="q")],
        tools=None,
        model="m",
        max_tokens=9,
        effort="low",
    )
    assert client.params["output_config"] == {"effort": "low"} and "tools" not in client.params
    with pytest.raises(ValueError, match="temperature"):
        await provider.complete(
            system="s", messages=[], tools=None, model="m", max_tokens=9, temperature=0.0
        )
    request = httpx2.Request("POST", "https://api.example.invalid/v1/messages")
    limited = anthropic.RateLimitError(
        "rate limited", response=httpx2.Response(429, request=request), body=None
    )
    with pytest.raises(ProviderError) as info:
        await AnthropicProvider(FakeAnthropicClient(error=limited)).complete(
            system="s", messages=[], tools=None, model="m", max_tokens=9
        )
    assert info.value.status == 429 and info.value.retryable
    bad = anthropic.BadRequestError(
        "bad", response=httpx2.Response(400, request=request), body=None
    )
    with pytest.raises(ProviderError) as info:
        await AnthropicProvider(FakeAnthropicClient(error=bad)).complete(
            system="s", messages=[], tools=None, model="m", max_tokens=9
        )
    assert info.value.status == 400 and not info.value.retryable


def completion(message, finish="tool_calls", usage=None):
    return ChatCompletion.model_validate(
        {
            "id": "c1",
            "object": "chat.completion",
            "created": 0,
            "model": "open-model",
            "choices": [{"index": 0, "finish_reason": finish, "message": message}],
            "usage": usage or {"prompt_tokens": 20, "completion_tokens": 4, "total_tokens": 24},
        }
    )


def test_openai_normalization_and_malformed_arguments():
    resp = normalize_completion(
        completion(
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "a",
                        "type": "function",
                        "function": {"name": "margin", "arguments": '{"numerator": "1"}'},
                    },
                    {
                        "id": "b",
                        "type": "function",
                        "function": {"name": "margin", "arguments": "{oops"},
                    },
                ],
            },
            usage={
                "prompt_tokens": 20,
                "completion_tokens": 4,
                "total_tokens": 24,
                "prompt_tokens_details": {"cached_tokens": 5},
            },
        ),
        3,
    )
    assert resp.stop_reason == "tool_use"
    assert resp.tool_calls[0].arguments == {"numerator": "1"}
    assert resp.tool_calls[1].arguments_error and resp.tool_calls[1].arguments == {}
    assert (resp.usage.input_tokens, resp.usage.cache_read_tokens) == (15, 5)
    assert resp.provider_raw[0]["tool_calls"][1]["function"]["arguments"] == "{oops"
    for finish, mapped in [
        ("stop", "end_turn"),
        ("length", "max_tokens"),
        ("content_filter", "refusal"),
    ]:
        msg = {"role": "assistant", "content": "x"}
        assert normalize_completion(completion(msg, finish), 0).stop_reason == mapped


def test_openai_messages_use_system_and_tool_roles():
    raw = {"role": "assistant", "content": None, "tool_calls": [{"id": "a"}]}
    out = to_openai_messages(
        "sys",
        [
            Msg(role="user", text="q"),
            Msg(role="assistant", provider_raw=[raw]),
            Msg(role="tool_results", tool_results=[ToolResultPart(tool_call_id="a", content="r")]),
        ],
    )
    assert out[0] == {"role": "system", "content": "sys"}
    assert out[2] == raw
    assert out[3] == {"role": "tool", "tool_call_id": "a", "content": "r"}


class FakeOpenAIClient:
    def __init__(self, result=None, error=None):
        self.params = None
        self.result, self.error = result, error
        self.chat = self
        self.completions = self

    async def create(self, **params):
        self.params = params
        if self.error:
            raise self.error
        return self.result


async def test_openai_compat_temperature_only_when_set_and_errors_wrapped():
    client = FakeOpenAIClient(completion({"role": "assistant", "content": "{}"}, "stop"))
    provider = OpenAICompatProvider(client)
    await provider.complete(
        system="s", messages=[], tools=[SPEC], model="m", max_tokens=5, effort="low"
    )
    assert "temperature" not in client.params and client.params["tools"][0]["type"] == "function"
    await provider.complete(
        system="s", messages=[], tools=None, model="m", max_tokens=5, temperature=0.0
    )
    assert client.params["temperature"] == 0.0
    request = httpx.Request("POST", "https://compat.example.invalid/v1/chat/completions")
    error = openai.InternalServerError(
        "down", response=httpx.Response(503, request=request), body=None
    )
    with pytest.raises(ProviderError) as info:
        await OpenAICompatProvider(FakeOpenAIClient(error=error)).complete(
            system="s", messages=[], tools=None, model="m", max_tokens=5
        )
    assert info.value.status == 503 and info.value.retryable


def test_tool_call_model_defaults():
    assert ToolCall(id="x", name="y").arguments == {}

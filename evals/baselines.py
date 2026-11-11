"""Single-prompt baselines B0 (closed-book), B1 (web search) and B2 (stuffed statements).

One request per question on the official SDK (API version 2026-10-21): no sampling parameters,
model-default thinking and effort, max_tokens 16,000 (D087). B1/B2 may run through the Message
Batches API (D088/D089). Nothing here runs at import time; tests pass fake clients.
"""

import asyncio
import time
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from evals.answers import parse_answer, system_prompt

MAX_TOKENS = 16_000
MAX_CONTINUATIONS = 3  # pause_turn continuations for server tools (D088)
WEB_SEARCH_TOOL = {"type": "web_search_20260209", "name": "web_search"}
HANDWRITTEN_PROMPT = (
    "You answer questions about US public companies using what they reported in their SEC "
    "10-K and 10-Q filings. Answer in a short paragraph. If you are unsure, say so."
)


@dataclass
class BaselineSpec:
    kind: str  # b0 | b1 | b2
    model: str
    max_uses: int = 5
    batch: bool = False

    def settings(self) -> dict[str, Any]:
        """Everything that changes a baseline's output; part of the cache key (D090)."""
        out = {
            "kind": self.kind,
            "model": self.model,
            "max_tokens": MAX_TOKENS,
            "prompt": system_prompt(self.kind),
            "handwritten_prompt": HANDWRITTEN_PROMPT,
        }
        if self.kind == "b1":
            out["tool"] = {**WEB_SEARCH_TOOL, "max_uses": self.max_uses}
            out["max_continuations"] = MAX_CONTINUATIONS
        return out


@dataclass
class BaselineResult:
    text: str
    stop_reason: str | None
    usage: dict[str, int] = field(default_factory=dict)
    latency_ms: int | None = None
    request_ids: list[str] = field(default_factory=list)


def build_params(
    spec: BaselineSpec,
    question: dict[str, Any],
    context: str | None = None,
    handwritten: bool = False,
) -> dict[str, Any]:
    """messages.create parameters; B2 places the statements before the question."""
    text = question["question"]
    if spec.kind == "b2":
        if context is None:
            raise ValueError("B2 needs its stuffed context")
        text = f"Filing excerpts:\n<filings>\n{context}\n</filings>\n\nQuestion: {text}"
    params: dict[str, Any] = {
        "model": spec.model,
        "max_tokens": MAX_TOKENS,
        "system": HANDWRITTEN_PROMPT if handwritten else system_prompt(spec.kind),
        "messages": [{"role": "user", "content": text}],
    }
    if spec.kind == "b1":
        params["tools"] = [{**WEB_SEARCH_TOOL, "max_uses": spec.max_uses}]
    return params


def _usage(message: Any) -> dict[str, int]:
    u = message.usage
    server = getattr(u, "server_tool_use", None)
    return {
        "input_tokens": u.input_tokens or 0,
        "output_tokens": u.output_tokens or 0,
        "cache_read_tokens": u.cache_read_input_tokens or 0,
        "cache_write_tokens": u.cache_creation_input_tokens or 0,
        "web_searches": (server.web_search_requests or 0) if server else 0,
    }


def _add(total: dict[str, int], part: dict[str, int]) -> dict[str, int]:
    return {k: total.get(k, 0) + part.get(k, 0) for k in set(total) | set(part)}


def blocks_of(message: Any) -> list[dict[str, Any]]:
    """The assistant's exact content blocks as JSON, for pause_turn continuations."""
    return [b.model_dump(mode="json", exclude_none=True) for b in message.content]


def text_of(message: Any) -> str:
    return "".join(b.text for b in message.content if getattr(b, "type", None) == "text")


async def call_realtime(client: Any, params: dict[str, Any]) -> BaselineResult:
    """One request, continued on pause_turn (server tools) up to MAX_CONTINUATIONS times."""
    started = time.perf_counter()
    messages = list(params["messages"])
    usage: dict[str, int] = {}
    texts, ids = [], []
    for _ in range(MAX_CONTINUATIONS + 1):
        message = await client.messages.create(**{**params, "messages": messages})
        usage = _add(usage, _usage(message))
        texts.append(text_of(message))
        ids.append(getattr(message, "_request_id", None) or getattr(message, "id", ""))
        if message.stop_reason != "pause_turn":
            break
        messages = [*messages, {"role": "assistant", "content": blocks_of(message)}]
    return BaselineResult(
        text="".join(texts),
        stop_reason=message.stop_reason,
        usage=usage,
        latency_ms=int((time.perf_counter() - started) * 1000),
        request_ids=ids,
    )


async def run_batch(
    client: Any,
    requests: dict[str, dict[str, Any]],
    poll_seconds: float = 30.0,
    sleep=asyncio.sleep,
) -> dict[str, BaselineResult]:
    """Submit params by custom_id, wait for the batch, collect results by custom_id.

    pause_turn results are continued in follow-up batches (up to MAX_CONTINUATIONS rounds).
    Latency is not measured: batch latency is not comparable (D088/D089).
    """
    pending = {cid: (params, list(params["messages"])) for cid, params in requests.items()}
    out: dict[str, BaselineResult] = {}
    acc: dict[str, BaselineResult] = {cid: BaselineResult("", None) for cid in requests}
    for _ in range(MAX_CONTINUATIONS + 1):
        if not pending:
            break
        batch = await client.messages.batches.create(
            requests=[
                {"custom_id": cid, "params": {**p, "messages": msgs}}
                for cid, (p, msgs) in pending.items()
            ]
        )
        while (await client.messages.batches.retrieve(batch.id)).processing_status != "ended":
            await sleep(poll_seconds)
        follow: dict[str, tuple[dict[str, Any], list]] = {}
        async for item in await client.messages.batches.results(batch.id):
            cid = item.custom_id
            result = acc[cid]
            if item.result.type != "succeeded":
                out[cid] = BaselineResult(result.text, f"batch_{item.result.type}", result.usage)
                continue
            message = item.result.message
            result.text += text_of(message)
            result.usage = _add(result.usage, _usage(message))
            result.stop_reason = message.stop_reason
            if message.stop_reason == "pause_turn":
                params, msgs = pending[cid]
                follow[cid] = (
                    params,
                    [*msgs, {"role": "assistant", "content": blocks_of(message)}],
                )
            else:
                out[cid] = result
        pending = follow
    for cid, (_p, _m) in pending.items():  # still paused after the last round
        out[cid] = acc[cid]
    return out


def cost_usd(
    usage: dict[str, int],
    model_price: Any,
    web_search_per_1000: Decimal | None,
    batch_multiplier: Decimal | None,
) -> Decimal:
    """Token cost from pricing.toml, x the batch multiplier when batched, plus search fees."""
    from filinglens.llm.base import Usage

    tokens = model_price.cost(
        Usage(
            input_tokens=usage.get("input_tokens", 0),
            output_tokens=usage.get("output_tokens", 0),
            cache_read_tokens=usage.get("cache_read_tokens", 0),
            cache_write_tokens=usage.get("cache_write_tokens", 0),
        )
    )
    if batch_multiplier is not None:
        tokens *= batch_multiplier
    searches = usage.get("web_searches", 0)
    if searches:
        if web_search_per_1000 is None:
            raise ValueError("pricing.toml needs [tools.web_search] usd_per_1000 for B1")
        tokens += Decimal(searches) * web_search_per_1000 / 1000
    return tokens


def prediction_of(result: BaselineResult, handwritten: bool = False) -> dict[str, Any]:
    if handwritten:
        return {"text": result.text, "parse_ok": bool(result.text.strip())}
    return parse_answer(result.text).to_json()

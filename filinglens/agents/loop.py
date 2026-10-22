"""The hand-written agent loop (SPEC §10.3, D052, D063)."""

import json
import re
from collections.abc import Callable

from pydantic import BaseModel, ValidationError

from filinglens.agents.budget import BudgetExceeded
from filinglens.agents.context import RunContext, role_of
from filinglens.agents.toolbox import Toolbox
from filinglens.llm.base import LLMRequest, Msg, ToolResultPart

FENCE = re.compile(r"```(?:json)?\s*(\{.*\})\s*```", re.DOTALL)
MAX_FEEDBACK_CHARS = 4000


class AgentOutputError(RuntimeError):
    """The final output stayed invalid after the single corrective retry."""


class AgentRefused(RuntimeError):
    pass


class SemanticError(ValueError):
    """A schema-valid output that violates a role rule (e.g. an unknown period)."""


def extract_json(text: str) -> dict:
    stripped = text.strip()
    match = FENCE.search(stripped)
    if match:
        stripped = match.group(1)
    elif not stripped.startswith("{"):
        start, end = stripped.find("{"), stripped.rfind("}")
        if start == -1 or end <= start:
            raise ValueError("No JSON object found in the final reply.")
        stripped = stripped[start : end + 1]
    value = json.loads(stripped)
    if not isinstance(value, dict):
        raise ValueError("The final reply must be a JSON object.")
    return value


async def run_agent[T: BaseModel](
    ctx: RunContext,
    *,
    instance: str,
    system: str,
    task: str,
    model: str,
    provider: str,
    output_model: type[T],
    toolbox: Toolbox | None = None,
    validator: Callable[[T], None] | None = None,
    max_steps: int = 8,
    max_tokens: int = 16_000,
    effort: str | None = None,
    temperature: float | None = None,
) -> T:
    role = role_of(instance)
    await ctx.recorder.emit(role, "agent_start", {"instance": instance, "model": model})
    messages = [Msg(role="user", text=task)]
    sent = 0
    retried = False
    for step in range(max_steps):
        request = LLMRequest(
            provider=provider,
            model=model,
            system=system,
            messages=list(messages),
            tools=toolbox.specs if toolbox else [],
            max_tokens=max_tokens,
            effort=effort,
            temperature=temperature,
        )
        new_messages, sent = messages[sent:], len(messages)
        response = await ctx.gateway.complete(instance, step, request, new_messages)
        if response.stop_reason == "refusal":
            raise AgentRefused(f"{instance} refused ({response.raw_stop_reason}).")
        messages.append(
            Msg(
                role="assistant",
                text=response.text,
                tool_calls=response.tool_calls,
                provider_raw=response.provider_raw,
            )
        )
        if response.tool_calls:
            if toolbox is None:
                results = [
                    ToolResultPart(
                        tool_call_id=c.id,
                        content='{"error":{"code":"TOOL_NOT_ALLOWED","message":"No tools."}}',
                        is_error=True,
                    )
                    for c in response.tool_calls
                ]
            else:
                results = await toolbox.call_many(response.tool_calls)
            messages.append(Msg(role="tool_results", tool_results=results))
            continue
        try:
            if response.stop_reason == "max_tokens":
                raise ValueError("The reply was cut off at max_tokens; be more concise.")
            output = output_model.model_validate(extract_json(response.text))
            if validator:
                validator(output)
        except (ValueError, ValidationError) as exc:  # JSONDecodeError and SemanticError too
            feedback = str(exc)[:MAX_FEEDBACK_CHARS]
            if retried:
                await ctx.recorder.emit(
                    role, "agent_end", {"instance": instance, "status": "invalid_output"}
                )
                raise AgentOutputError(f"{instance}: invalid final output: {feedback}") from exc
            retried = True
            messages.append(
                Msg(
                    role="user",
                    text=(
                        "Your final reply was not valid. Errors:\n"
                        f"{feedback}\n"
                        "Fix these problems. You may call tools again if needed; finish with "
                        "only the corrected JSON object."
                    ),
                )
            )
            continue
        await ctx.recorder.emit(
            role, "agent_end", {"instance": instance, "status": "ok", "steps": step + 1}
        )
        return output
    await ctx.recorder.emit(role, "agent_end", {"instance": instance, "status": "max_steps"})
    raise BudgetExceeded("steps", f"{instance} reached max_steps={max_steps}.")

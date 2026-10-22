"""Deterministic conversion of MCP tool schemas into provider tool formats."""

import copy
from typing import Any

from filinglens.llm.base import ToolSpec


def inline_refs(schema: dict[str, Any]) -> dict[str, Any]:
    """Inline local $defs references and drop titles; some compatible endpoints reject $ref."""
    defs = schema.get("$defs", {})

    def resolve(node: Any, seen: tuple[str, ...]) -> Any:
        if isinstance(node, dict):
            ref = node.get("$ref")
            if isinstance(ref, str) and ref.startswith("#/$defs/"):
                name = ref.removeprefix("#/$defs/")
                if name in seen:
                    raise ValueError(f"Recursive schema reference: {name}")
                merged = {
                    **copy.deepcopy(defs[name]),
                    **{k: v for k, v in node.items() if k != "$ref"},
                }
                return resolve(merged, (*seen, name))
            return {
                key: resolve(value, seen)
                for key, value in node.items()
                if key not in {"$defs", "title"}
            }
        if isinstance(node, list):
            return [resolve(item, seen) for item in node]
        return node

    return resolve(schema, ())


def spec_from_mcp(tool: Any) -> ToolSpec:
    return ToolSpec(
        name=tool.name,
        description=(tool.description or "").strip(),
        input_schema=inline_refs(tool.input_schema),
    )


def anthropic_tool(spec: ToolSpec) -> dict[str, Any]:
    return {"name": spec.name, "description": spec.description, "input_schema": spec.input_schema}


def openai_tool(spec: ToolSpec) -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": spec.name,
            "description": spec.description,
            "parameters": spec.input_schema,
        },
    }

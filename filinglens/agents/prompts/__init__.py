"""System prompts, one Markdown file per role; output schemas are appended at load time."""

import hashlib
import json
from pathlib import Path

from pydantic import BaseModel

PROMPT_DIR = Path(__file__).parent


def load_prompt(name: str, output_model: type[BaseModel]) -> tuple[str, str]:
    """Return the full system prompt and its SHA-256 (covers the appended schema)."""
    text = (PROMPT_DIR / f"{name}.md").read_text(encoding="utf-8").strip()
    schema = json.dumps(output_model.model_json_schema(), indent=1, sort_keys=True)
    system = (
        f"{text}\n\n## Output JSON schema ({output_model.__name__})\n\n```json\n{schema}\n```\n"
    )
    return system, hashlib.sha256(system.encode()).hexdigest()

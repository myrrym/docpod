"""Prompt loading. Prompts are plain .md files the user can edit.

Resolution order: config [prompts] dir -> the repo's prompts/ (source
checkouts) -> the copies bundled into the installed package.

Templating is literal string replacement of {placeholder} tokens — NOT
str.format — because the prompt files contain JSON examples full of braces.
"""

from __future__ import annotations

from importlib import resources
from pathlib import Path

from ..config import Config
from ..errors import ConfigError

_REPO_PROMPTS = Path(__file__).resolve().parents[3] / "prompts"


def load_prompt(name: str, config: Config) -> str:
    filename = f"{name}.md"
    for directory in (config.prompts_dir, _REPO_PROMPTS):
        if directory is not None:
            candidate = Path(directory) / filename
            if candidate.is_file():
                return candidate.read_text(encoding="utf-8")

    packaged = resources.files("docpod") / "prompts" / filename
    if packaged.is_file():
        return packaged.read_text(encoding="utf-8")

    raise ConfigError(
        f"prompt '{filename}' not found (looked in [prompts] dir, {_REPO_PROMPTS}, and the installed package)"
    )


def render(template: str, **values: str) -> str:
    for key, value in values.items():
        template = template.replace("{" + key + "}", value)
    return template

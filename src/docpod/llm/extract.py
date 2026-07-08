"""Stage 1: document text -> structured extraction (extracted.json).

Two-tier: documents that fit the context window go through in a single call.
Larger ones are split on structure (headings / page breaks / paragraphs),
extracted per chunk, then merged in one final pass. No embeddings, no RAG —
extraction is one-shot summarization, not retrieval.
"""

from __future__ import annotations

import json
import re

from ..config import Config
from ..errors import LLMError
from .client import LLMClient
from .prompts import load_prompt, render

# The universal rough estimate; only used to pick a tier, so precision is not needed.
_CHARS_PER_TOKEN = 4


def estimate_tokens(text: str) -> int:
    return len(text) // _CHARS_PER_TOKEN


def run_extract(document: str, config: Config, llm: LLMClient) -> dict:
    template = load_prompt("extract", config)

    if estimate_tokens(document) <= config.single_call_max_tokens:
        return _extract_once(template, document, llm)

    chunks = chunk_text(document, config.chunk_target_tokens)
    partials = [_extract_once(template, chunk, llm) for chunk in chunks]

    merge_template = load_prompt("merge", config)
    prompt = render(merge_template, extractions=json.dumps(partials, indent=2))
    return parse_json_response(llm.complete(prompt, max_tokens=16384))


def _extract_once(template: str, document: str, llm: LLMClient) -> dict:
    prompt = render(template, document=document)
    return parse_json_response(llm.complete(prompt, max_tokens=16384))


def chunk_text(text: str, target_tokens: int) -> list[str]:
    """Split on structure — markdown headings, page breaks (\\f), then blank
    lines — and greedily pack blocks up to the target size. A single block
    larger than the target is hard-split rather than dropped."""
    target_chars = target_tokens * _CHARS_PER_TOKEN
    blocks = re.split(r"\f|\n\s*\n|\n(?=#{1,6}\s)", text)

    chunks: list[str] = []
    current: list[str] = []
    current_len = 0
    for block in blocks:
        if not block.strip():
            continue
        while len(block) > target_chars:
            head, block = block[:target_chars], block[target_chars:]
            if current:
                chunks.append("\n\n".join(current))
                current, current_len = [], 0
            chunks.append(head)
        if current_len + len(block) > target_chars and current:
            chunks.append("\n\n".join(current))
            current, current_len = [], 0
        current.append(block)
        current_len += len(block) + 2
    if current:
        chunks.append("\n\n".join(current))
    return chunks


def parse_json_response(text: str) -> dict:
    """Models wrap JSON in prose or code fences; dig the object out."""
    candidate = text.strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)```", candidate, re.DOTALL)
    if fenced:
        candidate = fenced.group(1).strip()
    if not candidate.startswith("{"):
        start, end = candidate.find("{"), candidate.rfind("}")
        if start != -1 and end > start:
            candidate = candidate[start : end + 1]
    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError as exc:
        raise LLMError(
            f"the model did not return valid JSON for the extract stage ({exc}). "
            f"Response began: {text[:200]!r}"
        ) from exc
    if not isinstance(parsed, dict):
        raise LLMError("the extract stage returned JSON, but not an object")
    return parsed

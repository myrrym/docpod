"""Stage 2: extracted.json -> spoken script (script.md), plus the script
format itself: speaker-tagged lines that the TTS stage consumes.

The format is `[SPEAKER]: text`. v1 configs define one narrator, but nothing
here assumes a speaker count — parse_script returns whatever tags it finds.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

from ..config import Config
from ..errors import ConfigError
from .client import LLMClient
from .prompts import load_prompt, render

# Spoken-word pace used to turn "10min" into a word budget for the prompt.
_WORDS_PER_MINUTE = 150

_TAG_RE = re.compile(r"^\s*\[([^\]\n]+)\]\s*:\s*(.*)$")
_LENGTH_RE = re.compile(r"^\s*(\d+)\s*(?:m|min|mins|minutes)?\s*$", re.IGNORECASE)


@dataclass
class Segment:
    speaker: str
    text: str


def word_budget(length: str) -> int:
    match = _LENGTH_RE.match(length)
    if not match:
        raise ConfigError(f"can't parse length '{length}' — use minutes, e.g. '10min'")
    return int(match.group(1)) * _WORDS_PER_MINUTE


def run_script(extracted: dict, config: Config, llm: LLMClient) -> str:
    budget = word_budget(config.length)
    prompt = render(
        load_prompt("script", config),
        word_budget=str(budget),
        length=config.length,
        tone=config.tone,
        speakers=", ".join(name.upper() for name in config.speakers),
        extracted_json=json.dumps(extracted, indent=2),
    )
    # Words -> tokens is ~1.4x; leave generous headroom so scripts never truncate.
    max_tokens = min(int(budget * 2) + 2000, 32_000)
    return llm.complete(prompt, max_tokens=max_tokens)


def parse_script(text: str, default_speaker: str) -> list[Segment]:
    """Turn script.md into ordered segments. Untagged lines continue the
    current segment; leading untagged prose gets the default speaker so a
    hand-written script without tags still works."""
    segments: list[Segment] = []
    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        if not line.strip() or line.lstrip().startswith(("```", "#")):
            continue
        match = _TAG_RE.match(line)
        if match:
            segments.append(Segment(speaker=match.group(1).strip().lower(), text=match.group(2).strip()))
        elif segments:
            segments[-1].text = (segments[-1].text + " " + line.strip()).strip()
        else:
            segments.append(Segment(speaker=default_speaker, text=line.strip()))
    return [s for s in segments if s.text]


def split_segment(segment: Segment, max_chars: int = 3500) -> list[Segment]:
    """TTS APIs cap input size (OpenAI: 4096 chars); split oversized segments
    at sentence boundaries."""
    if len(segment.text) <= max_chars:
        return [segment]
    sentences = re.split(r"(?<=[.!?])\s+", segment.text)
    pieces: list[Segment] = []
    current = ""
    for sentence in sentences:
        while len(sentence) > max_chars:  # pathological run-on: hard split
            head, sentence = sentence[:max_chars], sentence[max_chars:]
            if current:
                pieces.append(Segment(segment.speaker, current.strip()))
                current = ""
            pieces.append(Segment(segment.speaker, head))
        if len(current) + len(sentence) + 1 > max_chars and current:
            pieces.append(Segment(segment.speaker, current.strip()))
            current = ""
        current += " " + sentence
    if current.strip():
        pieces.append(Segment(segment.speaker, current.strip()))
    return pieces

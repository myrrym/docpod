from __future__ import annotations

import os
from pathlib import Path

from ..errors import MissingAPIKeyError
from .base import TTSError, TTSProvider


class OpenAITTS(TTSProvider):
    name = "openai"
    default_voice = "alloy"
    DEFAULT_MODEL = "gpt-4o-mini-tts"

    # OpenAI has no list-voices endpoint; this is the documented set.
    VOICES = ["alloy", "ash", "ballad", "coral", "echo", "fable", "nova", "onyx", "sage", "shimmer", "verse"]

    def __init__(self, model: str | None = None):
        if not os.environ.get("OPENAI_API_KEY"):
            raise MissingAPIKeyError("OPENAI_API_KEY", "openai (tts)")
        import openai

        self._client = openai.OpenAI()
        self._errors = openai.OpenAIError
        self.model = model or self.DEFAULT_MODEL

    def synthesize(self, text: str, voice: str, out_path: Path) -> Path:
        tmp = out_path.with_suffix(".part")
        try:
            with self._client.audio.speech.with_streaming_response.create(
                model=self.model, voice=voice, input=text, response_format="mp3"
            ) as response:
                response.stream_to_file(tmp)
        except self._errors as exc:
            tmp.unlink(missing_ok=True)
            raise TTSError(f"openai tts failed: {exc}") from exc
        tmp.replace(out_path)  # atomic: never leave a partial segment behind
        return out_path

    def available_voices(self) -> list[str]:
        return list(self.VOICES)

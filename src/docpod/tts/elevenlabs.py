from __future__ import annotations

import os
from pathlib import Path

from ..errors import MissingAPIKeyError
from .base import TTSError, TTSProvider


class ElevenLabsTTS(TTSProvider):
    name = "elevenlabs"
    default_voice = "21m00Tcm4TlvDq8ikWAM"  # "Rachel", a stock voice on every account
    DEFAULT_MODEL = "eleven_multilingual_v2"

    def __init__(self, model: str | None = None):
        if not os.environ.get("ELEVENLABS_API_KEY"):
            raise MissingAPIKeyError("ELEVENLABS_API_KEY", "elevenlabs")
        from elevenlabs.client import ElevenLabs

        self._client = ElevenLabs(api_key=os.environ["ELEVENLABS_API_KEY"])
        self.model = model or self.DEFAULT_MODEL

    def synthesize(self, text: str, voice: str, out_path: Path) -> Path:
        tmp = out_path.with_suffix(".part")
        try:
            audio = self._client.text_to_speech.convert(
                voice_id=voice, text=text, model_id=self.model, output_format="mp3_44100_128"
            )
            with open(tmp, "wb") as fh:
                for chunk in audio:
                    fh.write(chunk)
        except Exception as exc:  # the SDK raises assorted ApiError types
            tmp.unlink(missing_ok=True)
            raise TTSError(f"elevenlabs tts failed: {exc}") from exc
        tmp.replace(out_path)  # atomic: never leave a partial segment behind
        return out_path

    def available_voices(self) -> list[str]:
        try:
            listing = getattr(self._client.voices, "get_all", None) or self._client.voices.search
            voices = listing().voices
        except Exception as exc:
            raise TTSError(f"couldn't list elevenlabs voices: {exc}") from exc
        return [f"{v.voice_id}  ({v.name})" for v in voices]

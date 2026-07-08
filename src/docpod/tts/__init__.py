"""TTS providers behind the TTSProvider interface in base.py."""

from __future__ import annotations

from ..config import Config
from .base import TTSError, TTSProvider

# Known so the pipeline can fingerprint voices without instantiating a
# provider (which requires an API key the user may not need for a cached run).
DEFAULT_VOICES = {
    "openai": "alloy",
    "elevenlabs": "21m00Tcm4TlvDq8ikWAM",
}

__all__ = ["TTSProvider", "TTSError", "DEFAULT_VOICES", "make_tts"]


def make_tts(config: Config) -> TTSProvider:
    if config.tts_provider == "elevenlabs":
        from .elevenlabs import ElevenLabsTTS

        return ElevenLabsTTS(config.tts_model)
    from .openai import OpenAITTS

    return OpenAITTS(config.tts_model)

"""The TTS provider interface.

Implementations live beside this file (elevenlabs.py, openai.py) and are selected
by name via config ([tts] provider). Adding a provider means implementing this
one class in one new file — nothing in the pipeline may import a concrete
provider directly.
"""

from abc import ABC, abstractmethod
from pathlib import Path

from ..errors import DocpodError


class TTSProvider(ABC):
    """Voices one script segment at a time.

    The pipeline calls synthesize() once per script segment and handles
    ordering, retries, and stitching itself, so implementations stay small:
    text in, audio file out.
    """

    #: config name, e.g. "elevenlabs" or "openai"
    name: str
    #: voice used when a speaker has no voice configured
    default_voice: str

    @abstractmethod
    def synthesize(self, text: str, voice: str, out_path: Path) -> Path:
        """Render `text` with `voice` (a provider-specific voice id) to `out_path`
        as mp3 and return the path. Must raise TTSError on provider failure —
        never return a partial file."""

    @abstractmethod
    def available_voices(self) -> list[str]:
        """Voice ids the configured account can use (for `docpod voices`)."""


class TTSError(DocpodError):
    """A provider call failed. The pipeline keeps completed segments on disk so
    a re-run resumes from the first missing segment."""

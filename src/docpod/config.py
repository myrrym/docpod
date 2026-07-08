"""Configuration: defaults <- config.toml <- CLI flag overrides.

API keys never live here — they come from the environment (loaded from .env
via python-dotenv) and are handed only to the provider clients the user
selected. That is the local-first guarantee from the README.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from .errors import ConfigError

LLM_PROVIDERS = ("anthropic", "openai")
TTS_PROVIDERS = ("elevenlabs", "openai")


@dataclass
class Config:
    llm_provider: str = "anthropic"
    llm_model: str | None = None  # None -> provider default
    tts_provider: str = "openai"
    tts_model: str | None = None  # None -> provider default
    length: str = "10min"  # advisory: becomes a word budget in the script prompt
    tone: str = "conversational"
    # speaker name -> provider voice id (None -> provider default voice).
    # A named map, not a count: v1 ships one narrator, more speakers are additive.
    speakers: dict[str, str | None] = field(default_factory=lambda: {"narrator": None})
    single_call_max_tokens: int = 150_000
    chunk_target_tokens: int = 20_000
    prompts_dir: Path | None = None
    workdir: Path | None = None


def load_config(config_path: Path | None = None, overrides: dict[str, Any] | None = None) -> Config:
    """Build the effective Config. `overrides` holds CLI flag values keyed by
    Config field name; None values are ignored so unset flags don't clobber
    the file."""
    load_dotenv()

    if config_path is not None and not Path(config_path).is_file():
        raise ConfigError(f"config file not found: {config_path}")
    path = config_path or (Path("config.toml") if Path("config.toml").is_file() else None)

    cfg = Config()
    if path is not None:
        data = tomllib.loads(Path(path).read_text(encoding="utf-8"))
        _apply_toml(cfg, data)

    for key, value in (overrides or {}).items():
        if value is not None:
            setattr(cfg, key, value)

    if cfg.llm_provider not in LLM_PROVIDERS:
        raise ConfigError(f"unknown llm provider '{cfg.llm_provider}' (choose from {', '.join(LLM_PROVIDERS)})")
    if cfg.tts_provider not in TTS_PROVIDERS:
        raise ConfigError(f"unknown tts provider '{cfg.tts_provider}' (choose from {', '.join(TTS_PROVIDERS)})")
    if not cfg.speakers:
        raise ConfigError("at least one speaker must be defined under [speakers.<name>]")
    if cfg.prompts_dir is not None:
        cfg.prompts_dir = Path(cfg.prompts_dir)
    if cfg.workdir is not None:
        cfg.workdir = Path(cfg.workdir)
    return cfg


def _apply_toml(cfg: Config, data: dict[str, Any]) -> None:
    llm = data.get("llm", {})
    cfg.llm_provider = llm.get("provider", cfg.llm_provider)
    cfg.llm_model = llm.get("model", cfg.llm_model)

    tts = data.get("tts", {})
    cfg.tts_provider = tts.get("provider", cfg.tts_provider)
    cfg.tts_model = tts.get("model", cfg.tts_model)

    episode = data.get("episode", {})
    cfg.length = str(episode.get("length", cfg.length))
    cfg.tone = episode.get("tone", cfg.tone)

    if "speakers" in data:
        speakers = data["speakers"]
        if not isinstance(speakers, dict) or not speakers:
            raise ConfigError("[speakers] must contain at least one [speakers.<name>] table")
        cfg.speakers = {name: tbl.get("voice") for name, tbl in speakers.items()}

    chunking = data.get("chunking", {})
    cfg.single_call_max_tokens = int(chunking.get("single_call_max_tokens", cfg.single_call_max_tokens))
    cfg.chunk_target_tokens = int(chunking.get("chunk_target_tokens", cfg.chunk_target_tokens))

    prompts = data.get("prompts", {})
    if prompts.get("dir"):
        cfg.prompts_dir = Path(prompts["dir"])

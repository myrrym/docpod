"""The pipeline orchestrator: parse -> extract -> script -> tts -> stitch,
skipping any stage whose inputs haven't changed (see stages.py for the
contract). `llm` and `tts` are injectable for tests."""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path

from ..config import Config
from ..errors import DocpodError
from ..llm.client import LLMClient, make_llm
from ..llm.extract import run_extract
from ..llm.prompts import load_prompt
from ..llm.script import Segment, parse_script, run_script, split_segment
from ..parsing import parse_document
from ..tts import DEFAULT_VOICES, TTSProvider, make_tts
from .audio import stitch
from .stages import STAGES, Manifest, file_fingerprint, fingerprint

Report = Callable[[str], None]


def run_pipeline(
    source: Path,
    config: Config,
    force_from: str | None = None,
    llm: LLMClient | None = None,
    tts: TTSProvider | None = None,
    report: Report = lambda message: None,
) -> Path:
    source = Path(source).resolve()
    if not source.is_file():
        raise DocpodError(f"input file not found: {source}")
    workdir = Path(config.workdir).resolve() if config.workdir else source.with_suffix(".docpod")
    workdir.mkdir(parents=True, exist_ok=True)

    manifest = Manifest(workdir)
    if force_from is not None and force_from not in STAGES:
        raise DocpodError(f"unknown stage '{force_from}' (stages: {', '.join(STAGES)})")
    forced_from = STAGES.index(force_from) if force_from else len(STAGES)

    def needs(stage: str, input_hash: str, *artifacts: Path) -> bool:
        if STAGES.index(stage) >= forced_from:
            return True
        if not all(p.exists() for p in artifacts):
            return True
        return not manifest.is_fresh(stage, input_hash)

    # Build the LLM client only if a stage actually needs it — re-voicing a
    # cached script must not demand an LLM key.
    def get_llm() -> LLMClient:
        nonlocal llm
        if llm is None:
            llm = make_llm(config)
        return llm

    # ---------------------------------------------------------------- parse
    document_path = workdir / "document.txt"
    parse_hash = fingerprint("parse", file_fingerprint(source))
    if needs("parse", parse_hash, document_path):
        report(f"parse: reading {source.name}")
        document_path.write_text(parse_document(source), encoding="utf-8")
        manifest.record("parse", parse_hash)
    else:
        report("parse: unchanged, skipping")
    document = document_path.read_text(encoding="utf-8")

    # -------------------------------------------------------------- extract
    extracted_path = workdir / "extracted.json"
    extract_hash = fingerprint(
        "extract",
        document,
        load_prompt("extract", config),
        load_prompt("merge", config),
        config.llm_provider,
        config.llm_model or "",
        str(config.single_call_max_tokens),
        str(config.chunk_target_tokens),
    )
    if needs("extract", extract_hash, extracted_path):
        report(f"extract: structuring concepts ({config.llm_provider})")
        extracted = run_extract(document, config, get_llm())
        extracted_path.write_text(json.dumps(extracted, indent=2), encoding="utf-8")
        manifest.record("extract", extract_hash)
    else:
        report("extract: unchanged, skipping")
    extracted = json.loads(extracted_path.read_text(encoding="utf-8"))

    # --------------------------------------------------------------- script
    script_path = workdir / "script.md"
    script_hash = fingerprint(
        "script",
        json.dumps(extracted, sort_keys=True),
        load_prompt("script", config),
        config.llm_provider,
        config.llm_model or "",
        config.length,
        config.tone,
        ",".join(config.speakers),
    )
    if needs("script", script_hash, script_path):
        report(f"script: writing the episode ({config.llm_provider})")
        script_path.write_text(run_script(extracted, config, get_llm()), encoding="utf-8")
        manifest.record("script", script_hash)
    else:
        report("script: unchanged, skipping")
    script_text = script_path.read_text(encoding="utf-8")

    # ------------------------------------------------------------------ tts
    default_speaker = next(iter(config.speakers))
    segments = [
        piece
        for segment in parse_script(script_text, default_speaker=default_speaker)
        for piece in split_segment(segment)
    ]
    if not segments:
        raise DocpodError(f"{script_path} contains no speakable lines")

    voices = _voice_map(config, segments, default_speaker, report)
    segment_hashes = [
        fingerprint("segment", s.speaker, s.text, voices[s.speaker], config.tts_provider, config.tts_model or "")
        for s in segments
    ]
    audio_dir = workdir / "audio"
    segment_files = [audio_dir / f"segment_{i:03d}.mp3" for i in range(len(segments))]
    tts_hash = fingerprint("tts", *segment_hashes)
    if needs("tts", tts_hash, *segment_files):
        provider = tts if tts is not None else make_tts(config)
        _synthesize(
            segments,
            segment_hashes,
            segment_files,
            voices,
            provider,
            audio_dir,
            reuse_cached=STAGES.index("tts") < forced_from,
            report=report,
        )
        manifest.record("tts", tts_hash)
    else:
        report("tts: all segments unchanged, skipping")

    # --------------------------------------------------------------- stitch
    episode_path = workdir / "episode.mp3"
    stitch_hash = fingerprint("stitch", *(file_fingerprint(f) for f in segment_files))
    if needs("stitch", stitch_hash, episode_path):
        report(f"stitch: joining {len(segment_files)} segments")
        stitch(segment_files, episode_path)
        manifest.record("stitch", stitch_hash)
    else:
        report("stitch: unchanged, skipping")

    return episode_path


def _voice_map(config: Config, segments: list[Segment], default_speaker: str, report: Report) -> dict[str, str]:
    """Resolve every speaker appearing in the script to a voice id."""
    provider_default = DEFAULT_VOICES.get(config.tts_provider, "")
    configured = {name.lower(): voice for name, voice in config.speakers.items()}
    fallback = configured.get(default_speaker.lower()) or provider_default

    voices: dict[str, str] = {}
    for segment in segments:
        if segment.speaker in voices:
            continue
        if segment.speaker in configured:
            voices[segment.speaker] = configured[segment.speaker] or provider_default
        else:
            report(f"tts: speaker [{segment.speaker.upper()}] not in config, using {default_speaker}'s voice")
            voices[segment.speaker] = fallback
        if not voices[segment.speaker]:
            raise DocpodError(f"no voice configured for speaker '{segment.speaker}' and no provider default")
    return voices


def _synthesize(
    segments: list[Segment],
    segment_hashes: list[str],
    segment_files: list[Path],
    voices: dict[str, str],
    provider: TTSProvider,
    audio_dir: Path,
    reuse_cached: bool,
    report: Report,
) -> None:
    """Voice each segment, skipping ones already on disk from an interrupted
    or previous run (unless forced). The sidecar is rewritten after every
    segment so a crash at segment N resumes at segment N."""
    audio_dir.mkdir(parents=True, exist_ok=True)
    sidecar_path = audio_dir / "segments.json"
    previous: list[str] = []
    if reuse_cached and sidecar_path.is_file():
        previous = json.loads(sidecar_path.read_text(encoding="utf-8")).get("hashes", [])

    completed: list[str] = []
    for i, (segment, seg_hash, path) in enumerate(zip(segments, segment_hashes, segment_files)):
        if reuse_cached and i < len(previous) and previous[i] == seg_hash and path.is_file():
            report(f"tts: segment {i + 1}/{len(segments)} cached")
        else:
            report(f"tts: segment {i + 1}/{len(segments)} [{segment.speaker}] ({provider.name})")
            provider.synthesize(segment.text, voices[segment.speaker], path)
        completed.append(seg_hash)
        sidecar_path.write_text(json.dumps({"hashes": completed}, indent=2), encoding="utf-8")

    # Drop stale segments from an older, longer script so they can't be stitched.
    for stale in sorted(audio_dir.glob("segment_*.mp3")):
        if stale not in segment_files:
            stale.unlink()

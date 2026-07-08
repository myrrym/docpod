"""The resumability contract, exercised through the real pipeline with stub
LLM/TTS providers and a stubbed stitcher (no network, no ffmpeg):

- a completed run re-runs nothing;
- a hand-edited script.md re-runs tts/stitch but never the LLM stages;
- --force-from tts re-voices everything without touching the LLM stages;
- a mid-TTS crash preserves upstream artifacts and completed segments, and
  the retry synthesizes only what's missing.
"""

import json
from pathlib import Path

import pytest

import docpod.pipeline.run as run_module
from docpod.config import Config
from docpod.pipeline.run import run_pipeline
from docpod.tts.base import TTSError, TTSProvider

EXTRACTION = {
    "title": "Test Doc",
    "thesis": "Testing preserves tokens.",
    "audience": "developers",
    "concepts": [{"name": "resume", "explanation": "skip done work", "why_it_matters": "money", "supporting_detail": "hashes"}],
    "narrative_order": ["resume"],
    "open_questions": [],
}

SCRIPT = "[NARRATOR]: Welcome to the show.\n\n[NARRATOR]: Resumable pipelines never waste tokens.\n\n[NARRATOR]: Thanks for listening.\n"


class StubLLM:
    def __init__(self):
        self.calls = []

    def complete(self, prompt, max_tokens=8192):
        self.calls.append(prompt)
        if "Extraction follows" in prompt:  # the script prompt
            return SCRIPT
        return json.dumps(EXTRACTION)


class StubTTS(TTSProvider):
    name = "stub"
    default_voice = "stub-voice"

    def __init__(self, fail_on_call=None):
        self.calls = 0
        self.fail_on_call = fail_on_call

    def synthesize(self, text, voice, out_path):
        self.calls += 1
        if self.fail_on_call is not None and self.calls == self.fail_on_call:
            raise TTSError("stub provider exploded")
        Path(out_path).write_bytes(b"MP3" + text.encode("utf-8"))
        return out_path

    def available_voices(self):
        return [self.default_voice]


@pytest.fixture
def env(tmp_path, monkeypatch):
    """A source doc, a config pointing at tmp, and a stitch stub that just
    concatenates segment bytes (real stitching needs ffmpeg)."""
    stitch_calls = []

    def fake_stitch(files, out_path):
        stitch_calls.append(list(files))
        out_path.write_bytes(b"".join(Path(f).read_bytes() for f in files))
        return out_path

    monkeypatch.setattr(run_module, "stitch", fake_stitch)

    source = tmp_path / "doc.txt"
    source.write_text("A document about resumable pipelines and token thrift.", encoding="utf-8")
    config = Config(speakers={"narrator": "test-voice"}, workdir=tmp_path / "work")
    return source, config, stitch_calls


def run_once(source, config, force_from=None, fail_on_call=None):
    llm, tts = StubLLM(), StubTTS(fail_on_call=fail_on_call)
    episode = run_pipeline(source, config, force_from=force_from, llm=llm, tts=tts)
    return episode, llm, tts


def test_full_run_then_noop_rerun(env):
    source, config, stitch_calls = env
    episode, llm, tts = run_once(source, config)

    workdir = config.workdir
    assert episode.is_file()
    assert (workdir / "extracted.json").is_file()
    assert (workdir / "script.md").read_text() == SCRIPT
    assert len(llm.calls) == 2  # extract + script, nothing else
    assert tts.calls == 3  # one per [NARRATOR] line
    assert len(stitch_calls) == 1

    _, llm2, tts2 = run_once(source, config)
    assert llm2.calls == []
    assert tts2.calls == 0
    assert len(stitch_calls) == 1  # stitch skipped too


def test_edited_script_revoices_without_llm(env):
    source, config, _ = env
    run_once(source, config)

    script_path = config.workdir / "script.md"
    script_path.write_text(SCRIPT + "\n[NARRATOR]: A hand-written outro line.\n", encoding="utf-8")

    _, llm, tts = run_once(source, config)
    assert llm.calls == []  # extract and script stages untouched
    assert tts.calls == 1  # only the new line is synthesized
    assert (config.workdir / "audio" / "segment_003.mp3").is_file()


def test_force_from_tts_revoices_everything(env):
    source, config, _ = env
    run_once(source, config)

    _, llm, tts = run_once(source, config, force_from="tts")
    assert llm.calls == []
    assert tts.calls == 3  # cached segments deliberately ignored


def test_force_all_reruns_llm(env):
    source, config, _ = env
    run_once(source, config)

    _, llm, tts = run_once(source, config, force_from="parse")
    assert len(llm.calls) == 2
    assert tts.calls == 3


def test_tts_crash_preserves_upstream_and_resumes(env):
    source, config, stitch_calls = env

    with pytest.raises(TTSError):
        run_once(source, config, fail_on_call=2)

    workdir = config.workdir
    # LLM artifacts survived the crash; segment 1 of 3 completed.
    assert (workdir / "extracted.json").is_file()
    assert (workdir / "script.md").is_file()
    assert (workdir / "audio" / "segment_000.mp3").is_file()
    assert not (workdir / "audio" / "segment_001.mp3").exists()
    assert not (workdir / "episode.mp3").exists()

    _, llm, tts = run_once(source, config)
    assert llm.calls == []  # no tokens re-spent — the hard requirement
    assert tts.calls == 2  # only the two missing segments
    assert (workdir / "episode.mp3").is_file()
    assert len(stitch_calls) == 1

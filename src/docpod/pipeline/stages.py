"""Stage orchestration: the resumability contract.

Each stage declares its output artifact(s) inside the working directory:

    parse    -> document.txt
    extract  -> extracted.json
    script   -> script.md
    tts      -> audio/segment_NNN.mp3   (one per script segment)
    stitch   -> episode.mp3

A stage runs only if its artifact is missing, its recorded *input* hash in
manifest.json no longer matches, or the user passed --force / --force-from.
Hashing inputs (not outputs) is what makes hand-edits do the right thing:
editing script.md leaves the script stage's inputs untouched (skip) while
changing the tts stage's inputs (re-voice). A downstream failure never
discards upstream artifacts, so LLM tokens already spent are never re-spent.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

STAGES = ["parse", "extract", "script", "tts", "stitch"]


def fingerprint(*parts: str) -> str:
    digest = hashlib.sha256()
    for part in parts:
        digest.update(part.encode("utf-8"))
        digest.update(b"\x1f")  # separator so ("ab","c") != ("a","bc")
    return digest.hexdigest()


def file_fingerprint(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class Manifest:
    def __init__(self, workdir: Path):
        self.path = workdir / "manifest.json"
        if self.path.is_file():
            self.data = json.loads(self.path.read_text(encoding="utf-8"))
        else:
            self.data = {"stages": {}}

    def is_fresh(self, stage: str, input_hash: str) -> bool:
        return self.data["stages"].get(stage, {}).get("input_hash") == input_hash

    def record(self, stage: str, input_hash: str) -> None:
        self.data["stages"][stage] = {
            "input_hash": input_hash,
            "completed_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }
        self.path.write_text(json.dumps(self.data, indent=2), encoding="utf-8")

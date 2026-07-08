"""Stitch per-segment mp3s into one episode via ffmpeg's concat demuxer.

All segments come from the same provider with the same encoding, so stream
copy (-c copy) is safe and fast — no re-encode, no pydub dependency.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from ..errors import DocpodError


def stitch(segment_files: list[Path], out_path: Path) -> Path:
    if not segment_files:
        raise DocpodError("nothing to stitch: no audio segments were produced")
    if shutil.which("ffmpeg") is None:
        raise DocpodError(
            "ffmpeg not found on PATH — it's the one non-Python dependency. "
            "Install it (e.g. `brew install ffmpeg` / `apt install ffmpeg`) and re-run; "
            "your synthesized segments are saved and won't be re-generated."
        )

    list_file = out_path.parent / "audio" / "concat.txt"
    escaped = [str(p.resolve()).replace("'", "'\\''") for p in segment_files]
    list_file.write_text("".join(f"file '{p}'\n" for p in escaped), encoding="utf-8")

    result = subprocess.run(
        ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(list_file), "-c", "copy", str(out_path)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise DocpodError(f"ffmpeg failed to stitch the episode:\n{result.stderr[-2000:]}")
    return out_path

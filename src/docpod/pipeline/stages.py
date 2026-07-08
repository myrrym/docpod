"""Stage orchestration: the resumability contract.

Each stage declares its output artifact(s) inside the working directory:

    parse    -> document.txt
    extract  -> extracted.json
    script   -> script.md
    tts      -> audio/segment_NNN.mp3   (one per script segment)
    stitch   -> episode.mp3

A stage runs only if its artifact is missing, its recorded input hash in
manifest.json no longer matches (e.g. the user edited script.md by hand),
or the user passed --force / --force-from <stage>. A downstream failure must
never discard upstream artifacts: a TTS crash leaves extracted.json and
script.md untouched, so the LLM tokens already spent are never re-spent.
"""

STAGES = ["parse", "extract", "script", "tts", "stitch"]

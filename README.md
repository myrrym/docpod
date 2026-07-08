# docpod

**Turn documents into podcasts, locally.** docpod is an open-source, local-first CLI
that converts a PDF, Word doc, or text/markdown file into a narrated podcast episode —
using AI providers *you* choose, with API keys that never leave your machine.

```
docpod run paper.pdf
# → paper.docpod/episode.mp3
```

## How it works

```
document ──► parse ──► extract ──► script ──► tts ──► stitch ──► episode.mp3
             (text)   (extracted   (script.md)  (audio/         (single mp3)
                        .json)                   segment_*.mp3)
```

1. **Parse** — extract text from PDF (PyMuPDF), .docx (python-docx), or .txt/.md.
   Scanned PDFs with no extractable text fail fast with a clear message (OCR is out
   of scope for v1).
2. **Extract** — an LLM pulls out and structures the document's key concepts
   (`extracted.json`).
3. **Script** — a second LLM pass writes a natural spoken script (`script.md`).
   The script is speaker-tagged, so you can edit it by hand before voicing.
4. **TTS** — your chosen text-to-speech provider voices each segment.
5. **Stitch** — segments are joined into a single `episode.mp3` (requires ffmpeg).

### Resumable by design

Every stage writes its output to a working directory (`<input>.docpod/` by default).
Re-running skips completed stages, so **a TTS failure never re-spends the LLM tokens
you already paid for**. Edit `script.md` by hand and re-run to re-voice only.
Use `--force` (or `--force-from <stage>`) to redo stages deliberately.

## Local-first guarantee

- API keys are read from a local `.env` file — see [`.env.example`](.env.example).
- Keys are sent **only** to the provider APIs you configured (e.g. `api.anthropic.com`,
  `api.openai.com`, `api.elevenlabs.io`). Nothing else. No telemetry, no phoning home.
- All intermediate artifacts stay on your disk in the working directory.

This guarantee is a hard requirement of the project; any PR that violates it will be
rejected.

## Providers

Bring your own keys. Pick providers in `config.toml`:

| Role | Providers (v1)      |
| ---- | ------------------- |
| LLM  | Anthropic, OpenAI   |
| TTS  | ElevenLabs, OpenAI  |

Both roles sit behind a small provider interface (`src/docpod/llm/`, `src/docpod/tts/`),
so adding a provider is one file.

## Setup

Requires Python 3.11+ and [ffmpeg](https://ffmpeg.org/) on your PATH.

```bash
pip install docpod            # or: pip install -e . from a checkout
cp .env.example .env          # add the keys for the providers you use
cp config.example.toml config.toml   # optional — defaults work out of the box
```

## Example: end to end

```bash
# 1. Configure (one-time)
echo 'ANTHROPIC_API_KEY=sk-ant-...' >> .env
echo 'OPENAI_API_KEY=sk-...'        >> .env

# 2. Run
docpod run attention-is-all-you-need.pdf --length 10min --tone conversational

# 3. Listen
open attention-is-all-you-need.docpod/episode.mp3

# 4. Didn't like a phrase? Edit the script and re-voice — no LLM calls repeated:
$EDITOR attention-is-all-you-need.docpod/script.md
docpod run attention-is-all-you-need.pdf --force-from tts
```

## Configuration

TOML file + CLI flag overrides (flags win). Every field has a default, so a bare
`docpod run file.pdf` works with only a `.env`. See
[`config.example.toml`](config.example.toml).

Speakers are a named map, not a hardcoded count — v1 ships single-narrator, but the
script format and config are designed so multi-speaker episodes are additive, not a
rewrite.

## Prompts are yours to edit

The two LLM prompts live as plain files in [`prompts/`](prompts/) — `extract.md`
(stage 1: structure the concepts) and `script.md` (stage 2: write the spoken script).
Tweak them freely; no code changes needed.

## v1 scope

**In:** single-narrator episodes; PDF/.docx/.txt/.md input; two LLM + two TTS
providers; resumable staged pipeline; editable prompts; two-tier chunking (documents
that fit the context window go through in one extract call; larger ones are split on
structure and merged in a final pass).

**Out (deliberately):** OCR for scanned PDFs, multi-speaker dialogue (v1.1 —
the design allows it), enforced episode duration (target length is advisory),
embeddings/RAG, a server or GUI.

## Development

```bash
pip install -e ".[dev]"
pytest
```

Module layout:

```
src/docpod/
├── cli.py        # typer entry point
├── config.py     # TOML + .env loading, defaults
├── parsing/      # pdf, docx, plain text — dispatch by extension
├── llm/          # provider wrapper + the two pipeline stages (extract, script)
├── tts/          # TTSProvider interface + elevenlabs, openai implementations
└── pipeline/     # stage orchestration, skip-if-done manifest, audio stitching
```

## License

MIT

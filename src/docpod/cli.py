"""Typer entry point: `docpod run <input>` and `docpod voices`."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from .config import load_config
from .errors import DocpodError
from .pipeline.stages import STAGES

app = typer.Typer(help="Turn documents into podcasts, locally. Bring your own API keys.", no_args_is_help=True)


@app.command()
def run(
    input: Path = typer.Argument(..., help="Document to convert: .pdf, .docx, .txt, or .md"),
    config: Optional[Path] = typer.Option(None, "--config", "-c", help="Config file (default: ./config.toml if present)"),
    workdir: Optional[Path] = typer.Option(None, help="Working directory (default: <input>.docpod/ beside the input)"),
    length: Optional[str] = typer.Option(None, help="Target length, e.g. '10min' (advisory)"),
    tone: Optional[str] = typer.Option(None, help="Tone for the script, e.g. 'conversational'"),
    llm_provider: Optional[str] = typer.Option(None, help="anthropic | openai"),
    llm_model: Optional[str] = typer.Option(None, help="Model id for the LLM provider"),
    tts_provider: Optional[str] = typer.Option(None, help="elevenlabs | openai"),
    tts_model: Optional[str] = typer.Option(None, help="Model id for the TTS provider"),
    voice: Optional[str] = typer.Option(None, help="Voice id for the first configured speaker"),
    force: bool = typer.Option(False, "--force", help="Re-run every stage"),
    force_from: Optional[str] = typer.Option(None, "--force-from", help=f"Re-run from a stage onward: {', '.join(STAGES)}"),
) -> None:
    """Convert a document into a podcast episode. Completed stages are skipped
    on re-run, so failures never re-spend LLM tokens."""
    from .pipeline.run import run_pipeline

    try:
        cfg = load_config(
            config,
            overrides={
                "workdir": workdir,
                "length": length,
                "tone": tone,
                "llm_provider": llm_provider,
                "llm_model": llm_model,
                "tts_provider": tts_provider,
                "tts_model": tts_model,
            },
        )
        if voice is not None:
            first = next(iter(cfg.speakers))
            cfg.speakers[first] = voice
        episode = run_pipeline(
            input,
            cfg,
            force_from="parse" if force else force_from,
            report=lambda message: typer.secho(f"  {message}", fg=typer.colors.BLUE),
        )
    except DocpodError as exc:
        typer.secho(f"error: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)

    typer.secho(f"✔ episode ready: {episode}", fg=typer.colors.GREEN, bold=True)
    typer.echo(f"  script (editable): {episode.parent / 'script.md'} — edit it and re-run to re-voice only")


@app.command()
def voices(
    config: Optional[Path] = typer.Option(None, "--config", "-c", help="Config file (default: ./config.toml if present)"),
    tts_provider: Optional[str] = typer.Option(None, help="elevenlabs | openai"),
) -> None:
    """List voice ids available from the configured TTS provider."""
    from .tts import make_tts

    try:
        cfg = load_config(config, overrides={"tts_provider": tts_provider})
        provider = make_tts(cfg)
        for voice_id in provider.available_voices():
            typer.echo(voice_id)
    except DocpodError as exc:
        typer.secho(f"error: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()

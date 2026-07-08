"""Typer entry point. Planned surface (implementation comes after scope lock):

    docpod run <input> [--config PATH] [--workdir PATH] [--length 10min]
               [--tone TEXT] [--force] [--force-from STAGE]
    docpod voices        # list voice ids for the configured TTS provider
"""

import typer

app = typer.Typer(help="Turn documents into podcasts, locally.")

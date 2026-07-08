"""Load config: defaults <- config.toml (tomllib, stdlib) <- CLI flags.
Keys come from .env via python-dotenv and are handed only to the selected
provider clients — enforcing the local-first guarantee in the README."""

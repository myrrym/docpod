"""All docpod errors inherit DocpodError so the CLI can catch one type and
print a clean message instead of a traceback."""


class DocpodError(Exception):
    """Base for every error docpod raises on purpose."""


class ConfigError(DocpodError):
    """Bad or missing configuration."""


class MissingAPIKeyError(ConfigError):
    """A provider was selected but its key is absent from the environment."""

    def __init__(self, env_var: str, provider: str):
        super().__init__(
            f"{env_var} is not set, but the '{provider}' provider needs it. "
            f"Add it to your .env file (see .env.example). Keys are only ever "
            f"sent to the provider itself."
        )


class UnsupportedFormatError(DocpodError):
    """Input file extension we don't parse."""


class EmptyDocumentError(DocpodError):
    """The document parsed to nothing."""


class ScannedPDFError(DocpodError):
    """PDF has no extractable text layer (OCR is out of scope for v1)."""


class LLMError(DocpodError):
    """An LLM call failed or returned something unusable."""

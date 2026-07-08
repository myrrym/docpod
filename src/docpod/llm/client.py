"""Thin LLM provider wrapper — deliberately not an abstraction framework.

One method, two providers. Keys come from the environment and go only to the
selected provider's API. Provider SDKs are imported lazily so importing docpod
never requires every SDK.
"""

from __future__ import annotations

import os
from abc import ABC, abstractmethod

from ..config import Config
from ..errors import LLMError, MissingAPIKeyError


class LLMClient(ABC):
    model: str

    @abstractmethod
    def complete(self, prompt: str, max_tokens: int = 8192) -> str:
        """Send one user prompt, return the assistant text."""


class AnthropicLLM(LLMClient):
    DEFAULT_MODEL = "claude-sonnet-5"

    def __init__(self, model: str | None = None):
        if not os.environ.get("ANTHROPIC_API_KEY"):
            raise MissingAPIKeyError("ANTHROPIC_API_KEY", "anthropic")
        import anthropic

        self._client = anthropic.Anthropic()
        self._errors = anthropic.APIError
        self.model = model or self.DEFAULT_MODEL

    def complete(self, prompt: str, max_tokens: int = 8192) -> str:
        try:
            response = self._client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}],
            )
        except self._errors as exc:
            raise LLMError(f"anthropic call failed: {exc}") from exc
        return "".join(block.text for block in response.content if block.type == "text")


class OpenAILLM(LLMClient):
    DEFAULT_MODEL = "gpt-4o"

    def __init__(self, model: str | None = None):
        if not os.environ.get("OPENAI_API_KEY"):
            raise MissingAPIKeyError("OPENAI_API_KEY", "openai")
        import openai

        self._client = openai.OpenAI()
        self._errors = openai.OpenAIError
        self.model = model or self.DEFAULT_MODEL

    def complete(self, prompt: str, max_tokens: int = 8192) -> str:
        try:
            response = self._client.chat.completions.create(
                model=self.model,
                max_completion_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}],
            )
        except self._errors as exc:
            raise LLMError(f"openai call failed: {exc}") from exc
        return response.choices[0].message.content or ""


def make_llm(config: Config) -> LLMClient:
    if config.llm_provider == "anthropic":
        return AnthropicLLM(config.llm_model)
    return OpenAILLM(config.llm_model)

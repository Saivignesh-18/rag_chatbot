"""Shared LLM provider contract.

Both GroqProvider and GeminiProvider return the same normalized completion so the
RAG service and router are provider-agnostic.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass
class LLMCompletion:
    content: str
    provider: str = "groq"
    model: str | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    latency_ms: int | None = None


@runtime_checkable
class LLMProvider(Protocol):
    """Contract every LLM provider implements."""

    name: str

    @property
    def is_configured(self) -> bool:  # pragma: no cover - structural
        ...

    def generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> LLMCompletion:  # pragma: no cover - structural
        ...

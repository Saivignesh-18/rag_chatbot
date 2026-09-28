"""Gemini LLM service (fallback provider).

A thin wrapper around Google's Gen AI SDK that returns the same normalized
``LLMCompletion`` as the Groq provider. The API key is read from configuration
and is NEVER logged. It receives the exact same system prompt + user prompt
(which already contains the retrieved, selected-document context) as Groq, so the
document-only behaviour is identical.
"""
from __future__ import annotations

import time

from app.core.config import settings
from app.core.exceptions import (
    LLMError,
    LLMRateLimitError,
    LLMTimeoutError,
    ServiceUnavailableError,
)
from app.core.logging import get_logger
from app.services.llm_base import LLMCompletion

logger = get_logger(__name__)


class GeminiService:
    name = "gemini"

    def __init__(self) -> None:
        self._client = None

    @property
    def is_configured(self) -> bool:
        return settings.gemini_configured

    def _ensure_client(self):
        if self._client is not None:
            return self._client
        if not settings.gemini_configured:
            raise LLMError(
                "The Gemini API key is not configured on the server.",
                error_code="LLM_NOT_CONFIGURED",
                status_code=503,
            )
        try:
            from google import genai
        except ImportError as exc:  # pragma: no cover
            raise LLMError("The Gemini SDK (google-genai) is not installed.") from exc

        self._client = genai.Client(api_key=settings.gemini_api_key)
        return self._client

    def generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> LLMCompletion:
        """Call Gemini and return the assistant text. Raises AppError on failure."""
        from google.genai import errors, types

        client = self._ensure_client()
        model = model or settings.gemini_model
        temperature = settings.gemini_temperature if temperature is None else temperature
        max_tokens = settings.gemini_max_tokens if max_tokens is None else max_tokens

        started = time.perf_counter()
        try:
            response = client.models.generate_content(
                model=model,
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    temperature=temperature,
                    max_output_tokens=max_tokens,
                ),
            )
        except errors.APIError as exc:
            code = getattr(exc, "code", None)
            if code == 429:
                logger.warning("Gemini request status: RATE_LIMITED (model=%s)", model)
                raise LLMRateLimitError() from exc
            if isinstance(code, int) and code >= 500:
                logger.error("Gemini request status: UPSTREAM_UNAVAILABLE (model=%s, code=%s)", model, code)
                raise ServiceUnavailableError(
                    "The language model service is temporarily unavailable. Please try again."
                ) from exc
            logger.error("Gemini request status: API_ERROR (model=%s, code=%s)", model, code)
            raise LLMError(
                f"The Gemini request was rejected (code={code}). Check GEMINI_MODEL / GEMINI_API_KEY.",
                error_code="LLM_PROVIDER_ERROR",
            ) from exc
        except (TimeoutError,) as exc:
            logger.warning("Gemini request status: TIMEOUT (model=%s)", model)
            raise LLMTimeoutError() from exc
        except Exception as exc:  # noqa: BLE001
            # Detect timeout-like errors from the underlying HTTP client by name.
            if "timeout" in type(exc).__name__.lower():
                logger.warning("Gemini request status: TIMEOUT (model=%s)", model)
                raise LLMTimeoutError() from exc
            logger.exception("Gemini request status: UNEXPECTED (model=%s)", model)
            raise LLMError() from exc

        latency_ms = int((time.perf_counter() - started) * 1000)
        content = self._extract(response)

        usage = getattr(response, "usage_metadata", None)
        prompt_tokens = getattr(usage, "prompt_token_count", None)
        completion_tokens = getattr(usage, "candidates_token_count", None)

        logger.info(
            "Gemini request status: OK (model=%s, latency_ms=%d, prompt_tokens=%s, completion_tokens=%s)",
            model, latency_ms, prompt_tokens, completion_tokens,
        )

        return LLMCompletion(
            content=content,
            provider="gemini",
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            latency_ms=latency_ms,
        )

    @staticmethod
    def _extract(response) -> str:
        try:
            content = (getattr(response, "text", None) or "").strip()
        except Exception as exc:  # noqa: BLE001
            raise LLMError(
                "The language model returned a malformed response.",
                error_code="LLM_MALFORMED_RESPONSE",
            ) from exc
        if not content:
            raise LLMError("The language model returned an empty response.", error_code="LLM_EMPTY_RESPONSE")
        return content


# Module-level singleton.
gemini_service = GeminiService()

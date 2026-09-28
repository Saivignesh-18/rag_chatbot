"""Groq LLM service.

A thin, resilient wrapper around the Groq chat-completions API. The API key is
read from configuration (environment) and is NEVER logged. All Groq error modes
are mapped to application errors:

* timeout           -> LLMTimeoutError (504)
* rate limit        -> LLMRateLimitError (429)
* connection issues -> ServiceUnavailableError (503)
* auth / bad model  -> LLMError (502)
* empty / malformed -> LLMError (502)
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

# Backwards-compatible alias: the normalized completion is shared across providers.
GroqCompletion = LLMCompletion


class GroqService:
    name = "groq"

    def __init__(self) -> None:
        self._client = None

    @property
    def is_configured(self) -> bool:
        return settings.groq_configured

    def _ensure_client(self):
        if self._client is not None:
            return self._client
        if not settings.groq_configured:
            raise LLMError(
                "The Groq API key is not configured on the server.",
                error_code="LLM_NOT_CONFIGURED",
                status_code=503,
            )
        try:
            from groq import Groq
        except ImportError as exc:  # pragma: no cover
            raise LLMError("The Groq SDK is not installed.") from exc

        # Timeout and retries are handled by the SDK. Key is never logged.
        self._client = Groq(
            api_key=settings.groq_api_key,
            timeout=settings.groq_timeout_seconds,
            max_retries=2,
        )
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
        """Call Groq chat completions and return the assistant text.

        Raises an :class:`AppError` subclass on any failure.
        """
        import groq

        client = self._ensure_client()
        model = model or settings.groq_model
        temperature = settings.groq_temperature if temperature is None else temperature
        max_tokens = settings.groq_max_tokens if max_tokens is None else max_tokens

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        started = time.perf_counter()
        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        except groq.APITimeoutError as exc:
            logger.warning("Groq request status: TIMEOUT (model=%s)", model)
            raise LLMTimeoutError() from exc
        except groq.RateLimitError as exc:
            logger.warning("Groq request status: RATE_LIMITED (model=%s)", model)
            raise LLMRateLimitError() from exc
        except groq.AuthenticationError as exc:
            logger.error("Groq request status: AUTH_FAILED (model=%s)", model)
            raise LLMError(
                "Groq authentication failed. Please verify the server's API key.",
                error_code="LLM_AUTH_FAILED",
            ) from exc
        except groq.NotFoundError as exc:
            logger.error("Groq request status: MODEL_NOT_FOUND (model=%s)", model)
            raise LLMError(
                f"The configured model '{model}' is unavailable. Update GROQ_MODEL to a supported model.",
                error_code="LLM_MODEL_UNAVAILABLE",
            ) from exc
        except groq.BadRequestError as exc:
            # Groq returns 400 for decommissioned models and invalid requests.
            logger.error("Groq request status: BAD_REQUEST (model=%s)", model)
            raise LLMError(
                f"The request to the model '{model}' was rejected. The model may be "
                "decommissioned or the request invalid. Update GROQ_MODEL if needed.",
                error_code="LLM_BAD_REQUEST",
            ) from exc
        except (groq.InternalServerError, groq.APIConnectionError) as exc:
            logger.error("Groq request status: UPSTREAM_UNAVAILABLE (model=%s)", model)
            raise ServiceUnavailableError(
                "The language model service is temporarily unavailable. Please try again."
            ) from exc
        except groq.APIError as exc:  # base for any other API error
            logger.error("Groq request status: API_ERROR (model=%s): %s", model, type(exc).__name__)
            raise LLMError() from exc
        except Exception as exc:  # noqa: BLE001 - last resort, do not leak details
            logger.exception("Groq request status: UNEXPECTED (model=%s)", model)
            raise LLMError() from exc

        latency_ms = int((time.perf_counter() - started) * 1000)

        content, usage = self._extract(response)
        prompt_tokens = getattr(usage, "prompt_tokens", None)
        completion_tokens = getattr(usage, "completion_tokens", None)

        logger.info(
            "Groq request status: OK (model=%s, latency_ms=%d, prompt_tokens=%s, completion_tokens=%s)",
            model, latency_ms, prompt_tokens, completion_tokens,
        )

        return LLMCompletion(
            content=content,
            provider="groq",
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            latency_ms=latency_ms,
        )

    @staticmethod
    def _extract(response) -> tuple[str, object]:
        """Safely pull text content from a Groq response; guard against malformed data."""
        try:
            choices = response.choices
            if not choices:
                raise LLMError("The language model returned an empty response.", error_code="LLM_EMPTY_RESPONSE")
            message = choices[0].message
            content = (getattr(message, "content", None) or "").strip()
        except LLMError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise LLMError(
                "The language model returned a malformed response.",
                error_code="LLM_MALFORMED_RESPONSE",
            ) from exc

        if not content:
            raise LLMError("The language model returned an empty response.", error_code="LLM_EMPTY_RESPONSE")

        return content, getattr(response, "usage", None)


# Module-level singleton.
groq_service = GroqService()

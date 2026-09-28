"""LLM router: Groq primary, Gemini automatic fallback.

The RAG service builds the document-only prompt ONCE and hands it to the router.
The router calls the primary provider; on a *retryable provider failure* (rate
limit, timeout, temporary 5xx/service-unavailable) it retries the SAME prompt on
the fallback provider. Application/programming errors (auth, bad model, malformed
request, empty response) are NOT retried. Both providers receive identical input,
so document-only grounding and selected-document scope are preserved on fallback.
"""
from __future__ import annotations

from app.core.config import settings
from app.core.exceptions import (
    AppError,
    LLMRateLimitError,
    LLMTimeoutError,
    ServiceUnavailableError,
)
from app.core.logging import get_logger
from app.services.gemini_service import gemini_service
from app.services.groq_service import groq_service
from app.services.llm_base import LLMCompletion, LLMProvider

logger = get_logger(__name__)

_PROVIDERS: dict[str, LLMProvider] = {
    "groq": groq_service,
    "gemini": gemini_service,
}

# Provider failures worth retrying on the fallback provider.
_RETRYABLE = (LLMRateLimitError, LLMTimeoutError, ServiceUnavailableError)


def is_retryable_provider_error(error: Exception) -> bool:
    """True for transient provider failures (rate limit / timeout / 5xx).

    Uses exception *types* (mapped from structured SDK errors), not string
    matching. Application errors (auth, bad model, validation, bugs) return False.
    """
    return isinstance(error, _RETRYABLE)


def _provider(name: str) -> LLMProvider | None:
    return _PROVIDERS.get((name or "").strip().lower())


class LLMRouter:
    def generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
    ) -> LLMCompletion:
        primary_name = settings.primary_llm
        primary = _provider(primary_name) or groq_service

        logger.info("LLM request started: provider=%s", primary.name)
        try:
            completion = primary.generate(system_prompt=system_prompt, user_prompt=user_prompt)
            logger.info("LLM response generated: provider=%s", completion.provider)
            return completion
        except AppError as exc:
            # Transient provider failures (rate limit/timeout/5xx) AND authentication
            # failures fall back to the secondary provider: if the primary API key is
            # invalid/expired, a configured fallback should keep the app working.
            # Other errors (bad model, validation, empty response) still surface as-is.
            auth_failed = getattr(exc, "error_code", "") == "LLM_AUTH_FAILED"
            if not is_retryable_provider_error(exc) and not auth_failed:
                logger.info(
                    "%s failed with non-retryable error (%s); not falling back.",
                    primary.name, exc.error_code,
                )
                raise

            if not settings.enable_llm_fallback:
                logger.warning("%s failed (%s) and fallback is disabled.", primary.name, exc.error_code)
                raise

            fallback = _provider(settings.fallback_llm)
            if fallback is None or fallback is primary or not fallback.is_configured:
                logger.warning(
                    "%s failed (%s); no usable fallback provider configured.",
                    primary.name, exc.error_code,
                )
                raise

            if auth_failed:
                logger.warning(
                    "%s authentication failed (%s) - its API key looks invalid/expired. "
                    "Falling back to %s; replace the primary key to restore it.",
                    primary.name, exc.error_code, fallback.name,
                )
            else:
                logger.warning(
                    "%s request failed with retryable error (%s). Falling back to %s.",
                    primary.name, exc.error_code, fallback.name,
                )
            try:
                completion = fallback.generate(system_prompt=system_prompt, user_prompt=user_prompt)
                logger.info("LLM response generated: provider=%s (fallback)", completion.provider)
                return completion
            except AppError as exc2:
                logger.error(
                    "Both LLM providers failed (primary=%s: %s, fallback=%s: %s).",
                    primary.name, exc.error_code, fallback.name, exc2.error_code,
                )
                raise ServiceUnavailableError(
                    "Sorry, the AI service is temporarily unavailable. Please try again."
                ) from exc2


# Module-level singleton.
llm_router = LLMRouter()

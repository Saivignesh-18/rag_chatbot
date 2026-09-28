"""Groq service tests using a fake client (no network)."""
from __future__ import annotations

from types import SimpleNamespace

import groq
import httpx
import pytest

from app.core.exceptions import (
    LLMError,
    LLMRateLimitError,
    LLMTimeoutError,
    ServiceUnavailableError,
)
from app.services.groq_service import GroqService

_REQ = httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions")


def _response(code: int) -> httpx.Response:
    return httpx.Response(code, request=_REQ)


class _FakeClient:
    """Minimal stand-in for the Groq client whose create() runs a behaviour."""

    def __init__(self, behavior):
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=behavior))


def _service_with(behavior) -> GroqService:
    svc = GroqService()
    svc._client = _FakeClient(behavior)  # inject fake, bypass real client creation
    return svc


def _ok_response(**_kwargs):
    message = SimpleNamespace(content="The answer is 42.", reasoning="thinking...")
    choice = SimpleNamespace(message=message, finish_reason="stop")
    usage = SimpleNamespace(prompt_tokens=8, completion_tokens=4)
    return SimpleNamespace(choices=[choice], usage=usage)


def test_successful_request():
    svc = _service_with(_ok_response)
    result = svc.generate(system_prompt="s", user_prompt="u")
    assert result.content == "The answer is 42."
    assert result.completion_tokens == 4


def test_empty_response():
    def behavior(**_):
        message = SimpleNamespace(content="", reasoning="only reasoning, no answer")
        return SimpleNamespace(choices=[SimpleNamespace(message=message)], usage=None)

    svc = _service_with(behavior)
    with pytest.raises(LLMError) as exc:
        svc.generate(system_prompt="s", user_prompt="u")
    assert exc.value.error_code == "LLM_EMPTY_RESPONSE"


def test_malformed_response():
    def behavior(**_):
        return SimpleNamespace(choices=[])  # no choices

    svc = _service_with(behavior)
    with pytest.raises(LLMError):
        svc.generate(system_prompt="s", user_prompt="u")


def test_timeout_maps_to_llm_timeout():
    def behavior(**_):
        raise groq.APITimeoutError(request=_REQ)

    svc = _service_with(behavior)
    with pytest.raises(LLMTimeoutError):
        svc.generate(system_prompt="s", user_prompt="u")


def test_rate_limit_maps_to_llm_rate_limit():
    def behavior(**_):
        raise groq.RateLimitError("rate limited", response=_response(429), body=None)

    svc = _service_with(behavior)
    with pytest.raises(LLMRateLimitError):
        svc.generate(system_prompt="s", user_prompt="u")


def test_connection_error_maps_to_service_unavailable():
    def behavior(**_):
        raise groq.APIConnectionError(message="connection failed", request=_REQ)

    svc = _service_with(behavior)
    with pytest.raises(ServiceUnavailableError):
        svc.generate(system_prompt="s", user_prompt="u")


def test_model_not_found_maps_to_llm_error():
    def behavior(**_):
        raise groq.NotFoundError("model missing", response=_response(404), body=None)

    svc = _service_with(behavior)
    with pytest.raises(LLMError) as exc:
        svc.generate(system_prompt="s", user_prompt="u")
    assert exc.value.error_code == "LLM_MODEL_UNAVAILABLE"


def test_auth_error_message_does_not_leak_key():
    def behavior(**_):
        raise groq.AuthenticationError("invalid key", response=_response(401), body=None)

    svc = _service_with(behavior)
    with pytest.raises(LLMError) as exc:
        svc.generate(system_prompt="s", user_prompt="u")
    assert exc.value.error_code == "LLM_AUTH_FAILED"
    assert "gsk_" not in exc.value.message

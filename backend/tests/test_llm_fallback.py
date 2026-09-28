"""LLM router tests: Groq primary with automatic Gemini fallback.

Providers are patched (no network). Fallback triggers only on retryable provider
errors and always reuses the SAME prompt/context.
"""
from __future__ import annotations

import pytest

from app.core.config import settings
from app.core.exceptions import (
    LLMError,
    LLMRateLimitError,
    LLMTimeoutError,
    ServiceUnavailableError,
)
from app.services.gemini_service import gemini_service
from app.services.groq_service import groq_service
from app.services.llm_base import LLMCompletion
from app.services.llm_router import is_retryable_provider_error, llm_router
from tests.conftest import PDF_CT, ask, create_session, make_pdf, upload


@pytest.fixture
def enable_fallback(monkeypatch):
    """Ensure fallback is enabled and Gemini is considered configured."""
    monkeypatch.setattr(settings, "primary_llm", "groq")
    monkeypatch.setattr(settings, "fallback_llm", "gemini")
    monkeypatch.setattr(settings, "enable_llm_fallback", True)
    monkeypatch.setattr(settings, "gemini_api_key", "test-gemini-key")


def _groq_raises(monkeypatch, exc):
    calls = {"groq": 0}

    def fake(**_):
        calls["groq"] += 1
        raise exc

    monkeypatch.setattr(groq_service, "generate", fake)
    return calls


def _gemini_returns(monkeypatch, content="Gemini answer."):
    calls = {"gemini": 0}

    def fake(**kwargs):
        calls["gemini"] += 1
        # Echo the prompt so context-preservation can be asserted.
        return LLMCompletion(content=f"{content} :: {kwargs.get('user_prompt', '')}", provider="gemini", model="gemini-x")

    monkeypatch.setattr(gemini_service, "generate", fake)
    return calls


# ---- unit: retryable classification ----
def test_is_retryable_classification():
    assert is_retryable_provider_error(LLMRateLimitError())
    assert is_retryable_provider_error(LLMTimeoutError())
    assert is_retryable_provider_error(ServiceUnavailableError())
    assert not is_retryable_provider_error(LLMError())
    assert not is_retryable_provider_error(ValueError("bug"))


# ---- router behaviour ----
def test_groq_success_no_fallback(monkeypatch, enable_fallback):
    monkeypatch.setattr(groq_service, "generate", lambda **_: LLMCompletion(content="Groq!", provider="groq"))
    g = _gemini_returns(monkeypatch)
    res = llm_router.generate(system_prompt="s", user_prompt="u")
    assert res.provider == "groq" and res.content == "Groq!"
    assert g["gemini"] == 0  # fallback not used


@pytest.mark.parametrize("exc", [LLMRateLimitError(), LLMTimeoutError(), ServiceUnavailableError()])
def test_fallback_on_retryable_errors(monkeypatch, enable_fallback, exc):
    _groq_raises(monkeypatch, exc)
    g = _gemini_returns(monkeypatch)
    res = llm_router.generate(system_prompt="s", user_prompt="u")
    assert res.provider == "gemini"
    assert g["gemini"] == 1


def test_no_fallback_on_application_error(monkeypatch, enable_fallback):
    _groq_raises(monkeypatch, LLMError("bad model", error_code="LLM_MODEL_UNAVAILABLE"))
    g = _gemini_returns(monkeypatch)
    with pytest.raises(LLMError):
        llm_router.generate(system_prompt="s", user_prompt="u")
    assert g["gemini"] == 0  # app errors do not trigger fallback


def test_both_providers_fail_returns_controlled_error(monkeypatch, enable_fallback):
    _groq_raises(monkeypatch, LLMRateLimitError())

    def gemini_fail(**_):
        raise LLMError("gemini down")

    monkeypatch.setattr(gemini_service, "generate", gemini_fail)
    with pytest.raises(ServiceUnavailableError):
        llm_router.generate(system_prompt="s", user_prompt="u")


def test_fallback_disabled(monkeypatch, enable_fallback):
    monkeypatch.setattr(settings, "enable_llm_fallback", False)
    _groq_raises(monkeypatch, LLMRateLimitError())
    g = _gemini_returns(monkeypatch)
    with pytest.raises(LLMRateLimitError):
        llm_router.generate(system_prompt="s", user_prompt="u")
    assert g["gemini"] == 0


# ---- end-to-end via /api/chat: fallback preserves selected-document context ----
def test_fallback_preserves_selected_document_scope(client, auth_a, monkeypatch, enable_fallback):
    """Force Groq to fail; Gemini must answer from the SAME selected document."""
    _groq_raises(monkeypatch, LLMRateLimitError())
    _gemini_returns(monkeypatch, content="Based on the selected documents:")

    doc_a = upload(client, auth_a["headers"], "A.pdf", make_pdf(["The retirement age is 60."]), PDF_CT).json()["document_id"]
    doc_b = upload(client, auth_a["headers"], "B.pdf", make_pdf(["The retirement age is 58."]), PDF_CT).json()["document_id"]

    s_a = create_session(client, auth_a["headers"], [doc_a]).json()["session"]
    ans_a = ask(client, auth_a["headers"], s_a["id"], "What is the retirement age?").json()["answer"]
    assert "60" in ans_a and "58" not in ans_a  # Gemini got Document A's context only

    s_b = create_session(client, auth_a["headers"], [doc_b]).json()["session"]
    ans_b = ask(client, auth_a["headers"], s_b["id"], "What is the retirement age?").json()["answer"]
    assert "58" in ans_b and "60" not in ans_b


def test_fallback_still_refuses_when_no_relevant_context(client, auth_a, monkeypatch, enable_fallback):
    """Threshold gate runs before the LLM, so fallback never sees irrelevant queries."""
    from app.services.prompt_service import REFUSAL_MESSAGE

    _groq_raises(monkeypatch, LLMRateLimitError())
    g = _gemini_returns(monkeypatch)

    doc = upload(client, auth_a["headers"], "A.pdf", make_pdf(["The retirement age is 60."]), PDF_CT).json()["document_id"]
    s = create_session(client, auth_a["headers"], [doc]).json()["session"]
    r = ask(client, auth_a["headers"], s["id"], "Who is the Prime Minister of India?").json()
    assert r["answer"] == REFUSAL_MESSAGE
    assert g["gemini"] == 0  # refused before reaching any LLM

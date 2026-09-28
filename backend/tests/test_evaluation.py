"""Critical RAG evaluation (spec section 35), using the REAL Groq API.

Skipped automatically when no Groq key is configured.
"""
from __future__ import annotations

import pytest

from app.core.config import settings
from app.services.prompt_service import REFUSAL_MESSAGE
from tests.conftest import PDF_CT, ask, create_session, make_pdf, upload

pytestmark = pytest.mark.skipif(
    not settings.groq_configured,
    reason="GROQ_API_KEY not configured; skipping live LLM evaluation.",
)

EVAL_DOC = [
    "System Capacity Specification",
    "The system supports 600 concurrent users under normal conditions and 3,000 "
    "concurrent users during peak periods.",
]


def _setup_session(client, headers):
    doc_id = upload(client, headers, "capacity.pdf", make_pdf(EVAL_DOC), PDF_CT).json()["document_id"]
    return create_session(client, headers, [doc_id]).json()["session"]["id"]


def test_answer_is_grounded_in_the_document(client, auth_a):
    sid = _setup_session(client, auth_a["headers"])
    r = ask(client, auth_a["headers"], sid, "How many concurrent users are supported?")
    assert r.status_code == 200
    answer = r.json()["answer"]
    assert "600" in answer
    assert "3,000" in answer or "3000" in answer
    assert len(r.json()["sources"]) >= 1


def test_general_knowledge_is_refused(client, auth_a):
    sid = _setup_session(client, auth_a["headers"])
    r = ask(client, auth_a["headers"], sid, "Who is the Prime Minister of India?")
    assert r.status_code == 200
    assert r.json()["answer"] == REFUSAL_MESSAGE
    assert r.json()["sources"] == []

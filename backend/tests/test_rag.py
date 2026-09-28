"""RAG pipeline tests: session scope, selective retrieval, threshold, refusal."""
from __future__ import annotations

import uuid

from app.services.prompt_service import REFUSAL_MESSAGE
from tests.conftest import PDF_CT, ask, create_session, make_pdf, upload


def _upload(client, headers, name, pages):
    return upload(client, headers, name, make_pdf(pages), PDF_CT).json()["document_id"]


def test_relevant_question_uses_scope_and_returns_sources(client, auth_a, mock_groq):
    doc = _upload(client, auth_a["headers"], "rfp.pdf", [
        "The system supports 600 concurrent users under normal conditions and 3,000 during peak.",
    ])
    session = create_session(client, auth_a["headers"], [doc], "capacity").json()["session"]

    r = ask(client, auth_a["headers"], session["id"], "How many concurrent users are supported?")
    assert r.status_code == 200
    body = r.json()
    assert len(body["sources"]) >= 1
    assert "600" in body["answer"]  # the mock echoes the retrieved context
    assert len(mock_groq) == 1


def test_irrelevant_question_refuses_without_calling_llm(client, auth_a, mock_groq):
    doc = _upload(client, auth_a["headers"], "rfp.pdf", ["Encryption at rest and in transit is required."])
    session = create_session(client, auth_a["headers"], [doc]).json()["session"]

    r = ask(client, auth_a["headers"], session["id"], "Who is the Prime Minister of India?")
    assert r.status_code == 200
    assert r.json()["answer"] == REFUSAL_MESSAGE
    assert r.json()["sources"] == []
    assert len(mock_groq) == 0  # threshold gate refused before the LLM


# ---- MANDATORY: document isolation (spec section 30) ----
def test_document_isolation(client, auth_a, mock_groq):
    doc_a = _upload(client, auth_a["headers"], "A.pdf", ["The retirement age is 60."])
    doc_b = _upload(client, auth_a["headers"], "B.pdf", ["The retirement age is 58."])
    doc_c = _upload(client, auth_a["headers"], "C.pdf", ["The cafeteria serves lunch at noon."])

    # Scope = A only -> answer reflects 60, never 58.
    s_a = create_session(client, auth_a["headers"], [doc_a]).json()["session"]
    ans_a = ask(client, auth_a["headers"], s_a["id"], "What is the retirement age?").json()["answer"]
    assert "60" in ans_a
    assert "58" not in ans_a

    # Scope = B only -> answer reflects 58, never 60.
    s_b = create_session(client, auth_a["headers"], [doc_b]).json()["session"]
    ans_b = ask(client, auth_a["headers"], s_b["id"], "What is the retirement age?").json()["answer"]
    assert "58" in ans_b
    assert "60" not in ans_b

    # Scope = C (neither answer) -> refusal.
    s_c = create_session(client, auth_a["headers"], [doc_c]).json()["session"]
    ans_c = ask(client, auth_a["headers"], s_c["id"], "What is the retirement age?").json()
    assert ans_c["answer"] == REFUSAL_MESSAGE
    assert ans_c["sources"] == []


def test_change_scope_changes_answer_and_preserves_history(client, auth_a, mock_groq):
    doc_a = _upload(client, auth_a["headers"], "A.pdf", ["The retirement age is 60."])
    doc_b = _upload(client, auth_a["headers"], "B.pdf", ["The retirement age is 58."])

    session = create_session(client, auth_a["headers"], [doc_a]).json()["session"]
    sid = session["id"]
    a1 = ask(client, auth_a["headers"], sid, "What is the retirement age?").json()["answer"]
    assert "60" in a1

    # Change scope to B (preserve the same session).
    patched = client.patch(
        f"/api/chat/sessions/{sid}/documents",
        json={"document_ids": [doc_b]},
        headers=auth_a["headers"],
    )
    assert patched.status_code == 200
    assert patched.json()["session"]["document_count"] == 1

    a2 = ask(client, auth_a["headers"], sid, "What is the retirement age?").json()["answer"]
    assert "58" in a2

    # History preserved: 2 Q + 2 A = 4 messages.
    detail = client.get(f"/api/chat/sessions/{sid}", headers=auth_a["headers"]).json()
    assert len(detail["messages"]) == 4


def test_multiple_document_retrieval(client, auth_a, mock_groq):
    doc_rfp = _upload(client, auth_a["headers"], "rfp.pdf", ["Peak capacity is 3,000 concurrent users."])
    doc_pay = _upload(client, auth_a["headers"], "pay.pdf", ["Salaries are paid on the last working day."])
    session = create_session(client, auth_a["headers"], [doc_rfp, doc_pay]).json()["session"]

    r = ask(client, auth_a["headers"], session["id"], "When are salaries paid?")
    names = {s["document_name"] for s in r.json()["sources"]}
    assert "pay.pdf" in names


def test_similarity_threshold_gate(client, auth_a):
    """Threshold is enforced after user+scope restricted retrieval."""
    from app.db.database import SessionLocal
    from app.services.retrieval_service import retrieve

    uid = uuid.UUID(auth_a["id"])
    doc = _upload(client, auth_a["headers"], "leave.pdf", ["Employees receive 24 days of paid annual leave."])
    doc_uuid = uuid.UUID(doc)

    with SessionLocal() as db:
        strict = retrieve(db, "annual leave allowance", user_id=uid, document_ids=[doc_uuid], threshold=0.99)
        lenient = retrieve(db, "annual leave allowance", user_id=uid, document_ids=[doc_uuid], threshold=0.0)

    assert len(strict.accepted) == 0
    assert len(lenient.accepted) >= 1


def test_empty_question_rejected(client, auth_a):
    doc = _upload(client, auth_a["headers"], "x.pdf", ["Some content here."])
    session = create_session(client, auth_a["headers"], [doc]).json()["session"]
    r = ask(client, auth_a["headers"], session["id"], "   ")
    assert r.status_code in (400, 422)
    assert r.json()["success"] is False

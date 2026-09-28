"""User-isolation tests (spec section 31): cross-user access must be blocked."""
from __future__ import annotations

from tests.conftest import PDF_CT, ask, create_session, make_pdf, upload


def _upload(client, headers, name, text):
    return upload(client, headers, name, make_pdf([text]), PDF_CT).json()["document_id"]


def test_users_only_see_their_own_documents(client, auth_a, auth_b):
    a1 = _upload(client, auth_a["headers"], "A1.pdf", "Alice document one.")
    _upload(client, auth_b["headers"], "B1.pdf", "Bob document one.")

    a_list = client.get("/api/documents", headers=auth_a["headers"]).json()
    b_list = client.get("/api/documents", headers=auth_b["headers"]).json()

    a_names = {d["filename"] for d in a_list["documents"]}
    b_names = {d["filename"] for d in b_list["documents"]}
    assert a_names == {"A1.pdf"}
    assert b_names == {"B1.pdf"}

    # A's document id exists, but B cannot fetch or delete it (404, not leaked).
    assert client.get(f"/api/documents/{a1}", headers=auth_b["headers"]).status_code == 404
    assert client.delete(f"/api/documents/{a1}", headers=auth_b["headers"]).status_code == 404


def test_user_cannot_scope_session_to_another_users_document(client, auth_a, auth_b):
    a1 = _upload(client, auth_a["headers"], "A1.pdf", "Alice secret content.")
    # Bob tries to create a session referencing Alice's document id -> forbidden.
    r = create_session(client, auth_b["headers"], [a1])
    assert r.status_code == 403
    assert r.json()["error_code"] == "FORBIDDEN"


def test_user_cannot_use_another_users_session(client, auth_a, auth_b, mock_groq):
    a1 = _upload(client, auth_a["headers"], "A1.pdf", "The budget is 5 million dollars.")
    session = create_session(client, auth_a["headers"], [a1]).json()["session"]

    # Bob cannot read, chat in, or delete Alice's session (404, existence hidden).
    assert client.get(f"/api/chat/sessions/{session['id']}", headers=auth_b["headers"]).status_code == 404
    assert ask(client, auth_b["headers"], session["id"], "What is the budget?").status_code == 404
    assert client.delete(f"/api/chat/sessions/{session['id']}", headers=auth_b["headers"]).status_code == 404


def test_users_only_see_their_own_sessions(client, auth_a, auth_b):
    a1 = _upload(client, auth_a["headers"], "A1.pdf", "Alice content.")
    create_session(client, auth_a["headers"], [a1], "Alice chat")

    b_sessions = client.get("/api/chat/sessions", headers=auth_b["headers"]).json()
    assert b_sessions["total"] == 0

    a_sessions = client.get("/api/chat/sessions", headers=auth_a["headers"]).json()
    assert a_sessions["total"] == 1


def test_retrieval_never_crosses_users(client, auth_a, auth_b, mock_groq):
    # Alice and Bob both have a document mentioning a distinct secret number.
    a1 = _upload(client, auth_a["headers"], "A.pdf", "The alpha access code is 111.")
    _upload(client, auth_b["headers"], "B.pdf", "The bravo access code is 999.")

    # Alice chats over her own doc; Bob's content (999) must never appear.
    s = create_session(client, auth_a["headers"], [a1]).json()["session"]
    ans = ask(client, auth_a["headers"], s["id"], "What is the access code?").json()["answer"]
    assert "111" in ans
    assert "999" not in ans

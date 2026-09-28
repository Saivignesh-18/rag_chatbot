"""Email/password auth tests: register, login, forgot/reset password."""
from __future__ import annotations


def test_register_then_login(client):
    r = client.post("/api/auth/register", json={"email": "dana@example.com", "password": "secret123", "name": "Dana"})
    assert r.status_code == 200
    body = r.json()
    assert body["access_token"]
    assert body["user"]["email"] == "dana@example.com"
    assert body["user"]["provider"] == "Email"
    token = body["access_token"]

    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["user"]["email"] == "dana@example.com"

    ok = client.post("/api/auth/login", json={"email": "dana@example.com", "password": "secret123"})
    assert ok.status_code == 200
    assert ok.json()["access_token"]


def test_login_wrong_password_rejected(client):
    client.post("/api/auth/register", json={"email": "eve@example.com", "password": "correct-horse", "name": "Eve"})
    bad = client.post("/api/auth/login", json={"email": "eve@example.com", "password": "wrong-pass"})
    assert bad.status_code == 401
    assert bad.json()["error_code"] == "UNAUTHORIZED"


def test_duplicate_registration_conflict(client):
    client.post("/api/auth/register", json={"email": "frank@example.com", "password": "password1", "name": "Frank"})
    dup = client.post("/api/auth/register", json={"email": "frank@example.com", "password": "password2", "name": "F"})
    assert dup.status_code == 409
    assert dup.json()["error_code"] == "CONFLICT"


def test_register_validation(client):
    short = client.post("/api/auth/register", json={"email": "gary@example.com", "password": "short", "name": "Gary"})
    assert short.status_code == 422
    bademail = client.post("/api/auth/register", json={"email": "not-an-email", "password": "longenough", "name": "X"})
    assert bademail.status_code == 422


def test_forgot_and_reset_password(client):
    client.post("/api/auth/register", json={"email": "helen@example.com", "password": "oldpassword", "name": "Helen"})

    forgot = client.post("/api/auth/forgot-password", json={"email": "helen@example.com"})
    assert forgot.status_code == 200
    reset_token = forgot.json()["reset_token"]
    assert reset_token  # dev-mode token returned

    reset = client.post("/api/auth/reset-password", json={"token": reset_token, "new_password": "brandnewpass"})
    assert reset.status_code == 200

    # Old password no longer works; new one does.
    assert client.post("/api/auth/login", json={"email": "helen@example.com", "password": "oldpassword"}).status_code == 401
    assert client.post("/api/auth/login", json={"email": "helen@example.com", "password": "brandnewpass"}).status_code == 200


def test_forgot_password_unknown_email_no_enumeration(client):
    r = client.post("/api/auth/forgot-password", json={"email": "nobody@example.com"})
    assert r.status_code == 200
    assert r.json()["reset_token"] is None


def test_email_login_document_isolation(client, mock_groq):
    """A registered email user gets a working, isolated workspace."""
    from tests.conftest import PDF_CT, ask, create_session, make_pdf, upload

    reg = client.post("/api/auth/register", json={"email": "ivan@example.com", "password": "password1", "name": "Ivan"})
    headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}

    doc = upload(client, headers, "A.pdf", make_pdf(["The retirement age is 60."]), PDF_CT).json()["document_id"]
    session = create_session(client, headers, [doc]).json()["session"]
    ans = ask(client, headers, session["id"], "What is the retirement age?").json()["answer"]
    assert "60" in ans

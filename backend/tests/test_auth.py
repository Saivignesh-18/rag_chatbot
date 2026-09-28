"""Authentication tests (Google verification is mocked; no network)."""
from __future__ import annotations


def test_me_requires_auth(client):
    assert client.get("/api/auth/me").status_code == 401


def test_invalid_token_rejected(client):
    r = client.get("/api/auth/me", headers={"Authorization": "Bearer not-a-real-token"})
    assert r.status_code == 401
    assert r.json()["error_code"] == "UNAUTHORIZED"


def test_chat_requires_auth(client):
    r = client.post("/api/chat", json={"session_id": "00000000-0000-0000-0000-000000000000", "question": "hi"})
    assert r.status_code == 401


def test_google_login_creates_and_reuses_user(client, monkeypatch):
    # Mock Google verification to return stable claims for a fixed subject.
    from app.api import auth as auth_api

    claims = {
        "sub": "google-sub-123",
        "email": "carol@example.com",
        "name": "Carol",
        "picture": "https://example.com/c.png",
        "iss": "https://accounts.google.com",
    }
    monkeypatch.setattr(auth_api, "verify_google_token", lambda credential: claims)

    r1 = client.post("/api/auth/google", json={"credential": "fake-token"})
    assert r1.status_code == 200
    body1 = r1.json()
    assert body1["access_token"]
    assert body1["user"]["email"] == "carol@example.com"
    user_id_1 = body1["user"]["id"]

    # /me works with the issued token.
    token = body1["access_token"]
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["user"]["email"] == "carol@example.com"

    # Logging in again with the same google_sub reuses the same user (no dup).
    r2 = client.post("/api/auth/google", json={"credential": "fake-token-2"})
    assert r2.json()["user"]["id"] == user_id_1

    # Logout requires a valid token and succeeds.
    out = client.post("/api/auth/logout", headers={"Authorization": f"Bearer {token}"})
    assert out.status_code == 200
    assert out.json()["success"] is True

"""Security-focused tests: validation, limits, filename safety, secret exposure."""
from __future__ import annotations

import json

import pytest

from app.core.exceptions import EmptyFileError, FileTooLargeError, UnsupportedFileTypeError
from app.core.security import sanitize_filename, validate_upload
from tests.conftest import TXT_CT, make_txt, upload


def test_sanitize_filename_strips_path_traversal():
    assert sanitize_filename("../../etc/passwd") == "passwd"
    assert sanitize_filename("..\\..\\windows\\system32\\evil.txt") == "evil.txt"
    assert "/" not in sanitize_filename("a/b/c.pdf")
    assert "\\" not in sanitize_filename("a\\b\\c.pdf")


def test_sanitize_filename_removes_dangerous_characters():
    cleaned = sanitize_filename("  My  Rép$ort<>:.PDF ")
    assert cleaned.endswith(".pdf")
    assert all(c.isalnum() or c in "-_." for c in cleaned)


def test_validate_upload_rejects_unsupported_type():
    with pytest.raises(UnsupportedFileTypeError):
        validate_upload("script.js", b"console.log(1)")


def test_validate_upload_rejects_empty():
    with pytest.raises(EmptyFileError):
        validate_upload("empty.txt", b"")


def test_validate_upload_rejects_oversized():
    with pytest.raises(FileTooLargeError):
        validate_upload("big.txt", b"x" * (21 * 1024 * 1024))


def test_fake_pdf_signature_rejected():
    with pytest.raises(UnsupportedFileTypeError):
        validate_upload("fake.pdf", b"not a pdf")


def test_invalid_chat_payload_returns_422(client, auth_a):
    # Authenticated but missing required fields -> validation error.
    r = client.post("/api/chat", json={}, headers=auth_a["headers"])
    assert r.status_code == 422
    assert r.json()["success"] is False


def test_oversized_upload_endpoint(client, auth_a):
    r = upload(client, auth_a["headers"], "big.txt", b"a" * (21 * 1024 * 1024), TXT_CT)
    assert r.status_code == 413


def test_health_does_not_expose_secrets(client):
    r = client.get("/api/health")
    payload = json.dumps(r.json())
    assert "gsk_" not in payload
    assert "JWT" not in payload and "jwt_secret" not in payload
    assert isinstance(r.json()["groq_configured"], bool)


def test_error_responses_are_sanitized(client, auth_a):
    r = upload(client, auth_a["headers"], "x.exe", b"binary", "application/octet-stream")
    body = r.json()
    assert set(body.keys()) == {"success", "message", "error_code"}
    assert "Traceback" not in body["message"]

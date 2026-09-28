"""Document upload & processing tests (authenticated, user-scoped)."""
from __future__ import annotations

from tests.conftest import (
    DOCX_CT,
    PDF_CT,
    TXT_CT,
    make_docx,
    make_pdf,
    make_txt,
    upload,
)


def test_valid_pdf(client, auth_a):
    data = make_pdf(["Page one text about onboarding.", "Page two: vacation policy details."])
    r = upload(client, auth_a["headers"], "handbook.pdf", data, PDF_CT)
    assert r.status_code == 200
    body = r.json()
    assert body["success"] is True
    assert body["filename"] == "handbook.pdf"
    assert body["total_chunks"] >= 1


def test_valid_docx(client, auth_a):
    data = make_docx(["The reimbursement limit is 500 dollars per month.", "Approvals need manager sign-off."])
    r = upload(client, auth_a["headers"], "policy.docx", data, DOCX_CT)
    assert r.status_code == 200
    assert r.json()["total_chunks"] >= 1


def test_valid_txt(client, auth_a):
    r = upload(client, auth_a["headers"], "notes.txt", make_txt("Standup happens at 9:30 AM every weekday."), TXT_CT)
    assert r.status_code == 200
    assert r.json()["total_chunks"] >= 1


def test_invalid_file_type(client, auth_a):
    r = upload(client, auth_a["headers"], "malware.exe", b"MZ\x90\x00binarystuff", "application/octet-stream")
    assert r.status_code == 400
    assert r.json()["error_code"] == "UNSUPPORTED_FILE_TYPE"


def test_empty_file(client, auth_a):
    r = upload(client, auth_a["headers"], "empty.txt", b"", TXT_CT)
    assert r.status_code == 400
    assert r.json()["error_code"] == "EMPTY_FILE"


def test_large_file_rejected(client, auth_a):
    big = b"a" * (21 * 1024 * 1024)
    r = upload(client, auth_a["headers"], "big.txt", big, TXT_CT)
    assert r.status_code == 413
    assert r.json()["error_code"] == "FILE_TOO_LARGE"


def test_corrupted_pdf(client, auth_a):
    r = upload(client, auth_a["headers"], "broken.pdf", b"%PDF-1.4\nthis is not a real pdf body", PDF_CT)
    assert r.status_code in (400, 500)
    assert r.json()["success"] is False


def test_list_get_delete_lifecycle(client, auth_a):
    up = upload(client, auth_a["headers"], "lifecycle.txt", make_txt("Alpha bravo charlie delta echo."), TXT_CT)
    doc_id = up.json()["document_id"]

    listing = client.get("/api/documents", headers=auth_a["headers"]).json()
    assert listing["total"] == 1
    assert listing["documents"][0]["id"] == doc_id

    detail = client.get(f"/api/documents/{doc_id}", headers=auth_a["headers"])
    assert detail.status_code == 200
    assert detail.json()["document"]["status"] == "completed"

    f = client.get(f"/api/documents/{doc_id}/file", headers=auth_a["headers"])
    assert f.status_code == 200

    d = client.delete(f"/api/documents/{doc_id}", headers=auth_a["headers"])
    assert d.status_code == 200
    assert client.get(f"/api/documents/{doc_id}", headers=auth_a["headers"]).status_code == 404


def test_documents_require_authentication(client):
    assert client.get("/api/documents").status_code == 401
    assert client.post("/api/documents/upload").status_code == 401

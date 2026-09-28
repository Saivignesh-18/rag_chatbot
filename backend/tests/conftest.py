"""Shared pytest fixtures and helpers.

Tests exercise the REAL pipeline (parsing, embeddings, PostgreSQL + pgvector).
Groq is mocked for determinism (a live evaluation test uses the real API and is
skipped when unconfigured). Authentication is exercised by minting app JWTs for
test users directly (no real Google round-trip needed).
"""
from __future__ import annotations

import io
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text


# ---- Sample document builders ----
def make_pdf(pages: list[str]) -> bytes:
    from fpdf import FPDF

    pdf = FPDF()
    pdf.set_font("Helvetica", size=12)
    for page_text in pages:
        pdf.add_page()
        pdf.multi_cell(0, 6, page_text)
    return bytes(pdf.output())


def make_docx(paragraphs: list[str]) -> bytes:
    from docx import Document as DocxDocument

    doc = DocxDocument()
    for p in paragraphs:
        doc.add_paragraph(p)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def make_txt(text_content: str) -> bytes:
    return text_content.encode("utf-8")


PDF_CT = "application/pdf"
DOCX_CT = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
TXT_CT = "text/plain"


@pytest.fixture(scope="session")
def client():
    from app.core.rate_limit import limiter
    from app.main import app

    # Disable API rate limiting during tests (the suite hammers endpoints from a
    # single client IP within a minute, which would otherwise trip 429s).
    limiter.enabled = False

    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def clean_db(client):
    from app.core.config import settings
    from app.db.database import engine

    with engine.begin() as conn:
        conn.execute(text("TRUNCATE users CASCADE"))
        conn.execute(text("TRUNCATE documents CASCADE"))
        conn.execute(text("TRUNCATE chat_sessions CASCADE"))

    storage = Path(settings.upload_storage_dir)
    if storage.exists():
        for f in storage.glob("*"):
            try:
                f.unlink()
            except OSError:
                pass
    yield


def create_user(email: str, sub: str) -> tuple[str, dict]:
    """Create a user directly and return (user_id, auth headers)."""
    from app.core.auth import create_access_token
    from app.db.database import SessionLocal
    from app.models.user import User

    with SessionLocal() as db:
        user = User(google_sub=sub, email=email, name=email.split("@")[0])
        db.add(user)
        db.commit()
        db.refresh(user)
        uid = user.id
    token = create_access_token(uid)
    return str(uid), {"Authorization": f"Bearer {token}"}


@pytest.fixture
def auth_a():
    uid, headers = create_user("alice@example.com", f"sub-a-{uuid.uuid4()}")
    return {"id": uid, "headers": headers}


@pytest.fixture
def auth_b():
    uid, headers = create_user("bob@example.com", f"sub-b-{uuid.uuid4()}")
    return {"id": uid, "headers": headers}


@pytest.fixture
def mock_groq(monkeypatch):
    """Replace the Groq call with a deterministic echo of the retrieved context.

    Echoing the context lets isolation tests assert which document influenced the
    answer (e.g. that '60' appears only when Document A is in scope).
    """
    from app.services import groq_service as gs_module
    from app.services.groq_service import GroqCompletion

    calls: list[dict] = []

    def fake_generate(*, system_prompt, user_prompt, model=None, temperature=None, max_tokens=None):
        calls.append({"system": system_prompt, "user": user_prompt})
        # The user_prompt contains the retrieved context; echo it back so tests
        # can verify grounding/scope (e.g. that only Document A's text is present).
        return GroqCompletion(
            content=f"Based on the selected documents: {user_prompt}",
            model="mock-model",
            prompt_tokens=10,
            completion_tokens=12,
            latency_ms=1,
        )

    monkeypatch.setattr(gs_module.groq_service, "generate", fake_generate)
    return calls


# ---- Authenticated request helpers ----
def upload(client: TestClient, headers: dict, filename: str, data: bytes, content_type: str):
    return client.post(
        "/api/documents/upload",
        files={"file": (filename, data, content_type)},
        headers=headers,
    )


def create_session(client: TestClient, headers: dict, document_ids: list[str], title: str | None = None):
    return client.post(
        "/api/chat/sessions",
        json={"document_ids": document_ids, "title": title},
        headers=headers,
    )


def ask(client: TestClient, headers: dict, session_id: str, question: str):
    return client.post(
        "/api/chat",
        json={"session_id": session_id, "question": question},
        headers=headers,
    )

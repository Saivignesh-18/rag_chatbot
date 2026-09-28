"""Document service: orchestrates upload validation, storage, parsing and
persistence. The chunking + embedding ingestion step is added in Phase 4.
"""
from __future__ import annotations

import uuid
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import AppError, DocumentProcessingError, NotFoundError
from app.core.logging import get_logger
from app.core.security import get_extension, validate_upload
from app.models.document import (
    STATUS_COMPLETED,
    STATUS_FAILED,
    STATUS_PROCESSING,
    Document,
)
from app.services.document_parser import ParsedDocument, parse_document

logger = get_logger(__name__)


def _storage_dir() -> Path:
    path = Path(settings.upload_storage_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _stored_path(document_id: uuid.UUID, ext: str) -> Path:
    return _storage_dir() / f"{document_id}{ext}"


def save_raw_file(document_id: uuid.UUID, ext: str, data: bytes) -> Path:
    """Persist the original bytes for optional preview/download."""
    path = _stored_path(document_id, ext)
    path.write_bytes(data)
    return path


def get_stored_file(document: Document) -> Path | None:
    ext = get_extension(document.filename)
    path = _stored_path(document.id, ext)
    return path if path.exists() else None


def process_upload(
    db: Session, original_filename: str | None, data: bytes, *, user_id: uuid.UUID | None = None
) -> Document:
    """Validate, store, parse and persist an uploaded document owned by ``user_id``.

    Raises an :class:`AppError` subclass on any failure. When a document row has
    already been created, its status is set to ``failed`` before re-raising.
    """
    # 1) Validate (size, extension, signature). Raises before any DB writes.
    file_type, safe_name = validate_upload(original_filename, data)
    ext = get_extension(safe_name)

    logger.info(
        "Document uploaded: name=%r type=%s size=%d bytes user=%s",
        safe_name, file_type, len(data), user_id,
    )

    # 2) Create the document row (processing), owned by the current user.
    document = Document(
        user_id=user_id,
        filename=safe_name,
        file_type=file_type,
        file_size=len(data),
        status=STATUS_PROCESSING,
        total_chunks=0,
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    logger.info("Document processing started: id=%s", document.id)

    try:
        # 3) Persist raw bytes (best-effort, for preview/download).
        save_raw_file(document.id, ext, data)

        # 4) Extract + clean text.
        parsed: ParsedDocument = parse_document(data, file_type)
        document.page_count = parsed.page_count

        # 5) Chunk + embed + store vectors, then finalise.
        total_chunks = _ingest_parsed_document(db, document, parsed)
        document.total_chunks = total_chunks
        document.status = STATUS_COMPLETED
        db.commit()
        db.refresh(document)
        logger.info(
            "Document processing completed: id=%s pages=%s chunks=%d",
            document.id, document.page_count, total_chunks,
        )
        return document

    except AppError as exc:
        _mark_failed(db, document, exc.message)
        logger.warning("Document processing failed: id=%s code=%s", document.id, exc.error_code)
        raise
    except Exception as exc:  # noqa: BLE001
        _mark_failed(db, document, "Document processing failed.")
        logger.exception("Unexpected error processing document id=%s: %s", document.id, type(exc).__name__)
        raise DocumentProcessingError() from exc


def _ingest_parsed_document(db: Session, document: Document, parsed: ParsedDocument) -> int:
    """Chunk, embed and store vectors for a parsed document.

    Wired to the real chunking + embedding + pgvector pipeline in Phase 4.
    """
    from app.services.ingestion_service import ingest_document

    return ingest_document(db, document, parsed)


# NOTE: ``app.services.ingestion_service`` is implemented in Phase 4. Until then a
# lightweight placeholder module provides ``ingest_document`` returning 0 chunks so
# the upload pipeline is exercisable end-to-end.


def _mark_failed(db: Session, document: Document, message: str) -> None:
    try:
        document.status = STATUS_FAILED
        document.error_message = message[:1000]
        db.commit()
    except Exception:  # noqa: BLE001 - never mask the original error
        db.rollback()


def list_documents(db: Session, user_id: uuid.UUID) -> list[Document]:
    stmt = (
        select(Document)
        .where(Document.user_id == user_id)
        .order_by(Document.created_at.desc())
    )
    return list(db.execute(stmt).scalars().all())


def get_document(db: Session, user_id: uuid.UUID, document_id: uuid.UUID) -> Document:
    document = db.get(Document, document_id)
    # 404 (not 403) so we don't reveal another user's document existence.
    if document is None or document.user_id != user_id:
        raise NotFoundError("Document not found.")
    return document


def delete_document(db: Session, user_id: uuid.UUID, document_id: uuid.UUID) -> None:
    document = get_document(db, user_id, document_id)

    # Remove stored file if present.
    stored = get_stored_file(document)
    if stored is not None:
        try:
            stored.unlink()
        except OSError:
            logger.warning("Could not delete stored file for document id=%s", document_id)

    # Chunks are removed via ON DELETE CASCADE.
    db.delete(document)
    db.commit()
    logger.info("Document deleted: id=%s", document_id)

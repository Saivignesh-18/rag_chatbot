"""Original-file storage backend.

Stores the raw uploaded files that back the "View"/preview action. Two backends:

- ``disk`` (default): local filesystem at ``settings.upload_storage_dir`` — ideal
  for local development.
- ``supabase``: a Supabase Storage **private bucket** (default name ``Documents``),
  used in production. Render Free's local disk is ephemeral, so originals must live
  in durable object storage.

Supabase access uses the Storage REST API over ``httpx`` with the service-role key
(no extra SDK dependency). Every operation degrades gracefully and never logs keys.
If ``supabase`` is selected but not configured, we fall back to local disk with a
warning so a misconfigured environment still works.
"""
from __future__ import annotations

import uuid
from pathlib import Path

import httpx

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_MEDIA_TYPES = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".txt": "text/plain; charset=utf-8",
}

_TIMEOUT = 30.0


def media_type_for(filename: str) -> str:
    """Best-effort content type for inline serving."""
    ext = Path(filename or "").suffix.lower()
    return _MEDIA_TYPES.get(ext, "application/octet-stream")


def object_key(document_id: uuid.UUID, ext: str) -> str:
    """Stable storage key for a document (schema-compatible: id + extension)."""
    return f"{document_id}{ext}"


def _use_supabase() -> bool:
    if not settings.use_supabase_storage:
        return False
    if not settings.supabase_storage_configured:
        logger.warning(
            "UPLOAD_STORAGE_BACKEND=supabase but SUPABASE_URL / "
            "SUPABASE_SERVICE_ROLE_KEY are not set; falling back to local disk."
        )
        return False
    return True


# --- local disk -----------------------------------------------------------
def _storage_dir() -> Path:
    path = Path(settings.upload_storage_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _disk_path(key: str) -> Path:
    return _storage_dir() / key


# --- supabase storage REST -------------------------------------------------
def _sb_object_url(key: str) -> str:
    base = settings.supabase_url.rstrip("/")
    return f"{base}/storage/v1/object/{settings.supabase_bucket}/{key}"


def _sb_headers() -> dict[str, str]:
    token = settings.supabase_service_role_key
    return {"Authorization": f"Bearer {token}", "apikey": token}


# --- public API ------------------------------------------------------------
def save(document_id: uuid.UUID, ext: str, data: bytes) -> None:
    """Persist original bytes. Raises on a hard Supabase failure (disk writes raise
    their own OSError), so the caller can mark the document failed."""
    key = object_key(document_id, ext)
    if _use_supabase():
        headers = _sb_headers() | {"content-type": media_type_for(key), "x-upsert": "true"}
        resp = httpx.post(_sb_object_url(key), content=data, headers=headers, timeout=_TIMEOUT)
        if resp.status_code >= 400:
            raise RuntimeError(f"Supabase upload failed (HTTP {resp.status_code}).")
        logger.info("Stored original in Supabase bucket=%s key=%s", settings.supabase_bucket, key)
        return
    _disk_path(key).write_bytes(data)


def local_path(document_id: uuid.UUID, ext: str) -> Path | None:
    """Local filesystem path if present (disk backend); ``None`` for Supabase."""
    if _use_supabase():
        return None
    path = _disk_path(object_key(document_id, ext))
    return path if path.exists() else None


def fetch_bytes(document_id: uuid.UUID, ext: str) -> bytes | None:
    """Return the stored bytes, or ``None`` if missing/unreachable."""
    key = object_key(document_id, ext)
    if _use_supabase():
        try:
            resp = httpx.get(_sb_object_url(key), headers=_sb_headers(), timeout=_TIMEOUT)
        except Exception as exc:  # noqa: BLE001 - never break the request
            logger.warning("Supabase download error (%s).", type(exc).__name__)
            return None
        return resp.content if resp.status_code < 400 else None
    path = _disk_path(key)
    return path.read_bytes() if path.exists() else None


def delete(document_id: uuid.UUID, ext: str) -> None:
    """Best-effort delete of the stored original (never raises)."""
    key = object_key(document_id, ext)
    if _use_supabase():
        try:
            httpx.request("DELETE", _sb_object_url(key), headers=_sb_headers(), timeout=_TIMEOUT)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Supabase delete error (%s).", type(exc).__name__)
        return
    path = _disk_path(key)
    try:
        if path.exists():
            path.unlink()
    except OSError:
        logger.warning("Could not delete stored file key=%s", key)

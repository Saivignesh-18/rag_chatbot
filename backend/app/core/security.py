"""Security helpers: safe filenames and upload validation.

Uploaded filenames are never trusted. We derive a safe, sanitised name and
validate extension, size and (lightweight) content signatures.
"""
from __future__ import annotations

import os
import re
import unicodedata

from app.core.config import settings
from app.core.exceptions import (
    EmptyFileError,
    FileTooLargeError,
    UnsupportedFileTypeError,
)

_SAFE_CHARS = re.compile(r"[^A-Za-z0-9._-]+")
_MULTI_DASH = re.compile(r"[-_]{2,}")
_MAX_NAME_LEN = 200


def sanitize_filename(filename: str | None) -> str:
    """Return a safe basename with no path components or dangerous characters."""
    if not filename:
        return "document"

    # Drop any directory components (defends against path traversal).
    name = filename.replace("\\", "/").split("/")[-1]
    name = os.path.basename(name)

    # Normalise unicode and strip control characters.
    name = unicodedata.normalize("NFKD", name)
    name = "".join(ch for ch in name if ord(ch) >= 32)

    root, ext = os.path.splitext(name)
    # Sanitise the extension too: keep only alphanumerics (drops trailing spaces,
    # stray punctuation, etc.) so extension checks remain reliable.
    ext_alnum = re.sub(r"[^A-Za-z0-9]", "", ext).lower()
    ext = f".{ext_alnum}" if ext_alnum else ""

    root = _SAFE_CHARS.sub("-", root).strip("-_.")
    root = _MULTI_DASH.sub("-", root)
    if not root:
        root = "document"

    root = root[:_MAX_NAME_LEN]
    return f"{root}{ext}"


def get_extension(filename: str) -> str:
    return os.path.splitext(filename or "")[1].lower()


# Minimal content signatures for defence-in-depth (not a substitute for parsing).
def _looks_like_pdf(data: bytes) -> bool:
    return data[:5] == b"%PDF-"


def _looks_like_zip(data: bytes) -> bool:
    # DOCX is a ZIP container.
    return data[:2] == b"PK"


def validate_upload(original_filename: str | None, data: bytes) -> tuple[str, str]:
    """Validate an uploaded file's size, extension and basic signature.

    Returns ``(file_type, safe_filename)`` or raises an :class:`AppError`.
    """
    if not data:
        raise EmptyFileError()

    if len(data) > settings.max_file_size_bytes:
        raise FileTooLargeError(
            f"The uploaded file exceeds the maximum allowed size of {settings.max_file_size_mb} MB."
        )

    safe_name = sanitize_filename(original_filename)
    ext = get_extension(safe_name)

    file_type = settings.ALLOWED_EXTENSIONS.get(ext)
    if file_type is None:
        raise UnsupportedFileTypeError()

    # Lightweight signature checks (txt is unconstrained).
    if file_type == "pdf" and not _looks_like_pdf(data):
        raise UnsupportedFileTypeError("File does not appear to be a valid PDF.")
    if file_type == "docx" and not _looks_like_zip(data):
        raise UnsupportedFileTypeError("File does not appear to be a valid DOCX.")

    return file_type, safe_name

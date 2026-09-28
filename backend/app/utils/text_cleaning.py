"""Text cleaning utilities used after extraction and before chunking."""
from __future__ import annotations

import re

_NULL = "\x00"
# Collapse 3+ newlines to a paragraph break; collapse runs of spaces/tabs.
_MULTI_NEWLINE = re.compile(r"\n{3,}")
_TRAILING_SPACES = re.compile(r"[ \t]+(\n)")
_MULTI_SPACE = re.compile(r"[ \t]{2,}")
# Control chars except tab/newline/carriage-return.
_CONTROL = re.compile(r"[\x01-\x08\x0b\x0c\x0e-\x1f]")


def clean_text(text: str) -> str:
    """Normalise whitespace and strip control characters while keeping structure."""
    if not text:
        return ""

    text = text.replace(_NULL, " ")
    # Normalise line endings.
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = _CONTROL.sub("", text)
    text = _TRAILING_SPACES.sub(r"\1", text)
    text = _MULTI_SPACE.sub(" ", text)
    text = _MULTI_NEWLINE.sub("\n\n", text)
    return text.strip()


def normalize_whitespace(text: str) -> str:
    """Collapse all whitespace to single spaces (useful for previews)."""
    return re.sub(r"\s+", " ", text or "").strip()

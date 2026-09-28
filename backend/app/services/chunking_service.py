"""Chunking service.

Splits cleaned, page-aware text into overlapping chunks suitable for embedding.
Chunk size and overlap are configurable. Page numbers are preserved from the
parsed segments so citations remain accurate.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.core.config import settings
from app.services.document_parser import ParsedDocument


@dataclass
class Chunk:
    index: int
    page_number: int | None
    content: str


def split_text(text: str, size: int, overlap: int) -> list[str]:
    """Split ``text`` into ~``size``-character chunks with ``overlap`` characters.

    Chunk boundaries are snapped to the nearest whitespace/newline (when one is
    reasonably close) to avoid cutting words mid-token.
    """
    text = (text or "").strip()
    if not text:
        return []

    size = max(1, size)
    overlap = max(0, min(overlap, size - 1))

    if len(text) <= size:
        return [text]

    chunks: list[str] = []
    start = 0
    n = len(text)
    # Only search for a boundary in the latter part of the window.
    min_boundary_offset = int(size * 0.6)

    while start < n:
        end = min(start + size, n)
        if end < n:
            search_from = start + min_boundary_offset
            boundary = max(text.rfind(" ", search_from, end), text.rfind("\n", search_from, end))
            if boundary > start:
                end = boundary
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= n:
            break
        start = max(end - overlap, start + 1)

    return chunks


def chunk_parsed_document(parsed: ParsedDocument) -> list[Chunk]:
    """Produce ordered chunks across all page segments of a parsed document."""
    chunks: list[Chunk] = []
    index = 0
    for segment in parsed.segments:
        for piece in split_text(segment.text, settings.chunk_size, settings.chunk_overlap):
            chunks.append(Chunk(index=index, page_number=segment.page_number, content=piece))
            index += 1
    return chunks

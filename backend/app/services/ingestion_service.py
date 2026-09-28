"""Ingestion pipeline: chunk -> embed -> store vectors in PostgreSQL/pgvector."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.services.chunking_service import chunk_parsed_document
from app.services.document_parser import ParsedDocument
from app.services.embedding_service import embedding_service

logger = get_logger(__name__)


def ingest_document(db: Session, document: Document, parsed: ParsedDocument) -> int:
    """Chunk the parsed document, embed each chunk and persist vectors.

    Returns the number of chunks stored. The caller commits the transaction.
    """
    chunks = chunk_parsed_document(parsed)
    if not chunks:
        logger.warning("No chunks produced for document id=%s", document.id)
        return 0

    logger.info("Chunked document id=%s into %d chunks; generating embeddings...", document.id, len(chunks))

    # Embed all chunk texts (fastembed batches internally).
    vectors = embedding_service.embed_documents([c.content for c in chunks])
    if len(vectors) != len(chunks):  # pragma: no cover - defensive
        raise ValueError(f"Embedding count {len(vectors)} != chunk count {len(chunks)}")

    rows = [
        DocumentChunk(
            document_id=document.id,
            chunk_index=chunk.index,
            content=chunk.content,
            page_number=chunk.page_number,
            embedding=vector,
        )
        for chunk, vector in zip(chunks, vectors)
    ]
    db.add_all(rows)
    db.flush()  # persist within the caller's transaction

    logger.info("Stored %d chunks with embeddings for document id=%s", len(rows), document.id)
    return len(rows)

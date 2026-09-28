"""Retrieval service.

Embeds a user question with the SAME model used for documents, performs a
pgvector cosine-similarity search, and applies a configurable similarity
threshold. This is real vector retrieval - no keyword matching.

Cosine similarity is derived from pgvector's cosine *distance*::

    similarity = 1 - cosine_distance      (range roughly [-1, 1])
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging import get_logger
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.services.embedding_service import embedding_service

logger = get_logger(__name__)


@dataclass
class RetrievedChunk:
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    document_name: str
    content: str
    page_number: int | None
    chunk_index: int
    similarity_score: float


@dataclass
class RetrievalResult:
    query: str
    accepted: list[RetrievedChunk] = field(default_factory=list)
    candidates: list[RetrievedChunk] = field(default_factory=list)
    threshold: float = 0.0
    top_k: int = 0

    @property
    def has_relevant(self) -> bool:
        return len(self.accepted) > 0

    @property
    def max_similarity(self) -> float:
        return max((c.similarity_score for c in self.candidates), default=0.0)


def retrieve(
    db: Session,
    query: str,
    *,
    user_id: uuid.UUID | None = None,
    document_ids: list[uuid.UUID] | None = None,
    top_k: int | None = None,
    threshold: float | None = None,
) -> RetrievalResult:
    """Retrieve the most similar chunks to ``query`` and gate them by threshold.

    Retrieval is restricted at the DATABASE-QUERY level:
    - ``user_id``      : only chunks from documents owned by this user.
    - ``document_ids`` : only chunks from these specific documents (the session's
                          selected scope). When None, all of the user's documents
                          are searched. When an empty list, nothing is returned.

    We never over-fetch and filter afterwards - unselected documents cannot
    contribute to the result set.
    """
    top_k = top_k if top_k is not None else settings.top_k
    threshold = threshold if threshold is not None else settings.similarity_threshold

    query = (query or "").strip()
    if not query:
        return RetrievalResult(query=query, threshold=threshold, top_k=top_k)

    # An explicit empty scope means "no documents selected" -> no results.
    if document_ids is not None and len(document_ids) == 0:
        return RetrievalResult(query=query, threshold=threshold, top_k=top_k)

    query_vector = embedding_service.embed_query(query)

    distance = DocumentChunk.embedding.cosine_distance(query_vector).label("distance")
    stmt = (
        select(
            DocumentChunk.id,
            DocumentChunk.document_id,
            DocumentChunk.content,
            DocumentChunk.page_number,
            DocumentChunk.chunk_index,
            Document.filename,
            distance,
        )
        .join(Document, Document.id == DocumentChunk.document_id)
    )
    if user_id is not None:
        stmt = stmt.where(Document.user_id == user_id)
    if document_ids is not None:
        stmt = stmt.where(Document.id.in_(document_ids))
    stmt = stmt.order_by(distance).limit(top_k)

    rows = db.execute(stmt).all()

    candidates: list[RetrievedChunk] = []
    for row in rows:
        similarity = 1.0 - float(row.distance)
        candidates.append(
            RetrievedChunk(
                chunk_id=row.id,
                document_id=row.document_id,
                document_name=row.filename,
                content=row.content,
                page_number=row.page_number,
                chunk_index=row.chunk_index,
                similarity_score=round(similarity, 4),
            )
        )

    accepted = [c for c in candidates if c.similarity_score >= threshold]

    scope = "all-user-docs" if document_ids is None else f"{len(document_ids)}-selected"
    logger.info(
        "Retrieval completed: scope=%s candidates=%d accepted=%d "
        "top_k=%d threshold=%.2f max_sim=%.4f",
        scope, len(candidates), len(accepted), top_k, threshold,
        candidates[0].similarity_score if candidates else 0.0,
    )

    return RetrievalResult(
        query=query,
        accepted=accepted,
        candidates=candidates,
        threshold=threshold,
        top_k=top_k,
    )

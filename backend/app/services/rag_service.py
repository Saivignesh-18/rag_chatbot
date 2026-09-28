"""RAG orchestration with per-user isolation and per-session document scope.

Pipeline:

    question -> embedding -> pgvector search restricted to (user's) SELECTED
    documents (from chat_session_documents) -> threshold gate
        -> (relevant)     build context -> Groq -> grounded answer + citations
        -> (not relevant) standard refusal (no LLM call)

Security invariants (the database is the source of truth):
- Every session and document is verified to belong to the authenticated user.
- Selected document IDs are read from the DB by session_id, never from the client.
- Vector search is filtered by user_id AND selected document IDs at query level.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import BadRequestError, ForbiddenError, NotFoundError
from app.core.logging import get_logger
from app.models.chat_message import ROLE_ASSISTANT, ROLE_USER, ChatMessage
from app.models.chat_session import ChatSession
from app.models.chat_session_document import ChatSessionDocument
from app.models.document import Document
from app.models.user import User
from app.services.llm_router import llm_router
from app.services.prompt_service import (
    REFUSAL_MESSAGE,
    SYSTEM_PROMPT,
    build_context,
    build_user_prompt,
    sanitize_answer,
)
from app.services.retrieval_service import RetrievedChunk, retrieve
from app.services.smalltalk_service import detect_smalltalk

logger = get_logger(__name__)


@dataclass
class Source:
    document_id: uuid.UUID
    document_name: str
    page_number: int | None
    chunk_id: uuid.UUID
    similarity_score: float

    def to_json(self) -> dict:
        return {
            "document_id": str(self.document_id),
            "document_name": self.document_name,
            "page_number": self.page_number,
            "chunk_id": str(self.chunk_id),
            "similarity_score": self.similarity_score,
        }


@dataclass
class ChatAnswer:
    answer: str
    sources: list[Source] = field(default_factory=list)
    session_id: uuid.UUID | None = None
    refused: bool = False


# ---------------------------------------------------------------------------
# Ownership-checked session helpers
# ---------------------------------------------------------------------------
def _owned_session(db: Session, user: User, session_id: uuid.UUID) -> ChatSession:
    session = db.get(ChatSession, session_id)
    # 404 (not 403) so we don't reveal whether another user's session exists.
    if session is None or session.user_id != user.id:
        raise NotFoundError("Chat session not found.")
    return session


def _validate_document_ownership(db: Session, user: User, document_ids: list[uuid.UUID]) -> list[uuid.UUID]:
    """Return the unique, verified document IDs owned by `user`.

    Raises ForbiddenError if any requested document does not belong to the user.
    """
    unique_ids = list(dict.fromkeys(document_ids))  # de-dup, preserve order
    if not unique_ids:
        return []
    owned = set(
        db.execute(
            select(Document.id).where(Document.id.in_(unique_ids), Document.user_id == user.id)
        ).scalars().all()
    )
    missing = [d for d in unique_ids if d not in owned]
    if missing:
        raise ForbiddenError("One or more selected documents do not belong to you.")
    return unique_ids


def get_selected_document_ids(db: Session, session_id: uuid.UUID) -> list[uuid.UUID]:
    return list(
        db.execute(
            select(ChatSessionDocument.document_id).where(ChatSessionDocument.session_id == session_id)
        ).scalars().all()
    )


def _set_session_documents(db: Session, session_id: uuid.UUID, document_ids: list[uuid.UUID]) -> None:
    db.execute(ChatSessionDocument.__table__.delete().where(ChatSessionDocument.session_id == session_id))
    for doc_id in document_ids:
        db.add(ChatSessionDocument(session_id=session_id, document_id=doc_id))


# ---------------------------------------------------------------------------
# Public session operations
# ---------------------------------------------------------------------------
def create_session(
    db: Session, user: User, document_ids: list[uuid.UUID], title: str | None = None
) -> ChatSession:
    verified = _validate_document_ownership(db, user, document_ids)
    session = ChatSession(user_id=user.id, title=title)
    db.add(session)
    db.flush()
    _set_session_documents(db, session.id, verified)
    db.commit()
    db.refresh(session)
    logger.info("Chat session created: id=%s user=%s docs=%d", session.id, user.id, len(verified))
    return session


def update_session_documents(
    db: Session, user: User, session_id: uuid.UUID, document_ids: list[uuid.UUID]
) -> ChatSession:
    session = _owned_session(db, user, session_id)
    verified = _validate_document_ownership(db, user, document_ids)
    _set_session_documents(db, session.id, verified)
    db.commit()
    db.refresh(session)
    logger.info("Chat session scope updated: id=%s docs=%d", session.id, len(verified))
    return session


def list_sessions(db: Session, user: User) -> list[ChatSession]:
    stmt = select(ChatSession).where(ChatSession.user_id == user.id).order_by(ChatSession.updated_at.desc())
    return list(db.execute(stmt).scalars().all())


def get_session(db: Session, user: User, session_id: uuid.UUID) -> ChatSession:
    return _owned_session(db, user, session_id)


def get_session_messages(db: Session, user: User, session_id: uuid.UUID) -> list[ChatMessage]:
    session = _owned_session(db, user, session_id)
    return list(session.messages)


def delete_session(db: Session, user: User, session_id: uuid.UUID) -> None:
    session = _owned_session(db, user, session_id)
    db.delete(session)
    db.commit()
    logger.info("Chat session deleted: id=%s", session_id)


def document_count(db: Session, session_id: uuid.UUID) -> int:
    return db.scalar(
        select(func.count()).select_from(ChatSessionDocument).where(
            ChatSessionDocument.session_id == session_id
        )
    ) or 0


# ---------------------------------------------------------------------------
# Answering
# ---------------------------------------------------------------------------
def _build_sources(chunks: list[RetrievedChunk]) -> list[Source]:
    """Deduplicate by (document, page), keeping the highest-similarity chunk."""
    best: dict[tuple[uuid.UUID, int | None], RetrievedChunk] = {}
    for chunk in chunks:
        key = (chunk.document_id, chunk.page_number)
        current = best.get(key)
        if current is None or chunk.similarity_score > current.similarity_score:
            best[key] = chunk
    sources = [
        Source(
            document_id=c.document_id,
            document_name=c.document_name,
            page_number=c.page_number,
            chunk_id=c.chunk_id,
            similarity_score=c.similarity_score,
        )
        for c in best.values()
    ]
    sources.sort(key=lambda s: s.similarity_score, reverse=True)
    return sources


def answer_question(db: Session, user: User, session_id: uuid.UUID, question: str) -> ChatAnswer:
    question = (question or "").strip()
    if not question:
        raise BadRequestError("Question must not be empty.")

    # Verify session ownership and derive scope from the database.
    session = _owned_session(db, user, session_id)

    # Greetings / acknowledgements are not document questions: reply in a
    # friendly way and skip retrieval + the document-only refusal entirely.
    smalltalk_reply = detect_smalltalk(question)
    if smalltalk_reply is not None:
        if not session.title:
            session.title = question[:60] + ("..." if len(question) > 60 else "")
        db.add(ChatMessage(session_id=session.id, role=ROLE_USER, content=question))
        db.add(ChatMessage(session_id=session.id, role=ROLE_ASSISTANT, content=smalltalk_reply))
        db.commit()
        logger.info("Chat request handled as small talk (session=%s).", session.id)
        return ChatAnswer(answer=smalltalk_reply, sources=[], session_id=session.id, refused=False)

    selected_ids = get_selected_document_ids(db, session.id)
    # A session with an explicit selection restricts to it; a session with no
    # selection searches all of the user's documents.
    scope_ids: list[uuid.UUID] | None = selected_ids if selected_ids else None

    logger.info(
        "Chat request: user=%s session=%s selected_docs=%d question_len=%d",
        user.id, session.id, len(selected_ids), len(question),
    )

    result = retrieve(db, question, user_id=user.id, document_ids=scope_ids)

    if not result.has_relevant:
        logger.info("No chunks passed threshold (max_sim=%.4f) -> refusing.", result.max_similarity)
        answer_text = REFUSAL_MESSAGE
        sources: list[Source] = []
        refused = True
    else:
        context = build_context(result.accepted)
        # The prompt (system + user + retrieved context) is built ONCE here and
        # passed to the router, so Groq and any fallback (Gemini) receive exactly
        # the same document-only context and selected-document scope.
        completion = llm_router.generate(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=build_user_prompt(question, context),
        )
        answer_text = sanitize_answer(completion.content)
        sources = _build_sources(result.accepted)
        refused = False
        logger.info(
            "Chat answer generated with %d source(s) via provider=%s.",
            len(sources), completion.provider,
        )

    # Persist messages; set a title from the first question if unset.
    if not session.title:
        session.title = question[:60] + ("..." if len(question) > 60 else "")
    db.add(ChatMessage(session_id=session.id, role=ROLE_USER, content=question))
    db.add(
        ChatMessage(
            session_id=session.id,
            role=ROLE_ASSISTANT,
            content=answer_text,
            sources=[s.to_json() for s in sources] if sources else None,
        )
    )
    db.commit()

    logger.info("Chat request status: OK (session=%s, refused=%s)", session.id, refused)
    return ChatAnswer(answer=answer_text, sources=sources, session_id=session.id, refused=refused)

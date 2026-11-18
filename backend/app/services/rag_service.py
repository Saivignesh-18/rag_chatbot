"""RAG orchestration with per-user isolation and per-session document scope.

Pipeline:

    question -> NLP preprocessing (normalize / spell-correct / intent /
                 follow-up resolution / query expansion)
             -> basic conversational intent? -> canned reply (no retrieval/LLM)
             -> else embedding -> pgvector search restricted to (user's) SELECTED
                 documents -> relevance check with graceful query fallback
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
from app.services.retrieval_service import RetrievalResult, RetrievedChunk, retrieve
from app.nlp import preprocess_query

logger = get_logger(__name__)

# How many recent messages to load for follow-up / feedback / clarification.
_HISTORY_TURNS = 6


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
    # NLP preprocessing metadata (additive; defaults preserve backward compatibility).
    original_query: str | None = None
    corrected_query: str | None = None
    detected_intent: str | None = None
    preprocessing_applied: bool = False
    response_source: str = "rag"
    retrieval_confidence: float | None = None


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


def _recent_history(db: Session, session_id: uuid.UUID, limit: int = _HISTORY_TURNS) -> list[tuple[str, str]]:
    """Return the most recent prior messages as chronological (role, content).

    Used only for follow-up resolution; the CURRENT user message has not been
    persisted yet, so this returns strictly prior turns.
    """
    rows = db.execute(
        select(ChatMessage.role, ChatMessage.content)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at.desc(), ChatMessage.id.desc())
        .limit(limit)
    ).all()
    return [(row.role, row.content) for row in reversed(rows)]


def _retrieve_with_fallback(
    db: Session,
    *,
    candidates: list[str],
    user_id: uuid.UUID,
    scope_ids: list[uuid.UUID] | None,
) -> tuple[RetrievalResult | None, float]:
    """Try each candidate query in order and return the first relevant result.

    Candidates are tried best-first (expanded -> corrected -> original). This
    prevents a weak first query from prematurely returning "no information found"
    when a simpler query would have retrieved evidence. Blank/duplicate queries
    are skipped. Returns ``(result, confidence)`` where ``confidence`` is the best
    observed max-similarity across attempts (0..1).
    """
    seen: set[str] = set()
    best_result: RetrievalResult | None = None
    best_confidence = 0.0
    for raw in candidates:
        query = (raw or "").strip()
        key = query.lower()
        if not query or key in seen:
            continue
        seen.add(key)
        result = retrieve(db, query, user_id=user_id, document_ids=scope_ids)
        if result.max_similarity > best_confidence:
            best_confidence = result.max_similarity
            best_result = result
        if result.has_relevant:
            return result, round(result.max_similarity, 4)
    return best_result, round(best_confidence, 4)


def answer_question(db: Session, user: User, session_id: uuid.UUID, question: str) -> ChatAnswer:
    question = (question or "").strip()
    if not question:
        raise BadRequestError("Question must not be empty.")

    # Verify session ownership and derive scope from the database.
    session = _owned_session(db, user, session_id)

    # Recent prior turns enable follow-up / feedback / clarification handling.
    history = _recent_history(db, session.id)

    # --- NLP preprocessing: normalize -> spell-correct -> intent -> context ---
    pre = preprocess_query(question, history=history)

    # Basic conversational intents (greeting / gratitude / goodbye / help /
    # positive feedback) AND unresolvable follow-ups (which become a clarification
    # question) are answered directly, WITHOUT embeddings, vector search or any LLM.
    if pre.is_basic and pre.basic_response:
        if not session.title:
            session.title = question[:60] + ("..." if len(question) > 60 else "")
        db.add(ChatMessage(session_id=session.id, role=ROLE_USER, content=question))
        db.add(ChatMessage(session_id=session.id, role=ROLE_ASSISTANT, content=pre.basic_response))
        db.commit()
        logger.info("Chat answered by NLP layer (intent=%s, session=%s).", pre.intent, session.id)
        return ChatAnswer(
            answer=pre.basic_response,
            sources=[],
            session_id=session.id,
            refused=False,
            original_query=question,
            corrected_query=pre.corrected,
            detected_intent=pre.intent,
            preprocessing_applied=pre.preprocessing_applied,
            response_source=pre.response_source,
            retrieval_confidence=None,
        )

    selected_ids = get_selected_document_ids(db, session.id)
    # A session with an explicit selection restricts to it; a session with no
    # selection searches all of the user's documents.
    scope_ids: list[uuid.UUID] | None = selected_ids if selected_ids else None

    logger.info(
        "Chat request: user=%s session=%s selected_docs=%d intent=%s followup=%s corrected=%s informal=%s",
        user.id, session.id, len(selected_ids), pre.intent, pre.is_followup,
        bool(pre.corrections), pre.informal,
    )

    # Retrieve with a relevance check and graceful query fallback. The expanded
    # (synonym/Telgish-enriched) query is tried first for recall; we then fall
    # back to the plain corrected and original text.
    result, retrieval_confidence = _retrieve_with_fallback(
        db,
        candidates=[pre.retrieval_query, pre.corrected, pre.original, question],
        user_id=user.id,
        scope_ids=scope_ids,
    )

    if result is None or not result.has_relevant:
        max_sim = result.max_similarity if result is not None else 0.0
        logger.info("No chunks passed threshold (best_sim=%.4f) -> refusing.", max_sim)
        answer_text = REFUSAL_MESSAGE
        sources: list[Source] = []
        refused = True
    else:
        context = build_context(result.accepted)
        # For a follow-up asking to expand, nudge the model to add detail - still
        # strictly from the retrieved context (grounding is unchanged).
        extra_instruction = (
            "The user is following up on the previous answer and asked for more "
            "detail. Expand with additional specifics, using ONLY the context."
            if pre.elaborate
            else ""
        )
        # The prompt uses the NATURAL question (resolved for follow-ups), NOT the
        # expanded keyword string, so Groq and any Gemini fallback receive an
        # identical, focused, document-only prompt.
        completion = llm_router.generate(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=build_user_prompt(
                pre.prompt_question or question, context, extra_instruction=extra_instruction
            ),
        )
        answer_text = sanitize_answer(completion.content)
        sources = _build_sources(result.accepted)
        refused = False
        logger.info(
            "Chat answer generated with %d source(s) via provider=%s (confidence=%.4f).",
            len(sources), completion.provider, retrieval_confidence,
        )

    # Persist messages; set a title from the first question if unset. The user
    # message stores the ORIGINAL text — we never replace what the user typed.
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
    return ChatAnswer(
        answer=answer_text,
        sources=sources,
        session_id=session.id,
        refused=refused,
        original_query=question,
        corrected_query=pre.corrected,
        detected_intent=pre.intent,
        preprocessing_applied=pre.preprocessing_applied,
        response_source=pre.response_source,
        retrieval_confidence=retrieval_confidence,
    )

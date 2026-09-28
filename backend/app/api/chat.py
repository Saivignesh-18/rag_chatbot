"""Chat endpoints: sessions (scoped to selected documents) and Q&A.

All endpoints require authentication and are scoped to the current user. The
document scope for answering is derived from the database (chat_session_documents),
never from the chat request body.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.config import settings
from app.core.logging import get_logger
from app.core.rate_limit import limiter
from app.db.database import get_db
from app.models.user import User
from app.schemas.chat import (
    ChatMessageOut,
    ChatRequest,
    ChatResponse,
    ChatSessionDetailResponse,
    ChatSessionListResponse,
    DeleteResponse,
    SessionCreateRequest,
    SessionResponse,
    Source,
    UpdateScopeRequest,
    session_to_out,
)
from app.services import rag_service

logger = get_logger(__name__)

router = APIRouter(tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
@limiter.limit(settings.rate_limit_chat)
async def chat(
    request: Request,
    payload: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ChatResponse:
    """Answer a question strictly from the session's selected documents."""
    result = rag_service.answer_question(db, current_user, payload.session_id, payload.question)
    return ChatResponse(
        answer=result.answer,
        sources=[Source(**s.to_json()) for s in result.sources],
        session_id=result.session_id,
    )


@router.post("/chat/sessions", response_model=SessionResponse)
async def create_session(
    payload: SessionCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SessionResponse:
    """Create a chat session scoped to the selected documents."""
    session = rag_service.create_session(db, current_user, payload.document_ids, payload.title)
    return SessionResponse(session=session_to_out(session))


@router.patch("/chat/sessions/{session_id}/documents", response_model=SessionResponse)
async def update_scope(
    session_id: uuid.UUID,
    payload: UpdateScopeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SessionResponse:
    """Change which documents a session is scoped to (preserves chat history)."""
    session = rag_service.update_session_documents(db, current_user, session_id, payload.document_ids)
    return SessionResponse(session=session_to_out(session))


@router.get("/chat/sessions", response_model=ChatSessionListResponse)
async def list_sessions(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
) -> ChatSessionListResponse:
    sessions = rag_service.list_sessions(db, current_user)
    return ChatSessionListResponse(
        sessions=[session_to_out(s) for s in sessions],
        total=len(sessions),
    )


@router.get("/chat/sessions/{session_id}", response_model=ChatSessionDetailResponse)
async def get_session(
    session_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ChatSessionDetailResponse:
    session = rag_service.get_session(db, current_user, session_id)
    messages = rag_service.get_session_messages(db, current_user, session_id)
    return ChatSessionDetailResponse(
        session=session_to_out(session),
        messages=[ChatMessageOut.model_validate(m) for m in messages],
    )


@router.delete("/chat/sessions/{session_id}", response_model=DeleteResponse)
async def delete_session(
    session_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DeleteResponse:
    rag_service.delete_session(db, current_user, session_id)
    return DeleteResponse(message="Chat session deleted")

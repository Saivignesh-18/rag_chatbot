"""Per-user dashboard statistics (real data, authenticated)."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.db.database import get_db
from app.models.chat_message import ROLE_USER, ChatMessage
from app.models.chat_session import ChatSession
from app.models.chat_session_document import ChatSessionDocument
from app.models.document import STATUS_COMPLETED, Document
from app.models.document_chunk import DocumentChunk
from app.models.user import User

router = APIRouter(tags=["stats"])


class StatsResponse(BaseModel):
    success: bool = True
    documents: int
    ready_documents: int
    indexed_chunks: int
    chat_sessions: int
    questions: int
    selected_documents: int


@router.get("/stats", response_model=StatsResponse)
async def get_stats(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
) -> StatsResponse:
    uid = current_user.id

    documents = db.scalar(
        select(func.count()).select_from(Document).where(Document.user_id == uid)
    ) or 0
    ready_documents = db.scalar(
        select(func.count()).select_from(Document).where(
            Document.user_id == uid, Document.status == STATUS_COMPLETED
        )
    ) or 0
    indexed_chunks = db.scalar(
        select(func.count())
        .select_from(DocumentChunk)
        .join(Document, Document.id == DocumentChunk.document_id)
        .where(Document.user_id == uid)
    ) or 0
    chat_sessions = db.scalar(
        select(func.count()).select_from(ChatSession).where(ChatSession.user_id == uid)
    ) or 0
    questions = db.scalar(
        select(func.count())
        .select_from(ChatMessage)
        .join(ChatSession, ChatSession.id == ChatMessage.session_id)
        .where(ChatSession.user_id == uid, ChatMessage.role == ROLE_USER)
    ) or 0
    selected_documents = db.scalar(
        select(func.count(func.distinct(ChatSessionDocument.document_id)))
        .select_from(ChatSessionDocument)
        .join(ChatSession, ChatSession.id == ChatSessionDocument.session_id)
        .where(ChatSession.user_id == uid)
    ) or 0

    return StatsResponse(
        documents=documents,
        ready_documents=ready_documents,
        indexed_chunks=indexed_chunks,
        chat_sessions=chat_sessions,
        questions=questions,
        selected_documents=selected_documents,
    )

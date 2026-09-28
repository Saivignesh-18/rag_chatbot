"""Pydantic schemas for chat endpoints."""
from __future__ import annotations

import datetime
import uuid

from pydantic import BaseModel, ConfigDict, Field


class ChatRequest(BaseModel):
    # session_id is required: the backend derives document scope from it.
    session_id: uuid.UUID
    question: str = Field(min_length=1, max_length=4000, examples=["What is the retirement age?"])


class SessionCreateRequest(BaseModel):
    document_ids: list[uuid.UUID] = Field(default_factory=list)
    title: str | None = None


class UpdateScopeRequest(BaseModel):
    document_ids: list[uuid.UUID] = Field(default_factory=list)


class Source(BaseModel):
    document_id: uuid.UUID
    document_name: str
    page_number: int | None = None
    chunk_id: uuid.UUID
    similarity_score: float


class ChatResponse(BaseModel):
    success: bool = True
    answer: str
    sources: list[Source] = []
    session_id: uuid.UUID


class SessionDocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    filename: str
    file_type: str
    status: str


class ChatMessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    role: str
    content: str
    sources: list[Source] | None = None
    created_at: datetime.datetime


class ChatSessionOut(BaseModel):
    id: uuid.UUID
    title: str | None = None
    created_at: datetime.datetime
    updated_at: datetime.datetime
    document_count: int = 0
    documents: list[SessionDocumentOut] = []


class ChatSessionListResponse(BaseModel):
    success: bool = True
    sessions: list[ChatSessionOut]
    total: int


class ChatSessionDetailResponse(BaseModel):
    success: bool = True
    session: ChatSessionOut
    messages: list[ChatMessageOut]


class SessionResponse(BaseModel):
    success: bool = True
    session: ChatSessionOut


class DeleteResponse(BaseModel):
    success: bool = True
    message: str = "Deleted successfully"


def session_to_out(session) -> ChatSessionOut:
    """Build a ChatSessionOut including its selected documents."""
    docs = [SessionDocumentOut.model_validate(d) for d in session.selected_documents]
    return ChatSessionOut(
        id=session.id,
        title=session.title,
        created_at=session.created_at,
        updated_at=session.updated_at,
        document_count=len(docs),
        documents=docs,
    )

"""Pydantic schemas for document endpoints."""
from __future__ import annotations

import datetime
import uuid

from pydantic import BaseModel, ConfigDict, Field


class DocumentOut(BaseModel):
    """Public representation of a document."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    filename: str
    file_type: str
    file_size: int
    status: str
    total_chunks: int
    page_count: int | None = None
    error_message: str | None = None
    created_at: datetime.datetime
    updated_at: datetime.datetime


class DocumentListResponse(BaseModel):
    success: bool = True
    documents: list[DocumentOut]
    total: int


class DocumentDetailResponse(BaseModel):
    success: bool = True
    document: DocumentOut


class UploadResponse(BaseModel):
    success: bool = True
    document_id: uuid.UUID
    filename: str
    total_chunks: int
    message: str = "Document processed successfully"


class DeleteResponse(BaseModel):
    success: bool = True
    message: str = "Document deleted successfully"


class ErrorResponse(BaseModel):
    """Consistent error envelope (documented for OpenAPI)."""

    success: bool = False
    message: str
    error_code: str = Field(examples=["DOCUMENT_PROCESSING_ERROR"])

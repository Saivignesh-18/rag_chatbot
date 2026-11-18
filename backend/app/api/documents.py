"""Document management endpoints (all require authentication + user scoping)."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, File, Request, UploadFile
from fastapi.responses import FileResponse, Response
from sqlalchemy.orm import Session

from app.core.auth import get_current_user, get_current_user_flexible
from app.core.config import settings
from app.core.exceptions import EmptyFileError, NotFoundError
from app.core.logging import get_logger
from app.core.rate_limit import limiter
from app.core.security import get_extension
from app.db.database import get_db
from app.models.user import User
from app.schemas.document import (
    DeleteResponse,
    DocumentDetailResponse,
    DocumentListResponse,
    DocumentOut,
    UploadResponse,
)
from app.services import document_service, storage_service

logger = get_logger(__name__)

router = APIRouter(prefix="/documents", tags=["documents"])

_READ_CAP = settings.max_file_size_bytes + 1024


@router.post("/upload", response_model=UploadResponse)
@limiter.limit(settings.rate_limit_upload)
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UploadResponse:
    """Upload, validate, extract and index a document owned by the current user."""
    data = await file.read(_READ_CAP)
    if not data:
        raise EmptyFileError()

    document = document_service.process_upload(db, file.filename, data, user_id=current_user.id)
    return UploadResponse(
        document_id=document.id,
        filename=document.filename,
        total_chunks=document.total_chunks,
        message="Document processed successfully",
    )


@router.get("", response_model=DocumentListResponse)
async def list_documents(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
) -> DocumentListResponse:
    documents = document_service.list_documents(db, current_user.id)
    return DocumentListResponse(
        documents=[DocumentOut.model_validate(d) for d in documents],
        total=len(documents),
    )


@router.get("/{document_id}", response_model=DocumentDetailResponse)
async def get_document(
    document_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DocumentDetailResponse:
    document = document_service.get_document(db, current_user.id, document_id)
    return DocumentDetailResponse(document=DocumentOut.model_validate(document))


@router.get("/{document_id}/file")
async def download_document(
    document_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_flexible),
) -> Response:
    """Return the original stored file (used for the 'View' action / source preview).

    Works with both storage backends: a local-disk original is streamed with
    ``FileResponse``; a Supabase-stored original is fetched and returned inline.
    """
    document = document_service.get_document(db, current_user.id, document_id)
    ext = get_extension(document.filename)
    path = storage_service.local_path(document.id, ext)
    if path is not None:
        return FileResponse(path=str(path), filename=document.filename, content_disposition_type="inline")
    data = storage_service.fetch_bytes(document.id, ext)
    if data is None:
        raise NotFoundError("Stored file not found for this document.")
    return Response(
        content=data,
        media_type=storage_service.media_type_for(document.filename),
        headers={"Content-Disposition": f'inline; filename="{document.filename}"'},
    )


@router.delete("/{document_id}", response_model=DeleteResponse)
async def delete_document(
    document_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DeleteResponse:
    document_service.delete_document(db, current_user.id, document_id)
    return DeleteResponse(message="Document deleted successfully")

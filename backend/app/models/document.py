"""Document model - one row per uploaded file."""
from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.document_chunk import DocumentChunk


# Processing lifecycle states.
STATUS_PENDING = "pending"
STATUS_PROCESSING = "processing"
STATUS_COMPLETED = "completed"
STATUS_FAILED = "failed"


class Document(Base, TimestampMixin):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # Owner. Nullable for migration safety; always set for newly uploaded documents.
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True
    )
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    file_type: Mapped[str] = mapped_column(String(16), nullable=False)  # pdf | docx | txt
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)  # bytes
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default=STATUS_PENDING, server_default=STATUS_PENDING
    )
    total_chunks: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    chunks: Mapped[list["DocumentChunk"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<Document {self.id} {self.filename!r} status={self.status}>"

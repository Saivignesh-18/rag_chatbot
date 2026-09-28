"""ChatSession model - groups a conversation's messages."""
from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.chat_message import ChatMessage
    from app.models.document import Document


class ChatSession(Base, TimestampMixin):
    __tablename__ = "chat_sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True
    )
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)

    messages: Mapped[list["ChatMessage"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="ChatMessage.created_at",
    )

    # Documents this session is scoped to (via chat_session_documents).
    selected_documents: Mapped[list["Document"]] = relationship(
        secondary="chat_session_documents",
        lazy="selectin",
        viewonly=False,
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<ChatSession {self.id}>"

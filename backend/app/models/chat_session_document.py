"""Association between a chat session and the documents it is scoped to.

This is the source of truth for a session's document scope. The chat request
only carries a session_id; the backend derives the selected document IDs from
this table (never trusting the client).
"""
from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class ChatSessionDocument(Base):
    __tablename__ = "chat_session_documents"

    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chat_sessions.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
    )

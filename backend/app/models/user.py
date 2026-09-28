"""User model - a Google account and/or an email+password account."""
from __future__ import annotations

import uuid

from sqlalchemy import String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base, TimestampMixin


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    profile_picture: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    # Google identity (nullable: email/password users have none).
    google_sub: Mapped[str | None] = mapped_column(String(255), unique=True, index=True, nullable=True)
    # bcrypt hash (nullable: Google-only users have none).
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)

    @property
    def provider(self) -> str:
        if self.google_sub and self.password_hash:
            return "Google + Email"
        if self.google_sub:
            return "Google"
        return "Email"

    def __repr__(self) -> str:  # pragma: no cover
        return f"<User {self.id} {self.email!r}>"

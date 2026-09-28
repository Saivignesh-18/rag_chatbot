"""Database engine, session management and initialisation.

Uses SQLAlchemy 2.0 style. The pgvector extension is enabled and tables are
created on startup via :func:`init_db`.
"""
from __future__ import annotations

import datetime
from collections.abc import Iterator

from sqlalchemy import DateTime, create_engine, func, text
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# pool_pre_ping avoids stale-connection errors after the DB restarts.
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    future=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


class TimestampMixin:
    """Adds server-managed created_at / updated_at columns."""

    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


def get_db() -> Iterator[Session]:
    """FastAPI dependency that yields a database session and always closes it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Enable pgvector and create all tables.

    Safe to call repeatedly (uses IF NOT EXISTS semantics).
    """
    # Import models so they register with Base.metadata before create_all.
    from app import models  # noqa: F401  (side-effect import)

    logger.info("Enabling pgvector extension and creating tables...")
    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))

    # Creates any missing tables (users, chat_session_documents, ...). Existing
    # tables are left untouched by create_all, so column additions are handled
    # by the idempotent migration below.
    Base.metadata.create_all(bind=engine)
    _run_lightweight_migrations()
    logger.info("Database initialised (tables ready).")


def _run_lightweight_migrations() -> None:
    """Idempotently add auth-related columns/indexes to pre-existing tables.

    Safe on both fresh databases (no-ops) and previously-created databases that
    predate multi-user support. Does NOT drop or modify existing data.
    """
    statements = [
        "ALTER TABLE documents ADD COLUMN IF NOT EXISTS user_id UUID",
        "ALTER TABLE chat_sessions ADD COLUMN IF NOT EXISTS user_id UUID",
        "CREATE INDEX IF NOT EXISTS ix_documents_user_id ON documents (user_id)",
        "CREATE INDEX IF NOT EXISTS ix_chat_sessions_user_id ON chat_sessions (user_id)",
        # Email/password support: google_sub becomes optional; add password_hash;
        # enforce unique email (safe on empty/deduped data).
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS password_hash VARCHAR(255)",
        "ALTER TABLE users ALTER COLUMN google_sub DROP NOT NULL",
        "CREATE UNIQUE INDEX IF NOT EXISTS ix_users_email ON users (email)",
    ]
    # Add FK constraints only if the column has no FK yet (avoids duplicates on
    # fresh databases where create_all already created them).
    fk_block = """
    DO $$
    BEGIN
      IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu ON tc.constraint_name = kcu.constraint_name
        WHERE tc.table_name = 'documents' AND tc.constraint_type = 'FOREIGN KEY'
          AND kcu.column_name = 'user_id'
      ) THEN
        ALTER TABLE documents ADD CONSTRAINT fk_documents_user
          FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;
      END IF;
      IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu ON tc.constraint_name = kcu.constraint_name
        WHERE tc.table_name = 'chat_sessions' AND tc.constraint_type = 'FOREIGN KEY'
          AND kcu.column_name = 'user_id'
      ) THEN
        ALTER TABLE chat_sessions ADD CONSTRAINT fk_chat_sessions_user
          FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;
      END IF;
    END $$;
    """
    with engine.begin() as conn:
        for stmt in statements:
            conn.execute(text(stmt))
        conn.execute(text(fk_block))

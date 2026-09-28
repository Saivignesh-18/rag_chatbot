-- ============================================================
--  Reference schema for AI Document Assistant
--  The application creates these tables automatically on startup
--  via SQLAlchemy. This file documents the schema and can be used
--  for manual provisioning. Vector dimension (384) matches the
--  default embedding model BAAI/bge-small-en-v1.5.
-- ============================================================

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS documents (
    id            UUID PRIMARY KEY,
    filename      VARCHAR(512) NOT NULL,
    file_type     VARCHAR(16)  NOT NULL,
    file_size     INTEGER      NOT NULL,
    status        VARCHAR(32)  NOT NULL DEFAULT 'pending',
    total_chunks  INTEGER      NOT NULL DEFAULT 0,
    page_count    INTEGER,
    error_message TEXT,
    created_at    TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS document_chunks (
    id           UUID PRIMARY KEY,
    document_id  UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index  INTEGER NOT NULL,
    content      TEXT NOT NULL,
    page_number  INTEGER,
    embedding    VECTOR(384) NOT NULL,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_document_chunks_document_id
    ON document_chunks (document_id);

-- Approximate nearest neighbour index (cosine distance).
CREATE INDEX IF NOT EXISTS ix_document_chunks_embedding_hnsw
    ON document_chunks USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

CREATE TABLE IF NOT EXISTS chat_sessions (
    id         UUID PRIMARY KEY,
    title      VARCHAR(255),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS chat_messages (
    id         UUID PRIMARY KEY,
    session_id UUID NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
    role       VARCHAR(16) NOT NULL,
    content    TEXT NOT NULL,
    sources    JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_chat_messages_session_id
    ON chat_messages (session_id);

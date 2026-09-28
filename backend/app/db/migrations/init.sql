-- ============================================================
--  Database bootstrap for AI Document Assistant
--  Runs automatically on first Postgres container init.
--  Enables the pgvector extension. Tables are created by the
--  application on startup (SQLAlchemy metadata) so the schema
--  stays in one place, but the schema is also documented in
--  001_schema.sql for reference / manual provisioning.
-- ============================================================

CREATE EXTENSION IF NOT EXISTS vector;

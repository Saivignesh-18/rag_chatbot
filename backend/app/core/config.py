"""Application configuration.

All settings are loaded from environment variables (and the project-root ``.env``
file for local development). Sensible defaults are provided so the app runs with
only ``GROQ_API_KEY`` set. Secrets are NEVER hard-coded here.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import ClassVar

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Project root = .../ (three levels up from this file: core -> app -> backend -> root)
BACKEND_DIR = Path(__file__).resolve().parents[2]
PROJECT_ROOT = BACKEND_DIR.parent


class Settings(BaseSettings):
    """Typed application settings."""

    model_config = SettingsConfigDict(
        # Load from project-root .env first, then backend/.env as a fallback.
        env_file=(PROJECT_ROOT / ".env", BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ---- App ----
    app_name: str = "AI Document Assistant"
    api_prefix: str = "/api"
    debug: bool = False

    # ---- Groq LLM (secret) ----
    groq_api_key: str = Field(default="", description="Groq API key. Provided via env only.")
    # openai/gpt-oss-20b is a current Groq production model (fast + inexpensive).
    # Note: reasoning models spend some completion tokens on reasoning, so keep
    # max_tokens comfortably above the desired answer length.
    groq_model: str = Field(default="openai/gpt-oss-20b")
    groq_timeout_seconds: float = Field(default=45.0)
    groq_max_tokens: int = Field(default=2048)
    groq_temperature: float = Field(default=0.1)

    # ---- Gemini LLM (fallback, secret) ----
    gemini_api_key: str = Field(default="")
    gemini_model: str = Field(default="gemini-flash-latest")
    gemini_timeout_seconds: float = Field(default=45.0)
    gemini_max_tokens: int = Field(default=2048)
    gemini_temperature: float = Field(default=0.1)

    # ---- LLM routing ----
    primary_llm: str = Field(default="groq")
    fallback_llm: str = Field(default="gemini")
    enable_llm_fallback: bool = Field(default=True)

    # ---- Database ----
    database_url: str = Field(
        default="postgresql+psycopg2://raguser:ragpassword@localhost:5433/ragdb"
    )

    # ---- Auth (Google OAuth + JWT) ----
    google_client_id: str = Field(default="")
    jwt_secret_key: str = Field(default="change-me-in-production-a-long-random-secret")
    jwt_algorithm: str = Field(default="HS256")
    jwt_expire_minutes: int = Field(default=60 * 24 * 7)  # 7 days

    # ---- Embeddings ----
    embedding_model: str = Field(default="BAAI/bge-small-en-v1.5")
    embedding_dim: int = Field(default=384, description="Must match the embedding model output dim.")

    # ---- Chunking ----
    chunk_size: int = Field(default=1000)
    chunk_overlap: int = Field(default=200)

    # ---- Retrieval ----
    top_k: int = Field(default=5)
    similarity_threshold: float = Field(default=0.5)

    # ---- Uploads ----
    max_file_size_mb: int = Field(default=20)
    upload_storage_dir: str = Field(default=str(BACKEND_DIR / "storage"))

    # ---- Rate limiting (slowapi syntax) ----
    rate_limit_upload: str = Field(default="30/minute")
    rate_limit_chat: str = Field(default="60/minute")
    rate_limit_default: str = Field(default="240/minute")

    # ---- CORS ----
    cors_origins: str = Field(default="http://localhost:3000")

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _coerce_cors(cls, value: object) -> str:
        if isinstance(value, (list, tuple)):
            return ",".join(str(v) for v in value)
        return str(value)

    @field_validator("database_url", mode="before")
    @classmethod
    def _normalize_database_url(cls, value: object) -> object:
        """Pin the psycopg2 driver regardless of the incoming URL scheme.

        Managed hosts (Render, Heroku, Fly) hand out ``postgres://`` or
        ``postgresql://`` connection strings, but SQLAlchemy 2.0 needs an
        explicit driver. Normalise both to ``postgresql+psycopg2://``.
        """
        if isinstance(value, str):
            url = value.strip()
            if url.startswith("postgres://"):
                return "postgresql+psycopg2://" + url[len("postgres://") :]
            if url.startswith("postgresql://"):
                return "postgresql+psycopg2://" + url[len("postgresql://") :]
            return url
        return value

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def max_file_size_bytes(self) -> int:
        return self.max_file_size_mb * 1024 * 1024

    @property
    def groq_configured(self) -> bool:
        key = self.groq_api_key.strip()
        return bool(key) and key != "YOUR_GROQ_API_KEY"

    @property
    def google_auth_configured(self) -> bool:
        return bool(self.google_client_id.strip())

    @property
    def gemini_configured(self) -> bool:
        key = self.gemini_api_key.strip()
        return bool(key) and key != "YOUR_GEMINI_API_KEY"

    # Supported upload types: extension -> logical file_type.
    ALLOWED_EXTENSIONS: ClassVar[dict[str, str]] = {
        ".pdf": "pdf",
        ".docx": "docx",
        ".txt": "txt",
    }


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()


settings = get_settings()

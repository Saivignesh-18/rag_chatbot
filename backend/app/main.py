"""FastAPI application entry point.

Wires together configuration, logging, CORS, error handling, rate limiting and the
API routers. Business logic lives in the ``services`` package - this file only
assembles the app.
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.api.auth import router as auth_router
from app.api.chat import router as chat_router
from app.api.documents import router as documents_router
from app.api.stats import router as stats_router
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging, get_logger
from app.core.rate_limit import limiter
from app.db.database import init_db

configure_logging(logging.DEBUG if settings.debug else logging.INFO)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting %s", settings.app_name)
    logger.info("Groq configured: %s | model=%s", settings.groq_configured, settings.groq_model)
    logger.info("Gemini configured: %s | model=%s", settings.gemini_configured, settings.gemini_model)
    logger.info(
        "LLM routing: primary=%s fallback=%s enabled=%s",
        settings.primary_llm, settings.fallback_llm, settings.enable_llm_fallback,
    )
    logger.info("Embedding model: %s (dim=%d)", settings.embedding_model, settings.embedding_dim)
    logger.info("Google auth configured: %s", settings.google_auth_configured)
    try:
        init_db()
    except Exception:  # pragma: no cover - startup diagnostics
        logger.exception("Database initialisation failed. Is PostgreSQL running with pgvector?")
        raise
    yield
    logger.info("Shutting down %s", settings.app_name)


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="Document-grounded RAG chatbot API.",
    lifespan=lifespan,
)

# ---- Rate limiting ----
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)

# ---- CORS ----
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---- Error handling (consistent envelope, no stack traces leaked) ----
register_exception_handlers(app)


@app.exception_handler(RateLimitExceeded)
async def _rate_limited(_, exc: RateLimitExceeded):
    from fastapi.responses import JSONResponse

    return JSONResponse(
        status_code=429,
        content={
            "success": False,
            "message": "Too many requests. Please slow down and try again shortly.",
            "error_code": "RATE_LIMITED",
        },
    )


# ---- Routers ----
app.include_router(auth_router, prefix=settings.api_prefix)
app.include_router(documents_router, prefix=settings.api_prefix)
app.include_router(chat_router, prefix=settings.api_prefix)
app.include_router(stats_router, prefix=settings.api_prefix)


@app.get("/", tags=["health"])
async def root() -> dict:
    return {"name": settings.app_name, "status": "ok"}


@app.get(f"{settings.api_prefix}/health", tags=["health"])
async def health() -> dict:
    return {
        "success": True,
        "status": "healthy",
        "groq_configured": settings.groq_configured,
        "gemini_configured": settings.gemini_configured,
        "google_auth_configured": settings.google_auth_configured,
        "llm": {
            "primary": settings.primary_llm,
            "fallback": settings.fallback_llm,
            "fallback_enabled": settings.enable_llm_fallback,
        },
        "embedding_model": settings.embedding_model,
    }

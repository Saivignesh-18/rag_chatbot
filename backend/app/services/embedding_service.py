"""Embedding service.

Generates real vector embeddings with a local, configurable model via
``fastembed`` (ONNX runtime, no external API key required). The SAME model is
used for document chunks and user questions so vectors live in one space.

For retrieval-tuned models (e.g. BGE), fastembed's ``query_embed`` /
``passage_embed`` apply the correct instruction prefixes automatically.
"""
from __future__ import annotations

import threading
from collections.abc import Iterable

from app.core.config import settings
from app.core.exceptions import EmbeddingError
from app.core.logging import get_logger

logger = get_logger(__name__)


class EmbeddingService:
    def __init__(self, model_name: str, expected_dim: int) -> None:
        self._model_name = model_name
        self._expected_dim = expected_dim
        self._model = None
        self._lock = threading.Lock()

    # -- model lifecycle -------------------------------------------------
    def _ensure_model(self) -> None:
        if self._model is not None:
            return
        with self._lock:
            if self._model is not None:
                return
            try:
                from fastembed import TextEmbedding

                logger.info("Loading embedding model '%s' (first load may download it)...", self._model_name)
                self._model = TextEmbedding(model_name=self._model_name)
                logger.info("Embedding model ready: %s", self._model_name)
            except Exception as exc:  # noqa: BLE001
                raise EmbeddingError(
                    f"Failed to load embedding model '{self._model_name}'. "
                    "Check EMBEDDING_MODEL is a valid fastembed model."
                ) from exc

    # -- helpers ---------------------------------------------------------
    def _validate_dim(self, vectors: list[list[float]]) -> None:
        if not vectors:
            return
        dim = len(vectors[0])
        if dim != self._expected_dim:
            raise EmbeddingError(
                f"Embedding dimension mismatch: model produced {dim}, but EMBEDDING_DIM is "
                f"{self._expected_dim}. Update EMBEDDING_DIM to match '{self._model_name}' "
                "and recreate the document_chunks table."
            )

    def _run(self, method_name: str, texts: list[str]) -> list[list[float]]:
        self._ensure_model()
        assert self._model is not None
        method = getattr(self._model, method_name, None) or self._model.embed
        try:
            vectors = [list(map(float, v)) for v in method(texts)]
        except Exception as exc:  # noqa: BLE001
            raise EmbeddingError("Embedding generation failed.") from exc
        self._validate_dim(vectors)
        return vectors

    # -- public API ------------------------------------------------------
    def embed_documents(self, texts: Iterable[str]) -> list[list[float]]:
        text_list = [t for t in texts]
        if not text_list:
            return []
        vectors = self._run("passage_embed", text_list)
        logger.info("Generated %d document embeddings (dim=%d)", len(vectors), self._expected_dim)
        return vectors

    def embed_query(self, text: str) -> list[float]:
        vectors = self._run("query_embed", [text])
        return vectors[0]

    @property
    def dimension(self) -> int:
        return self._expected_dim

    @property
    def model_name(self) -> str:
        return self._model_name


# Module-level singleton so the model is loaded once per process.
embedding_service = EmbeddingService(settings.embedding_model, settings.embedding_dim)

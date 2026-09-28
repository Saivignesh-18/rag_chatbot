"""Application-level exceptions and consistent error responses.

Every error surfaced to the client uses the shape::

    {"success": false, "message": "...", "error_code": "..."}

Stack traces are never exposed to clients.
"""
from __future__ import annotations

from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.logging import get_logger

logger = get_logger(__name__)


class AppError(Exception):
    """Base class for expected, client-safe application errors."""

    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    error_code: str = "INTERNAL_ERROR"
    message: str = "An unexpected error occurred."

    def __init__(self, message: str | None = None, *, error_code: str | None = None,
                 status_code: int | None = None) -> None:
        if message is not None:
            self.message = message
        if error_code is not None:
            self.error_code = error_code
        if status_code is not None:
            self.status_code = status_code
        super().__init__(self.message)

    def to_response(self) -> JSONResponse:
        return JSONResponse(
            status_code=self.status_code,
            content={"success": False, "message": self.message, "error_code": self.error_code},
        )


class ValidationAppError(AppError):
    status_code = 422  # Unprocessable Content
    error_code = "VALIDATION_ERROR"
    message = "Invalid input."


class BadRequestError(AppError):
    status_code = status.HTTP_400_BAD_REQUEST
    error_code = "BAD_REQUEST"
    message = "Bad request."


class UnsupportedFileTypeError(AppError):
    status_code = status.HTTP_400_BAD_REQUEST
    error_code = "UNSUPPORTED_FILE_TYPE"
    message = "Unsupported file type. Allowed types: PDF, DOCX, TXT."


class EmptyFileError(AppError):
    status_code = status.HTTP_400_BAD_REQUEST
    error_code = "EMPTY_FILE"
    message = "The uploaded file is empty."


class FileTooLargeError(AppError):
    status_code = 413  # Content Too Large
    error_code = "FILE_TOO_LARGE"
    message = "The uploaded file exceeds the maximum allowed size."


class CorruptedFileError(AppError):
    status_code = status.HTTP_400_BAD_REQUEST
    error_code = "CORRUPTED_FILE"
    message = "The file could not be read. It may be corrupted or password-protected."


class DocumentProcessingError(AppError):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    error_code = "DOCUMENT_PROCESSING_ERROR"
    message = "Document processing failed."


class NoTextExtractedError(AppError):
    status_code = status.HTTP_400_BAD_REQUEST
    error_code = "NO_TEXT_EXTRACTED"
    message = "No readable text could be extracted from the document."


class NotFoundError(AppError):
    status_code = status.HTTP_404_NOT_FOUND
    error_code = "NOT_FOUND"
    message = "The requested resource was not found."


class UnauthorizedError(AppError):
    status_code = status.HTTP_401_UNAUTHORIZED
    error_code = "UNAUTHORIZED"
    message = "Authentication is required."


class ForbiddenError(AppError):
    status_code = status.HTTP_403_FORBIDDEN
    error_code = "FORBIDDEN"
    message = "You do not have access to this resource."


class ConflictError(AppError):
    status_code = status.HTTP_409_CONFLICT
    error_code = "CONFLICT"
    message = "The resource already exists."


class EmbeddingError(AppError):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    error_code = "EMBEDDING_ERROR"
    message = "Failed to generate embeddings."


class LLMError(AppError):
    status_code = status.HTTP_502_BAD_GATEWAY
    error_code = "LLM_ERROR"
    message = "The language model service returned an error."


class LLMTimeoutError(AppError):
    status_code = status.HTTP_504_GATEWAY_TIMEOUT
    error_code = "LLM_TIMEOUT"
    message = "The language model service timed out."


class LLMRateLimitError(AppError):
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    error_code = "LLM_RATE_LIMITED"
    message = "The language model service is rate limited. Please try again shortly."


class ServiceUnavailableError(AppError):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    error_code = "SERVICE_UNAVAILABLE"
    message = "The service is temporarily unavailable."


def register_exception_handlers(app) -> None:
    """Attach handlers that produce the consistent error envelope."""

    @app.exception_handler(AppError)
    async def _app_error_handler(_: Request, exc: AppError) -> JSONResponse:
        # Log at appropriate level; never log secrets.
        if exc.status_code >= 500:
            logger.error("AppError %s (%s): %s", exc.error_code, exc.status_code, exc.message)
        else:
            logger.info("AppError %s (%s): %s", exc.error_code, exc.status_code, exc.message)
        return exc.to_response()

    @app.exception_handler(RequestValidationError)
    async def _validation_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
        # Summarise validation errors without leaking internals.
        first = exc.errors()[0] if exc.errors() else {}
        loc = ".".join(str(p) for p in first.get("loc", []) if p != "body")
        detail = first.get("msg", "Invalid input.")
        message = f"{loc}: {detail}" if loc else detail
        return JSONResponse(
            status_code=422,
            content={"success": False, "message": message, "error_code": "VALIDATION_ERROR"},
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http_exception_handler(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "message": exc.detail if isinstance(exc.detail, str) else "Request failed.",
                "error_code": f"HTTP_{exc.status_code}",
            },
        )

    @app.exception_handler(Exception)
    async def _unhandled_handler(_: Request, exc: Exception) -> JSONResponse:
        # Catch-all: log full detail server-side, return sanitised message.
        logger.exception("Unhandled server error: %s", type(exc).__name__)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "message": "An internal server error occurred.",
                "error_code": "INTERNAL_ERROR",
            },
        )

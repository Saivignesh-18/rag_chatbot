"""Authentication: Google ID-token verification, JWT issuance and the
`get_current_user` dependency.

Security model:
- The frontend obtains a Google ID token via Google Identity Services.
- The backend VERIFIES that token with Google's libraries (signature, audience,
  issuer, expiry). Identity is taken ONLY from the verified claims.
- The backend then issues its own short-lived JWT (Bearer) used for all
  subsequent API calls. The Google token is never trusted again.
"""
from __future__ import annotations

import datetime
import uuid

import jwt
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import LLMError, UnauthorizedError
from app.core.logging import get_logger
from app.db.database import get_db
from app.models.user import User

logger = get_logger(__name__)

_bearer = HTTPBearer(auto_error=False)


def verify_google_token(credential: str) -> dict:
    """Verify a Google ID token and return its claims.

    Raises UnauthorizedError if the token is invalid/expired or the audience
    does not match the configured Google client id.
    """
    if not settings.google_auth_configured:
        # Misconfiguration, not a client error.
        raise LLMError(
            "Google login is not configured on the server (GOOGLE_CLIENT_ID missing).",
            error_code="GOOGLE_NOT_CONFIGURED",
            status_code=503,
        )
    if not credential:
        raise UnauthorizedError("Missing Google credential.")

    try:
        claims = google_id_token.verify_oauth2_token(
            credential,
            google_requests.Request(),
            audience=settings.google_client_id,
        )
    except ValueError as exc:
        logger.info("Google token verification failed: %s", type(exc).__name__)
        raise UnauthorizedError("Invalid or expired Google credential.") from exc

    # Extra hardening: issuer must be Google.
    if claims.get("iss") not in ("accounts.google.com", "https://accounts.google.com"):
        raise UnauthorizedError("Invalid Google token issuer.")
    if not claims.get("sub"):
        raise UnauthorizedError("Google token is missing the subject claim.")

    return claims


def create_access_token(user_id: uuid.UUID) -> str:
    now = datetime.datetime.now(datetime.timezone.utc)
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + datetime.timedelta(minutes=settings.jwt_expire_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except jwt.ExpiredSignatureError as exc:
        raise UnauthorizedError("Session expired. Please sign in again.") from exc
    except jwt.PyJWTError as exc:
        raise UnauthorizedError("Invalid authentication token.") from exc


_RESET_PURPOSE = "password_reset"


def create_reset_token(user_id: uuid.UUID, minutes: int = 30) -> str:
    now = datetime.datetime.now(datetime.timezone.utc)
    payload = {
        "sub": str(user_id),
        "purpose": _RESET_PURPOSE,
        "iat": now,
        "exp": now + datetime.timedelta(minutes=minutes),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_reset_token(token: str) -> uuid.UUID:
    """Validate a password-reset token and return the target user id."""
    payload = decode_token(token)
    if payload.get("purpose") != _RESET_PURPOSE:
        raise UnauthorizedError("Invalid password reset token.")
    try:
        return uuid.UUID(str(payload.get("sub")))
    except (ValueError, TypeError) as exc:
        raise UnauthorizedError("Invalid password reset token.") from exc


def _user_from_token(db: Session, token: str) -> User:
    payload = decode_token(token)
    sub = payload.get("sub")
    try:
        user_id = uuid.UUID(str(sub))
    except (ValueError, TypeError) as exc:
        raise UnauthorizedError() from exc
    user = db.get(User, user_id)
    if user is None:
        raise UnauthorizedError("User no longer exists.")
    return user


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    """FastAPI dependency that returns the authenticated user or raises 401."""
    if creds is None or not creds.credentials:
        raise UnauthorizedError()
    return _user_from_token(db, creds.credentials)


def get_current_user_flexible(request: Request, db: Session = Depends(get_db)) -> User:
    """Like get_current_user but also accepts a ?token= query param.

    Used for file preview links opened in a new browser tab, which cannot send
    an Authorization header.
    """
    token: str | None = None
    header = request.headers.get("Authorization")
    if header and header.lower().startswith("bearer "):
        token = header[7:]
    if not token:
        token = request.query_params.get("token")
    if not token:
        raise UnauthorizedError()
    return _user_from_token(db, token)

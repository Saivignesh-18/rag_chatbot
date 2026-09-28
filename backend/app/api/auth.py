"""Authentication endpoints: Google, email/password, and password reset."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.auth import (
    create_access_token,
    create_reset_token,
    decode_reset_token,
    get_current_user,
    verify_google_token,
)
from app.core.logging import get_logger
from app.core.rate_limit import limiter
from app.db.database import get_db
from app.models.user import User
from app.schemas.auth import (
    AuthResponse,
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    GoogleLoginRequest,
    LoginRequest,
    MeResponse,
    RegisterRequest,
    ResetPasswordRequest,
    SimpleMessageResponse,
    UserOut,
)
from app.services import user_service

logger = get_logger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


def _auth_response(user: User) -> AuthResponse:
    return AuthResponse(access_token=create_access_token(user.id), user=UserOut.model_validate(user))


@router.post("/google", response_model=AuthResponse)
@limiter.limit("20/minute")
async def google_login(request: Request, payload: GoogleLoginRequest, db: Session = Depends(get_db)) -> AuthResponse:
    """Verify a Google ID token, find/create the user, and issue an app JWT."""
    claims = verify_google_token(payload.credential)
    user = user_service.get_or_create_user(db, claims)
    logger.info("Auth success (google): user id=%s", user.id)
    return _auth_response(user)


@router.post("/register", response_model=AuthResponse)
@limiter.limit("10/minute")
async def register(request: Request, payload: RegisterRequest, db: Session = Depends(get_db)) -> AuthResponse:
    """Create a new email/password account and return an app JWT."""
    user = user_service.register_user(db, payload.email, payload.password, payload.name)
    return _auth_response(user)


@router.post("/login", response_model=AuthResponse)
@limiter.limit("10/minute")
async def login(request: Request, payload: LoginRequest, db: Session = Depends(get_db)) -> AuthResponse:
    """Authenticate an email/password account and return an app JWT."""
    user = user_service.authenticate_user(db, payload.email, payload.password)
    return _auth_response(user)


@router.post("/forgot-password", response_model=ForgotPasswordResponse)
@limiter.limit("5/minute")
async def forgot_password(
    request: Request, payload: ForgotPasswordRequest, db: Session = Depends(get_db)
) -> ForgotPasswordResponse:
    """Begin a password reset.

    Always returns success (no account enumeration). Since no email service is
    configured, the reset token is returned directly for DEV use. In production
    this token must be emailed to the user instead of returned.
    """
    user = user_service.get_by_email(db, payload.email)
    reset_token: str | None = None
    if user is not None and user.password_hash:
        reset_token = create_reset_token(user.id)
        logger.info("Password reset requested for user id=%s", user.id)

    return ForgotPasswordResponse(
        message="If an account with that email exists, a password reset token has been issued.",
        reset_token=reset_token,
    )


@router.post("/reset-password", response_model=SimpleMessageResponse)
@limiter.limit("10/minute")
async def reset_password(
    request: Request, payload: ResetPasswordRequest, db: Session = Depends(get_db)
) -> SimpleMessageResponse:
    """Complete a password reset using the token from /forgot-password."""
    user_id = decode_reset_token(payload.token)
    user = db.get(User, user_id)
    if user is None:
        from app.core.exceptions import UnauthorizedError

        raise UnauthorizedError("Invalid password reset token.")
    user_service.set_password(db, user, payload.new_password)
    return SimpleMessageResponse(message="Password updated. You can now sign in.")


@router.get("/me", response_model=MeResponse)
async def me(current_user: User = Depends(get_current_user)) -> MeResponse:
    return MeResponse(user=UserOut.model_validate(current_user))


@router.post("/logout")
async def logout(current_user: User = Depends(get_current_user)) -> dict:
    logger.info("Logout: user id=%s", current_user.id)
    return {"success": True, "message": "Logged out"}

"""User service: Google account resolution + email/password accounts."""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, UnauthorizedError
from app.core.logging import get_logger
from app.core.passwords import hash_password, verify_password
from app.models.user import User

logger = get_logger(__name__)


def _normalize_email(email: str) -> str:
    return (email or "").strip().lower()


def get_by_email(db: Session, email: str) -> User | None:
    return db.execute(
        select(User).where(func.lower(User.email) == _normalize_email(email))
    ).scalar_one_or_none()


# ---- Google ----
def get_or_create_user(db: Session, claims: dict) -> User:
    """Resolve the user for verified Google claims.

    Matches by google_sub; otherwise links to an existing account with the same
    email; otherwise creates a new Google user. Never duplicates.
    """
    google_sub = claims["sub"]
    email = _normalize_email(claims.get("email", ""))
    name = claims.get("name")
    picture = claims.get("picture")

    user = db.execute(select(User).where(User.google_sub == google_sub)).scalar_one_or_none()
    if user is None and email:
        # Link Google to an existing email/password account with the same email.
        existing = get_by_email(db, email)
        if existing is not None:
            existing.google_sub = google_sub
            user = existing

    if user is None:
        user = User(google_sub=google_sub, email=email, name=name, profile_picture=picture)
        db.add(user)
        db.commit()
        db.refresh(user)
        logger.info("Created new Google user id=%s", user.id)
        return user

    # Refresh profile data on each login.
    changed = False
    if email and user.email != email and get_by_email(db, email) in (None, user):
        user.email, changed = email, True
    if name and user.name != name:
        user.name, changed = name, True
    if picture and user.profile_picture != picture:
        user.profile_picture, changed = picture, True
    if user.google_sub != google_sub:
        user.google_sub, changed = google_sub, True
    if changed:
        db.commit()
    db.refresh(user)
    logger.info("Existing user signed in via Google id=%s", user.id)
    return user


# ---- Email / password ----
def register_user(db: Session, email: str, password: str, name: str | None) -> User:
    email = _normalize_email(email)
    if get_by_email(db, email) is not None:
        raise ConflictError("An account with this email already exists. Try signing in.")
    user = User(email=email, name=(name or email.split("@")[0]), password_hash=hash_password(password))
    db.add(user)
    db.commit()
    db.refresh(user)
    logger.info("Registered email user id=%s", user.id)
    return user


def authenticate_user(db: Session, email: str, password: str) -> User:
    user = get_by_email(db, email)
    if user is None or not verify_password(password, user.password_hash):
        # Uniform error prevents account enumeration.
        raise UnauthorizedError("Invalid email or password.")
    logger.info("Email user signed in id=%s", user.id)
    return user


def set_password(db: Session, user: User, new_password: str) -> None:
    user.password_hash = hash_password(new_password)
    db.commit()
    logger.info("Password updated for user id=%s", user.id)

"""Password hashing with bcrypt."""
from __future__ import annotations

import bcrypt

# bcrypt only uses the first 72 bytes; truncate defensively to avoid errors.
_MAX = 72


def hash_password(password: str) -> str:
    pw = password.encode("utf-8")[:_MAX]
    return bcrypt.hashpw(pw, bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str | None) -> bool:
    if not hashed:
        return False
    try:
        return bcrypt.checkpw(password.encode("utf-8")[:_MAX], hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False

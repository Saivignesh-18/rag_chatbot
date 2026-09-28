"""Shared slowapi rate limiter."""
from __future__ import annotations

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import settings

# Keyed by client IP. Applied per-route via decorators and a default global limit.
limiter = Limiter(key_func=get_remote_address, default_limits=[settings.rate_limit_default])

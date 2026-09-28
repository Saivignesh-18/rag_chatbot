"""Auth schemas."""
from __future__ import annotations

import datetime
import uuid

from pydantic import BaseModel, ConfigDict, Field, field_validator


class GoogleLoginRequest(BaseModel):
    credential: str  # Google ID token from Google Identity Services


class RegisterRequest(BaseModel):
    email: str = Field(max_length=320)
    password: str = Field(min_length=8, max_length=128)
    name: str | None = Field(default=None, max_length=255)

    @field_validator("email")
    @classmethod
    def _valid_email(cls, v: str) -> str:
        v = v.strip()
        if "@" not in v or "." not in v.split("@")[-1] or len(v) < 5:
            raise ValueError("A valid email address is required.")
        return v


class LoginRequest(BaseModel):
    email: str
    password: str


class ForgotPasswordRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=8, max_length=128)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    name: str | None = None
    profile_picture: str | None = None
    provider: str = "Email"
    created_at: datetime.datetime | None = None


class AuthResponse(BaseModel):
    success: bool = True
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class MeResponse(BaseModel):
    success: bool = True
    user: UserOut


class ForgotPasswordResponse(BaseModel):
    success: bool = True
    message: str
    # DEV ONLY: no email service is configured, so the reset token is returned
    # directly. In production this must be emailed, not returned.
    reset_token: str | None = None


class SimpleMessageResponse(BaseModel):
    success: bool = True
    message: str

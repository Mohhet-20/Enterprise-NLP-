import re
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, field_validator

from backend.core.common_passwords import is_common_password
from backend.core.constants import (
    MAX_PASSWORD_LENGTH,
    MAX_USERNAME_LENGTH,
    MIN_PASSWORD_LENGTH,
    MIN_USERNAME_LENGTH,
    UserRole,
)

_USERNAME_PATTERN = re.compile(r"^[a-zA-Z0-9_]+$")
_EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class CurrentUser(BaseModel):
    """The authenticated principal for the current request — resolved
    fresh from the database on every request (see auth/dependencies.py),
    not trusted blindly from the JWT payload."""

    user_id: str
    username: str
    role: UserRole


class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        if not (MIN_USERNAME_LENGTH <= len(v) <= MAX_USERNAME_LENGTH):
            raise ValueError(
                f"Username must be between {MIN_USERNAME_LENGTH} and {MAX_USERNAME_LENGTH} characters."
            )
        if not _USERNAME_PATTERN.match(v):
            raise ValueError("Username may only contain letters, numbers, and underscores.")
        return v

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        if not _EMAIL_PATTERN.match(v):
            raise ValueError("Enter a valid email address.")
        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < MIN_PASSWORD_LENGTH:
            raise ValueError(f"Password must be at least {MIN_PASSWORD_LENGTH} characters.")
        if len(v) > MAX_PASSWORD_LENGTH:
            raise ValueError(f"Password must be at most {MAX_PASSWORD_LENGTH} characters.")
        if is_common_password(v):
            raise ValueError(
                "This password appears in common breach lists and is too easy to guess. "
                "Choose something less predictable."
            )
        return v


class LoginRequest(BaseModel):
    username: str
    password: str
    remember_me: bool = False


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str


class UserPublic(BaseModel):
    id: str
    username: str
    email: str
    role: UserRole
    is_active: bool
    created_at: datetime
    last_login_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserPublic


class SessionInfo(BaseModel):
    id: str
    issued_at: datetime
    expires_at: datetime

    model_config = {"from_attributes": True}

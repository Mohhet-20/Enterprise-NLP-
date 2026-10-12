"""
Auth orchestration: everything that touches both the User and RefreshToken
tables lives here so the API layer stays a thin pass-through. Endpoints
never construct a User/RefreshToken row directly.

Refresh-token design: opaque random string, SHA-256 hash stored (never the
raw value). Each successful `rotate` revokes the presented token and issues
a brand new one, linked via `replaced_by` — a classic rotation chain. This
means a stolen-but-rotated refresh token becomes useless the moment the
legitimate client rotates it, and every session can be individually or
fully revoked without waiting for a JWT to expire.
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import List, Tuple

from sqlalchemy.orm import Session

from backend.auth.jwt_handler import create_access_token
from backend.auth.password import hash_password, verify_password
from backend.config.logging_config import get_logger
from backend.config.settings import get_settings
from backend.core.constants import UserRole
from backend.core.exceptions import (
    AccountLockedError,
    AuthenticationError,
    DuplicateUserError,
    InvalidRefreshTokenError,
)
from backend.core.time_utils import ensure_aware_utc
from backend.models.refresh_token import RefreshToken
from backend.models.user import User
from backend.repositories.refresh_token_repository import RefreshTokenRepository
from backend.repositories.user_repository import UserRepository
from backend.services.audit_service import audit_service
from backend.services.base_service import BaseService

logger = get_logger("auth")


class AuthService(BaseService):
    def register(self, db: Session, username: str, email: str, password: str) -> User:
        users = UserRepository(db)
        if users.find_by_username(username) is not None:
            raise DuplicateUserError("Username is already taken.")
        if users.find_by_email(email) is not None:
            raise DuplicateUserError("Email is already registered.")

        user = User(
            username=username,
            email=email,
            hashed_password=hash_password(password),
            role=UserRole.READ_ONLY_USER.value,
        )
        created = users.create(user)
        logger.info("user_registered", extra={"username": username})
        audit_service.record(
            db, action="user.registered", actor_id=created.id, actor_username=username,
            resource_type="user", resource_id=created.id,
        )
        return created

    def authenticate(self, db: Session, username: str, password: str) -> User:
        settings = get_settings()
        users = UserRepository(db)
        user = users.find_by_username(username)

        # Deliberately identical error for "no such user" and "wrong
        # password" — distinguishing them lets an attacker enumerate
        # valid usernames.
        invalid_credentials = AuthenticationError("Invalid username or password.")

        if user is None:
            audit_service.record(db, action="user.login_failed", actor_username=username, details={"reason": "unknown_username"})
            raise invalid_credentials

        now = datetime.now(timezone.utc)
        if user.locked_until is not None and ensure_aware_utc(user.locked_until) > now:
            audit_service.record(
                db, action="user.login_blocked_locked", actor_id=user.id, actor_username=username,
                resource_type="user", resource_id=user.id,
            )
            raise AccountLockedError(
                f"Account is locked until {ensure_aware_utc(user.locked_until).isoformat()}."
            )

        if not user.is_active:
            raise AuthenticationError("This account has been deactivated.")

        if not verify_password(password, user.hashed_password):
            user.failed_login_attempts += 1
            locked_now = False
            if user.failed_login_attempts >= settings.max_failed_login_attempts:
                user.locked_until = now + timedelta(minutes=settings.account_lockout_minutes)
                locked_now = True
                logger.warning("account_locked", extra={"username": username})
            db.commit()
            audit_service.record(
                db, action="user.account_locked" if locked_now else "user.login_failed",
                actor_id=user.id, actor_username=username, resource_type="user", resource_id=user.id,
                details={"failed_attempts": user.failed_login_attempts},
            )
            raise invalid_credentials

        user.failed_login_attempts = 0
        user.locked_until = None
        user.last_login_at = now
        db.commit()
        db.refresh(user)
        logger.info("user_login_success", extra={"username": username})
        audit_service.record(
            db, action="user.login_success", actor_id=user.id, actor_username=username,
            resource_type="user", resource_id=user.id,
        )
        return user

    def issue_tokens(self, db: Session, user: User, remember_me: bool = False) -> TokenBundle:
        settings = get_settings()
        access_token = create_access_token(user.id, {"username": user.username, "role": user.role})
        lifetime_days = (
            settings.remember_me_refresh_token_expire_days
            if remember_me
            else settings.refresh_token_expire_days
        )
        raw_refresh, _ = self._create_refresh_token(db, user.id, lifetime_days)
        return TokenBundle(
            access_token=access_token,
            refresh_token=raw_refresh,
            expires_in=settings.access_token_expire_minutes * 60,
            user=user,
        )

    def rotate_refresh_token(self, db: Session, raw_token: str) -> TokenBundle:
        settings = get_settings()
        tokens = RefreshTokenRepository(db)
        token_hash = self._hash_token(raw_token)
        record = tokens.find_by_hash(token_hash)

        now = datetime.now(timezone.utc)
        if record is None or record.revoked_at is not None or ensure_aware_utc(record.expires_at) <= now:
            raise InvalidRefreshTokenError()

        user = UserRepository(db).get(record.user_id)
        if not user.is_active:
            raise AuthenticationError("This account has been deactivated.")

        record.revoked_at = now
        new_raw, new_record = self._create_refresh_token(db, user.id, settings.refresh_token_expire_days)
        record.replaced_by = new_record.id
        db.commit()

        access_token = create_access_token(user.id, {"username": user.username, "role": user.role})
        logger.info("refresh_token_rotated", extra={"user_id": user.id})
        return TokenBundle(
            access_token=access_token,
            refresh_token=new_raw,
            expires_in=settings.access_token_expire_minutes * 60,
            user=user,
        )

    def revoke_refresh_token(self, db: Session, raw_token: str) -> None:
        tokens = RefreshTokenRepository(db)
        record = tokens.find_by_hash(self._hash_token(raw_token))
        # Logout is idempotent/safe: an already-invalid token is a no-op,
        # not an error — we never confirm-or-deny token validity here.
        if record is not None and record.revoked_at is None:
            record.revoked_at = datetime.now(timezone.utc)
            db.commit()
            logger.info("refresh_token_revoked", extra={"user_id": record.user_id})

    def revoke_all_sessions(self, db: Session, user_id: str) -> int:
        count = RefreshTokenRepository(db).revoke_all_for_user(user_id)
        logger.info("all_sessions_revoked", extra={"user_id": user_id, "count": count})
        return count

    def list_active_sessions(self, db: Session, user_id: str) -> List[RefreshToken]:
        return RefreshTokenRepository(db).find_active_for_user(user_id)

    def get_user(self, db: Session, user_id: str) -> User:
        return UserRepository(db).get(user_id)

    # --- internals ---

    @staticmethod
    def _hash_token(raw_token: str) -> str:
        return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()

    def _create_refresh_token(
        self, db: Session, user_id: str, lifetime_days: int
    ) -> Tuple[str, RefreshToken]:
        raw_token = secrets.token_urlsafe(48)
        record = RefreshToken(
            user_id=user_id,
            token_hash=self._hash_token(raw_token),
            expires_at=datetime.now(timezone.utc) + timedelta(days=lifetime_days),
        )
        RefreshTokenRepository(db).create(record)
        return raw_token, record


class TokenBundle:
    """Plain data holder returned by AuthService — kept out of schemas/ since
    it carries the ORM User, not the API-facing UserPublic shape; endpoints
    convert it to TokenResponse."""

    def __init__(self, access_token: str, refresh_token: str, expires_in: int, user: User) -> None:
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.expires_in = expires_in
        self.user = user


auth_service = AuthService()

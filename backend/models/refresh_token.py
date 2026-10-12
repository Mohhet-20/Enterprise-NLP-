"""
Refresh tokens are opaque random strings (not JWTs) so they can be
individually revoked and rotated — a JWT refresh token can't be invalidated
without a separate blocklist, which defeats the point. Only a SHA-256 hash
of the token is ever stored; the raw value is shown to the client exactly
once, at issuance, the same way a password is never stored in plaintext.

`replaced_by` links a rotation chain (old token -> new token id), which is
what makes "this refresh token was reused after rotation" detectable later
if that hardening is added.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.core.time_utils import ensure_aware_utc
from backend.database.base import Base


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    token_hash: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)

    issued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    replaced_by: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)

    @property
    def is_active(self) -> bool:
        return self.revoked_at is None and ensure_aware_utc(self.expires_at) > datetime.now(timezone.utc)

from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy.orm import Session

from backend.models.refresh_token import RefreshToken
from backend.repositories.base_repository import BaseRepository


class RefreshTokenRepository(BaseRepository[RefreshToken]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, RefreshToken)

    def find_by_hash(self, token_hash: str) -> Optional[RefreshToken]:
        return self._db.query(RefreshToken).filter(RefreshToken.token_hash == token_hash).first()

    def find_active_for_user(self, user_id: str) -> List[RefreshToken]:
        now = datetime.now(timezone.utc)
        return list(
            self._db.query(RefreshToken)
            .filter(
                RefreshToken.user_id == user_id,
                RefreshToken.revoked_at.is_(None),
                RefreshToken.expires_at > now,
            )
            .order_by(RefreshToken.issued_at.desc())
            .all()
        )

    def revoke_all_for_user(self, user_id: str) -> int:
        now = datetime.now(timezone.utc)
        active = (
            self._db.query(RefreshToken)
            .filter(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
            .all()
        )
        for token in active:
            token.revoked_at = now
        self._db.commit()
        return len(active)

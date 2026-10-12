from typing import Optional

from sqlalchemy.orm import Session

from backend.models.user import User
from backend.repositories.base_repository import BaseRepository


class UserRepository(BaseRepository[User]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, User)

    def find_by_username(self, username: str) -> Optional[User]:
        return self._db.query(User).filter(User.username == username).first()

    def find_by_email(self, email: str) -> Optional[User]:
        return self._db.query(User).filter(User.email == email).first()

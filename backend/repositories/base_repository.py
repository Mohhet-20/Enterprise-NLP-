"""
Generic Repository pattern base class.

Services depend on this abstraction, never on SQLAlchemy directly — this is
what lets us swap the persistence layer (e.g. Postgres -> a document store
for a specific dataset type) without touching service or API code.
"""

from typing import Generic, List, Type, TypeVar

from sqlalchemy.orm import Session

from backend.core.exceptions import RecordNotFoundError
from backend.database.base import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    def __init__(self, db: Session, model: Type[ModelType]) -> None:
        self._db = db
        self._model = model

    def get(self, record_id: str) -> ModelType:
        record = self._db.get(self._model, record_id)
        if record is None:
            raise RecordNotFoundError(
                f"{self._model.__name__} with id={record_id!r} was not found."
            )
        return record

    def list(self, *, limit: int = 100, offset: int = 0) -> List[ModelType]:
        return list(
            self._db.query(self._model).offset(offset).limit(limit).all()
        )

    def create(self, instance: ModelType) -> ModelType:
        self._db.add(instance)
        self._db.commit()
        self._db.refresh(instance)
        return instance

    def delete(self, record_id: str) -> None:
        record = self.get(record_id)
        self._db.delete(record)
        self._db.commit()

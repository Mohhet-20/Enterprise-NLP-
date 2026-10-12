from typing import List, Optional

from sqlalchemy.orm import Session

from backend.models.model_registry_entry import ModelRegistryEntry
from backend.repositories.base_repository import BaseRepository


class ModelRegistryRepository(BaseRepository[ModelRegistryEntry]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, ModelRegistryEntry)

    def list_filtered(
        self, *, task: Optional[str] = None, stage: Optional[str] = None
    ) -> List[ModelRegistryEntry]:
        query = self._db.query(ModelRegistryEntry)
        if task:
            query = query.filter(ModelRegistryEntry.task == task)
        if stage:
            query = query.filter(ModelRegistryEntry.stage == stage)
        return list(query.order_by(ModelRegistryEntry.created_at.desc()).all())

    def find_champion_for_task(self, task: str) -> Optional[ModelRegistryEntry]:
        return (
            self._db.query(ModelRegistryEntry)
            .filter(ModelRegistryEntry.task == task, ModelRegistryEntry.is_champion.is_(True))
            .first()
        )

    def find_deployed_for_task(self, task: str) -> Optional[ModelRegistryEntry]:
        return (
            self._db.query(ModelRegistryEntry)
            .filter(
                ModelRegistryEntry.task == task,
                ModelRegistryEntry.deployment_status == "deployed",
            )
            .first()
        )

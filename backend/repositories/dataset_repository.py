from typing import List, Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session

from backend.models.dataset import Dataset
from backend.repositories.base_repository import BaseRepository


class DatasetRepository(BaseRepository[Dataset]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, Dataset)

    def search(
        self,
        *,
        query: Optional[str] = None,
        task: Optional[str] = None,
        tag: Optional[str] = None,
        include_archived: bool = False,
    ) -> List[Dataset]:
        q = self._db.query(Dataset)
        if not include_archived:
            q = q.filter(Dataset.is_archived.is_(False))
        if task:
            q = q.filter(Dataset.task == task)
        if query:
            like = f"%{query}%"
            q = q.filter(or_(Dataset.name.ilike(like), Dataset.description.ilike(like)))
        results = list(q.order_by(Dataset.created_at.desc()).all())
        if tag:
            results = [d for d in results if tag in (d.tags or [])]
        return results

    def find_version_chain(self, dataset_id: str) -> List[Dataset]:
        """Walk the parent_version_id chain back to the root, returning
        every version from oldest to newest."""
        chain: List[Dataset] = []
        current = self.get(dataset_id)
        chain.append(current)
        while current.parent_version_id:
            current = self.get(current.parent_version_id)
            chain.append(current)
        return list(reversed(chain))

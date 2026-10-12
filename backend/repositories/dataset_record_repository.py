from typing import List

from sqlalchemy.orm import Session

from backend.models.dataset_record import DatasetRecord
from backend.repositories.base_repository import BaseRepository


class DatasetRecordRepository(BaseRepository[DatasetRecord]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, DatasetRecord)

    def bulk_create(self, records: List[DatasetRecord]) -> List[DatasetRecord]:
        self._db.add_all(records)
        self._db.commit()
        for r in records:
            self._db.refresh(r)
        return records

    def list_for_dataset(self, dataset_id: str, *, limit: int = 50, offset: int = 0) -> List[DatasetRecord]:
        return list(
            self._db.query(DatasetRecord)
            .filter(DatasetRecord.dataset_id == dataset_id)
            .order_by(DatasetRecord.created_at.asc())
            .offset(offset)
            .limit(limit)
            .all()
        )

    def all_for_dataset(self, dataset_id: str) -> List[DatasetRecord]:
        return list(
            self._db.query(DatasetRecord)
            .filter(DatasetRecord.dataset_id == dataset_id)
            .order_by(DatasetRecord.created_at.asc())
            .all()
        )

    def copy_all_to_new_dataset(self, source_dataset_id: str, target_dataset_id: str) -> int:
        source_records = self.all_for_dataset(source_dataset_id)
        new_records = [
            DatasetRecord(dataset_id=target_dataset_id, text=r.text, label=r.label, extra_metadata=r.extra_metadata)
            for r in source_records
        ]
        self.bulk_create(new_records)
        return len(new_records)

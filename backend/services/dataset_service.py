"""
Dataset Management orchestration: parses an uploaded CSV, optionally runs
it through the real cleaning pipeline, validates it for real, persists the
records, and keeps the dataset's denormalized `row_count`/`status` in
sync. Versioning is a copy-with-lineage-pointer (see models/dataset.py);
archiving is always soft-delete.
"""

import csv
import io
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy.orm import Session

from backend.core.constants import DatasetStatus
from backend.core.exceptions import DatasetValidationFailedError, EmptyDatasetError
from backend.datasets.cleaning import CleaningConfig, text_cleaner
from backend.datasets.profiling import DatasetProfile, dataset_profiler
from backend.datasets.validation import DatasetRecordInput, ValidationReport, dataset_validator
from backend.models.dataset import Dataset
from backend.models.dataset_record import DatasetRecord
from backend.repositories.dataset_record_repository import DatasetRecordRepository
from backend.repositories.dataset_repository import DatasetRepository
from backend.services.base_service import BaseService

MAX_CSV_ROWS = 50_000


class DatasetService(BaseService):
    def create_dataset(
        self, db: Session, *, name: str, task: str, description: Optional[str], label_set: List[str], created_by: str
    ) -> Dataset:
        dataset = Dataset(
            name=name,
            task=task,
            description=description,
            label_set=label_set,
            created_by=created_by,
            modified_by=created_by,
        )
        return DatasetRepository(db).create(dataset)

    def upload_csv(
        self, db: Session, dataset_id: str, csv_text: str, uploaded_by: str, apply_cleaning: bool = True
    ) -> tuple[Dataset, ValidationReport]:
        dataset = DatasetRepository(db).get(dataset_id)

        reader = csv.DictReader(io.StringIO(csv_text))
        raw_rows = [row for row in reader]
        if not raw_rows:
            raise EmptyDatasetError("The uploaded CSV has no data rows.")
        if len(raw_rows) > MAX_CSV_ROWS:
            raise DatasetValidationFailedError(
                f"CSV has {len(raw_rows)} rows, exceeding the {MAX_CSV_ROWS}-row limit per upload. "
                f"Split large datasets into multiple uploads."
            )

        cleaning_config = CleaningConfig() if apply_cleaning else None
        validation_inputs: List[DatasetRecordInput] = []
        for row in raw_rows:
            raw_text = row.get("text", "") or ""
            cleaned_text = text_cleaner.clean(raw_text, cleaning_config) if cleaning_config else raw_text
            validation_inputs.append(DatasetRecordInput(text=cleaned_text, label=row.get("label") or None))

        report = dataset_validator.validate(validation_inputs, label_set=dataset.label_set or None)

        records = [
            DatasetRecord(
                dataset_id=dataset.id,
                text=v.text,
                label=v.label,
                extra_metadata={"cleaned": apply_cleaning},
            )
            for v in validation_inputs
        ]
        DatasetRecordRepository(db).bulk_create(records)

        dataset.row_count = len(records)
        dataset.status = DatasetStatus.VALIDATED.value if report.is_valid else DatasetStatus.DRAFT.value
        dataset.modified_by = uploaded_by
        db.commit()
        db.refresh(dataset)

        return dataset, report

    def list_datasets(
        self, db: Session, *, query: Optional[str], task: Optional[str], tag: Optional[str], include_archived: bool
    ) -> List[Dataset]:
        return DatasetRepository(db).search(query=query, task=task, tag=tag, include_archived=include_archived)

    def get_dataset(self, db: Session, dataset_id: str) -> Dataset:
        return DatasetRepository(db).get(dataset_id)

    def preview(self, db: Session, dataset_id: str, limit: int = 50, offset: int = 0) -> List[DatasetRecord]:
        return DatasetRecordRepository(db).list_for_dataset(dataset_id, limit=limit, offset=offset)

    def get_validation_report(self, db: Session, dataset_id: str) -> ValidationReport:
        dataset = DatasetRepository(db).get(dataset_id)
        records = DatasetRecordRepository(db).all_for_dataset(dataset_id)
        inputs = [DatasetRecordInput(text=r.text, label=r.label) for r in records]
        return dataset_validator.validate(inputs, label_set=dataset.label_set or None)

    def get_profile(self, db: Session, dataset_id: str) -> DatasetProfile:
        records = DatasetRecordRepository(db).all_for_dataset(dataset_id)
        if not records:
            raise EmptyDatasetError(f"Dataset {dataset_id!r} has no records to profile.")
        inputs = [DatasetRecordInput(text=r.text, label=r.label) for r in records]
        return dataset_profiler.profile(inputs)

    def create_version(self, db: Session, dataset_id: str, created_by: str) -> Dataset:
        source = DatasetRepository(db).get(dataset_id)
        new_version = Dataset(
            name=source.name,
            task=source.task,
            description=source.description,
            label_set=source.label_set,
            tags=source.tags,
            version=source.version + 1,
            parent_version_id=source.id,
            created_by=created_by,
            modified_by=created_by,
        )
        created = DatasetRepository(db).create(new_version)

        copied_count = DatasetRecordRepository(db).copy_all_to_new_dataset(source.id, created.id)
        created.row_count = copied_count
        created.status = source.status
        db.commit()
        db.refresh(created)
        return created

    def get_version_history(self, db: Session, dataset_id: str) -> List[Dataset]:
        return DatasetRepository(db).find_version_chain(dataset_id)

    def archive(self, db: Session, dataset_id: str) -> Dataset:
        dataset = DatasetRepository(db).get(dataset_id)
        dataset.is_archived = True
        dataset.archived_at = datetime.now(timezone.utc)
        dataset.status = DatasetStatus.ARCHIVED.value
        db.commit()
        db.refresh(dataset)
        return dataset

    def restore(self, db: Session, dataset_id: str) -> Dataset:
        dataset = DatasetRepository(db).get(dataset_id)
        dataset.is_archived = False
        dataset.archived_at = None
        dataset.status = DatasetStatus.DRAFT.value
        db.commit()
        db.refresh(dataset)
        return dataset

    def update_tags(self, db: Session, dataset_id: str, tags: List[str]) -> Dataset:
        dataset = DatasetRepository(db).get(dataset_id)
        dataset.tags = tags
        db.commit()
        db.refresh(dataset)
        return dataset

    def compare(self, db: Session, dataset_id_a: str, dataset_id_b: str) -> dict:
        repo = DatasetRepository(db)
        a, b = repo.get(dataset_id_a), repo.get(dataset_id_b)
        profile_a = self.get_profile(db, dataset_id_a)
        profile_b = self.get_profile(db, dataset_id_b)
        return {
            "dataset_a": {"id": a.id, "name": a.name, "version": a.version, "row_count": a.row_count},
            "dataset_b": {"id": b.id, "name": b.name, "version": b.version, "row_count": b.row_count},
            "row_count_delta": b.row_count - a.row_count,
            "vocabulary_size_delta": profile_b.vocabulary_size - profile_a.vocabulary_size,
            "label_distribution_a": profile_a.label_distribution,
            "label_distribution_b": profile_b.label_distribution,
        }


dataset_service = DatasetService()

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, ConfigDict

from backend.core.constants import DatasetStatus


class DatasetCreateRequest(BaseModel):
    name: str
    task: str
    description: Optional[str] = None
    label_set: List[str] = []


class TagUpdateRequest(BaseModel):
    tags: List[str]


class DatasetPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    task: str
    description: Optional[str] = None
    label_set: List[str]
    tags: List[str]
    version: int
    parent_version_id: Optional[str] = None
    status: DatasetStatus
    row_count: int
    is_archived: bool
    archived_at: Optional[datetime] = None
    created_by: Optional[str] = None
    modified_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class DatasetRecordPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    dataset_id: str
    text: str
    label: Optional[str] = None
    extra_metadata: Dict[str, Any]
    created_at: datetime


class ValidationIssueSchema(BaseModel):
    kind: str
    message: str
    record_indices: List[int] = []


class ValidationReportSchema(BaseModel):
    total_records: int
    is_valid: bool
    issues: List[ValidationIssueSchema]
    label_distribution: Dict[str, int]
    duplicate_count: int
    empty_count: int
    short_text_count: int
    long_text_count: int
    missing_label_count: int
    invalid_label_count: int


class UploadResponse(BaseModel):
    dataset: DatasetPublic
    validation_report: ValidationReportSchema


class SequenceLengthStatsSchema(BaseModel):
    min_words: int
    max_words: int
    mean_words: float
    median_words: float


class DatasetProfileSchema(BaseModel):
    total_records: int
    vocabulary_size: int
    sequence_length: SequenceLengthStatsSchema
    label_distribution: Dict[str, int]
    top_words: List[Tuple[str, int]]


class AugmentationRequest(BaseModel):
    text: str
    method: Optional[str] = None  # None = run all methods


class AugmentationResultSchema(BaseModel):
    method: str
    original_text: str
    augmented_text: str

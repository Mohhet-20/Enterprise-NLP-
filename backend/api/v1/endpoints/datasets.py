from dataclasses import asdict
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, File, Query, UploadFile
from sqlalchemy.orm import Session

from backend.auth.dependencies import get_current_user
from backend.auth.rbac import require_permission
from backend.core.exceptions import ValidationError
from backend.database.session import get_db_session
from backend.datasets.augmentation import data_augmenter
from backend.schemas.auth import CurrentUser
from backend.schemas.dataset import (
    AugmentationRequest,
    AugmentationResultSchema,
    DatasetCreateRequest,
    DatasetProfileSchema,
    DatasetPublic,
    DatasetRecordPublic,
    TagUpdateRequest,
    UploadResponse,
    ValidationReportSchema,
)
from backend.services.audit_service import audit_service
from backend.services.background_jobs import rebuild_embedding_index_task
from backend.services.dataset_service import dataset_service

router = APIRouter()


@router.post("/datasets", response_model=DatasetPublic, status_code=201)
def create_dataset(
    request: DatasetCreateRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> DatasetPublic:
    require_permission(current_user.role, "dataset:write")
    dataset = dataset_service.create_dataset(
        db,
        name=request.name,
        task=request.task,
        description=request.description,
        label_set=request.label_set,
        created_by=current_user.user_id,
    )
    return DatasetPublic.model_validate(dataset)


MAX_CSV_UPLOAD_BYTES = 10 * 1024 * 1024  # 10MB


@router.post("/datasets/{dataset_id}/upload", response_model=UploadResponse)
async def upload_dataset_csv(
    dataset_id: str,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    apply_cleaning: bool = Query(default=True),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> UploadResponse:
    require_permission(current_user.role, "dataset:write")
    # The filename is only ever used for this extension check — it is
    # never used to construct a filesystem path (uploaded content is
    # parsed in memory and persisted as DatasetRecord rows, never written
    # to disk under a user-supplied name), so path traversal via a
    # crafted filename isn't a live risk here. Documented, not just true
    # by accident.
    if not file.filename.lower().endswith(".csv"):
        raise ValidationError("Only .csv uploads are supported (columns: text, label).")

    raw_bytes = await file.read()
    if len(raw_bytes) > MAX_CSV_UPLOAD_BYTES:
        raise ValidationError(
            f"CSV upload exceeds the {MAX_CSV_UPLOAD_BYTES // (1024*1024)}MB limit "
            f"({len(raw_bytes) / (1024*1024):.1f}MB received)."
        )
    csv_text = raw_bytes.decode("utf-8", errors="replace")

    dataset, report = dataset_service.upload_csv(
        db, dataset_id, csv_text, uploaded_by=current_user.user_id, apply_cleaning=apply_cleaning
    )
    audit_service.record(
        db, action="dataset.uploaded", actor_id=current_user.user_id,
        resource_type="dataset", resource_id=dataset.id,
        details={"row_count": dataset.row_count, "is_valid": report.is_valid},
    )

    # Deferred, best-effort: rebuild the embedding index in the background
    # so the response returns immediately with the validation report
    # rather than waiting on a vectorizer fit. See
    # backend/services/background_jobs.py for why this opens its own DB session.
    background_tasks.add_task(rebuild_embedding_index_task, dataset.id)

    return UploadResponse(
        dataset=DatasetPublic.model_validate(dataset),
        validation_report=ValidationReportSchema(**asdict(report)),
    )


@router.get("/datasets", response_model=list[DatasetPublic])
def list_datasets(
    query: Optional[str] = Query(default=None),
    task: Optional[str] = Query(default=None),
    tag: Optional[str] = Query(default=None),
    include_archived: bool = Query(default=False),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> list[DatasetPublic]:
    require_permission(current_user.role, "dataset:read")
    datasets = dataset_service.list_datasets(db, query=query, task=task, tag=tag, include_archived=include_archived)
    return [DatasetPublic.model_validate(d) for d in datasets]


@router.get("/datasets/{dataset_id}", response_model=DatasetPublic)
def get_dataset(
    dataset_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> DatasetPublic:
    require_permission(current_user.role, "dataset:read")
    return DatasetPublic.model_validate(dataset_service.get_dataset(db, dataset_id))


@router.get("/datasets/{dataset_id}/preview", response_model=list[DatasetRecordPublic])
def preview_dataset(
    dataset_id: str,
    limit: int = Query(default=20, le=200),
    offset: int = Query(default=0),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> list[DatasetRecordPublic]:
    require_permission(current_user.role, "dataset:read")
    records = dataset_service.preview(db, dataset_id, limit=limit, offset=offset)
    return [DatasetRecordPublic.model_validate(r) for r in records]


@router.get("/datasets/{dataset_id}/validation-report", response_model=ValidationReportSchema)
def get_validation_report(
    dataset_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> ValidationReportSchema:
    require_permission(current_user.role, "dataset:read")
    report = dataset_service.get_validation_report(db, dataset_id)
    return ValidationReportSchema(**asdict(report))


@router.get("/datasets/{dataset_id}/profile", response_model=DatasetProfileSchema)
def get_dataset_profile(
    dataset_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> DatasetProfileSchema:
    require_permission(current_user.role, "dataset:read")
    profile = dataset_service.get_profile(db, dataset_id)
    return DatasetProfileSchema(
        total_records=profile.total_records,
        vocabulary_size=profile.vocabulary_size,
        sequence_length=profile.sequence_length.__dict__,
        label_distribution=profile.label_distribution,
        top_words=profile.top_words,
    )


@router.get("/datasets/{dataset_id}/versions", response_model=list[DatasetPublic])
def get_version_history(
    dataset_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> list[DatasetPublic]:
    require_permission(current_user.role, "dataset:read")
    versions = dataset_service.get_version_history(db, dataset_id)
    return [DatasetPublic.model_validate(v) for v in versions]


@router.post("/datasets/{dataset_id}/version", response_model=DatasetPublic, status_code=201)
def create_new_version(
    dataset_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> DatasetPublic:
    require_permission(current_user.role, "dataset:write")
    new_version = dataset_service.create_version(db, dataset_id, created_by=current_user.user_id)
    return DatasetPublic.model_validate(new_version)


@router.post("/datasets/{dataset_id}/archive", response_model=DatasetPublic)
def archive_dataset(
    dataset_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> DatasetPublic:
    require_permission(current_user.role, "dataset:write")
    return DatasetPublic.model_validate(dataset_service.archive(db, dataset_id))


@router.post("/datasets/{dataset_id}/restore", response_model=DatasetPublic)
def restore_dataset(
    dataset_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> DatasetPublic:
    require_permission(current_user.role, "dataset:write")
    return DatasetPublic.model_validate(dataset_service.restore(db, dataset_id))


@router.put("/datasets/{dataset_id}/tags", response_model=DatasetPublic)
def update_tags(
    dataset_id: str,
    request: TagUpdateRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> DatasetPublic:
    require_permission(current_user.role, "dataset:write")
    return DatasetPublic.model_validate(dataset_service.update_tags(db, dataset_id, request.tags))


@router.get("/datasets/compare/{dataset_id_a}/{dataset_id_b}")
def compare_datasets(
    dataset_id_a: str,
    dataset_id_b: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> dict:
    require_permission(current_user.role, "dataset:read")
    return dataset_service.compare(db, dataset_id_a, dataset_id_b)


@router.post("/datasets/augment", response_model=list[AugmentationResultSchema])
def augment_text(
    request: AugmentationRequest,
    current_user: CurrentUser = Depends(get_current_user),
) -> list[AugmentationResultSchema]:
    require_permission(current_user.role, "dataset:write")
    if request.method:
        method = getattr(data_augmenter, request.method, None)
        if method is None:
            raise ValidationError(
                f"Unknown augmentation method {request.method!r}. "
                f"Choose one of: synonym_replacement, random_deletion, random_swap, random_insertion."
            )
        results = [method(request.text)]
    else:
        results = data_augmenter.augment_all_methods(request.text)
    return [AugmentationResultSchema(**r.__dict__) for r in results]

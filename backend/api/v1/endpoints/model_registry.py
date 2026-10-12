from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.auth.dependencies import get_current_user
from backend.auth.rbac import require_any_role, require_permission
from backend.core.constants import ModelLifecycleStage, NLPTask, UserRole
from backend.database.session import get_db_session
from backend.schemas.auth import CurrentUser
from backend.schemas.model_registry import (
    ModelRegistrationRequest,
    ModelRegistryEntryPublic,
    PromotionRequest,
    RejectionRequest,
)
from backend.services.model_registry_service import model_registry_service

router = APIRouter()


@router.post("/models", response_model=ModelRegistryEntryPublic, status_code=201)
def register_model(
    request: ModelRegistrationRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> ModelRegistryEntryPublic:
    require_permission(current_user.role, "experiment:write")
    entry = model_registry_service.register(
        db,
        name=request.name,
        task=request.task,
        architecture=request.architecture,
        version=request.version,
        model_name_or_path=request.model_name_or_path,
        registered_by=current_user.user_id,
        evaluation_run_id=request.evaluation_run_id,
        notes=request.notes,
    )
    return ModelRegistryEntryPublic.model_validate(entry)


@router.get("/models", response_model=list[ModelRegistryEntryPublic])
def list_models(
    task: Optional[NLPTask] = Query(default=None),
    stage: Optional[ModelLifecycleStage] = Query(default=None),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> list[ModelRegistryEntryPublic]:
    require_permission(current_user.role, "experiment:read")
    entries = model_registry_service.list_models(db, task=task, stage=stage)
    return [ModelRegistryEntryPublic.model_validate(e) for e in entries]


@router.get("/models/{entry_id}", response_model=ModelRegistryEntryPublic)
def get_model(
    entry_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> ModelRegistryEntryPublic:
    require_permission(current_user.role, "experiment:read")
    return ModelRegistryEntryPublic.model_validate(model_registry_service.get(db, entry_id))


@router.post("/models/{entry_id}/approve", response_model=ModelRegistryEntryPublic)
def approve_model(
    entry_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> ModelRegistryEntryPublic:
    # Separation of duties: the reviewer approving a model is deliberately
    # gated by role, not by the generic experiment:write permission an
    # ML engineer already has — an engineer shouldn't be able to approve
    # their own submission.
    require_any_role(current_user.role, [UserRole.REVIEWER, UserRole.ADMIN, UserRole.SUPER_ADMIN])
    entry = model_registry_service.approve(db, entry_id, approved_by=current_user.user_id)
    return ModelRegistryEntryPublic.model_validate(entry)


@router.post("/models/{entry_id}/reject", response_model=ModelRegistryEntryPublic)
def reject_model(
    entry_id: str,
    request: RejectionRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> ModelRegistryEntryPublic:
    require_any_role(current_user.role, [UserRole.REVIEWER, UserRole.ADMIN, UserRole.SUPER_ADMIN])
    entry = model_registry_service.reject(db, entry_id, approved_by=current_user.user_id, reason=request.reason)
    return ModelRegistryEntryPublic.model_validate(entry)


@router.post("/models/{entry_id}/promote", response_model=ModelRegistryEntryPublic)
def promote_model(
    entry_id: str,
    request: PromotionRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> ModelRegistryEntryPublic:
    require_permission(current_user.role, "experiment:write")
    entry = model_registry_service.promote(db, entry_id, request.stage)
    return ModelRegistryEntryPublic.model_validate(entry)


@router.post("/models/{entry_id}/deploy", response_model=ModelRegistryEntryPublic)
def deploy_model(
    entry_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> ModelRegistryEntryPublic:
    require_permission(current_user.role, "experiment:write")
    entry = model_registry_service.deploy(db, entry_id, deployed_by=current_user.user_id)
    return ModelRegistryEntryPublic.model_validate(entry)


@router.post("/models/{entry_id}/rollback", response_model=ModelRegistryEntryPublic)
def rollback_model(
    entry_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> ModelRegistryEntryPublic:
    require_permission(current_user.role, "experiment:write")
    entry = model_registry_service.rollback(db, entry_id, rolled_back_by=current_user.user_id)
    return ModelRegistryEntryPublic.model_validate(entry)


@router.post("/models/{entry_id}/set-champion", response_model=ModelRegistryEntryPublic)
def set_champion(
    entry_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> ModelRegistryEntryPublic:
    require_permission(current_user.role, "experiment:write")
    entry = model_registry_service.set_champion(db, entry_id, actor_id=current_user.user_id)
    return ModelRegistryEntryPublic.model_validate(entry)


@router.get("/models/compare/{entry_id_a}/{entry_id_b}")
def compare_models(
    entry_id_a: str,
    entry_id_b: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> dict:
    require_permission(current_user.role, "experiment:read")
    return model_registry_service.compare(db, entry_id_a, entry_id_b)

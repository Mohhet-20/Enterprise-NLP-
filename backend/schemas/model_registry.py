from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

from backend.core.constants import ApprovalStatus, DeploymentStatus, ModelLifecycleStage, NLPTask


class ModelRegistrationRequest(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    name: str
    task: NLPTask
    architecture: str
    version: str
    model_name_or_path: str
    evaluation_run_id: Optional[str] = None
    notes: Optional[str] = None


class RejectionRequest(BaseModel):
    reason: str


class PromotionRequest(BaseModel):
    stage: ModelLifecycleStage


class ModelRegistryEntryPublic(BaseModel):
    model_config = ConfigDict(protected_namespaces=(), from_attributes=True)

    id: str
    name: str
    task: NLPTask
    architecture: str
    version: str
    model_name_or_path: str
    stage: ModelLifecycleStage
    approval_status: ApprovalStatus
    deployment_status: DeploymentStatus
    is_champion: bool
    evaluation_run_id: Optional[str] = None
    accuracy: Optional[float] = None
    macro_f1: Optional[float] = None
    registered_by: Optional[str] = None
    approved_by: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

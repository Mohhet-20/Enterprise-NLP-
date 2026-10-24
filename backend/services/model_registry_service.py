"""
Model Registry orchestration.

The business rules enforced here (each raises on violation) are what make
this a registry rather than a CRUD table:

- A model can only be promoted to PRODUCTION once it's APPROVED.
- A model can only be deployed once it's in PRODUCTION and APPROVED.
- Deploying a model automatically rolls back whatever was previously
  deployed *for the same task* — there is never more than one "deployed"
  entry per task at a time.
- Setting a champion automatically un-champions the previous champion for
  that task — there is never more than one champion per task.
"""

from typing import List, Optional

from sqlalchemy.orm import Session

from backend.core.constants import ApprovalStatus, DeploymentStatus, ModelLifecycleStage, NLPTask
from backend.core.exceptions import InvalidStageTransitionError, ModelNotApprovedError
from backend.models.model_registry_entry import ModelRegistryEntry
from backend.repositories.model_registry_repository import ModelRegistryRepository
from backend.services.audit_service import audit_service
from backend.services.base_service import BaseService


class ModelRegistryService(BaseService):
    def register(
        self,
        db: Session,
        *,
        name: str,
        task: NLPTask,
        architecture: str,
        version: str,
        model_name_or_path: str,
        registered_by: str,
        evaluation_run_id: Optional[str] = None,
        accuracy: Optional[float] = None,
        macro_f1: Optional[float] = None,
        notes: Optional[str] = None,
    ) -> ModelRegistryEntry:
        entry = ModelRegistryEntry(
            name=name,
            task=task.value,
            architecture=architecture,
            version=version,
            model_name_or_path=model_name_or_path,
            registered_by=registered_by,
            evaluation_run_id=evaluation_run_id,
            accuracy=accuracy,
            macro_f1=macro_f1,
            notes=notes,
        )
        return ModelRegistryRepository(db).create(entry)

    def get(self, db: Session, entry_id: str) -> ModelRegistryEntry:
        return ModelRegistryRepository(db).get(entry_id)

    def list_models(
        self, db: Session, *, task: Optional[NLPTask] = None, stage: Optional[ModelLifecycleStage] = None
    ) -> List[ModelRegistryEntry]:
        return ModelRegistryRepository(db).list_filtered(
            task=task.value if task else None, stage=stage.value if stage else None
        )

    def approve(self, db: Session, entry_id: str, approved_by: str) -> ModelRegistryEntry:
        entry = self.get(db, entry_id)
        entry.approval_status = ApprovalStatus.APPROVED.value
        entry.approved_by = approved_by
        db.commit()
        db.refresh(entry)
        audit_service.record(
            db, action="model.approved", actor_id=approved_by,
            resource_type="model_registry_entry", resource_id=entry.id,
            details={"name": entry.name, "version": entry.version},
        )
        return entry

    def reject(self, db: Session, entry_id: str, approved_by: str, reason: str) -> ModelRegistryEntry:
        entry = self.get(db, entry_id)
        entry.approval_status = ApprovalStatus.REJECTED.value
        entry.approved_by = approved_by
        entry.notes = f"{entry.notes or ''}\nRejected: {reason}".strip()
        db.commit()
        db.refresh(entry)
        audit_service.record(
            db, action="model.rejected", actor_id=approved_by,
            resource_type="model_registry_entry", resource_id=entry.id,
            details={"name": entry.name, "version": entry.version, "reason": reason},
        )
        return entry

    def promote(self, db: Session, entry_id: str, target_stage: ModelLifecycleStage) -> ModelRegistryEntry:
        entry = self.get(db, entry_id)

        if target_stage == ModelLifecycleStage.PRODUCTION and entry.approval_status != ApprovalStatus.APPROVED.value:
            raise ModelNotApprovedError(
                f"Model {entry.name!r} v{entry.version} must be approved before promotion to production "
                f"(current approval status: {entry.approval_status})."
            )

        if entry.stage == ModelLifecycleStage.ARCHIVED.value:
            raise InvalidStageTransitionError("An archived model cannot be promoted — register a new version instead.")

        entry.stage = target_stage.value
        db.commit()
        db.refresh(entry)
        return entry

    def deploy(self, db: Session, entry_id: str, deployed_by: Optional[str] = None) -> ModelRegistryEntry:
        entry = self.get(db, entry_id)
        repo = ModelRegistryRepository(db)

        if entry.approval_status != ApprovalStatus.APPROVED.value:
            raise ModelNotApprovedError(
                f"Model {entry.name!r} v{entry.version} must be approved before deployment."
            )
        if entry.stage != ModelLifecycleStage.PRODUCTION.value:
            raise InvalidStageTransitionError(
                f"Model {entry.name!r} v{entry.version} must be promoted to production before deployment "
                f"(current stage: {entry.stage})."
            )

        # Rollback whatever was previously deployed for this task — a
        # task never has more than one deployed model at a time.
        previously_deployed = repo.find_deployed_for_task(entry.task)
        rolled_back_id = None
        if previously_deployed is not None and previously_deployed.id != entry.id:
            previously_deployed.deployment_status = DeploymentStatus.ROLLED_BACK.value
            rolled_back_id = previously_deployed.id

        entry.deployment_status = DeploymentStatus.DEPLOYED.value
        db.commit()
        db.refresh(entry)
        audit_service.record(
            db, action="model.deployed", actor_id=deployed_by,
            resource_type="model_registry_entry", resource_id=entry.id,
            details={"name": entry.name, "version": entry.version, "auto_rolled_back": rolled_back_id},
        )
        return entry

    def rollback(self, db: Session, entry_id: str, rolled_back_by: Optional[str] = None) -> ModelRegistryEntry:
        entry = self.get(db, entry_id)
        entry.deployment_status = DeploymentStatus.ROLLED_BACK.value
        db.commit()
        db.refresh(entry)
        audit_service.record(
            db, action="model.rolled_back", actor_id=rolled_back_by,
            resource_type="model_registry_entry", resource_id=entry.id,
        )
        return entry

    def set_champion(self, db: Session, entry_id: str, actor_id: Optional[str] = None) -> ModelRegistryEntry:
        entry = self.get(db, entry_id)
        repo = ModelRegistryRepository(db)

        current_champion = repo.find_champion_for_task(entry.task)
        if current_champion is not None and current_champion.id != entry.id:
            current_champion.is_champion = False

        entry.is_champion = True
        db.commit()
        db.refresh(entry)
        audit_service.record(
            db, action="model.champion_set", actor_id=actor_id,
            resource_type="model_registry_entry", resource_id=entry.id,
        )
        return entry

    def compare(self, db: Session, entry_id_a: str, entry_id_b: str) -> dict:
        a = self.get(db, entry_id_a)
        b = self.get(db, entry_id_b)
        return {
            "model_a": {"id": a.id, "name": a.name, "version": a.version, "accuracy": a.accuracy, "macro_f1": a.macro_f1},
            "model_b": {"id": b.id, "name": b.name, "version": b.version, "accuracy": b.accuracy, "macro_f1": b.macro_f1},
            "accuracy_delta": (
                round(a.accuracy - b.accuracy, 4) if a.accuracy is not None and b.accuracy is not None else None
            ),
            "macro_f1_delta": (
                round(a.macro_f1 - b.macro_f1, 4) if a.macro_f1 is not None and b.macro_f1 is not None else None
            ),
        }


model_registry_service = ModelRegistryService()

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.auth.dependencies import get_current_user
from backend.auth.rbac import require_permission
from backend.database.session import get_db_session
from backend.schemas.audit import AuditLogPublic
from backend.schemas.auth import CurrentUser
from backend.services.audit_service import audit_service

router = APIRouter()


@router.get("/audit-logs", response_model=list[AuditLogPublic])
def list_audit_logs(
    actor_id: Optional[str] = Query(default=None),
    action: Optional[str] = Query(default=None),
    resource_type: Optional[str] = Query(default=None),
    resource_id: Optional[str] = Query(default=None),
    limit: int = Query(default=100, le=500),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> list[AuditLogPublic]:
    # audit:read is granted to Auditor, Admin, Super Admin only — the
    # audit trail is deliberately not readable by everyone who can read
    # experiments/datasets.
    require_permission(current_user.role, "audit:read")
    logs = audit_service.search(
        db, actor_id=actor_id, action=action, resource_type=resource_type, resource_id=resource_id, limit=limit
    )
    return [AuditLogPublic.model_validate(log) for log in logs]

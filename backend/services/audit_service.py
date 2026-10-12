"""
Single write path for the audit trail — every caller (auth, model
registry, dataset service, ...) goes through `audit_service.record(...)`
rather than constructing `AuditLog` rows directly, so the shape of an
audit entry can't drift between subsystems.
"""

from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from backend.models.audit_log import AuditLog
from backend.repositories.audit_log_repository import AuditLogRepository
from backend.services.base_service import BaseService


class AuditService(BaseService):
    def record(
        self,
        db: Session,
        *,
        action: str,
        actor_id: Optional[str] = None,
        actor_username: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
    ) -> AuditLog:
        entry = AuditLog(
            action=action,
            actor_id=actor_id,
            actor_username=actor_username,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details or {},
            ip_address=ip_address,
        )
        return AuditLogRepository(db).create(entry)

    def search(
        self,
        db: Session,
        *,
        actor_id: Optional[str] = None,
        action: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[AuditLog]:
        return AuditLogRepository(db).search(
            actor_id=actor_id, action=action, resource_type=resource_type, resource_id=resource_id, limit=limit
        )


audit_service = AuditService()

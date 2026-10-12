"""
A persisted, queryable audit trail — distinct from the structured JSON
logs the platform already emits (backend/config/logging_config.py).
Logs are for operators grepping/aggregating in a log platform; this table
is for "show me every action user X took" or "who approved this model"
as a first-class query, which structured logs don't support without
shipping them somewhere else first.

Written synchronously in the same request as the action it records
(never as a fire-and-forget background task) — audit correctness matters
for compliance, so it shouldn't be silently droppable if the process
restarts before a background task runs.
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy import JSON, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.database.base import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    actor_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    actor_username: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    action: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    resource_type: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    resource_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)

    details: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    ip_address: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True
    )

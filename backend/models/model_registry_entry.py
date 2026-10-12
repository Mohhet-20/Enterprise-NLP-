"""
A registered model version and its position in the promotion lifecycle:
development -> staging -> production, gated by an approval step, with
champion/challenger tracking (only one champion per task at a time) and
rollback support (deploying a new model demotes the previously deployed
one rather than leaving two "deployed" entries for the same task).

`accuracy`/`macro_f1` are denormalized from an evaluation run at
registration time so the registry can be listed/sorted without joining
out to the evaluation store on every request — a deliberate tradeoff
(read performance over normalization) common in real model registries.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Boolean, DateTime, Float, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.core.constants import ApprovalStatus, DeploymentStatus, ModelLifecycleStage
from backend.database.base import Base


class ModelRegistryEntry(Base):
    __tablename__ = "model_registry_entries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    task: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    architecture: Mapped[str] = mapped_column(String(64), nullable=False)
    version: Mapped[str] = mapped_column(String(32), nullable=False)
    model_name_or_path: Mapped[str] = mapped_column(String(255), nullable=False)

    stage: Mapped[str] = mapped_column(String(32), default=ModelLifecycleStage.DEVELOPMENT.value)
    approval_status: Mapped[str] = mapped_column(String(32), default=ApprovalStatus.PENDING.value)
    deployment_status: Mapped[str] = mapped_column(String(32), default=DeploymentStatus.NOT_DEPLOYED.value)
    is_champion: Mapped[bool] = mapped_column(Boolean, default=False)

    evaluation_run_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    accuracy: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    macro_f1: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    registered_by: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    approved_by: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

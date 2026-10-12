"""
A dataset's metadata (not its rows — see dataset_record.py for those).

Versioning is a simple parent-pointer chain rather than a separate
"DatasetVersion" table: creating a new version copies this row with a new
id, an incremented `version` number, and `parent_version_id` pointing back
— enough to answer "what changed since v1" by walking the chain, without
the join complexity of a fully normalized version-history table. A real
data-lake-scale platform would likely need the heavier design; this is
the right-sized version for what this platform actually stores.

Soft delete: `is_archived` + `archived_at`, never a hard DELETE — matches
the "Archiving / Restoration" requirement and keeps dataset lineage intact
(an archived dataset that was used to train a still-deployed model
shouldn't disappear from the audit trail).
"""

import uuid
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import JSON, Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.core.constants import DatasetStatus
from backend.database.base import Base


class Dataset(Base):
    __tablename__ = "datasets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    task: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)

    label_set: Mapped[List[str]] = mapped_column(JSON, default=list)
    tags: Mapped[List[str]] = mapped_column(JSON, default=list)

    version: Mapped[int] = mapped_column(Integer, default=1)
    parent_version_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)

    status: Mapped[str] = mapped_column(String(32), default=DatasetStatus.DRAFT.value)
    row_count: Mapped[int] = mapped_column(Integer, default=0)

    is_archived: Mapped[bool] = mapped_column(Boolean, default=False)
    archived_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # --- Audit fields ---
    created_by: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    modified_by: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

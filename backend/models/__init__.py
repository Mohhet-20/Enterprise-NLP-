"""
Every concrete ORM model must be imported here so `Base.metadata` knows
about it before `Base.metadata.create_all(...)` runs (see
backend/database/session.py::init_db). A model defined but never imported
anywhere is invisible to `create_all` — this file is that single import
point.

(This fixes a gap from the initial architecture skeleton: this file was
empty, so `Experiment` was technically never registered on startup unless
something else happened to import it first.)
"""

from backend.models.audit_log import AuditLog
from backend.models.dataset import Dataset
from backend.models.dataset_record import DatasetRecord
from backend.models.experiment import Experiment
from backend.models.model_registry_entry import ModelRegistryEntry
from backend.models.refresh_token import RefreshToken
from backend.models.user import User

__all__ = ["AuditLog", "Dataset", "DatasetRecord", "Experiment", "ModelRegistryEntry", "RefreshToken", "User"]

"""
Lightweight experiment tracking.

Backed by the `Experiment` ORM model / `ExperimentRepository` for anything
that needs to be queryable (status, task, model), and by flat JSON files on
disk (under `settings.experiments_dir`) for the free-form parts (full
hyperparameter dumps, metric history) that don't need a schema. Swap the
JSON-file store for MLflow/W&B later without touching callers of this class.
"""

import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from backend.config.settings import get_settings
from backend.core.constants import ExperimentStatus


@dataclass
class ExperimentRecord:
    experiment_id: str
    name: str
    task: str
    model_name: str
    hyperparameters: Dict[str, Any]
    status: str = ExperimentStatus.PENDING.value
    metric_history: List[Dict[str, float]] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ExperimentTracker:
    def __init__(self, storage_dir: Optional[str] = None) -> None:
        self._storage_dir = storage_dir or get_settings().experiments_dir
        os.makedirs(self._storage_dir, exist_ok=True)

    def _path_for(self, experiment_id: str) -> str:
        return os.path.join(self._storage_dir, f"{experiment_id}.json")

    def create(self, record: ExperimentRecord) -> ExperimentRecord:
        with open(self._path_for(record.experiment_id), "w") as f:
            json.dump(asdict(record), f, indent=2)
        return record

    def log_metrics(self, experiment_id: str, metrics: Dict[str, float]) -> None:
        record = self.load(experiment_id)
        record.metric_history.append(metrics)
        with open(self._path_for(experiment_id), "w") as f:
            json.dump(asdict(record), f, indent=2)

    def load(self, experiment_id: str) -> ExperimentRecord:
        with open(self._path_for(experiment_id)) as f:
            data = json.load(f)
        return ExperimentRecord(**data)

    def compare(self, experiment_ids: List[str], metric: str) -> Dict[str, Optional[float]]:
        """Return the latest value of `metric` for each experiment, for
        side-by-side comparison."""
        result: Dict[str, Optional[float]] = {}
        for exp_id in experiment_ids:
            record = self.load(exp_id)
            latest = record.metric_history[-1] if record.metric_history else {}
            result[exp_id] = latest.get(metric)
        return result

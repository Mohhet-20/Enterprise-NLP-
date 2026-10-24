"""
Persists full evaluation run results as JSON files, the same pattern
`backend/experiments/experiment_tracker.py` already uses — deliberately
not a new persistence mechanism, just that mechanism applied to a
different artifact (a completed evaluation report rather than an
in-progress training run's metric history).
"""

import json
import os
import uuid
from typing import Any, Dict, List, Optional

from backend.config.settings import get_settings


class EvaluationRunStore:
    def __init__(self, storage_dir: Optional[str] = None) -> None:
        self._storage_dir = storage_dir or get_settings().evaluation_runs_dir
        os.makedirs(self._storage_dir, exist_ok=True)

    def _path_for(self, run_id: str) -> str:
        # run_id arrives from a URL path segment; only canonical UUIDs may
        # ever reach the filesystem (blocks "..\\" traversal on Windows).
        try:
            canonical = str(uuid.UUID(run_id))
        except (ValueError, TypeError, AttributeError):
            raise FileNotFoundError(run_id) from None
        return os.path.join(self._storage_dir, f"{canonical}.json")

    def save(self, run_id: str, result: Dict[str, Any]) -> None:
        with open(self._path_for(run_id), "w") as f:
            json.dump(result, f, indent=2)

    def load(self, run_id: str) -> Dict[str, Any]:
        with open(self._path_for(run_id)) as f:
            return json.load(f)

    def exists(self, run_id: str) -> bool:
        try:
            return os.path.exists(self._path_for(run_id))
        except FileNotFoundError:
            return False

    def list_summaries(self) -> List[Dict[str, Any]]:
        summaries = []
        for filename in os.listdir(self._storage_dir):
            if not filename.endswith(".json"):
                continue
            with open(os.path.join(self._storage_dir, filename)) as f:
                data = json.load(f)
            summaries.append(
                {
                    "run_id": data["run_id"],
                    "task": data["task"],
                    "model_name": data["model_name"],
                    "model_kind": data.get("model_kind", "lexicon_baseline"),
                    "eval_set": data.get("eval_set", "challenge_set"),
                    "macro_f1": data.get("macro_f1"),
                    "created_at": data["created_at"],
                    "accuracy": data["accuracy"],
                    "num_samples": data["num_samples"],
                }
            )
        summaries.sort(key=lambda s: s["created_at"], reverse=True)
        return summaries


evaluation_run_store = EvaluationRunStore()

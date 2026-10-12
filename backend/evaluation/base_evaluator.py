"""Evaluation subsystem: computes metrics for a model against a dataset
split. Kept separate from training so a model can be re-evaluated (e.g. on
a new test set) without retraining."""

from abc import ABC, abstractmethod
from typing import Dict, List


class BaseEvaluator(ABC):
    @abstractmethod
    def evaluate(self, predictions: List[str], references: List[str]) -> Dict[str, float]:
        """Return a metrics dict, e.g. {'accuracy': 0.91, 'f1_macro': 0.89}."""
        raise NotImplementedError


class ClassificationEvaluator(BaseEvaluator):
    """Reference implementation covering the common classification metrics.
    Deliberately dependency-light (no sklearn requirement at skeleton
    stage) — swap in sklearn.metrics once the dependency is added."""

    def evaluate(self, predictions: List[str], references: List[str]) -> Dict[str, float]:
        if len(predictions) != len(references):
            raise ValueError("predictions and references must be the same length.")
        if not predictions:
            return {"accuracy": 0.0, "support": 0}

        correct = sum(p == r for p, r in zip(predictions, references))
        return {
            "accuracy": correct / len(predictions),
            "support": len(predictions),
        }

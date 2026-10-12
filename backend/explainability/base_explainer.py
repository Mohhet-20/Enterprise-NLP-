"""Explainability subsystem interface. Real implementations (SHAP,
Captum integrated-gradients, attention-weight visualization) plug in here
later — the API/service layers depend only on this contract."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List


@dataclass
class TokenAttribution:
    token: str
    importance: float


class BaseExplainer(ABC):
    @abstractmethod
    def explain(self, text: str, predicted_label: str) -> List[TokenAttribution]:
        """Return a per-token importance score for the given prediction."""
        raise NotImplementedError

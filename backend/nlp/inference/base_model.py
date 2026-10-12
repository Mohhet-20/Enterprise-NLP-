"""
Strategy interface every model backend must implement.

This is the seam that lets BERT, RoBERTa, DeBERTa, DistilBERT, ELECTRA,
MiniLM, MPNet, Sentence-Transformers, or any future architecture plug into
the platform identically. Nothing outside `backend/nlp/inference/` should
ever import a specific model class directly — always go through
`ModelFactory` (model_factory.py) and depend on `BaseNLPModel`.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List

from backend.core.constants import NLPTask


@dataclass
class Prediction:
    label: str
    score: float
    raw_scores: Dict[str, float] = field(default_factory=dict)


class BaseNLPModel(ABC):
    """
    Strategy interface. Every concrete model (BertModel, DistilBertModel,
    ...) implements `load` and `predict`. The rest of the platform only
    ever calls these two methods.
    """

    model_name: str
    supported_tasks: List[NLPTask]

    def __init__(self, model_name: str) -> None:
        self.model_name = model_name
        self._is_loaded = False

    @abstractmethod
    def load(self) -> None:
        """Load weights/tokenizer into memory. Called lazily on first use
        and cached by ModelFactory — implementations should be idempotent
        and cheap to call more than once."""
        raise NotImplementedError

    @abstractmethod
    def predict(self, text: str, task: NLPTask, **kwargs) -> List[Prediction]:
        raise NotImplementedError

    @property
    def is_loaded(self) -> bool:
        return self._is_loaded

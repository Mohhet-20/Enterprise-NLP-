"""
Strategy interface every model backend must implement.

This is the seam that lets BERT, RoBERTa, DeBERTa, DistilBERT, XLM-R,
Sentence-Transformers, or any future architecture plug into
the platform identically. Nothing outside `backend/nlp/inference/` should
ever import a specific model class directly — always go through
`ModelFactory` (model_factory.py) and depend on `BaseNLPModel`.
"""

import functools
import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List

from backend.core.constants import NLPTask


@dataclass
class Prediction:
    label: str
    score: float
    raw_scores: Dict[str, float] = field(default_factory=dict)


# One model loads at a time, process-wide: a request arriving while a model is being preloaded waits for it instead
# of loading a second copy (which on a small host is the difference between fitting in memory and not).
_LOAD_LOCK = threading.RLock()


class BaseNLPModel(ABC):
    """
    Strategy interface. Every concrete model (BertModel, DistilBertModel,
    ...) implements `load` and `predict`. The rest of the platform only
    ever calls these two methods.
    """

    model_name: str
    supported_tasks: List[NLPTask]

    def __init_subclass__(cls, **kwargs) -> None:
        super().__init_subclass__(**kwargs)
        own_load = cls.__dict__.get("load")
        if own_load is None or getattr(own_load, "_serialised", False):
            return

        @functools.wraps(own_load)
        def load(self) -> None:
            if self._is_loaded:
                return
            with _LOAD_LOCK:
                own_load(self)  # implementations re-check _is_loaded, so a waiter returns immediately

        load._serialised = True  # type: ignore[attr-defined]
        cls.load = load  # type: ignore[method-assign]

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

    def predict_batch(self, texts: List[str], task: NLPTask, **kwargs) -> List[List[Prediction]]:
        """Default batch implementation: one forward pass per text.
        Backends that can pad-and-stack (see BertModel) override this."""
        return [self.predict(text, task, **kwargs) for text in texts]

    def unload(self) -> None:
        """Release weights so the factory can enforce its memory cap. The
        next predict() reloads lazily."""
        for attr in ("_model", "_tokenizer", "_pipeline"):
            if hasattr(self, attr):
                delattr(self, attr)
        self._is_loaded = False

    @property
    def is_loaded(self) -> bool:
        return self._is_loaded

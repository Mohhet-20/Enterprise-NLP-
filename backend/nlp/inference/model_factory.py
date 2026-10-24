"""
Factory pattern: the ONLY place in the platform that knows how to turn a
`ModelArchitecture` + model name into a concrete `BaseNLPModel` instance.

To add a new architecture:
  1. Implement `BaseNLPModel` under `backend/nlp/inference/models/` (most
     `transformers` encoders need nothing new — they reuse `BertModel`).
  2. Add one line to `_ARCHITECTURE_REGISTRY` below.

Instances are cached per (architecture, model_name, task-family). Because
loaded weights are large (100MB–1GB each), the cache also enforces an LRU
cap on how many models may be *loaded* at once (`max_loaded_models`):
when a new model is requested beyond the cap, the least recently used
loaded model has its weights released. It reloads transparently on next use.
"""

import gc
from collections import OrderedDict
from typing import Dict, Optional, Type

from backend.config.settings import get_settings
from backend.core.constants import ModelArchitecture, NLPTask
from backend.core.exceptions import ModelNotFoundError
from backend.nlp.inference.base_model import BaseNLPModel
from backend.nlp.inference.models.bert_model import BertModel
from backend.nlp.inference.models.distilbert_model import DistilBertModel
from backend.nlp.inference.models.sentence_transformer_model import SentenceTransformerModel
from backend.nlp.inference.models.zero_shot_model import ZeroShotModel

_ARCHITECTURE_REGISTRY: Dict[ModelArchitecture, Type[BaseNLPModel]] = {
    ModelArchitecture.BERT: BertModel,
    ModelArchitecture.DISTILBERT: DistilBertModel,
    ModelArchitecture.ROBERTA: BertModel,
    ModelArchitecture.DEBERTA: BertModel,
    ModelArchitecture.XLM_ROBERTA: BertModel,
    ModelArchitecture.SENTENCE_TRANSFORMER: SentenceTransformerModel,
}

# Some tasks need a different inference strategy regardless of the encoder
# underneath (zero-shot runs NLI over label hypotheses, not a plain head).
_TASK_STRATEGY_OVERRIDES: Dict[NLPTask, Type[BaseNLPModel]] = {
    NLPTask.ZERO_SHOT_CLASSIFICATION: ZeroShotModel,
}


class ModelFactory:
    """Creates and caches model instances; bounds how many are loaded."""

    def __init__(self, max_loaded_models: Optional[int] = None) -> None:
        self._cache: "OrderedDict[tuple, BaseNLPModel]" = OrderedDict()
        self._max_loaded = max_loaded_models or get_settings().max_loaded_models

    def get_model(
        self, architecture: ModelArchitecture, model_name: str, task: Optional[NLPTask] = None
    ) -> BaseNLPModel:
        model_cls = _TASK_STRATEGY_OVERRIDES.get(task) if task else None
        model_cls = model_cls or _ARCHITECTURE_REGISTRY.get(architecture)
        if model_cls is None:
            raise ModelNotFoundError(
                f"No model implementation registered for architecture '{architecture.value}'."
            )

        cache_key = (architecture, model_name, model_cls.__name__)
        instance = self._cache.get(cache_key)
        if instance is None:
            instance = model_cls(model_name)
            self._cache[cache_key] = instance
        self._cache.move_to_end(cache_key)
        self._evict_if_needed(keep=cache_key)
        return instance

    def _evict_if_needed(self, keep: tuple) -> None:
        loaded = [key for key, inst in self._cache.items() if inst.is_loaded and key != keep]
        # `keep` is about to be (or already is) loaded, so it counts toward the cap.
        evicted = False
        while len(loaded) + 1 > self._max_loaded and loaded:
            victim = loaded.pop(0)
            self._cache[victim].unload()
            evicted = True
        # A full collection costs ~150ms with transformer weights on the heap,
        # so only pay it when weights were actually released.
        if evicted:
            gc.collect()

    def list_cached_models(self) -> Dict[str, bool]:
        """Which (architecture, model_name) pairs have been instantiated, and
        whether their weights are currently loaded into memory."""
        return {
            f"{architecture.value}:{model_name}": instance.is_loaded
            for (architecture, model_name, _), instance in self._cache.items()
        }

    def registered_architectures(self) -> list[str]:
        return [a.value for a in _ARCHITECTURE_REGISTRY.keys()]


# Process-wide factory instance (models are cached in memory once loaded).
model_factory = ModelFactory()

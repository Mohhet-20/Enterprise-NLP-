"""
Factory pattern: the ONLY place in the platform that knows how to turn a
`ModelArchitecture` + model name into a concrete `BaseNLPModel` instance.

To add a new architecture (e.g. RoBERTa):
  1. Create `backend/nlp/inference/models/roberta_model.py` implementing BaseNLPModel.
  2. Add one line to `_ARCHITECTURE_REGISTRY` below.
That's it — no other file in the platform needs to change.
"""

from typing import Dict, Type

from backend.core.constants import ModelArchitecture
from backend.core.exceptions import ModelNotFoundError
from backend.nlp.inference.base_model import BaseNLPModel
from backend.nlp.inference.models.bert_model import BertModel
from backend.nlp.inference.models.distilbert_model import DistilBertModel

_ARCHITECTURE_REGISTRY: Dict[ModelArchitecture, Type[BaseNLPModel]] = {
    ModelArchitecture.BERT: BertModel,
    ModelArchitecture.DISTILBERT: DistilBertModel,
    # ModelArchitecture.ROBERTA: RobertaModel,          # add as implemented
    # ModelArchitecture.DEBERTA: DebertaModel,          # add as implemented
    # ModelArchitecture.ELECTRA: ElectraModel,          # add as implemented
    # ModelArchitecture.MINILM: MiniLMModel,            # add as implemented
    # ModelArchitecture.MPNET: MPNetModel,               # add as implemented
    # ModelArchitecture.SENTENCE_TRANSFORMER: SentenceTransformerModel,
}


class ModelFactory:
    """Creates and caches model instances by (architecture, model_name)."""

    def __init__(self) -> None:
        self._cache: Dict[tuple, BaseNLPModel] = {}

    def get_model(self, architecture: ModelArchitecture, model_name: str) -> BaseNLPModel:
        cache_key = (architecture, model_name)
        if cache_key in self._cache:
            return self._cache[cache_key]

        model_cls = _ARCHITECTURE_REGISTRY.get(architecture)
        if model_cls is None:
            raise ModelNotFoundError(
                f"No model implementation registered for architecture '{architecture.value}'."
            )

        instance = model_cls(model_name)
        self._cache[cache_key] = instance
        return instance

    def list_cached_models(self) -> Dict[str, bool]:
        """Public introspection for health/observability checks — which
        (architecture, model_name) pairs have been instantiated, and
        whether their weights are actually loaded into memory yet
        (lazy-loaded on first predict() call, so a cached instance may
        still be pre-load)."""
        return {
            f"{architecture.value}:{model_name}": instance.is_loaded
            for (architecture, model_name), instance in self._cache.items()
        }

    def registered_architectures(self) -> list[str]:
        return [a.value for a in _ARCHITECTURE_REGISTRY.keys()]


# Process-wide factory instance (models are cached in memory once loaded).
model_factory = ModelFactory()

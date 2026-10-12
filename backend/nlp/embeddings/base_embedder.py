"""Strategy interface for embedding generation (semantic similarity,
retrieval, clustering). Mirrors the BaseNLPModel pattern used for
classification models so both subsystems stay consistent."""

from abc import ABC, abstractmethod
from typing import List


class BaseEmbedder(ABC):
    def __init__(self, model_name: str) -> None:
        self.model_name = model_name

    @abstractmethod
    def embed(self, texts: List[str]) -> List[List[float]]:
        """Return one dense vector per input text."""
        raise NotImplementedError

    @abstractmethod
    def similarity(self, text_a: str, text_b: str) -> float:
        """Return a similarity score (typically cosine similarity) in [-1, 1]."""
        raise NotImplementedError

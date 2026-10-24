"""
Per-dataset vector index for semantic search and record-to-record similarity.

Two encoders sit behind one interface:
  - "dense" (default): the TEXT_EMBEDDINGS plugin model
    (sentence-transformers/all-MiniLM-L6-v2) — captures meaning, so
    "great battery performance" finds "lasts all day long" with no word overlap
  - "tfidf": scikit-learn TF-IDF over word 1–2-grams — lexical only, but
    needs no model download; used by the unit tests and as a fallback when
    the ML extras aren't installed

Vectors are L2-normalised, so cosine similarity is a matrix-vector dot
product. Search is exact (brute force): at the 50k-record upload cap that
is a single (50k × 384) matvec, well under 100ms on CPU — an ANN index
(FAISS / pgvector) only pays for itself well beyond that.
"""

import time
from dataclasses import dataclass
from typing import Dict, List, Optional

import numpy as np

from backend.config.settings import get_settings
from backend.core.exceptions import EmptyDatasetError, RecordNotFoundError


class TfidfEncoder:
    name = "tfidf"

    def __init__(self) -> None:
        from sklearn.feature_extraction.text import TfidfVectorizer

        self._vectorizer = TfidfVectorizer(max_features=5000, ngram_range=(1, 2))

    def fit_encode(self, texts: List[str]) -> np.ndarray:
        return self._normalise(self._vectorizer.fit_transform(texts).toarray())

    def encode(self, texts: List[str]) -> np.ndarray:
        return self._normalise(self._vectorizer.transform(texts).toarray())

    @property
    def model_name(self) -> str:
        return "tfidf-1-2gram"

    @staticmethod
    def _normalise(m: np.ndarray) -> np.ndarray:
        norms = np.linalg.norm(m, axis=1, keepdims=True)
        return m / np.where(norms == 0, 1, norms)


class DenseEncoder:
    name = "dense"

    def __init__(self) -> None:
        from backend.core.constants import NLPTask
        from backend.nlp.inference.model_factory import model_factory
        from backend.plugins.plugin_registry import get_task_plugin

        plugin = get_task_plugin(NLPTask.TEXT_EMBEDDINGS)
        self.model_name = plugin.default_model_name
        self._model = model_factory.get_model(plugin.default_architecture, self.model_name)

    def fit_encode(self, texts: List[str]) -> np.ndarray:
        return self.encode(texts)

    def encode(self, texts: List[str]) -> np.ndarray:
        vectors = np.asarray(self._model.embed(texts), dtype=np.float32)
        return TfidfEncoder._normalise(vectors)


@dataclass
class EmbeddingIndexStats:
    dataset_id: str
    num_vectors: int
    dimension: int
    encoder: str
    model_name: str
    build_seconds: float
    built_at: float


@dataclass
class NearestNeighborResult:
    record_id: str
    text: str
    label: Optional[str]
    similarity: float


class EmbeddingIndex:
    def __init__(
        self, dataset_id: str, record_ids: List[str], texts: List[str], labels: List[Optional[str]], encoder
    ) -> None:
        self.dataset_id = dataset_id
        self.record_ids = record_ids
        self.texts = texts
        self.labels = labels
        self.encoder = encoder
        self._row_of = {rid: i for i, rid in enumerate(record_ids)}

        started = time.perf_counter()
        self.matrix = encoder.fit_encode(texts)
        self.build_seconds = time.perf_counter() - started
        self.built_at = time.time()

    def stats(self) -> EmbeddingIndexStats:
        return EmbeddingIndexStats(
            dataset_id=self.dataset_id,
            num_vectors=int(self.matrix.shape[0]),
            dimension=int(self.matrix.shape[1]),
            encoder=self.encoder.name,
            model_name=self.encoder.model_name,
            build_seconds=round(self.build_seconds, 3),
            built_at=self.built_at,
        )

    def search(self, query: str, top_k: int = 5) -> List[NearestNeighborResult]:
        scores = self.matrix @ self.encoder.encode([query])[0]
        top_k = min(top_k, len(scores))
        # argpartition is O(n); only the k winners get fully sorted.
        candidates = np.argpartition(-scores, top_k - 1)[:top_k]
        ranked = candidates[np.argsort(-scores[candidates])]
        return [
            NearestNeighborResult(
                record_id=self.record_ids[i],
                text=self.texts[i],
                label=self.labels[i],
                similarity=round(float(scores[i]), 4),
            )
            for i in ranked
        ]

    def similarity_between(self, record_id_a: str, record_id_b: str) -> float:
        try:
            a, b = self._row_of[record_id_a], self._row_of[record_id_b]
        except KeyError as exc:
            raise RecordNotFoundError(f"Record {exc.args[0]!r} is not in this dataset's index.") from None
        return round(float(self.matrix[a] @ self.matrix[b]), 4)


class EmbeddingIndexService:
    def __init__(self, encoder: Optional[str] = None) -> None:
        self._encoder_name = encoder or get_settings().embedding_encoder
        self._indices: Dict[str, EmbeddingIndex] = {}

    @property
    def encoder_name(self) -> str:
        return self._encoder_name

    @property
    def index_count(self) -> int:
        return len(self._indices)

    def _make_encoder(self):
        return DenseEncoder() if self._encoder_name == "dense" else TfidfEncoder()

    def build_index(
        self, dataset_id: str, record_ids: List[str], texts: List[str], labels: List[Optional[str]]
    ) -> EmbeddingIndexStats:
        if not texts:
            raise EmptyDatasetError("Cannot build an embedding index over zero records.")
        index = EmbeddingIndex(dataset_id, record_ids, texts, labels, self._make_encoder())
        self._indices[dataset_id] = index
        return index.stats()

    def get_index(self, dataset_id: str) -> EmbeddingIndex:
        index = self._indices.get(dataset_id)
        if index is None:
            raise RecordNotFoundError(
                f"No embedding index has been built for dataset {dataset_id!r} yet — "
                f"call POST /datasets/{dataset_id}/embeddings/build first."
            )
        return index

    def search(self, dataset_id: str, query: str, top_k: int = 5) -> List[NearestNeighborResult]:
        return self.get_index(dataset_id).search(query, top_k)

    def similarity_between_records(self, dataset_id: str, record_id_a: str, record_id_b: str) -> float:
        return self.get_index(dataset_id).similarity_between(record_id_a, record_id_b)


embedding_index_service = EmbeddingIndexService()

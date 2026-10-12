"""
Per-dataset embedding index: fits one TF-IDF vectorizer over a dataset's
text records and keeps the fitted matrix in memory, keyed by dataset id.
Supports real cosine-similarity search and nearest-neighbor lookup against
that index — the same "build a search index over a corpus" pattern any
production embedding platform uses, just backed by TF-IDF instead of a
downloaded transformer (see PROJECT_STATUS.md for why).

In-memory storage is a deliberate, documented stand-in for a real vector
database (FAISS, pgvector, Pinecone, ...) — swapping the storage backend
later doesn't need to change this service's public methods, only what's
inside `EmbeddingIndex`.
"""

import time
from dataclasses import dataclass
from typing import Dict, List, Optional

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from backend.core.exceptions import EmptyDatasetError, RecordNotFoundError


@dataclass
class EmbeddingIndexStats:
    dataset_id: str
    num_vectors: int
    vocabulary_size: int
    built_at: float


@dataclass
class NearestNeighborResult:
    record_id: str
    text: str
    label: Optional[str]
    similarity: float


class EmbeddingIndex:
    def __init__(
        self, dataset_id: str, record_ids: List[str], texts: List[str], labels: List[Optional[str]]
    ) -> None:
        self.dataset_id = dataset_id
        self.record_ids = record_ids
        self.texts = texts
        self.labels = labels
        self.vectorizer = TfidfVectorizer(max_features=5000, ngram_range=(1, 2))
        self.matrix = self.vectorizer.fit_transform(texts)
        self.built_at = time.time()

    def stats(self) -> EmbeddingIndexStats:
        return EmbeddingIndexStats(
            dataset_id=self.dataset_id,
            num_vectors=self.matrix.shape[0],
            vocabulary_size=len(self.vectorizer.vocabulary_),
            built_at=self.built_at,
        )

    def search(self, query: str, top_k: int = 5) -> List[NearestNeighborResult]:
        query_vector = self.vectorizer.transform([query])
        similarities = cosine_similarity(query_vector, self.matrix)[0]
        ranked_indices = sorted(range(len(similarities)), key=lambda i: similarities[i], reverse=True)[:top_k]
        return [
            NearestNeighborResult(
                record_id=self.record_ids[i],
                text=self.texts[i],
                label=self.labels[i],
                similarity=round(float(similarities[i]), 4),
            )
            for i in ranked_indices
        ]

    def similarity_between(self, record_id_a: str, record_id_b: str) -> float:
        idx_a = self.record_ids.index(record_id_a)
        idx_b = self.record_ids.index(record_id_b)
        sim = cosine_similarity(self.matrix[idx_a], self.matrix[idx_b])[0][0]
        return round(float(sim), 4)


class EmbeddingIndexService:
    def __init__(self) -> None:
        self._indices: Dict[str, EmbeddingIndex] = {}

    def build_index(
        self, dataset_id: str, record_ids: List[str], texts: List[str], labels: List[Optional[str]]
    ) -> EmbeddingIndexStats:
        if not texts:
            raise EmptyDatasetError("Cannot build an embedding index over zero records.")
        index = EmbeddingIndex(dataset_id, record_ids, texts, labels)
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

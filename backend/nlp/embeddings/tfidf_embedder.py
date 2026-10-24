"""
Sparse lexical embeddings via TF-IDF (scikit-learn).

The dense, semantic path is `SentenceTransformerModel`; this one needs no
model download and remains the right tool for exact-term matching.

Standalone `embed()`/`similarity()` calls (the BaseEmbedder contract) fit
a fresh vectorizer per call when nothing has been fit yet — fine for a
single similarity comparison, but vectors from *separate* unfit calls
aren't comparable to each other. For a real corpus-scoped search index,
use `backend.services.embedding_service.embedding_index_service` instead,
which fits once over a whole dataset and keeps the fitted space stable.
"""

from typing import List

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from backend.nlp.embeddings.base_embedder import BaseEmbedder


class TfidfEmbedder(BaseEmbedder):
    def __init__(self, model_name: str = "tfidf-v1") -> None:
        super().__init__(model_name)
        self._vectorizer = TfidfVectorizer(max_features=5000, ngram_range=(1, 2))
        self._fitted = False

    def embed(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        if not self._fitted:
            self._vectorizer.fit(texts)
            self._fitted = True
        return self._vectorizer.transform(texts).toarray().tolist()

    def similarity(self, text_a: str, text_b: str) -> float:
        vectors = self.embed([text_a, text_b])
        return round(float(cosine_similarity([vectors[0]], [vectors[1]])[0][0]), 4)


tfidf_embedder = TfidfEmbedder()

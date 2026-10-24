"""
Dense sentence embeddings (bi-encoder) via `sentence-transformers`.

Serves two tasks from one loaded model:
  - TEXT_EMBEDDINGS:      `embed()` -> L2-normalised vectors
  - SEMANTIC_SIMILARITY:  `predict(text, text_pair=...)` -> cosine similarity

Vectors are normalised at encode time, so cosine similarity is a plain dot
product everywhere downstream (including the dataset vector index).
"""

from typing import List

from backend.config.settings import get_settings
from backend.core.constants import NLPTask
from backend.core.exceptions import ModelLoadError, ValidationError
from backend.nlp.embeddings.base_embedder import BaseEmbedder
from backend.nlp.inference.base_model import BaseNLPModel, Prediction


class SentenceTransformerModel(BaseNLPModel, BaseEmbedder):
    supported_tasks = [NLPTask.SEMANTIC_SIMILARITY, NLPTask.TEXT_EMBEDDINGS]

    def __init__(self, model_name: str) -> None:
        BaseNLPModel.__init__(self, model_name)

    def load(self) -> None:
        if self._is_loaded:
            return
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise ModelLoadError("Embeddings require the 'sentence-transformers' package.") from exc
        try:
            self._model = SentenceTransformer(
                self.model_name, cache_folder=get_settings().model_cache_dir, device="cpu"
            )
        except Exception as exc:  # noqa: BLE001
            raise ModelLoadError(f"Failed to load model '{self.model_name}': {exc}") from exc
        self._is_loaded = True

    @property
    def dimension(self) -> int:
        self.load()
        return int(self._model.get_sentence_embedding_dimension())

    def encode(self, texts: List[str], batch_size: int = 64):
        """Return an (n, d) float32 numpy array of unit-length vectors."""
        self.load()
        return self._model.encode(
            texts, batch_size=batch_size, normalize_embeddings=True, convert_to_numpy=True, show_progress_bar=False
        )

    def embed(self, texts: List[str]) -> List[List[float]]:
        return self.encode(texts).tolist()

    def similarity(self, text_a: str, text_b: str) -> float:
        vectors = self.encode([text_a, text_b])
        return float(vectors[0] @ vectors[1])

    def predict(self, text: str, task: NLPTask, **kwargs) -> List[Prediction]:
        if task == NLPTask.SEMANTIC_SIMILARITY:
            text_pair = kwargs.get("text_pair")
            if not text_pair or not text_pair.strip():
                raise ValidationError("Semantic similarity needs a second text in 'text_pair'.")
            score = round(self.similarity(text, text_pair), 6)
            return [Prediction(label="cosine_similarity", score=score, raw_scores={"cosine_similarity": score})]

        vector = self.encode([text])[0]
        return [Prediction(label="embedding", score=1.0, raw_scores={"dimension": float(len(vector))})]

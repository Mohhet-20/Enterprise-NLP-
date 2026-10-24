"""
Concrete strategy for any `AutoModelForSequenceClassification` checkpoint
(BERT, DistilBERT, RoBERTa, DeBERTa, XLM-R, ELECTRA, ...).

Single-label heads are scored with softmax; heads whose config declares
`problem_type == "multi_label_classification"` (e.g. unitary/toxic-bert,
cardiffnlp/tweet-topic-21-multi) are scored with an independent sigmoid
per label, and every label above `multi_label_threshold` is returned.

`transformers`/`torch` are imported lazily inside `load()` so the API
process (and the test suite) can import the platform without the ML
extras installed — loading only happens on first use.
"""

from typing import List

from backend.config.settings import get_settings
from backend.core.constants import NLPTask
from backend.core.exceptions import ModelInferenceError, ModelLoadError
from backend.nlp.inference.base_model import BaseNLPModel, Prediction
from backend.nlp.inference.hub import load_with_retry


class BertModel(BaseNLPModel):
    supported_tasks = [
        NLPTask.SENTIMENT_ANALYSIS,
        NLPTask.EMOTION_DETECTION,
        NLPTask.TOPIC_CLASSIFICATION,
        NLPTask.TOXICITY_DETECTION,
        NLPTask.LANGUAGE_DETECTION,
    ]

    multi_label_threshold = 0.5

    def load(self) -> None:
        if self._is_loaded:
            return
        try:
            from transformers import AutoModelForSequenceClassification, AutoTokenizer
        except ImportError as exc:
            raise ModelLoadError(
                "The 'transformers' and 'torch' packages are required to serve models. "
                "Install them with: pip install -r requirements-ml.txt"
            ) from exc

        settings = get_settings()
        try:
            self._tokenizer = load_with_retry(
                lambda: AutoTokenizer.from_pretrained(self.model_name, cache_dir=settings.model_cache_dir)
            )
            self._model = load_with_retry(
                lambda: AutoModelForSequenceClassification.from_pretrained(
                    self.model_name, cache_dir=settings.model_cache_dir
                )
            )
        except Exception as exc:  # noqa: BLE001 - re-raised as a domain error
            raise ModelLoadError(f"Failed to load model '{self.model_name}': {exc}") from exc

        self._model.eval()
        self._max_length = min(settings.max_sequence_length, self._tokenizer.model_max_length)
        self._multi_label = self._model.config.problem_type == "multi_label_classification"
        self._id2label = self._model.config.id2label
        self._is_loaded = True

    def predict(self, text: str, task: NLPTask, **kwargs) -> List[Prediction]:
        return self.predict_batch([text], task, **kwargs)[0]

    def predict_batch(self, texts: List[str], task: NLPTask, **kwargs) -> List[List[Prediction]]:
        if task not in self.supported_tasks:
            raise ModelInferenceError(f"{type(self).__name__} does not support task '{task.value}'.")
        self.load()
        try:
            import torch

            inputs = self._tokenizer(
                texts, return_tensors="pt", truncation=True, padding=True, max_length=self._max_length
            )
            with torch.inference_mode():
                logits = self._model(**inputs).logits
            probs = torch.sigmoid(logits) if self._multi_label else torch.softmax(logits, dim=-1)
        except Exception as exc:  # noqa: BLE001
            raise ModelInferenceError(f"Inference failed for model '{self.model_name}': {exc}") from exc

        return [self._to_predictions(row.tolist()) for row in probs]

    def _to_predictions(self, scores: List[float]) -> List[Prediction]:
        raw_scores = {self._id2label[i]: round(float(s), 6) for i, s in enumerate(scores)}
        ranked = sorted(raw_scores.items(), key=lambda kv: kv[1], reverse=True)

        if self._multi_label:
            hits = [(label, score) for label, score in ranked if score >= self.multi_label_threshold]
            # Always surface at least the top label so callers never get an empty list.
            chosen = hits or ranked[:1]
            return [Prediction(label=label, score=score, raw_scores=raw_scores) for label, score in chosen]

        label, score = ranked[0]
        return [Prediction(label=label, score=score, raw_scores=raw_scores)]

    # --- Hooks used by the explainability module -------------------------

    @property
    def hf_model(self):
        self.load()
        return self._model

    @property
    def hf_tokenizer(self):
        self.load()
        return self._tokenizer

    def label_index(self, label: str) -> int:
        self.load()
        for idx, name in self._id2label.items():
            if name == label:
                return int(idx)
        raise ModelInferenceError(f"Label '{label}' is not produced by model '{self.model_name}'.")

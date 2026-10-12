"""
Concrete strategy for BERT-family classification models.

`transformers`/`torch` are imported lazily inside `load()` rather than at
module scope. This keeps the architecture skeleton importable (and its
tests fast) on machines that don't have the heavy ML dependencies installed
yet — loading only happens the first time the model is actually used.
"""

from typing import List

from backend.core.constants import NLPTask
from backend.core.exceptions import ModelInferenceError, ModelLoadError
from backend.nlp.inference.base_model import BaseNLPModel, Prediction


class BertModel(BaseNLPModel):
    supported_tasks = [
        NLPTask.SENTIMENT_ANALYSIS,
        NLPTask.EMOTION_DETECTION,
        NLPTask.TOPIC_CLASSIFICATION,
        NLPTask.TOXICITY_DETECTION,
        NLPTask.HATE_SPEECH_DETECTION,
        NLPTask.INTENT_CLASSIFICATION,
    ]

    def load(self) -> None:
        if self._is_loaded:
            return
        try:
            from transformers import AutoModelForSequenceClassification, AutoTokenizer

            self._tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self._model = AutoModelForSequenceClassification.from_pretrained(self.model_name)
            self._model.eval()
            self._is_loaded = True
        except ImportError as exc:
            raise ModelLoadError(
                "The 'transformers' and 'torch' packages are required to load real "
                "model weights. Install them to move past the architecture skeleton."
            ) from exc
        except Exception as exc:  # noqa: BLE001 - re-raised as a domain error
            raise ModelLoadError(f"Failed to load model '{self.model_name}': {exc}") from exc

    def predict(self, text: str, task: NLPTask, **kwargs) -> List[Prediction]:
        if task not in self.supported_tasks:
            raise ModelInferenceError(
                f"{type(self).__name__} does not support task '{task.value}'."
            )
        self.load()
        try:
            import torch

            inputs = self._tokenizer(text, return_tensors="pt", truncation=True)
            with torch.no_grad():
                logits = self._model(**inputs).logits
            probs = torch.softmax(logits, dim=-1)[0]
            id2label = self._model.config.id2label
            raw_scores = {id2label[i]: float(probs[i]) for i in range(len(probs))}
            best_idx = int(probs.argmax())
            return [Prediction(label=id2label[best_idx], score=float(probs[best_idx]), raw_scores=raw_scores)]
        except Exception as exc:  # noqa: BLE001
            raise ModelInferenceError(f"Inference failed for model '{self.model_name}': {exc}") from exc

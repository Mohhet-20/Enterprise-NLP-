"""
Zero-shot classification via natural-language inference.

Each candidate label is turned into a hypothesis ("This text is about
{label}.") and scored against the input as an NLI premise; the label's
score is the model's entailment probability. This is the standard
Yin et al. (2019) formulation that `transformers`' zero-shot pipeline
implements — we delegate to that pipeline rather than re-deriving the
entailment-index bookkeeping by hand.
"""

from typing import List

from backend.config.settings import get_settings
from backend.core.constants import NLPTask
from backend.core.exceptions import ModelLoadError, ValidationError
from backend.nlp.inference.base_model import BaseNLPModel, Prediction
from backend.nlp.inference.hub import load_with_retry

MAX_CANDIDATE_LABELS = 20


class ZeroShotModel(BaseNLPModel):
    supported_tasks = [NLPTask.ZERO_SHOT_CLASSIFICATION]

    def load(self) -> None:
        if self._is_loaded:
            return
        try:
            from transformers import pipeline
        except ImportError as exc:
            raise ModelLoadError("Zero-shot classification requires 'transformers' and 'torch'.") from exc
        try:
            self._pipeline = load_with_retry(
                lambda: pipeline(
                    "zero-shot-classification",
                    model=self.model_name,
                    model_kwargs={"cache_dir": get_settings().model_cache_dir},
                    device=-1,
                )
            )
        except Exception as exc:  # noqa: BLE001
            raise ModelLoadError(f"Failed to load model '{self.model_name}': {exc}") from exc
        self._is_loaded = True

    def predict(self, text: str, task: NLPTask, **kwargs) -> List[Prediction]:
        labels = [label.strip() for label in (kwargs.get("candidate_labels") or []) if label and label.strip()]
        if len(labels) < 2:
            raise ValidationError("Zero-shot classification needs at least 2 candidate_labels.")
        if len(labels) > MAX_CANDIDATE_LABELS:
            raise ValidationError(f"At most {MAX_CANDIDATE_LABELS} candidate_labels are allowed.")

        self.load()
        multi_label = bool(kwargs.get("multi_label", False))
        output = self._pipeline(text, candidate_labels=labels, multi_label=multi_label)
        raw_scores = {label: round(float(score), 6) for label, score in zip(output["labels"], output["scores"])}
        top_label, top_score = output["labels"][0], float(output["scores"][0])
        return [Prediction(label=top_label, score=round(top_score, 6), raw_scores=raw_scores)]

"""
Evaluation & Error Analysis orchestration.

A run = (model, evaluation set) -> real predictions -> scikit-learn metrics
+ error analysis -> persisted report.

Models:
  - "served":            the task's registered transformer (plugin default)
  - "lexicon_baseline":  the rule-based sentiment baseline, kept as a floor
                         every served model has to beat

Evaluation sets:
  - "challenge_set":     48 hand-labelled sentences built to stress negation,
                         sarcasm, mixed sentiment and very short text
  - "sst2_validation":   the 872-sentence SST-2 validation split (GLUE),
                         downloaded once via `datasets` and cached
  - a Data Platform dataset (`dataset_id`): any uploaded, labelled dataset

Comparing the same model on several sets — or several models on the same
set — is how the README's results table is produced.
"""

import time
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from backend.core.constants import NLPTask
from backend.core.exceptions import (
    EmptyDatasetError,
    ExternalServiceError,
    RecordNotFoundError,
    UnsupportedEvaluationTaskError,
)
from backend.evaluation.baseline_classifier import baseline_sentiment_classifier
from backend.evaluation.error_analysis import EvalSampleResult, error_analyzer
from backend.evaluation.evaluation_store import evaluation_run_store
from backend.evaluation.metrics import compute_classification_metrics
from backend.evaluation.sample_dataset import SENTIMENT_EVAL_SET, LabeledExample
from backend.nlp.inference.model_factory import model_factory
from backend.plugins.plugin_registry import display_model_name, get_task_plugin
from backend.repositories.dataset_record_repository import DatasetRecordRepository
from backend.repositories.dataset_repository import DatasetRepository
from backend.services.base_service import BaseService

LEXICON_BASELINE_NAME = "lexicon-baseline-v1"

# Tasks whose model emits exactly one label per text — the only ones where
# accuracy / confusion-matrix metrics are well defined against a gold label.
SINGLE_LABEL_TASKS = {
    NLPTask.SENTIMENT_ANALYSIS,
    NLPTask.EMOTION_DETECTION,
    NLPTask.LANGUAGE_DETECTION,
    NLPTask.ZERO_SHOT_CLASSIFICATION,
}

BUILTIN_EVAL_SETS = {"challenge_set", "sst2_validation"}
MAX_EVAL_SAMPLES = 5_000
EVAL_BATCH_SIZE = 32

# Cap how many misclassified samples ride along in the API response body —
# the full list is always in the persisted JSON report and the CSV export.
MAX_INLINE_MISCLASSIFIED_SAMPLES = 25


def _normalise(label: str) -> str:
    return label.strip().upper()


def _load_sst2_validation() -> List[LabeledExample]:
    try:
        from datasets import load_dataset

        split = load_dataset("stanfordnlp/sst2", split="validation")
    except Exception as exc:  # noqa: BLE001 - offline / missing extra
        raise ExternalServiceError(f"Could not load the SST-2 validation split: {exc}") from exc
    names = split.features["label"].names
    return [LabeledExample(row["sentence"], names[row["label"]].upper()) for row in split]


class EvaluationService(BaseService):
    def run_evaluation(
        self,
        task: NLPTask,
        *,
        model: str = "served",
        eval_set: Optional[str] = "challenge_set",
        dataset_id: Optional[str] = None,
        db: Optional[Session] = None,
    ) -> Dict:
        if task not in SINGLE_LABEL_TASKS:
            raise UnsupportedEvaluationTaskError(
                f"'{task.value}' is not a single-label classification task, so accuracy-style "
                f"evaluation against gold labels isn't defined for it."
            )
        if model == "lexicon_baseline" and task != NLPTask.SENTIMENT_ANALYSIS:
            raise UnsupportedEvaluationTaskError("The lexicon baseline only covers sentiment_analysis.")

        examples, set_name, label_set = self._load_examples(task, eval_set, dataset_id, db)
        if task == NLPTask.ZERO_SHOT_CLASSIFICATION and len(label_set) < 2:
            raise UnsupportedEvaluationTaskError(
                "Zero-shot evaluation needs a dataset whose label_set has at least 2 labels."
            )

        started = time.perf_counter()
        if model == "lexicon_baseline":
            predictions = [
                (p.label, p.score) for p in (baseline_sentiment_classifier.predict(e.text) for e in examples)
            ]
            model_name = LEXICON_BASELINE_NAME
        else:
            predictions, model_name = self._predict_served(task, [e.text for e in examples], label_set)
        elapsed = time.perf_counter() - started

        samples = [
            EvalSampleResult(
                text=e.text,
                true_label=_normalise(e.true_label),
                predicted_label=_normalise(label),
                confidence=score,
            )
            for e, (label, score) in zip(examples, predictions)
        ]
        return self._build_and_save(task, model, model_name, set_name, samples, elapsed)

    def _load_examples(
        self, task: NLPTask, eval_set: Optional[str], dataset_id: Optional[str], db: Optional[Session]
    ) -> Tuple[List[LabeledExample], str, List[str]]:
        if dataset_id:
            if db is None:
                raise ValueError("A database session is required to evaluate on a stored dataset.")
            dataset = DatasetRepository(db).get(dataset_id)
            records = [r for r in DatasetRecordRepository(db).all_for_dataset(dataset_id) if r.label]
            if not records:
                raise EmptyDatasetError(f"Dataset {dataset.name!r} has no labelled records to evaluate on.")
            examples = [LabeledExample(r.text, r.label) for r in records[:MAX_EVAL_SAMPLES]]
            label_set = dataset.label_set or sorted({r.label for r in records})
            return examples, f"dataset:{dataset.name}", label_set

        if eval_set not in BUILTIN_EVAL_SETS:
            raise UnsupportedEvaluationTaskError(f"Unknown evaluation set {eval_set!r}.")
        if task != NLPTask.SENTIMENT_ANALYSIS:
            raise UnsupportedEvaluationTaskError(
                f"Built-in evaluation sets are sentiment-only; evaluate '{task.value}' on an uploaded dataset."
            )
        examples = SENTIMENT_EVAL_SET if eval_set == "challenge_set" else _load_sst2_validation()
        return list(examples), eval_set, ["NEGATIVE", "POSITIVE"]

    def _predict_served(
        self, task: NLPTask, texts: List[str], label_set: List[str]
    ) -> Tuple[List[Tuple[str, float]], str]:
        plugin = get_task_plugin(task)
        served = model_factory.get_model(plugin.default_architecture, plugin.default_model_name, task=task)
        kwargs = {"candidate_labels": label_set} if task == NLPTask.ZERO_SHOT_CLASSIFICATION else {}

        out: List[Tuple[str, float]] = []
        for i in range(0, len(texts), EVAL_BATCH_SIZE):
            for preds in served.predict_batch(texts[i : i + EVAL_BATCH_SIZE], task, **kwargs):
                out.append((preds[0].label, preds[0].score))
        return out, display_model_name(plugin.default_model_name)

    def _build_and_save(
        self, task: NLPTask, model_kind: str, model_name: str, set_name: str,
        samples: List[EvalSampleResult], elapsed_seconds: float,
    ) -> Dict:
        y_true = [s.true_label for s in samples]
        y_pred = [s.predicted_label for s in samples]
        confidences = [s.confidence for s in samples]

        metrics = compute_classification_metrics(y_true, y_pred, confidences)
        errors = error_analyzer.analyze(samples)

        run_id = str(uuid.uuid4())
        result = {
            "run_id": run_id,
            "task": task.value,
            "model_name": model_name,
            "model_kind": model_kind,
            "eval_set": set_name,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "num_samples": len(samples),
            "duration_seconds": round(elapsed_seconds, 3),
            "accuracy": metrics.accuracy,
            "macro_f1": metrics.macro_f1,
            "weighted_f1": metrics.weighted_f1,
            "roc_auc": metrics.roc_auc,
            "labels": metrics.labels,
            "confusion_matrix": metrics.confusion_matrix,
            "per_class": [pc.__dict__ for pc in metrics.per_class],
            "calibration_bins": [cb.__dict__ for cb in metrics.calibration_bins],
            "error_summary": {
                "total_errors": len(errors.misclassified),
                "confidence_error_count": len(errors.confidence_errors),
                "hard_example_count": len(errors.hard_examples),
                "false_positives_by_class": errors.false_positives_by_class,
                "false_negatives_by_class": errors.false_negatives_by_class,
                "errors_by_class": errors.errors_by_class,
                "length_slices": [ls.__dict__ for ls in errors.length_slices],
            },
            # Full list persisted for the CSV export; API responses cap it.
            "misclassified_samples_full": [s.__dict__ for s in errors.misclassified],
            "misclassified_samples": [s.__dict__ for s in errors.misclassified][
                :MAX_INLINE_MISCLASSIFIED_SAMPLES
            ],
        }

        evaluation_run_store.save(run_id, result)
        return result

    def get_run(self, run_id: str) -> Dict:
        if not evaluation_run_store.exists(run_id):
            raise RecordNotFoundError(f"No evaluation run found with id={run_id!r}.")
        return evaluation_run_store.load(run_id)

    def list_runs(self) -> List[Dict]:
        return evaluation_run_store.list_summaries()


evaluation_service = EvaluationService()

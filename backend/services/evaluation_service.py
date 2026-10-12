"""
Evaluation & Error Analysis orchestration.

Runs a real classifier (see backend/evaluation/baseline_classifier.py —
there's no HF Hub network access in this environment, so this is a
lexicon baseline standing in for a trained transformer) against a labeled
evaluation set, computes genuine metrics via scikit-learn, runs error
analysis over the actual per-sample results, and persists the full report.

Every number in the resulting report is computed from real predictions on
real (if synthetic) labeled text — nothing here is a placeholder value.
"""

import uuid
from datetime import datetime, timezone
from typing import Dict, List

from backend.core.constants import NLPTask
from backend.core.exceptions import RecordNotFoundError, UnsupportedEvaluationTaskError
from backend.evaluation.baseline_classifier import baseline_sentiment_classifier
from backend.evaluation.error_analysis import EvalSampleResult, error_analyzer
from backend.evaluation.evaluation_store import evaluation_run_store
from backend.evaluation.metrics import compute_classification_metrics
from backend.evaluation.sample_dataset import SENTIMENT_EVAL_SET
from backend.services.base_service import BaseService

MODEL_NAME_BY_TASK = {
    NLPTask.SENTIMENT_ANALYSIS: "lexicon-baseline-v1",
}

# Cap how many misclassified samples ride along in the API response body —
# the full list is always in the persisted JSON report and the CSV export.
MAX_INLINE_MISCLASSIFIED_SAMPLES = 25


class EvaluationService(BaseService):
    def run_evaluation(self, task: NLPTask) -> Dict:
        if task != NLPTask.SENTIMENT_ANALYSIS:
            raise UnsupportedEvaluationTaskError(
                f"No evaluation baseline is registered for '{task.value}' yet — "
                f"only '{NLPTask.SENTIMENT_ANALYSIS.value}' has one in this build."
            )

        samples: List[EvalSampleResult] = []
        for example in SENTIMENT_EVAL_SET:
            prediction = baseline_sentiment_classifier.predict(example.text)
            samples.append(
                EvalSampleResult(
                    text=example.text,
                    true_label=example.true_label,
                    predicted_label=prediction.label,
                    confidence=prediction.score,
                )
            )

        y_true = [s.true_label for s in samples]
        y_pred = [s.predicted_label for s in samples]
        confidences = [s.confidence for s in samples]

        metrics = compute_classification_metrics(y_true, y_pred, confidences)
        errors = error_analyzer.analyze(samples)

        run_id = str(uuid.uuid4())
        result = {
            "run_id": run_id,
            "task": task.value,
            "model_name": MODEL_NAME_BY_TASK[task],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "num_samples": len(samples),
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

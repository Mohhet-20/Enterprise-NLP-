"""
Comprehensive classification metrics, backed by scikit-learn rather than
hand-rolled math — confusion matrices and calibration curves are easy to
get subtly wrong by hand, and sklearn's implementations are the standard
enterprise practice this platform should reflect.
"""

from dataclasses import dataclass, field
from typing import List, Optional

import numpy as np
from sklearn.metrics import confusion_matrix, precision_recall_fscore_support, roc_auc_score


@dataclass
class PerClassMetric:
    label: str
    precision: float
    recall: float
    f1: float
    support: int


@dataclass
class CalibrationBin:
    bucket_low: float
    bucket_high: float
    avg_confidence: float
    accuracy: float
    count: int


@dataclass
class ClassificationMetrics:
    accuracy: float
    macro_f1: float
    weighted_f1: float
    per_class: List[PerClassMetric]
    confusion_matrix: List[List[int]]
    labels: List[str]
    roc_auc: Optional[float] = None
    calibration_bins: List[CalibrationBin] = field(default_factory=list)
    ece: float = 0.0


def compute_classification_metrics(
    y_true: List[str],
    y_pred: List[str],
    confidences: List[float],
    labels: Optional[List[str]] = None,
) -> ClassificationMetrics:
    if len(y_true) != len(y_pred) or len(y_true) != len(confidences):
        raise ValueError("y_true, y_pred, and confidences must be the same length.")
    if not y_true:
        raise ValueError("Cannot compute metrics over an empty evaluation set.")

    resolved_labels = labels or sorted(set(y_true) | set(y_pred))

    precision, recall, f1, support = precision_recall_fscore_support(
        y_true, y_pred, labels=resolved_labels, zero_division=0
    )
    per_class = [
        PerClassMetric(
            label=label,
            precision=round(float(p), 4),
            recall=round(float(r), 4),
            f1=round(float(f), 4),
            support=int(s),
        )
        for label, p, r, f, s in zip(resolved_labels, precision, recall, f1, support)
    ]

    macro_f1 = round(float(np.mean(f1)), 4)
    weighted_f1 = round(float(np.average(f1, weights=support)) if support.sum() > 0 else 0.0, 4)
    accuracy = round(sum(t == p for t, p in zip(y_true, y_pred)) / len(y_true), 4)

    cm = confusion_matrix(y_true, y_pred, labels=resolved_labels).tolist()

    roc_auc = None
    if len(resolved_labels) == 2:
        # Binary case: treat confidence as P(predicted label), convert to
        # P(positive class) so roc_auc_score gets a consistent score axis.
        positive_label = resolved_labels[1]
        y_true_binary = [1 if t == positive_label else 0 for t in y_true]
        scores = [
            conf if pred == positive_label else 1 - conf
            for pred, conf in zip(y_pred, confidences)
        ]
        try:
            roc_auc = round(float(roc_auc_score(y_true_binary, scores)), 4)
        except ValueError:
            roc_auc = None  # only one class present in y_true — AUC undefined

    calibration_bins = _compute_calibration_bins(y_true, y_pred, confidences)

    return ClassificationMetrics(
        accuracy=accuracy,
        macro_f1=macro_f1,
        weighted_f1=weighted_f1,
        per_class=per_class,
        confusion_matrix=cm,
        labels=resolved_labels,
        roc_auc=roc_auc,
        calibration_bins=calibration_bins,
        ece=expected_calibration_error(calibration_bins),
    )


def _compute_calibration_bins(
    y_true: List[str], y_pred: List[str], confidences: List[float], n_bins: int = 5
) -> List[CalibrationBin]:
    """
    Reliability-diagram data: for each confidence bucket, what fraction of
    predictions in that bucket were actually correct? A well-calibrated
    classifier's accuracy should track its confidence closely; large gaps
    indicate over- or under-confidence.
    """
    # Binned directly rather than via sklearn's calibration_curve, which drops
    # empty bins from its output and so can't be zipped back onto bin edges.
    correctness = np.array([1.0 if t == p else 0.0 for t, p in zip(y_true, y_pred)])
    confidence_arr = np.clip(np.array(confidences, dtype=float), 0.0, 1.0)

    bin_edges = np.linspace(0.0, 1.0, n_bins + 1)
    # Right-closed last bin so a confidence of exactly 1.0 is counted.
    bin_ids = np.minimum(np.digitize(confidence_arr, bin_edges[1:-1], right=False), n_bins - 1)

    bins: List[CalibrationBin] = []
    for i in range(n_bins):
        in_bin = bin_ids == i
        count = int(in_bin.sum())
        if count == 0:
            continue
        bins.append(
            CalibrationBin(
                bucket_low=round(float(bin_edges[i]), 2),
                bucket_high=round(float(bin_edges[i + 1]), 2),
                avg_confidence=round(float(confidence_arr[in_bin].mean()), 4),
                accuracy=round(float(correctness[in_bin].mean()), 4),
                count=count,
            )
        )
    return bins


def expected_calibration_error(bins: List[CalibrationBin]) -> float:
    """ECE: the sample-weighted mean |accuracy − confidence| over buckets.
    0 is perfectly calibrated; 0.05 means confidence is off by 5 points on average."""
    total = sum(b.count for b in bins)
    if total == 0:
        return 0.0
    return round(sum(b.count * abs(b.accuracy - b.avg_confidence) for b in bins) / total, 4)

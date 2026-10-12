from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict

from backend.core.constants import NLPTask


class EvaluationRunRequest(BaseModel):
    task: NLPTask


class PerClassMetricSchema(BaseModel):
    label: str
    precision: float
    recall: float
    f1: float
    support: int


class CalibrationBinSchema(BaseModel):
    bucket_low: float
    bucket_high: float
    avg_confidence: float
    accuracy: float
    count: int


class MisclassifiedSampleSchema(BaseModel):
    text: str
    true_label: str
    predicted_label: str
    confidence: float


class LengthSliceSchema(BaseModel):
    name: str
    count: int
    accuracy: float
    error_count: int


class ErrorSummarySchema(BaseModel):
    total_errors: int
    confidence_error_count: int
    hard_example_count: int
    false_positives_by_class: Dict[str, int]
    false_negatives_by_class: Dict[str, int]
    errors_by_class: Dict[str, int]
    length_slices: List[LengthSliceSchema]


class EvaluationRunSummary(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    run_id: str
    task: NLPTask
    model_name: str
    created_at: datetime
    accuracy: float
    num_samples: int


class EvaluationRunResult(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    run_id: str
    task: NLPTask
    model_name: str
    created_at: datetime
    num_samples: int

    accuracy: float
    macro_f1: float
    weighted_f1: float
    roc_auc: Optional[float] = None
    labels: List[str]
    confusion_matrix: List[List[int]]
    per_class: List[PerClassMetricSchema]
    calibration_bins: List[CalibrationBinSchema]

    error_summary: ErrorSummarySchema
    misclassified_samples: List[MisclassifiedSampleSchema]

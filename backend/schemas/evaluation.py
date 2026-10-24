from datetime import datetime
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from backend.core.constants import NLPTask


class EvaluationRunRequest(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    task: NLPTask
    model: Literal["served", "lexicon_baseline"] = Field(
        default="served", description="The task's served transformer, or the lexicon baseline."
    )
    eval_set: Literal["challenge_set", "sst2_validation"] = "challenge_set"
    dataset_id: Optional[str] = Field(
        default=None, description="Evaluate on an uploaded Data Platform dataset instead of a built-in set."
    )


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
    model_kind: str = "lexicon_baseline"
    eval_set: str = "challenge_set"
    created_at: datetime
    accuracy: float
    macro_f1: Optional[float] = None
    num_samples: int


class EvaluationRunResult(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    run_id: str
    task: NLPTask
    model_name: str
    model_kind: str = "lexicon_baseline"
    eval_set: str = "challenge_set"
    created_at: datetime
    num_samples: int
    duration_seconds: Optional[float] = None

    accuracy: float
    macro_f1: float
    weighted_f1: float
    roc_auc: Optional[float] = None
    ece: Optional[float] = None
    labels: List[str]
    confusion_matrix: List[List[int]]
    per_class: List[PerClassMetricSchema]
    calibration_bins: List[CalibrationBinSchema]

    error_summary: ErrorSummarySchema
    misclassified_samples: List[MisclassifiedSampleSchema]

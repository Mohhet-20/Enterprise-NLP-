from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from backend.core.constants import NLPTask


class InferenceRequest(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    task: NLPTask
    text: str = Field(..., min_length=1, max_length=100_000)
    model_name: Optional[str] = Field(
        default=None,
        description="Explicit model identifier. Falls back to the task's registered default.",
    )
    candidate_labels: Optional[List[str]] = Field(
        default=None,
        description="Required for zero-shot classification; ignored otherwise.",
    )


class InferenceResult(BaseModel):
    label: str
    score: float
    raw_scores: Optional[Dict[str, float]] = None


class InferenceResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    task: NLPTask
    model_name: str
    results: List[InferenceResult]
    latency_ms: float

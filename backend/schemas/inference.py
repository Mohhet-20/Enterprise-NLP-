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
    multi_label: bool = Field(
        default=False,
        description="Zero-shot only: score each candidate label independently.",
    )
    text_pair: Optional[str] = Field(
        default=None,
        max_length=100_000,
        description="Required for semantic similarity: the second text to compare against.",
    )


class BatchInferenceRequest(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    task: NLPTask
    texts: List[str] = Field(..., min_length=1)
    model_name: Optional[str] = None
    candidate_labels: Optional[List[str]] = None
    multi_label: bool = False


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


class BatchInferenceItem(BaseModel):
    text: str
    results: List[InferenceResult]


class BatchInferenceResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    task: NLPTask
    model_name: str
    items: List[BatchInferenceItem]
    latency_ms: float
    throughput_texts_per_second: float


class ExplainRequest(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    task: NLPTask
    text: str = Field(..., min_length=1, max_length=5_000)
    target_label: Optional[str] = Field(
        default=None, description="Label to explain. Defaults to the model's top prediction."
    )
    n_steps: int = Field(default=32, ge=8, le=128)


class TokenAttributionSchema(BaseModel):
    token: str
    importance: float


class ExplainResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    task: NLPTask
    model_name: str
    method: str
    label: str
    target_score: float
    baseline_score: float
    convergence_delta: float
    attributions: List[TokenAttributionSchema]
    latency_ms: float


class EmbedRequest(BaseModel):
    texts: List[str] = Field(..., min_length=1)


class EmbedResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    model_name: str
    dimension: int
    embeddings: List[List[float]]

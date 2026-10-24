from typing import Optional

from pydantic import BaseModel


class EmbeddingIndexStatsSchema(BaseModel):
    dataset_id: str
    num_vectors: int
    dimension: int
    encoder: str
    model_name: str
    build_seconds: float
    built_at: float

    model_config = {"protected_namespaces": ()}


class NearestNeighborResultSchema(BaseModel):
    record_id: str
    text: str
    label: Optional[str] = None
    similarity: float


class SimilarityResponse(BaseModel):
    record_id_a: str
    record_id_b: str
    similarity: float

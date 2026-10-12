from typing import Optional

from pydantic import BaseModel


class EmbeddingIndexStatsSchema(BaseModel):
    dataset_id: str
    num_vectors: int
    vocabulary_size: int
    built_at: float


class NearestNeighborResultSchema(BaseModel):
    record_id: str
    text: str
    label: Optional[str] = None
    similarity: float


class SimilarityResponse(BaseModel):
    record_id_a: str
    record_id_b: str
    similarity: float

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.auth.dependencies import get_current_user
from backend.auth.rbac import require_permission
from backend.database.session import get_db_session
from backend.repositories.dataset_record_repository import DatasetRecordRepository
from backend.schemas.auth import CurrentUser
from backend.schemas.embedding import (
    EmbeddingIndexStatsSchema,
    NearestNeighborResultSchema,
    SimilarityResponse,
)
from backend.services.embedding_service import embedding_index_service

router = APIRouter()


@router.post("/datasets/{dataset_id}/embeddings/build", response_model=EmbeddingIndexStatsSchema)
def build_embedding_index(
    dataset_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> EmbeddingIndexStatsSchema:
    require_permission(current_user.role, "dataset:read")
    records = DatasetRecordRepository(db).all_for_dataset(dataset_id)
    stats = embedding_index_service.build_index(
        dataset_id,
        record_ids=[r.id for r in records],
        texts=[r.text for r in records],
        labels=[r.label for r in records],
    )
    return EmbeddingIndexStatsSchema(**stats.__dict__)


@router.get("/datasets/{dataset_id}/embeddings/search", response_model=list[NearestNeighborResultSchema])
def search_embedding_index(
    dataset_id: str,
    query: str = Query(...),
    top_k: int = Query(default=5, le=50),
    current_user: CurrentUser = Depends(get_current_user),
) -> list[NearestNeighborResultSchema]:
    require_permission(current_user.role, "dataset:read")
    results = embedding_index_service.search(dataset_id, query, top_k=top_k)
    return [NearestNeighborResultSchema(**r.__dict__) for r in results]


@router.get("/datasets/{dataset_id}/embeddings/similarity", response_model=SimilarityResponse)
def compare_record_similarity(
    dataset_id: str,
    record_id_a: str = Query(...),
    record_id_b: str = Query(...),
    current_user: CurrentUser = Depends(get_current_user),
) -> SimilarityResponse:
    require_permission(current_user.role, "dataset:read")
    similarity = embedding_index_service.similarity_between_records(dataset_id, record_id_a, record_id_b)
    return SimilarityResponse(record_id_a=record_id_a, record_id_b=record_id_b, similarity=similarity)

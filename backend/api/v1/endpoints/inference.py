from fastapi import APIRouter, Depends

from backend.auth.dependencies import get_current_user
from backend.auth.rbac import require_permission
from backend.schemas.auth import CurrentUser
from backend.schemas.inference import (
    BatchInferenceRequest,
    BatchInferenceResponse,
    EmbedRequest,
    EmbedResponse,
    ExplainRequest,
    ExplainResponse,
    InferenceRequest,
    InferenceResponse,
)
from backend.services.inference_service import inference_service

router = APIRouter()


@router.post("/predict", response_model=InferenceResponse)
def predict(
    request: InferenceRequest,
    current_user: CurrentUser = Depends(get_current_user),
) -> InferenceResponse:
    require_permission(current_user.role, "model:infer")
    return inference_service.run_inference(request)


@router.post("/predict/batch", response_model=BatchInferenceResponse)
def predict_batch(
    request: BatchInferenceRequest,
    current_user: CurrentUser = Depends(get_current_user),
) -> BatchInferenceResponse:
    require_permission(current_user.role, "model:infer")
    return inference_service.run_batch(request)


@router.post("/explain", response_model=ExplainResponse)
def explain(
    request: ExplainRequest,
    current_user: CurrentUser = Depends(get_current_user),
) -> ExplainResponse:
    require_permission(current_user.role, "model:infer")
    return inference_service.explain(request)


@router.post("/embed", response_model=EmbedResponse)
def embed(
    request: EmbedRequest,
    current_user: CurrentUser = Depends(get_current_user),
) -> EmbedResponse:
    require_permission(current_user.role, "model:infer")
    return inference_service.embed(request)

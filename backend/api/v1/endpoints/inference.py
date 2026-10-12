from fastapi import APIRouter, Depends

from backend.auth.dependencies import get_current_user
from backend.auth.rbac import require_permission
from backend.schemas.auth import CurrentUser
from backend.schemas.inference import InferenceRequest, InferenceResponse
from backend.services.inference_service import inference_service

router = APIRouter()


@router.post("/predict", response_model=InferenceResponse)
def predict(
    request: InferenceRequest,
    current_user: CurrentUser = Depends(get_current_user),
) -> InferenceResponse:
    require_permission(current_user.role, "model:infer")
    return inference_service.run_inference(request)

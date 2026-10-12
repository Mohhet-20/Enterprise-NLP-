from fastapi import APIRouter

from backend.monitoring.metrics import metrics_registry

router = APIRouter()


@router.get("/metrics")
def get_metrics() -> dict:
    return metrics_registry.snapshot()

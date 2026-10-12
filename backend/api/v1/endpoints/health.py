"""
Health & Observability endpoints. No authentication required — these are
meant to be polled by load balancers, container orchestrators, and
uptime monitors, none of which carry a user's bearer token.

Each endpoint delegates to a real check in
backend/monitoring/health_checks.py — nothing here is a hardcoded "ok".
"""

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from backend.config.settings import get_settings
from backend.database.session import get_db_session
from backend.monitoring import health_checks

router = APIRouter()


@router.get("/health")
def health_check() -> dict:
    settings = get_settings()
    return {
        "status": "ok",
        "app_name": settings.app_name,
        "environment": settings.environment.value,
    }


@router.get("/liveness")
def liveness() -> dict:
    return health_checks.check_liveness()


@router.get("/readiness")
def readiness(response: Response, db: Session = Depends(get_db_session)) -> dict:
    result = health_checks.check_readiness(db)
    if result["status"] != "ready":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return result


@router.get("/database")
def database_health(response: Response, db: Session = Depends(get_db_session)) -> dict:
    result = health_checks.check_database(db)
    if result["status"] != "ok":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return result


@router.get("/model")
def model_health() -> dict:
    return health_checks.check_model_registry()


@router.get("/embedding")
def embedding_health() -> dict:
    return health_checks.check_embedding_subsystem()


@router.get("/monitoring-health")
def monitoring_health() -> dict:
    # Named distinctly from GET /monitoring/metrics (the full metrics
    # dump) — this is a lightweight "is the subsystem itself healthy"
    # check, not the data it collects.
    return health_checks.check_monitoring_subsystem()


@router.get("/cache")
def cache_health() -> dict:
    return health_checks.check_cache_subsystem()


@router.get("/system")
def system_health() -> dict:
    return health_checks.check_system_resources()


@router.get("/version")
def version() -> dict:
    return health_checks.get_version_info()


@router.get("/status")
def overall_status(response: Response, db: Session = Depends(get_db_session)) -> dict:
    result = health_checks.check_overall_status(db)
    if result["status"] == "error":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return result

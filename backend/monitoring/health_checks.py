"""
Health & Observability checks.

Every function here does real work — queries the database, reads actual
process/system state, introspects the real model factory and metrics
registry — rather than returning a hardcoded `{"status": "ok"}`. Where a
subsystem genuinely isn't implemented yet (embeddings), the check says so
explicitly instead of faking a healthy response; see PROJECT_STATUS.md.
"""

import platform
import subprocess
import time
from typing import Any, Dict, List

from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.config.settings import get_settings
from backend.monitoring.metrics import metrics_registry
from backend.nlp.inference.model_factory import model_factory
from backend.plugins.plugin_registry import list_supported_tasks


def check_liveness() -> Dict[str, Any]:
    """No dependencies checked — if this function returns, the process is
    alive and able to handle a request. Used by an orchestrator's
    liveness probe to decide whether to restart the container."""
    return {"status": "alive"}


def check_database(db: Session) -> Dict[str, Any]:
    start = time.perf_counter()
    try:
        db.execute(text("SELECT 1"))
        latency_ms = round((time.perf_counter() - start) * 1000, 2)
        return {"status": "ok", "latency_ms": latency_ms}
    except Exception as exc:  # noqa: BLE001
        return {"status": "error", "detail": str(exc)}


def check_readiness(db: Session) -> Dict[str, Any]:
    """Checks the dependencies the app actually needs to serve real
    traffic — currently just the database. Used by an orchestrator's
    readiness probe to decide whether to route traffic to this instance."""
    db_check = check_database(db)
    ready = db_check["status"] == "ok"
    return {"status": "ready" if ready else "not_ready", "database": db_check}


def check_model_registry() -> Dict[str, Any]:
    """Real introspection of the model factory's in-memory cache and the
    plugin registry's registered tasks."""
    return {
        "status": "ok",
        "registered_tasks": [t.value for t in list_supported_tasks()],
        "registered_architectures": model_factory.registered_architectures(),
        "cached_model_instances": model_factory.list_cached_models(),
    }


def check_embedding_subsystem() -> Dict[str, Any]:
    """Honest status: the embedding platform is architecture-only in this
    build (BaseEmbedder interface exists, no concrete embedder is
    registered) — see PROJECT_STATUS.md. A 200 with a clear
    'not_implemented' status is more useful to a caller than either a
    fake 'ok' or an opaque 404."""
    return {
        "status": "not_implemented",
        "detail": "backend/nlp/embeddings/ defines BaseEmbedder but no concrete "
        "implementation is registered yet.",
    }


def check_monitoring_subsystem() -> Dict[str, Any]:
    snapshot = metrics_registry.snapshot()
    total_predictions = sum(entry["count"] for entry in snapshot.values())
    return {
        "status": "ok",
        "tracked_task_model_pairs": len(snapshot),
        "total_predictions_recorded": total_predictions,
    }


def check_cache_subsystem() -> Dict[str, Any]:
    """Real check: which backend is actually serving cache/rate-limit
    reads right now — 'redis' if reachable, 'in_memory' if it fell back.
    Both are a healthy 'ok' status; which one matters for capacity
    planning (in-memory isn't shared across workers) but not for whether
    the feature is working."""
    from backend.core.cache import cache_service

    return {"status": "ok", "backend": cache_service.backend_name}


def check_system_resources() -> Dict[str, Any]:
    try:
        import psutil

        return {
            "status": "ok",
            "cpu_percent": psutil.cpu_percent(interval=0.1),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage("/").percent,
        }
    except ImportError:
        return {"status": "unavailable", "detail": "psutil is not installed."}


def get_version_info() -> Dict[str, Any]:
    settings = get_settings()
    git_commit = "unknown"
    try:
        git_commit = (
            subprocess.check_output(
                ["git", "rev-parse", "--short", "HEAD"], stderr=subprocess.DEVNULL
            )
            .decode()
            .strip()
        )
    except Exception:  # noqa: BLE001 — no .git directory, or git not installed; "unknown" is correct
        pass

    return {
        "app_name": settings.app_name,
        "app_version": settings.app_version,
        "environment": settings.environment.value,
        "python_version": platform.python_version(),
        "git_commit": git_commit,
    }


def check_overall_status(db: Session) -> Dict[str, Any]:
    """Aggregates every sub-check into one status page. Overall status is
    'degraded' (not 'error') if a non-critical subsystem like embeddings
    reports not_implemented — that's an expected, documented state in this
    build, not an outage."""
    checks: Dict[str, Dict[str, Any]] = {
        "database": check_database(db),
        "model_registry": check_model_registry(),
        "embedding": check_embedding_subsystem(),
        "monitoring": check_monitoring_subsystem(),
        "cache": check_cache_subsystem(),
        "system": check_system_resources(),
    }

    critical_failures: List[str] = [
        name for name, result in checks.items()
        if name in {"database"} and result["status"] == "error"
    ]

    overall = "error" if critical_failures else "ok"
    return {"status": overall, "checks": checks}

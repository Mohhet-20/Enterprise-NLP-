"""
Aggregates every v1 endpoint module under one router.

Adding a new endpoint module = create it under `endpoints/`, then add one
`api_router.include_router(...)` line here. `main.py` never needs to change.
"""

from fastapi import APIRouter

from backend.api.v1.endpoints import (
    audit,
    auth,
    datasets,
    embeddings,
    evaluation,
    health,
    inference,
    model_registry,
    monitoring,
    tasks,
)

api_router = APIRouter()

api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router, tags=["auth"])
api_router.include_router(tasks.router, tags=["tasks"])
api_router.include_router(inference.router, tags=["inference"])
api_router.include_router(evaluation.router, tags=["evaluation"])
api_router.include_router(model_registry.router, tags=["model_registry"])
api_router.include_router(datasets.router, tags=["datasets"])
api_router.include_router(embeddings.router, tags=["embeddings"])
api_router.include_router(audit.router, tags=["audit"])
api_router.include_router(monitoring.router, tags=["monitoring"])

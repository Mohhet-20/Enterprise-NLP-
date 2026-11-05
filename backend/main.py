"""
Application entrypoint. Run with:
    uvicorn backend.main:app --reload

Responsibilities kept here (and ONLY here):
- construct the FastAPI app
- wire cross-cutting middleware and exception handlers
- mount the versioned API router
- run startup/shutdown hooks (DB init, plugin loading)

Everything else lives in its own module.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.v1.router import api_router
from backend.config.logging_config import configure_logging, get_logger
from backend.config.settings import get_settings
from backend.core.exception_handlers import register_exception_handlers
from backend.core.middleware import RequestContextMiddleware
from backend.core.rate_limiting import RateLimitMiddleware
from backend.core.security_headers import RequestSizeLimitMiddleware, SecurityHeadersMiddleware
from backend.database.session import init_db

settings = get_settings()
configure_logging()
logger = get_logger("api")


def _preload_models() -> None:
    """Warm the served tasks' models (one at a time; see BaseNLPModel's load lock). Failures are logged, not fatal:
    the model then loads on first use as usual."""
    from backend.nlp.inference.model_factory import model_factory
    from backend.plugins.plugin_registry import get_task_plugin, list_supported_tasks

    seen = set()
    for task in list_supported_tasks():
        plugin = get_task_plugin(task)
        key = (plugin.default_architecture, plugin.default_model_name)
        if key in seen:
            continue
        seen.add(key)
        try:
            model_factory.get_model(plugin.default_architecture, plugin.default_model_name, task=task).load()
            logger.info("model_preloaded", extra={"task": task.value})
        except Exception as exc:  # noqa: BLE001 - preloading is an optimisation
            logger.warning("model_preload_failed", extra={"task": task.value, "error": str(exc)})


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("startup", extra={"environment": settings.environment.value})
    init_db()

    from backend.database.seed import seed_default_admin
    from backend.database.session import SessionLocal

    seed_db = SessionLocal()
    try:
        seed_default_admin(seed_db)
    finally:
        seed_db.close()

    import backend.plugins  # noqa: F401  registers all task plugins

    if settings.preload_models:
        import threading

        threading.Thread(target=_preload_models, name="model-preload", daemon=True).start()

    yield
    logger.info("shutdown")


app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(RequestContextMiddleware)
# Outermost: reject oversized requests before request-id assignment, rate
# limiting, or auth decode ever run — the cheapest possible rejection.
app.add_middleware(RequestSizeLimitMiddleware)

register_exception_handlers(app)

app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.get("/")
def root() -> dict:
    return {"message": f"{settings.app_name} is running.", "docs": "/docs"}

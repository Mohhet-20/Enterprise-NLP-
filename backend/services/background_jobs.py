"""
Background job functions, dispatched via FastAPI's `BackgroundTasks`
(runs after the response has been sent, in the same process). A
distributed queue (Celery / RQ / Arq) is the next step once jobs need to
survive restarts or run on separate workers.

Each function opens its own database session rather than reusing the
request-scoped one: `get_db_session`'s `finally: session.close()` runs as
soon as the response is returned, which is *before* a background task
actually executes — reusing that session would mean operating on an
already-closed one.
"""

from backend.config.logging_config import get_logger
from backend.database import session as db_session_module
from backend.repositories.dataset_record_repository import DatasetRecordRepository
from backend.services.embedding_service import embedding_index_service

logger = get_logger("api")


def rebuild_embedding_index_task(dataset_id: str) -> None:
    """Dispatched after a dataset upload so the request returns
    immediately with the validation report, while the embedding index
    (previously a manual, separate `/embeddings/build` call) rebuilds
    quietly in the background. A background task must never let an
    exception escape and crash the worker — caught and logged instead."""
    db = db_session_module.SessionLocal()
    try:
        records = DatasetRecordRepository(db).all_for_dataset(dataset_id)
        if not records:
            return
        embedding_index_service.build_index(
            dataset_id,
            record_ids=[r.id for r in records],
            texts=[r.text for r in records],
            labels=[r.label for r in records],
        )
        logger.info(
            "background_embedding_index_rebuilt",
            extra={"dataset_id": dataset_id, "num_records": len(records)},
        )
    except Exception as exc:  # noqa: BLE001 — background tasks must not crash the worker
        logger.error(
            "background_embedding_index_rebuild_failed",
            extra={"dataset_id": dataset_id, "error": str(exc)},
        )
    finally:
        db.close()

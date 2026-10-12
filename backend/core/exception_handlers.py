"""
Maps PlatformError subclasses (and unhandled exceptions) to consistent
JSON error responses. Registered once in main.py via register_exception_handlers(app).
"""

import uuid

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from backend.config.logging_config import get_logger
from backend.core.exceptions import PlatformError

logger = get_logger("api")


def _error_payload(error_code: str, message: str, details: dict, request_id: str) -> dict:
    return {
        "error": {
            "code": error_code,
            "message": message,
            "details": details,
            "request_id": request_id,
        }
    }


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(PlatformError)
    async def platform_error_handler(request: Request, exc: PlatformError) -> JSONResponse:
        request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
        logger.warning(
            "platform_error",
            extra={
                "request_id": request_id,
                "error_type": type(exc).__name__,
                "path": str(request.url.path),
            },
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_payload(type(exc).__name__, exc.message, exc.details, request_id),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
        logger.error(
            "unhandled_exception",
            extra={
                "request_id": request_id,
                "error_type": type(exc).__name__,
                "path": str(request.url.path),
            },
            exc_info=exc,
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=_error_payload(
                "InternalServerError",
                "An unexpected error occurred. It has been logged.",
                {},
                request_id,
            ),
        )

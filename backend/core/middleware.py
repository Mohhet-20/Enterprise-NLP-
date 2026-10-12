"""
Cross-cutting HTTP middleware:
- assigns a request_id to every request (propagated into logs and error payloads)
- logs every request/response with latency (the "Performance metrics" +
  "API requests" logging categories called out in the platform spec)
"""

import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from backend.config.logging_config import get_logger

api_logger = get_logger("api")
perf_logger = get_logger("performance")


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - start) * 1000, 2)

        response.headers["X-Request-ID"] = request_id

        api_logger.info(
            "request_completed",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
            },
        )
        perf_logger.info(
            "request_latency",
            extra={"path": request.url.path, "duration_ms": duration_ms},
        )
        return response

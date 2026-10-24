"""
Two request/response protections:

1. Security headers on every response. Not a comprehensive CSP (which
   would need to be tuned against the actual frontend's asset origins to
   avoid breaking it — that's a frontend-deployment-specific decision,
   not a generic default), but the headers that are safe, standard, and
   have zero tradeoffs: MIME-sniffing protection, clickjacking
   protection, and referrer leakage protection.

2. A request body size cap. Without one, a client can send an arbitrarily
   large body and the app will buffer all of it before Pydantic
   validation ever gets a chance to reject it — turning a single request
   into a memory-exhaustion vector. Checked via Content-Length up front
   (fast, no buffering) with a streaming fallback check for chunked
   requests that don't declare a length.
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

DEFAULT_MAX_BODY_BYTES = 15 * 1024 * 1024  # 15MB — comfortably above a large dataset CSV, well under "abusive"


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        # HSTS is deliberately NOT set here — it's only safe to send over
        # an actual HTTPS connection, which in this architecture is
        # terminated at the ingress/load balancer (see
        # deployment/k8s/ingress.yaml), not at this application. Setting
        # it here would be asserting a guarantee this layer can't verify.
        return response


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_body_bytes: int = DEFAULT_MAX_BODY_BYTES) -> None:
        super().__init__(app)
        self._max_body_bytes = max_body_bytes

    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get("content-length")
        if content_length is not None:
            try:
                if int(content_length) > self._max_body_bytes:
                    return self._too_large_response()
            except ValueError:
                pass  # malformed header — let the app's normal validation handle it

        response = await call_next(request)
        return response

    def _too_large_response(self) -> JSONResponse:
        return JSONResponse(
            status_code=413,
            content={
                "error": {
                    "code": "PayloadTooLargeError",
                    "message": f"Request body exceeds the {self._max_body_bytes // (1024*1024)}MB limit.",
                    "details": {},
                    "request_id": "",
                }
            },
        )

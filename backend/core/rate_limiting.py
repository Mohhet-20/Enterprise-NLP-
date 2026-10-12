"""
Rate limiting middleware: a fixed 60-second window, keyed by
authenticated user id when available (from the bearer token) or by
client IP otherwise. Backed by `backend.core.cache.cache_service`, so it
gets real cross-worker correctness when Redis is reachable and a
same-process approximation when it isn't — same tradeoff as the cache
itself, documented there.

Login and registration get a stricter, separate limit than the general
API — standard brute-force/credential-stuffing/registration-spam
protection, independent of the per-account lockout in
backend/services/auth_service.py (that protects one specific account
after repeated failures against it; this limits how fast *any* number of
attempts, against any number of accounts, can be made from one identity).

Health/observability endpoints are exempt — an orchestrator's liveness
probe shouldn't be able to get itself rate-limited.
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from backend.auth.jwt_handler import decode_access_token
from backend.config.settings import get_settings
from backend.core.cache import cache_service

_EXEMPT_PATH_PREFIXES = (
    "/api/v1/health",
    "/api/v1/liveness",
    "/api/v1/readiness",
    "/api/v1/status",
    "/docs",
    "/openapi.json",
    "/redoc",
)

# Paths that get the stricter auth-specific limit instead of the general one.
_AUTH_RATE_LIMITED_PATHS = (
    "/api/v1/auth/login",
    "/api/v1/auth/register",
    "/api/v1/auth/refresh",
)


def _rate_limit_identity(request: Request) -> str:
    auth_header = request.headers.get("authorization", "")
    if auth_header.lower().startswith("bearer "):
        token = auth_header[7:]
        try:
            payload = decode_access_token(token)
            user_id = payload.get("sub")
            if user_id:
                return f"user:{user_id}"
        except Exception:  # noqa: BLE001 — invalid/expired token, fall back to IP
            pass
    client_host = request.client.host if request.client else "unknown"
    return f"ip:{client_host}"


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if any(request.url.path.startswith(p) for p in _EXEMPT_PATH_PREFIXES):
            return await call_next(request)

        settings = get_settings()
        identity = _rate_limit_identity(request)

        is_auth_endpoint = request.url.path in _AUTH_RATE_LIMITED_PATHS
        if is_auth_endpoint:
            limit = settings.auth_rate_limit_requests_per_minute
            window_key = f"ratelimit:auth:{identity}"
        else:
            limit = settings.rate_limit_requests_per_minute
            window_key = f"ratelimit:{identity}"

        count = cache_service.increment(window_key, ttl_seconds=60)

        if count > limit:
            return JSONResponse(
                status_code=429,
                content={
                    "error": {
                        "code": "RateLimitExceededError",
                        "message": "Rate limit exceeded. Please slow down.",
                        "details": {"limit_per_minute": limit},
                        "request_id": getattr(request.state, "request_id", ""),
                    }
                },
                headers={"Retry-After": "60"},
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(max(0, limit - count))
        return response

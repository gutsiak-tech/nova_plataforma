"""Rate limiting simples por IP (memória, sem Redis)."""

from __future__ import annotations

import time
from collections import defaultdict
from threading import Lock

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

_LIMITED_PREFIXES = (
    "/api/gold",
    "/api/ict",
    "/api/map",
    "/api/ops",
)
_WINDOW_SECONDS = 60.0


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, *, enabled: bool, per_minute: int) -> None:
        super().__init__(app)
        self.enabled = enabled
        self.per_minute = max(1, per_minute)
        self._lock = Lock()
        self._hits: dict[str, list[float]] = defaultdict(list)

    @staticmethod
    def _client_ip(request: Request) -> str:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        if request.client and request.client.host:
            return request.client.host
        return "unknown"

    @staticmethod
    def _should_limit(path: str) -> bool:
        return any(path.startswith(prefix) for prefix in _LIMITED_PREFIXES)

    @staticmethod
    def _bucket_key(request: Request) -> str:
        ip = RateLimitMiddleware._client_ip(request)
        path = request.url.path
        for prefix in _LIMITED_PREFIXES:
            if path.startswith(prefix):
                return f"{ip}:{prefix}"
        return ip

    def _is_allowed(self, client_key: str) -> bool:
        now = time.monotonic()
        cutoff = now - _WINDOW_SECONDS
        with self._lock:
            bucket = self._hits[client_key]
            self._hits[client_key] = [ts for ts in bucket if ts > cutoff]
            if len(self._hits[client_key]) >= self.per_minute:
                return False
            self._hits[client_key].append(now)
            return True

    async def dispatch(self, request: Request, call_next) -> Response:
        if not self.enabled or request.method == "OPTIONS":
            return await call_next(request)

        path = request.url.path
        if not self._should_limit(path):
            return await call_next(request)

        client_key = self._bucket_key(request)
        if not self._is_allowed(client_key):
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests."},
            )

        return await call_next(request)

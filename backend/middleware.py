"""
backend/middleware.py – FastAPI middleware stack.
  - RequestLoggingMiddleware : logs method, path, status, duration
  - SecurityHeadersMiddleware: adds security headers to every response
"""
import time
import uuid
import logging
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("agentflow.access")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Structured access log for every request."""

    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())[:8]
        start = time.perf_counter()
        request.state.request_id = request_id

        try:
            response: Response = await call_next(request)
        except Exception as exc:
            elapsed = (time.perf_counter() - start) * 1000
            logger.error(
                f"[{request_id}] {request.method} {request.url.path} "
                f"ERROR {elapsed:.1f}ms — {exc}"
            )
            raise

        elapsed = (time.perf_counter() - start) * 1000
        log_level = logging.WARNING if response.status_code >= 400 else logging.INFO
        logger.log(
            log_level,
            f"[{request_id}] {request.method} {request.url.path} "
            f"{response.status_code} {elapsed:.1f}ms",
        )

        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time"] = f"{elapsed:.1f}ms"
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add basic security headers to every response."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        if "server" in response.headers:
            del response.headers["server"]
        return response

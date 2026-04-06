"""
backend/exceptions.py
Custom exceptions + FastAPI exception handlers.
"""
from __future__ import annotations
import logging
from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("agentflow.errors")


# ── Domain Exceptions ─────────────────────────────────────────────────────────

class AgentFlowError(Exception):
    """Base exception for all AgentFlow errors."""
    status_code: int = 500
    detail: str = "An unexpected error occurred"

    def __init__(self, detail: str | None = None):
        self.detail = detail or self.__class__.detail
        super().__init__(self.detail)


class NotFoundError(AgentFlowError):
    status_code = 404
    detail = "Resource not found"


class ValidationError(AgentFlowError):
    status_code = 422
    detail = "Validation error"


class AgentError(AgentFlowError):
    status_code = 503
    detail = "Agent processing failed"


class DatabaseError(AgentFlowError):
    status_code = 503
    detail = "Database operation failed"


# ── FastAPI Exception Handlers ────────────────────────────────────────────────

async def agentflow_exception_handler(request: Request, exc: AgentFlowError):
    logger.error(f"{request.method} {request.url.path} -> {exc.__class__.__name__}: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.__class__.__name__, "detail": exc.detail},
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": "HTTPException", "detail": exc.detail},
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = []
    for e in exc.errors():
        field = " -> ".join(str(loc) for loc in e["loc"] if loc != "body")
        errors.append({"field": field, "message": e["msg"], "type": e["type"]})
    logger.warning(f"Validation error on {request.url.path}: {errors}")
    return JSONResponse(
        status_code=422,
        content={"error": "ValidationError", "detail": errors},
    )


async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error on {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "InternalServerError", "detail": "Something went wrong. Please try again."},
    )


def register_exception_handlers(app):
    """Call this in main.py to wire up all handlers."""
    app.add_exception_handler(AgentFlowError, agentflow_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)

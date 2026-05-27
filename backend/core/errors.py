import json
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend.core.logging import get_logger

PROBLEM_CONTENT_TYPE = "application/problem+json"

logger = get_logger(__name__)


class AppError(Exception):
    status_code: int = 500
    code: str = "internal_error"
    title: str = "Internal Server Error"

    def __init__(
        self,
        detail: str | None = None,
        *,
        code: str | None = None,
        title: str | None = None,
        status_code: int | None = None,
        extra: dict[str, Any] | None = None,
    ):
        super().__init__(detail or self.title)
        self.detail = detail or self.title
        if code is not None:
            self.code = code
        if title is not None:
            self.title = title
        if status_code is not None:
            self.status_code = status_code
        self.extra = extra or {}


class NotFoundError(AppError):
    status_code = 404
    code = "not_found"
    title = "Not Found"


class ValidationError(AppError):
    status_code = 422
    code = "validation_error"
    title = "Validation Error"


class ConflictError(AppError):
    status_code = 409
    code = "conflict"
    title = "Conflict"


class GoneError(AppError):
    status_code = 410
    code = "gone"
    title = "Gone"


class RateLimitError(AppError):
    status_code = 429
    code = "rate_limited"
    title = "Too Many Requests"


class UpstreamError(AppError):
    status_code = 502
    code = "upstream_error"
    title = "Upstream Error"


def _problem_response(
    request: Request,
    *,
    status_code: int,
    code: str,
    title: str,
    detail: str,
    extra: dict[str, Any] | None = None,
) -> JSONResponse:
    payload: dict[str, Any] = {
        "type": f"about:blank#{code}",
        "title": title,
        "status": status_code,
        "detail": detail,
        "code": code,
        "instance": str(request.url.path),
    }
    request_id = getattr(request.state, "request_id", None)
    if request_id:
        payload["request_id"] = request_id
    if extra:
        payload.update(extra)
    return JSONResponse(
        status_code=status_code,
        content=payload,
        media_type=PROBLEM_CONTENT_TYPE,
    )


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    logger.warning(
        "app_error",
        code=exc.code,
        status=exc.status_code,
        detail=exc.detail,
        path=request.url.path,
    )
    return _problem_response(
        request,
        status_code=exc.status_code,
        code=exc.code,
        title=exc.title,
        detail=exc.detail,
        extra=exc.extra,
    )


async def http_exception_handler(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    title = exc.detail if isinstance(exc.detail, str) else "HTTP Error"
    return _problem_response(
        request,
        status_code=exc.status_code,
        code=f"http_{exc.status_code}",
        title=title,
        detail=title,
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    # Pydantic v2 includes ctx.error as an Exception instance, which is not
    # JSON-serializable. Roundtrip through json with default=str to sanitize.
    raw_errors = exc.errors()
    safe_errors = json.loads(json.dumps(raw_errors, default=str))
    return _problem_response(
        request,
        status_code=422,
        code="validation_error",
        title="Validation Error",
        detail="Request validation failed.",
        extra={"errors": safe_errors},
    )


async def unhandled_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    logger.exception(
        "unhandled_exception",
        path=request.url.path,
        method=request.method,
    )
    return _problem_response(
        request,
        status_code=500,
        code="internal_error",
        title="Internal Server Error",
        detail="An unexpected error occurred.",
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)

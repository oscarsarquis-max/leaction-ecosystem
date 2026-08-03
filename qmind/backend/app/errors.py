"""Uniform API errors (ADR-003) — no internal details in responses."""

from __future__ import annotations

from uuid import uuid4

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.schemas.common import ErrorBody, FieldError


class AppError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = 400,
        field_errors: list[FieldError] | None = None,
    ) -> None:
        self.code = code
        self.message = message
        self.status_code = status_code
        self.field_errors = field_errors
        super().__init__(message)


def _dump_error(
    *,
    code: str,
    message: str,
    correlation_id: str,
    field_errors: list[FieldError] | None = None,
) -> dict:
    body = ErrorBody(
        code=code,
        message=message,
        correlation_id=correlation_id,
        field_errors=field_errors,
    )
    # Exclude null field_errors for cleaner payloads; always keep the three core keys.
    data = body.model_dump(exclude_none=True)
    return data


async def app_error_handler(_request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=_dump_error(
            code=exc.code,
            message=exc.message,
            correlation_id=str(uuid4()),
            field_errors=exc.field_errors,
        ),
    )


async def validation_error_handler(
    _request: Request, exc: RequestValidationError
) -> JSONResponse:
    field_errors: list[FieldError] = []
    for err in exc.errors():
        loc = err.get("loc") or ()
        # Drop leading "body" / "query" / "header" for a stable field path.
        parts = [str(p) for p in loc if p not in ("body", "query", "header", "path")]
        field = ".".join(parts) if parts else "request"
        field_errors.append(
            FieldError(
                field=field,
                code=str(err.get("type") or "validation_error"),
                message=str(err.get("msg") or "Invalid value"),
            )
        )
    return JSONResponse(
        status_code=422,
        content=_dump_error(
            code="validation_error",
            message="Request validation failed",
            correlation_id=str(uuid4()),
            field_errors=field_errors or None,
        ),
    )


async def http_exception_handler(
    _request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    """Map framework HTTPException to ErrorBody (no raw detail objects)."""
    detail = exc.detail
    if isinstance(detail, str):
        message = detail
        code = "http_error"
    else:
        message = "Request failed"
        code = "http_error"
    if exc.status_code == 401:
        code = "unauthorized"
    elif exc.status_code == 403:
        code = "forbidden"
    elif exc.status_code == 404:
        code = "not_found"
    return JSONResponse(
        status_code=exc.status_code,
        content=_dump_error(
            code=code,
            message=message,
            correlation_id=str(uuid4()),
        ),
    )

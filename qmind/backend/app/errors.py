"""Uniform API errors (ADR-003)."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from fastapi import Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel


class ErrorBody(BaseModel):
    code: str
    message: str
    correlation_id: str
    details: dict[str, Any] | None = None


class AppError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = 400,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details
        super().__init__(message)


async def app_error_handler(_request: Request, exc: AppError) -> JSONResponse:
    body = ErrorBody(
        code=exc.code,
        message=exc.message,
        correlation_id=str(uuid4()),
        details=exc.details,
    )
    return JSONResponse(status_code=exc.status_code, content=body.model_dump())

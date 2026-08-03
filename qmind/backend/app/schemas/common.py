"""Cross-cutting request/response shapes for the public API contract."""

from __future__ import annotations

from typing import Annotated

from fastapi import Header, Query
from pydantic import BaseModel, Field


class FieldError(BaseModel):
    """Field-level validation detail — never includes stack traces or SQL."""

    field: str = Field(..., examples=["body.waiver_reason"])
    code: str = Field(..., examples=["required", "too_short", "invalid_type"])
    message: str = Field(..., examples=["Field required"])


class ErrorBody(BaseModel):
    """Uniform error envelope (ADR-003)."""

    code: str = Field(..., examples=["not_found", "sod_violation", "validation_error"])
    message: str = Field(..., examples=["Resource not found"])
    correlation_id: str = Field(
        ...,
        examples=["11111111-2222-4333-8444-555555555555"],
        description="Correlate client logs with platform_audit_events / server logs.",
    )
    field_errors: list[FieldError] | None = Field(
        default=None,
        description="Present for input validation failures; omit or null otherwise.",
    )


class PageMeta(BaseModel):
    """Pagination metadata for collection endpoints."""

    limit: int = Field(..., ge=1, le=100, examples=[50])
    next_cursor: str | None = Field(
        default=None,
        description="Opaque cursor for the next page; null when no further items.",
        examples=[None],
    )


LimitQuery = Annotated[
    int,
    Query(
        ge=1,
        le=100,
        description="Maximum items to return (collections). Default 50, max 100.",
    ),
]
CursorQuery = Annotated[
    str | None,
    Query(
        description=(
            "Opaque pagination cursor from a previous PageMeta.next_cursor. "
            "Omit for the first page. Currently reserved: first page only "
            "(cursor ignored until envelope migration)."
        ),
    ),
]

IdempotencyKeyHeader = Annotated[
    str | None,
    Header(
        alias="Idempotency-Key",
        description=(
            "Optional client idempotency key for safely retrying create/command "
            "operations (ADR-003). Scope is the organization. Max 128 chars."
        ),
        max_length=128,
    ),
]

OrganizationIdHeader = Annotated[
    str,
    Header(
        alias="X-Organization-Id",
        description=(
            "Active organization UUID. Must match an active Membership for the "
            "authenticated user. Required on tenant-scoped routes."
        ),
        examples=["aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee"],
    ),
]

ERROR_RESPONSES = {
    400: {"model": ErrorBody, "description": "Bad request / domain guard"},
    401: {"model": ErrorBody, "description": "Missing or invalid authentication"},
    403: {"model": ErrorBody, "description": "Forbidden / SoD / role"},
    404: {"model": ErrorBody, "description": "Not found (or cross-tenant hide)"},
    409: {"model": ErrorBody, "description": "Conflict / invalid transition"},
    410: {"model": ErrorBody, "description": "Gone (e.g. upload expired)"},
    422: {"model": ErrorBody, "description": "Validation error"},
    503: {"model": ErrorBody, "description": "Dependency unavailable"},
}

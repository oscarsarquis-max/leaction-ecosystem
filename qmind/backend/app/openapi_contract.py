"""OpenAPI 3 contract customization — stable operationIds, security, errors."""

from __future__ import annotations

import copy
import json
from typing import Any

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

from app.schemas.common import ERROR_RESPONSES, ErrorBody

API_TITLE = "QMind API"
API_VERSION = "1.0.0"
API_DESCRIPTION = """
QMind HTTP API — multi-tenant quality diagnosis (domain-docs-v0).

## Authentication

- **Production / Cognito:** `Authorization: Bearer <JWT>` (AWS Cognito User Pool).
- **Local only (`AUTH_MODE=dev`):** `X-Dev-User-Sub` + `X-Dev-User-Email` (forbidden when `ENVIRONMENT=prod`).

## Tenant context

Tenant-scoped routes require **`X-Organization-Id`** matching an active Membership.
Cross-tenant access returns **404** (no existence leak).

## Idempotency

Commands that may be safely retried accept optional **`Idempotency-Key`**
(scoped per organization). Documented on create/command operations.

## Pagination & filters

Collection endpoints accept `limit` (1–100, default 50) and optional `cursor`.
Filters are explicit query parameters (e.g. `assessment_id`).
Responses currently return JSON arrays; `PageMeta` is defined for the upcoming
envelope without breaking this initial freeze.

## Errors

All errors use `ErrorBody`: `code`, `message`, `correlation_id`, optional `field_errors`.
Responses never include stack traces, SQL, storage URLs, or peer-tenant data.

## Synthetic examples

Examples use fictional UUIDs and placeholder text — never production data.
"""

_SYNTH_ORG = "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee"
_SYNTH_CORR = "11111111-2222-4333-8444-555555555555"


def _error_example(code: str, message: str, with_fields: bool = False) -> dict[str, Any]:
    body: dict[str, Any] = {
        "code": code,
        "message": message,
        "correlation_id": _SYNTH_CORR,
    }
    if with_fields:
        body["field_errors"] = [
            {
                "field": "body.waiver_reason",
                "code": "string_too_short",
                "message": "String should have at least 1 character",
            }
        ]
    return body


def build_openapi_schema(app: FastAPI) -> dict[str, Any]:
    if app.openapi_schema:
        return app.openapi_schema

    schema = get_openapi(
        title=API_TITLE,
        version=API_VERSION,
        description=API_DESCRIPTION.strip(),
        routes=app.routes,
        tags=[
            {"name": "health", "description": "Liveness and readiness (no auth)."},
            {"name": "organizations", "description": "Organization and membership."},
            {"name": "assessments", "description": "Assessment lifecycle, scope, team."},
            {"name": "Interviews", "description": "Field interviews, answers, and model questions."},
            {"name": "evidences", "description": "Evidence upload, links, and approval."},
            {"name": "findings", "description": "Findings lifecycle."},
            {"name": "actions", "description": "Action plans and action items."},
            {"name": "maturity", "description": "Maturity assessment packages."},
            {"name": "reports", "description": "Versioned report publication."},
        ],
    )

    schema["servers"] = [
        {"url": "/", "description": "Current host"},
    ]

    components = schema.setdefault("components", {})
    schemas = components.setdefault("schemas", {})
    schemas["FieldError"] = {
        "type": "object",
        "required": ["field", "code", "message"],
        "properties": {
            "field": {"type": "string", "examples": ["body.waiver_reason"]},
            "code": {"type": "string", "examples": ["required"]},
            "message": {"type": "string", "examples": ["Field required"]},
        },
        "additionalProperties": False,
        "title": "FieldError",
    }
    schemas["ErrorBody"] = {
        "type": "object",
        "required": ["code", "message", "correlation_id"],
        "properties": {
            "code": {"type": "string", "examples": ["not_found"]},
            "message": {"type": "string", "examples": ["Resource not found"]},
            "correlation_id": {
                "type": "string",
                "format": "uuid",
                "examples": [_SYNTH_CORR],
            },
            "field_errors": {
                "type": "array",
                "items": {"$ref": "#/components/schemas/FieldError"},
                "nullable": True,
            },
        },
        "additionalProperties": False,
        "title": "ErrorBody",
        "description": "Uniform error envelope (ADR-003). No internal details.",
    }
    # Drop unused import side-effect: keep ErrorBody model referenced for runtime.
    _ = ErrorBody

    components["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "Cognito access token (AUTH_MODE=cognito).",
        },
        "DevUserSub": {
            "type": "apiKey",
            "in": "header",
            "name": "X-Dev-User-Sub",
            "description": "Local DEV only — Cognito subject substitute.",
        },
        "DevUserEmail": {
            "type": "apiKey",
            "in": "header",
            "name": "X-Dev-User-Email",
            "description": "Local DEV only — user email for upsert.",
        },
    }

    error_ref = {"$ref": "#/components/schemas/ErrorBody"}
    standard_errors = {
        str(code): {
            "description": meta["description"],
            "content": {
                "application/json": {
                    "schema": error_ref,
                    "example": _error_example(
                        "validation_error" if code == 422 else "not_found",
                        "Request validation failed"
                        if code == 422
                        else "Resource not found",
                        with_fields=(code == 422),
                    ),
                }
            },
        }
        for code, meta in ERROR_RESPONSES.items()
    }

    paths = schema.get("paths", {})
    # Drop non-contract paths (root discovery).
    paths.pop("/", None)

    for path, methods in list(paths.items()):
        if path not in ("/health", "/ready") and not path.startswith("/api/v1"):
            paths.pop(path, None)
            continue
        for method, operation in list(methods.items()):
            if method.startswith("x-") or not isinstance(operation, dict):
                continue
            op_id = operation.get("operationId")
            if not op_id:
                raise RuntimeError(f"Missing operationId for {method.upper()} {path}")

            # Security: health/ready public; else bearer (and document org header).
            if path in ("/health", "/ready"):
                operation["security"] = []
            else:
                operation["security"] = [{"BearerAuth": []}]

            responses = operation.setdefault("responses", {})
            for code, body in standard_errors.items():
                if code not in responses:
                    responses[code] = copy.deepcopy(body)

            # Synthetic org header parameter on tenant routes (document even if
            # dependency injection also reads it).
            if path.startswith("/api/v1") and path not in (
                "/api/v1/organizations",
                "/api/v1/organizations/me/memberships",
            ):
                params = operation.setdefault("parameters", [])
                if not any(
                    isinstance(p, dict)
                    and p.get("name") == "X-Organization-Id"
                    and p.get("in") == "header"
                    for p in params
                ):
                    params.append(
                        {
                            "name": "X-Organization-Id",
                            "in": "header",
                            "required": True,
                            "schema": {
                                "type": "string",
                                "format": "uuid",
                                "example": _SYNTH_ORG,
                            },
                            "description": "Active organization context (Membership required).",
                        }
                    )

    # Stable key order for deterministic export.
    app.openapi_schema = _canonicalize(schema)
    return app.openapi_schema


def _canonicalize(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: _canonicalize(obj[k]) for k in sorted(obj.keys())}
    if isinstance(obj, list):
        return [_canonicalize(x) for x in obj]
    return obj


def dump_openapi_json(app: FastAPI) -> str:
    """Deterministic JSON (sorted keys, stable separators, trailing newline)."""
    schema = build_openapi_schema(app)
    return json.dumps(schema, indent=2, sort_keys=True, ensure_ascii=False) + "\n"

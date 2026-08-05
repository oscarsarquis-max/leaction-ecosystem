from __future__ import annotations

from fastapi import APIRouter

from app.config import get_settings
from app.db import ping_database
from app.errors import AppError
from app.schemas.common import ERROR_RESPONSES

router = APIRouter(tags=["health"])


@router.get(
    "/health",
    operation_id="getHealth",
    responses={503: ERROR_RESPONSES[503]},
    summary="Health check",
)
def health() -> dict:
    settings = get_settings()
    try:
        db = ping_database()
    except Exception as exc:
        raise AppError("db_unavailable", "Database unavailable", status_code=503) from exc
    return {
        "status": "ok",
        "app": settings.app_name,
        "environment": settings.environment,
        "auth_mode": settings.auth_mode,
        "database": db["database"],
        "cluster_note": "logical database qmind_dev on shared Postgres service leaction_db",
    }


@router.get(
    "/ready",
    operation_id="getReady",
    responses={503: ERROR_RESPONSES[503]},
    summary="Readiness probe",
)
def ready() -> dict:
    """Liveness/readiness for orchestrators — no config, auth mode, or host details."""
    try:
        ping_database()
    except Exception as exc:
        raise AppError("not_ready", "Service not ready", status_code=503) from exc
    return {"status": "ready"}

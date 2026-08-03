"""QMind API — FastAPI foundation (post Phase-0 gate)."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.health import router as health_router
from app.config import get_settings
from app.errors import AppError, app_error_handler
from app.modules.actions.router import router as actions_router
from app.modules.assessments.router import router as assessments_router
from app.modules.evidence.router import router as evidence_router
from app.modules.findings.router import router as findings_router
from app.modules.orgs.router import router as orgs_router


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Validates AUTH_MODE=dev forbidden under ENVIRONMENT=prod.
    get_settings()
    yield


settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.environment != "prod" else None,
)

app.add_exception_handler(AppError, app_error_handler)
app.include_router(health_router)
app.include_router(orgs_router, prefix=settings.api_prefix)
app.include_router(assessments_router, prefix=settings.api_prefix)
app.include_router(evidence_router, prefix=settings.api_prefix)
app.include_router(findings_router, prefix=settings.api_prefix)
app.include_router(actions_router, prefix=settings.api_prefix)


@app.get("/")
def root() -> dict[str, str]:
    return {
        "service": settings.app_name,
        "docs": "/docs",
        "health": "/health",
        "api": settings.api_prefix,
    }

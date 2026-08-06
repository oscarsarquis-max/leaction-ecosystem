"""QMind API — FastAPI foundation (post Phase-0 gate)."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.health import router as health_router
from app.config import get_settings
from app.errors import (
    AppError,
    app_error_handler,
    http_exception_handler,
    validation_error_handler,
)
from app.modules.actions.router import router as actions_router
from app.modules.agenda.router import router as agenda_router
from app.modules.assessments.router import router as assessments_router
from app.modules.evidence.router import router as evidence_router
from app.modules.findings.router import router as findings_router
from app.modules.guided.router import router as guided_router
from app.modules.audit_plan.router import router as audit_plan_router
from app.modules.interviews.router import router as interviews_router
from app.modules.jobs.router import router as jobs_router
from app.modules.maturity.router import router as maturity_router
from app.modules.orgs.router import router as orgs_router
from app.modules.reports.router import router as reports_router
from app.openapi_contract import API_DESCRIPTION, API_TITLE, API_VERSION, build_openapi_schema


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Validates AUTH_MODE=dev forbidden under ENVIRONMENT=prod.
    get_settings()
    yield


settings = get_settings()

app = FastAPI(
    title=API_TITLE,
    version=API_VERSION,
    description=API_DESCRIPTION.strip(),
    lifespan=lifespan,
    docs_url="/docs" if settings.environment != "prod" else None,
    redoc_url="/redoc" if settings.environment != "prod" else None,
)

app.add_exception_handler(AppError, app_error_handler)
app.add_exception_handler(RequestValidationError, validation_error_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)

if settings.cors_origin_list:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=[
            "Authorization",
            "Content-Type",
            "X-Organization-Id",
            "Idempotency-Key",
            "X-QMind-Tenant-Epoch",
        ],
        expose_headers=["X-Request-Id"],
        max_age=600,
    )

app.include_router(health_router)
app.include_router(orgs_router, prefix=settings.api_prefix)
app.include_router(agenda_router, prefix=settings.api_prefix)
app.include_router(assessments_router, prefix=settings.api_prefix)
app.include_router(guided_router, prefix=settings.api_prefix)
app.include_router(audit_plan_router, prefix=settings.api_prefix)
app.include_router(interviews_router, prefix=settings.api_prefix)
app.include_router(evidence_router, prefix=settings.api_prefix)
app.include_router(findings_router, prefix=settings.api_prefix)
app.include_router(actions_router, prefix=settings.api_prefix)
app.include_router(maturity_router, prefix=settings.api_prefix)
app.include_router(reports_router, prefix=settings.api_prefix)
app.include_router(jobs_router, prefix=settings.api_prefix)


@app.get("/", include_in_schema=False)
def root() -> dict[str, str]:
    return {
        "service": settings.app_name,
        "docs": "/docs",
        "health": "/health",
        "api": settings.api_prefix,
    }


def custom_openapi() -> dict:
    return build_openapi_schema(app)


app.openapi = custom_openapi  # type: ignore[method-assign]

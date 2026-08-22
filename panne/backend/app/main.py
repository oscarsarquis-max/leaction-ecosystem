from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.health import HealthResponse, build_health
from app.modules.identity_organization.http import router as identity_router
from app.modules.production_http.errors import sanitized_exception_handler
from app.modules.production_http.reads import router as production_reads
from app.modules.production_http.roles_http import router as membership_roles
from app.modules.production_http.writes import router as production_writes
from app.ready import ReadyResponse, assert_database_ready

settings = get_settings()

app = FastAPI(
    title="Panne",
    version=settings.versao,
    docs_url=None,
    redoc_url=None,
    openapi_url="/openapi.json",
)
app.include_router(identity_router)
app.include_router(
    production_reads,
    prefix="/api/v1/organizations/{organization_id}/production",
)
app.include_router(
    production_writes,
    prefix="/api/v1/organizations/{organization_id}/production",
)
app.include_router(
    membership_roles,
    prefix="/api/v1/organizations/{organization_id}/memberships",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5180",
        "http://localhost:5180",
    ],
    allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE"],
    allow_headers=["*"],
)
app.add_exception_handler(RequestValidationError, sanitized_exception_handler)


@app.exception_handler(HTTPException)
def http_exception_handler(_request: Request, exc: HTTPException) -> JSONResponse:
    if isinstance(exc.detail, dict) and "code" in exc.detail:
        return JSONResponse(status_code=exc.status_code, content=exc.detail)
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


def _custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    schema = get_openapi(title=app.title, version=app.version, routes=app.routes)
    schema.setdefault("components", {}).setdefault("securitySchemes", {})["HTTPBearer"] = {
        "type": "http",
        "scheme": "bearer",
    }
    public = {"/health", "/ready"}
    for path, methods in schema.get("paths", {}).items():
        if path in public:
            continue
        for operation in methods.values():
            if isinstance(operation, dict):
                operation["security"] = [{"HTTPBearer": []}]
    app.openapi_schema = schema
    return schema


app.openapi = _custom_openapi


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return build_health()


@app.get("/ready", response_model=ReadyResponse)
def ready() -> ReadyResponse:
    try:
        assert_database_ready()
    except Exception:
        raise HTTPException(status_code=503, detail="indisponivel") from None
    return ReadyResponse()

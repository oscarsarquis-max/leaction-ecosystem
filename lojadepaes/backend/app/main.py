from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.v1 import api_router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.domain.errors import (
    AuthDisabledError,
    AuthError,
    AuthForbiddenError,
    CapacityError,
    ConfirmationError,
    ConflictError,
    DomainError,
    NotFoundError,
    PriceChangedError,
    RateLimitError,
    TransitionError,
)


def _status_for_domain_error(exc: DomainError) -> int:
    if isinstance(exc, AuthDisabledError):
        return 503
    if isinstance(exc, AuthForbiddenError):
        return 403
    if isinstance(exc, RateLimitError):
        return 429
    if isinstance(exc, AuthError):
        return 401
    if isinstance(exc, NotFoundError):
        return 404
    if isinstance(exc, (TransitionError, CapacityError, ConflictError)):
        return 409
    if isinstance(exc, ConfirmationError):
        return 422
    return 400


def _spa_dir() -> Path | None:
    raw = get_settings().spa_dir.strip()
    if not raw:
        return None
    path = Path(raw).resolve()
    if path.is_dir() and (path / "index.html").is_file():
        return path
    return None


def create_app() -> FastAPI:
    configure_logging()
    from app.admin.configure import ensure_local_session_secret
    from app.domain.email_worker import start_email_outbox_worker

    ensure_local_session_secret()
    get_settings.cache_clear()
    settings = get_settings()

    @asynccontextmanager
    async def lifespan(_application: FastAPI):
        stop = start_email_outbox_worker()
        yield
        if stop is not None:
            stop.set()

    application = FastAPI(
        title="Loja de Pães",
        version="0.1.0",
        docs_url=None,
        redoc_url=None,
        lifespan=lifespan,
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["GET", "HEAD", "OPTIONS", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Content-Type", "Accept", "X-CSRF-Token", "X-Order-Token", "Authorization"],
    )

    @application.middleware("http")
    async def security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        if request.url.path.startswith("/ativar") or "/admin/activate" in request.url.path:
            response.headers["Cache-Control"] = "no-store"
            response.headers["Referrer-Policy"] = "no-referrer"
        return response

    @application.exception_handler(DomainError)
    async def domain_error_handler(_request: Request, exc: DomainError) -> JSONResponse:
        if isinstance(exc, PriceChangedError):
            return JSONResponse(
                {
                    "detail": str(exc),
                    "code": exc.code,
                    "quoted_cents": exc.quoted_cents,
                    "current_cents": exc.current_cents,
                },
                status_code=409,
            )
        return JSONResponse({"detail": str(exc)}, status_code=_status_for_domain_error(exc))

    from app.api.v1.tracking import router as tracking_router

    application.include_router(api_router, prefix="/api/v1")
    application.include_router(tracking_router)

    spa = _spa_dir()
    if spa is not None:
        assets = spa / "assets"
        if assets.is_dir():
            application.mount("/assets", StaticFiles(directory=assets), name="spa-assets")
        images = spa / "images"
        if images.is_dir():
            application.mount("/images", StaticFiles(directory=images), name="spa-images")

        @application.get("/{full_path:path}")
        def spa_fallback(full_path: str):
            candidate = (spa / full_path).resolve()
            if full_path and candidate.is_file() and spa in candidate.parents:
                return FileResponse(candidate)
            return FileResponse(spa / "index.html")

    return application


app = create_app()

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
    UnpaidProductionError,
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


def _code_for_domain_error(exc: DomainError) -> str | None:
    if isinstance(exc, CapacityError):
        return "schedule"
    if isinstance(exc, TransitionError):
        return "transition"
    if isinstance(exc, ConflictError):
        return "conflict"
    return None


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
        stop_mail = start_email_outbox_worker()
        from app.domain.push_worker import start_push_worker

        stop_push = start_push_worker()
        from app.domain.payment_worker import start_payment_worker

        stop_payments = start_payment_worker()
        yield
        if stop_mail is not None:
            stop_mail.set()
        if stop_push is not None:
            stop_push.set()
        if stop_payments is not None:
            stop_payments.set()

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
        if isinstance(exc, UnpaidProductionError):
            return JSONResponse(
                {
                    "detail": str(exc),
                    "code": exc.code,
                    "public_reference": exc.public_reference,
                    "total_cents": exc.total_cents,
                    "currency": exc.currency,
                    "financial_bucket": exc.financial_bucket,
                    "financial_label": exc.financial_label,
                    "uncertain": exc.uncertain,
                },
                status_code=409,
            )
        payload = {"detail": str(exc)}
        code = _code_for_domain_error(exc)
        if code:
            payload["code"] = code
        return JSONResponse(payload, status_code=_status_for_domain_error(exc))

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
                headers = (
                    {"Cache-Control": "no-cache"}
                    if full_path in {"sw.js", "manifest.webmanifest"}
                    else None
                )
                if full_path == "sw.js":
                    return FileResponse(
                        candidate,
                        media_type="application/javascript",
                        headers=headers,
                    )
                return FileResponse(candidate, headers=headers)
            return FileResponse(
                spa / "index.html",
                headers={"Cache-Control": "no-store"},
            )

    return application


app = create_app()

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

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


def create_app() -> FastAPI:
    configure_logging()
    from app.admin.configure import ensure_local_session_secret

    ensure_local_session_secret()
    get_settings.cache_clear()
    settings = get_settings()
    application = FastAPI(
        title="Loja de Pães",
        version="0.1.0",
        docs_url=None,
        redoc_url=None,
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["GET", "HEAD", "OPTIONS", "POST", "PUT", "PATCH"],
        allow_headers=["Content-Type", "Accept", "X-CSRF-Token"],
    )

    @application.exception_handler(DomainError)
    async def domain_error_handler(_request: Request, exc: DomainError) -> JSONResponse:
        return JSONResponse({"detail": str(exc)}, status_code=_status_for_domain_error(exc))

    application.include_router(api_router, prefix="/api/v1")
    return application


app = create_app()

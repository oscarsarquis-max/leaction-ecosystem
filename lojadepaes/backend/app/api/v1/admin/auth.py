from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field

from app.api.deps import AdminUser, AppSettings, ClientHost, DbSession, require_admin_configured
from app.core.config import Settings
from app.domain.activation import consume_activation, lookup_activation
from app.domain.admin_auth import (
    SESSION_COOKIE,
    load_session,
    login_admin,
    login_admin_local,
    revoke_session,
)
from app.domain.errors import (
    AuthDisabledError,
    AuthError,
    AuthForbiddenError,
    RateLimitError,
)
from app.schemas.admin import AccessModeResponse, LoginRequest, SessionResponse

router = APIRouter(prefix="/admin", tags=["admin-auth"])


def _set_session_cookie(response: Response, settings: Settings, raw_token: str) -> None:
    response.set_cookie(
        key=SESSION_COOKIE,
        value=raw_token,
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
        max_age=settings.session_ttl_hours * 3600,
        path="/",
    )


def _clear_session_cookie(response: Response, settings: Settings) -> None:
    response.delete_cookie(
        key=SESSION_COOKIE,
        path="/",
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
    )


def _server_host(request: Request) -> str | None:
    server = request.scope.get("server")
    if not server:
        return None
    return str(server[0]) if server[0] is not None else None


@router.get("/access", response_model=AccessModeResponse)
def access_mode(settings: AppSettings) -> AccessModeResponse:
    return AccessModeResponse(local_passwordless=settings.local_passwordless_eligible)


@router.post("/local-login", response_model=SessionResponse)
def local_login(
    request: Request,
    response: Response,
    db: DbSession,
    settings: AppSettings,
    client_host: ClientHost,
) -> SessionResponse:
    try:
        raw_token, csrf_token, _row = login_admin_local(
            db,
            settings,
            client_host=client_host,
            server_host=_server_host(request),
        )
    except AuthForbiddenError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from None
    except AuthDisabledError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from None
    except RateLimitError as exc:
        db.commit()
        raise HTTPException(status_code=429, detail=str(exc)) from None
    _set_session_cookie(response, settings, raw_token)
    return SessionResponse(
        username=_row.username,
        csrf_token=csrf_token,
        bakery_timezone=settings.bakery_timezone,
    )


@router.post("/login", response_model=SessionResponse)
def login(
    payload: LoginRequest,
    response: Response,
    db: DbSession,
    settings: AppSettings,
    client_host: ClientHost,
) -> SessionResponse:
    try:
        raw_token, csrf_token, _row = login_admin(
            db,
            settings,
            username=payload.username,
            password=payload.password,
            client_host=client_host,
        )
    except AuthDisabledError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from None
    except RateLimitError as exc:
        db.commit()
        raise HTTPException(status_code=429, detail=str(exc)) from None
    except AuthError as exc:
        db.commit()
        raise HTTPException(status_code=401, detail=str(exc)) from None
    _set_session_cookie(response, settings, raw_token)
    return SessionResponse(
        username=settings.admin_username,
        csrf_token=csrf_token,
        bakery_timezone=settings.bakery_timezone,
    )


@router.get("/session", response_model=SessionResponse)
def current_session(
    response: Response,
    db: DbSession,
    settings: AppSettings,
    session_token: str | None = Cookie(alias=SESSION_COOKIE, default=None),
    _: Settings = Depends(require_admin_configured),
) -> SessionResponse:
    loaded = load_session(db, settings, session_token, rotate_csrf=True)
    if loaded is None:
        _clear_session_cookie(response, settings)
        raise HTTPException(status_code=401, detail="não autenticado")
    principal, _row = loaded
    return SessionResponse(
        username=principal.username,
        csrf_token=principal.csrf_token,
        bakery_timezone=settings.bakery_timezone,
    )


@router.post("/logout")
def logout(
    response: Response,
    db: DbSession,
    settings: AppSettings,
    principal: AdminUser,
    session_token: str | None = Cookie(alias=SESSION_COOKIE, default=None),
) -> dict[str, str]:
    del principal
    loaded = load_session(db, settings, session_token, rotate_csrf=False)
    if loaded is not None:
        _unused, row = loaded
        revoke_session(db, row)
    _clear_session_cookie(response, settings)
    return {"status": "ok"}


class ActivatePasswordIn(BaseModel):
    token: str = Field(min_length=16, max_length=200)
    password: str = Field(min_length=1, max_length=200)
    confirm: str = Field(min_length=1, max_length=200)


def _activation_headers(response: Response) -> None:
    response.headers["Cache-Control"] = "no-store"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["X-Robots-Tag"] = "noindex, nofollow"


@router.get("/activate/{token}")
def peek_activation(token: str, db: DbSession, settings: AppSettings, response: Response) -> dict:
    _activation_headers(response)
    return lookup_activation(db, settings, token)


@router.post("/activate")
def complete_activation(
    payload: ActivatePasswordIn, db: DbSession, settings: AppSettings, response: Response
) -> dict:
    _activation_headers(response)
    return consume_activation(
        db,
        settings,
        raw_token=payload.token,
        password=payload.password,
        confirm=payload.confirm,
    )

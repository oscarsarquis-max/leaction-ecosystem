from typing import Annotated

from fastapi import Cookie, Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.db.session import get_db
from app.domain.admin_auth import (
    CSRF_HEADER,
    SESSION_COOKIE,
    AdminPrincipal,
    load_session,
    verify_csrf,
)

DbSession = Annotated[Session, Depends(get_db)]
AppSettings = Annotated[Settings, Depends(get_settings)]


def _client_host(request: Request) -> str:
    if request.client is None:
        return "unknown"
    return request.client.host[:80]


def require_admin_configured(settings: AppSettings) -> Settings:
    if not settings.admin_enabled:
        raise HTTPException(
            status_code=503,
            detail="gestão administrativa desabilitada: execute a configuração local e reinicie a API",
        )
    return settings


def get_principal(
    request: Request,
    db: DbSession,
    settings: Annotated[Settings, Depends(require_admin_configured)],
    session_token: Annotated[str | None, Cookie(alias=SESSION_COOKIE)] = None,
    csrf_header: Annotated[str | None, Header(alias=CSRF_HEADER)] = None,
) -> AdminPrincipal:
    loaded = load_session(db, settings, session_token, rotate_csrf=False)
    if loaded is None:
        raise HTTPException(status_code=401, detail="não autenticado")
    principal, row = loaded
    if request.method.upper() not in {"GET", "HEAD", "OPTIONS"}:
        origin = request.headers.get("origin")
        if origin and origin not in settings.cors_origin_list:
            raise HTTPException(status_code=403, detail="origem não permitida")
        if not verify_csrf(settings, row, csrf_header):
            raise HTTPException(status_code=403, detail="requisição recusada")
    return principal


AdminUser = Annotated[AdminPrincipal, Depends(get_principal)]
ClientHost = Annotated[str, Depends(_client_host)]

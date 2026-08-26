"""Middleware de autorização — allowlist por role legado e por nível."""

from __future__ import annotations

from typing import Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from auth import (
    AuthUser,
    NIVEL_ADMIN,
    NIVEL_EXECUTOR,
    NIVEL_GESTOR,
    executor_has_permission,
    is_public_path,
    path_allowed_for_nivel,
    path_allowed_for_restricted,
    permission_for_executor_route,
    resolve_auth_user,
)
from database import SessionLocal
from fastapi.security import HTTPAuthorizationCredentials
from hub_client import resolve_perfil_cached


class AuthAllowlistMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path
        if request.method.upper() == "OPTIONS" or is_public_path(path):
            return await call_next(request)

        auth_header = request.headers.get("authorization") or ""
        credentials = None
        if auth_header.lower().startswith("bearer "):
            credentials = HTTPAuthorizationCredentials(
                scheme="Bearer", credentials=auth_header[7:].strip()
            )

        db = SessionLocal()
        try:
            try:
                user = resolve_auth_user(db, credentials)
            except Exception as exc:
                # HTTPException from resolve
                status = getattr(exc, "status_code", 401)
                detail = getattr(exc, "detail", "Não autenticado")
                return JSONResponse(status_code=status, content={"detail": detail})

            request.state.auth_user = user

            if user.is_restricted:
                if not path_allowed_for_restricted(request.method, path):
                    return JSONResponse(
                        status_code=403,
                        content={
                            "detail": (
                                "Acesso negado para restricted_tester. "
                                "Permitido apenas Simulação Mativas."
                            )
                        },
                    )
            elif user.is_nivel_user:
                denied = _deny_nivel_user(user, request.method, path)
                if denied is not None:
                    return denied
        finally:
            db.close()

        return await call_next(request)


def _deny_nivel_user(user: AuthUser, method: str, path: str) -> Optional[JSONResponse]:
    email = user.email or user.username
    perfil, err = resolve_perfil_cached(email)
    if perfil is None:
        return JSONResponse(
            status_code=403,
            content={
                "detail": (
                    "Não foi possível confirmar o perfil no Hub e não há "
                    "cache local para este usuário. Tente de novo em instantes."
                    + (f" ({err})" if err else "")
                )
            },
        )
    if str(perfil.get("status") or "ativo") == "inativo":
        return JSONResponse(
            status_code=403,
            content={"detail": "Perfil inativo no catálogo de identidade."},
        )
    nivel = str(perfil.get("nivel") or user.nivel or "")
    if nivel in (NIVEL_ADMIN, NIVEL_GESTOR):
        if path_allowed_for_nivel(nivel, method, path):
            return None
        return JSONResponse(
            status_code=403,
            content={"detail": "Acesso negado para este nível."},
        )
    if nivel == NIVEL_EXECUTOR:
        permissoes = perfil.get("permissoes") or []
        if executor_has_permission(permissoes, method, path):
            return None
        required = permission_for_executor_route(method, path)
        return JSONResponse(
            status_code=403,
            content={
                "detail": (
                    "Permissão insuficiente no catálogo de identidade."
                    + (f" Exige '{required}'." if required else "")
                )
            },
        )
    return JSONResponse(
        status_code=403,
        content={"detail": "Nível não autorizado no catálogo de identidade."},
    )

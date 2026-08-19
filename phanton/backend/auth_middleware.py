"""Middleware de autorização — allowlist para restricted_tester."""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from auth import (
    AuthUser,
    is_public_path,
    path_allowed_for_restricted,
    resolve_auth_user,
)
from database import SessionLocal
from fastapi.security import HTTPAuthorizationCredentials


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
        finally:
            db.close()

        return await call_next(request)

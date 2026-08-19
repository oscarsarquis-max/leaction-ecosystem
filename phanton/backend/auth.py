"""Auth aditivo — usuários, JWT e allowlist por role."""

from __future__ import annotations

import os
import re
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Optional
from uuid import UUID

import bcrypt
import jwt
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, Session, mapped_column

from database import Base, get_db

ROLE_ADMIN = "admin"
ROLE_RESTRICTED = "restricted_tester"
VALID_ROLES = frozenset({ROLE_ADMIN, ROLE_RESTRICTED})

# Sessão 12h (entre 8–24h do briefing)
JWT_TTL_HOURS = int(os.getenv("PHANTON_JWT_TTL_HOURS", "12"))
JWT_ALG = "HS256"


def _jwt_secret() -> str:
    secret = (os.getenv("PHANTON_JWT_SECRET") or "").strip()
    if secret:
        return secret
    # Dev fallback — override em produção via .env
    return "phanton-dev-jwt-secret-change-me"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )


@dataclass(frozen=True)
class AuthUser:
    id: Optional[UUID]
    username: str
    role: str

    @property
    def is_admin(self) -> bool:
        return self.role == ROLE_ADMIN

    @property
    def is_restricted(self) -> bool:
        return self.role == ROLE_RESTRICTED


# Admin local sem login — não quebra fluxo atual do dono
LOCAL_ADMIN = AuthUser(id=None, username="local-admin", role=ROLE_ADMIN)

_bearer = HTTPBearer(auto_error=False)

# Allowlist restrita: negar por padrão; só o que estiver aqui.
# Ownership de shadow é checada nas rotas (não só o path).
_RESTRICTED_ALLOW: list[tuple[str, re.Pattern[str]]] = [
    ("GET", re.compile(r"^/api/auth/me$")),
    ("POST", re.compile(r"^/api/auth/logout$")),
    ("POST", re.compile(r"^/api/crystal-ball/experimental-run$")),
    (
        "POST",
        re.compile(
            r"^/api/crystal-ball/experimental-run/"
            r"[0-9a-fA-F-]{36}/recalculate$"
        ),
    ),
    (
        "GET",
        re.compile(r"^/api/crystal-ball/shadow/[0-9a-fA-F-]{36}$"),
    ),
]

_PUBLIC_PATHS = frozenset(
    {
        "/health",
        "/api/auth/login",
    }
)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(
            password.encode("utf-8"), password_hash.encode("utf-8")
        )
    except Exception:
        return False


def create_access_token(*, user_id: UUID, username: str, role: str) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "username": username,
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=JWT_TTL_HOURS)).timestamp()),
    }
    return jwt.encode(payload, _jwt_secret(), algorithm=JWT_ALG)


def decode_access_token(token: str) -> dict[str, Any]:
    return jwt.decode(token, _jwt_secret(), algorithms=[JWT_ALG])


def path_allowed_for_restricted(method: str, path: str) -> bool:
    method_u = method.upper()
    # strip query
    path_only = path.split("?", 1)[0]
    for m, pattern in _RESTRICTED_ALLOW:
        if m == method_u and pattern.match(path_only):
            return True
    return False


def is_public_path(path: str) -> bool:
    path_only = path.split("?", 1)[0]
    return path_only in _PUBLIC_PATHS


def user_from_row(row: User) -> AuthUser:
    return AuthUser(id=row.id, username=row.username, role=row.role)


def resolve_auth_user(
    db: Session,
    credentials: Optional[HTTPAuthorizationCredentials],
) -> AuthUser:
    """Exige Bearer JWT. Sem token → 401 (não há bypass de admin local)."""
    if credentials is None or not (credentials.credentials or "").strip():
        raise HTTPException(status_code=401, detail="Autenticação necessária")
    try:
        payload = decode_access_token(credentials.credentials)
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail="Token inválido ou expirado") from exc

    role = str(payload.get("role") or "")
    username = str(payload.get("username") or "")
    sub = payload.get("sub")
    if role not in VALID_ROLES or not sub or not username:
        raise HTTPException(status_code=401, detail="Token malformado")

    try:
        user_id = UUID(str(sub))
    except ValueError as exc:
        raise HTTPException(status_code=401, detail="Token malformado") from exc

    row = db.get(User, user_id)
    if row is None or row.username != username or row.role != role:
        raise HTTPException(status_code=401, detail="Usuário do token não encontrado")

    return user_from_row(row)


def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
) -> AuthUser:
    # Preferência: usuário já resolvido pelo middleware
    cached = getattr(request.state, "auth_user", None)
    if isinstance(cached, AuthUser):
        return cached
    user = resolve_auth_user(db, credentials)
    request.state.auth_user = user
    return user


def require_admin(user: AuthUser = Depends(get_current_user)) -> AuthUser:
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Acesso restrito a admin")
    return user


def assert_shadow_owner(
    db: Session,
    shadow_run_id: UUID | str,
    user: AuthUser,
) -> None:
    """restricted_tester só acessa shadow que ela criou."""
    if user.is_admin:
        return
    from services.crystal_ball.models import CrystalShadowRun

    shadow_uuid = (
        shadow_run_id if isinstance(shadow_run_id, UUID) else UUID(str(shadow_run_id))
    )
    shadow = db.get(CrystalShadowRun, shadow_uuid)
    if shadow is None:
        raise HTTPException(status_code=404, detail="shadow run não encontrado")
    owner = getattr(shadow, "owned_by_user_id", None)
    if owner is None or user.id is None or owner != user.id:
        raise HTTPException(
            status_code=403,
            detail="Shadow não pertence a este usuário",
        )

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
from sqlalchemy import Boolean, CheckConstraint, DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, Session, mapped_column

from database import Base, get_db

ROLE_ADMIN = "admin"
ROLE_RESTRICTED = "restricted_tester"
VALID_ROLES = frozenset({ROLE_ADMIN, ROLE_RESTRICTED})
NIVEL_ADMIN = "admin"
NIVEL_GESTOR = "gestor_produtivo"
NIVEL_EXECUTOR = "usuario_executor"
VALID_NIVEIS = frozenset({NIVEL_ADMIN, NIVEL_GESTOR, NIVEL_EXECUTOR})

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
    __table_args__ = (
        CheckConstraint(
            "role IS NULL OR role IN ('admin', 'restricted_tester')",
            name="users_role_check",
        ),
        CheckConstraint(
            "nivel IS NULL OR nivel IN "
            "('admin', 'gestor_produtivo', 'usuario_executor')",
            name="chk_users_nivel",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    nome: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    email: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    nivel: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    funcao: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    sync_pendente: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )


class CodigoAcesso(Base):
    __tablename__ = "codigos_acesso"

    codigo: Mapped[str] = mapped_column(Text, primary_key=True)
    nivel: Mapped[str] = mapped_column(Text, nullable=False)
    funcao: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ativo: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    usado_por: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    criado_em: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    usado_em: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


@dataclass(frozen=True)
class AuthUser:
    id: Optional[UUID]
    username: str
    role: str
    nivel: Optional[str] = None
    funcao: Optional[str] = None
    email: Optional[str] = None
    nome: Optional[str] = None

    @property
    def is_admin(self) -> bool:
        return self.role == ROLE_ADMIN

    @property
    def is_restricted(self) -> bool:
        return self.role == ROLE_RESTRICTED

    @property
    def is_nivel_user(self) -> bool:
        return bool(self.nivel) and not self.role


# Admin local sem login — não quebra fluxo atual do dono
LOCAL_ADMIN = AuthUser(id=None, username="local-admin", role=ROLE_ADMIN)

_bearer = HTTPBearer(auto_error=False)

# Allowlist restrita (legado restricted_tester): negar por padrão.
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

# usuario_executor: rota autenticada → chave do catálogo identidade_permissoes
# (sistema=phanton). Não herda _RESTRICTED_ALLOW. Rotas mais específicas primeiro.
_UUID = r"[0-9a-fA-F-]{36}"
_EXECUTOR_ROUTE_PERMS: list[tuple[str, re.Pattern[str], str]] = [
    ("GET", re.compile(r"^/api/auth/me$"), "ver_sessao"),
    ("POST", re.compile(r"^/api/auth/logout$"), "encerrar_sessao"),
    ("POST", re.compile(r"^/api/auth/codigos-acesso$"), "gerar_codigo_acesso"),
    ("POST", re.compile(r"^/api/crystal-ball/experimental-run$"), "executar_simulacao"),
    (
        "POST",
        re.compile(rf"^/api/crystal-ball/experimental-run/{_UUID}/recalculate$"),
        "recalcular_simulacao",
    ),
    ("GET", re.compile(r"^/api/crystal-ball/corpora$"), "listar_corpora"),
    ("POST", re.compile(r"^/api/crystal-ball/corpora$"), "cadastrar_corpus"),
    (
        "POST",
        re.compile(r"^/api/crystal-ball/corpus/[^/]+/sugestao-prompt$"),
        "gerar_sugestao_prompt",
    ),
    ("GET", re.compile(r"^/api/crystal-ball/corpus/[^/]+/ciclos$"), "listar_ciclos"),
    (
        "POST",
        re.compile(r"^/api/crystal-ball/corpus/[^/]+/resultado-real$"),
        "registrar_resultado_real",
    ),
    (
        "GET",
        re.compile(rf"^/api/crystal-ball/shadow/{_UUID}/lineage$"),
        "ler_linhagem_shadow",
    ),
    ("GET", re.compile(rf"^/api/crystal-ball/shadow/{_UUID}$"), "ler_shadow_proprio"),
    ("POST", re.compile(rf"^/api/crystal-ball/shadow/{_UUID}/edit$"), "editar_shadow"),
    (
        "POST",
        re.compile(rf"^/api/crystal-ball/shadow/{_UUID}/recalculate$"),
        "recalcular_shadow",
    ),
    ("POST", re.compile(r"^/api/crystal-ball/quick-preview$"), "executar_previa"),
    (
        "GET",
        re.compile(rf"^/api/crystal-ball/{_UUID}/lineage$"),
        "ler_linhagem_oficial",
    ),
    ("POST", re.compile(rf"^/api/crystal-ball/{_UUID}/fork$"), "ramificar_run"),
    (
        "POST",
        re.compile(rf"^/api/crystal-ball/{_UUID}/recalculate$"),
        "recalcular_run_oficial",
    ),
    ("POST", re.compile(rf"^/api/crystal-ball/{_UUID}/calibrate$"), "calibrar_run"),
    ("POST", re.compile(r"^/api/pipeline/draft-requirements$"), "rascunhar_requisitos"),
    ("POST", re.compile(r"^/api/pipeline/generate-spec$"), "gerar_especificacao"),
    ("GET", re.compile(r"^/api/pipeline$"), "listar_pipeline"),
    ("POST", re.compile(r"^/api/pipeline/start$"), "iniciar_pipeline"),
    ("POST", re.compile(r"^/api/pipeline/approve/[^/]+$"), "aprovar_fase"),
    ("GET", re.compile(rf"^/api/pipeline/{_UUID}$"), "ler_pipeline"),
    (
        "PATCH",
        re.compile(rf"^/api/pipeline/{_UUID}/auto-approve$"),
        "auto_aprovar_pipeline",
    ),
    (
        "POST",
        re.compile(rf"^/api/pipeline/{_UUID}/phases/[^/]+/reopen$"),
        "reabrir_fase",
    ),
    (
        "POST",
        re.compile(rf"^/api/pipeline/{_UUID}/phases/[^/]+/modules/deliver$"),
        "entregar_modulo",
    ),
    ("POST", re.compile(rf"^/api/pipeline/{_UUID}/accept$"), "aceitar_projeto"),
    ("POST", re.compile(rf"^/api/pipeline/{_UUID}/export/linear$"), "exportar_linear"),
    ("POST", re.compile(rf"^/api/pipeline/{_UUID}/retorno$"), "enviar_retorno"),
    ("POST", re.compile(rf"^/api/pipeline/{_UUID}/evolve$"), "evoluir_projeto"),
    ("GET", re.compile(r"^/api/projects/search$"), "buscar_projetos"),
    (
        "POST",
        re.compile(rf"^/api/phanton-improvements/{_UUID}/decide$"),
        "decidir_melhoria_phanton",
    ),
    ("GET", re.compile(r"^/docs(?:/.*)?$"), "ver_documentacao_api"),
    ("GET", re.compile(r"^/redoc$"), "ver_documentacao_api"),
    ("GET", re.compile(r"^/openapi\.json$"), "ver_documentacao_api"),
]

_PUBLIC_PATHS = frozenset(
    {
        "/health",
        "/api/auth/login",
        "/api/auth/register",
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


def create_access_token(
    *,
    user_id: UUID,
    username: str,
    role: str,
    nivel: Optional[str] = None,
    email: Optional[str] = None,
) -> str:
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "username": username,
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=JWT_TTL_HOURS)).timestamp()),
    }
    if nivel:
        payload["nivel"] = nivel
    if email:
        payload["email"] = email
    return jwt.encode(payload, _jwt_secret(), algorithm=JWT_ALG)


def decode_access_token(token: str) -> dict[str, Any]:
    return jwt.decode(token, _jwt_secret(), algorithms=[JWT_ALG])


def _path_in_allow(
    allow: list[tuple[str, re.Pattern[str]]], method: str, path: str
) -> bool:
    method_u = method.upper()
    path_only = path.split("?", 1)[0]
    return any(m == method_u and pattern.match(path_only) for m, pattern in allow)


def path_allowed_for_restricted(method: str, path: str) -> bool:
    return _path_in_allow(_RESTRICTED_ALLOW, method, path)


def permission_for_executor_route(method: str, path: str) -> Optional[str]:
    """Chave de permissão exigida pela rota; None = rota sem mapeamento (nega)."""
    method_u = method.upper()
    path_only = path.split("?", 1)[0]
    for m, pattern, chave in _EXECUTOR_ROUTE_PERMS:
        if m == method_u and pattern.match(path_only):
            return chave
    return None


def executor_has_permission(
    permissoes: Any, method: str, path: str
) -> bool:
    """True se a lista do Hub contém a chave exigida pela rota."""
    required = permission_for_executor_route(method, path)
    if not required:
        return False
    granted = {
        str(item).strip()
        for item in (permissoes or [])
        if str(item or "").strip()
    }
    return required in granted


def path_allowed_for_nivel(nivel: str, method: str, path: str) -> bool:
    """admin/gestor_produtivo: acesso amplo. usuario_executor não usa isto."""
    if nivel == NIVEL_ADMIN or nivel == NIVEL_GESTOR:
        return True
    return False


def is_public_path(path: str) -> bool:
    path_only = path.split("?", 1)[0]
    return path_only in _PUBLIC_PATHS


def user_from_row(row: User) -> AuthUser:
    email = row.email or (row.username if "@" in (row.username or "") else None)
    return AuthUser(
        id=row.id,
        username=row.username,
        role=row.role or "",
        nivel=row.nivel,
        funcao=row.funcao,
        email=email,
        nome=row.nome,
    )


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

    try:
        user_id = UUID(str(sub))
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=401, detail="Token malformado") from exc

    # Legado admin / restricted_tester — mesmo contrato de sempre
    if role in VALID_ROLES:
        if not sub or not username:
            raise HTTPException(status_code=401, detail="Token malformado")
        row = db.get(User, user_id)
        if row is None or row.username != username or row.role != role:
            raise HTTPException(
                status_code=401, detail="Usuário do token não encontrado"
            )
        return user_from_row(row)

    if not sub or not username:
        raise HTTPException(status_code=401, detail="Token malformado")

    row = db.get(User, user_id)
    if row is None or row.username != username:
        raise HTTPException(status_code=401, detail="Usuário do token não encontrado")
    if row.role in VALID_ROLES:
        raise HTTPException(status_code=401, detail="Token malformado")
    if (row.nivel or "") not in VALID_NIVEIS:
        raise HTTPException(status_code=401, detail="Token malformado")
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
    """restricted_tester / usuario_executor só acessam shadow que criaram."""
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

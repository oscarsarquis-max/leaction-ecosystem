"""Rotas de autenticação — prefixo /api/auth."""

from __future__ import annotations

import logging
import secrets
import uuid
from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from auth import (
    JWT_TTL_HOURS,
    VALID_NIVEIS,
    VALID_ROLES,
    AuthUser,
    CodigoAcesso,
    User,
    create_access_token,
    get_current_user,
    hash_password,
    require_admin,
    verify_password,
)
from database import get_db
from hub_client import sync_usuario_hub

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=2, max_length=64)
    password: str = Field(..., min_length=4, max_length=256)


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in_hours: int
    user: dict[str, Any]


class MeResponse(BaseModel):
    id: Optional[str]
    username: str
    role: str
    is_local_admin: bool = False
    nivel: Optional[str] = None
    funcao: Optional[str] = None
    email: Optional[str] = None


class RegisterRequest(BaseModel):
    codigo: str = Field(..., min_length=4, max_length=64)
    nome: str = Field(..., min_length=2, max_length=120)
    email: str = Field(..., min_length=5, max_length=64)
    senha: str = Field(..., min_length=4, max_length=256)


class RegisterResponse(BaseModel):
    ok: bool = True
    email: str
    nivel: str
    funcao: Optional[str] = None


class CodigoAcessoRequest(BaseModel):
    nivel: str = Field(..., min_length=3, max_length=40)
    funcao: Optional[str] = Field(default=None, max_length=80)


class CodigoAcessoResponse(BaseModel):
    codigo: str
    nivel: str
    funcao: Optional[str] = None


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> LoginResponse:
    username = payload.username.strip()
    row = (
        db.query(User)
        .filter((User.username == username) | (User.email == username.lower()))
        .one_or_none()
    )
    if row is None or not verify_password(payload.password, row.password_hash):
        raise HTTPException(status_code=401, detail="Usuário ou senha inválidos")

    if row.role in VALID_ROLES:
        token = create_access_token(
            user_id=row.id, username=row.username, role=row.role
        )
        user_payload: dict[str, Any] = {
            "id": str(row.id),
            "username": row.username,
            "role": row.role,
        }
    elif (row.nivel or "") in VALID_NIVEIS:
        token = create_access_token(
            user_id=row.id,
            username=row.username,
            role="",
            nivel=row.nivel,
            email=row.email,
        )
        user_payload = {
            "id": str(row.id),
            "username": row.username,
            "role": row.role,
            "nivel": row.nivel,
            "funcao": row.funcao,
            "email": row.email,
        }
    else:
        raise HTTPException(status_code=403, detail="Role inválida")

    return LoginResponse(
        access_token=token,
        expires_in_hours=JWT_TTL_HOURS,
        user=user_payload,
    )


@router.get("/me", response_model=MeResponse)
def me(user: AuthUser = Depends(get_current_user)) -> MeResponse:
    return MeResponse(
        id=str(user.id) if user.id else None,
        username=user.username,
        role=user.role,
        is_local_admin=False,
        nivel=user.nivel,
        funcao=user.funcao,
        email=user.email,
    )


@router.post("/register", response_model=RegisterResponse)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> RegisterResponse:
    codigo = payload.codigo.strip()
    nome = payload.nome.strip()
    email = payload.email.strip().lower()
    if "@" not in email or "." not in email.split("@")[-1]:
        raise HTTPException(status_code=400, detail="Informe um e-mail válido")

    row_codigo = db.query(CodigoAcesso).filter(CodigoAcesso.codigo == codigo).one_or_none()
    if row_codigo is None or not row_codigo.ativo or row_codigo.usado_por:
        raise HTTPException(
            status_code=400,
            detail="Código de acesso inválido, já usado ou inativo",
        )
    if row_codigo.nivel not in VALID_NIVEIS:
        raise HTTPException(status_code=400, detail="Código de acesso com nível inválido")

    existing = (
        db.query(User)
        .filter((User.username == email) | (User.email == email))
        .one_or_none()
    )
    if existing is not None:
        raise HTTPException(status_code=400, detail="Já existe uma conta com este e-mail")

    user = User(
        id=uuid.uuid4(),
        username=email,
        password_hash=hash_password(payload.senha),
        role=None,
        nome=nome,
        email=email,
        nivel=row_codigo.nivel,
        funcao=row_codigo.funcao,
        sync_pendente=False,
    )
    row_codigo.ativo = False
    row_codigo.usado_por = email
    row_codigo.usado_em = datetime.utcnow()
    db.add(user)
    db.flush()

    ok, err = sync_usuario_hub(
        email=email,
        nome=nome,
        nivel=row_codigo.nivel,
        funcao=row_codigo.funcao,
    )
    if not ok:
        user.sync_pendente = True
        logger.warning("cadastro local ok; sync Hub pendente (%s): %s", email, err)

    db.commit()
    db.refresh(user)
    return RegisterResponse(email=email, nivel=user.nivel or "", funcao=user.funcao)


@router.post("/codigos-acesso", response_model=CodigoAcessoResponse)
def criar_codigo_acesso(
    payload: CodigoAcessoRequest,
    db: Session = Depends(get_db),
    _admin: AuthUser = Depends(require_admin),
) -> CodigoAcessoResponse:
    nivel = payload.nivel.strip()
    if nivel not in VALID_NIVEIS:
        raise HTTPException(
            status_code=400,
            detail="nivel inválido (use: admin, gestor_produtivo, usuario_executor)",
        )
    funcao = (payload.funcao or "").strip() or None
    codigo = secrets.token_urlsafe(9)
    row = CodigoAcesso(codigo=codigo, nivel=nivel, funcao=funcao, ativo=True)
    db.add(row)
    db.commit()
    return CodigoAcessoResponse(codigo=codigo, nivel=nivel, funcao=funcao)


@router.post("/logout")
def logout() -> dict[str, bool]:
    """Cliente descarta o token; servidor é stateless (JWT)."""
    return {"ok": True}


def create_user(
    db: Session,
    *,
    username: str,
    password: str,
    role: str,
) -> User:
    """Helper para script CLI / testes — não exposto na API pública."""
    role_n = (role or "").strip()
    if role_n not in VALID_ROLES:
        raise ValueError(f"role inválida: {role!r} (use {sorted(VALID_ROLES)})")
    uname = (username or "").strip()
    if len(uname) < 2:
        raise ValueError("username muito curto")
    if len(password or "") < 4:
        raise ValueError("password muito curto")
    existing = db.query(User).filter(User.username == uname).one_or_none()
    if existing is not None:
        raise ValueError(f"username já existe: {uname}")
    row = User(
        id=uuid.uuid4(),
        username=uname,
        password_hash=hash_password(password),
        role=role_n,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row

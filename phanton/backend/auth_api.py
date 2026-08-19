"""Rotas de autenticação — prefixo /api/auth."""

from __future__ import annotations

import uuid
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from auth import (
    JWT_TTL_HOURS,
    ROLE_ADMIN,
    VALID_ROLES,
    AuthUser,
    User,
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)
from database import get_db

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


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> LoginResponse:
    username = payload.username.strip()
    row = db.query(User).filter(User.username == username).one_or_none()
    if row is None or not verify_password(payload.password, row.password_hash):
        raise HTTPException(status_code=401, detail="Usuário ou senha inválidos")
    if row.role not in VALID_ROLES:
        raise HTTPException(status_code=403, detail="Role inválida")

    token = create_access_token(
        user_id=row.id, username=row.username, role=row.role
    )
    return LoginResponse(
        access_token=token,
        expires_in_hours=JWT_TTL_HOURS,
        user={"id": str(row.id), "username": row.username, "role": row.role},
    )


@router.get("/me", response_model=MeResponse)
def me(user: AuthUser = Depends(get_current_user)) -> MeResponse:
    return MeResponse(
        id=str(user.id) if user.id else None,
        username=user.username,
        role=user.role,
        is_local_admin=False,
    )


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

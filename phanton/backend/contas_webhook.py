"""Receptor S2S do Cofre (vault-api) — criar / rotacionar contas privilegiadas.

Canal separado da Gestão de Identidade: PHANTON_VAULT_CONTA_SECRET,
não PHANTON_HUB_APP_SECRET. Login e auto-cadastro permanecem iguais.
"""

from __future__ import annotations

import logging
import os
import secrets as pysecrets
import uuid
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from auth import VALID_NIVEIS, User, hash_password
from database import get_db
from hub_client import sync_usuario_hub

_BACKEND_ENV = Path(__file__).resolve().parent / ".env"
load_dotenv(_BACKEND_ENV, override=False)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])

_VAULT_SECRET_ENV = "PHANTON_VAULT_CONTA_SECRET"


class ContaWebhookRequest(BaseModel):
    acao: str = Field(..., min_length=3, max_length=40)
    email: str = Field(..., min_length=5, max_length=64)
    senha: Optional[str] = Field(default=None, max_length=256)
    novo_valor: Optional[str] = Field(default=None, max_length=256)
    nivel: Optional[str] = Field(default=None, max_length=40)
    funcao: Optional[str] = Field(default=None, max_length=80)


class ContaWebhookResponse(BaseModel):
    ok: bool = True
    email: str


def _vault_conta_secret() -> str:
    return (os.getenv(_VAULT_SECRET_ENV) or "").strip()


def _header_matches(got: str, expected: str) -> bool:
    if not got or not expected or len(got) != len(expected):
        return False
    return pysecrets.compare_digest(got, expected)


def require_vault_conta_s2s(
    request: Request,
    authorization: Optional[str] = Header(default=None),
    x_app_secret: Optional[str] = Header(default=None, alias="X-App-Secret"),
) -> None:
    expected = _vault_conta_secret()
    if not expected:
        raise HTTPException(
            status_code=401, detail="Canal S2S de contas não configurado"
        )

    bearer = ""
    header = (authorization or request.headers.get("authorization") or "").strip()
    if header.lower().startswith("bearer "):
        bearer = header[7:].strip()
    x_secret = (x_app_secret or request.headers.get("x-app-secret") or "").strip()

    if _header_matches(bearer, expected) or _header_matches(x_secret, expected):
        return
    raise HTTPException(status_code=401, detail="Autenticação S2S inválida")


def _normalize_email(raw: str) -> str:
    email = (raw or "").strip().lower()
    if "@" not in email or "." not in email.split("@")[-1]:
        raise HTTPException(status_code=400, detail="Informe um e-mail válido")
    return email


def _find_user_by_email(db: Session, email: str) -> Optional[User]:
    return (
        db.query(User)
        .filter((User.username == email) | (User.email == email))
        .one_or_none()
    )


def _criar_conta(payload: ContaWebhookRequest, db: Session) -> ContaWebhookResponse:
    email = _normalize_email(payload.email)
    senha = (payload.senha or "").strip()
    if len(senha) < 4:
        raise HTTPException(status_code=400, detail="Informe a senha da conta")

    nivel = (payload.nivel or "").strip()
    if nivel not in VALID_NIVEIS:
        raise HTTPException(status_code=400, detail="Nível inválido")

    funcao = (payload.funcao or "").strip() or None
    nome = email.split("@", 1)[0] or email

    if _find_user_by_email(db, email) is not None:
        raise HTTPException(status_code=409, detail="Já existe uma conta com este e-mail")

    user = User(
        id=uuid.uuid4(),
        username=email,
        password_hash=hash_password(senha),
        role=None,
        nome=nome,
        email=email,
        nivel=nivel,
        funcao=funcao,
        sync_pendente=False,
    )
    db.add(user)
    db.flush()

    ok, err = sync_usuario_hub(
        email=email,
        nome=nome,
        nivel=nivel,
        funcao=funcao,
    )
    if not ok:
        user.sync_pendente = True
        logger.warning("conta vault ok; sync Hub pendente (%s): %s", email, err)

    db.commit()
    db.refresh(user)
    return ContaWebhookResponse(email=email)


def _rotacionar_senha(
    payload: ContaWebhookRequest, db: Session
) -> ContaWebhookResponse:
    email = _normalize_email(payload.email)
    novo = (payload.novo_valor or "").strip()
    if len(novo) < 4:
        raise HTTPException(status_code=400, detail="Informe o novo valor da senha")

    user = _find_user_by_email(db, email)
    if user is None:
        raise HTTPException(status_code=404, detail="Conta não encontrada")

    user.password_hash = hash_password(novo)
    db.commit()
    return ContaWebhookResponse(email=email)


@router.post("/contas", response_model=ContaWebhookResponse)
def webhook_contas(
    payload: ContaWebhookRequest,
    db: Session = Depends(get_db),
    _: None = Depends(require_vault_conta_s2s),
) -> ContaWebhookResponse:
    acao = (payload.acao or "").strip().lower()
    if acao == "criar":
        return _criar_conta(payload, db)
    if acao == "rotacionar_senha":
        return _rotacionar_senha(payload, db)
    raise HTTPException(status_code=400, detail="Ação inválida")

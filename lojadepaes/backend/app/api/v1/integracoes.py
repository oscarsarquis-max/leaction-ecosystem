"""Rotas de serviço LePain (BLOG-025). Autenticadas por X-Service-Key."""
from __future__ import annotations

import hmac
import logging

from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel, Field

from app.api.deps import AppSettings, DbSession
from app.domain.errors import ConfirmationError, NotFoundError
from app.domain.integracoes_lepain import (
    assert_rate_limit,
    cliente_status,
    credit_stamp,
    list_vitrine,
)

router = APIRouter(prefix="/integracoes", tags=["integracoes"])
logger = logging.getLogger("integracoes.lepain")


def _client_host(request: Request) -> str:
    if request.client is None:
        return "unknown"
    return request.client.host[:80]


def _require_service_key(
    settings: AppSettings,
    x_service_key: str | None,
) -> None:
    expected = str(getattr(settings, "integracoes_service_key", "") or "").strip()
    got = str(x_service_key or "").strip()
    if not expected:
        raise HTTPException(status_code=503, detail="integração desabilitada")
    if not got or not hmac.compare_digest(expected, got):
        raise HTTPException(status_code=401, detail="chave de serviço inválida")


class CreditoBody(BaseModel):
    telefone: str = Field(min_length=8, max_length=40)
    referencia: str = Field(min_length=3, max_length=80)


@router.get("/fidelidade/cliente")
def get_cliente(
    request: Request,
    db: DbSession,
    settings: AppSettings,
    telefone: str = "",
    x_service_key: str | None = Header(default=None, alias="X-Service-Key"),
):
    _require_service_key(settings, x_service_key)
    try:
        assert_rate_limit(_client_host(request))
        return cliente_status(db, settings, telefone)
    except ConfirmationError as err:
        raise HTTPException(status_code=429 if "muitas" in str(err).lower() else 400, detail=str(err)) from err


@router.post("/fidelidade/credito")
def post_credito(
    request: Request,
    body: CreditoBody,
    db: DbSession,
    settings: AppSettings,
    x_service_key: str | None = Header(default=None, alias="X-Service-Key"),
):
    _require_service_key(settings, x_service_key)
    try:
        assert_rate_limit(_client_host(request))
        result = credit_stamp(
            db, settings, telefone=body.telefone, referencia=body.referencia
        )
        db.commit()
        return result
    except NotFoundError as err:
        db.rollback()
        raise HTTPException(status_code=404, detail=str(err)) from err
    except ConfirmationError as err:
        db.rollback()
        text = str(err)
        code = 429 if "muitas" in text.lower() else 400
        raise HTTPException(status_code=code, detail=text) from err


@router.get("/vitrine")
def get_vitrine(
    request: Request,
    db: DbSession,
    settings: AppSettings,
    x_service_key: str | None = Header(default=None, alias="X-Service-Key"),
):
    _require_service_key(settings, x_service_key)
    try:
        assert_rate_limit(_client_host(request))
    except ConfirmationError as err:
        raise HTTPException(status_code=429, detail=str(err)) from err
    return list_vitrine(db)

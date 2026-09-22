"""Rastro da Loja para o Action-Sponge.

A emissão nunca altera pedido, reserva ou cobrança. Se o Hub falhar, só há log.
"""

from __future__ import annotations

import json
import logging
import os
import re
import threading
from uuid import uuid4

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models.orders import Order, OrderItem

logger = logging.getLogger("lojadepaes.tracking")

SISTEMA_ORIGEM = "lojadepaes"
PROD_URL = "https://actionhub.com.br/hub-api/api/crm/tracking/receber"
LOCAL_URL = "http://127.0.0.1:4001/api/crm/tracking/receber"
DADOS_MAX_BYTES = 4096
UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
    re.IGNORECASE,
)
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
ALLOWED_DADOS = {
    "pagina",
    "data_fornada",
    "produto_id",
    "quantidade",
    "data_solicitada",
    "pedido_id",
    "situacao",
    "sessao_origem_ausente",
}
SITUACOES = {"submitted", "confirmed", "paid"}


def hub_tracking_url(settings: Settings) -> str:
    explicit = settings.crm_tracking_url.strip()
    if explicit:
        return explicit
    if settings.env.strip().lower() in {"production", "prod"}:
        return PROD_URL
    return LOCAL_URL


def crm_secret(settings: Settings) -> str:
    own = settings.crm_tracking_secret.strip()
    if own:
        return own
    return os.environ.get("CRM_TRACKING_SECRET", "").strip()


def optional_session_id(value: object) -> str | None:
    raw = str(value or "").strip()
    if UUID_RE.fullmatch(raw):
        return raw.lower()
    return None


def _parece_pessoal(value: str) -> bool:
    if "@" in value:
        return True
    digits = re.sub(r"\D", "", value)
    return len(digits) == 11 and len(value) <= 14


def sanitize_id_usuario(value: object) -> str | None:
    raw = str(value or "").strip()
    if not raw or len(raw) > 64 or _parece_pessoal(raw):
        if raw and _parece_pessoal(raw):
            logger.warning("[tracking] id_usuario pessoal recusado")
        return None
    return raw


def _clean_dados_value(key: str, value: object) -> object | None:
    if key in {"data_fornada", "data_solicitada"}:
        text = str(value or "").strip()
        return text if DATE_RE.fullmatch(text) else None
    if key == "pagina":
        text = str(value or "").strip()
        if not text.startswith("/") or "?" in text or "@" in text or len(text) > 80:
            return None
        return text
    if key in {"produto_id", "pedido_id"}:
        text = str(value or "").strip()
        if not text or len(text) > 64 or _parece_pessoal(text) or " " in text:
            return None
        return text
    if key == "quantidade":
        try:
            number = int(value)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return None
        if number < 0 or number > 10000:
            return None
        return number
    if key == "situacao":
        text = str(value or "").strip()
        return text if text in SITUACOES else None
    if key == "sessao_origem_ausente":
        return True if value is True else None
    return None


def sanitize_dados(value: object) -> dict | None:
    if not isinstance(value, dict):
        return None
    cleaned: dict = {}
    for key in ALLOWED_DADOS:
        if key not in value:
            continue
        item = _clean_dados_value(key, value[key])
        if item is not None:
            cleaned[key] = item
    if not cleaned:
        return None
    encoded = json.dumps(cleaned, ensure_ascii=False).encode("utf-8")
    if len(encoded) > DADOS_MAX_BYTES:
        logger.warning("[tracking] dados acima de 4KB — não encaminhado")
        return None
    return cleaned


def build_hub_body(
    *,
    id_sessao: str,
    tipo_evento: str,
    url_pagina: str | None = None,
    id_usuario: object = None,
    dados: object = None,
    ip_real: str | None = None,
    user_agent: str | None = None,
) -> dict | None:
    session_id = optional_session_id(id_sessao)
    if session_id is None:
        return None
    body: dict = {
        "sistema_origem": SISTEMA_ORIGEM,
        "id_sessao": session_id,
        "tipo_evento": str(tipo_evento or "pageview").strip().lower()[:128] or "pageview",
        "url_pagina": (url_pagina or "/")[:2048],
    }
    usuario = sanitize_id_usuario(id_usuario)
    if usuario:
        body["id_usuario"] = usuario
    safe_dados = sanitize_dados(dados)
    if safe_dados is not None:
        body["dados"] = safe_dados
    if ip_real:
        body["ip_real"] = ip_real[:80]
    if user_agent:
        body["user_agent"] = user_agent[:4000]
    return body


def _post(settings: Settings, body: dict) -> None:
    secret = crm_secret(settings)
    if not secret:
        logger.warning("[tracking] CRM_TRACKING_SECRET ausente — evento não enviado")
        return
    headers = {"Content-Type": "application/json", "x-crm-secret": secret}
    try:
        response = httpx.post(hub_tracking_url(settings), json=body, headers=headers, timeout=4.0)
        if response.status_code >= 400:
            logger.warning(
                "[tracking] Hub respondeu %s para %s",
                response.status_code,
                body.get("tipo_evento"),
            )
    except httpx.HTTPError as exc:
        logger.warning("[tracking] Hub indisponível (%s): %s", body.get("tipo_evento"), exc)


def emit_tracking(settings: Settings, body: dict | None) -> None:
    if body is None:
        return
    if os.environ.get("LOJADEPAES_CRM_TRACKING_SYNC") == "1":
        try:
            _post(settings, body)
        except Exception as exc:
            logger.warning("[tracking] falha local: %s", exc)
        return
    threading.Thread(target=_post, args=(settings, body), daemon=True).start()


def order_quantity(session: Session, order: Order) -> int:
    items = session.scalars(select(OrderItem).where(OrderItem.order_id == order.id)).all()
    total = 0
    for item in items:
        units = item.physical_units if item.physical_units else item.quantity
        total += int(units or 0)
    return total


def emit_order_fact(
    session: Session,
    settings: Settings,
    order: Order,
    tipo_evento: str,
    *,
    situacao: str,
) -> None:
    try:
        session_id = optional_session_id(order.crm_id_sessao)
        missing = session_id is None
        if missing:
            session_id = str(uuid4())
        dados: dict = {"pedido_id": str(order.id), "situacao": situacao}
        if tipo_evento != "pagamento_registrar" and order.production_local_date is not None:
            dados["data_fornada"] = order.production_local_date.isoformat()
            dados["quantidade"] = order_quantity(session, order)
        if missing:
            dados["sessao_origem_ausente"] = True
        emit_tracking(
            settings,
            build_hub_body(
                id_sessao=session_id,
                tipo_evento=tipo_evento,
                id_usuario=str(order.id),
                dados=dados,
                url_pagina="/pedido",
            ),
        )
    except Exception as exc:
        logger.warning("[tracking] emissão de %s não enviada: %s", tipo_evento, exc)


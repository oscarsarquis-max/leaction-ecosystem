"""
Proxy PLG Tracking — inove4us (sensor) → Action Hub (Action-Sponge).

Não persiste no banco do inove4us. Enriquece IP/UA, id_clie e
instituicao_b2b_id (quando houver) e encaminha S2S.
Falhas no Hub NÃO travam a UX (sempre 202/ok local).
"""

from __future__ import annotations

import logging
import os

import requests
from flask import Blueprint, jsonify, request, session
from psycopg2.extras import RealDictCursor

logger = logging.getLogger(__name__)

tracking_bp = Blueprint("crm_tracking_proxy", __name__)

DEFAULT_HUB_TRACKING_URL = "http://127.0.0.1:4001/api/crm/tracking/receber"
SISTEMA_ORIGEM = "inove4us"


def _client_ip() -> str:
    forwarded = (request.headers.get("X-Forwarded-For") or "").strip()
    if forwarded:
        return forwarded.split(",")[0].strip()
    real_ip = (request.headers.get("X-Real-IP") or "").strip()
    if real_ip:
        return real_ip
    return (request.remote_addr or "").strip() or "unknown"


def _hub_receber_url() -> str:
    explicit = (os.environ.get("ACTION_HUB_CRM_TRACKING_URL") or "").strip()
    if explicit:
        return explicit
    base = (
        os.environ.get("ACTION_HUB_API_URL")
        or os.environ.get("HUB_API_URL")
        or "http://127.0.0.1:4001"
    ).strip()
    return f"{base.rstrip('/')}/api/crm/tracking/receber"


def _id_clie_para_hub(payload: dict):
    raw = payload.get("id_usuario")
    if raw is not None and raw != "":
        try:
            return int(raw)
        except (TypeError, ValueError):
            pass
    user = session.get("user") or {}
    if isinstance(user, dict) and user.get("id_clie") is not None:
        try:
            return int(user["id_clie"])
        except (TypeError, ValueError):
            return None
    return None


def _normalize_instituicao(value) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if text in ("", "None", "null"):
        return None
    return text


def _instituicao_id_para_hub(id_clie) -> str | None:
    user = session.get("user") or {}
    if isinstance(user, dict) and user:
        # Sessão já carrega instituicao_b2b_id (None = professor solo).
        if "instituicao_b2b_id" in user:
            return _normalize_instituicao(user.get("instituicao_b2b_id"))
    if id_clie is None:
        return None
    try:
        from db import get_conn

        with get_conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT instituicao_b2b_id
                      FROM public.ctdi_clie
                     WHERE id_clie = %s
                     LIMIT 1
                    """,
                    (int(id_clie),),
                )
                row = cur.fetchone()
        if not row:
            return None
        return _normalize_instituicao(row.get("instituicao_b2b_id"))
    except Exception as exc:
        logger.warning("[tracking/enviar] leitura instituicao_b2b_id: %s", exc)
        return None


@tracking_bp.route("/api/tracking/enviar", methods=["POST", "OPTIONS"])
def tracking_enviar():
    if request.method == "OPTIONS":
        return ("", 204)

    payload = request.get_json(silent=True) or {}
    id_sessao = str(payload.get("id_sessao") or payload.get("session_id") or "").strip()
    tipo_evento = str(payload.get("tipo_evento") or "pageview").strip()
    url_pagina = str(payload.get("url_pagina") or payload.get("url") or "").strip()

    if not id_sessao:
        return jsonify({"ok": False, "error": "id_sessao obrigatório"}), 400
    if not tipo_evento:
        return jsonify({"ok": False, "error": "tipo_evento obrigatório"}), 400

    id_usuario = _id_clie_para_hub(payload)
    instituicao_id = _instituicao_id_para_hub(id_usuario)

    tempo = payload.get("tempo_gasto_segundos", 0)
    try:
        tempo_gasto = max(0, int(tempo))
    except (TypeError, ValueError):
        tempo_gasto = 0

    dados = payload.get("dados") if isinstance(payload.get("dados"), dict) else None

    hub_body = {
        "sistema_origem": SISTEMA_ORIGEM,
        "id_sessao": id_sessao,
        "id_usuario": id_usuario,
        "tipo_evento": tipo_evento,
        "url_pagina": url_pagina or request.headers.get("Referer") or "/",
        "ip_real": _client_ip(),
        "user_agent": request.headers.get("User-Agent") or "",
        "tempo_gasto_segundos": tempo_gasto,
    }
    if instituicao_id:
        hub_body["instituicao_id"] = instituicao_id
    if dados is not None:
        hub_body["dados"] = dados

    secret = (os.environ.get("CRM_TRACKING_SECRET") or "").strip()
    headers = {"Content-Type": "application/json"}
    if secret:
        headers["x-crm-secret"] = secret

    try:
        resp = requests.post(
            _hub_receber_url(),
            json=hub_body,
            headers=headers,
            timeout=(2.5, 4.0),
        )
        if resp.status_code >= 400:
            logger.warning(
                "[tracking/enviar] Hub respondeu %s: %s",
                resp.status_code,
                (resp.text or "")[:240],
            )
            return jsonify(
                {
                    "ok": True,
                    "forwarded": False,
                    "hub_status": resp.status_code,
                }
            ), 202

        data = {}
        try:
            data = resp.json() if resp.content else {}
        except ValueError:
            data = {}
        return jsonify({"ok": True, "forwarded": True, "hub": data}), 200
    except requests.RequestException as exc:
        logger.warning("[tracking/enviar] Hub indisponível: %s", exc)
        return jsonify(
            {
                "ok": True,
                "forwarded": False,
                "error": "actionhub_unavailable",
            }
        ), 202

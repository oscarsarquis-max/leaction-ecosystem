"""
Proxy CRM Tracking — inove4us-school (sensor) → Action Hub (Action-Sponge).

Não persiste no banco do School. Enriquece IP/UA, id do gestor e instituicao_id
da sessão, e encaminha S2S.
Falhas no Hub NÃO travam a UX (sempre 202/ok local).
"""

from __future__ import annotations

import logging
import os

import requests
from flask import Blueprint, jsonify, request, session

logger = logging.getLogger(__name__)

tracking_bp = Blueprint("crm_tracking_proxy", __name__)

SISTEMA_ORIGEM = "inove4us-school"
SESSION_KEY = "school_gestor"


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


def _session_gestor() -> dict:
    raw = session.get(SESSION_KEY) or {}
    return raw if isinstance(raw, dict) else {}


def _id_usuario_para_hub(payload: dict) -> str | None:
    raw = payload.get("id_usuario")
    if raw is not None and str(raw).strip() != "":
        return str(raw).strip()
    gid = _session_gestor().get("id")
    if gid is not None and str(gid).strip() != "":
        return str(gid).strip()
    return None


def _clean_nome(value) -> str | None:
    text = str(value or "").strip()
    if not text or "@" in text:
        return None
    digits = "".join(ch for ch in text if ch.isdigit())
    if len(digits) == 11 and len(text) <= 14:
        return None
    return text[:160]


def _usuario_nome_para_hub(payload: dict) -> str | None:
    from_payload = _clean_nome(payload.get("usuario_nome"))
    if from_payload:
        return from_payload
    return _clean_nome(_session_gestor().get("nome"))


def _instituicao_nome_para_hub(payload: dict) -> str | None:
    from_payload = _clean_nome(payload.get("instituicao_nome"))
    if from_payload:
        return from_payload
    g = _session_gestor()
    return _clean_nome(g.get("instituicao_nome") or g.get("razao_social"))


def _instituicao_da_sessao() -> str | None:
    inst = _session_gestor().get("instituicao_id")
    if inst is None or str(inst).strip() == "":
        return None
    return str(inst).strip()


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

    id_usuario = _id_usuario_para_hub(payload)
    instituicao_id = _instituicao_da_sessao()

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
    usuario_nome = _usuario_nome_para_hub(payload) if id_usuario else None
    instituicao_nome = _instituicao_nome_para_hub(payload) if instituicao_id else None
    if usuario_nome:
        hub_body["usuario_nome"] = usuario_nome
    if instituicao_nome:
        hub_body["instituicao_nome"] = instituicao_nome
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

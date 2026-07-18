"""Webhook Server-to-Server do Action Hub (outbox JWT)."""

from __future__ import annotations

import os
import sys

import jwt
from flask import Blueprint, jsonify, request

from db import adicionar_creditos_ia, find_cliente_by_email

webhook_bp = Blueprint("actionhub_webhooks", __name__)


def _webhook_secret() -> str:
    return (
        os.environ.get("ACTIONHUB_WEBHOOK_SECRET")
        or os.environ.get("ACTION_HUB_APP_SECRET")
        or ""
    ).strip()


def _extract_bearer_token() -> str:
    auth = (request.headers.get("Authorization") or "").strip()
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()
    # Hub também envia X-Hub-Signature com o mesmo JWT
    sig = (request.headers.get("X-Hub-Signature") or "").strip()
    if sig:
        return sig
    body = request.get_json(silent=True) or {}
    token = body.get("token")
    return str(token).strip() if token else ""


def _decode_hub_jwt(token: str) -> dict:
    secret = _webhook_secret()
    if not secret:
        raise RuntimeError("ACTIONHUB_WEBHOOK_SECRET não configurado")
    return jwt.decode(token, secret, algorithms=["HS256"])


def _event_payload(decoded: dict, body: dict) -> tuple[str, dict]:
    event_type = str(
        decoded.get("event_type") or body.get("event_type") or ""
    ).strip()
    inner = decoded.get("payload")
    if inner is None:
        inner = decoded.get("payload_json")
    if inner is None:
        inner = body.get("payload")
    if inner is None:
        inner = body.get("payload_json")
    if not isinstance(inner, dict):
        inner = {}
    return event_type, inner


def _credits_delta(payload: dict) -> int:
    """Créditos a adicionar — campo credits ou quantity do pack."""
    for key in ("credits", "credits_granted", "quantidade", "quantity"):
        if key in payload and payload[key] is not None:
            try:
                n = int(payload[key])
                return max(0, n)
            except (TypeError, ValueError):
                continue
    items = payload.get("items")
    if isinstance(items, list):
        total = 0
        for item in items:
            if not isinstance(item, dict):
                continue
            if str(item.get("item_type") or "") == "credit_pack":
                try:
                    total += max(0, int(item.get("quantity") or 0))
                except (TypeError, ValueError):
                    pass
        if total > 0:
            return total
    return 0


def _handle_credits_granted(payload: dict) -> dict:
    subject_id = str(payload.get("subject_id") or "").strip().lower()
    delta = _credits_delta(payload)
    if not subject_id:
        print(
            "[actionhub-webhook] CREDITS_GRANTED sem subject_id - ignorado",
            file=sys.stderr,
        )
        return {"handled": False, "reason": "missing_subject"}

    cliente = find_cliente_by_email(subject_id)
    if not cliente:
        print(
            f"[actionhub-webhook] CREDITS_GRANTED: cliente nao encontrado "
            f"mail={subject_id} credits={delta} - ack sem aplicar",
            file=sys.stderr,
        )
        return {"handled": False, "reason": "user_not_found", "subject_id": subject_id}

    if delta <= 0:
        print(
            f"[actionhub-webhook] CREDITS_GRANTED: delta=0 mail={subject_id}",
            file=sys.stderr,
        )
        return {
            "handled": True,
            "subject_id": subject_id,
            "credits_added": 0,
            "creditos_ia": int(cliente.get("creditos_ia") or 0),
        }

    novo = adicionar_creditos_ia(int(cliente["id_clie"]), delta)
    print(
        f"[actionhub-webhook] CREDITS_GRANTED mail={subject_id} "
        f"+{delta} -> saldo={novo}"
    )
    return {
        "handled": True,
        "subject_id": subject_id,
        "credits_added": delta,
        "creditos_ia": novo,
    }


def _handle_contract_activated(payload: dict) -> dict:
    subject_id = str(payload.get("subject_id") or "").strip().lower()
    print(
        f"[actionhub-webhook] CONTRACT_ACTIVATED recebido "
        f"subject_id={subject_id or '-'} contract_id={payload.get('contract_id')}"
    )
    # Premium / entitlements persistidos — fase futura
    return {"handled": True, "logged": True, "subject_id": subject_id or None}


@webhook_bp.post("/api/webhooks/actionhub")
def actionhub_webhook():
    """Recebe eventos do outbox Action Hub. Sem login de sessão."""
    token = _extract_bearer_token()
    if not token:
        return jsonify({"error": "Token ausente"}), 401

    try:
        decoded = _decode_hub_jwt(token)
    except RuntimeError as exc:
        print(f"[actionhub-webhook] config: {exc}", file=sys.stderr)
        return jsonify({"error": "Webhook secret não configurado"}), 503
    except jwt.ExpiredSignatureError:
        return jsonify({"error": "Token expirado"}), 401
    except jwt.InvalidTokenError as exc:
        print(f"[actionhub-webhook] JWT inválido: {exc}", file=sys.stderr)
        return jsonify({"error": "Token inválido"}), 401

    body = request.get_json(silent=True) or {}
    event_type, payload = _event_payload(decoded, body)

    result: dict
    if event_type == "CREDITS_GRANTED":
        result = _handle_credits_granted(payload)
    elif event_type == "CONTRACT_ACTIVATED":
        result = _handle_contract_activated(payload)
    else:
        print(
            f"[actionhub-webhook] event_type desconhecido: {event_type or '(vazio)'}",
            file=sys.stderr,
        )
        result = {"handled": False, "reason": "unknown_event", "event_type": event_type}

    # Sempre 200 em eventos de negócio — evita reprocessamento eterno no outbox
    return jsonify({"status": "received", "event_type": event_type, "result": result}), 200

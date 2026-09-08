"""Webhook Server-to-Server do Action Hub (outbox JWT)."""

from __future__ import annotations

import os
import sys

import jwt
from flask import Blueprint, jsonify, request

from db import (
    adicionar_creditos_ia,
    find_cliente_by_email,
    get_conn,
    set_plan_tier,
    upsert_hub_notice,
)

webhook_bp = Blueprint("actionhub_webhooks", __name__)

_processed_ensured = False


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


def ensure_hub_webhook_processed_table() -> None:
    global _processed_ensured
    if _processed_ensured:
        return
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS public.inove_hub_webhook_processed (
                    idempotency_key TEXT PRIMARY KEY,
                    event_type      VARCHAR(64) NOT NULL,
                    processed_at   TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
    _processed_ensured = True


def resolve_hub_idempotency_key(
    *,
    decoded: dict | None = None,
    body: dict | None = None,
    payload: dict | None = None,
    headers: dict | None = None,
) -> str:
    """Chave de idempotência do outbox Hub (mesmo critério do worker)."""
    decoded = decoded or {}
    body = body or {}
    payload = payload or {}
    headers = headers or {}
    header_key = ""
    for name, value in (headers or {}).items():
        if str(name).lower() == "x-hub-idempotency-key":
            header_key = str(value or "").strip()
            break
    for candidate in (
        header_key,
        body.get("idempotency_key"),
        decoded.get("idempotency_key"),
        payload.get("idempotency_key"),
    ):
        key = str(candidate or "").strip()
        if key:
            return key[:256]
    order_id = str(payload.get("order_id") or "").strip()
    if order_id:
        return f"order_{order_id}_activation"[:256]
    return ""


def _claim_hub_idempotency(key: str, event_type: str) -> bool:
    """True se esta entrega é a primeira (pode creditar). False = já processada."""
    ensure_hub_webhook_processed_table()
    token = str(key or "").strip()
    if not token:
        return True
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO public.inove_hub_webhook_processed
                    (idempotency_key, event_type)
                VALUES (%s, %s)
                ON CONFLICT (idempotency_key) DO NOTHING
                RETURNING idempotency_key
                """,
                (token, str(event_type or "")[:64]),
            )
            return cur.fetchone() is not None


def _release_hub_idempotency(key: str) -> None:
    token = str(key or "").strip()
    if not token:
        return
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                DELETE FROM public.inove_hub_webhook_processed
                 WHERE idempotency_key = %s
                """,
                (token,),
            )


def _credits_delta(payload: dict) -> int:
    """
    Créditos a CREDITAR nesta entrega (delta), nunca o saldo acumulado do Hub.

    Ordem:
      1) credits_added / credits_granted
      2) soma de items[].quantity (credit_pack)
      3) credits — só se não houver items (legado / inject manual)
    """
    for key in ("credits_added", "credits_granted"):
        if key in payload and payload[key] is not None:
            try:
                return max(0, int(payload[key]))
            except (TypeError, ValueError):
                continue

    items = payload.get("items")
    if isinstance(items, list) and items:
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

    for key in ("creditos", "credits", "quantidade", "quantity"):
        if key in payload and payload[key] is not None:
            try:
                return max(0, int(payload[key]))
            except (TypeError, ValueError):
                continue
    return 0


def _resolve_tier_from_payload(payload: dict) -> str | None:
    """Mapeia SKU / direitos.nivel (ou legado entitlements.tier) → plan_tier local."""
    direitos = payload.get("direitos") or payload.get("entitlements") or {}
    if not isinstance(direitos, dict):
        direitos = {}
    tier = str(
        payload.get("nivel")
        or payload.get("tier")
        or direitos.get("nivel")
        or direitos.get("tier")
        or ""
    ).strip().lower()
    if tier in ("profissional", "mentor", "starter"):
        return tier

    sku = str(payload.get("sku") or "").strip().upper()
    if not sku and isinstance(payload.get("items"), list):
        for item in payload["items"]:
            if isinstance(item, dict) and item.get("sku"):
                sku = str(item["sku"]).strip().upper()
                break
    if sku.startswith("INOVE4US_PRO"):
        return "profissional"
    if sku.startswith("INOVE4US_MENTOR") or sku.startswith("GOLIVE"):
        return "mentor"
    return None


def _handle_credits_granted(payload: dict, *, idempotency_key: str = "") -> dict:
    subject_id = str(payload.get("subject_id") or "").strip().lower()
    delta = _credits_delta(payload)
    if not subject_id:
        print(
            "[actionhub-webhook] CREDITS_GRANTED sem subject_id - ignorado",
            file=sys.stderr,
        )
        return {"handled": False, "reason": "missing_subject"}

    key = str(idempotency_key or "").strip()
    claimed = _claim_hub_idempotency(key, "CREDITS_GRANTED") if key else True
    if key and not claimed:
        cliente = find_cliente_by_email(subject_id)
        saldo = int((cliente or {}).get("creditos_ia") or 0)
        print(
            f"[actionhub-webhook] CREDITS_GRANTED idempotente key={key} mail={subject_id}",
            flush=True,
        )
        return {
            "handled": True,
            "idempotent": True,
            "subject_id": subject_id,
            "credits_added": 0,
            "creditos_ia": saldo,
        }

    try:
        cliente = find_cliente_by_email(subject_id)
        if not cliente:
            if key:
                _release_hub_idempotency(key)
            print(
                f"[actionhub-webhook] CREDITS_GRANTED: cliente nao encontrado "
                f"mail={subject_id} credits={delta} - ack sem aplicar",
                file=sys.stderr,
            )
            return {"handled": False, "reason": "user_not_found", "subject_id": subject_id}

        id_clie = int(cliente["id_clie"])
        tier = _resolve_tier_from_payload(payload)
        plan_tier = None
        if tier in ("profissional", "mentor"):
            plan_tier = set_plan_tier(id_clie, tier)

        if delta <= 0:
            print(
                f"[actionhub-webhook] CREDITS_GRANTED: delta=0 mail={subject_id} tier={plan_tier}",
                file=sys.stderr,
            )
            return {
                "handled": True,
                "subject_id": subject_id,
                "credits_added": 0,
                "creditos_ia": int(cliente.get("creditos_ia") or 0),
                "plan_tier": plan_tier,
                "idempotent": False,
            }

        novo = adicionar_creditos_ia(id_clie, delta)
        print(
            f"[actionhub-webhook] CREDITS_GRANTED mail={subject_id} "
            f"+{delta} -> saldo={novo} tier={plan_tier}"
        )
        return {
            "handled": True,
            "subject_id": subject_id,
            "credits_added": delta,
            "creditos_ia": novo,
            "plan_tier": plan_tier,
            "idempotent": False,
        }
    except Exception:
        if key:
            _release_hub_idempotency(key)
        raise


def _handle_contract_activated(payload: dict) -> dict:
    subject_id = str(payload.get("subject_id") or "").strip().lower()
    print(
        f"[actionhub-webhook] CONTRACT_ACTIVATED recebido "
        f"subject_id={subject_id or '-'} contract_id={payload.get('contract_id')}"
    )
    plan_tier = None
    if subject_id:
        cliente = find_cliente_by_email(subject_id)
        tier = _resolve_tier_from_payload(payload)
        if cliente and tier in ("profissional", "mentor"):
            plan_tier = set_plan_tier(int(cliente["id_clie"]), tier)
    return {
        "handled": True,
        "logged": True,
        "subject_id": subject_id or None,
        "plan_tier": plan_tier,
    }


def _handle_payment_notice(payload: dict) -> dict:
    subject_id = str(payload.get("subject_id") or "").strip().lower()
    message = str(payload.get("message") or "").strip()
    order_id = payload.get("order_id")
    status_label = payload.get("status_label")
    if not subject_id or not message:
        return {"handled": False, "reason": "missing_fields"}
    notice = upsert_hub_notice(
        mail_clie=subject_id,
        message=message,
        order_id=str(order_id) if order_id else None,
        status_label=str(status_label) if status_label else None,
    )
    print(
        f"[actionhub-webhook] PAYMENT_NOTICE mail={subject_id} "
        f"order={order_id or '-'} id={notice.get('id')}"
    )
    return {"handled": True, "notice_id": notice.get("id"), "subject_id": subject_id}


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
    headers = {k: v for k, v in request.headers.items()}
    idem_key = resolve_hub_idempotency_key(
        decoded=decoded,
        body=body,
        payload=payload,
        headers=headers,
    )

    result: dict
    if event_type == "CREDITS_GRANTED":
        result = _handle_credits_granted(payload, idempotency_key=idem_key)
    elif event_type == "CONTRACT_ACTIVATED":
        result = _handle_contract_activated(payload)
    elif event_type == "PAYMENT_NOTICE":
        result = _handle_payment_notice(payload)
    else:
        print(
            f"[actionhub-webhook] event_type desconhecido: {event_type or '(vazio)'}",
            file=sys.stderr,
        )
        result = {"handled": False, "reason": "unknown_event", "event_type": event_type}

    # Sempre 200 em eventos de negócio — evita reprocessamento eterno no outbox
    return jsonify({"status": "received", "event_type": event_type, "result": result}), 200

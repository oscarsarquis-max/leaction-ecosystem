"""Webhook S2S Action Hub → inove4us-school (padrão Outbox JWT).

POST /api/webhooks/actionhub — sem sessão de gestor / RBAC.
Sempre HTTP 200 após JWT válido (ACK outbox).
"""
from __future__ import annotations

import sys
import uuid
from typing import Any

from flask import Blueprint, g, jsonify, request
from psycopg2.extras import RealDictCursor

from db import get_conn
from hub_jwt import require_hub_jwt

bp = Blueprint("actionhub_webhooks", __name__)


def _event_payload(decoded: dict, body: dict) -> tuple[str, dict]:
    event_type = str(
        decoded.get("event_type")
        or body.get("event_type")
        or request.headers.get("X-Hub-Event-Type")
        or ""
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


def _log(msg: str) -> None:
    print(f"[actionhub-webhook] {msg}", flush=True)


def _as_uuid(value: Any) -> str | None:
    if value is None or value == "":
        return None
    try:
        return str(uuid.UUID(str(value)))
    except (ValueError, TypeError, AttributeError):
        return None


def _licenses_qty(payload: dict) -> int:
    for key in (
        "licenses_granted",
        "licenses",
        "licencas",
        "seats",
        "quantity",
        "quantidade",
    ):
        if key in payload and payload[key] is not None:
            try:
                n = int(payload[key])
                if n > 0:
                    return n
            except (TypeError, ValueError):
                pass

    direitos = payload.get("direitos") or payload.get("entitlements") or {}
    if isinstance(direitos, dict):
        for key in ("licenses_granted", "licenses", "licencas", "seats"):
            if key in direitos and direitos[key] is not None:
                try:
                    n = int(direitos[key])
                    if n > 0:
                        return n
                except (TypeError, ValueError):
                    pass

    items = payload.get("items")
    if isinstance(items, list):
        total = 0
        for item in items:
            if not isinstance(item, dict):
                continue
            itype = str(item.get("item_type") or "").lower()
            if itype in ("seat", "addon", "plan"):
                try:
                    total += max(0, int(item.get("quantity") or 0))
                except (TypeError, ValueError):
                    pass
        if total > 0:
            return total
    return 0


def _resolve_instituicao_id(payload: dict) -> str | None:
    for key in ("instituicao_id", "institution_id", "school_id"):
        found = _as_uuid(payload.get(key))
        if found:
            return found
    subject_type = str(payload.get("subject_type") or "").strip().lower()
    subject = payload.get("subject_id")
    if subject_type in ("instituicao", "institution", "school"):
        return _as_uuid(subject)
    # subject_id pode ser o UUID da instituição (checkout B2B)
    return _as_uuid(subject)


def _count_professores_ativos(cur: Any, instituicao_id: str) -> int:
    cur.execute(
        """
        SELECT count(*)::int AS n
        FROM public.school_professores_vinculo
        WHERE instituicao_id = %s AND status_vinculo = 'ativo'
        """,
        (instituicao_id,),
    )
    row = cur.fetchone()
    return int(row["n"] or 0) if row else 0


def _apply_licenses_granted(payload: dict, *, event_label: str) -> dict:
    instituicao_id = _resolve_instituicao_id(payload)
    qty = _licenses_qty(payload)
    sku = str(payload.get("sku") or "").strip() or None
    contract_id = str(payload.get("contract_id") or "").strip() or None

    if not instituicao_id:
        _log(f"{event_label} sem instituicao_id/subject_id UUID — ignorado")
        return {
            "handled": False,
            "reason": "instituicao_id_missing",
            "event": event_label,
        }
    if qty <= 0:
        _log(f"{event_label} instituicao={instituicao_id} qty=0 — ack sem aplicar")
        return {
            "handled": False,
            "reason": "licenses_qty_zero",
            "instituicao_id": instituicao_id,
            "event": event_label,
        }

    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT 1 FROM public.school_instituicoes WHERE id = %s",
                (instituicao_id,),
            )
            if not cur.fetchone():
                _log(f"{event_label} instituição inexistente: {instituicao_id}")
                return {
                    "handled": False,
                    "reason": "instituicao_not_found",
                    "instituicao_id": instituicao_id,
                    "event": event_label,
                }

            em_uso = _count_professores_ativos(cur, instituicao_id)

            cur.execute(
                """
                INSERT INTO public.school_licencas (
                    instituicao_id,
                    total_assentos,
                    assentos_em_uso,
                    sku_ultimo,
                    contrato_hub_id
                )
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (instituicao_id) DO UPDATE SET
                    total_assentos = public.school_licencas.total_assentos + EXCLUDED.total_assentos,
                    assentos_em_uso = EXCLUDED.assentos_em_uso,
                    sku_ultimo = COALESCE(EXCLUDED.sku_ultimo, public.school_licencas.sku_ultimo),
                    contrato_hub_id = COALESCE(
                        EXCLUDED.contrato_hub_id, public.school_licencas.contrato_hub_id
                    ),
                    updated_at = CURRENT_TIMESTAMP
                RETURNING id, total_assentos, assentos_em_uso
                """,
                (instituicao_id, qty, em_uso, sku, contract_id),
            )
            lic = cur.fetchone()

            # Espelho legado na instituição (Equipe / convites)
            cur.execute(
                """
                UPDATE public.school_instituicoes
                SET licencas_contratadas = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
                """,
                (int(lic["total_assentos"]), instituicao_id),
            )

    _log(
        f"{event_label} instituicao={instituicao_id} +{qty} "
        f"total={lic['total_assentos']} em_uso={lic['assentos_em_uso']} sku={sku}"
    )
    return {
        "handled": True,
        "event": event_label,
        "instituicao_id": instituicao_id,
        "licenses_granted": qty,
        "total_assentos": int(lic["total_assentos"]),
        "assentos_em_uso": int(lic["assentos_em_uso"]),
        "sku": sku,
        "contract_id": contract_id,
    }


def _handle_subscription_canceled(payload: dict) -> dict:
    instituicao_id = _resolve_instituicao_id(payload)
    _log(
        f"SUBSCRIPTION_CANCELED instituicao={instituicao_id} "
        f"contract_id={payload.get('contract_id')} "
        f"(sem revogação automática de assentos — curadoria manual)"
    )
    return {
        "handled": True,
        "event": "SUBSCRIPTION_CANCELED",
        "instituicao_id": instituicao_id,
        "note": "assentos preservados; ajuste manual se necessário",
    }


def _handle_credits_granted(payload: dict) -> dict:
    _log(
        f"CREDITS_GRANTED (N/A School B2B) subject={payload.get('subject_id')} "
        f"payload_keys={list(payload.keys())}"
    )
    return {"handled": False, "reason": "school_uses_licenses_not_credits", "event": "CREDITS_GRANTED"}


def _handle_payment_notice(payload: dict) -> dict:
    _log(
        f"PAYMENT_NOTICE subject={payload.get('subject_id')} "
        f"message={str(payload.get('message') or '')[:80]}"
    )
    return {"handled": True, "simulated": False, "event": "PAYMENT_NOTICE"}


@bp.post("/api/webhooks/actionhub")
@require_hub_jwt
def actionhub_webhook():
    """Receptor Outbox. Gatekeeper S2S — sem login de gestor."""
    body = request.get_json(silent=True) or {}
    decoded = getattr(g, "hub_jwt", {}) or {}
    event_type, payload = _event_payload(decoded, body)

    try:
        if event_type == "LICENSES_GRANTED":
            result = _apply_licenses_granted(payload, event_label="LICENSES_GRANTED")
        elif event_type == "CONTRACT_ACTIVATED":
            # Planos seat também podem chegar como CONTRACT_ACTIVATED (legado Hub).
            if _licenses_qty(payload) > 0:
                result = _apply_licenses_granted(payload, event_label="CONTRACT_ACTIVATED")
            else:
                _log(
                    f"CONTRACT_ACTIVATED sem licenses — "
                    f"subject={payload.get('subject_id')} contract={payload.get('contract_id')}"
                )
                result = {
                    "handled": True,
                    "event": "CONTRACT_ACTIVATED",
                    "note": "sem licenses_granted no payload",
                }
        elif event_type == "SUBSCRIPTION_CANCELED":
            result = _handle_subscription_canceled(payload)
        elif event_type == "CREDITS_GRANTED":
            result = _handle_credits_granted(payload)
        elif event_type == "PAYMENT_NOTICE":
            result = _handle_payment_notice(payload)
        else:
            _log(f"event_type desconhecido: {event_type or '(vazio)'}")
            print(
                f"[actionhub-webhook] payload preview: {str(payload)[:300]}",
                file=sys.stderr,
                flush=True,
            )
            result = {
                "handled": False,
                "reason": "unknown_event",
                "event_type": event_type,
            }
    except Exception as exc:
        _log(f"erro processando {event_type}: {exc}")
        print(f"[actionhub-webhook] {exc}", file=sys.stderr, flush=True)
        result = {"handled": False, "error": str(exc), "event_type": event_type}

    return (
        jsonify(
            {
                "status": "received",
                "app": "inove4us-school",
                "event_type": event_type,
                "result": result,
            }
        ),
        200,
    )

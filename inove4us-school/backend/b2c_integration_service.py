"""Dispatch S2S School → inove4us B2C (JWT HS256).

Assina com iss='inove4us-school' e POST no webhook do B2C.
"""
from __future__ import annotations

import os
import sys
from typing import Any

import requests

from school_b2c_jwt import ISSUER_SCHOOL, sign_bridge_jwt


def b2c_webhook_url() -> str:
    return (
        os.getenv("INOVE4US_B2C_WEBHOOK_URL")
        or os.getenv("INOVE4US_B2C_API_URL", "http://127.0.0.1:5010").rstrip("/")
        + "/api/webhooks/school"
    ).strip()


def dispatch_event_to_b2c(event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Assina e envia evento ao B2C. Não levanta se o B2C estiver offline (log + retorno)."""
    event = str(event_type or "").strip()
    body_payload = payload if isinstance(payload, dict) else {}
    if not event:
        return {"ok": False, "error": "event_type vazio"}

    try:
        token = sign_bridge_jwt(
            issuer=ISSUER_SCHOOL,
            event_type=event,
            payload=body_payload,
        )
    except RuntimeError as exc:
        print(f"[school→b2c] config: {exc}", file=sys.stderr, flush=True)
        return {"ok": False, "error": str(exc)}

    url = b2c_webhook_url()
    body = {
        "event_type": event,
        "app_id": ISSUER_SCHOOL,
        "payload": body_payload,
        "token": token,
    }
    headers = {
        "Authorization": f"Bearer {token}",
        "X-School-B2C-Signature": token,
        "Content-Type": "application/json",
        "X-School-Event-Type": event,
    }
    try:
        res = requests.post(url, json=body, headers=headers, timeout=5.0)
        ok = 200 <= res.status_code < 300
        print(
            f"[school→b2c] {event} → {url} http={res.status_code}",
            flush=True,
        )
        return {
            "ok": ok,
            "status_code": res.status_code,
            "event_type": event,
            "response": (res.text or "")[:300],
        }
    except requests.RequestException as exc:
        print(f"[school→b2c] falha de rede {event}: {exc}", file=sys.stderr, flush=True)
        return {"ok": False, "error": str(exc), "event_type": event}


def dispatch_methodology_override_updated(
    *,
    instituicao_id: str,
    metodologia_nome: str,
    diretriz_customizada: str | None,
) -> dict[str, Any]:
    return dispatch_event_to_b2c(
        "METHODOLOGY_OVERRIDE_UPDATED",
        {
            "instituicao_id": str(instituicao_id),
            "metodologia_nome": str(metodologia_nome or "").strip(),
            "diretriz_customizada": diretriz_customizada,
        },
    )


def dispatch_teacher_allocated(payload: dict[str, Any]) -> dict[str, Any]:
    """Atalho tipado para o despertar do professor no B2C."""
    return dispatch_event_to_b2c("TEACHER_ALLOCATED", payload or {})

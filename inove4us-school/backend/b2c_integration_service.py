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
    explicit = (os.getenv("INOVE4US_B2C_WEBHOOK_URL") or "").strip()
    if explicit:
        return explicit
    base = (os.getenv("INOVE4US_B2C_API_URL") or "http://127.0.0.1:5011").rstrip("/")
    return f"{base}/api/webhooks/school"


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
        print(f"[school->b2c] config: {exc}", file=sys.stderr, flush=True)
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
            f"[school->b2c] {event} -> {url} http={res.status_code}",
            flush=True,
        )
        return {
            "ok": ok,
            "status_code": res.status_code,
            "event_type": event,
            "response": (res.text or "")[:300],
        }
    except requests.RequestException as exc:
        print(f"[school->b2c] falha de rede {event}: {exc}", file=sys.stderr, flush=True)
        return {"ok": False, "error": str(exc), "event_type": event}


def dispatch_methodology_override_updated(
    *,
    instituicao_id: str,
    metodologia_nome: str,
    diretriz_customizada: str | None,
    metodologia_codigo: str | None = None,
    disponivel_dia_a_dia: bool = True,
    disponivel_desafio: bool = True,
    is_active: bool = True,
    atualizado_em: str | None = None,
    versao: int | None = None,
    origem_config_school_id: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "instituicao_id": str(instituicao_id),
        "metodologia_nome": str(metodologia_nome or "").strip(),
        "diretriz_customizada": diretriz_customizada,
        "disponivel_dia_a_dia": bool(disponivel_dia_a_dia),
        "disponivel_desafio": bool(disponivel_desafio),
        "is_active": bool(is_active),
    }
    codigo = str(metodologia_codigo or "").strip()
    if codigo:
        payload["metodologia_codigo"] = codigo
        payload["metodologia_key"] = codigo
    if atualizado_em:
        payload["atualizado_em"] = str(atualizado_em)
    if versao is not None:
        try:
            payload["versao"] = int(versao)
        except (TypeError, ValueError):
            pass
    if origem_config_school_id:
        payload["origem_config_school_id"] = str(origem_config_school_id)
    return dispatch_event_to_b2c("METHODOLOGY_OVERRIDE_UPDATED", payload)


def dispatch_teacher_allocated(payload: dict[str, Any]) -> dict[str, Any]:
    """Atalho tipado para o despertar do professor no B2C."""
    return dispatch_event_to_b2c("TEACHER_ALLOCATED", payload or {})


def dispatch_pei_override_updated(payload: dict[str, Any] | None = None, **kwargs: Any) -> dict[str, Any]:
    """School → B2C: PEI_OVERRIDE_UPDATED (níveis aee_base | individual).

    Aceita dict completo ou kwargs legados. Campos None são omitidos.
    """
    body: dict[str, Any] = {}
    if isinstance(payload, dict):
        body.update(payload)
    body.update(kwargs)
    clean = {k: v for k, v in body.items() if v is not None}
    if "instituicao_id" in clean:
        clean["instituicao_id"] = str(clean["instituicao_id"])
    return dispatch_event_to_b2c("PEI_OVERRIDE_UPDATED", clean)


def b2c_api_base() -> str:
    return (
        os.getenv("INOVE4US_B2C_API_URL")
        or "http://127.0.0.1:5011"
    ).rstrip("/")


def school_integration_api_key() -> str:
    return (
        os.getenv("SCHOOL_INTEGRATION_API_KEY")
        or os.getenv("INOVE4US_SCHOOL_API_KEY")
        or ""
    ).strip()


def push_comunicado_to_b2c(payload: dict[str, Any]) -> dict[str, Any]:
    """POST /api/integracoes/school/comunicados (API key) → mural + agenda no B2C."""
    return _post_school_integration(
        "/api/integracoes/school/comunicados",
        payload,
        label="COMUNICADO",
    )


def push_planejamento_to_b2c(payload: dict[str, Any]) -> dict[str, Any]:
    """POST /api/integracoes/school/planejamento (API key) → esqueleto aula/evento no B2C."""
    return _post_school_integration(
        "/api/integracoes/school/planejamento",
        payload,
        label="PLANEJAMENTO",
        timeout=12.0,
    )


def _post_school_integration(
    path: str,
    payload: dict[str, Any],
    *,
    label: str,
    timeout: float = 6.0,
) -> dict[str, Any]:
    key = school_integration_api_key()
    if not key:
        return {"ok": False, "error": "SCHOOL_INTEGRATION_API_KEY não configurada"}

    url = f"{b2c_api_base()}{path}"
    headers = {
        "Content-Type": "application/json",
        "X-School-Api-Key": key,
    }
    body = payload if isinstance(payload, dict) else {}
    try:
        res = requests.post(url, json=body, headers=headers, timeout=timeout)
        ok = 200 <= res.status_code < 300
        print(
            f"[school->b2c] {label} -> {url} http={res.status_code}",
            flush=True,
        )
        parsed: Any = None
        try:
            parsed = res.json()
        except Exception:
            parsed = (res.text or "")[:300]
        return {
            "ok": ok,
            "status_code": res.status_code,
            "response": parsed,
        }
    except requests.RequestException as exc:
        print(
            f"[school->b2c] falha de rede {label}: {exc}",
            file=sys.stderr,
            flush=True,
        )
        return {"ok": False, "error": str(exc)}

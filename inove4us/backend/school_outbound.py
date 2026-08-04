"""Outbound S2S inove4us B2C → inove4us-school (JWT HS256).

Assina com iss='inove4us' e POST no webhook do School.
"""
from __future__ import annotations

import os
import sys
import time
from typing import Any

import jwt
import requests
from psycopg2.extras import RealDictCursor

from db import get_conn

ISSUER_B2C = "inove4us"


def _shared_secret() -> str:
    return (os.environ.get("SCHOOL_B2C_SHARED_SECRET") or "").strip()


def school_webhook_url() -> str:
    return (
        os.getenv("INOVE4US_SCHOOL_WEBHOOK_URL")
        or os.getenv("SCHOOL_WEBHOOK_URL")
        or (
            (os.getenv("INOVE4US_SCHOOL_API_URL") or "http://127.0.0.1:5012").rstrip("/")
            + "/api/webhooks/b2c"
        )
    ).strip()


def sign_bridge_jwt(
    *,
    event_type: str,
    payload: dict[str, Any],
    expires_sec: int = 3600,
) -> str:
    secret = _shared_secret()
    if not secret:
        raise RuntimeError("SCHOOL_B2C_SHARED_SECRET não configurado")
    now = int(time.time())
    return jwt.encode(
        {
            "iss": ISSUER_B2C,
            "event_type": event_type,
            "payload": payload or {},
            "iat": now,
            "exp": now + max(60, int(expires_sec)),
        },
        secret,
        algorithm="HS256",
    )


def dispatch_event_to_school(event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
    event = str(event_type or "").strip()
    body_payload = payload if isinstance(payload, dict) else {}
    if not event:
        return {"ok": False, "error": "event_type vazio"}
    try:
        token = sign_bridge_jwt(event_type=event, payload=body_payload)
    except RuntimeError as exc:
        print(f"[b2c→school] config: {exc}", file=sys.stderr, flush=True)
        return {"ok": False, "error": str(exc)}

    url = school_webhook_url()
    body = {
        "event_type": event,
        "app_id": ISSUER_B2C,
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
        print(f"[b2c→school] {event} → {url} http={res.status_code}", flush=True)
        return {
            "ok": ok,
            "status_code": res.status_code,
            "event_type": event,
            "response": (res.text or "")[:300],
        }
    except requests.RequestException as exc:
        print(f"[b2c→school] falha de rede {event}: {exc}", file=sys.stderr, flush=True)
        return {"ok": False, "error": str(exc), "event_type": event}


def _cliente_bridge_context(id_clie: int) -> dict[str, Any]:
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id_clie, mail_clie, instituicao_b2b_id, institutional_name
                FROM public.ctdi_clie
                WHERE id_clie = %s
                LIMIT 1
                """,
                (int(id_clie),),
            )
            row = cur.fetchone()
    return dict(row) if row else {}


def _metodologia_nome_from_evento(evento: dict[str, Any]) -> str:
    meta = evento.get("meta_json") if isinstance(evento.get("meta_json"), dict) else {}
    plan = evento.get("plan_data") if isinstance(evento.get("plan_data"), dict) else {}
    for src in (meta, plan, evento):
        for key in (
            "metodologia_nome",
            "metodologia",
            "metodologia_usada",
            "nome_metodologia",
        ):
            val = str(src.get(key) or "").strip()
            if val:
                return val
    tipo = str(evento.get("tipo") or "").strip()
    if "eduscrum" in tipo.lower():
        return "EduScrum"
    if "pbl" in tipo.lower():
        return "PBL"
    return tipo or "Metodologia"


def dispatch_lesson_record_sync(
    *,
    id_clie: int,
    evento: dict[str, Any],
    has_teacher_adaptations: bool,
    teacher_adaptation_text: str | None = None,
    metodologia_usada: str | None = None,
    has_pei_adaptations: bool = False,
    pei_adaptation_text: str | None = None,
    pei_aluno_id: str | None = None,
    aluno_nome: str | None = None,
) -> dict[str, Any]:
    """Empurra LESSON_RECORD_SYNC ao School (curadoria bottom-up se houver adaptação)."""
    cliente = _cliente_bridge_context(id_clie)
    instituicao_id = cliente.get("instituicao_b2b_id")
    if not instituicao_id:
        return {"ok": False, "skipped": True, "reason": "sem_instituicao_b2b"}

    met_nome = (metodologia_usada or "").strip() or _metodologia_nome_from_evento(evento)
    adapt_text = (teacher_adaptation_text or "").strip() or None
    has_adapt = bool(has_teacher_adaptations) and bool(adapt_text)
    pei_text = (pei_adaptation_text or "").strip() or None
    has_pei = bool(has_pei_adaptations) and bool(pei_text)

    origem = None
    raw_origem = evento.get("desafio_id") or evento.get("id_evento")
    if raw_origem is not None:
        origem = str(raw_origem)

    mesa = {
        "id": str(evento.get("id_evento") or ""),
        "titulo": evento.get("titulo") or "",
        "tipo_aula": "desafio",
        "status": evento.get("status") or "concluido",
        "metodologia_nome": met_nome,
        "semana_referencia": str(evento.get("data_evento") or "")[:10] or None,
        "has_teacher_adaptations": has_adapt,
        "teacher_adaptation_text": adapt_text,
        "adaptations": {"texto": adapt_text} if adapt_text else None,
        "has_pei_adaptations": has_pei,
        "pei_adaptation_text": pei_text,
        "pei_aluno_id": pei_aluno_id,
        "aluno_nome": aluno_nome,
        "relato_sala": evento.get("relato_sala"),
        "participantes": evento.get("participantes"),
    }

    payload = {
        "instituicao_id": str(instituicao_id),
        "origem_plano_b2c_id": origem,
        "professor_email": cliente.get("mail_clie"),
        "email": cliente.get("mail_clie"),
        "professor_b2c_id": str(id_clie),
        "metodologia_nome": met_nome,
        "metodologia_usada": met_nome,
        "semana_referencia": mesa["semana_referencia"],
        "tipo_aula": "desafio",
        "status": "aprovado",
        "conteudo_resumo": evento.get("titulo") or met_nome,
        "has_teacher_adaptations": has_adapt,
        "teacher_adaptation_text": adapt_text,
        "adaptations": {"texto": adapt_text} if adapt_text else None,
        "has_pei_adaptations": has_pei,
        "pei_adaptation_text": pei_text,
        "pei_aluno_id": pei_aluno_id,
        "aluno_nome": aluno_nome,
        "mesa": mesa,
    }
    return dispatch_event_to_school("LESSON_RECORD_SYNC", payload)

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
        print(f"[b2c->school] config: {exc}", file=sys.stderr, flush=True)
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
        # ASCII only: console Windows (cp1252) quebra com setas Unicode no print.
        print(f"[b2c->school] {event} -> {url} http={res.status_code}", flush=True)
        return {
            "ok": ok,
            "status_code": res.status_code,
            "event_type": event,
            "response": (res.text or "")[:300],
        }
    except requests.RequestException as exc:
        print(f"[b2c->school] falha de rede {event}: {exc}", file=sys.stderr, flush=True)
        return {"ok": False, "error": str(exc), "event_type": event}


def _cliente_bridge_context(id_clie: int) -> dict[str, Any]:
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id_clie, nome_clie, mail_clie, instituicao_b2b_id, institutional_name
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


def _aula_contexto_from_evento(
    evento: dict[str, Any],
    *,
    metodologia: str,
    aula_contexto: str | None = None,
) -> str:
    explicit = (aula_contexto or "").strip()
    if explicit:
        return explicit
    meta = evento.get("meta_json") if isinstance(evento.get("meta_json"), dict) else {}
    disc = str(
        meta.get("disciplina_nome")
        or evento.get("disciplina_nome")
        or ""
    ).strip()
    titulo = str(evento.get("titulo") or "").strip()
    parts = [p for p in (metodologia, disc, titulo) if p]
    return " · ".join(parts) or metodologia or "Aula"


def _tarefas_from_kanban(kanban_state: Any) -> list[dict[str, Any]]:
    if isinstance(kanban_state, list):
        return [t for t in kanban_state if isinstance(t, dict)]
    if isinstance(kanban_state, dict):
        tarefas = kanban_state.get("tarefas")
        if isinstance(tarefas, list):
            return [t for t in tarefas if isinstance(t, dict)]
    return []


def _cards_snapshot_from_evento(evento: dict[str, Any]) -> list[dict[str, Any]]:
    """Snapshot enxuto dos cards (com historico) para o espelho School."""
    ks = evento.get("kanban_state")
    if isinstance(ks, str) and ks.strip():
        try:
            import json

            ks = json.loads(ks)
        except Exception:
            ks = None
    cards_out: list[dict[str, Any]] = []
    for t in _tarefas_from_kanban(ks):
        cards_out.append(
            {
                "id": t.get("id"),
                "titulo": t.get("titulo") or t.get("titulo_do_card"),
                "coluna": t.get("coluna") or "para_fazer",
                "cor": t.get("cor"),
                "duracao_minutos": t.get("duracao_minutos"),
                "objetivo": t.get("objetivo"),
                "como_executar_detalhado": t.get("como_executar_detalhado")
                or t.get("mecanica_passo_a_passo")
                or t.get("descricao"),
                "dica_de_facilitacao": t.get("dica_de_facilitacao"),
                "ultima_observacao": t.get("ultima_observacao"),
                "historico": t.get("historico") if isinstance(t.get("historico"), list) else [],
                "perfil_inclusao": t.get("perfil_inclusao"),
                "parent_card_id": t.get("parent_card_id"),
                "pei_concluido": t.get("pei_concluido"),
                "aula_id": t.get("aula_id"),
            }
        )
    return cards_out


def dispatch_lesson_record_sync(
    *,
    id_clie: int,
    evento: dict[str, Any],
    has_teacher_adaptations: bool,
    teacher_adaptation_text: str | None = None,
    metodologia_usada: str | None = None,
    aula_contexto: str | None = None,
    professor_nome: str | None = None,
    has_pei_adaptations: bool = False,
    pei_adaptation_text: str | None = None,
    pei_aluno_id: str | None = None,
    aluno_nome: str | None = None,
    school_status: str | None = None,
) -> dict[str, Any]:
    """Empurra LESSON_RECORD_SYNC ao School (curadoria bottom-up se houver adaptação)."""
    cliente = _cliente_bridge_context(id_clie)
    instituicao_id = cliente.get("instituicao_b2b_id")
    if not instituicao_id:
        return {"ok": False, "skipped": True, "reason": "sem_instituicao_b2b"}

    met_nome = (metodologia_usada or "").strip() or _metodologia_nome_from_evento(evento)
    adapt_text = (teacher_adaptation_text or "").strip() or None
    # Curadoria só com texto concreto no fechamento (flag sozinha não basta).
    has_adapt = bool(adapt_text)
    pei_text = (pei_adaptation_text or "").strip() or None
    has_pei = bool(has_pei_adaptations) and bool(pei_text)

    prof_nome = (
        (professor_nome or "").strip()
        or str(cliente.get("nome_clie") or "").strip()
        or None
    )
    contexto = _aula_contexto_from_evento(
        evento, metodologia=met_nome, aula_contexto=aula_contexto
    )

    origem = None
    raw_origem = evento.get("desafio_id") or evento.get("id_evento")
    if raw_origem is not None:
        origem = str(raw_origem)

    ev_status = str(evento.get("status") or "").strip().lower()
    mesa_status = ev_status or "concluido"
    # Status no School: aprovado só no fechamento; em andamento → pendente.
    if school_status:
        payload_status = school_status
    elif has_adapt or mesa_status in ("concluido", "concluído", "done"):
        payload_status = "aprovado"
    else:
        payload_status = "pendente"

    cards = _cards_snapshot_from_evento(evento)

    # Cadeia School: desafio exige desafio_grupo_id; aula avulsa/Dia a Dia não.
    raw_desafio = evento.get("desafio_id") or evento.get("desafio_grupo_id")
    desafio_grupo_id = None
    if raw_desafio not in (None, ""):
        desafio_grupo_id = str(raw_desafio).strip() or None
    tipo_aula = "desafio" if desafio_grupo_id else "dia_a_dia"

    mesa = {
        "id": str(evento.get("id_evento") or ""),
        "titulo": evento.get("titulo") or "",
        "tipo_aula": tipo_aula,
        "status": mesa_status,
        "metodologia_nome": met_nome,
        "semana_referencia": str(evento.get("data_evento") or "")[:10] or None,
        "has_teacher_adaptations": has_adapt,
        "teacher_adaptation_text": adapt_text,
        "texto_sugestao": adapt_text,
        "aula_contexto": contexto,
        "adaptations": {"texto": adapt_text} if adapt_text else None,
        "has_pei_adaptations": has_pei,
        "pei_adaptation_text": pei_text,
        "pei_aluno_id": pei_aluno_id,
        "aluno_nome": aluno_nome,
        "relato_sala": evento.get("relato_sala"),
        "participantes": evento.get("participantes"),
        "professor_id": str(id_clie),
        "professor_nome": prof_nome,
        "desafio_grupo_id": desafio_grupo_id,
        "cards": cards,
        "kanban_cards": cards,
    }

    payload = {
        "instituicao_id": str(instituicao_id),
        "origem_plano_b2c_id": origem,
        "professor_email": cliente.get("mail_clie"),
        "email": cliente.get("mail_clie"),
        "professor_b2c_id": str(id_clie),
        "professor_id": str(id_clie),
        "professor_nome": prof_nome,
        "aula_contexto": contexto,
        "texto_sugestao": adapt_text,
        "metodologia_nome": met_nome,
        "metodologia_usada": met_nome,
        "semana_referencia": mesa["semana_referencia"],
        "tipo_aula": tipo_aula,
        "desafio_grupo_id": desafio_grupo_id,
        "status": payload_status,
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

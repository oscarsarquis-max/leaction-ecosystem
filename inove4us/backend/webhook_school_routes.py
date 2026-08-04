"""Webhook S2S inove4us-school → inove4us B2C (ponte interna JWT).

POST /api/webhooks/school — sem login de sessão / gatekeeper exempt via /api/webhooks/.
Sempre HTTP 200 após JWT válido (ACK).
"""
from __future__ import annotations

import os
import sys
from datetime import date, datetime
from functools import wraps
from pathlib import Path
from typing import Any, Callable

import jwt
from dotenv import load_dotenv
from flask import Blueprint, g, jsonify, request
from psycopg2.extras import Json, RealDictCursor

from db import find_cliente_by_email, get_conn

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

webhook_school_bp = Blueprint("school_webhooks", __name__)

ISSUER_SCHOOL = "inove4us-school"


def _shared_secret() -> str:
    secret = (os.environ.get("SCHOOL_B2C_SHARED_SECRET") or "").strip()
    if secret:
        return secret
    env_file = Path(__file__).resolve().parents[1] / ".env"
    if env_file.is_file():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("SCHOOL_B2C_SHARED_SECRET="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def _extract_token() -> str:
    auth = (request.headers.get("Authorization") or "").strip()
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()
    sig = (request.headers.get("X-School-B2C-Signature") or "").strip()
    if sig:
        return sig
    body = request.get_json(silent=True) or {}
    token = body.get("token")
    return str(token).strip() if token else ""


def require_school_bridge_jwt(view: Callable):
    @wraps(view)
    def wrapped(*args, **kwargs):
        token = _extract_token()
        if not token:
            return jsonify({"error": "Token ausente"}), 401
        secret = _shared_secret()
        if not secret:
            return jsonify({"error": "SCHOOL_B2C_SHARED_SECRET não configurado"}), 503
        try:
            decoded = jwt.decode(token, secret, algorithms=["HS256"])
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token expirado"}), 401
        except jwt.InvalidTokenError as exc:
            return jsonify({"error": "Token inválido", "detail": str(exc)}), 401
        iss = str(decoded.get("iss") or "").strip()
        if iss != ISSUER_SCHOOL:
            return jsonify({"error": "iss inválido", "detail": iss or "(vazio)"}), 401
        g.school_bridge_jwt = decoded
        return view(*args, **kwargs)

    return wrapped


def _event_payload(decoded: dict, body: dict) -> tuple[str, dict]:
    event_type = str(
        decoded.get("event_type")
        or body.get("event_type")
        or request.headers.get("X-School-Event-Type")
        or ""
    ).strip()
    inner = decoded.get("payload")
    if inner is None:
        inner = body.get("payload")
    if not isinstance(inner, dict):
        inner = {}
    return event_type, inner


def _log(msg: str) -> None:
    print(f"[school-webhook] {msg}", flush=True)


def _parse_event_dt(raw: Any) -> datetime:
    if isinstance(raw, datetime):
        return raw
    if isinstance(raw, date):
        return datetime(raw.year, raw.month, raw.day, 8, 0, 0)
    s = str(raw or "").strip()
    if not s:
        return datetime.now().replace(hour=8, minute=0, second=0, microsecond=0)
    try:
        if "T" in s or " " in s:
            return datetime.fromisoformat(s.replace("Z", "+00:00")).replace(tzinfo=None)
        d = date.fromisoformat(s[:10])
        return datetime(d.year, d.month, d.day, 8, 0, 0)
    except ValueError:
        return datetime.now().replace(hour=8, minute=0, second=0, microsecond=0)


def _resolve_id_clie(payload: dict) -> int | None:
    """Resolve professor School → id_clie B2C (e-mail preferencial; id numérico fallback)."""
    email = str(
        payload.get("professor_email")
        or payload.get("email")
        or payload.get("mail_clie")
        or ""
    ).strip().lower()
    if email and "@" in email:
        cliente = find_cliente_by_email(email)
        if cliente and cliente.get("id_clie"):
            return int(cliente["id_clie"])

    raw = str(payload.get("professor_b2c_id") or "").strip()
    if raw.isdigit():
        return int(raw)

    # UUID provisório School (uuid5) — tenta match por meta futura; por ora e-mail é a chave.
    return None


def _ensure_school_agenda_columns(cur) -> None:
    cur.execute(
        """
        ALTER TABLE public.inove_agenda_eventos
            ADD COLUMN IF NOT EXISTS is_from_school BOOLEAN NOT NULL DEFAULT FALSE
        """
    )


def _handle_methodology_override(payload: dict) -> dict:
    instituicao_id = payload.get("instituicao_id")
    metodologia_nome = payload.get("metodologia_nome")
    diretriz = payload.get("diretriz_customizada")
    _log(
        f"METHODOLOGY_OVERRIDE_UPDATED instituicao={instituicao_id} "
        f"metodologia={metodologia_nome!r} "
        f"diretriz_len={len(str(diretriz or ''))}"
    )
    return {
        "handled": True,
        "event": "METHODOLOGY_OVERRIDE_UPDATED",
        "instituicao_id": instituicao_id,
        "metodologia_nome": metodologia_nome,
        "override_applied": False,
        "note": "receiver stub — apply override in teacher IA layer next",
    }


def _handle_teacher_allocated(payload: dict) -> dict:
    """
    TEACHER_ALLOCATED → cria compromisso em inove_agenda_eventos para o professor.
    Status inicial: planejado (padrão da agenda; equivalente a 'pendente' de planejamento).
    """
    professor_b2c_id = payload.get("professor_b2c_id")
    disciplina_nome = str(payload.get("disciplina_nome") or "").strip() or "Disciplina"
    ementa_macro = str(payload.get("ementa_macro") or "").strip()
    data_inicio = payload.get("data_inicio_periodo")
    alocacao_id = str(payload.get("alocacao_id") or "").strip() or None

    id_clie = _resolve_id_clie(payload)
    if not id_clie:
        _log(
            f"TEACHER_ALLOCATED sem professor resolvido "
            f"b2c_id={professor_b2c_id} email={payload.get('professor_email')}"
        )
        return {
            "handled": False,
            "reason": "professor_not_found",
            "event": "TEACHER_ALLOCATED",
            "professor_b2c_id": professor_b2c_id,
        }

    titulo = f"Planejamento Institucional: {disciplina_nome}"[:200]
    data_evento = _parse_event_dt(data_inicio)
    meta = {
        "alocacao_escola": True,
        "is_from_school": True,
        "professor_b2c_id": str(professor_b2c_id) if professor_b2c_id else None,
        "disciplina_nome": disciplina_nome,
        "ementa_macro": ementa_macro,
        "instituicao_id": payload.get("instituicao_id"),
        "unidade_nome": payload.get("unidade_nome"),
        "periodo_nome": payload.get("periodo_nome"),
        "alocacao_id": alocacao_id,
        "status_planejamento": "pendente",
    }

    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            _ensure_school_agenda_columns(cur)

            if alocacao_id:
                cur.execute(
                    """
                    SELECT id_evento
                    FROM public.inove_agenda_eventos
                    WHERE id_clie = %s
                      AND origem = 'alocacao_escola'
                      AND id_externo_importacao = %s
                    LIMIT 1
                    """,
                    (id_clie, alocacao_id),
                )
                existing = cur.fetchone()
                if existing:
                    _log(
                        f"TEACHER_ALLOCATED idempotente id_evento={existing['id_evento']} "
                        f"alocacao={alocacao_id}"
                    )
                    return {
                        "handled": True,
                        "event": "TEACHER_ALLOCATED",
                        "idempotent": True,
                        "id_evento": int(existing["id_evento"]),
                        "id_clie": id_clie,
                        "calendar_event_created": False,
                    }

            cur.execute(
                """
                INSERT INTO public.inove_agenda_eventos (
                    id_clie,
                    data_evento,
                    titulo,
                    nota_texto,
                    status,
                    tipo,
                    origem,
                    is_from_school,
                    id_externo_importacao,
                    meta_json
                )
                VALUES (
                    %s, %s, %s, %s,
                    'planejado', 'geral', 'alocacao_escola', TRUE,
                    %s, %s
                )
                RETURNING id_evento
                """,
                (
                    id_clie,
                    data_evento,
                    titulo,
                    ementa_macro or None,
                    alocacao_id,
                    Json(meta),
                ),
            )
            row = cur.fetchone()
            id_evento = int(row["id_evento"])

    _log(
        f"TEACHER_ALLOCATED criado id_evento={id_evento} id_clie={id_clie} "
        f"disciplina={disciplina_nome!r} data={data_evento.date().isoformat()}"
    )
    return {
        "handled": True,
        "event": "TEACHER_ALLOCATED",
        "id_evento": id_evento,
        "id_clie": id_clie,
        "professor_b2c_id": professor_b2c_id,
        "disciplina_nome": disciplina_nome,
        "data_inicio_periodo": data_inicio,
        "calendar_event_created": True,
        "status": "planejado",
        "is_from_school": True,
    }


@webhook_school_bp.post("/api/webhooks/school")
@require_school_bridge_jwt
def school_webhook():
    body = request.get_json(silent=True) or {}
    decoded = getattr(g, "school_bridge_jwt", {}) or {}
    event_type, payload = _event_payload(decoded, body)

    try:
        if event_type == "METHODOLOGY_OVERRIDE_UPDATED":
            result = _handle_methodology_override(payload)
        elif event_type == "TEACHER_ALLOCATED":
            result = _handle_teacher_allocated(payload)
        else:
            _log(f"event_type desconhecido: {event_type or '(vazio)'}")
            print(
                f"[school-webhook] payload preview: {str(payload)[:300]}",
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
        print(f"[school-webhook] {exc}", file=sys.stderr, flush=True)
        result = {"handled": False, "error": str(exc), "event_type": event_type}

    # ACK outbox — sempre 200 após JWT válido
    return (
        jsonify(
            {
                "status": "received",
                "app": "inove4us",
                "event_type": event_type,
                "result": result,
            }
        ),
        200,
    )

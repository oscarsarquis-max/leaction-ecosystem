"""Webhook S2S inove4us-school → inove4us B2C (ponte interna JWT).

POST /api/webhooks/school — sem login de sessão / gatekeeper exempt via /api/webhooks/.
Sempre HTTP 200 após JWT válido (ACK).
"""
from __future__ import annotations

import os
import sys
import json
from datetime import date, datetime
from functools import wraps
from pathlib import Path
from typing import Any, Callable

import jwt
from dotenv import load_dotenv
from flask import Blueprint, g, jsonify, request
from psycopg2.extras import Json, RealDictCursor

from db import find_cliente_by_email, get_conn

# Só preenche ausentes — nunca sobrescreve env da task ECS.
load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=False)

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
    """Persiste override da escola (upsert por instituição + metodologia_key)."""
    instituicao_id = payload.get("instituicao_id")
    metodologia_nome = payload.get("metodologia_nome")
    diretriz = payload.get("diretriz_customizada")
    _log(
        f"METHODOLOGY_OVERRIDE_UPDATED instituicao={instituicao_id} "
        f"metodologia={metodologia_nome!r} "
        f"codigo={payload.get('metodologia_codigo')!r} "
        f"diretriz_len={len(str(diretriz or ''))}"
    )
    try:
        from services.methodology_override_service import upsert_methodology_override

        result = upsert_methodology_override(payload if isinstance(payload, dict) else {})
    except Exception as exc:
        _log(f"METHODOLOGY_OVERRIDE persist falhou: {exc}")
        # ACK mesmo em falha de persistência — não derruba a ponte School→B2C
        return {
            "handled": True,
            "event": "METHODOLOGY_OVERRIDE_UPDATED",
            "instituicao_id": instituicao_id,
            "metodologia_nome": metodologia_nome,
            "override_applied": False,
            "error": str(exc),
        }

    return {
        "handled": True,
        "event": "METHODOLOGY_OVERRIDE_UPDATED",
        "instituicao_id": instituicao_id,
        "metodologia_nome": metodologia_nome,
        "metodologia_key": result.get("metodologia_key"),
        "override_applied": bool(result.get("ok") and result.get("applied")),
        "stale": result.get("reason") == "stale_event",
        "override": result.get("override"),
        "reason": result.get("reason"),
    }


def _handle_pei_override(payload: dict) -> dict:
    """Persiste PEI_OVERRIDE_UPDATED (níveis aee_base | individual)."""
    body = payload if isinstance(payload, dict) else {}
    nivel = str(body.get("nivel") or "").strip().lower()
    instituicao_id = body.get("instituicao_id")
    _log(
        f"PEI_OVERRIDE_UPDATED nivel={nivel!r} instituicao={instituicao_id} "
        f"condicao={body.get('condicao')!r} aluno={body.get('aluno_nome')!r} "
        f"pei_aluno_id={body.get('pei_aluno_id')}"
    )
    if not nivel:
        # Payload legado (Ciclo Vivo) — não persiste; ACK sem aplicar
        return {
            "handled": True,
            "event": "PEI_OVERRIDE_UPDATED",
            "instituicao_id": instituicao_id,
            "override_applied": False,
            "reason": "nivel ausente (payload legado ignorado)",
        }
    try:
        from services.pei_override_service import upsert_pei_override

        result = upsert_pei_override(body)
    except Exception as exc:
        _log(f"PEI_OVERRIDE persist falhou: {exc}")
        return {
            "handled": True,
            "event": "PEI_OVERRIDE_UPDATED",
            "instituicao_id": instituicao_id,
            "nivel": nivel,
            "override_applied": False,
            "error": str(exc),
        }
    return {
        "handled": True,
        "event": "PEI_OVERRIDE_UPDATED",
        "instituicao_id": instituicao_id,
        "nivel": result.get("nivel") or nivel,
        "override_applied": bool(result.get("ok") and result.get("applied")),
        "stale": result.get("reason") == "stale_event",
        "override": result.get("override"),
        "reason": result.get("reason"),
    }


def _handle_teacher_allocated(payload: dict) -> dict:
    """TEACHER_ALLOCATED → espelha árvore acadêmica + agenda de planejamento."""
    from services.school_academic_mirror import handle_teacher_allocated

    return handle_teacher_allocated(payload if isinstance(payload, dict) else {})


def _ensure_avisos_mesa(cur: Any) -> None:
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS public.inove_avisos_mesa (
            id                          UUID PRIMARY KEY,
            instituicao_b2b_id          UUID,
            texto                       TEXT NOT NULL,
            disciplina_nome             TEXT,
            turma_nome                  TEXT,
            disciplina_id               UUID,
            turma_id                    UUID,
            ativo                       BOOLEAN NOT NULL DEFAULT TRUE,
            synced_at                   TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_inove_avisos_mesa_ativos
            ON public.inove_avisos_mesa (ativo, synced_at DESC)
            WHERE ativo = TRUE;
        CREATE INDEX IF NOT EXISTS idx_inove_avisos_mesa_inst_ativos
            ON public.inove_avisos_mesa (instituicao_b2b_id, synced_at DESC)
            WHERE ativo = TRUE AND instituicao_b2b_id IS NOT NULL;
        ALTER TABLE public.inove_avisos_mesa
            ADD COLUMN IF NOT EXISTS professor_b2c_id INTEGER;
        ALTER TABLE public.inove_avisos_mesa
            ADD COLUMN IF NOT EXISTS tipo VARCHAR(64) NOT NULL DEFAULT 'geral';
        ALTER TABLE public.inove_avisos_mesa
            ADD COLUMN IF NOT EXISTS meta_json JSONB;
        """
    )


def _handle_aviso_mesa_pinned(payload: dict) -> dict:
    aviso_id = str(payload.get("aviso_id") or payload.get("id") or "").strip()
    texto = str(payload.get("texto") or "").strip()
    if not aviso_id or not texto:
        return {"handled": False, "reason": "aviso_id/texto obrigatórios", "event": "AVISO_MESA_PINNED"}
    ativo = payload.get("ativo")
    if ativo is None:
        ativo = True
    inst = str(payload.get("instituicao_id") or "").strip() or None
    # Fail-safe fechado na ingestão: aviso ativo sem instituição não é persistido
    # (evita linha órfã que, em bug de listagem, vaze para todos).
    if bool(ativo) and not inst:
        return {
            "handled": False,
            "reason": "instituicao_id obrigatório para aviso ativo",
            "event": "AVISO_MESA_PINNED",
        }
    disc_id = str(payload.get("disciplina_id") or "").strip() or None
    turma_id = str(payload.get("turma_id") or "").strip() or None
    tipo = str(payload.get("tipo") or "geral").strip() or "geral"
    professor_b2c = payload.get("professor_b2c_id")
    try:
        professor_b2c_id = int(professor_b2c) if professor_b2c not in (None, "") else None
    except (TypeError, ValueError):
        professor_b2c_id = None
    meta = {
        "resultado": payload.get("resultado"),
        "sugestao_resumo": payload.get("sugestao_resumo"),
        "retorno_docente": payload.get("retorno_docente"),
        "rotulo": payload.get("rotulo"),
    }
    with get_conn() as conn:
        with conn.cursor() as cur:
            _ensure_avisos_mesa(cur)
            cur.execute(
                """
                INSERT INTO public.inove_avisos_mesa
                    (id, instituicao_b2b_id, texto, disciplina_nome, turma_nome,
                     disciplina_id, turma_id, ativo, synced_at,
                     professor_b2c_id, tipo, meta_json)
                VALUES (
                    %s::uuid, NULLIF(%s, '')::uuid, %s, %s, %s,
                    NULLIF(%s, '')::uuid, NULLIF(%s, '')::uuid, %s, CURRENT_TIMESTAMP,
                    %s, %s, %s::jsonb
                )
                ON CONFLICT (id) DO UPDATE SET
                    instituicao_b2b_id = COALESCE(
                        EXCLUDED.instituicao_b2b_id,
                        inove_avisos_mesa.instituicao_b2b_id
                    ),
                    texto = EXCLUDED.texto,
                    disciplina_nome = EXCLUDED.disciplina_nome,
                    turma_nome = EXCLUDED.turma_nome,
                    disciplina_id = EXCLUDED.disciplina_id,
                    turma_id = EXCLUDED.turma_id,
                    ativo = EXCLUDED.ativo,
                    professor_b2c_id = EXCLUDED.professor_b2c_id,
                    tipo = EXCLUDED.tipo,
                    meta_json = EXCLUDED.meta_json,
                    synced_at = CURRENT_TIMESTAMP
                """,
                (
                    aviso_id,
                    inst or "",
                    texto,
                    payload.get("disciplina_nome"),
                    payload.get("turma_nome"),
                    disc_id or "",
                    turma_id or "",
                    bool(ativo),
                    professor_b2c_id,
                    tipo,
                    json.dumps(meta, ensure_ascii=False),
                ),
            )
    _log(
        f"AVISO_MESA_PINNED id={aviso_id} inst={inst} ativo={bool(ativo)} "
        f"prof={professor_b2c_id} tipo={tipo}"
    )
    return {"handled": True, "event": "AVISO_MESA_PINNED", "aviso_id": aviso_id}


def _handle_teacher_invite(payload: dict) -> dict:
    from services.school_academic_mirror import handle_teacher_invite

    return handle_teacher_invite(payload if isinstance(payload, dict) else {})


def _handle_school_gestor_credentials(payload: dict) -> dict:
    """Disparo transacional da credencial do gestor School. Sem senha no log."""
    from mail import send_school_gestor_credentials_email

    email = str(
        payload.get("payer_email") or payload.get("email") or payload.get("gestor_email") or ""
    ).strip().lower()
    senha = str(payload.get("senha_temporaria") or payload.get("password") or "").strip()
    acesso_url = str(
        payload.get("acesso_url") or "https://school.inove4us.com.br/acesso"
    ).strip()
    razao = str(payload.get("razao_social") or "").strip()
    if not email or "@" not in email or not senha:
        _log("SCHOOL_GESTOR_CREDENTIALS sem e-mail ou senha — ignorado")
        return {"handled": False, "reason": "missing_email_or_password"}
    info = send_school_gestor_credentials_email(
        recipient=email,
        password=senha,
        acesso_url=acesso_url,
        razao_social=razao,
    )
    sent = bool(info.get("sent"))
    _log(
        f"SCHOOL_GESTOR_CREDENTIALS email={email} sent={sent} channel={info.get('channel')}"
    )
    return {
        "handled": True,
        "event": "SCHOOL_GESTOR_CREDENTIALS",
        "sent": sent,
        "channel": info.get("channel"),
        "error": info.get("error"),
    }


def _handle_school_homologador_credentials(payload: dict) -> dict:
    """Um e-mail: senha School + link Inove (homologação)."""
    from mail import send_homologador_credentials_email

    email = str(
        payload.get("email") or payload.get("gestor_email") or payload.get("payer_email") or ""
    ).strip().lower()
    senha = str(payload.get("senha_temporaria") or payload.get("password") or "").strip()
    nome = str(payload.get("nome") or payload.get("gestor_nome") or "").strip()
    school_url = str(
        payload.get("acesso_url") or "https://school.inove4us.com.br/acesso"
    ).strip()
    invite_url = str(
        payload.get("invite_url") or payload.get("inove_invite_url") or ""
    ).strip()
    razao = str(payload.get("razao_social") or "").strip()
    school_bypass = str(payload.get("school_bypass_url") or "").strip()
    inove_bypass = str(payload.get("inove_bypass_url") or "").strip()
    if not email or "@" not in email or not senha:
        _log("SCHOOL_HOMOLOGADOR_CREDENTIALS sem e-mail ou senha — ignorado")
        return {"handled": False, "reason": "missing_email_or_password"}
    if not invite_url:
        _log("SCHOOL_HOMOLOGADOR_CREDENTIALS sem invite_url — ignorado")
        return {"handled": False, "reason": "missing_invite_url"}
    info = send_homologador_credentials_email(
        recipient=email,
        nome=nome or email.split("@", 1)[0],
        password=senha,
        school_acesso_url=school_url,
        inove_invite_url=invite_url,
        razao_social=razao,
        school_bypass_url=school_bypass or None,
        inove_bypass_url=inove_bypass or None,
    )
    sent = bool(info.get("sent"))
    _log(
        f"SCHOOL_HOMOLOGADOR_CREDENTIALS email={email} sent={sent} "
        f"channel={info.get('channel')}"
    )
    return {
        "handled": True,
        "event": "SCHOOL_HOMOLOGADOR_CREDENTIALS",
        "sent": sent,
        "channel": info.get("channel"),
        "error": info.get("error"),
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
        elif event_type == "PEI_OVERRIDE_UPDATED":
            result = _handle_pei_override(payload)
        elif event_type == "TEACHER_ALLOCATED":
            result = _handle_teacher_allocated(payload)
        elif event_type == "AVISO_MESA_PINNED":
            result = _handle_aviso_mesa_pinned(payload)
        elif event_type == "TEACHER_INVITE":
            result = _handle_teacher_invite(payload)
        elif event_type == "SCHOOL_GESTOR_CREDENTIALS":
            result = _handle_school_gestor_credentials(payload)
        elif event_type == "SCHOOL_HOMOLOGADOR_CREDENTIALS":
            result = _handle_school_homologador_credentials(payload)
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

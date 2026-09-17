"""Programa de Co-criação — feedbacks (ideia / bug / melhoria)."""

from __future__ import annotations

import hmac
import os
import sys
import uuid

from flask import Blueprint, jsonify, request, session
from psycopg2.extras import Json, RealDictCursor

from db import get_conn

feedback_bp = Blueprint("feedbacks", __name__)

_ensured = False

TIPOS = frozenset({"ideia", "bug", "melhoria"})
STATUSES = frozenset({"pendente", "lido", "recompensado", "arquivado"})
MAX_MENSAGEM = 8000
MAX_RETORNO = 8000
AVISO_TIPO_NINA = "resposta_feedback_nina"


def _require_user():
    user = session.get("user")
    if not user or not user.get("id_clie"):
        return None
    email = str(user.get("mail_clie") or "").strip().lower()
    if not email:
        return None
    return user


def _iso(value):
    return value.isoformat() if hasattr(value, "isoformat") else value


def _crm_tracking_secret() -> str:
    return (os.environ.get("CRM_TRACKING_SECRET") or "").strip()


def _s2s_deny():
    """Autenticação S2S Hub↔Inove (mesmo secret do tracking). None = ok."""
    expected = _crm_tracking_secret()
    if not expected:
        return jsonify({"ok": False, "error": "CRM_TRACKING_SECRET não configurado"}), 503
    got = (request.headers.get("x-crm-secret") or "").strip()
    if not got or not hmac.compare_digest(got, expected):
        return jsonify({"ok": False, "error": "x-crm-secret inválido ou ausente"}), 401
    return None


def _ensure_table(conn) -> None:
    global _ensured
    if _ensured:
        return
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS public.inove_user_feedbacks (
                id           SERIAL PRIMARY KEY,
                user_email   VARCHAR(254) NOT NULL,
                id_clie      INTEGER REFERENCES public.ctdi_clie (id_clie) ON DELETE SET NULL,
                tipo         VARCHAR(32) NOT NULL,
                mensagem     TEXT NOT NULL,
                status       VARCHAR(32) NOT NULL DEFAULT 'pendente',
                created_at   TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_inove_user_feedbacks_email_created
                ON public.inove_user_feedbacks (lower(user_email), created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_inove_user_feedbacks_status
                ON public.inove_user_feedbacks (status, created_at DESC);
            ALTER TABLE public.inove_user_feedbacks
                ADD COLUMN IF NOT EXISTS retorno_texto TEXT;
            ALTER TABLE public.inove_user_feedbacks
                ADD COLUMN IF NOT EXISTS retorno_em TIMESTAMP WITHOUT TIME ZONE;
            """
        )
    _ensured = True


def _ensure_avisos_mesa(cur) -> None:
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
        ALTER TABLE public.inove_avisos_mesa
            ADD COLUMN IF NOT EXISTS professor_b2c_id INTEGER;
        ALTER TABLE public.inove_avisos_mesa
            ADD COLUMN IF NOT EXISTS tipo VARCHAR(64) NOT NULL DEFAULT 'geral';
        ALTER TABLE public.inove_avisos_mesa
            ADD COLUMN IF NOT EXISTS meta_json JSONB;
        CREATE INDEX IF NOT EXISTS idx_inove_avisos_mesa_prof_nina
            ON public.inove_avisos_mesa (professor_b2c_id, synced_at DESC)
            WHERE ativo = TRUE AND tipo = 'resposta_feedback_nina';
        """
    )


def _row_public(row: dict) -> dict:
    return {
        "id": row["id"],
        "user_email": row.get("user_email"),
        "id_clie": row.get("id_clie"),
        "tipo": row.get("tipo"),
        "mensagem": row.get("mensagem"),
        "status": row.get("status"),
        "created_at": _iso(row.get("created_at")),
        "retorno_texto": row.get("retorno_texto"),
        "retorno_em": _iso(row.get("retorno_em")),
    }


def _criar_aviso_devolutiva(cur, row: dict, retorno_texto: str) -> str | None:
    """Aviso dirigido ao autor (id_clie). Sem instituicao — não é comunicado de escola."""
    id_clie = row.get("id_clie")
    if id_clie is None:
        return None
    aviso_id = str(uuid.uuid4())
    tipo_fb = str(row.get("tipo") or "")
    meta = {
        "feedback_id": row["id"],
        "tipo_feedback": tipo_fb,
        "rotulo": "Resposta ao seu feedback (Nina)",
        "retorno_texto": retorno_texto,
    }
    cur.execute(
        """
        INSERT INTO public.inove_avisos_mesa
            (id, instituicao_b2b_id, texto, ativo, synced_at,
             professor_b2c_id, tipo, meta_json)
        VALUES (
            %s::uuid, NULL, %s, TRUE, CURRENT_TIMESTAMP,
            %s, %s, %s
        )
        """,
        (aviso_id, retorno_texto, int(id_clie), AVISO_TIPO_NINA, Json(meta)),
    )
    return aviso_id


@feedback_bp.post("/api/feedbacks")
def create_feedback():
    user = _require_user()
    if not user:
        return jsonify({"success": False, "error": "Não autenticado"}), 401

    data = request.get_json(silent=True) or {}
    tipo = str(data.get("tipo") or "").strip().lower()
    mensagem = str(data.get("mensagem") or "").strip()

    if tipo not in TIPOS:
        return (
            jsonify(
                {
                    "success": False,
                    "error": "tipo inválido — use ideia, bug ou melhoria",
                }
            ),
            400,
        )
    if not mensagem:
        return jsonify({"success": False, "error": "mensagem é obrigatória"}), 400
    if len(mensagem) > MAX_MENSAGEM:
        return (
            jsonify(
                {
                    "success": False,
                    "error": f"mensagem excede o limite de {MAX_MENSAGEM} caracteres",
                }
            ),
            400,
        )

    user_email = str(user.get("mail_clie") or "").strip().lower()
    id_clie = int(user["id_clie"])

    try:
        with get_conn() as conn:
            _ensure_table(conn)
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    INSERT INTO public.inove_user_feedbacks
                        (user_email, id_clie, tipo, mensagem, status)
                    VALUES (%s, %s, %s, %s, 'pendente')
                    RETURNING id, user_email, tipo, status, created_at
                    """,
                    (user_email, id_clie, tipo, mensagem),
                )
                row = dict(cur.fetchone())
    except Exception as exc:
        print(f"⚠️ feedback create: {exc}", file=sys.stderr)
        return jsonify({"success": False, "error": "Falha ao gravar feedback"}), 500

    return (
        jsonify(
            {
                "success": True,
                "message": "Feedback recebido com sucesso!",
                "feedback": {
                    "id": row["id"],
                    "user_email": row["user_email"],
                    "tipo": row["tipo"],
                    "status": row["status"],
                    "created_at": _iso(row.get("created_at")),
                },
            }
        ),
        201,
    )


@feedback_bp.get("/internal/feedbacks")
def list_feedbacks_s2s():
    denied = _s2s_deny()
    if denied:
        return denied

    status_filter = str(request.args.get("status") or "").strip().lower()
    if status_filter and status_filter not in STATUSES:
        return jsonify({"ok": False, "error": "status inválido"}), 400

    try:
        with get_conn() as conn:
            _ensure_table(conn)
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                if status_filter:
                    cur.execute(
                        """
                        SELECT id, user_email, id_clie, tipo, mensagem, status,
                               created_at, retorno_texto, retorno_em
                        FROM public.inove_user_feedbacks
                        WHERE status = %s
                        ORDER BY created_at DESC
                        LIMIT 200
                        """,
                        (status_filter,),
                    )
                else:
                    cur.execute(
                        """
                        SELECT id, user_email, id_clie, tipo, mensagem, status,
                               created_at, retorno_texto, retorno_em
                        FROM public.inove_user_feedbacks
                        ORDER BY
                            CASE WHEN status = 'pendente' THEN 0
                                 WHEN status = 'lido' THEN 1
                                 WHEN status = 'recompensado' THEN 2
                                 ELSE 3 END,
                            created_at DESC
                        LIMIT 200
                        """
                    )
                rows = [dict(r) for r in cur.fetchall()]
    except Exception as exc:
        print(f"⚠️ feedback list s2s: {exc}", file=sys.stderr)
        return jsonify({"ok": False, "error": "Falha ao listar feedbacks"}), 500

    return jsonify({"ok": True, "feedbacks": [_row_public(r) for r in rows]})


@feedback_bp.patch("/internal/feedbacks/<int:feedback_id>")
def patch_feedback_s2s(feedback_id: int):
    denied = _s2s_deny()
    if denied:
        return denied

    data = request.get_json(silent=True) or {}
    status_raw = data.get("status")
    status = str(status_raw).strip().lower() if status_raw is not None else None
    retorno = str(data.get("retorno_texto") or "").strip()

    if status is None and not retorno:
        return (
            jsonify({"ok": False, "error": "informe status e/ou retorno_texto"}),
            400,
        )
    if status is not None and status not in STATUSES:
        return jsonify({"ok": False, "error": "status inválido"}), 400
    if len(retorno) > MAX_RETORNO:
        return (
            jsonify(
                {
                    "ok": False,
                    "error": f"retorno_texto excede o limite de {MAX_RETORNO} caracteres",
                }
            ),
            400,
        )

    aviso_id = None
    try:
        with get_conn() as conn:
            _ensure_table(conn)
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT id, user_email, id_clie, tipo, mensagem, status,
                           created_at, retorno_texto, retorno_em
                    FROM public.inove_user_feedbacks
                    WHERE id = %s
                    FOR UPDATE
                    """,
                    (feedback_id,),
                )
                row = cur.fetchone()
                if not row:
                    return jsonify({"ok": False, "error": "feedback não encontrado"}), 404
                row = dict(row)

                sets = []
                params = []
                if status is not None:
                    sets.append("status = %s")
                    params.append(status)
                if retorno:
                    sets.append("retorno_texto = %s")
                    sets.append("retorno_em = CURRENT_TIMESTAMP")
                    params.append(retorno)
                params.append(feedback_id)
                cur.execute(
                    f"""
                    UPDATE public.inove_user_feedbacks
                    SET {", ".join(sets)}
                    WHERE id = %s
                    RETURNING id, user_email, id_clie, tipo, mensagem, status,
                              created_at, retorno_texto, retorno_em
                    """,
                    tuple(params),
                )
                updated = dict(cur.fetchone())

                if retorno:
                    _ensure_avisos_mesa(cur)
                    aviso_id = _criar_aviso_devolutiva(cur, updated, retorno)
    except Exception as exc:
        print(f"⚠️ feedback patch s2s: {exc}", file=sys.stderr)
        return jsonify({"ok": False, "error": "Falha ao atualizar feedback"}), 500

    payload = {
        "ok": True,
        "feedback": _row_public(updated),
        "aviso_id": aviso_id,
        "aviso_concessao_manual": (updated.get("status") == "recompensado"),
    }
    return jsonify(payload)

"""Programa de Co-criação — feedbacks (ideia / bug / melhoria)."""

from __future__ import annotations

import sys

from flask import Blueprint, jsonify, request, session
from psycopg2.extras import RealDictCursor

from db import get_conn

feedback_bp = Blueprint("feedbacks", __name__)

_ensured = False

TIPOS = frozenset({"ideia", "bug", "melhoria"})
STATUSES = frozenset({"pendente", "lido", "recompensado", "arquivado"})
MAX_MENSAGEM = 8000


def _require_user():
    user = session.get("user")
    if not user or not user.get("id_clie"):
        return None
    email = str(user.get("mail_clie") or "").strip().lower()
    if not email:
        return None
    return user


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
            """
        )
    _ensured = True


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

    created_at = row.get("created_at")
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
                    "created_at": created_at.isoformat()
                    if hasattr(created_at, "isoformat")
                    else created_at,
                },
            }
        ),
        201,
    )

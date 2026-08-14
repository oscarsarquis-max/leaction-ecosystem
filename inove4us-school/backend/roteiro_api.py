"""Roteiro Guiado — respostas gravadas (homologação / treinamento).

Melhoria futura (fora de escopo): painel/drawer flutuante sobre as telas reais.
"""
from __future__ import annotations

import uuid
from typing import Any

from flask import Blueprint, jsonify, request
from psycopg2.extras import RealDictCursor

from auth_guards import current_gestor, require_gestor, require_zona, resolve_instituicao_id
from db import get_conn

bp = Blueprint("roteiro_guiado", __name__)

TIPOS = frozenset({"homologacao", "treinamento"})
PASSOS_NUMERADOS = (
    "A.1",
    "A.2",
    "A.3",
    "A.4",
    "A.5",
    "A.6",
    "B.7",
    "B.8",
    "B.9",
    "C.10",
    "C.11",
)
PASSOS_PERSISTIVEIS = frozenset(
    PASSOS_NUMERADOS
    + (
        "A.checkpoint",
        "B.checkpoint",
        "C.checkpoint",
        "feedback.entendi",
        "feedback.travou",
        "feedback.termo_estranho",
        "feedback.falta_para_usar",
        "feedback.impacto",
        "feedback.notas_livres",
    )
)
TOTAL_PASSOS = len(PASSOS_NUMERADOS)


def _parse_tipo(raw: Any, *, default: str = "homologacao") -> str | tuple:
    tipo = str(raw or default).strip().lower() or default
    if tipo not in TIPOS:
        return (
            jsonify(
                {
                    "error": "Tipo inválido. Use homologacao ou treinamento.",
                    "code": "INVALID_TIPO",
                }
            ),
            400,
        )
    return tipo


def _session_ids():
    inst = resolve_instituicao_id()
    if isinstance(inst, tuple):
        return inst
    user = current_gestor() or {}
    try:
        gestor_id = uuid.UUID(str(user.get("id") or ""))
        instituicao_id = uuid.UUID(str(inst))
    except (ValueError, TypeError, AttributeError):
        return jsonify({"error": "Sessão inválida", "code": "UNAUTHENTICATED"}), 401
    return instituicao_id, gestor_id


def _serialize_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "passo_id": row["passo_id"],
        "concluido": bool(row.get("concluido")),
        "observacao": row.get("observacao") or "",
        "atualizado_em": row["atualizado_em"].isoformat() if row.get("atualizado_em") else None,
    }


@bp.get("/api/roteiro-guiado/historico")
@require_zona("administrativo")
def historico():
    """Lista simples da própria instituição — não é dashboard."""
    parsed = _session_ids()
    if isinstance(parsed[0], tuple) or not isinstance(parsed[0], uuid.UUID):
        return parsed
    instituicao_id, _gestor_id = parsed

    tipo_raw = request.args.get("tipo")
    tipo_filter = None
    if tipo_raw is not None and str(tipo_raw).strip():
        tipo = _parse_tipo(tipo_raw)
        if isinstance(tipo, tuple):
            return tipo
        tipo_filter = tipo

    sql = """
        SELECT
            g.id AS gestor_id,
            g.nome AS gestor_nome,
            g.email AS gestor_email,
            i.razao_social AS instituicao,
            r.tipo,
            COUNT(*) FILTER (
                WHERE r.passo_id = ANY(%s) AND r.concluido IS TRUE
            )::int AS passos_concluidos,
            MAX(r.atualizado_em) AS atualizado_em
        FROM public.school_roteiro_respostas r
        JOIN public.school_gestores g ON g.id = r.gestor_id
        JOIN public.school_instituicoes i ON i.id = r.instituicao_id
        WHERE r.instituicao_id = %s
    """
    params: list[Any] = [list(PASSOS_NUMERADOS), str(instituicao_id)]
    if tipo_filter:
        sql += " AND r.tipo = %s"
        params.append(tipo_filter)
    sql += """
        GROUP BY g.id, g.nome, g.email, i.razao_social, r.tipo
        ORDER BY atualizado_em DESC NULLS LAST, g.nome
    """

    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()

    itens = []
    for row in rows:
        concluidos = int(row.get("passos_concluidos") or 0)
        itens.append(
            {
                "gestor_id": str(row["gestor_id"]),
                "gestor": row["gestor_nome"],
                "email": row["gestor_email"],
                "instituicao": row["instituicao"],
                "tipo": row["tipo"],
                "passos_concluidos": concluidos,
                "passos_total": TOTAL_PASSOS,
                "percentual": round(100.0 * concluidos / TOTAL_PASSOS) if TOTAL_PASSOS else 0,
                "atualizado_em": row["atualizado_em"].isoformat() if row.get("atualizado_em") else None,
            }
        )
    return jsonify({"ok": True, "itens": itens})


@bp.get("/api/roteiro-guiado")
@require_gestor
def get_estado():
    parsed = _session_ids()
    if isinstance(parsed[0], tuple) or not isinstance(parsed[0], uuid.UUID):
        return parsed
    instituicao_id, gestor_id = parsed

    tipo = _parse_tipo(request.args.get("tipo"), default="homologacao")
    if isinstance(tipo, tuple):
        return tipo

    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT passo_id, concluido, observacao, atualizado_em
                FROM public.school_roteiro_respostas
                WHERE instituicao_id = %s
                  AND gestor_id = %s
                  AND tipo = %s
                ORDER BY passo_id
                """,
                (str(instituicao_id), str(gestor_id), tipo),
            )
            rows = cur.fetchall()

    respostas = {row["passo_id"]: _serialize_row(row) for row in rows}
    return jsonify({"ok": True, "tipo": tipo, "respostas": respostas})


@bp.patch("/api/roteiro-guiado/<passo_id>")
@require_gestor
def patch_passo(passo_id: str):
    parsed = _session_ids()
    if isinstance(parsed[0], tuple) or not isinstance(parsed[0], uuid.UUID):
        return parsed
    instituicao_id, gestor_id = parsed

    pid = str(passo_id or "").strip()
    if pid not in PASSOS_PERSISTIVEIS:
        return jsonify({"error": "Passo inválido", "code": "INVALID_PASSO"}), 400

    body = request.get_json(silent=True) or {}
    tipo = _parse_tipo(body.get("tipo"), default="homologacao")
    if isinstance(tipo, tuple):
        return tipo

    concluido = bool(body.get("concluido"))
    observacao = body.get("observacao")
    if observacao is None:
        observacao = ""
    else:
        observacao = str(observacao)

    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                INSERT INTO public.school_roteiro_respostas (
                    instituicao_id, gestor_id, tipo, passo_id, concluido, observacao, atualizado_em
                )
                VALUES (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (instituicao_id, gestor_id, tipo, passo_id)
                DO UPDATE SET
                    concluido = EXCLUDED.concluido,
                    observacao = EXCLUDED.observacao,
                    atualizado_em = CURRENT_TIMESTAMP
                RETURNING passo_id, concluido, observacao, atualizado_em
                """,
                (str(instituicao_id), str(gestor_id), tipo, pid, concluido, observacao),
            )
            row = cur.fetchone()

    return jsonify({"ok": True, "tipo": tipo, "resposta": _serialize_row(row)})

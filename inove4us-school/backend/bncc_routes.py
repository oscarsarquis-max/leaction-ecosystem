"""BNCC canônica — leitura do catálogo importado e do recorte disciplina×ano.

GET /api/secretaria/bncc/temas-canonico — gestor (revisão).
GET /api/internal/bncc/temas — B2C (só status=aprovado).
"""
from __future__ import annotations

from flask import Blueprint, jsonify, request
from psycopg2.extras import RealDictCursor

from auth_guards import require_zona
from db import get_conn
from school_b2c_jwt import require_b2c_bridge_jwt

bp = Blueprint("bncc_canonico", __name__)
require_gestor = require_zona("operacional")


def _serialize(row) -> dict:
    return {
        "id": str(row["id"]) if row.get("id") else None,
        "disciplina_nome": row.get("disciplina_nome"),
        "curso_ano": row.get("curso_ano"),
        "etapa": row.get("etapa"),
        "tema": row.get("tema"),
        "habilidade_codigo": row.get("habilidade_codigo"),
        "texto_oficial": row.get("texto") or row.get("texto_oficial"),
        "origem": row.get("origem"),
        "status": row.get("status"),
        "agrupamento_fonte": row.get("agrupamento_fonte"),
        "fonte_url": row.get("fonte_url"),
        "rotulo_seletor": (
            f"{row.get('tema') or ''} — {row.get('habilidade_codigo') or ''}"
        ).strip(" —"),
    }


@bp.get("/api/secretaria/bncc/temas-canonico")
@require_gestor
def list_temas_secretaria():
    disciplina = (request.args.get("disciplina") or "").strip()
    curso_ano = (request.args.get("curso_ano") or "").strip()
    status = (request.args.get("status") or "").strip()
    sql = """
        SELECT t.id, t.disciplina_nome, t.curso_ano, t.etapa, t.tema,
               t.habilidade_codigo, t.origem, t.status, t.agrupamento_fonte,
               o.texto, o.fonte_url
          FROM public.school_bncc_temas_canonico t
          JOIN public.bncc_habilidades_oficial o ON o.codigo = t.habilidade_codigo
         WHERE 1=1
    """
    params: list = []
    if disciplina:
        sql += " AND lower(t.disciplina_nome) = lower(%s)"
        params.append(disciplina)
    if curso_ano:
        sql += " AND t.curso_ano = %s"
        params.append(curso_ano)
    if status:
        sql += " AND t.status = %s"
        params.append(status)
    sql += " ORDER BY t.disciplina_nome, t.curso_ano, t.tema, t.habilidade_codigo"
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, params)
            rows = [dict(r) for r in cur.fetchall()]
    return jsonify({"items": [_serialize(r) for r in rows], "count": len(rows)})


@bp.get("/api/internal/bncc/temas")
@require_b2c_bridge_jwt
def list_temas_b2c():
    """Só aprovados — o Dia a Dia não vê pendente_revisao.

    `codigos=EF06MA30,EF06MA10` (prompt 103): lookup pontual sem exigir disciplina.
    """
    disciplina = (request.args.get("disciplina") or "").strip()
    curso_ano = (request.args.get("curso_ano") or "").strip()
    raw_codes = (request.args.get("codigos") or "").strip()
    codes = [
        c.strip().upper()
        for c in raw_codes.replace(";", ",").split(",")
        if c.strip()
    ]
    if not disciplina and not codes:
        return jsonify({"error": "disciplina ou codigos obrigatório"}), 400
    sql = """
        SELECT t.id, t.disciplina_nome, t.curso_ano, t.etapa, t.tema,
               t.habilidade_codigo, t.origem, t.status, t.agrupamento_fonte,
               o.texto, o.fonte_url
          FROM public.school_bncc_temas_canonico t
          JOIN public.bncc_habilidades_oficial o ON o.codigo = t.habilidade_codigo
         WHERE t.status = 'aprovado'
    """
    params: list = []
    if codes:
        sql += " AND t.habilidade_codigo = ANY(%s)"
        params.append(codes)
    if disciplina:
        sql += " AND lower(t.disciplina_nome) = lower(%s)"
        params.append(disciplina)
    if curso_ano:
        sql += " AND t.curso_ano = %s"
        params.append(curso_ano)
    sql += " ORDER BY t.tema, t.habilidade_codigo"
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, params)
            rows = [dict(r) for r in cur.fetchall()]
    return jsonify({"items": [_serialize(r) for r in rows], "count": len(rows)})

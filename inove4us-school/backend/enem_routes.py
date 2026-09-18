"""Catálogo ENEM disponível por disciplina (view do 150).

GET /api/internal/enem/habilidades — B2C Dia a Dia.
Sem escola no mapeamento: o recorte é a interseção com o catálogo dela.
"""
from __future__ import annotations

from flask import Blueprint, jsonify, request
from psycopg2.extras import RealDictCursor

from db import get_conn
from school_b2c_jwt import require_b2c_bridge_jwt

bp = Blueprint("enem_catalogo_api", __name__)


def _codigo_oficial(row: dict) -> str:
    return str(row.get("habilidade_codigo") or row.get("redacao_codigo") or "").strip()


def serialize_enem(row: dict) -> dict:
    codigo = _codigo_oficial(row)
    area = str(row.get("area_codigo") or "").strip()
    comp = row.get("competencia_numero")
    rotulo = str(row.get("rotulo") or "").strip()
    tema = f"{area} · C{comp}" if area and comp is not None else area or codigo
    return {
        "habilidade_codigo": codigo,
        "area_codigo": area or None,
        "competencia_numero": comp,
        "tema": tema,
        "texto_oficial": rotulo,
        "disciplina_nome": row.get("disciplina_nome"),
        "disciplina_canonica": row.get("disciplina_canonica"),
        "nuance": row.get("nuance"),
        "rotulo_seletor": f"{codigo} — {rotulo}".strip(" —"),
        "origem": "enem_oficial",
        "status": row.get("status") or "aprovado",
    }


def listar_habilidades_enem(*, disciplina: str, instituicao_id: str = "", codigos: list[str] | None = None) -> list[dict]:
    nome = (disciplina or "").strip()
    inst = (instituicao_id or "").strip()
    codes = [c.strip().upper() for c in (codigos or []) if str(c).strip()]
    if not nome and not codes:
        return []
    sql = """
        SELECT v.instituicao_id, v.disciplina_id, v.disciplina_nome, v.disciplina_canonica,
               v.area_codigo, v.habilidade_codigo, v.redacao_codigo, v.competencia_numero,
               v.rotulo, v.nuance, v.status
          FROM public.school_enem_habilidades_canonico v
         WHERE 1=1
    """
    params: list = []
    if nome:
        sql += """
           AND v.disciplina_canonica IN (
                SELECT a.disciplina_canonica
                  FROM public.enem_disciplina_alias a
                 WHERE a.alias_norm = public.enem_norm_disciplina(%s)
           )
        """
        params.append(nome)
    if inst:
        sql += " AND v.instituicao_id = %s::uuid"
        params.append(inst)
    if codes:
        sql += """
           AND (
                v.habilidade_codigo = ANY(%s)
             OR v.redacao_codigo = ANY(%s)
           )
        """
        params.extend([codes, codes])
    sql += """
         ORDER BY v.area_codigo, v.competencia_numero NULLS LAST,
                  COALESCE(v.habilidade_codigo, v.redacao_codigo)
    """
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, params)
            rows = [dict(r) for r in cur.fetchall()]
    seen: set[str] = set()
    out: list[dict] = []
    for row in rows:
        codigo = _codigo_oficial(row)
        if not codigo or codigo in seen:
            continue
        seen.add(codigo)
        out.append(serialize_enem(row))
    return out


@bp.get("/api/internal/enem/habilidades")
@require_b2c_bridge_jwt
def list_habilidades_b2c():
    disciplina = (request.args.get("disciplina") or "").strip()
    instituicao_id = (request.args.get("instituicao_id") or "").strip()
    raw_codes = (request.args.get("codigos") or "").strip()
    codes = [
        c.strip().upper()
        for c in raw_codes.replace(";", ",").split(",")
        if c.strip()
    ]
    if not disciplina and not codes:
        return jsonify({"error": "disciplina ou codigos obrigatório"}), 400
    items = listar_habilidades_enem(
        disciplina=disciplina,
        instituicao_id=instituicao_id,
        codigos=codes or None,
    )
    return jsonify({"items": items, "count": len(items)})

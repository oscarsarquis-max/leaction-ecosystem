"""Retrieval S2S do card AEE modificado (prompt 86 / 102). Zero IA."""
from __future__ import annotations

from flask import Blueprint, jsonify, request
from psycopg2.extras import RealDictCursor

from db import get_conn
from school_b2c_jwt import require_b2c_bridge_jwt

bp = Blueprint("aee_internal", __name__)

ESCOLA_TESTE = "3fa7aff7-4bd1-4e7f-ae64-76d5eb781e50"


def _item_from_row(row: dict | None) -> dict | None:
    if not row:
        return None
    passos = str(row.get("passos_adaptados") or "").strip()
    if not passos:
        return None
    return {
        "metodologia_codigo": row.get("metodologia_codigo"),
        "metodologia_nome": row.get("metodologia_nome"),
        "condicao_categoria": row.get("condicao_categoria"),
        "passos_adaptados": passos,
        "turma_nome": row.get("turma_nome"),
        "aluno_nome": row.get("aluno_nome"),
        "fonte": "card_modificado_79_81",
    }


def lookup_canonico_por_condicao(cur, *, codigo: str, condicao: str) -> dict | None:
    """Card aprovado condição × metodologia — não exige PEI de aluno na turma."""
    cur.execute(
        """
        SELECT
            metodologia_codigo,
            metodologia_nome,
            condicao_categoria,
            passos_adaptados,
            status,
            NULL::text AS turma_nome,
            NULL::text AS aluno_nome
          FROM public.school_aee_metodologias_canonico
         WHERE status = 'aprovado'
           AND (
                metodologia_codigo = %s
                OR lower(trim(metodologia_codigo)) = lower(trim(%s))
           )
           AND lower(trim(condicao_categoria)) = lower(trim(%s))
         LIMIT 1
        """,
        (codigo, codigo, condicao),
    )
    return _item_from_row(cur.fetchone())


@bp.get("/api/internal/aee/card-modificado")
@require_b2c_bridge_jwt
def card_modificado():
    """Card já gerado em lote (79/81).

    Com `condicao`: lookup direto no canônico (🧩 do Desafio, prompt 102).
    Sem `condicao`: infere a condição pelo PEI ativo da turma (Dia a Dia / 86).
    """
    codigo = (request.args.get("metodologia_codigo") or "").strip()
    turma_nome = (request.args.get("turma_nome") or "").strip()
    condicao = (request.args.get("condicao") or "").strip()
    inst = (request.args.get("instituicao_id") or "").strip() or ESCOLA_TESTE
    if not codigo:
        return jsonify({"error": "metodologia_codigo obrigatório", "ia_called": False}), 400

    try:
        with get_conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                if condicao:
                    item = lookup_canonico_por_condicao(
                        cur, codigo=codigo, condicao=condicao
                    )
                    if item:
                        return jsonify({"ia_called": False, "item": item})
                    return jsonify({"item": None, "ia_called": False})

                sql = """
                    SELECT
                        can.metodologia_codigo,
                        can.metodologia_nome,
                        can.condicao_categoria,
                        can.passos_adaptados,
                        can.status,
                        t.nome AS turma_nome,
                        p.nome_completo AS aluno_nome
                      FROM public.school_pei_alunos p
                      JOIN public.school_aee_matrizes m ON m.id = p.aee_matriz_id
                      JOIN public.school_alunos a ON a.id = p.aluno_id
                      JOIN public.school_turmas t ON t.id = a.turma_id
                      JOIN public.school_aee_metodologias_canonico can
                        ON lower(trim(can.condicao_categoria)) = lower(trim(m.condicao_categoria))
                       AND (
                            can.metodologia_codigo = %s
                            OR lower(trim(can.metodologia_codigo)) = lower(trim(%s))
                       )
                     WHERE p.instituicao_id = %s::uuid
                       AND can.status = 'aprovado'
                       AND m.status::text = 'ativo'
                """
                params: list = [codigo, codigo, inst]
                if turma_nome:
                    sql += " AND lower(t.nome) = lower(%s)"
                    params.append(turma_nome)
                sql += " ORDER BY p.updated_at DESC NULLS LAST LIMIT 1"
                cur.execute(sql, params)
                item = _item_from_row(cur.fetchone())
    except Exception:
        return jsonify({"item": None, "ia_called": False, "error": "schema"}), 200
    if not item:
        return jsonify({"item": None, "ia_called": False})
    return jsonify({"ia_called": False, "item": item})

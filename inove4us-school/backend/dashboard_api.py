"""Dashboard — calendário pedagógico consolidado.

Fonte: school_planos_aula_espelhados (espelho local). Sem sync B2C ainda.
Auth interina: instituicao_id / unidade_id na URL.
"""
from __future__ import annotations

import calendar
import uuid
from datetime import date, datetime
from typing import Any

from flask import Blueprint, jsonify, request
from psycopg2.extras import RealDictCursor

from db import get_conn

bp = Blueprint("dashboard", __name__)

_PLANOS_SELECT = """
SELECT
    p.id,
    p.turma_id,
    t.nome AS turma_nome,
    t.unidade_id,
    u.nome AS unidade_nome,
    p.professor_vinculo_id,
    m.nome AS metodologia_nome,
    p.tipo_aula,
    p.semana_referencia,
    p.status,
    p.conteudo_resumo,
    p.desafio_grupo_id,
    p.desafio_titulo,
    p.desafio_sequencia
FROM public.school_planos_aula_espelhados p
JOIN public.school_turmas t
    ON t.id = p.turma_id
JOIN public.school_unidades u
    ON u.id = t.unidade_id
JOIN public.school_metodologias_catalogo m
    ON m.id = p.metodologia_catalogo_id
"""


def _parse_uuid(value: str, label: str):
    try:
        return uuid.UUID(str(value))
    except (ValueError, TypeError, AttributeError):
        return jsonify({"error": f"Identificador de {label} inválido"}), 400


def _parse_date(raw: str | None, label: str):
    if not raw:
        return None
    try:
        return date.fromisoformat(str(raw)[:10])
    except ValueError:
        return jsonify({"error": f"Data inválida em {label} (use AAAA-MM-DD)"}), 400


def _periodo_padrao() -> tuple[date, date]:
    hoje = date.today()
    inicio = date(hoje.year, hoje.month, 1)
    ultimo = calendar.monthrange(hoje.year, hoje.month)[1]
    fim = date(hoje.year, hoje.month, ultimo)
    return inicio, fim


def _resolver_periodo():
    di = _parse_date(request.args.get("data_inicio"), "data_inicio")
    if isinstance(di, tuple):
        return di
    df = _parse_date(request.args.get("data_fim"), "data_fim")
    if isinstance(df, tuple):
        return df
    if di is None and df is None:
        return _periodo_padrao()
    if di is None or df is None:
        return jsonify(
            {"error": "Informe data_inicio e data_fim juntos, ou nenhum dos dois"}
        ), 400
    if di > df:
        return jsonify({"error": "data_inicio não pode ser depois de data_fim"}), 400
    return di, df


def _unidade_exists(cur: Any, unidade_id: uuid.UUID) -> dict[str, Any] | None:
    cur.execute(
        """
        SELECT id, instituicao_id, nome, ativo
        FROM public.school_unidades
        WHERE id = %s
        """,
        (str(unidade_id),),
    )
    return cur.fetchone()


def _instituicao_exists(cur: Any, instituicao_id: uuid.UUID) -> bool:
    cur.execute(
        "SELECT 1 FROM public.school_instituicoes WHERE id = %s",
        (str(instituicao_id),),
    )
    return cur.fetchone() is not None


def _fmt_date(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, (date, datetime)):
        return value.isoformat()[:10]
    return str(value)


def _plano_row(r: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(r["id"]),
        "turma_id": str(r["turma_id"]),
        "turma_nome": r["turma_nome"],
        "unidade_id": str(r["unidade_id"]),
        "unidade_nome": r["unidade_nome"],
        "professor_vinculo_id": str(r["professor_vinculo_id"]),
        "metodologia_nome": r["metodologia_nome"],
        "tipo_aula": r["tipo_aula"],
        "semana_referencia": _fmt_date(r["semana_referencia"]),
        "status": r["status"],
        "conteudo_resumo": r.get("conteudo_resumo"),
        "desafio_grupo_id": str(r["desafio_grupo_id"]) if r.get("desafio_grupo_id") else None,
        "desafio_titulo": r.get("desafio_titulo"),
        "desafio_sequencia": r.get("desafio_sequencia"),
    }


def _resumo_payload(row: dict[str, Any], data_inicio: date, data_fim: date) -> dict[str, Any]:
    return {
        "total": int(row.get("total") or 0),
        "por_tipo_aula": {
            "dia_a_dia": int(row.get("dia_a_dia") or 0),
            "desafio": int(row.get("desafio") or 0),
        },
        "por_status": {
            "pendente": int(row.get("pendente") or 0),
            "aprovado": int(row.get("aprovado") or 0),
            "reprovado": int(row.get("reprovado") or 0),
        },
        "professores_ativos": int(row.get("professores_ativos") or 0),
        "data_inicio": data_inicio.isoformat(),
        "data_fim": data_fim.isoformat(),
    }


_RESUMO_SELECT = """
SELECT
    COUNT(*)::int AS total,
    COUNT(*) FILTER (WHERE p.tipo_aula = 'dia_a_dia')::int AS dia_a_dia,
    COUNT(*) FILTER (WHERE p.tipo_aula = 'desafio')::int AS desafio,
    COUNT(*) FILTER (WHERE p.status = 'pendente')::int AS pendente,
    COUNT(*) FILTER (WHERE p.status = 'aprovado')::int AS aprovado,
    COUNT(*) FILTER (WHERE p.status = 'reprovado')::int AS reprovado,
    COUNT(DISTINCT p.professor_vinculo_id)::int AS professores_ativos
FROM public.school_planos_aula_espelhados p
JOIN public.school_turmas t ON t.id = p.turma_id
JOIN public.school_unidades u ON u.id = t.unidade_id
"""


@bp.get("/api/instituicoes/<instituicao_id>/unidades")
def list_unidades(instituicao_id: str):
    parsed = _parse_uuid(instituicao_id, "instituição")
    if not isinstance(parsed, uuid.UUID):
        return parsed

    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            if not _instituicao_exists(cur, parsed):
                return jsonify({"error": "Instituição não encontrada"}), 404
            cur.execute(
                """
                SELECT id, nome, codigo, cidade, uf
                FROM public.school_unidades
                WHERE instituicao_id = %s AND ativo = TRUE
                ORDER BY nome
                """,
                (str(parsed),),
            )
            rows = cur.fetchall()

    return jsonify(
        [
            {
                "id": str(r["id"]),
                "nome": r["nome"],
                "codigo": r.get("codigo"),
                "cidade": r.get("cidade"),
                "uf": r.get("uf"),
            }
            for r in rows
        ]
    )


@bp.get("/api/unidades/<unidade_id>/calendario-pedagogico")
def calendario_pedagogico(unidade_id: str):
    parsed = _parse_uuid(unidade_id, "unidade")
    if not isinstance(parsed, uuid.UUID):
        return parsed
    periodo = _resolver_periodo()
    if not isinstance(periodo, tuple) or not isinstance(periodo[0], date):
        return periodo
    data_inicio, data_fim = periodo

    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            unidade = _unidade_exists(cur, parsed)
            if not unidade or not unidade["ativo"]:
                return jsonify({"error": "Unidade não encontrada"}), 404
            cur.execute(
                _PLANOS_SELECT
                + """
                WHERE t.unidade_id = %s
                  AND p.semana_referencia >= %s
                  AND p.semana_referencia <= %s
                ORDER BY p.semana_referencia, t.nome, m.nome
                """,
                (str(parsed), data_inicio, data_fim),
            )
            rows = cur.fetchall()

    return jsonify([_plano_row(r) for r in rows])


@bp.get("/api/unidades/<unidade_id>/calendario-pedagogico/resumo")
def calendario_pedagogico_resumo(unidade_id: str):
    parsed = _parse_uuid(unidade_id, "unidade")
    if not isinstance(parsed, uuid.UUID):
        return parsed
    periodo = _resolver_periodo()
    if not isinstance(periodo, tuple) or not isinstance(periodo[0], date):
        return periodo
    data_inicio, data_fim = periodo

    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            unidade = _unidade_exists(cur, parsed)
            if not unidade or not unidade["ativo"]:
                return jsonify({"error": "Unidade não encontrada"}), 404
            cur.execute(
                _RESUMO_SELECT
                + """
                WHERE t.unidade_id = %s
                  AND p.semana_referencia >= %s
                  AND p.semana_referencia <= %s
                """,
                (str(parsed), data_inicio, data_fim),
            )
            row = cur.fetchone() or {}

    return jsonify(_resumo_payload(row, data_inicio, data_fim))


@bp.get("/api/instituicoes/<instituicao_id>/calendario-pedagogico")
def calendario_instituicao(instituicao_id: str):
    parsed = _parse_uuid(instituicao_id, "instituição")
    if not isinstance(parsed, uuid.UUID):
        return parsed
    periodo = _resolver_periodo()
    if not isinstance(periodo, tuple) or not isinstance(periodo[0], date):
        return periodo
    data_inicio, data_fim = periodo

    unidade_raw = (request.args.get("unidade_id") or "").strip()
    unidade_id = None
    if unidade_raw:
        unidade_id = _parse_uuid(unidade_raw, "unidade")
        if not isinstance(unidade_id, uuid.UUID):
            return unidade_id

    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            if not _instituicao_exists(cur, parsed):
                return jsonify({"error": "Instituição não encontrada"}), 404

            if unidade_id is not None:
                unidade = _unidade_exists(cur, unidade_id)
                if (
                    not unidade
                    or not unidade["ativo"]
                    or str(unidade["instituicao_id"]) != str(parsed)
                ):
                    return jsonify({"error": "Unidade não encontrada"}), 404
                cur.execute(
                    _PLANOS_SELECT
                    + """
                    WHERE t.unidade_id = %s
                      AND p.semana_referencia >= %s
                      AND p.semana_referencia <= %s
                    ORDER BY p.semana_referencia, t.nome, m.nome
                    """,
                    (str(unidade_id), data_inicio, data_fim),
                )
            else:
                cur.execute(
                    _PLANOS_SELECT
                    + """
                    WHERE u.instituicao_id = %s
                      AND u.ativo = TRUE
                      AND p.semana_referencia >= %s
                      AND p.semana_referencia <= %s
                    ORDER BY u.nome, p.semana_referencia, t.nome, m.nome
                    """,
                    (str(parsed), data_inicio, data_fim),
                )
            rows = cur.fetchall()

    return jsonify([_plano_row(r) for r in rows])


@bp.get("/api/instituicoes/<instituicao_id>/calendario-pedagogico/resumo")
def calendario_instituicao_resumo(instituicao_id: str):
    parsed = _parse_uuid(instituicao_id, "instituição")
    if not isinstance(parsed, uuid.UUID):
        return parsed
    periodo = _resolver_periodo()
    if not isinstance(periodo, tuple) or not isinstance(periodo[0], date):
        return periodo
    data_inicio, data_fim = periodo

    unidade_raw = (request.args.get("unidade_id") or "").strip()
    unidade_id = None
    if unidade_raw:
        unidade_id = _parse_uuid(unidade_raw, "unidade")
        if not isinstance(unidade_id, uuid.UUID):
            return unidade_id

    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            if not _instituicao_exists(cur, parsed):
                return jsonify({"error": "Instituição não encontrada"}), 404

            if unidade_id is not None:
                unidade = _unidade_exists(cur, unidade_id)
                if (
                    not unidade
                    or not unidade["ativo"]
                    or str(unidade["instituicao_id"]) != str(parsed)
                ):
                    return jsonify({"error": "Unidade não encontrada"}), 404
                cur.execute(
                    _RESUMO_SELECT
                    + """
                    WHERE t.unidade_id = %s
                      AND p.semana_referencia >= %s
                      AND p.semana_referencia <= %s
                    """,
                    (str(unidade_id), data_inicio, data_fim),
                )
            else:
                cur.execute(
                    _RESUMO_SELECT
                    + """
                    WHERE u.instituicao_id = %s
                      AND u.ativo = TRUE
                      AND p.semana_referencia >= %s
                      AND p.semana_referencia <= %s
                    """,
                    (str(parsed), data_inicio, data_fim),
                )
            row = cur.fetchone() or {}

    return jsonify(_resumo_payload(row, data_inicio, data_fim))

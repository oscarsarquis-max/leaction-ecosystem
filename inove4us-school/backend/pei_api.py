"""PEI — plano geral (Pilar 2 do Editor Pedagógico).

Cadastro por tipo de neurodivergência:
  • área geral (5 campos + resumo `diretriz`)
  • campos de experiência BNCC (Educação Infantil) — vários objetivos por campo

Soft-delete via `ativo` (sem DELETE). Auth interina: instituicao_id na URL.
"""
from __future__ import annotations

import uuid
from typing import Any

from flask import Blueprint, jsonify, request
from psycopg2 import errors as pg_errors
from psycopg2.extras import RealDictCursor

from db import get_conn

bp = Blueprint("pei", __name__)

CAMPOS_EXPERIENCIA = (
    "o_eu_o_outro_e_o_nos",
    "corpo_gestos_e_movimentos",
    "escuta_fala_pensamento_e_imaginacao",
    "tracos_sons_cores_e_formas",
    "espacos_tempos_quantidades_relacoes_e_transformacoes",
)

AREA_GERAL_COLS = (
    "capacidades_interesses",
    "necessidades",
    "metas_prazos",
    "recursos_estrategias",
    "profissionais_envolvidos",
)


def _parse_uuid(value: str, label: str):
    try:
        return uuid.UUID(str(value))
    except (ValueError, TypeError, AttributeError):
        return jsonify({"error": f"Identificador de {label} inválido"}), 400


def _instituicao_exists(cur: Any, instituicao_id: uuid.UUID) -> bool:
    cur.execute(
        "SELECT 1 FROM public.school_instituicoes WHERE id = %s",
        (str(instituicao_id),),
    )
    return cur.fetchone() is not None


def _text_or_none(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _serialize_list_item(row: dict[str, Any]) -> dict:
    return {
        "id": str(row["id"]),
        "tipo_neurodivergencia": row["tipo_neurodivergencia"],
        "diretriz": row["diretriz"],
        "ativo": bool(row["ativo"]),
    }


def _serialize_campo(row: dict[str, Any]) -> dict:
    return {
        "id": str(row["id"]),
        "campo_experiencia": row["campo_experiencia"],
        "objetivo": row["objetivo"],
        "curriculo_habilidades": row.get("curriculo_habilidades"),
        "estrategias_ensino": row.get("estrategias_ensino"),
        "prazo": row.get("prazo"),
        "ativo": bool(row["ativo"]),
    }


def _serialize_detail(row: dict[str, Any], campos: list[dict[str, Any]]) -> dict:
    return {
        "id": str(row["id"]),
        "instituicao_id": str(row["instituicao_id"]),
        "tipo_neurodivergencia": row["tipo_neurodivergencia"],
        "diretriz": row["diretriz"],
        "capacidades_interesses": row.get("capacidades_interesses"),
        "necessidades": row.get("necessidades"),
        "metas_prazos": row.get("metas_prazos"),
        "recursos_estrategias": row.get("recursos_estrategias"),
        "profissionais_envolvidos": row.get("profissionais_envolvidos"),
        "ativo": bool(row["ativo"]),
        "campos_experiencia": [_serialize_campo(c) for c in campos],
        "created_at": row["created_at"].isoformat() if row.get("created_at") else None,
        "updated_at": row["updated_at"].isoformat() if row.get("updated_at") else None,
    }


def _load_plano(cur: Any, pei_id: uuid.UUID):
    cur.execute(
        "SELECT * FROM public.school_pei_diretriz_base WHERE id = %s",
        (str(pei_id),),
    )
    return cur.fetchone()


def _load_campos(cur: Any, pei_id: uuid.UUID) -> list:
    cur.execute(
        """
        SELECT *
        FROM public.school_pei_campo_experiencia
        WHERE pei_diretriz_base_id = %s
        ORDER BY campo_experiencia, created_at, id
        """,
        (str(pei_id),),
    )
    return list(cur.fetchall())


@bp.get("/api/instituicoes/<instituicao_id>/pei/planos-gerais")
def listar_planos_gerais(instituicao_id: str):
    """Lista resumida — ativos e inativos."""
    parsed = _parse_uuid(instituicao_id, "instituição")
    if not isinstance(parsed, uuid.UUID):
        return parsed

    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            if not _instituicao_exists(cur, parsed):
                return jsonify({"error": "Instituição não encontrada"}), 404
            cur.execute(
                """
                SELECT id, tipo_neurodivergencia, diretriz, ativo
                FROM public.school_pei_diretriz_base
                WHERE instituicao_id = %s
                ORDER BY ativo DESC, tipo_neurodivergencia
                """,
                (str(parsed),),
            )
            rows = cur.fetchall()

    return jsonify([_serialize_list_item(r) for r in rows])


@bp.get("/api/pei/planos-gerais/<pei_id>")
def obter_plano_geral(pei_id: str):
    parsed = _parse_uuid(pei_id, "plano geral")
    if not isinstance(parsed, uuid.UUID):
        return parsed

    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            row = _load_plano(cur, parsed)
            if not row:
                return jsonify({"error": "Plano geral não encontrado"}), 404
            campos = _load_campos(cur, parsed)

    return jsonify(_serialize_detail(row, campos))


@bp.post("/api/instituicoes/<instituicao_id>/pei/planos-gerais")
def criar_plano_geral(instituicao_id: str):
    parsed = _parse_uuid(instituicao_id, "instituição")
    if not isinstance(parsed, uuid.UUID):
        return parsed

    body = request.get_json(silent=True) or {}
    tipo = _text_or_none(body.get("tipo_neurodivergencia"))
    if not tipo:
        return jsonify({"error": "Informe o tipo de neurodivergência"}), 400

    diretriz = _text_or_none(body.get("diretriz")) or "—"
    area = {col: _text_or_none(body.get(col)) for col in AREA_GERAL_COLS}

    try:
        with get_conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                if not _instituicao_exists(cur, parsed):
                    return jsonify({"error": "Instituição não encontrada"}), 404
                cur.execute(
                    """
                    INSERT INTO public.school_pei_diretriz_base (
                        instituicao_id,
                        tipo_neurodivergencia,
                        diretriz,
                        capacidades_interesses,
                        necessidades,
                        metas_prazos,
                        recursos_estrategias,
                        profissionais_envolvidos
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING *
                    """,
                    (
                        str(parsed),
                        tipo,
                        diretriz,
                        area["capacidades_interesses"],
                        area["necessidades"],
                        area["metas_prazos"],
                        area["recursos_estrategias"],
                        area["profissionais_envolvidos"],
                    ),
                )
                row = cur.fetchone()
    except pg_errors.UniqueViolation:
        return (
            jsonify(
                {
                    "error": (
                        "Já existe um plano geral para este tipo de neurodivergência "
                        "nesta instituição"
                    )
                }
            ),
            409,
        )

    return jsonify(_serialize_detail(row, [])), 201


@bp.put("/api/pei/planos-gerais/<pei_id>")
def atualizar_plano_geral(pei_id: str):
    parsed = _parse_uuid(pei_id, "plano geral")
    if not isinstance(parsed, uuid.UUID):
        return parsed

    body = request.get_json(silent=True) or {}

    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            row = _load_plano(cur, parsed)
            if not row:
                return jsonify({"error": "Plano geral não encontrado"}), 404

            tipo = (
                _text_or_none(body.get("tipo_neurodivergencia"))
                if "tipo_neurodivergencia" in body
                else row["tipo_neurodivergencia"]
            )
            if not tipo:
                return jsonify({"error": "Informe o tipo de neurodivergência"}), 400

            diretriz = (
                _text_or_none(body.get("diretriz"))
                if "diretriz" in body
                else row["diretriz"]
            ) or "—"

            area = {}
            for col in AREA_GERAL_COLS:
                if col in body:
                    area[col] = _text_or_none(body.get(col))
                else:
                    area[col] = row.get(col)

            ativo = bool(body.get("ativo")) if "ativo" in body else bool(row["ativo"])

            try:
                cur.execute(
                    """
                    UPDATE public.school_pei_diretriz_base
                    SET
                        tipo_neurodivergencia = %s,
                        diretriz = %s,
                        capacidades_interesses = %s,
                        necessidades = %s,
                        metas_prazos = %s,
                        recursos_estrategias = %s,
                        profissionais_envolvidos = %s,
                        ativo = %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                    RETURNING *
                    """,
                    (
                        tipo,
                        diretriz,
                        area["capacidades_interesses"],
                        area["necessidades"],
                        area["metas_prazos"],
                        area["recursos_estrategias"],
                        area["profissionais_envolvidos"],
                        ativo,
                        str(parsed),
                    ),
                )
                updated = cur.fetchone()
            except pg_errors.UniqueViolation:
                return (
                    jsonify(
                        {
                            "error": (
                                "Já existe um plano geral para este tipo de "
                                "neurodivergência nesta instituição"
                            )
                        }
                    ),
                    409,
                )

            campos = _load_campos(cur, parsed)

    return jsonify(_serialize_detail(updated, campos))


@bp.post("/api/pei/planos-gerais/<pei_id>/campos-experiencia")
def criar_campo_experiencia(pei_id: str):
    parsed = _parse_uuid(pei_id, "plano geral")
    if not isinstance(parsed, uuid.UUID):
        return parsed

    body = request.get_json(silent=True) or {}
    campo = _text_or_none(body.get("campo_experiencia"))
    if campo not in CAMPOS_EXPERIENCIA:
        return (
            jsonify(
                {
                    "error": "Campo de experiência inválido",
                    "permitidos": list(CAMPOS_EXPERIENCIA),
                }
            ),
            400,
        )
    objetivo = _text_or_none(body.get("objetivo"))
    if not objetivo:
        return jsonify({"error": "Informe o objetivo"}), 400

    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            if not _load_plano(cur, parsed):
                return jsonify({"error": "Plano geral não encontrado"}), 404
            try:
                cur.execute(
                    """
                    INSERT INTO public.school_pei_campo_experiencia (
                        pei_diretriz_base_id,
                        campo_experiencia,
                        objetivo,
                        curriculo_habilidades,
                        estrategias_ensino,
                        prazo
                    )
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING *
                    """,
                    (
                        str(parsed),
                        campo,
                        objetivo,
                        _text_or_none(body.get("curriculo_habilidades")),
                        _text_or_none(body.get("estrategias_ensino")),
                        _text_or_none(body.get("prazo")),
                    ),
                )
                row = cur.fetchone()
            except pg_errors.CheckViolation:
                return jsonify({"error": "Campo de experiência inválido"}), 400

    return jsonify(_serialize_campo(row)), 201


@bp.put("/api/pei/campos-experiencia/<campo_id>")
def atualizar_campo_experiencia(campo_id: str):
    parsed = _parse_uuid(campo_id, "objetivo")
    if not isinstance(parsed, uuid.UUID):
        return parsed

    body = request.get_json(silent=True) or {}

    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM public.school_pei_campo_experiencia WHERE id = %s",
                (str(parsed),),
            )
            row = cur.fetchone()
            if not row:
                return jsonify({"error": "Objetivo não encontrado"}), 404

            campo = row["campo_experiencia"]
            if "campo_experiencia" in body:
                campo = _text_or_none(body.get("campo_experiencia"))
                if campo not in CAMPOS_EXPERIENCIA:
                    return (
                        jsonify(
                            {
                                "error": "Campo de experiência inválido",
                                "permitidos": list(CAMPOS_EXPERIENCIA),
                            }
                        ),
                        400,
                    )

            objetivo = (
                _text_or_none(body.get("objetivo"))
                if "objetivo" in body
                else row["objetivo"]
            )
            if not objetivo:
                return jsonify({"error": "Informe o objetivo"}), 400

            curriculo = (
                _text_or_none(body.get("curriculo_habilidades"))
                if "curriculo_habilidades" in body
                else row.get("curriculo_habilidades")
            )
            estrategias = (
                _text_or_none(body.get("estrategias_ensino"))
                if "estrategias_ensino" in body
                else row.get("estrategias_ensino")
            )
            prazo = (
                _text_or_none(body.get("prazo")) if "prazo" in body else row.get("prazo")
            )
            ativo = bool(body.get("ativo")) if "ativo" in body else bool(row["ativo"])

            cur.execute(
                """
                UPDATE public.school_pei_campo_experiencia
                SET
                    campo_experiencia = %s,
                    objetivo = %s,
                    curriculo_habilidades = %s,
                    estrategias_ensino = %s,
                    prazo = %s,
                    ativo = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
                RETURNING *
                """,
                (
                    campo,
                    objetivo,
                    curriculo,
                    estrategias,
                    prazo,
                    ativo,
                    str(parsed),
                ),
            )
            updated = cur.fetchone()

    return jsonify(_serialize_campo(updated))

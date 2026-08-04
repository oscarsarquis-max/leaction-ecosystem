"""Editor Pedagógico — metodologias alinhadas ao inove4us do professor.

Dicotomia pública (mesmo léxico do B2C):
  • Dia a Dia · ciclo rápido
  • Desafio · método inove4us

A escola adapta sem alterar a referência inove4us.
Auth real ainda não existe: instituicao_id na URL (interino).
"""
from __future__ import annotations

import re
import unicodedata
import uuid
from typing import Any

from flask import Blueprint, jsonify, request
from psycopg2.extras import Json, RealDictCursor

from db import get_conn

bp = Blueprint("metodologias", __name__)

# Famílias públicas — mesmas etiquetas do app do professor.
FAMILIAS = ("Indutivas", "Agilidade", "Contextuais", "Dedutivas")

VETOR_DIA = "dia_a_dia"
VETOR_DESAFIO = "desafio"


def _parse_uuid(value: str, label: str):
    try:
        return uuid.UUID(str(value))
    except (ValueError, TypeError, AttributeError):
        return jsonify({"error": f"Identificador de {label} inválido"}), 400


def _slug(nome: str) -> str:
    raw = unicodedata.normalize("NFKD", nome or "")
    raw = "".join(c for c in raw if not unicodedata.combining(c))
    raw = re.sub(r"[^a-z0-9]+", "_", raw.lower().strip()).strip("_")
    return raw or "metodologia"


def _instituicao_exists(cur: Any, instituicao_id: uuid.UUID) -> bool:
    cur.execute(
        "SELECT 1 FROM public.school_instituicoes WHERE id = %s",
        (str(instituicao_id),),
    )
    return cur.fetchone() is not None


def _normalize_passos(raw: Any) -> list[Any] | None:
    if raw is None:
        return None
    if not isinstance(raw, list):
        raise ValueError("O roteiro deve ser uma lista de etapas")
    out: list[Any] = []
    for item in raw:
        if isinstance(item, str):
            text = item.strip()
            if text:
                out.append(
                    {
                        "titulo": text[:120],
                        "objetivo": "",
                        "mecanica_passo_a_passo": text,
                        "como_executar_detalhado": text,
                        "dica_de_facilitacao": "",
                        "duracao_minutos": None,
                    }
                )
        elif isinstance(item, dict):
            titulo = str(item.get("titulo") or item.get("titulo_do_card") or "").strip()
            mec = str(
                item.get("mecanica_passo_a_passo")
                or item.get("passo")
                or item.get("texto")
                or ""
            ).strip()
            if not titulo and not mec:
                continue
            out.append(
                {
                    "titulo": titulo or (mec[:120] if mec else "Etapa"),
                    "objetivo": str(item.get("objetivo") or "").strip(),
                    "mecanica_passo_a_passo": mec or titulo,
                    "como_executar_detalhado": str(
                        item.get("como_executar_detalhado") or mec or titulo
                    ).strip(),
                    "dica_de_facilitacao": str(item.get("dica_de_facilitacao") or "").strip(),
                    "duracao_minutos": item.get("duracao_minutos"),
                }
            )
        else:
            raise ValueError("Cada etapa do roteiro deve ser um texto ou um bloco completo")
    return out


def _fonte_publica(origem: str | None) -> str:
    return "da_escola" if origem == "escola" else "referencia_inove4us"


def _row_merged(row: dict[str, Any]) -> dict[str, Any]:
    passos_ref = row.get("passos_execucao") or []
    passos_adapt = row.get("passos_customizados")
    origem = row.get("origem") or "padrao"
    return {
        "metodologia_id": str(row["metodologia_catalogo_id"]),
        "metodologia_catalogo_id": str(row["metodologia_catalogo_id"]),
        "codigo": row.get("codigo"),
        "nome": row["nome"],
        "familia": row.get("categoria") or "Indutivas",
        "categoria": row.get("categoria") or "Indutivas",
        "descricao": row.get("descricao"),
        "fonte": _fonte_publica(origem),
        "origem": origem,
        "vetores": {
            "dia_a_dia": bool(row.get("vetor_dia_a_dia", True)),
            "desafio": bool(row.get("vetor_desafio", True)),
        },
        "roteiro_referencia": passos_ref,
        "passos_execucao": passos_ref,
        "roteiro_adaptado": passos_adapt,
        "passos_customizados": passos_adapt,
        "roteiro_em_uso": passos_adapt if passos_adapt is not None else passos_ref,
        "passos_efetivos": passos_adapt if passos_adapt is not None else passos_ref,
        "orientacao_coordenacao": row.get("diretriz_customizada"),
        "diretriz_customizada": row.get("diretriz_customizada"),
        "disponivel_dia_a_dia": bool(row["disponivel_dia_a_dia"]),
        "disponivel_desafio": bool(row["disponivel_desafio"]),
        "is_active": bool(row["is_active"]),
        "adaptada_pela_escola": bool(row["tem_override"]),
    }


_LIST_SQL = """
SELECT
    c.id AS metodologia_catalogo_id,
    c.codigo,
    c.nome,
    c.categoria,
    c.descricao,
    c.origem,
    c.passos_execucao,
    COALESCE(c.vetor_dia_a_dia, TRUE) AS vetor_dia_a_dia,
    COALESCE(c.vetor_desafio, TRUE) AS vetor_desafio,
    cfg.passos_customizados,
    cfg.diretriz_customizada,
    COALESCE(cfg.is_active, TRUE) AS is_active,
    COALESCE(cfg.ativo_dia_a_dia, TRUE) AS disponivel_dia_a_dia,
    COALESCE(cfg.ativo_desafio, TRUE) AS disponivel_desafio,
    (cfg.id IS NOT NULL) AS tem_override
FROM public.school_metodologias_catalogo c
LEFT JOIN public.school_metodologia_config cfg
    ON cfg.metodologia_catalogo_id = c.id
   AND cfg.instituicao_id = %s
WHERE c.ativo = TRUE
  AND (
        c.origem = 'padrao'
        OR (c.origem = 'escola' AND c.instituicao_origem_id = %s)
      )
ORDER BY c.categoria, c.nome
"""

_ONE_SQL = _LIST_SQL.replace(
    "ORDER BY c.categoria, c.nome",
    "AND c.id = %s\nORDER BY c.categoria, c.nome",
)


@bp.get("/api/metodologias-catalogo")
def list_catalogo():
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id, codigo, nome, categoria, descricao, passos_execucao,
                       ativo, origem, vetor_dia_a_dia, vetor_desafio
                FROM public.school_metodologias_catalogo
                WHERE ativo = TRUE AND origem = 'padrao'
                ORDER BY categoria, nome
                """
            )
            rows = cur.fetchall()
    return jsonify(
        [
            {
                "id": str(r["id"]),
                "codigo": r.get("codigo"),
                "nome": r["nome"],
                "familia": r.get("categoria"),
                "categoria": r.get("categoria"),
                "descricao": r.get("descricao"),
                "roteiro_referencia": r.get("passos_execucao") or [],
                "passos_execucao": r.get("passos_execucao") or [],
                "ativo": bool(r["ativo"]),
                "fonte": "referencia_inove4us",
                "vetores": {
                    "dia_a_dia": bool(r.get("vetor_dia_a_dia", True)),
                    "desafio": bool(r.get("vetor_desafio", True)),
                },
            }
            for r in rows
        ]
    )


@bp.get("/api/instituicoes/<instituicao_id>/metodologias")
def list_instituicao_metodologias(instituicao_id: str):
    parsed = _parse_uuid(instituicao_id, "instituição")
    if not isinstance(parsed, uuid.UUID):
        return parsed

    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            if not _instituicao_exists(cur, parsed):
                return jsonify({"error": "Instituição não encontrada"}), 404
            cur.execute(_LIST_SQL, (str(parsed), str(parsed)))
            rows = cur.fetchall()
    return jsonify([_row_merged(r) for r in rows])


@bp.post("/api/instituicoes/<instituicao_id>/metodologias")
def create_instituicao_metodologia(instituicao_id: str):
    """Cria metodologia da escola. Não altera a referência inove4us."""
    parsed = _parse_uuid(instituicao_id, "instituição")
    if not isinstance(parsed, uuid.UUID):
        return parsed

    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        return jsonify({"error": "Dados inválidos"}), 400

    nome = str(body.get("nome") or "").strip()
    if not nome:
        return jsonify({"error": "Informe o nome da metodologia"}), 400

    categoria = str(body.get("categoria") or body.get("familia") or "Indutivas").strip()
    if categoria not in FAMILIAS:
        return jsonify(
            {"error": f"Família deve ser uma de: {', '.join(FAMILIAS)}"}
        ), 400

    descricao = str(body.get("descricao") or "").strip() or None
    try:
        passos = _normalize_passos(
            body.get("passos_execucao")
            or body.get("roteiro")
            or body.get("passos")
            or []
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    if not passos:
        return jsonify({"error": "Inclua ao menos uma etapa no roteiro"}), 400

    ativo_dia = body.get("disponivel_dia_a_dia", body.get("ativo_dia_a_dia", True))
    ativo_des = body.get("disponivel_desafio", body.get("ativo_desafio", True))
    if not isinstance(ativo_dia, bool) or not isinstance(ativo_des, bool):
        return jsonify(
            {"error": "Disponibilidade no Dia a Dia e no Desafio deve ser sim ou não"}
        ), 400

    codigo = f"escola_{_slug(nome)}_{uuid.uuid4().hex[:8]}"

    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            if not _instituicao_exists(cur, parsed):
                return jsonify({"error": "Instituição não encontrada"}), 404

            cur.execute(
                """
                SELECT 1 FROM public.school_metodologias_catalogo
                WHERE origem = 'padrao' AND lower(nome) = lower(%s)
                """,
                (nome,),
            )
            if cur.fetchone():
                return jsonify(
                    {
                        "error": "Já existe uma metodologia com este nome na referência "
                        "inove4us. Escolha outro nome ou adapte a referência existente."
                    }
                ), 409

            cur.execute(
                """
                SELECT 1 FROM public.school_metodologias_catalogo
                WHERE origem = 'escola'
                  AND instituicao_origem_id = %s
                  AND lower(nome) = lower(%s)
                """,
                (str(parsed), nome),
            )
            if cur.fetchone():
                return jsonify(
                    {"error": "A escola já registrou uma metodologia com este nome"}
                ), 409

            cur.execute(
                """
                INSERT INTO public.school_metodologias_catalogo (
                    codigo, nome, categoria, descricao, passos_execucao,
                    ativo, origem, instituicao_origem_id,
                    vetor_dia_a_dia, vetor_desafio
                )
                VALUES (%s, %s, %s, %s, %s, TRUE, 'escola', %s, %s, %s)
                RETURNING id
                """,
                (
                    codigo,
                    nome,
                    categoria,
                    descricao,
                    Json(passos),
                    str(parsed),
                    ativo_dia,
                    ativo_des,
                ),
            )
            new_id = cur.fetchone()["id"]

            cur.execute(
                """
                INSERT INTO public.school_metodologia_config (
                    instituicao_id, metodologia_catalogo_id,
                    is_active, ativo_dia_a_dia, ativo_desafio
                )
                VALUES (%s, %s, TRUE, %s, %s)
                """,
                (str(parsed), str(new_id), ativo_dia, ativo_des),
            )

            cur.execute(_ONE_SQL, (str(parsed), str(parsed), str(new_id)))
            row = cur.fetchone()

    return jsonify(_row_merged(row)), 201


@bp.put("/api/instituicoes/<instituicao_id>/metodologias/<metodologia_catalogo_id>")
def upsert_instituicao_metodologia(instituicao_id: str, metodologia_catalogo_id: str):
    parsed_inst = _parse_uuid(instituicao_id, "instituição")
    if not isinstance(parsed_inst, uuid.UUID):
        return parsed_inst
    parsed_met = _parse_uuid(metodologia_catalogo_id, "metodologia")
    if not isinstance(parsed_met, uuid.UUID):
        return parsed_met

    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        return jsonify({"error": "Dados inválidos"}), 400

    keys = (
        "diretriz_customizada",
        "orientacao_coordenacao",
        "is_active",
        "passos_customizados",
        "roteiro_adaptado",
        "disponivel_dia_a_dia",
        "disponivel_desafio",
        "ativo_dia_a_dia",
        "ativo_desafio",
    )
    if not any(k in body for k in keys):
        return jsonify(
            {
                "error": "Informe orientação, roteiro adaptado, disponibilidade "
                "no Dia a Dia / Desafio ou ativação na escola"
            }
        ), 400

    if "is_active" in body and not isinstance(body["is_active"], bool):
        return jsonify({"error": "Ativação na escola deve ser sim ou não"}), 400

    for k in (
        "disponivel_dia_a_dia",
        "disponivel_desafio",
        "ativo_dia_a_dia",
        "ativo_desafio",
    ):
        if k in body and not isinstance(body[k], bool):
            return jsonify({"error": f"{k} deve ser sim ou não"}), 400

    if "diretriz_customizada" in body or "orientacao_coordenacao" in body:
        d = body.get("orientacao_coordenacao", body.get("diretriz_customizada"))
        if d is not None and not isinstance(d, str):
            return jsonify({"error": "A orientação deve ser um texto"}), 400

    passos_custom = None
    has_passos = "passos_customizados" in body or "roteiro_adaptado" in body
    if has_passos:
        raw_passos = body.get("roteiro_adaptado", body.get("passos_customizados"))
        try:
            if raw_passos is None:
                passos_custom = None
            else:
                passos_custom = _normalize_passos(raw_passos)
                if passos_custom is not None and len(passos_custom) == 0:
                    passos_custom = None
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400

    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            if not _instituicao_exists(cur, parsed_inst):
                return jsonify({"error": "Instituição não encontrada"}), 404

            cur.execute(
                """
                SELECT id, origem, instituicao_origem_id, ativo
                FROM public.school_metodologias_catalogo
                WHERE id = %s
                """,
                (str(parsed_met),),
            )
            cat = cur.fetchone()
            if not cat or not cat["ativo"]:
                return jsonify({"error": "Metodologia não encontrada"}), 404
            if cat["origem"] == "escola" and str(cat["instituicao_origem_id"]) != str(
                parsed_inst
            ):
                return jsonify(
                    {"error": "Esta metodologia não pertence a esta instituição"}
                ), 403

            cur.execute(
                """
                SELECT diretriz_customizada, is_active, passos_customizados,
                       ativo_dia_a_dia, ativo_desafio
                FROM public.school_metodologia_config
                WHERE instituicao_id = %s AND metodologia_catalogo_id = %s
                """,
                (str(parsed_inst), str(parsed_met)),
            )
            existing = cur.fetchone()

            if "orientacao_coordenacao" in body:
                diretriz_in = body["orientacao_coordenacao"]
            elif "diretriz_customizada" in body:
                diretriz_in = body["diretriz_customizada"]
            else:
                diretriz_in = None
            has_diretriz = (
                "orientacao_coordenacao" in body or "diretriz_customizada" in body
            )

            if "disponivel_dia_a_dia" in body:
                dia_in = body["disponivel_dia_a_dia"]
            elif "ativo_dia_a_dia" in body:
                dia_in = body["ativo_dia_a_dia"]
            else:
                dia_in = None
            has_dia = "disponivel_dia_a_dia" in body or "ativo_dia_a_dia" in body

            if "disponivel_desafio" in body:
                des_in = body["disponivel_desafio"]
            elif "ativo_desafio" in body:
                des_in = body["ativo_desafio"]
            else:
                des_in = None
            has_des = "disponivel_desafio" in body or "ativo_desafio" in body

            if existing:
                diretriz = (
                    diretriz_in if has_diretriz else existing["diretriz_customizada"]
                )
                is_active = (
                    body["is_active"] if "is_active" in body else bool(existing["is_active"])
                )
                passos_val = passos_custom if has_passos else existing["passos_customizados"]
                ativo_dia = dia_in if has_dia else bool(existing["ativo_dia_a_dia"])
                ativo_des = des_in if has_des else bool(existing["ativo_desafio"])
            else:
                diretriz = diretriz_in if has_diretriz else None
                is_active = body["is_active"] if "is_active" in body else True
                passos_val = passos_custom if has_passos else None
                ativo_dia = dia_in if has_dia else True
                ativo_des = des_in if has_des else True

            if isinstance(diretriz, str):
                diretriz = diretriz.strip() or None

            cur.execute(
                """
                INSERT INTO public.school_metodologia_config (
                    instituicao_id,
                    metodologia_catalogo_id,
                    diretriz_customizada,
                    passos_customizados,
                    is_active,
                    ativo_dia_a_dia,
                    ativo_desafio
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (instituicao_id, metodologia_catalogo_id)
                DO UPDATE SET
                    diretriz_customizada = EXCLUDED.diretriz_customizada,
                    passos_customizados = EXCLUDED.passos_customizados,
                    is_active = EXCLUDED.is_active,
                    ativo_dia_a_dia = EXCLUDED.ativo_dia_a_dia,
                    ativo_desafio = EXCLUDED.ativo_desafio,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    str(parsed_inst),
                    str(parsed_met),
                    diretriz,
                    Json(passos_val) if passos_val is not None else None,
                    is_active,
                    ativo_dia,
                    ativo_des,
                ),
            )

            if cat["origem"] == "escola" and has_passos and passos_custom is not None:
                cur.execute(
                    """
                    UPDATE public.school_metodologias_catalogo
                    SET passos_execucao = %s,
                        vetor_dia_a_dia = %s,
                        vetor_desafio = %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s AND origem = 'escola'
                    """,
                    (Json(passos_custom), ativo_dia, ativo_des, str(parsed_met)),
                )

            cur.execute(_ONE_SQL, (str(parsed_inst), str(parsed_inst), str(parsed_met)))
            row = cur.fetchone()

    if not row:
        return jsonify({"error": "Não foi possível confirmar o salvamento"}), 500

    merged = _row_merged(row)
    # Top-down S2S: coordenador editou metodologia → B2C sobrescreve canônico na IA.
    try:
        from b2c_integration_service import dispatch_methodology_override_updated

        dispatch_methodology_override_updated(
            instituicao_id=str(parsed_inst),
            metodologia_nome=str(merged.get("nome") or ""),
            diretriz_customizada=merged.get("diretriz_customizada"),
        )
    except Exception as exc:
        # Falha de ponte não bloqueia o save local do Editor Pedagógico.
        print(f"[metodologias] dispatch B2C falhou: {exc}", flush=True)

    return jsonify(merged)

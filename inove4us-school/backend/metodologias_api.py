"""Editor Pedagógico — metodologias alinhadas ao inove4us do professor.

Especialização por instituição: school_metodologias_org
  • Versão da Escola (passos_customizados TEXT)
  • ativo_dia_a_dia / ativo_desafio
  • uso_estrelas (1–3)

Auth real ainda não existe: instituicao_id na URL (interino).
"""
from __future__ import annotations

import os
import re
import unicodedata
import uuid
from typing import Any

from flask import Blueprint, jsonify, request, session
from psycopg2.extras import Json, RealDictCursor

from db import get_conn

bp = Blueprint("metodologias", __name__)

FAMILIAS = ("Indutivas", "Agilidade", "Contextuais", "Dedutivas")


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


def _dev_instituicao_id() -> str:
    user = session.get("school_gestor") or {}
    return str(
        user.get("instituicao_id")
        or os.getenv("DEV_INSTITUICAO_ID")
        or "a1111111-1111-4111-8111-111111111111"
    ).strip()


def _normalize_passos(raw: Any) -> list[Any] | None:
    if raw is None:
        return None
    if isinstance(raw, str):
        lines = [l.strip() for l in raw.split("\n") if l.strip()]
        if not lines:
            return None
        return [
            {
                "titulo": line[:120],
                "objetivo": "",
                "mecanica_passo_a_passo": line,
                "como_executar_detalhado": line,
                "dica_de_facilitacao": "",
                "duracao_minutos": None,
            }
            for line in lines
        ]
    if not isinstance(raw, list):
        raise ValueError("O roteiro deve ser um texto ou uma lista de etapas")
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
    return out or None


def _passos_to_text(passos: Any) -> str:
    if passos is None:
        return ""
    if isinstance(passos, str):
        return passos.strip()
    if not isinstance(passos, list):
        return str(passos).strip()
    lines: list[str] = []
    for p in passos:
        if isinstance(p, str):
            t = p.strip()
            if t:
                lines.append(t)
            continue
        if not isinstance(p, dict):
            continue
        titulo = str(p.get("titulo") or "").strip()
        mec = str(
            p.get("mecanica_passo_a_passo") or p.get("como_executar_detalhado") or ""
        ).strip()
        if titulo and mec and titulo != mec:
            lines.append(f"{titulo}: {mec}")
        else:
            line = titulo or mec
            if line:
                lines.append(line)
    return "\n".join(lines)


def _estrelas_from_count(n: Any) -> int:
    """0 sugestões → 0; 1 → 1; 2 → 2; 3+ → 3."""
    try:
        count = int(n or 0)
    except (TypeError, ValueError):
        count = 0
    if count <= 0:
        return 0
    return min(3, count)


def _fonte_publica(origem: str | None) -> str:
    return "da_escola" if origem == "escola" else "referencia_inove4us"


def _row_merged(row: dict[str, Any]) -> dict[str, Any]:
    passos_ref = row.get("passos_execucao") or []
    raw_custom = row.get("passos_customizados")
    versao = (raw_custom or "").strip() if raw_custom is not None else ""
    tem_override = bool(row.get("tem_override"))
    is_customizado = bool(tem_override and versao)
    origem = row.get("origem") or "padrao"
    texto_canonico = _passos_to_text(passos_ref)
    updated_at = row.get("org_updated_at") or row.get("updated_at")
    if hasattr(updated_at, "isoformat"):
        updated_at_iso = updated_at.isoformat()
    else:
        updated_at_iso = str(updated_at) if updated_at else None
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
        "texto_canonico": texto_canonico,
        # Persistência org: vazio se a escola ainda não adaptou
        "versao_escola": versao if is_customizado else "",
        "passos_customizados": versao if is_customizado else "",
        "roteiro_adaptado": versao if is_customizado else "",
        "roteiro_em_uso": versao if is_customizado else texto_canonico,
        "is_customizado": is_customizado,
        "updated_at": updated_at_iso if is_customizado else None,
        "disponivel_dia_a_dia": bool(row["disponivel_dia_a_dia"]),
        "disponivel_desafio": bool(row["disponivel_desafio"]),
        "ativo_dia_a_dia": bool(row["disponivel_dia_a_dia"]),
        "ativo_desafio": bool(row["disponivel_desafio"]),
        # Dinâmico: engajamento dos professores (curadoria), não o valor estático da org.
        "uso_estrelas": _estrelas_from_count(row.get("sugestoes_count")),
        "sugestoes_count": int(row.get("sugestoes_count") or 0),
        "is_active": bool(row["is_active"]),
        "adaptada_pela_escola": is_customizado,
        "tem_override_org": tem_override,
        "config_id": str(row["config_id"]) if row.get("config_id") else None,
        "org_id": str(row["org_id"]) if row.get("org_id") else None,
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
    org.passos_customizados,
    org.updated_at AS org_updated_at,
    COALESCE(org.is_active, TRUE) AS is_active,
    COALESCE(org.ativo_dia_a_dia, TRUE) AS disponivel_dia_a_dia,
    COALESCE(org.ativo_desafio, TRUE) AS disponivel_desafio,
    COALESCE(cur.sugestoes_count, 0) AS sugestoes_count,
    (org.id IS NOT NULL) AS tem_override
FROM public.school_metodologias_catalogo c
LEFT JOIN public.school_metodologias_org org
    ON org.metodologia_id_canonica = c.id
   AND org.instituicao_id = %s
LEFT JOIN (
    SELECT
        LOWER(TRIM(metodologia_nome)) AS nome_key,
        COUNT(*)::int AS sugestoes_count
    FROM public.school_curadoria_metodologias
    WHERE instituicao_id = %s
      AND status_analise IN (
          'pendente', 'em_analise', 'incorporada', 'incorporado'
      )
    GROUP BY LOWER(TRIM(metodologia_nome))
) cur
    ON cur.nome_key = LOWER(TRIM(c.nome))
WHERE c.ativo = TRUE
  AND (
        c.origem = 'padrao'
        OR (c.origem = 'escola' AND c.instituicao_origem_id = %s)
      )
ORDER BY c.categoria, c.nome
"""

_ONE_SQL = """
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
    org.passos_customizados,
    org.updated_at AS org_updated_at,
    COALESCE(org.is_active, TRUE) AS is_active,
    COALESCE(org.ativo_dia_a_dia, TRUE) AS disponivel_dia_a_dia,
    COALESCE(org.ativo_desafio, TRUE) AS disponivel_desafio,
    COALESCE(cur.sugestoes_count, 0) AS sugestoes_count,
    (org.id IS NOT NULL) AS tem_override,
    org.id AS org_id,
    cfg.id AS config_id
FROM public.school_metodologias_catalogo c
LEFT JOIN public.school_metodologias_org org
    ON org.metodologia_id_canonica = c.id
   AND org.instituicao_id = %s
LEFT JOIN public.school_metodologia_config cfg
    ON cfg.metodologia_catalogo_id = c.id
   AND cfg.instituicao_id = %s
LEFT JOIN (
    SELECT
        LOWER(TRIM(metodologia_nome)) AS nome_key,
        COUNT(*)::int AS sugestoes_count
    FROM public.school_curadoria_metodologias
    WHERE instituicao_id = %s
      AND status_analise IN (
          'pendente', 'em_analise', 'incorporada', 'incorporado'
      )
    GROUP BY LOWER(TRIM(metodologia_nome))
) cur
    ON cur.nome_key = LOWER(TRIM(c.nome))
WHERE c.ativo = TRUE
  AND c.id = %s
  AND (
        c.origem = 'padrao'
        OR (c.origem = 'escola' AND c.instituicao_origem_id = %s)
      )
"""


def _upsert_org(
    cur: Any,
    *,
    instituicao_id: str,
    metodologia_id: str,
    versao_escola: str | None,
    ativo_dia: bool,
    ativo_des: bool,
    is_active: bool,
    uso_estrelas: int,
) -> None:
    cur.execute(
        """
        INSERT INTO public.school_metodologias_org (
            instituicao_id,
            metodologia_id_canonica,
            passos_customizados,
            ativo_dia_a_dia,
            ativo_desafio,
            uso_estrelas,
            is_active
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (instituicao_id, metodologia_id_canonica)
        DO UPDATE SET
            passos_customizados = EXCLUDED.passos_customizados,
            ativo_dia_a_dia = EXCLUDED.ativo_dia_a_dia,
            ativo_desafio = EXCLUDED.ativo_desafio,
            uso_estrelas = EXCLUDED.uso_estrelas,
            is_active = EXCLUDED.is_active,
            updated_at = CURRENT_TIMESTAMP
        """,
        (
            instituicao_id,
            metodologia_id,
            versao_escola,
            ativo_dia,
            ativo_des,
            uso_estrelas,
            is_active,
        ),
    )
    # Espelho legado (curadoria / B2C ainda leem school_metodologia_config)
    passos_json = _normalize_passos(versao_escola) if versao_escola else None
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
            instituicao_id,
            metodologia_id,
            versao_escola,
            Json(passos_json) if passos_json is not None else None,
            is_active,
            ativo_dia,
            ativo_des,
        ),
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
                "texto_canonico": _passos_to_text(r.get("passos_execucao")),
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
            cur.execute(_LIST_SQL, (str(parsed), str(parsed), str(parsed)))
            rows = cur.fetchall()
    return jsonify([_row_merged(r) for r in rows])


@bp.get("/api/pedagogico/metodologias")
def list_pedagogico_metodologias():
    """Alias do Editor Pedagógico — usa instituição da sessão / DEV."""
    return list_instituicao_metodologias(_dev_instituicao_id())


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
            or body.get("versao_escola")
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
    versao_txt = _passos_to_text(passos)

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

            _upsert_org(
                cur,
                instituicao_id=str(parsed),
                metodologia_id=str(new_id),
                versao_escola=versao_txt,
                ativo_dia=ativo_dia,
                ativo_des=ativo_des,
                is_active=True,
                uso_estrelas=1,
            )

            cur.execute(
                _ONE_SQL,
                (
                    str(parsed),
                    str(parsed),
                    str(parsed),
                    str(new_id),
                    str(parsed),
                ),
            )
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
        "versao_escola",
        "passos_customizados",
        "roteiro_adaptado",
        "is_active",
        "disponivel_dia_a_dia",
        "disponivel_desafio",
        "ativo_dia_a_dia",
        "ativo_desafio",
        "uso_estrelas",
        "diretriz_customizada",
        "orientacao_coordenacao",
    )
    if not any(k in body for k in keys):
        return jsonify(
            {
                "error": "Informe versão da escola, disponibilidade "
                "no Dia a Dia / Desafio ou ativação"
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
                SELECT passos_customizados, is_active, ativo_dia_a_dia, ativo_desafio,
                       uso_estrelas
                FROM public.school_metodologias_org
                WHERE instituicao_id = %s AND metodologia_id_canonica = %s
                """,
                (str(parsed_inst), str(parsed_met)),
            )
            existing = cur.fetchone()

            has_versao = any(
                k in body
                for k in (
                    "versao_escola",
                    "passos_customizados",
                    "roteiro_adaptado",
                    "diretriz_customizada",
                    "orientacao_coordenacao",
                )
            )
            if has_versao:
                raw_v = body.get(
                    "versao_escola",
                    body.get(
                        "passos_customizados",
                        body.get(
                            "roteiro_adaptado",
                            body.get(
                                "orientacao_coordenacao",
                                body.get("diretriz_customizada"),
                            ),
                        ),
                    ),
                )
                if raw_v is None:
                    versao = None
                elif isinstance(raw_v, str):
                    versao = raw_v.strip() or None
                else:
                    try:
                        versao = _passos_to_text(_normalize_passos(raw_v)) or None
                    except ValueError as exc:
                        return jsonify({"error": str(exc)}), 400
            else:
                versao = (
                    (existing["passos_customizados"] or None) if existing else None
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
                is_active = (
                    body["is_active"] if "is_active" in body else bool(existing["is_active"])
                )
                ativo_dia = dia_in if has_dia else bool(existing["ativo_dia_a_dia"])
                ativo_des = des_in if has_des else bool(existing["ativo_desafio"])
            else:
                is_active = body["is_active"] if "is_active" in body else True
                ativo_dia = dia_in if has_dia else True
                ativo_des = des_in if has_des else True

            _upsert_org(
                cur,
                instituicao_id=str(parsed_inst),
                metodologia_id=str(parsed_met),
                versao_escola=versao,
                ativo_dia=ativo_dia,
                ativo_des=ativo_des,
                is_active=is_active,
                uso_estrelas=1,
            )

            if cat["origem"] == "escola" and has_versao and versao:
                passos_json = _normalize_passos(versao)
                cur.execute(
                    """
                    UPDATE public.school_metodologias_catalogo
                    SET passos_execucao = %s,
                        vetor_dia_a_dia = %s,
                        vetor_desafio = %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s AND origem = 'escola'
                    """,
                    (Json(passos_json), ativo_dia, ativo_des, str(parsed_met)),
                )

            cur.execute(
                _ONE_SQL,
                (
                    str(parsed_inst),
                    str(parsed_inst),
                    str(parsed_inst),
                    str(parsed_met),
                    str(parsed_inst),
                ),
            )
            row = cur.fetchone()

    if not row:
        return jsonify({"error": "Não foi possível confirmar o salvamento"}), 500

    merged = _row_merged(row)
    try:
        from b2c_integration_service import dispatch_methodology_override_updated

        updated_at = merged.get("updated_at")
        versao_ts = None
        if updated_at:
            try:
                from datetime import datetime

                raw = str(updated_at).replace("Z", "+00:00")
                versao_ts = int(datetime.fromisoformat(raw).timestamp())
            except Exception:
                versao_ts = None

        dispatch_methodology_override_updated(
            instituicao_id=str(parsed_inst),
            metodologia_nome=str(merged.get("nome") or ""),
            metodologia_codigo=merged.get("codigo"),
            diretriz_customizada=merged.get("versao_escola"),
            disponivel_dia_a_dia=bool(merged.get("disponivel_dia_a_dia", True)),
            disponivel_desafio=bool(merged.get("disponivel_desafio", True)),
            is_active=bool(merged.get("is_active", True)),
            atualizado_em=updated_at,
            versao=versao_ts,
            origem_config_school_id=merged.get("config_id"),
        )
    except Exception as exc:
        print(f"[metodologias] dispatch B2C falhou: {exc}", flush=True)

    return jsonify(merged)


def _canonico_chave_esperada() -> str:
    return (os.getenv("SCHOOL_CANONICO_CHAVE") or "pedagogia").strip()


@bp.post("/api/pedagogico/desbloquear-canonico")
def desbloquear_canonico():
    """Valida palavra-chave para liberar edição do texto canônico (base da escola)."""
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        return jsonify({"error": "Dados inválidos"}), 400
    chave = str(body.get("chave") or body.get("palavra_chave") or "").strip()
    esperada = _canonico_chave_esperada()
    if not esperada or chave != esperada:
        return jsonify({"error": "Palavra-chave incorreta"}), 403
    return jsonify({"ok": True, "message": "Edição do texto canônico liberada."})


@bp.post("/api/pedagogico/metodologia/<metodologia_id>/adaptar-ia")
def adaptar_metodologia_ia(metodologia_id: str):
    """Mescla texto canônico + sugestão do professor via LLM → Versão da Escola."""
    parsed_met = _parse_uuid(metodologia_id, "metodologia")
    if not isinstance(parsed_met, uuid.UUID):
        return parsed_met

    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        return jsonify({"error": "Dados inválidos"}), 400

    inst_raw = (
        body.get("instituicao_id")
        or request.args.get("instituicao_id")
        or _dev_instituicao_id()
    )
    parsed_inst = _parse_uuid(str(inst_raw), "instituição")
    if not isinstance(parsed_inst, uuid.UUID):
        return parsed_inst

    sugestao = str(body.get("sugestao") or body.get("sugestao_professor") or "").strip()
    sugestoes_raw = body.get("sugestoes") or body.get("sugestoes_aceitas") or []
    if isinstance(sugestoes_raw, str):
        sugestoes_lista = [sugestoes_raw.strip()] if sugestoes_raw.strip() else []
    elif isinstance(sugestoes_raw, list):
        sugestoes_lista = [str(s).strip() for s in sugestoes_raw if str(s or "").strip()]
    else:
        sugestoes_lista = []
    if sugestao and sugestao not in sugestoes_lista:
        sugestoes_lista.append(sugestao)
    if not sugestoes_lista:
        return jsonify({"error": "Informe ao menos uma sugestão do professor"}), 400

    observacoes = str(
        body.get("observacoes_coordenacao")
        or body.get("observacao_coordenacao")
        or body.get("coordenacao")
        or ""
    ).strip()

    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            if not _instituicao_exists(cur, parsed_inst):
                return jsonify({"error": "Instituição não encontrada"}), 404
            cur.execute(
                """
                SELECT id, nome, passos_execucao
                FROM public.school_metodologias_catalogo
                WHERE id = %s AND ativo = TRUE
                """,
                (str(parsed_met),),
            )
            cat = cur.fetchone()
            if not cat:
                return jsonify({"error": "Metodologia não encontrada"}), 404

    canonico = str(body.get("texto_canonico") or "").strip() or _passos_to_text(
        cat.get("passos_execucao")
    )

    try:
        from school_llm import sintetizar_versao_escola

        versao = sintetizar_versao_escola(
            texto_canonico=canonico,
            observacoes_coordenacao=observacoes,
            sugestoes_aceitas=sugestoes_lista,
        )
    except Exception as exc:
        return jsonify({"error": f"Falha na IA: {exc}"}), 502

    return jsonify(
        {
            "success": True,
            "metodologia_id": str(parsed_met),
            "metodologia_nome": cat["nome"],
            "versao_escola": versao,
            "texto_canonico": canonico,
            "observacoes_coordenacao": observacoes,
            "sugestoes_aceitas": sugestoes_lista,
            "sugestao": sugestoes_lista[-1] if sugestoes_lista else sugestao,
        }
    )

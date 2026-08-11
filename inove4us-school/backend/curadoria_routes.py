"""Curadoria de Metodologias (bottom-up) — zona pedagógica.

GET  /api/pedagogico/curadoria/pendentes
POST /api/pedagogico/curadoria/<id>/incorporar
POST /api/pedagogico/curadoria/<id>/rejeitar

Nota de schema: especialização por instituição em school_metodologias_org
(migration 022). school_metodologia_config permanece como espelho legado.
"""
from __future__ import annotations

import os
import uuid
from functools import wraps
from typing import Any

from flask import Blueprint, jsonify, request, session
from psycopg2.extras import RealDictCursor

from auth_guards import SESSION_KEY, require_zona, resolve_instituicao_id
from db import get_conn

bp = Blueprint("curadoria_pedagogica", __name__)

STATUS_PENDENTE = "pendente"
STATUS_INCORPORADO = "incorporado"
STATUS_MANTIDO_AULA = "mantido_apenas_na_aula"


require_gestor = require_zona("pedagogico")


def _instituicao_id() -> str:
    resolved = resolve_instituicao_id()
    if isinstance(resolved, tuple):
        return ""
    return resolved


def _parse_uuid(value: Any):
    try:
        return uuid.UUID(str(value))
    except (ValueError, TypeError, AttributeError):
        return None


def _ensure_curadoria_schema(conn) -> None:
    """Amplia status + coluna is_customizado na config pedagógica."""
    with conn.cursor() as cur:
        cur.execute(
            """
            ALTER TABLE public.school_metodologia_config
                ADD COLUMN IF NOT EXISTS is_customizado BOOLEAN NOT NULL DEFAULT FALSE
            """
        )
        # Recria CHECK com status do fluxo bottom-up + legado.
        cur.execute(
            """
            ALTER TABLE public.school_curadoria_metodologias
                DROP CONSTRAINT IF EXISTS school_curadoria_metodologias_status_analise_check
            """
        )
        cur.execute(
            """
            ALTER TABLE public.school_curadoria_metodologias
                ADD CONSTRAINT school_curadoria_metodologias_status_analise_check
                CHECK (status_analise IN (
                    'pendente',
                    'em_analise',
                    'incorporada',
                    'incorporado',
                    'rejeitada',
                    'mantido_apenas_na_aula'
                ))
            """
        )


def _extract_teacher_text(sugestao: Any) -> str:
    if not isinstance(sugestao, dict):
        return ""
    direct = str(
        sugestao.get("teacher_adaptation_text")
        or sugestao.get("texto_sugestao")
        or sugestao.get("texto")
        or ""
    ).strip()
    if direct:
        return direct
    adaptations = sugestao.get("adaptations")
    if isinstance(adaptations, str):
        return adaptations.strip()
    if isinstance(adaptations, dict):
        for key in ("texto", "text", "descricao", "description", "resumo"):
            val = str(adaptations.get(key) or "").strip()
            if val:
                return val
    mesa = sugestao.get("mesa") if isinstance(sugestao.get("mesa"), dict) else {}
    return str(mesa.get("teacher_adaptation_text") or "").strip()


def _extract_professor_nome(sugestao: Any) -> str:
    if not isinstance(sugestao, dict):
        return ""
    for key in (
        "professor_nome",
        "nome_professor",
        "teacher_name",
        "professor",
        "autor",
    ):
        val = str(sugestao.get(key) or "").strip()
        if val:
            return val
    mesa = sugestao.get("mesa") if isinstance(sugestao.get("mesa"), dict) else {}
    for key in ("professor_nome", "teacher_name", "professor"):
        val = str(mesa.get(key) or "").strip()
        if val:
            return val
    return ""


def _extract_aula_contexto(sugestao: Any) -> str:
    if not isinstance(sugestao, dict):
        return ""
    for key in (
        "aula_contexto",
        "contexto_aula",
        "aula",
        "disciplina",
        "lesson_context",
    ):
        val = str(sugestao.get(key) or "").strip()
        if val:
            return val
    # Monta a partir de peças comuns do payload B2C
    disc = str(sugestao.get("disciplina") or sugestao.get("materia") or "").strip()
    tema = str(sugestao.get("tema") or sugestao.get("titulo_aula") or "").strip()
    turma = str(sugestao.get("turma") or sugestao.get("ano") or "").strip()
    parts = [p for p in (disc, tema, turma) if p]
    if parts:
        if len(parts) >= 2:
            return f"{parts[0]}: {parts[1]}" + (f" ({parts[2]})" if len(parts) > 2 else "")
        return parts[0]
    mesa = sugestao.get("mesa") if isinstance(sugestao.get("mesa"), dict) else {}
    return str(mesa.get("aula_contexto") or mesa.get("titulo") or "").strip()


def _serialize_item(row: dict[str, Any]) -> dict[str, Any]:
    sugestao = row.get("sugestao_professor_json") or {}
    if not isinstance(sugestao, dict):
        sugestao = {}
    professor = _extract_professor_nome(sugestao)
    aula = _extract_aula_contexto(sugestao)
    return {
        "id": str(row["id"]),
        "instituicao_id": str(row["instituicao_id"]),
        "metodologia_nome": row["metodologia_nome"],
        "plano_espelhado_id": str(row["plano_espelhado_id"])
        if row.get("plano_espelhado_id")
        else None,
        "status_analise": row["status_analise"],
        "teacher_adaptation_text": _extract_teacher_text(sugestao),
        "professor_nome": professor,
        "aula_contexto": aula,
        "metodologia_usada": str(
            sugestao.get("metodologia_usada") or row["metodologia_nome"] or ""
        ).strip(),
        "sugestao_professor_json": sugestao,
        "created_at": row["created_at"].isoformat() if row.get("created_at") else None,
        "updated_at": row["updated_at"].isoformat() if row.get("updated_at") else None,
    }


def _append_diretriz(existing: str | None, teacher_text: str) -> str:
    block = f"[Sugestão da trincheira]\n{teacher_text.strip()}"
    base = (existing or "").strip()
    if not base:
        return block
    if teacher_text.strip() in base:
        return base
    return f"{base}\n\n{block}"


@bp.get("/api/pedagogico/curadoria/pendentes")
@require_gestor
def list_pendentes():
    """Pendentes agrupados por metodologia_nome."""
    inst = _instituicao_id()
    metodologia_q = str(request.args.get("metodologia_nome") or "").strip()

    with get_conn() as conn:
        _ensure_curadoria_schema(conn)
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            if metodologia_q:
                cur.execute(
                    """
                    SELECT *
                    FROM public.school_curadoria_metodologias
                    WHERE instituicao_id = %s
                      AND status_analise = %s
                      AND LOWER(TRIM(metodologia_nome)) = LOWER(TRIM(%s))
                    ORDER BY created_at DESC
                    """,
                    (inst, STATUS_PENDENTE, metodologia_q),
                )
            else:
                cur.execute(
                    """
                    SELECT *
                    FROM public.school_curadoria_metodologias
                    WHERE instituicao_id = %s
                      AND status_analise = %s
                    ORDER BY metodologia_nome ASC, created_at DESC
                    """,
                    (inst, STATUS_PENDENTE),
                )
            rows = [_serialize_item(r) for r in cur.fetchall()]

    grouped: dict[str, list] = {}
    for item in rows:
        key = item["metodologia_nome"] or "Sem nome"
        grouped.setdefault(key, []).append(item)

    return jsonify(
        {
            "items": rows,
            "grouped": [
                {"metodologia_nome": nome, "items": items}
                for nome, items in grouped.items()
            ],
            "total": len(rows),
        }
    )


@bp.post("/api/pedagogico/curadoria/<item_id>/incorporar")
@require_gestor
def incorporar(item_id: str):
    inst = _instituicao_id()
    cid = _parse_uuid(item_id)
    if not cid:
        return jsonify({"error": "Identificador inválido"}), 400

    with get_conn() as conn:
        _ensure_curadoria_schema(conn)
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT *
                FROM public.school_curadoria_metodologias
                WHERE id = %s AND instituicao_id = %s
                LIMIT 1
                """,
                (str(cid), inst),
            )
            row = cur.fetchone()
            if not row:
                return jsonify({"error": "Sugestão não encontrada"}), 404
            if row["status_analise"] != STATUS_PENDENTE:
                return (
                    jsonify(
                        {
                            "error": "Sugestão já analisada",
                            "status_analise": row["status_analise"],
                        }
                    ),
                    409,
                )

            teacher_text = _extract_teacher_text(row.get("sugestao_professor_json"))
            if not teacher_text:
                return jsonify({"error": "Sugestão sem texto do professor"}), 400

            met_nome = str(row["metodologia_nome"] or "").strip()
            # Resolve metodologia no catálogo (match case-insensitive / slug).
            cur.execute(
                """
                SELECT c.id AS metodologia_catalogo_id, c.nome, c.codigo,
                       cfg.id AS config_id, cfg.diretriz_customizada,
                       COALESCE(cfg.ativo_dia_a_dia, TRUE) AS ativo_dia_a_dia,
                       COALESCE(cfg.ativo_desafio, TRUE) AS ativo_desafio
                FROM public.school_metodologias_catalogo c
                LEFT JOIN public.school_metodologia_config cfg
                  ON cfg.metodologia_catalogo_id = c.id
                 AND cfg.instituicao_id = %s
                WHERE LOWER(TRIM(c.nome)) = LOWER(TRIM(%s))
                   OR LOWER(REGEXP_REPLACE(c.nome, '[^a-z0-9]+', '', 'g'))
                      = LOWER(REGEXP_REPLACE(%s, '[^a-z0-9]+', '', 'g'))
                ORDER BY cfg.id NULLS LAST
                LIMIT 1
                """,
                (inst, met_nome, met_nome),
            )
            met = cur.fetchone()
            if not met:
                return (
                    jsonify(
                        {
                            "error": f"Metodologia “{met_nome}” não encontrada no catálogo",
                        }
                    ),
                    404,
                )

            nova_diretriz = _append_diretriz(met.get("diretriz_customizada"), teacher_text)
            cur.execute(
                """
                INSERT INTO public.school_metodologia_config (
                    instituicao_id,
                    metodologia_catalogo_id,
                    diretriz_customizada,
                    is_active,
                    is_customizado
                )
                VALUES (%s, %s, %s, TRUE, TRUE)
                ON CONFLICT (instituicao_id, metodologia_catalogo_id)
                DO UPDATE SET
                    diretriz_customizada = EXCLUDED.diretriz_customizada,
                    is_customizado = TRUE,
                    updated_at = CURRENT_TIMESTAMP
                RETURNING id, diretriz_customizada, is_customizado, updated_at,
                          ativo_dia_a_dia, ativo_desafio, is_active
                """,
                (inst, str(met["metodologia_catalogo_id"]), nova_diretriz),
            )
            cfg = cur.fetchone()
            if cfg is not None:
                cfg = dict(cfg)
                cfg["codigo"] = met.get("codigo")

            # Espelho na especialização da organização (Editor Pedagógico)
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
                VALUES (%s, %s, %s, TRUE, TRUE, 1, TRUE)
                ON CONFLICT (instituicao_id, metodologia_id_canonica)
                DO UPDATE SET
                    passos_customizados = EXCLUDED.passos_customizados,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (inst, str(met["metodologia_catalogo_id"]), nova_diretriz),
            )

            cur.execute(
                """
                UPDATE public.school_curadoria_metodologias
                SET status_analise = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
                RETURNING *
                """,
                (STATUS_INCORPORADO, str(cid)),
            )
            updated = cur.fetchone()

    # Fora da TX — notifica B2C (IA do professor).
    from b2c_integration_service import dispatch_methodology_override_updated

    cfg_updated = None
    if cfg and hasattr(cfg.get("updated_at"), "isoformat"):
        cfg_updated = cfg["updated_at"].isoformat()
    elif cfg and cfg.get("updated_at"):
        cfg_updated = str(cfg["updated_at"])
    versao_ts = None
    if cfg_updated:
        try:
            from datetime import datetime

            versao_ts = int(
                datetime.fromisoformat(cfg_updated.replace("Z", "+00:00")).timestamp()
            )
        except Exception:
            versao_ts = None

    dispatch = dispatch_methodology_override_updated(
        instituicao_id=inst,
        metodologia_nome=met_nome,
        metodologia_codigo=(cfg or {}).get("codigo") if cfg else None,
        diretriz_customizada=cfg["diretriz_customizada"] if cfg else nova_diretriz,
        disponivel_dia_a_dia=bool((cfg or {}).get("ativo_dia_a_dia", True)) if cfg else True,
        disponivel_desafio=bool((cfg or {}).get("ativo_desafio", True)) if cfg else True,
        is_active=bool((cfg or {}).get("is_active", True)) if cfg else True,
        atualizado_em=cfg_updated,
        versao=versao_ts,
        origem_config_school_id=str(cfg["id"]) if cfg and cfg.get("id") else None,
    )

    return jsonify(
        {
            "item": _serialize_item(updated),
            "config": {
                "id": str(cfg["id"]) if cfg else None,
                "diretriz_customizada": cfg["diretriz_customizada"] if cfg else nova_diretriz,
                "is_customizado": True,
            },
            "b2c_dispatch": dispatch,
            "message": "Sugestão incorporada à metodologia da escola.",
        }
    )


@bp.post("/api/pedagogico/curadoria/<item_id>/rejeitar")
@require_gestor
def rejeitar(item_id: str):
    """Mantém a adaptação só na aula — não altera a metodologia institucional."""
    inst = _instituicao_id()
    cid = _parse_uuid(item_id)
    if not cid:
        return jsonify({"error": "Identificador inválido"}), 400

    with get_conn() as conn:
        _ensure_curadoria_schema(conn)
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                UPDATE public.school_curadoria_metodologias
                SET status_analise = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
                  AND instituicao_id = %s
                  AND status_analise = %s
                RETURNING *
                """,
                (STATUS_MANTIDO_AULA, str(cid), inst, STATUS_PENDENTE),
            )
            row = cur.fetchone()
            if not row:
                return jsonify({"error": "Sugestão não encontrada ou já analisada"}), 404

    return jsonify(
        {
            "item": _serialize_item(row),
            "message": "Sugestão mantida apenas na aula atual.",
        }
    )

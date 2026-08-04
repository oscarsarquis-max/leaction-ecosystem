"""Ciclo Vivo do PEI — adaptações por metodologia + curadoria da trincheira.

POST /api/pedagogico/pei/<pei_id>/metodologia/<metodologia_nome>/gerar
PUT  /api/pedagogico/pei/<pei_id>/metodologia/<metodologia_nome>
GET  /api/pedagogico/pei/alunos
GET  /api/pedagogico/pei/<pei_id>
GET  /api/pedagogico/pei/<pei_id>/curadoria
POST /api/pedagogico/curadoria_pei/<id>/incorporar
POST /api/pedagogico/curadoria_pei/<id>/rejeitar
"""
from __future__ import annotations

import os
import uuid
from functools import wraps
from typing import Any
from urllib.parse import unquote

from flask import Blueprint, jsonify, request, session
from psycopg2.extras import RealDictCursor

from db import get_conn

bp = Blueprint("pei_ciclo_vivo", __name__)

SESSION_KEY = "school_gestor"


def require_gestor(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        user = session.get(SESSION_KEY)
        if not user or not user.get("instituicao_id"):
            return jsonify({"error": "Não autenticado"}), 401
        return view(*args, **kwargs)

    return wrapped


def _instituicao_id() -> str:
    user = session.get(SESSION_KEY) or {}
    return str(
        user.get("instituicao_id") or os.getenv("DEV_INSTITUICAO_ID") or ""
    ).strip()


def _parse_uuid(value: Any):
    try:
        return uuid.UUID(str(value))
    except (ValueError, TypeError, AttributeError):
        return None


def _ensure_schema(conn) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS public.school_pei_metodologia_adaptacao (
                id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                instituicao_id       UUID NOT NULL
                    REFERENCES public.school_instituicoes (id) ON DELETE CASCADE,
                pei_aluno_id         UUID NOT NULL
                    REFERENCES public.school_pei_individualizado (id) ON DELETE CASCADE,
                metodologia_nome     TEXT NOT NULL,
                passos_customizados  TEXT NOT NULL DEFAULT '',
                gerado_por_ia        BOOLEAN NOT NULL DEFAULT FALSE,
                created_at           TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at           TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT uq_school_pei_met_adapt_pei_met
                    UNIQUE (pei_aluno_id, metodologia_nome)
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS public.school_curadoria_pei (
                id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                instituicao_id          UUID NOT NULL
                    REFERENCES public.school_instituicoes (id) ON DELETE CASCADE,
                pei_aluno_id            UUID
                    REFERENCES public.school_pei_individualizado (id) ON DELETE SET NULL,
                metodologia_nome        TEXT NOT NULL DEFAULT '',
                sugestao_professor_json JSONB NOT NULL DEFAULT '{}'::jsonb,
                status_analise          VARCHAR(32) NOT NULL DEFAULT 'pendente',
                plano_espelhado_id      UUID
                    REFERENCES public.school_planos_aula_espelhados (id)
                    ON DELETE SET NULL,
                created_at              TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at              TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )


def _serialize_adaptacao(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(row["id"]),
        "instituicao_id": str(row["instituicao_id"]),
        "pei_aluno_id": str(row["pei_aluno_id"]),
        "metodologia_nome": row["metodologia_nome"],
        "passos_customizados": row.get("passos_customizados") or "",
        "gerado_por_ia": bool(row.get("gerado_por_ia")),
        "created_at": row["created_at"].isoformat() if row.get("created_at") else None,
        "updated_at": row["updated_at"].isoformat() if row.get("updated_at") else None,
    }


def _perfil_pei(cur, pei_id: uuid.UUID, inst: str) -> dict[str, Any] | None:
    cur.execute(
        """
        SELECT
            p.*,
            a.nome AS aluno_nome,
            a.matricula AS aluno_matricula,
            d.tipo_neurodivergencia,
            d.diretriz AS diretriz_base,
            d.necessidades AS necessidades_base,
            d.capacidades_interesses,
            d.recursos_estrategias
        FROM public.school_pei_individualizado p
        JOIN public.school_alunos a ON a.id = p.aluno_id
        JOIN public.school_pei_diretriz_base d ON d.id = p.pei_diretriz_base_id
        WHERE p.id = %s
          AND a.instituicao_id = %s
          AND p.ativo = TRUE
        LIMIT 1
        """,
        (str(pei_id), inst),
    )
    return cur.fetchone()


def _necessidades_texto(row: dict[str, Any]) -> str:
    parts = [
        f"Aluno: {row.get('aluno_nome') or '—'}",
        f"Neurodivergência / perfil: {row.get('tipo_neurodivergencia') or '—'}",
        f"Particularidades do PEI: {(row.get('particularidades') or '').strip() or '—'}",
        f"Necessidades (plano geral): {(row.get('necessidades_base') or '').strip() or '—'}",
        f"Diretriz base: {(row.get('diretriz_base') or '').strip() or '—'}",
        f"Capacidades/interesses: {(row.get('capacidades_interesses') or '').strip() or '—'}",
        f"Recursos/estratégias: {(row.get('recursos_estrategias') or '').strip() or '—'}",
    ]
    return "\n".join(parts)


def _decode_metodologia(raw: str) -> str:
    return unquote(str(raw or "")).strip()


@bp.get("/api/pedagogico/pei/alunos")
@require_gestor
def list_peis_alunos():
    """Lista PEIs individualizados ativos da instituição."""
    inst = _instituicao_id()
    with get_conn() as conn:
        _ensure_schema(conn)
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT
                    p.id,
                    p.particularidades,
                    p.ativo,
                    p.updated_at,
                    a.id AS aluno_id,
                    a.nome AS aluno_nome,
                    a.matricula,
                    d.tipo_neurodivergencia
                FROM public.school_pei_individualizado p
                JOIN public.school_alunos a ON a.id = p.aluno_id
                JOIN public.school_pei_diretriz_base d ON d.id = p.pei_diretriz_base_id
                WHERE a.instituicao_id = %s
                  AND p.ativo = TRUE
                ORDER BY a.nome ASC
                """,
                (inst,),
            )
            rows = cur.fetchall()
    return jsonify(
        {
            "items": [
                {
                    "id": str(r["id"]),
                    "pei_aluno_id": str(r["id"]),
                    "aluno_id": str(r["aluno_id"]),
                    "aluno_nome": r["aluno_nome"],
                    "matricula": r.get("matricula"),
                    "tipo_neurodivergencia": r["tipo_neurodivergencia"],
                    "particularidades": r.get("particularidades") or "",
                    "updated_at": r["updated_at"].isoformat()
                    if r.get("updated_at")
                    else None,
                }
                for r in rows
            ]
        }
    )


@bp.get("/api/pedagogico/pei/<pei_id>")
@require_gestor
def get_pei_detail(pei_id: str):
    inst = _instituicao_id()
    pid = _parse_uuid(pei_id)
    if not pid:
        return jsonify({"error": "PEI inválido"}), 400
    with get_conn() as conn:
        _ensure_schema(conn)
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            pei = _perfil_pei(cur, pid, inst)
            if not pei:
                return jsonify({"error": "PEI não encontrado"}), 404
            cur.execute(
                """
                SELECT *
                FROM public.school_pei_metodologia_adaptacao
                WHERE pei_aluno_id = %s AND instituicao_id = %s
                ORDER BY metodologia_nome ASC
                """,
                (str(pid), inst),
            )
            adapts = [_serialize_adaptacao(r) for r in cur.fetchall()]
    return jsonify(
        {
            "pei": {
                "id": str(pei["id"]),
                "aluno_nome": pei.get("aluno_nome"),
                "matricula": pei.get("aluno_matricula"),
                "tipo_neurodivergencia": pei.get("tipo_neurodivergencia"),
                "particularidades": pei.get("particularidades") or "",
                "necessidades_resumo": _necessidades_texto(pei),
            },
            "adaptacoes": adapts,
        }
    )


@bp.post("/api/pedagogico/pei/<pei_id>/metodologia/<path:metodologia_nome>/gerar")
@require_gestor
def gerar_adaptacao(pei_id: str, metodologia_nome: str):
    inst = _instituicao_id()
    pid = _parse_uuid(pei_id)
    met = _decode_metodologia(metodologia_nome)
    if not pid or not met:
        return jsonify({"error": "PEI ou metodologia inválidos"}), 400

    with get_conn() as conn:
        _ensure_schema(conn)
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            pei = _perfil_pei(cur, pid, inst)
            if not pei:
                return jsonify({"error": "PEI não encontrado"}), 404
            necessidades = _necessidades_texto(pei)

    try:
        from school_llm import gerar_adaptacao_metodologia_pei

        texto = gerar_adaptacao_metodologia_pei(
            metodologia_nome=met,
            necessidades_especificas=necessidades,
        )
    except Exception as exc:
        return jsonify({"error": f"Falha na geração por IA: {exc}"}), 503

    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                INSERT INTO public.school_pei_metodologia_adaptacao (
                    instituicao_id, pei_aluno_id, metodologia_nome,
                    passos_customizados, gerado_por_ia
                )
                VALUES (%s, %s, %s, %s, TRUE)
                ON CONFLICT (pei_aluno_id, metodologia_nome)
                DO UPDATE SET
                    passos_customizados = EXCLUDED.passos_customizados,
                    gerado_por_ia = TRUE,
                    updated_at = CURRENT_TIMESTAMP
                RETURNING *
                """,
                (inst, str(pid), met, texto),
            )
            row = cur.fetchone()

    return jsonify(
        {
            "item": _serialize_adaptacao(row),
            "message": "Adaptação gerada por IA e salva.",
        }
    ), 201


@bp.put("/api/pedagogico/pei/<pei_id>/metodologia/<path:metodologia_nome>")
@require_gestor
def salvar_adaptacao(pei_id: str, metodologia_nome: str):
    """Pedagogo edita a versão oficial e dispara PEI_OVERRIDE_UPDATED."""
    inst = _instituicao_id()
    pid = _parse_uuid(pei_id)
    met = _decode_metodologia(metodologia_nome)
    if not pid or not met:
        return jsonify({"error": "PEI ou metodologia inválidos"}), 400

    body = request.get_json(silent=True) or {}
    passos = str(body.get("passos_customizados") or "").strip()
    if not passos:
        return jsonify({"error": "passos_customizados obrigatório"}), 400

    with get_conn() as conn:
        _ensure_schema(conn)
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            pei = _perfil_pei(cur, pid, inst)
            if not pei:
                return jsonify({"error": "PEI não encontrado"}), 404
            cur.execute(
                """
                INSERT INTO public.school_pei_metodologia_adaptacao (
                    instituicao_id, pei_aluno_id, metodologia_nome,
                    passos_customizados, gerado_por_ia
                )
                VALUES (%s, %s, %s, %s, FALSE)
                ON CONFLICT (pei_aluno_id, metodologia_nome)
                DO UPDATE SET
                    passos_customizados = EXCLUDED.passos_customizados,
                    gerado_por_ia = FALSE,
                    updated_at = CURRENT_TIMESTAMP
                RETURNING *
                """,
                (inst, str(pid), met, passos),
            )
            row = cur.fetchone()

    from b2c_integration_service import dispatch_pei_override_updated

    dispatch = dispatch_pei_override_updated(
        instituicao_id=inst,
        pei_aluno_id=str(pid),
        aluno_nome=str(pei.get("aluno_nome") or ""),
        metodologia_nome=met,
        passos_customizados=passos,
        tipo_neurodivergencia=str(pei.get("tipo_neurodivergencia") or ""),
    )

    return jsonify(
        {
            "item": _serialize_adaptacao(row),
            "b2c_dispatch": dispatch,
            "message": "Adaptação oficial salva e enviada ao B2C.",
        }
    )


@bp.get("/api/pedagogico/pei/<pei_id>/curadoria")
@require_gestor
def list_curadoria_pei(pei_id: str):
    inst = _instituicao_id()
    pid = _parse_uuid(pei_id)
    if not pid:
        return jsonify({"error": "PEI inválido"}), 400
    with get_conn() as conn:
        _ensure_schema(conn)
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            pei = _perfil_pei(cur, pid, inst)
            if not pei:
                return jsonify({"error": "PEI não encontrado"}), 404
            cur.execute(
                """
                SELECT *
                FROM public.school_curadoria_pei
                WHERE instituicao_id = %s
                  AND pei_aluno_id = %s
                  AND status_analise = 'pendente'
                ORDER BY created_at DESC
                """,
                (inst, str(pid)),
            )
            rows = cur.fetchall()

    items = []
    for r in rows:
        sug = r.get("sugestao_professor_json") or {}
        if not isinstance(sug, dict):
            sug = {}
        texto = str(sug.get("pei_adaptation_text") or sug.get("texto") or "").strip()
        adaptations = sug.get("adaptations")
        if not texto and isinstance(adaptations, dict):
            texto = str(adaptations.get("texto") or "").strip()
        items.append(
            {
                "id": str(r["id"]),
                "metodologia_nome": r.get("metodologia_nome") or "",
                "pei_adaptation_text": texto,
                "sugestao_professor_json": sug,
                "created_at": r["created_at"].isoformat() if r.get("created_at") else None,
            }
        )
    return jsonify({"items": items, "total": len(items)})


@bp.post("/api/pedagogico/curadoria_pei/<item_id>/incorporar")
@require_gestor
def incorporar_curadoria_pei(item_id: str):
    inst = _instituicao_id()
    cid = _parse_uuid(item_id)
    if not cid:
        return jsonify({"error": "Identificador inválido"}), 400

    with get_conn() as conn:
        _ensure_schema(conn)
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT *
                FROM public.school_curadoria_pei
                WHERE id = %s AND instituicao_id = %s
                LIMIT 1
                """,
                (str(cid), inst),
            )
            row = cur.fetchone()
            if not row:
                return jsonify({"error": "Sugestão não encontrada"}), 404
            if row["status_analise"] != "pendente":
                return jsonify({"error": "Sugestão já analisada"}), 409

            pei_id = row.get("pei_aluno_id")
            if not pei_id:
                return jsonify({"error": "Sugestão sem PEI vinculado"}), 400

            sug = row.get("sugestao_professor_json") or {}
            if not isinstance(sug, dict):
                sug = {}
            texto = str(
                sug.get("pei_adaptation_text")
                or sug.get("texto")
                or ""
            ).strip()
            if isinstance(sug.get("adaptations"), dict) and not texto:
                texto = str(sug["adaptations"].get("texto") or "").strip()
            if not texto:
                return jsonify({"error": "Sugestão sem texto do professor"}), 400

            met = str(row.get("metodologia_nome") or sug.get("metodologia_nome") or "").strip()
            if not met:
                met = "Metodologia"

            cur.execute(
                """
                SELECT passos_customizados
                FROM public.school_pei_metodologia_adaptacao
                WHERE pei_aluno_id = %s AND metodologia_nome = %s
                LIMIT 1
                """,
                (str(pei_id), met),
            )
            existing = cur.fetchone()
            block = f"[Sugestão da trincheira]\n{texto}"
            if existing and (existing.get("passos_customizados") or "").strip():
                base = existing["passos_customizados"].strip()
                novos = base if texto in base else f"{base}\n\n{block}"
            else:
                novos = block

            cur.execute(
                """
                INSERT INTO public.school_pei_metodologia_adaptacao (
                    instituicao_id, pei_aluno_id, metodologia_nome,
                    passos_customizados, gerado_por_ia
                )
                VALUES (%s, %s, %s, %s, FALSE)
                ON CONFLICT (pei_aluno_id, metodologia_nome)
                DO UPDATE SET
                    passos_customizados = EXCLUDED.passos_customizados,
                    gerado_por_ia = FALSE,
                    updated_at = CURRENT_TIMESTAMP
                RETURNING *
                """,
                (inst, str(pei_id), met, novos),
            )
            adapt = cur.fetchone()

            cur.execute(
                """
                UPDATE public.school_curadoria_pei
                SET status_analise = 'incorporado',
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
                RETURNING id, status_analise
                """,
                (str(cid),),
            )
            updated = cur.fetchone()

    pei_row = None
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            pei_row = _perfil_pei(cur, uuid.UUID(str(pei_id)), inst)

    from b2c_integration_service import dispatch_pei_override_updated

    dispatch = dispatch_pei_override_updated(
        instituicao_id=inst,
        pei_aluno_id=str(pei_id),
        aluno_nome=str((pei_row or {}).get("aluno_nome") or ""),
        metodologia_nome=met,
        passos_customizados=novos,
        tipo_neurodivergencia=str((pei_row or {}).get("tipo_neurodivergencia") or ""),
    )

    return jsonify(
        {
            "item": {
                "id": str(updated["id"]),
                "status_analise": updated["status_analise"],
            },
            "adaptacao": _serialize_adaptacao(adapt),
            "b2c_dispatch": dispatch,
            "message": "Sugestão incorporada à adaptação base do PEI.",
        }
    )


@bp.post("/api/pedagogico/curadoria_pei/<item_id>/rejeitar")
@require_gestor
def rejeitar_curadoria_pei(item_id: str):
    inst = _instituicao_id()
    cid = _parse_uuid(item_id)
    if not cid:
        return jsonify({"error": "Identificador inválido"}), 400
    with get_conn() as conn:
        _ensure_schema(conn)
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                UPDATE public.school_curadoria_pei
                SET status_analise = 'rejeitado',
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
                  AND instituicao_id = %s
                  AND status_analise = 'pendente'
                RETURNING id, status_analise
                """,
                (str(cid), inst),
            )
            row = cur.fetchone()
            if not row:
                return jsonify({"error": "Sugestão não encontrada ou já analisada"}), 404
    return jsonify(
        {
            "item": {"id": str(row["id"]), "status_analise": row["status_analise"]},
            "message": "Sugestão rejeitada.",
        }
    )

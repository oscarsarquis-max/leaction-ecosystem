"""Quadro de Avisos — fixados na Mesa do Professor (School → Inove)."""
from __future__ import annotations

import uuid
from typing import Any

from flask import Blueprint, jsonify, request
from psycopg2.extras import RealDictCursor

from auth_guards import require_zona, resolve_instituicao_id
from db import get_conn

bp = Blueprint("avisos_mesa", __name__)


@bp.before_request
@require_zona("operacional", "pedagogico")
def _authz_avisos():
    """Leitura no Radar (pedagógico) e gestão na Secretaria (operacional)."""
    return None


def _bound_instituicao(instituicao_id: str):
    inst = resolve_instituicao_id(instituicao_id)
    if isinstance(inst, tuple):
        return inst
    return _parse_uuid(inst, "instituição")


def _parse_uuid(value: str | None, label: str, *, required: bool = True):
    if value is None or str(value).strip() == "":
        if required:
            return jsonify({"error": f"Identificador de {label} obrigatório"}), 400
        return None
    try:
        return uuid.UUID(str(value))
    except (ValueError, TypeError, AttributeError):
        return jsonify({"error": f"Identificador de {label} inválido"}), 400


def _ensure_table(cur: Any) -> None:
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS public.school_avisos_mesa (
            id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            instituicao_id          UUID NOT NULL
                REFERENCES public.school_instituicoes (id) ON DELETE CASCADE,
            texto                   TEXT NOT NULL,
            disciplina_id           UUID
                REFERENCES public.school_disciplinas (id) ON DELETE SET NULL,
            turma_id                UUID
                REFERENCES public.school_turmas (id) ON DELETE SET NULL,
            ativo                   BOOLEAN NOT NULL DEFAULT TRUE,
            replicado_b2c           BOOLEAN NOT NULL DEFAULT FALSE,
            replicado_b2c_em        TIMESTAMPTZ,
            criado_por_gestor_id    UUID
                REFERENCES public.school_gestores (id) ON DELETE SET NULL,
            created_at              TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at              TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )


def _serialize(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(row["id"]),
        "instituicao_id": str(row["instituicao_id"]),
        "texto": row["texto"],
        "disciplina_id": str(row["disciplina_id"]) if row.get("disciplina_id") else None,
        "disciplina_nome": row.get("disciplina_nome"),
        "turma_id": str(row["turma_id"]) if row.get("turma_id") else None,
        "turma_nome": row.get("turma_nome"),
        "ativo": bool(row.get("ativo", True)),
        "replicado_b2c": bool(row.get("replicado_b2c")),
        "publico_label": _publico_label(row),
        "created_at": row["created_at"].isoformat() if row.get("created_at") else None,
    }


def _publico_label(row: dict[str, Any]) -> str:
    if row.get("turma_nome"):
        return f"Turma · {row['turma_nome']}"
    if row.get("disciplina_nome"):
        return f"Disciplina · {row['disciplina_nome']}"
    return "Toda a instituição"


def _push_b2c(aviso: dict[str, Any], instituicao_id: str) -> dict[str, Any]:
    try:
        from b2c_integration_service import dispatch_event_to_b2c

        return dispatch_event_to_b2c(
            "AVISO_MESA_PINNED",
            {
                "instituicao_id": str(instituicao_id),
                "aviso_id": aviso.get("id"),
                "texto": aviso.get("texto"),
                "disciplina_id": aviso.get("disciplina_id"),
                "disciplina_nome": aviso.get("disciplina_nome"),
                "turma_id": aviso.get("turma_id"),
                "turma_nome": aviso.get("turma_nome"),
                "ativo": aviso.get("ativo", True),
            },
        )
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


_SELECT = """
SELECT
    a.*,
    d.nome AS disciplina_nome,
    t.nome AS turma_nome
FROM public.school_avisos_mesa a
LEFT JOIN public.school_disciplinas d ON d.id = a.disciplina_id
LEFT JOIN public.school_turmas t ON t.id = a.turma_id
"""


@bp.get("/api/instituicoes/<instituicao_id>/avisos-mesa")
def list_avisos(instituicao_id: str):
    parsed = _bound_instituicao(instituicao_id)
    if isinstance(parsed, tuple):
        return parsed
    ativos_only = str(request.args.get("ativos") or "1").strip() not in ("0", "false", "no")

    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            _ensure_table(cur)
            cur.execute(
                "SELECT 1 FROM public.school_instituicoes WHERE id = %s",
                (str(parsed),),
            )
            if not cur.fetchone():
                return jsonify({"error": "Instituição não encontrada"}), 404
            sql = _SELECT + " WHERE a.instituicao_id = %s"
            params: list[Any] = [str(parsed)]
            if ativos_only:
                sql += " AND a.ativo = TRUE"
            sql += " ORDER BY a.created_at DESC LIMIT 100"
            cur.execute(sql, params)
            rows = cur.fetchall()

    return jsonify([_serialize(r) for r in rows])


@bp.post("/api/instituicoes/<instituicao_id>/avisos-mesa")
def criar_aviso(instituicao_id: str):
    parsed = _bound_instituicao(instituicao_id)
    if isinstance(parsed, tuple):
        return parsed

    body = request.get_json(silent=True) or {}
    texto = str(body.get("texto") or "").strip()
    if not texto or len(texto) > 500:
        return jsonify({"error": "Informe um texto curto (1–500 caracteres)."}), 400

    disc = _parse_uuid(body.get("disciplina_id"), "disciplina", required=False)
    if isinstance(disc, tuple):
        return disc
    turma = _parse_uuid(body.get("turma_id"), "turma", required=False)
    if isinstance(turma, tuple):
        return turma

    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            _ensure_table(cur)
            cur.execute(
                "SELECT 1 FROM public.school_instituicoes WHERE id = %s",
                (str(parsed),),
            )
            if not cur.fetchone():
                return jsonify({"error": "Instituição não encontrada"}), 404

            if disc:
                cur.execute(
                    """
                    SELECT d.id FROM public.school_disciplinas d
                    JOIN public.school_cursos c ON c.id = d.curso_id
                    JOIN public.school_periodos_letivos p ON p.id = c.periodo_letivo_id
                    WHERE d.id = %s AND p.instituicao_id = %s
                    """,
                    (str(disc), str(parsed)),
                )
                if not cur.fetchone():
                    return jsonify({"error": "Disciplina não encontrada"}), 404

            if turma:
                cur.execute(
                    """
                    SELECT t.id FROM public.school_turmas t
                    JOIN public.school_unidades u ON u.id = t.unidade_id
                    WHERE t.id = %s AND u.instituicao_id = %s
                    """,
                    (str(turma), str(parsed)),
                )
                if not cur.fetchone():
                    return jsonify({"error": "Turma não encontrada"}), 404

            cur.execute(
                """
                INSERT INTO public.school_avisos_mesa
                    (instituicao_id, texto, disciplina_id, turma_id, ativo)
                VALUES (%s, %s, %s, %s, TRUE)
                RETURNING id
                """,
                (
                    str(parsed),
                    texto,
                    str(disc) if disc else None,
                    str(turma) if turma else None,
                ),
            )
            new_id = str(cur.fetchone()["id"])
            cur.execute(_SELECT + " WHERE a.id = %s", (new_id,))
            row = cur.fetchone()

    aviso = _serialize(row)
    push = _push_b2c(aviso, str(parsed))
    if push.get("ok"):
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE public.school_avisos_mesa
                    SET replicado_b2c = TRUE,
                        replicado_b2c_em = CURRENT_TIMESTAMP
                    WHERE id = %s
                    """,
                    (aviso["id"],),
                )
        aviso["replicado_b2c"] = True

    return jsonify({"aviso": aviso, "b2c_push": push}), 201


@bp.patch("/api/instituicoes/<instituicao_id>/avisos-mesa/<aviso_id>")
def atualizar_aviso(instituicao_id: str, aviso_id: str):
    inst = _bound_instituicao(instituicao_id)
    if isinstance(inst, tuple):
        return inst
    aid = _parse_uuid(aviso_id, "aviso")
    if isinstance(aid, tuple):
        return aid

    body = request.get_json(silent=True) or {}
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            _ensure_table(cur)
            sets = []
            params: list[Any] = []
            if "ativo" in body:
                sets.append("ativo = %s")
                params.append(bool(body.get("ativo")))
            if "texto" in body:
                texto = str(body.get("texto") or "").strip()
                if not texto or len(texto) > 500:
                    return jsonify({"error": "Texto inválido."}), 400
                sets.append("texto = %s")
                params.append(texto)
            if not sets:
                return jsonify({"error": "Nada para atualizar."}), 400
            sets.append("updated_at = CURRENT_TIMESTAMP")
            params.extend([str(aid), str(inst)])
            cur.execute(
                f"""
                UPDATE public.school_avisos_mesa
                SET {", ".join(sets)}
                WHERE id = %s AND instituicao_id = %s
                RETURNING id
                """,
                params,
            )
            if not cur.fetchone():
                return jsonify({"error": "Aviso não encontrado"}), 404
            cur.execute(_SELECT + " WHERE a.id = %s", (str(aid),))
            row = cur.fetchone()

    aviso = _serialize(row)
    push = _push_b2c(aviso, str(inst))
    return jsonify({"aviso": aviso, "b2c_push": push})


@bp.get("/api/instituicoes/<instituicao_id>/avisos-mesa/opcoes")
def opcoes_vinculo(instituicao_id: str):
    """Turmas e disciplinas para o seletor do quadro de avisos."""
    parsed = _bound_instituicao(instituicao_id)
    if isinstance(parsed, tuple):
        return parsed

    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT t.id, t.nome, u.nome AS unidade_nome
                FROM public.school_turmas t
                JOIN public.school_unidades u ON u.id = t.unidade_id
                WHERE u.instituicao_id = %s
                ORDER BY u.nome, t.nome
                LIMIT 200
                """,
                (str(parsed),),
            )
            turmas = [
                {
                    "id": str(r["id"]),
                    "nome": r["nome"],
                    "unidade_nome": r.get("unidade_nome"),
                    "label": f"{r['nome']}"
                    + (f" · {r['unidade_nome']}" if r.get("unidade_nome") else ""),
                }
                for r in cur.fetchall()
            ]
            cur.execute(
                """
                SELECT d.id, d.nome
                FROM public.school_disciplinas d
                JOIN public.school_cursos c ON c.id = d.curso_id
                JOIN public.school_periodos_letivos p ON p.id = c.periodo_letivo_id
                WHERE p.instituicao_id = %s
                ORDER BY d.nome
                LIMIT 200
                """,
                (str(parsed),),
            )
            disciplinas = [
                {"id": str(r["id"]), "nome": r["nome"]} for r in cur.fetchall()
            ]

    return jsonify({"turmas": turmas, "disciplinas": disciplinas})

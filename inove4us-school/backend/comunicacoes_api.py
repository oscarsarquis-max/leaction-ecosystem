"""Secretaria — comunicações e eventos (zona operacional).

Cadastro em school_comunicacoes_eventos. Push B2C = etapa futura.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from flask import Blueprint, jsonify, request
from psycopg2.extras import RealDictCursor

from db import get_conn

bp = Blueprint("comunicacoes", __name__)

TIPOS = frozenset({"reuniao_pedagogica", "evento_escolar"})
PUBLICOS = frozenset({"toda_instituicao", "unidade", "turma", "professores"})
STATUS = frozenset({"agendado", "publicado", "cancelado"})

TIPO_LABEL = {
    "reuniao_pedagogica": "Reunião pedagógica",
    "evento_escolar": "Evento escolar",
}
PUBLICO_LABEL = {
    "toda_instituicao": "Toda a instituição",
    "unidade": "Unidade",
    "turma": "Turma",
    "professores": "Professores",
}
STATUS_LABEL = {
    "agendado": "Agendado",
    "publicado": "Publicado",
    "cancelado": "Cancelado",
}


def _parse_uuid(value: str | None, label: str, *, required: bool = True):
    if value is None or str(value).strip() == "":
        if required:
            return jsonify({"error": f"Identificador de {label} obrigatório"}), 400
        return None
    try:
        return uuid.UUID(str(value))
    except (ValueError, TypeError, AttributeError):
        return jsonify({"error": f"Identificador de {label} inválido"}), 400


def _parse_dt(raw: Any, label: str, *, required: bool = True):
    if raw is None or str(raw).strip() == "":
        if required:
            return jsonify({"error": f"{label} obrigatório"}), 400
        return None
    text = str(raw).strip().replace("Z", "+00:00")
    try:
        if len(text) == 16:  # YYYY-MM-DDTHH:MM
            text = text + ":00"
        return datetime.fromisoformat(text)
    except ValueError:
        return jsonify({"error": f"Data/hora inválida em {label}"}), 400


def _serialize(row: dict[str, Any]) -> dict:
    tipo = row["tipo"]
    publico = row["publico_alvo"]
    status = row["status"]
    return {
        "id": str(row["id"]),
        "instituicao_id": str(row["instituicao_id"]),
        "unidade_id": str(row["unidade_id"]) if row.get("unidade_id") else None,
        "unidade_nome": row.get("unidade_nome"),
        "turma_id": str(row["turma_id"]) if row.get("turma_id") else None,
        "turma_nome": row.get("turma_nome"),
        "titulo": row["titulo"],
        "descricao": row.get("descricao"),
        "tipo": tipo,
        "tipo_label": TIPO_LABEL.get(tipo, tipo),
        "data_hora_inicio": row["data_hora_inicio"].isoformat()
        if row.get("data_hora_inicio")
        else None,
        "data_hora_fim": row["data_hora_fim"].isoformat()
        if row.get("data_hora_fim")
        else None,
        "publico_alvo": publico,
        "publico_label": PUBLICO_LABEL.get(publico, publico),
        "status": status,
        "status_label": STATUS_LABEL.get(status, status),
        "replicado_b2c": bool(row.get("replicado_b2c")),
        "criado_por_gestor_id": str(row["criado_por_gestor_id"])
        if row.get("criado_por_gestor_id")
        else None,
        "created_at": row["created_at"].isoformat() if row.get("created_at") else None,
    }


_SELECT = """
SELECT
    c.*,
    u.nome AS unidade_nome,
    t.nome AS turma_nome
FROM public.school_comunicacoes_eventos c
LEFT JOIN public.school_unidades u ON u.id = c.unidade_id
LEFT JOIN public.school_turmas t ON t.id = c.turma_id
"""


@bp.get("/api/instituicoes/<instituicao_id>/comunicacoes")
def listar(instituicao_id: str):
    inst = _parse_uuid(instituicao_id, "instituição")
    if isinstance(inst, tuple):
        return inst

    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                _SELECT
                + """
                WHERE c.instituicao_id = %s
                  AND c.status <> 'cancelado'
                ORDER BY c.data_hora_inicio DESC, c.created_at DESC
                """,
                (str(inst),),
            )
            rows = [_serialize(r) for r in cur.fetchall()]

    return jsonify({"items": rows})


@bp.post("/api/instituicoes/<instituicao_id>/comunicacoes")
def criar(instituicao_id: str):
    inst = _parse_uuid(instituicao_id, "instituição")
    if isinstance(inst, tuple):
        return inst

    body = request.get_json(silent=True) or {}
    titulo = str(body.get("titulo") or "").strip()
    if not titulo:
        return jsonify({"error": "Título obrigatório"}), 400

    tipo = str(body.get("tipo") or "").strip()
    if tipo not in TIPOS:
        return jsonify({"error": "Tipo inválido"}), 400

    publico = str(body.get("publico_alvo") or "").strip()
    if publico not in PUBLICOS:
        return jsonify({"error": "Público-alvo inválido"}), 400

    inicio = _parse_dt(body.get("data_hora_inicio"), "data_hora_inicio")
    if isinstance(inicio, tuple):
        return inicio
    fim = _parse_dt(body.get("data_hora_fim"), "data_hora_fim", required=False)
    if isinstance(fim, tuple):
        return fim

    unidade = _parse_uuid(body.get("unidade_id"), "unidade", required=False)
    if isinstance(unidade, tuple):
        return unidade
    turma = _parse_uuid(body.get("turma_id"), "turma", required=False)
    if isinstance(turma, tuple):
        return turma

    if publico == "unidade" and not unidade:
        return jsonify({"error": "Selecione a unidade"}), 400
    if publico == "turma" and not turma:
        return jsonify({"error": "Selecione a turma"}), 400
    if publico == "toda_instituicao":
        unidade = None
        turma = None
    if publico == "professores":
        turma = None

    status = str(body.get("status") or "agendado").strip()
    if status not in STATUS:
        return jsonify({"error": "Status inválido"}), 400

    gestor = _parse_uuid(body.get("criado_por_gestor_id"), "gestor", required=False)
    if isinstance(gestor, tuple):
        return gestor

    descricao = str(body.get("descricao") or "").strip() or None

    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                INSERT INTO public.school_comunicacoes_eventos (
                    instituicao_id, unidade_id, titulo, descricao, tipo,
                    data_hora_inicio, data_hora_fim, publico_alvo, turma_id,
                    status, criado_por_gestor_id
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
                RETURNING id
                """,
                (
                    str(inst),
                    str(unidade) if unidade else None,
                    titulo,
                    descricao,
                    tipo,
                    inicio,
                    fim,
                    publico,
                    str(turma) if turma else None,
                    status,
                    str(gestor) if gestor else None,
                ),
            )
            new_id = cur.fetchone()["id"]
            cur.execute(_SELECT + " WHERE c.id = %s", (str(new_id),))
            row = cur.fetchone()

    return jsonify({"item": _serialize(row)}), 201


@bp.patch("/api/instituicoes/<instituicao_id>/comunicacoes/<item_id>")
def atualizar(instituicao_id: str, item_id: str):
    inst = _parse_uuid(instituicao_id, "instituição")
    if isinstance(inst, tuple):
        return inst
    cid = _parse_uuid(item_id, "comunicação")
    if isinstance(cid, tuple):
        return cid

    body = request.get_json(silent=True) or {}
    status = str(body.get("status") or "").strip()
    if status not in STATUS:
        return jsonify({"error": "Status inválido"}), 400

    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                UPDATE public.school_comunicacoes_eventos
                SET status = %s, updated_at = CURRENT_TIMESTAMP
                WHERE id = %s AND instituicao_id = %s
                RETURNING id
                """,
                (status, str(cid), str(inst)),
            )
            if not cur.fetchone():
                return jsonify({"error": "Comunicação não encontrada"}), 404
            cur.execute(_SELECT + " WHERE c.id = %s", (str(cid),))
            row = cur.fetchone()

    return jsonify({"item": _serialize(row)})

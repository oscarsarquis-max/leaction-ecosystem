"""Secretaria Acadêmica — CRUD flat + alocação docente (TEACHER_ALLOCATED).

Evolução da secretaria_api hierárquica: superfície /api/secretaria/* para o
painel operacional (unidades, períodos, disciplinas, alocações).
"""
from __future__ import annotations

import os
import uuid
from datetime import date, datetime
from functools import wraps
from typing import Any

from flask import Blueprint, jsonify, request, session
from psycopg2 import errors as pg_errors
from psycopg2.extras import RealDictCursor

from db import get_conn

bp = Blueprint("secretaria_academica", __name__)

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
        user.get("instituicao_id")
        or os.getenv("DEV_INSTITUICAO_ID")
        or ""
    ).strip()


def _parse_uuid(value: Any, label: str):
    try:
        return uuid.UUID(str(value))
    except (ValueError, TypeError, AttributeError):
        return None


def _parse_date(value: Any) -> date | None:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    raw = str(value or "").strip()[:10]
    if not raw:
        return None
    try:
        return date.fromisoformat(raw)
    except ValueError:
        return None


def _text(value: Any) -> str:
    return str(value or "").strip()


# ---------------------------------------------------------------------------
# Unidades
# ---------------------------------------------------------------------------
@bp.get("/api/secretaria/unidades")
@require_gestor
def list_unidades():
    inst = _instituicao_id()
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id, nome, endereco, codigo, cidade, uf, ativo, created_at
                FROM public.school_unidades
                WHERE instituicao_id = %s AND ativo = TRUE
                ORDER BY nome ASC
                """,
                (inst,),
            )
            rows = cur.fetchall()
    return jsonify(
        {
            "items": [
                {
                    "id": str(r["id"]),
                    "nome": r["nome"],
                    "endereco": r.get("endereco") or "",
                    "codigo": r.get("codigo"),
                    "cidade": r.get("cidade"),
                    "uf": r.get("uf"),
                }
                for r in rows
            ]
        }
    )


@bp.post("/api/secretaria/unidades")
@require_gestor
def create_unidade():
    inst = _instituicao_id()
    body = request.get_json(silent=True) or {}
    nome = _text(body.get("nome"))
    endereco = _text(body.get("endereco")) or None
    if not nome:
        return jsonify({"error": "nome é obrigatório"}), 400

    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                INSERT INTO public.school_unidades (instituicao_id, nome, endereco)
                VALUES (%s, %s, %s)
                RETURNING id, nome, endereco, codigo, cidade, uf, ativo
                """,
                (inst, nome, endereco),
            )
            row = cur.fetchone()
    return (
        jsonify(
            {
                "item": {
                    "id": str(row["id"]),
                    "nome": row["nome"],
                    "endereco": row.get("endereco") or "",
                }
            }
        ),
        201,
    )


# ---------------------------------------------------------------------------
# Períodos
# ---------------------------------------------------------------------------
@bp.get("/api/secretaria/periodos")
@require_gestor
def list_periodos():
    inst = _instituicao_id()
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id, rotulo AS nome, data_inicio, data_fim, ano_letivo,
                       tipo_periodo, unidade_id, status, ativo
                FROM public.school_periodos_letivos
                WHERE instituicao_id = %s AND ativo = TRUE
                ORDER BY data_inicio DESC, rotulo ASC
                """,
                (inst,),
            )
            rows = cur.fetchall()
    return jsonify(
        {
            "items": [
                {
                    "id": str(r["id"]),
                    "nome": r["nome"],
                    "data_inicio": r["data_inicio"].isoformat() if r["data_inicio"] else None,
                    "data_fim": r["data_fim"].isoformat() if r["data_fim"] else None,
                    "ano_letivo": r.get("ano_letivo"),
                    "tipo_periodo": r.get("tipo_periodo"),
                    "unidade_id": str(r["unidade_id"]) if r.get("unidade_id") else None,
                    "status": r.get("status"),
                }
                for r in rows
            ]
        }
    )


@bp.post("/api/secretaria/periodos")
@require_gestor
def create_periodo():
    inst = _instituicao_id()
    body = request.get_json(silent=True) or {}
    nome = _text(body.get("nome") or body.get("rotulo"))
    data_inicio = _parse_date(body.get("data_inicio"))
    data_fim = _parse_date(body.get("data_fim"))
    if not nome:
        return jsonify({"error": "nome é obrigatório"}), 400
    if not data_inicio or not data_fim:
        return jsonify({"error": "data_inicio e data_fim são obrigatórios"}), 400
    if data_fim <= data_inicio:
        return jsonify({"error": "data_fim deve ser posterior a data_inicio"}), 400

    ano = body.get("ano_letivo")
    try:
        ano_letivo = int(ano) if ano is not None else data_inicio.year
    except (TypeError, ValueError):
        ano_letivo = data_inicio.year
    tipo = _text(body.get("tipo_periodo")) or "semestral"
    if tipo not in ("anual", "semestral", "trimestral", "modular"):
        tipo = "semestral"
    unidade_id = _parse_uuid(body.get("unidade_id"), "unidade")
    unidade_s = str(unidade_id) if unidade_id else None

    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            if unidade_s:
                cur.execute(
                    """
                    SELECT 1 FROM public.school_unidades
                    WHERE id = %s AND instituicao_id = %s
                    """,
                    (unidade_s, inst),
                )
                if not cur.fetchone():
                    return jsonify({"error": "unidade inválida"}), 400

            cur.execute(
                """
                INSERT INTO public.school_periodos_letivos (
                    instituicao_id, unidade_id, rotulo, ano_letivo,
                    tipo_periodo, data_inicio, data_fim, status
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, 'planejamento')
                RETURNING id, rotulo, data_inicio, data_fim, ano_letivo, tipo_periodo
                """,
                (inst, unidade_s, nome, ano_letivo, tipo, data_inicio, data_fim),
            )
            row = cur.fetchone()
    return (
        jsonify(
            {
                "item": {
                    "id": str(row["id"]),
                    "nome": row["rotulo"],
                    "data_inicio": row["data_inicio"].isoformat(),
                    "data_fim": row["data_fim"].isoformat(),
                    "ano_letivo": row["ano_letivo"],
                    "tipo_periodo": row["tipo_periodo"],
                }
            }
        ),
        201,
    )


# ---------------------------------------------------------------------------
# Disciplinas (catálogo flat)
# ---------------------------------------------------------------------------
@bp.get("/api/secretaria/disciplinas")
@require_gestor
def list_disciplinas():
    inst = _instituicao_id()
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT d.id, d.nome, d.ementa, d.carga_horaria_horas, d.codigo, d.curso_id
                FROM public.school_disciplinas d
                LEFT JOIN public.school_cursos c ON c.id = d.curso_id
                LEFT JOIN public.school_periodos_letivos p ON p.id = c.periodo_letivo_id
                WHERE d.ativo = TRUE
                  AND (
                        d.instituicao_id = %s
                     OR p.instituicao_id = %s
                  )
                ORDER BY d.nome ASC
                """,
                (inst, inst),
            )
            rows = cur.fetchall()
    return jsonify(
        {
            "items": [
                {
                    "id": str(r["id"]),
                    "nome": r["nome"],
                    "ementa_macro": r.get("ementa") or "",
                    "carga_horaria": float(r["carga_horaria_horas"])
                    if r.get("carga_horaria_horas") is not None
                    else None,
                    "codigo": r.get("codigo"),
                    "curso_id": str(r["curso_id"]) if r.get("curso_id") else None,
                }
                for r in rows
            ]
        }
    )


@bp.post("/api/secretaria/disciplinas")
@require_gestor
def create_disciplina():
    inst = _instituicao_id()
    body = request.get_json(silent=True) or {}
    nome = _text(body.get("nome"))
    ementa = _text(body.get("ementa_macro") or body.get("ementa")) or None
    carga_raw = body.get("carga_horaria")
    if carga_raw is None:
        carga_raw = body.get("carga_horaria_horas")
    carga = None
    if carga_raw is not None and str(carga_raw).strip() != "":
        try:
            carga = float(carga_raw)
        except (TypeError, ValueError):
            return jsonify({"error": "carga_horaria inválida"}), 400
    if not nome:
        return jsonify({"error": "nome é obrigatório"}), 400

    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                INSERT INTO public.school_disciplinas (
                    instituicao_id, curso_id, nome, ementa, carga_horaria_horas
                )
                VALUES (%s, NULL, %s, %s, %s)
                RETURNING id, nome, ementa, carga_horaria_horas
                """,
                (inst, nome, ementa, carga),
            )
            row = cur.fetchone()
    return (
        jsonify(
            {
                "item": {
                    "id": str(row["id"]),
                    "nome": row["nome"],
                    "ementa_macro": row.get("ementa") or "",
                    "carga_horaria": float(row["carga_horaria_horas"])
                    if row.get("carga_horaria_horas") is not None
                    else None,
                }
            }
        ),
        201,
    )


# ---------------------------------------------------------------------------
# Alocações + TEACHER_ALLOCATED
# ---------------------------------------------------------------------------
@bp.get("/api/secretaria/alocacoes")
@require_gestor
def list_alocacoes():
    inst = _instituicao_id()
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT
                    a.id,
                    a.unidade_id,
                    u.nome AS unidade_nome,
                    a.periodo_id,
                    p.rotulo AS periodo_nome,
                    p.data_inicio AS data_inicio_periodo,
                    a.disciplina_id,
                    d.nome AS disciplina_nome,
                    a.professor_vinculo_id AS professor_id,
                    v.email_convite AS professor_email,
                    v.professor_b2c_id,
                    a.notificado_b2c,
                    a.created_at
                FROM public.school_alocacoes_docentes a
                JOIN public.school_unidades u ON u.id = a.unidade_id
                JOIN public.school_periodos_letivos p ON p.id = a.periodo_id
                JOIN public.school_disciplinas d ON d.id = a.disciplina_id
                JOIN public.school_professores_vinculo v ON v.id = a.professor_vinculo_id
                WHERE a.instituicao_id = %s AND a.ativo = TRUE
                ORDER BY a.created_at DESC
                """,
                (inst,),
            )
            rows = cur.fetchall()
    return jsonify(
        {
            "items": [
                {
                    "id": str(r["id"]),
                    "unidade_id": str(r["unidade_id"]),
                    "unidade_nome": r["unidade_nome"],
                    "periodo_id": str(r["periodo_id"]),
                    "periodo_nome": r["periodo_nome"],
                    "disciplina_id": str(r["disciplina_id"]),
                    "disciplina_nome": r["disciplina_nome"],
                    "professor_id": str(r["professor_id"]),
                    "professor_email": r.get("professor_email"),
                    "professor_b2c_id": str(r["professor_b2c_id"])
                    if r.get("professor_b2c_id")
                    else None,
                    "data_inicio_periodo": r["data_inicio_periodo"].isoformat()
                    if r.get("data_inicio_periodo")
                    else None,
                    "notificado_b2c": bool(r.get("notificado_b2c")),
                    "created_at": r["created_at"].isoformat() if r.get("created_at") else None,
                }
                for r in rows
            ]
        }
    )


@bp.get("/api/secretaria/professores")
@require_gestor
def list_professores_equipe():
    """Dropdown da alocação — vínculos ativos/pendentes da instituição."""
    inst = _instituicao_id()
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id, email_convite, professor_b2c_id, status_vinculo
                FROM public.school_professores_vinculo
                WHERE instituicao_id = %s
                  AND status_vinculo IN ('ativo', 'pendente')
                ORDER BY email_convite NULLS LAST, created_at ASC
                """,
                (inst,),
            )
            rows = cur.fetchall()
    return jsonify(
        {
            "items": [
                {
                    "id": str(r["id"]),
                    "professor_id": str(r["id"]),
                    "email": r.get("email_convite") or "",
                    "professor_b2c_id": str(r["professor_b2c_id"])
                    if r.get("professor_b2c_id")
                    else None,
                    "status": r["status_vinculo"],
                    "label": r.get("email_convite")
                    or f"Professor {str(r['id'])[:8]}",
                }
                for r in rows
            ]
        }
    )


@bp.post("/api/secretaria/alocacoes")
@require_gestor
def create_alocacao():
    """Casamento unidade+período+disciplina+professor → TEACHER_ALLOCATED no B2C."""
    inst = _instituicao_id()
    body = request.get_json(silent=True) or {}
    unidade_id = _parse_uuid(body.get("unidade_id"), "unidade")
    periodo_id = _parse_uuid(body.get("periodo_id"), "periodo")
    disciplina_id = _parse_uuid(body.get("disciplina_id"), "disciplina")
    professor_id = _parse_uuid(
        body.get("professor_id") or body.get("professor_vinculo_id"), "professor"
    )
    if not all([unidade_id, periodo_id, disciplina_id, professor_id]):
        return jsonify(
            {
                "error": "unidade_id, periodo_id, disciplina_id e professor_id são obrigatórios"
            }
        ), 400

    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id, nome FROM public.school_unidades
                WHERE id = %s AND instituicao_id = %s AND ativo = TRUE
                """,
                (str(unidade_id), inst),
            )
            unidade = cur.fetchone()
            if not unidade:
                return jsonify({"error": "unidade inválida"}), 400

            cur.execute(
                """
                SELECT id, rotulo, data_inicio
                FROM public.school_periodos_letivos
                WHERE id = %s AND instituicao_id = %s AND ativo = TRUE
                """,
                (str(periodo_id), inst),
            )
            periodo = cur.fetchone()
            if not periodo:
                return jsonify({"error": "período inválido"}), 400

            cur.execute(
                """
                SELECT d.id, d.nome, d.ementa, d.instituicao_id, p.instituicao_id AS periodo_inst
                FROM public.school_disciplinas d
                LEFT JOIN public.school_cursos c ON c.id = d.curso_id
                LEFT JOIN public.school_periodos_letivos p ON p.id = c.periodo_letivo_id
                WHERE d.id = %s AND d.ativo = TRUE
                """,
                (str(disciplina_id),),
            )
            disc = cur.fetchone()
            if not disc:
                return jsonify({"error": "disciplina inválida"}), 400
            disc_inst = str(disc.get("instituicao_id") or disc.get("periodo_inst") or "")
            if disc_inst and disc_inst != inst:
                return jsonify({"error": "disciplina não pertence à instituição"}), 403

            cur.execute(
                """
                SELECT id, professor_b2c_id, email_convite, status_vinculo
                FROM public.school_professores_vinculo
                WHERE id = %s AND instituicao_id = %s
                  AND status_vinculo IN ('ativo', 'pendente')
                """,
                (str(professor_id), inst),
            )
            prof = cur.fetchone()
            if not prof:
                return jsonify({"error": "professor inválido ou inativo"}), 400

            try:
                cur.execute(
                    """
                    INSERT INTO public.school_alocacoes_docentes (
                        instituicao_id, unidade_id, periodo_id,
                        disciplina_id, professor_vinculo_id
                    )
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (
                        inst,
                        str(unidade_id),
                        str(periodo_id),
                        str(disciplina_id),
                        str(professor_id),
                    ),
                )
                aloc = cur.fetchone()
            except pg_errors.UniqueViolation:
                conn.rollback()
                return jsonify({"error": "Esta alocação já existe"}), 409

            payload_b2c = {
                "professor_b2c_id": str(prof["professor_b2c_id"]),
                "disciplina_nome": disc["nome"],
                "ementa_macro": disc.get("ementa") or "",
                "data_inicio_periodo": periodo["data_inicio"].isoformat()
                if periodo.get("data_inicio")
                else None,
                "instituicao_id": inst,
                "unidade_id": str(unidade_id),
                "unidade_nome": unidade["nome"],
                "periodo_id": str(periodo_id),
                "periodo_nome": periodo["rotulo"],
                "disciplina_id": str(disciplina_id),
                "alocacao_id": str(aloc["id"]),
                "professor_email": prof.get("email_convite"),
            }

    # Fora da transação DB — falha de rede não desfaz a alocação
    from b2c_integration_service import dispatch_teacher_allocated

    dispatch = dispatch_teacher_allocated(payload_b2c)
    if dispatch.get("ok"):
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE public.school_alocacoes_docentes
                    SET notificado_b2c = TRUE, updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                    """,
                    (str(aloc["id"]),),
                )

    return (
        jsonify(
            {
                "item": {
                    "id": str(aloc["id"]),
                    "unidade_id": str(unidade_id),
                    "periodo_id": str(periodo_id),
                    "disciplina_id": str(disciplina_id),
                    "professor_id": str(professor_id),
                    "notificado_b2c": bool(dispatch.get("ok")),
                },
                "b2c_dispatch": dispatch,
                "message": (
                    "Professor alocado. Ambiente do professor notificado."
                    if dispatch.get("ok")
                    else "Professor alocado. Notificação B2C pendente (serviço indisponível)."
                ),
            }
        ),
        201,
    )

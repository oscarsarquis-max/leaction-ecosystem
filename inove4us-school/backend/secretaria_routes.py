"""Secretaria Acadêmica — CRUD operacional + alocação docente (TEACHER_ALLOCATED).

Superfície /api/secretaria/* para o painel operacional:
unidades, períodos, cursos, disciplinas, turmas, alunos, calendário,
alocações, comunicações e planejamento escolar.
"""
from __future__ import annotations

import json
import os
import uuid
from datetime import date, datetime, time
from functools import wraps
from typing import Any

from flask import Blueprint, jsonify, request, session
from psycopg2 import errors as pg_errors
from psycopg2.extras import Json, RealDictCursor

from auth_guards import (
    SESSION_KEY,
    require_zona,
    resolve_instituicao_id,
    resolve_unidade_id,
)
from db import get_conn

bp = Blueprint("secretaria_academica", __name__)

TIPOS_PERIODO = frozenset({"anual", "semestral", "trimestral", "modular"})
NIVEIS = frozenset(
    {
        "fundamental",
        "medio",
        "tecnico",
        "superior",
        "livre",
        "corporativo",
        "idiomas",
        "outro",
    }
)
TURNOS = frozenset({"manha", "tarde", "integral", "noite"})
CAL_TIPOS = frozenset({"letivo", "feriado", "avaliacao", "evento"})
PLAN_TIPOS = frozenset({"aula", "evento"})
PLAN_STATUS = frozenset({"rascunho", "enviado", "erro"})


# Zona operacional — Secretaria Acadêmica (inclui planejamento escolar).
require_gestor = require_zona("operacional")


def _instituicao_id() -> str:
    """Instituição da sessão (sem fallback DEV — evita vazamento multi-tenant)."""
    resolved = resolve_instituicao_id()
    if isinstance(resolved, tuple):
        return ""
    return resolved


def _unidade_escopo(claimed: Any = None):
    return resolve_unidade_id(claimed)


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


def _iso(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return str(value)


def _parse_time(value: Any) -> time | None:
    if value is None or value == "":
        return None
    if isinstance(value, time):
        return value
    if isinstance(value, datetime):
        return value.time().replace(microsecond=0)
    raw = str(value).strip()
    if not raw:
        return None
    if len(raw) >= 8:
        try:
            return datetime.strptime(raw[:8], "%H:%M:%S").time()
        except ValueError:
            pass
    try:
        return datetime.strptime(raw[:5], "%H:%M").time()
    except ValueError:
        return None


def _time_iso(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, time):
        return value.strftime("%H:%M")
    raw = str(value)
    return raw[:5] if len(raw) >= 5 else raw


# ---------------------------------------------------------------------------
# Unidades
# ---------------------------------------------------------------------------
@bp.get("/api/secretaria/unidades")
@require_gestor
def list_unidades():
    inst = _instituicao_id()
    escopo = _unidade_escopo()
    if isinstance(escopo, tuple):
        return escopo
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            sql = """
                SELECT id, nome, endereco, codigo, cidade, uf, ativo, created_at
                FROM public.school_unidades
                WHERE instituicao_id = %s
            """
            params: list[Any] = [inst]
            if escopo:
                sql += " AND id = %s"
                params.append(escopo)
            sql += " ORDER BY nome ASC"
            cur.execute(sql, params)
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
                    "ativo": bool(r["ativo"]),
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
    if not nome:
        return jsonify({"error": "nome é obrigatório"}), 400

    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            try:
                cur.execute(
                    """
                    INSERT INTO public.school_unidades (
                        instituicao_id, nome, endereco, codigo, cidade, uf
                    )
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING id, nome, endereco, codigo, cidade, uf, ativo
                    """,
                    (
                        inst,
                        nome,
                        _text(body.get("endereco")) or None,
                        _text(body.get("codigo")) or None,
                        _text(body.get("cidade")) or None,
                        _text(body.get("uf")) or None,
                    ),
                )
                row = cur.fetchone()
            except pg_errors.UniqueViolation:
                conn.rollback()
                return jsonify({"error": "Já existe unidade com este nome"}), 409
    return (
        jsonify(
            {
                "item": {
                    "id": str(row["id"]),
                    "nome": row["nome"],
                    "endereco": row.get("endereco") or "",
                    "codigo": row.get("codigo"),
                    "cidade": row.get("cidade"),
                    "uf": row.get("uf"),
                    "ativo": bool(row["ativo"]),
                }
            }
        ),
        201,
    )


@bp.put("/api/secretaria/unidades/<item_id>")
@require_gestor
def update_unidade(item_id: str):
    inst = _instituicao_id()
    uid = _parse_uuid(item_id, "unidade")
    if not uid:
        return jsonify({"error": "Identificador inválido"}), 400
    body = request.get_json(silent=True) or {}

    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            try:
                cur.execute(
                    """
                    UPDATE public.school_unidades
                    SET nome = COALESCE(%s, nome),
                        endereco = CASE WHEN %s THEN %s ELSE endereco END,
                        codigo = CASE WHEN %s THEN %s ELSE codigo END,
                        cidade = CASE WHEN %s THEN %s ELSE cidade END,
                        uf = CASE WHEN %s THEN %s ELSE uf END,
                        ativo = COALESCE(%s, ativo),
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s AND instituicao_id = %s
                    RETURNING id, nome, endereco, codigo, cidade, uf, ativo
                    """,
                    (
                        _text(body["nome"]) if body.get("nome") is not None else None,
                        "endereco" in body,
                        _text(body.get("endereco")) or None,
                        "codigo" in body,
                        _text(body.get("codigo")) or None,
                        "cidade" in body,
                        _text(body.get("cidade")) or None,
                        "uf" in body,
                        _text(body.get("uf")) or None,
                        bool(body["ativo"]) if "ativo" in body else None,
                        str(uid),
                        inst,
                    ),
                )
                row = cur.fetchone()
            except pg_errors.UniqueViolation:
                conn.rollback()
                return jsonify({"error": "Já existe unidade com este nome"}), 409
    if not row:
        return jsonify({"error": "Unidade não encontrada"}), 404
    return jsonify(
        {
            "item": {
                "id": str(row["id"]),
                "nome": row["nome"],
                "endereco": row.get("endereco") or "",
                "codigo": row.get("codigo"),
                "cidade": row.get("cidade"),
                "uf": row.get("uf"),
                "ativo": bool(row["ativo"]),
            }
        }
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
                WHERE instituicao_id = %s
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
                    "data_inicio": _iso(r["data_inicio"]),
                    "data_fim": _iso(r["data_fim"]),
                    "ano_letivo": r.get("ano_letivo"),
                    "tipo_periodo": r.get("tipo_periodo"),
                    "unidade_id": str(r["unidade_id"]) if r.get("unidade_id") else None,
                    "status": r.get("status"),
                    "ativo": bool(r["ativo"]),
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
    if tipo not in TIPOS_PERIODO:
        return jsonify({"error": "tipo_periodo inválido"}), 400
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
                RETURNING id, rotulo, data_inicio, data_fim, ano_letivo,
                          tipo_periodo, unidade_id, status, ativo
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
                    "data_inicio": _iso(row["data_inicio"]),
                    "data_fim": _iso(row["data_fim"]),
                    "ano_letivo": row["ano_letivo"],
                    "tipo_periodo": row["tipo_periodo"],
                    "unidade_id": str(row["unidade_id"]) if row.get("unidade_id") else None,
                    "status": row["status"],
                    "ativo": bool(row["ativo"]),
                }
            }
        ),
        201,
    )


@bp.put("/api/secretaria/periodos/<item_id>")
@require_gestor
def update_periodo(item_id: str):
    inst = _instituicao_id()
    pid = _parse_uuid(item_id, "período")
    if not pid:
        return jsonify({"error": "Identificador inválido"}), 400
    body = request.get_json(silent=True) or {}

    nome = None
    if body.get("nome") is not None or body.get("rotulo") is not None:
        nome = _text(body.get("nome") or body.get("rotulo")) or None
    tipo = _text(body.get("tipo_periodo")) if body.get("tipo_periodo") is not None else None
    if tipo is not None and tipo not in TIPOS_PERIODO:
        return jsonify({"error": "tipo_periodo inválido"}), 400

    unidade_s = None
    clear_unidade = False
    if "unidade_id" in body:
        if body.get("unidade_id") in (None, ""):
            clear_unidade = True
        else:
            unidade_id = _parse_uuid(body.get("unidade_id"), "unidade")
            if not unidade_id:
                return jsonify({"error": "unidade_id inválido"}), 400
            unidade_s = str(unidade_id)

    data_inicio = _parse_date(body.get("data_inicio")) if body.get("data_inicio") else None
    data_fim = _parse_date(body.get("data_fim")) if body.get("data_fim") else None
    ano_letivo = None
    if body.get("ano_letivo") is not None:
        try:
            ano_letivo = int(body["ano_letivo"])
        except (TypeError, ValueError):
            return jsonify({"error": "ano_letivo inválido"}), 400

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
                UPDATE public.school_periodos_letivos
                SET rotulo = COALESCE(%s, rotulo),
                    ano_letivo = COALESCE(%s, ano_letivo),
                    tipo_periodo = COALESCE(%s, tipo_periodo),
                    data_inicio = COALESCE(%s, data_inicio),
                    data_fim = COALESCE(%s, data_fim),
                    unidade_id = CASE
                        WHEN %s THEN NULL
                        WHEN %s IS NOT NULL THEN %s::uuid
                        ELSE unidade_id
                    END,
                    ativo = COALESCE(%s, ativo),
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s AND instituicao_id = %s
                RETURNING id, rotulo, data_inicio, data_fim, ano_letivo,
                          tipo_periodo, unidade_id, status, ativo
                """,
                (
                    nome,
                    ano_letivo,
                    tipo,
                    data_inicio,
                    data_fim,
                    clear_unidade,
                    unidade_s,
                    unidade_s,
                    bool(body["ativo"]) if "ativo" in body else None,
                    str(pid),
                    inst,
                ),
            )
            row = cur.fetchone()
    if not row:
        return jsonify({"error": "Período não encontrado"}), 404
    return jsonify(
        {
            "item": {
                "id": str(row["id"]),
                "nome": row["rotulo"],
                "data_inicio": _iso(row["data_inicio"]),
                "data_fim": _iso(row["data_fim"]),
                "ano_letivo": row["ano_letivo"],
                "tipo_periodo": row["tipo_periodo"],
                "unidade_id": str(row["unidade_id"]) if row.get("unidade_id") else None,
                "status": row["status"],
                "ativo": bool(row["ativo"]),
            }
        }
    )


# ---------------------------------------------------------------------------
# Cursos
# ---------------------------------------------------------------------------
@bp.get("/api/secretaria/cursos")
@require_gestor
def list_cursos():
    inst = _instituicao_id()
    periodo_id = _parse_uuid(
        request.args.get("periodo_letivo_id") or request.args.get("periodo_id"),
        "periodo",
    )
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            sql = """
                SELECT c.id, c.nome, c.nivel, c.turma_turno, c.ativo,
                       c.periodo_letivo_id,
                       (
                         SELECT COUNT(*)::int FROM public.school_turmas t
                         WHERE t.curso_id = c.id AND t.ativa = TRUE
                       ) AS turmas_count,
                       (
                         SELECT COUNT(*)::int FROM public.school_disciplinas d
                         WHERE d.curso_id = c.id AND d.ativo = TRUE
                       ) AS disciplinas_count
                FROM public.school_cursos c
                JOIN public.school_periodos_letivos p ON p.id = c.periodo_letivo_id
                WHERE p.instituicao_id = %s
            """
            params: list[Any] = [inst]
            if periodo_id:
                sql += " AND c.periodo_letivo_id = %s"
                params.append(str(periodo_id))
            sql += " ORDER BY c.nome ASC"
            cur.execute(sql, params)
            rows = cur.fetchall()
    return jsonify(
        {
            "items": [
                {
                    "id": str(r["id"]),
                    "nome": r["nome"],
                    "nivel": r.get("nivel"),
                    "turma_turno": r.get("turma_turno"),
                    "ativo": bool(r["ativo"]),
                    "periodo_letivo_id": str(r["periodo_letivo_id"]),
                    "turmas_count": int(r.get("turmas_count") or 0),
                    "disciplinas_count": int(r.get("disciplinas_count") or 0),
                }
                for r in rows
            ]
        }
    )


@bp.post("/api/secretaria/cursos")
@require_gestor
def create_curso():
    inst = _instituicao_id()
    body = request.get_json(silent=True) or {}
    nome = _text(body.get("nome"))
    periodo_id = _parse_uuid(body.get("periodo_letivo_id"), "periodo")
    if not nome:
        return jsonify({"error": "nome é obrigatório"}), 400
    if not periodo_id:
        return jsonify({"error": "periodo_letivo_id é obrigatório"}), 400
    nivel = _text(body.get("nivel")) or None
    if nivel and nivel not in NIVEIS:
        return jsonify({"error": "nivel inválido"}), 400

    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT 1 FROM public.school_periodos_letivos
                WHERE id = %s AND instituicao_id = %s
                """,
                (str(periodo_id), inst),
            )
            if not cur.fetchone():
                return jsonify({"error": "período inválido"}), 400
            cur.execute(
                """
                INSERT INTO public.school_cursos (
                    periodo_letivo_id, nome, nivel, turma_turno
                )
                VALUES (%s, %s, %s, %s)
                RETURNING id, nome, nivel, turma_turno, ativo, periodo_letivo_id
                """,
                (
                    str(periodo_id),
                    nome,
                    nivel,
                    _text(body.get("turma_turno")) or None,
                ),
            )
            row = cur.fetchone()
    return (
        jsonify(
            {
                "item": {
                    "id": str(row["id"]),
                    "nome": row["nome"],
                    "nivel": row.get("nivel"),
                    "turma_turno": row.get("turma_turno"),
                    "ativo": bool(row["ativo"]),
                    "periodo_letivo_id": str(row["periodo_letivo_id"]),
                }
            }
        ),
        201,
    )


@bp.put("/api/secretaria/cursos/<item_id>")
@require_gestor
def update_curso(item_id: str):
    inst = _instituicao_id()
    cid = _parse_uuid(item_id, "curso")
    if not cid:
        return jsonify({"error": "Identificador inválido"}), 400
    body = request.get_json(silent=True) or {}
    if "nivel" in body:
        nivel = _text(body.get("nivel")) or None
        if nivel and nivel not in NIVEIS:
            return jsonify({"error": "nivel inválido"}), 400

    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                UPDATE public.school_cursos c
                SET nome = COALESCE(%s, c.nome),
                    nivel = CASE WHEN %s THEN %s ELSE c.nivel END,
                    turma_turno = CASE WHEN %s THEN %s ELSE c.turma_turno END,
                    ativo = COALESCE(%s, c.ativo),
                    updated_at = CURRENT_TIMESTAMP
                FROM public.school_periodos_letivos p
                WHERE c.id = %s
                  AND c.periodo_letivo_id = p.id
                  AND p.instituicao_id = %s
                RETURNING c.id, c.nome, c.nivel, c.turma_turno, c.ativo, c.periodo_letivo_id
                """,
                (
                    _text(body["nome"]) if body.get("nome") is not None else None,
                    "nivel" in body,
                    _text(body.get("nivel")) or None,
                    "turma_turno" in body,
                    _text(body.get("turma_turno")) or None,
                    bool(body["ativo"]) if "ativo" in body else None,
                    str(cid),
                    inst,
                ),
            )
            row = cur.fetchone()
    if not row:
        return jsonify({"error": "Curso não encontrado"}), 404
    return jsonify(
        {
            "item": {
                "id": str(row["id"]),
                "nome": row["nome"],
                "nivel": row.get("nivel"),
                "turma_turno": row.get("turma_turno"),
                "ativo": bool(row["ativo"]),
                "periodo_letivo_id": str(row["periodo_letivo_id"]),
            }
        }
    )


# ---------------------------------------------------------------------------
# Disciplinas
# ---------------------------------------------------------------------------
@bp.get("/api/secretaria/disciplinas")
@require_gestor
def list_disciplinas():
    inst = _instituicao_id()
    curso_id = _parse_uuid(request.args.get("curso_id"), "curso")
    periodo_id = _parse_uuid(
        request.args.get("periodo_letivo_id") or request.args.get("periodo_id"),
        "periodo",
    )
    sem_curso = str(request.args.get("sem_curso") or "").lower() in (
        "1",
        "true",
        "yes",
    )
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            sql = """
                SELECT d.id, d.nome, d.ementa, d.carga_horaria_horas, d.codigo,
                       d.curso_id, d.ativo, c.nome AS curso_nome,
                       c.periodo_letivo_id
                FROM public.school_disciplinas d
                LEFT JOIN public.school_cursos c ON c.id = d.curso_id
                LEFT JOIN public.school_periodos_letivos p ON p.id = c.periodo_letivo_id
                WHERE (d.instituicao_id = %s OR p.instituicao_id = %s)
            """
            params: list[Any] = [inst, inst]
            if curso_id:
                sql += " AND d.curso_id = %s"
                params.append(str(curso_id))
            if sem_curso:
                sql += " AND d.curso_id IS NULL"
            if periodo_id and not curso_id and not sem_curso:
                sql += """
                    AND (
                        c.periodo_letivo_id = %s
                        OR d.curso_id IS NULL
                    )
                """
                params.append(str(periodo_id))
            sql += " ORDER BY d.nome ASC"
            cur.execute(sql, params)
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
                    "curso_nome": r.get("curso_nome"),
                    "periodo_letivo_id": str(r["periodo_letivo_id"])
                    if r.get("periodo_letivo_id")
                    else None,
                    "ativo": bool(r["ativo"]),
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
    carga = None
    carga_raw = body.get("carga_horaria", body.get("carga_horaria_horas"))
    if carga_raw is not None and str(carga_raw).strip() != "":
        try:
            carga = float(carga_raw)
        except (TypeError, ValueError):
            return jsonify({"error": "carga_horaria inválida"}), 400
    if not nome:
        return jsonify({"error": "nome é obrigatório"}), 400

    curso_id = None
    if body.get("curso_id") not in (None, ""):
        curso_id = _parse_uuid(body.get("curso_id"), "curso")
        if not curso_id:
            return jsonify({"error": "curso_id inválido"}), 400

    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            if curso_id:
                cur.execute(
                    """
                    SELECT c.id
                    FROM public.school_cursos c
                    JOIN public.school_periodos_letivos p ON p.id = c.periodo_letivo_id
                    WHERE c.id = %s AND p.instituicao_id = %s
                    """,
                    (str(curso_id), inst),
                )
                if not cur.fetchone():
                    return jsonify({"error": "curso inválido"}), 400
            cur.execute(
                """
                INSERT INTO public.school_disciplinas (
                    instituicao_id, curso_id, nome, ementa, carga_horaria_horas
                )
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id, nome, ementa, carga_horaria_horas, curso_id, ativo
                """,
                (inst, str(curso_id) if curso_id else None, nome, ementa, carga),
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
                    "curso_id": str(row["curso_id"]) if row.get("curso_id") else None,
                    "ativo": bool(row["ativo"]),
                }
            }
        ),
        201,
    )


@bp.put("/api/secretaria/disciplinas/<item_id>")
@require_gestor
def update_disciplina(item_id: str):
    inst = _instituicao_id()
    did = _parse_uuid(item_id, "disciplina")
    if not did:
        return jsonify({"error": "Identificador inválido"}), 400
    body = request.get_json(silent=True) or {}

    carga = None
    update_carga = False
    if "carga_horaria" in body or "carga_horaria_horas" in body:
        update_carga = True
        raw = body.get("carga_horaria", body.get("carga_horaria_horas"))
        if raw is not None and str(raw).strip() != "":
            try:
                carga = float(raw)
            except (TypeError, ValueError):
                return jsonify({"error": "carga_horaria inválida"}), 400

    curso_s = None
    clear_curso = False
    if "curso_id" in body:
        if body.get("curso_id") in (None, ""):
            clear_curso = True
        else:
            curso_id = _parse_uuid(body.get("curso_id"), "curso")
            if not curso_id:
                return jsonify({"error": "curso_id inválido"}), 400
            curso_s = str(curso_id)

    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            if curso_s:
                cur.execute(
                    """
                    SELECT c.id
                    FROM public.school_cursos c
                    JOIN public.school_periodos_letivos p ON p.id = c.periodo_letivo_id
                    WHERE c.id = %s AND p.instituicao_id = %s
                    """,
                    (curso_s, inst),
                )
                if not cur.fetchone():
                    return jsonify({"error": "curso inválido"}), 400

            cur.execute(
                """
                UPDATE public.school_disciplinas d
                SET nome = COALESCE(%s, d.nome),
                    ementa = CASE WHEN %s THEN %s ELSE d.ementa END,
                    carga_horaria_horas = CASE WHEN %s THEN %s ELSE d.carga_horaria_horas END,
                    curso_id = CASE
                        WHEN %s THEN NULL
                        WHEN %s IS NOT NULL THEN %s::uuid
                        ELSE d.curso_id
                    END,
                    ativo = COALESCE(%s, d.ativo),
                    updated_at = CURRENT_TIMESTAMP
                WHERE d.id = %s
                  AND (
                        d.instituicao_id = %s
                     OR EXISTS (
                            SELECT 1
                            FROM public.school_cursos c
                            JOIN public.school_periodos_letivos p ON p.id = c.periodo_letivo_id
                            WHERE c.id = d.curso_id AND p.instituicao_id = %s
                        )
                  )
                RETURNING d.id, d.nome, d.ementa, d.carga_horaria_horas,
                          d.curso_id, d.ativo
                """,
                (
                    _text(body["nome"]) if body.get("nome") is not None else None,
                    "ementa_macro" in body or "ementa" in body,
                    _text(body.get("ementa_macro") or body.get("ementa")) or None,
                    update_carga,
                    carga,
                    clear_curso,
                    curso_s,
                    curso_s,
                    bool(body["ativo"]) if "ativo" in body else None,
                    str(did),
                    inst,
                    inst,
                ),
            )
            row = cur.fetchone()
    if not row:
        return jsonify({"error": "Disciplina não encontrada"}), 404
    return jsonify(
        {
            "item": {
                "id": str(row["id"]),
                "nome": row["nome"],
                "ementa_macro": row.get("ementa") or "",
                "carga_horaria": float(row["carga_horaria_horas"])
                if row.get("carga_horaria_horas") is not None
                else None,
                "curso_id": str(row["curso_id"]) if row.get("curso_id") else None,
                "ativo": bool(row["ativo"]),
            }
        }
    )


# ---------------------------------------------------------------------------
# Turmas
# ---------------------------------------------------------------------------
def _serialize_turma(r: dict) -> dict[str, Any]:
    return {
        "id": str(r["id"]),
        "nome": r["nome"],
        "serie_ano": r["serie_ano"],
        "turno": r["turno"],
        "ano_letivo": r["ano_letivo"],
        "unidade_id": str(r["unidade_id"]),
        "unidade_nome": r.get("unidade_nome"),
        "periodo_letivo_id": str(r["periodo_letivo_id"])
        if r.get("periodo_letivo_id")
        else None,
        "curso_id": str(r["curso_id"]) if r.get("curso_id") else None,
        "curso_nome": r.get("curso_nome"),
        "ativa": bool(r["ativa"]),
    }


@bp.get("/api/secretaria/turmas")
@require_gestor
def list_turmas():
    inst = _instituicao_id()
    unidade_raw = request.args.get("unidade_id")
    escopo = _unidade_escopo(unidade_raw)
    if isinstance(escopo, tuple):
        return escopo
    unidade_id = _parse_uuid(escopo or unidade_raw, "unidade") if (escopo or unidade_raw) else None
    curso_id = _parse_uuid(request.args.get("curso_id"), "curso")
    periodo_id = _parse_uuid(
        request.args.get("periodo_letivo_id") or request.args.get("periodo_id"),
        "periodo",
    )
    sem_curso = str(request.args.get("sem_curso") or "").lower() in (
        "1",
        "true",
        "yes",
    )
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            sql = """
                SELECT t.id, t.nome, t.serie_ano, t.turno, t.ano_letivo,
                       t.unidade_id, t.ativa, t.periodo_letivo_id, t.curso_id,
                       u.nome AS unidade_nome, c.nome AS curso_nome
                FROM public.school_turmas t
                JOIN public.school_unidades u ON u.id = t.unidade_id
                LEFT JOIN public.school_cursos c ON c.id = t.curso_id
                WHERE t.instituicao_id = %s
            """
            params: list[Any] = [inst]
            if unidade_id:
                sql += " AND t.unidade_id = %s"
                params.append(str(unidade_id))
            elif escopo:
                sql += " AND t.unidade_id = %s"
                params.append(escopo)
            if curso_id:
                sql += " AND t.curso_id = %s"
                params.append(str(curso_id))
            if sem_curso:
                sql += " AND t.curso_id IS NULL"
            if periodo_id:
                sql += " AND t.periodo_letivo_id = %s"
                params.append(str(periodo_id))
            sql += " ORDER BY t.ano_letivo DESC, t.nome ASC"
            cur.execute(sql, params)
            rows = cur.fetchall()
    return jsonify({"items": [_serialize_turma(r) for r in rows]})


@bp.post("/api/secretaria/turmas")
@require_gestor
def create_turma():
    inst = _instituicao_id()
    body = request.get_json(silent=True) or {}
    nome = _text(body.get("nome"))
    serie_ano = _text(body.get("serie_ano"))
    turno = _text(body.get("turno"))
    unidade_id = _parse_uuid(body.get("unidade_id"), "unidade")
    periodo_id = _parse_uuid(
        body.get("periodo_letivo_id") or body.get("periodo_id"),
        "periodo",
    )
    if not nome:
        return jsonify({"error": "nome é obrigatório"}), 400
    if not serie_ano:
        return jsonify({"error": "serie_ano é obrigatório"}), 400
    if turno not in TURNOS:
        return jsonify({"error": "turno inválido"}), 400
    if not unidade_id:
        return jsonify({"error": "unidade_id é obrigatório"}), 400
    if not periodo_id:
        return jsonify({"error": "periodo_letivo_id é obrigatório"}), 400

    curso_id = None
    if body.get("curso_id") not in (None, ""):
        curso_id = _parse_uuid(body.get("curso_id"), "curso")
        if not curso_id:
            return jsonify({"error": "curso_id inválido"}), 400

    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT 1 FROM public.school_unidades
                WHERE id = %s AND instituicao_id = %s
                """,
                (str(unidade_id), inst),
            )
            if not cur.fetchone():
                return jsonify({"error": "unidade inválida"}), 400

            cur.execute(
                """
                SELECT ano_letivo, EXTRACT(YEAR FROM data_inicio)::int AS ano_inicio
                FROM public.school_periodos_letivos
                WHERE id = %s AND instituicao_id = %s
                """,
                (str(periodo_id), inst),
            )
            periodo = cur.fetchone()
            if not periodo:
                return jsonify({"error": "período inválido"}), 400

            if body.get("ano_letivo") is not None and str(body.get("ano_letivo")).strip() != "":
                try:
                    ano_letivo = int(body.get("ano_letivo"))
                except (TypeError, ValueError):
                    return jsonify({"error": "ano_letivo inválido"}), 400
            else:
                ano_letivo = int(
                    periodo.get("ano_letivo") or periodo.get("ano_inicio") or datetime.now().year
                )

            if curso_id:
                cur.execute(
                    """
                    SELECT 1 FROM public.school_cursos c
                    JOIN public.school_periodos_letivos p ON p.id = c.periodo_letivo_id
                    WHERE c.id = %s AND p.instituicao_id = %s
                      AND c.periodo_letivo_id = %s
                    """,
                    (str(curso_id), inst, str(periodo_id)),
                )
                if not cur.fetchone():
                    return jsonify({"error": "curso inválido para este período"}), 400

            try:
                cur.execute(
                    """
                    INSERT INTO public.school_turmas (
                        instituicao_id, nome, serie_ano, turno, ano_letivo,
                        unidade_id, periodo_letivo_id, curso_id
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id, nome, serie_ano, turno, ano_letivo, unidade_id,
                              periodo_letivo_id, curso_id, ativa
                    """,
                    (
                        inst,
                        nome,
                        serie_ano,
                        turno,
                        ano_letivo,
                        str(unidade_id),
                        str(periodo_id),
                        str(curso_id) if curso_id else None,
                    ),
                )
                row = cur.fetchone()
            except pg_errors.UniqueViolation:
                conn.rollback()
                return jsonify({"error": "Já existe turma com este nome no ano letivo"}), 409
    return jsonify({"item": _serialize_turma(row)}), 201


@bp.put("/api/secretaria/turmas/<item_id>")
@require_gestor
def update_turma(item_id: str):
    inst = _instituicao_id()
    tid = _parse_uuid(item_id, "turma")
    if not tid:
        return jsonify({"error": "Identificador inválido"}), 400
    body = request.get_json(silent=True) or {}
    turno = _text(body.get("turno")) if body.get("turno") is not None else None
    if turno is not None and turno not in TURNOS:
        return jsonify({"error": "turno inválido"}), 400

    unidade_s = None
    if body.get("unidade_id") not in (None, ""):
        unidade_id = _parse_uuid(body.get("unidade_id"), "unidade")
        if not unidade_id:
            return jsonify({"error": "unidade_id inválido"}), 400
        unidade_s = str(unidade_id)

    periodo_s = None
    if body.get("periodo_letivo_id") not in (None, "") or body.get("periodo_id") not in (
        None,
        "",
    ):
        periodo_id = _parse_uuid(
            body.get("periodo_letivo_id") or body.get("periodo_id"),
            "periodo",
        )
        if not periodo_id:
            return jsonify({"error": "periodo_letivo_id inválido"}), 400
        periodo_s = str(periodo_id)

    clear_curso = False
    curso_s = None
    if "curso_id" in body:
        if body.get("curso_id") in (None, ""):
            clear_curso = True
        else:
            curso_id = _parse_uuid(body.get("curso_id"), "curso")
            if not curso_id:
                return jsonify({"error": "curso_id inválido"}), 400
            curso_s = str(curso_id)

    ano_letivo = None
    if body.get("ano_letivo") is not None and str(body.get("ano_letivo")).strip() != "":
        try:
            ano_letivo = int(body["ano_letivo"])
        except (TypeError, ValueError):
            return jsonify({"error": "ano_letivo inválido"}), 400

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

            if periodo_s:
                cur.execute(
                    """
                    SELECT ano_letivo, EXTRACT(YEAR FROM data_inicio)::int AS ano_inicio
                    FROM public.school_periodos_letivos
                    WHERE id = %s AND instituicao_id = %s
                    """,
                    (periodo_s, inst),
                )
                periodo = cur.fetchone()
                if not periodo:
                    return jsonify({"error": "período inválido"}), 400
                if ano_letivo is None:
                    ano_letivo = int(
                        periodo.get("ano_letivo")
                        or periodo.get("ano_inicio")
                        or datetime.now().year
                    )

            if curso_s:
                cur.execute(
                    """
                    SELECT c.periodo_letivo_id
                    FROM public.school_cursos c
                    JOIN public.school_periodos_letivos p ON p.id = c.periodo_letivo_id
                    WHERE c.id = %s AND p.instituicao_id = %s
                    """,
                    (curso_s, inst),
                )
                curso_row = cur.fetchone()
                if not curso_row:
                    return jsonify({"error": "curso inválido"}), 400

            try:
                cur.execute(
                    """
                    UPDATE public.school_turmas
                    SET nome = COALESCE(%s, nome),
                        serie_ano = COALESCE(%s, serie_ano),
                        turno = COALESCE(%s, turno),
                        ano_letivo = COALESCE(%s, ano_letivo),
                        unidade_id = COALESCE(%s, unidade_id),
                        periodo_letivo_id = COALESCE(%s, periodo_letivo_id),
                        curso_id = CASE
                            WHEN %s THEN NULL
                            WHEN %s IS NOT NULL THEN %s::uuid
                            ELSE curso_id
                        END,
                        ativa = COALESCE(%s, ativa),
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s AND instituicao_id = %s
                    RETURNING id, nome, serie_ano, turno, ano_letivo, unidade_id,
                              periodo_letivo_id, curso_id, ativa
                    """,
                    (
                        _text(body["nome"]) if body.get("nome") is not None else None,
                        _text(body["serie_ano"]) if body.get("serie_ano") is not None else None,
                        turno,
                        ano_letivo,
                        unidade_s,
                        periodo_s,
                        clear_curso,
                        curso_s,
                        curso_s,
                        bool(body["ativa"]) if "ativa" in body else None,
                        str(tid),
                        inst,
                    ),
                )
                row = cur.fetchone()
            except pg_errors.UniqueViolation:
                conn.rollback()
                return jsonify({"error": "Já existe turma com este nome no ano letivo"}), 409
    if not row:
        return jsonify({"error": "Turma não encontrada"}), 404
    return jsonify({"item": _serialize_turma(row)})


# ---------------------------------------------------------------------------
# Alunos
# ---------------------------------------------------------------------------
@bp.get("/api/secretaria/alunos")
@require_gestor
def list_alunos():
    inst = _instituicao_id()
    turma_id = _parse_uuid(request.args.get("turma_id"), "turma")
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            sql = """
                SELECT a.id, a.nome, a.matricula, a.turma_id, a.data_nascimento,
                       a.ativo, t.nome AS turma_nome
                FROM public.school_alunos a
                LEFT JOIN public.school_turmas t ON t.id = a.turma_id
                WHERE a.instituicao_id = %s
            """
            params: list[Any] = [inst]
            if turma_id:
                sql += " AND a.turma_id = %s"
                params.append(str(turma_id))
            sql += " ORDER BY a.nome ASC"
            cur.execute(sql, params)
            rows = cur.fetchall()
    return jsonify(
        {
            "items": [
                {
                    "id": str(r["id"]),
                    "nome": r["nome"],
                    "matricula": r["matricula"],
                    "turma_id": str(r["turma_id"]) if r.get("turma_id") else None,
                    "turma_nome": r.get("turma_nome"),
                    "data_nascimento": _iso(r.get("data_nascimento")),
                    "ativo": bool(r["ativo"]),
                }
                for r in rows
            ]
        }
    )


@bp.post("/api/secretaria/alunos")
@require_gestor
def create_aluno():
    inst = _instituicao_id()
    body = request.get_json(silent=True) or {}
    nome = _text(body.get("nome"))
    matricula = _text(body.get("matricula"))
    if not nome:
        return jsonify({"error": "nome é obrigatório"}), 400
    if not matricula:
        return jsonify({"error": "matricula é obrigatória"}), 400

    turma_s = None
    if body.get("turma_id") not in (None, ""):
        turma_id = _parse_uuid(body.get("turma_id"), "turma")
        if not turma_id:
            return jsonify({"error": "turma_id inválido"}), 400
        turma_s = str(turma_id)

    data_nasc = _parse_date(body.get("data_nascimento"))

    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            if turma_s:
                cur.execute(
                    """
                    SELECT 1 FROM public.school_turmas
                    WHERE id = %s AND instituicao_id = %s
                    """,
                    (turma_s, inst),
                )
                if not cur.fetchone():
                    return jsonify({"error": "turma inválida"}), 400
            try:
                cur.execute(
                    """
                    INSERT INTO public.school_alunos (
                        instituicao_id, nome, matricula, turma_id, data_nascimento
                    )
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id, nome, matricula, turma_id, data_nascimento, ativo
                    """,
                    (inst, nome, matricula, turma_s, data_nasc),
                )
                row = cur.fetchone()
            except pg_errors.UniqueViolation:
                conn.rollback()
                return jsonify({"error": "Já existe aluno com esta matrícula"}), 409
    return (
        jsonify(
            {
                "item": {
                    "id": str(row["id"]),
                    "nome": row["nome"],
                    "matricula": row["matricula"],
                    "turma_id": str(row["turma_id"]) if row.get("turma_id") else None,
                    "data_nascimento": _iso(row.get("data_nascimento")),
                    "ativo": bool(row["ativo"]),
                }
            }
        ),
        201,
    )


@bp.put("/api/secretaria/alunos/<item_id>")
@require_gestor
def update_aluno(item_id: str):
    inst = _instituicao_id()
    aid = _parse_uuid(item_id, "aluno")
    if not aid:
        return jsonify({"error": "Identificador inválido"}), 400
    body = request.get_json(silent=True) or {}

    turma_s = None
    clear_turma = False
    if "turma_id" in body:
        if body.get("turma_id") in (None, ""):
            clear_turma = True
        else:
            turma_id = _parse_uuid(body.get("turma_id"), "turma")
            if not turma_id:
                return jsonify({"error": "turma_id inválido"}), 400
            turma_s = str(turma_id)

    data_nasc = _parse_date(body.get("data_nascimento")) if body.get("data_nascimento") else None
    if body.get("data_nascimento") == "":
        data_nasc = None
        clear_nasc = True
    else:
        clear_nasc = False

    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            if turma_s:
                cur.execute(
                    """
                    SELECT 1 FROM public.school_turmas
                    WHERE id = %s AND instituicao_id = %s
                    """,
                    (turma_s, inst),
                )
                if not cur.fetchone():
                    return jsonify({"error": "turma inválida"}), 400
            try:
                cur.execute(
                    """
                    UPDATE public.school_alunos
                    SET nome = COALESCE(%s, nome),
                        matricula = COALESCE(%s, matricula),
                        turma_id = CASE
                            WHEN %s THEN NULL
                            WHEN %s IS NOT NULL THEN %s::uuid
                            ELSE turma_id
                        END,
                        data_nascimento = CASE
                            WHEN %s THEN NULL
                            WHEN %s IS NOT NULL THEN %s
                            ELSE data_nascimento
                        END,
                        ativo = COALESCE(%s, ativo),
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s AND instituicao_id = %s
                    RETURNING id, nome, matricula, turma_id, data_nascimento, ativo
                    """,
                    (
                        _text(body["nome"]) if body.get("nome") is not None else None,
                        _text(body["matricula"]) if body.get("matricula") is not None else None,
                        clear_turma,
                        turma_s,
                        turma_s,
                        clear_nasc or body.get("data_nascimento") == "",
                        data_nasc,
                        data_nasc,
                        bool(body["ativo"]) if "ativo" in body else None,
                        str(aid),
                        inst,
                    ),
                )
                row = cur.fetchone()
            except pg_errors.UniqueViolation:
                conn.rollback()
                return jsonify({"error": "Já existe aluno com esta matrícula"}), 409
    if not row:
        return jsonify({"error": "Aluno não encontrado"}), 404
    return jsonify(
        {
            "item": {
                "id": str(row["id"]),
                "nome": row["nome"],
                "matricula": row["matricula"],
                "turma_id": str(row["turma_id"]) if row.get("turma_id") else None,
                "data_nascimento": _iso(row.get("data_nascimento")),
                "ativo": bool(row["ativo"]),
            }
        }
    )


# ---------------------------------------------------------------------------
# Calendário
# ---------------------------------------------------------------------------
@bp.get("/api/secretaria/calendario")
@require_gestor
def list_calendario():
    inst = _instituicao_id()
    unidade_raw = request.args.get("unidade_id")
    escopo = _unidade_escopo(unidade_raw)
    if isinstance(escopo, tuple):
        return escopo
    unidade_id = _parse_uuid(escopo or unidade_raw, "unidade") if (escopo or unidade_raw) else None
    data_inicio = _parse_date(request.args.get("data_inicio"))
    data_fim = _parse_date(request.args.get("data_fim"))
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            sql = """
                SELECT c.id, c.titulo, c.tipo, c.data_inicio, c.data_fim,
                       c.unidade_id, u.nome AS unidade_nome
                FROM public.school_calendario_letivo c
                LEFT JOIN public.school_unidades u ON u.id = c.unidade_id
                WHERE c.instituicao_id = %s
            """
            params: list[Any] = [inst]
            if unidade_id:
                sql += " AND c.unidade_id = %s"
                params.append(str(unidade_id))
            elif escopo:
                sql += " AND c.unidade_id = %s"
                params.append(escopo)
            if data_inicio:
                sql += " AND (c.data_fim IS NULL OR c.data_fim >= %s)"
                params.append(data_inicio)
            if data_fim:
                sql += " AND c.data_inicio <= %s"
                params.append(data_fim)
            sql += " ORDER BY c.data_inicio ASC, c.titulo ASC"
            cur.execute(sql, params)
            rows = cur.fetchall()
    return jsonify(
        {
            "items": [
                {
                    "id": str(r["id"]),
                    "titulo": r["titulo"],
                    "tipo": r["tipo"],
                    "data_inicio": _iso(r["data_inicio"]),
                    "data_fim": _iso(r.get("data_fim")),
                    "unidade_id": str(r["unidade_id"]) if r.get("unidade_id") else None,
                    "unidade_nome": r.get("unidade_nome"),
                }
                for r in rows
            ]
        }
    )


@bp.post("/api/secretaria/calendario")
@require_gestor
def create_calendario():
    inst = _instituicao_id()
    body = request.get_json(silent=True) or {}
    titulo = _text(body.get("titulo"))
    tipo = _text(body.get("tipo"))
    if not titulo:
        return jsonify({"error": "titulo é obrigatório"}), 400
    if tipo not in CAL_TIPOS:
        return jsonify({"error": "tipo inválido"}), 400
    data_inicio = _parse_date(body.get("data_inicio"))
    if not data_inicio:
        return jsonify({"error": "data_inicio é obrigatória"}), 400
    data_fim = _parse_date(body.get("data_fim"))

    unidade_s = None
    if body.get("unidade_id") not in (None, ""):
        unidade_id = _parse_uuid(body.get("unidade_id"), "unidade")
        if not unidade_id:
            return jsonify({"error": "unidade_id inválido"}), 400
        unidade_s = str(unidade_id)

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
                INSERT INTO public.school_calendario_letivo (
                    instituicao_id, titulo, tipo, data_inicio, data_fim, unidade_id
                )
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id, titulo, tipo, data_inicio, data_fim, unidade_id
                """,
                (inst, titulo, tipo, data_inicio, data_fim, unidade_s),
            )
            row = cur.fetchone()
    return (
        jsonify(
            {
                "item": {
                    "id": str(row["id"]),
                    "titulo": row["titulo"],
                    "tipo": row["tipo"],
                    "data_inicio": _iso(row["data_inicio"]),
                    "data_fim": _iso(row.get("data_fim")),
                    "unidade_id": str(row["unidade_id"]) if row.get("unidade_id") else None,
                }
            }
        ),
        201,
    )


@bp.put("/api/secretaria/calendario/<item_id>")
@require_gestor
def update_calendario(item_id: str):
    inst = _instituicao_id()
    cid = _parse_uuid(item_id, "calendário")
    if not cid:
        return jsonify({"error": "Identificador inválido"}), 400
    body = request.get_json(silent=True) or {}
    tipo = _text(body.get("tipo")) if body.get("tipo") is not None else None
    if tipo is not None and tipo not in CAL_TIPOS:
        return jsonify({"error": "tipo inválido"}), 400

    unidade_s = None
    clear_unidade = False
    if "unidade_id" in body:
        if body.get("unidade_id") in (None, ""):
            clear_unidade = True
        else:
            unidade_id = _parse_uuid(body.get("unidade_id"), "unidade")
            if not unidade_id:
                return jsonify({"error": "unidade_id inválido"}), 400
            unidade_s = str(unidade_id)

    data_inicio = _parse_date(body.get("data_inicio")) if body.get("data_inicio") else None
    clear_fim = body.get("data_fim") == ""
    data_fim = _parse_date(body.get("data_fim")) if body.get("data_fim") and not clear_fim else None

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
                UPDATE public.school_calendario_letivo
                SET titulo = COALESCE(%s, titulo),
                    tipo = COALESCE(%s, tipo),
                    data_inicio = COALESCE(%s, data_inicio),
                    data_fim = CASE
                        WHEN %s THEN NULL
                        WHEN %s IS NOT NULL THEN %s
                        ELSE data_fim
                    END,
                    unidade_id = CASE
                        WHEN %s THEN NULL
                        WHEN %s IS NOT NULL THEN %s::uuid
                        ELSE unidade_id
                    END,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s AND instituicao_id = %s
                RETURNING id, titulo, tipo, data_inicio, data_fim, unidade_id
                """,
                (
                    _text(body["titulo"]) if body.get("titulo") is not None else None,
                    tipo,
                    data_inicio,
                    clear_fim,
                    data_fim,
                    data_fim,
                    clear_unidade,
                    unidade_s,
                    unidade_s,
                    str(cid),
                    inst,
                ),
            )
            row = cur.fetchone()
    if not row:
        return jsonify({"error": "Evento de calendário não encontrado"}), 404
    return jsonify(
        {
            "item": {
                "id": str(row["id"]),
                "titulo": row["titulo"],
                "tipo": row["tipo"],
                "data_inicio": _iso(row["data_inicio"]),
                "data_fim": _iso(row.get("data_fim")),
                "unidade_id": str(row["unidade_id"]) if row.get("unidade_id") else None,
            }
        }
    )


@bp.delete("/api/secretaria/calendario/<item_id>")
@require_gestor
def delete_calendario(item_id: str):
    inst = _instituicao_id()
    cid = _parse_uuid(item_id, "calendário")
    if not cid:
        return jsonify({"error": "Identificador inválido"}), 400
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                DELETE FROM public.school_calendario_letivo
                WHERE id = %s AND instituicao_id = %s
                RETURNING id
                """,
                (str(cid), inst),
            )
            deleted = cur.fetchone()
    if not deleted:
        return jsonify({"error": "Evento de calendário não encontrado"}), 404
    return jsonify({"ok": True, "id": str(cid)})


# ---------------------------------------------------------------------------
# Professores (dropdown alocação)
# ---------------------------------------------------------------------------
@bp.get("/api/secretaria/professores")
@require_gestor
def list_professores_equipe():
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


def _build_teacher_allocated_payload(
    *,
    inst: str,
    aloc_id: str,
    unidade: dict,
    periodo: dict,
    disc: dict,
    prof: dict,
    turma: dict | None,
    instituicao_nome: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "professor_b2c_id": str(prof["professor_b2c_id"]),
        "disciplina_nome": disc["nome"],
        "ementa_macro": disc.get("ementa") or "",
        "data_inicio_periodo": _iso(periodo.get("data_inicio")),
        "data_fim_periodo": _iso(periodo.get("data_fim")),
        "tipo_periodo": periodo.get("tipo_periodo") or "semestral",
        "instituicao_id": inst,
        "instituicao_nome": (instituicao_nome or "").strip() or None,
        "unidade_id": str(unidade["id"]),
        "unidade_nome": unidade["nome"],
        "periodo_id": str(periodo["id"]),
        "periodo_nome": periodo["rotulo"],
        "disciplina_id": str(disc["id"]),
        "alocacao_id": str(aloc_id),
        "professor_email": prof.get("email_convite"),
        "vinculo_id": str(prof["id"]) if prof.get("id") else None,
    }
    curso_id = disc.get("curso_id") or (turma or {}).get("curso_id")
    curso_nome = disc.get("curso_nome") or (turma or {}).get("curso_nome")
    if curso_id:
        payload["curso_id"] = str(curso_id)
        payload["curso_nome"] = (curso_nome or "").strip() or "Curso"
    if turma:
        payload["turma_id"] = str(turma["id"])
        payload["turma_nome"] = turma["nome"]
        if turma.get("turno"):
            payload["turma_turno"] = turma.get("turno")
    return payload


def _mark_alocacao_notificado(aloc_id: str) -> None:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE public.school_alocacoes_docentes
                SET notificado_b2c = TRUE, updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
                """,
                (str(aloc_id),),
            )


def _dispatch_alocacao_b2c(payload: dict[str, Any]) -> dict[str, Any]:
    from b2c_integration_service import dispatch_teacher_allocated

    try:
        dispatch = dispatch_teacher_allocated(payload)
    except Exception as exc:
        return {"ok": False, "error": str(exc)}
    if dispatch.get("ok"):
        _mark_alocacao_notificado(payload["alocacao_id"])
    return dispatch


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
                    a.turma_id,
                    t.nome AS turma_nome,
                    a.ativo,
                    a.notificado_b2c,
                    a.created_at
                FROM public.school_alocacoes_docentes a
                JOIN public.school_unidades u ON u.id = a.unidade_id
                JOIN public.school_periodos_letivos p ON p.id = a.periodo_id
                JOIN public.school_disciplinas d ON d.id = a.disciplina_id
                JOIN public.school_professores_vinculo v ON v.id = a.professor_vinculo_id
                LEFT JOIN public.school_turmas t ON t.id = a.turma_id
                WHERE a.instituicao_id = %s
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
                    "turma_id": str(r["turma_id"]) if r.get("turma_id") else None,
                    "turma_nome": r.get("turma_nome"),
                    "ativo": bool(r.get("ativo")),
                    "data_inicio_periodo": _iso(r.get("data_inicio_periodo")),
                    "notificado_b2c": bool(r.get("notificado_b2c")),
                    "created_at": _iso(r.get("created_at")),
                }
                for r in rows
            ]
        }
    )


@bp.post("/api/secretaria/alocacoes")
@require_gestor
def create_alocacao():
    inst = _instituicao_id()
    body = request.get_json(silent=True) or {}
    unidade_id = _parse_uuid(body.get("unidade_id"), "unidade")
    periodo_id = _parse_uuid(body.get("periodo_id"), "periodo")
    disciplina_id = _parse_uuid(body.get("disciplina_id"), "disciplina")
    professor_id = _parse_uuid(
        body.get("professor_id") or body.get("professor_vinculo_id"), "professor"
    )
    turma_id = None
    if body.get("turma_id") not in (None, ""):
        turma_id = _parse_uuid(body.get("turma_id"), "turma")
        if not turma_id:
            return jsonify({"error": "turma_id inválido"}), 400
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
                SELECT id, rotulo, data_inicio, data_fim, tipo_periodo
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
                SELECT d.id, d.nome, d.ementa, d.curso_id, d.instituicao_id,
                       c.nome AS curso_nome,
                       p.instituicao_id AS periodo_inst
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

            cur.execute(
                "SELECT nome FROM public.school_instituicoes WHERE id = %s",
                (inst,),
            )
            inst_row = cur.fetchone()
            instituicao_nome = (inst_row or {}).get("nome")

            turma = None
            if turma_id:
                cur.execute(
                    """
                    SELECT t.id, t.nome, t.turno, t.curso_id, c.nome AS curso_nome
                    FROM public.school_turmas t
                    LEFT JOIN public.school_cursos c ON c.id = t.curso_id
                    WHERE t.id = %s AND t.instituicao_id = %s AND t.ativa = TRUE
                    """,
                    (str(turma_id), inst),
                )
                turma = cur.fetchone()
                if not turma:
                    return jsonify({"error": "turma inválida"}), 400

            try:
                cur.execute(
                    """
                    INSERT INTO public.school_alocacoes_docentes (
                        instituicao_id, unidade_id, periodo_id,
                        disciplina_id, professor_vinculo_id, turma_id
                    )
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (
                        inst,
                        str(unidade_id),
                        str(periodo_id),
                        str(disciplina_id),
                        str(professor_id),
                        str(turma_id) if turma_id else None,
                    ),
                )
                aloc = cur.fetchone()
            except pg_errors.UniqueViolation:
                conn.rollback()
                return jsonify({"error": "Esta alocação já existe"}), 409

            periodo_full = {
                "id": periodo["id"],
                "rotulo": periodo["rotulo"],
                "data_inicio": periodo["data_inicio"],
                "data_fim": periodo.get("data_fim"),
                "tipo_periodo": periodo.get("tipo_periodo"),
            }
            disc_full = {
                "id": disc["id"],
                "nome": disc["nome"],
                "ementa": disc.get("ementa"),
                "curso_id": disc.get("curso_id"),
                "curso_nome": disc.get("curso_nome"),
            }
            payload_b2c = _build_teacher_allocated_payload(
                inst=inst,
                aloc_id=str(aloc["id"]),
                unidade=unidade,
                periodo=periodo_full,
                disc=disc_full,
                prof=prof,
                turma=turma,
                instituicao_nome=instituicao_nome,
            )

    dispatch = _dispatch_alocacao_b2c(payload_b2c)
    return (
        jsonify(
            {
                "item": {
                    "id": str(aloc["id"]),
                    "unidade_id": str(unidade_id),
                    "periodo_id": str(periodo_id),
                    "disciplina_id": str(disciplina_id),
                    "professor_id": str(professor_id),
                    "turma_id": str(turma_id) if turma_id else None,
                    "turma_nome": turma["nome"] if turma else None,
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


@bp.put("/api/secretaria/alocacoes/<item_id>")
@require_gestor
def update_alocacao(item_id: str):
    inst = _instituicao_id()
    aid = _parse_uuid(item_id, "alocação")
    if not aid:
        return jsonify({"error": "Identificador inválido"}), 400
    body = request.get_json(silent=True) or {}

    unidade_s = None
    if body.get("unidade_id") not in (None, ""):
        uid = _parse_uuid(body.get("unidade_id"), "unidade")
        if not uid:
            return jsonify({"error": "unidade_id inválido"}), 400
        unidade_s = str(uid)

    periodo_s = None
    if body.get("periodo_id") not in (None, ""):
        pid = _parse_uuid(body.get("periodo_id"), "periodo")
        if not pid:
            return jsonify({"error": "periodo_id inválido"}), 400
        periodo_s = str(pid)

    disciplina_s = None
    if body.get("disciplina_id") not in (None, ""):
        did = _parse_uuid(body.get("disciplina_id"), "disciplina")
        if not did:
            return jsonify({"error": "disciplina_id inválido"}), 400
        disciplina_s = str(did)

    professor_s = None
    prof_raw = body.get("professor_id", body.get("professor_vinculo_id"))
    if prof_raw not in (None, ""):
        prid = _parse_uuid(prof_raw, "professor")
        if not prid:
            return jsonify({"error": "professor_id inválido"}), 400
        professor_s = str(prid)

    turma_s = None
    clear_turma = False
    if "turma_id" in body:
        if body.get("turma_id") in (None, ""):
            clear_turma = True
        else:
            tid = _parse_uuid(body.get("turma_id"), "turma")
            if not tid:
                return jsonify({"error": "turma_id inválido"}), 400
            turma_s = str(tid)

    activating = "ativo" in body and bool(body["ativo"])
    should_redispatch = activating or "turma_id" in body

    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            if unidade_s:
                cur.execute(
                    "SELECT 1 FROM public.school_unidades WHERE id = %s AND instituicao_id = %s",
                    (unidade_s, inst),
                )
                if not cur.fetchone():
                    return jsonify({"error": "unidade inválida"}), 400
            if periodo_s:
                cur.execute(
                    "SELECT 1 FROM public.school_periodos_letivos WHERE id = %s AND instituicao_id = %s",
                    (periodo_s, inst),
                )
                if not cur.fetchone():
                    return jsonify({"error": "período inválido"}), 400
            if disciplina_s:
                cur.execute(
                    """
                    SELECT d.id
                    FROM public.school_disciplinas d
                    LEFT JOIN public.school_cursos c ON c.id = d.curso_id
                    LEFT JOIN public.school_periodos_letivos p ON p.id = c.periodo_letivo_id
                    WHERE d.id = %s AND (d.instituicao_id = %s OR p.instituicao_id = %s)
                    """,
                    (disciplina_s, inst, inst),
                )
                if not cur.fetchone():
                    return jsonify({"error": "disciplina inválida"}), 400
            if professor_s:
                cur.execute(
                    """
                    SELECT 1 FROM public.school_professores_vinculo
                    WHERE id = %s AND instituicao_id = %s
                      AND status_vinculo IN ('ativo', 'pendente')
                    """,
                    (professor_s, inst),
                )
                if not cur.fetchone():
                    return jsonify({"error": "professor inválido ou inativo"}), 400
            if turma_s:
                cur.execute(
                    "SELECT 1 FROM public.school_turmas WHERE id = %s AND instituicao_id = %s",
                    (turma_s, inst),
                )
                if not cur.fetchone():
                    return jsonify({"error": "turma inválida"}), 400

            try:
                cur.execute(
                    """
                    UPDATE public.school_alocacoes_docentes
                    SET unidade_id = COALESCE(%s, unidade_id),
                        periodo_id = COALESCE(%s, periodo_id),
                        disciplina_id = COALESCE(%s, disciplina_id),
                        professor_vinculo_id = COALESCE(%s, professor_vinculo_id),
                        turma_id = CASE
                            WHEN %s THEN NULL
                            WHEN %s IS NOT NULL THEN %s::uuid
                            ELSE turma_id
                        END,
                        ativo = COALESCE(%s, ativo),
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s AND instituicao_id = %s
                    RETURNING id
                    """,
                    (
                        unidade_s,
                        periodo_s,
                        disciplina_s,
                        professor_s,
                        clear_turma,
                        turma_s,
                        turma_s,
                        bool(body["ativo"]) if "ativo" in body else None,
                        str(aid),
                        inst,
                    ),
                )
                if not cur.fetchone():
                    return jsonify({"error": "Alocação não encontrada"}), 404
            except pg_errors.UniqueViolation:
                conn.rollback()
                return jsonify({"error": "Esta alocação já existe"}), 409

            cur.execute(
                """
                SELECT
                    a.id,
                    u.id AS unidade_id,
                    u.nome AS unidade_nome,
                    p.id AS periodo_id,
                    p.rotulo,
                    p.data_inicio,
                    p.data_fim,
                    p.tipo_periodo,
                    d.id AS disciplina_id,
                    d.nome AS disciplina_nome,
                    d.ementa,
                    d.curso_id,
                    c.nome AS curso_nome,
                    v.id AS professor_vinculo_id,
                    v.professor_b2c_id,
                    v.email_convite,
                    a.turma_id,
                    t.nome AS turma_nome,
                    t.curso_id AS turma_curso_id,
                    i.nome AS instituicao_nome,
                    a.ativo,
                    a.notificado_b2c
                FROM public.school_alocacoes_docentes a
                JOIN public.school_unidades u ON u.id = a.unidade_id
                JOIN public.school_periodos_letivos p ON p.id = a.periodo_id
                JOIN public.school_disciplinas d ON d.id = a.disciplina_id
                JOIN public.school_professores_vinculo v ON v.id = a.professor_vinculo_id
                JOIN public.school_instituicoes i ON i.id = a.instituicao_id
                LEFT JOIN public.school_cursos c ON c.id = d.curso_id
                LEFT JOIN public.school_turmas t ON t.id = a.turma_id
                WHERE a.id = %s
                """,
                (str(aid),),
            )
            ctx = cur.fetchone()

    dispatch: dict[str, Any] = {"ok": False, "skipped": True}
    if ctx and ctx["ativo"] and (should_redispatch or not ctx["notificado_b2c"]):
        turma_row = None
        if ctx.get("turma_id"):
            turma_row = {
                "id": ctx["turma_id"],
                "nome": ctx.get("turma_nome") or "",
                "curso_id": ctx.get("turma_curso_id"),
                "curso_nome": ctx.get("curso_nome"),
            }
        payload_b2c = _build_teacher_allocated_payload(
            inst=inst,
            aloc_id=str(ctx["id"]),
            unidade={"id": ctx["unidade_id"], "nome": ctx["unidade_nome"]},
            periodo={
                "id": ctx["periodo_id"],
                "rotulo": ctx["rotulo"],
                "data_inicio": ctx["data_inicio"],
                "data_fim": ctx.get("data_fim"),
                "tipo_periodo": ctx.get("tipo_periodo"),
            },
            disc={
                "id": ctx["disciplina_id"],
                "nome": ctx["disciplina_nome"],
                "ementa": ctx.get("ementa"),
                "curso_id": ctx.get("curso_id"),
                "curso_nome": ctx.get("curso_nome"),
            },
            prof={
                "id": ctx["professor_vinculo_id"],
                "professor_b2c_id": ctx["professor_b2c_id"],
                "email_convite": ctx.get("email_convite"),
            },
            turma=turma_row,
            instituicao_nome=ctx.get("instituicao_nome"),
        )
        dispatch = _dispatch_alocacao_b2c(payload_b2c)

    return jsonify(
        {
            "item": {
                "id": str(ctx["id"]),
                "unidade_id": str(ctx["unidade_id"]),
                "periodo_id": str(ctx["periodo_id"]),
                "disciplina_id": str(ctx["disciplina_id"]),
                "professor_id": str(ctx["professor_vinculo_id"]),
                "turma_id": str(ctx["turma_id"]) if ctx.get("turma_id") else None,
                "turma_nome": ctx.get("turma_nome"),
                "ativo": bool(ctx["ativo"]),
                "notificado_b2c": bool(dispatch.get("ok") or ctx.get("notificado_b2c")),
            },
            "b2c_dispatch": dispatch,
        }
    )


# ---------------------------------------------------------------------------
# Comunicações / Mural (push → inove4us B2C)
# ---------------------------------------------------------------------------
COM_TIPOS = frozenset({"reuniao_pedagogica", "evento_escolar"})
COM_PUBLICOS = frozenset({"toda_instituicao", "unidade", "turma", "professores"})
COM_STATUS = frozenset({"agendado", "publicado", "cancelado"})

COM_TIPO_LABEL = {
    "reuniao_pedagogica": "Reunião pedagógica",
    "evento_escolar": "Evento escolar",
}
COM_PUBLICO_LABEL = {
    "toda_instituicao": "Toda a instituição",
    "unidade": "Unidade",
    "turma": "Turma",
    "professores": "Professores",
}
COM_STATUS_LABEL = {
    "agendado": "Agendado",
    "publicado": "Publicado",
    "cancelado": "Cancelado",
}


def _parse_dt_local(value: Any, *, required: bool = True):
    if value is None or str(value).strip() == "":
        if required:
            return None
        return None
    text = str(value).strip().replace("Z", "+00:00")
    try:
        if len(text) == 16:
            text = text + ":00"
        return datetime.fromisoformat(text)
    except ValueError:
        return False


def _serialize_comunicacao(row: dict[str, Any]) -> dict:
    tipo = row["tipo"]
    publico = row["publico_alvo"]
    status = row["status"]
    return {
        "id": str(row["id"]),
        "titulo": row["titulo"],
        "descricao": row.get("descricao") or "",
        "tipo": tipo,
        "tipo_label": COM_TIPO_LABEL.get(tipo, tipo),
        "publico_alvo": publico,
        "publico_label": COM_PUBLICO_LABEL.get(publico, publico),
        "status": status,
        "status_label": COM_STATUS_LABEL.get(status, status),
        "data_hora_inicio": _iso(row.get("data_hora_inicio")),
        "data_hora_fim": _iso(row.get("data_hora_fim")),
        "unidade_id": str(row["unidade_id"]) if row.get("unidade_id") else None,
        "replicado_b2c": bool(row.get("replicado_b2c")),
        "created_at": _iso(row.get("created_at")),
    }


def _resolve_professor_targets(cur, inst: str, publico: str, unidade_id: str | None):
    if publico == "unidade" and unidade_id:
        pass
    cur.execute(
        """
        SELECT email_convite, professor_b2c_id
        FROM public.school_professores_vinculo
        WHERE instituicao_id = %s
          AND status_vinculo IN ('ativo', 'pendente')
        """,
        (inst,),
    )
    emails: list[str] = []
    ids: list[int] = []
    for r in cur.fetchall():
        email = str(r.get("email_convite") or "").strip().lower()
        if email and "@" in email and email not in emails:
            emails.append(email)
        try:
            n = int(r.get("professor_b2c_id"))
        except (TypeError, ValueError):
            continue
        # Só id_clie real (positivo); provisórios da Equipe são negativos
        if n > 0 and n not in ids:
            ids.append(n)
    return emails, ids


def _push_comunicacao_row(cur, row: dict[str, Any], inst: str) -> dict[str, Any]:
    emails, ids = _resolve_professor_targets(
        cur, inst, row["publico_alvo"], str(row["unidade_id"]) if row.get("unidade_id") else None
    )
    from b2c_integration_service import push_comunicado_to_b2c

    payload = {
        "origem_comunicado_school_id": str(row["id"]),
        "instituicao_escola_id": inst,
        "titulo": row["titulo"],
        "descricao": row.get("descricao") or "",
        "tipo": row["tipo"],
        "data_hora_inicio": _iso(row.get("data_hora_inicio")),
        "data_hora_fim": _iso(row.get("data_hora_fim")),
        "status": row["status"],
        "professor_emails": emails,
        "professor_b2c_ids": ids,
    }
    return push_comunicado_to_b2c(payload)


@bp.get("/api/secretaria/comunicacoes")
@require_gestor
def list_comunicacoes():
    inst = _instituicao_id()
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT *
                FROM public.school_comunicacoes_eventos
                WHERE instituicao_id = %s
                  AND status <> 'cancelado'
                ORDER BY data_hora_inicio DESC, created_at DESC
                """,
                (inst,),
            )
            rows = [_serialize_comunicacao(r) for r in cur.fetchall()]
    return jsonify({"items": rows})


@bp.post("/api/secretaria/comunicacoes")
@require_gestor
def create_comunicacao():
    inst = _instituicao_id()
    body = request.get_json(silent=True) or {}
    titulo = _text(body.get("titulo"))
    if not titulo:
        return jsonify({"error": "Título obrigatório"}), 400
    tipo = _text(body.get("tipo")) or "reuniao_pedagogica"
    if tipo not in COM_TIPOS:
        return jsonify({"error": "Tipo inválido"}), 400
    publico = _text(body.get("publico_alvo")) or "professores"
    if publico not in COM_PUBLICOS:
        return jsonify({"error": "Público-alvo inválido"}), 400
    status = _text(body.get("status")) or "publicado"
    if status not in COM_STATUS:
        return jsonify({"error": "Status inválido"}), 400

    inicio = _parse_dt_local(body.get("data_hora_inicio"), required=True)
    if inicio is False or inicio is None:
        return jsonify({"error": "data_hora_inicio inválida ou obrigatória"}), 400
    fim = _parse_dt_local(body.get("data_hora_fim"), required=False)
    if fim is False:
        return jsonify({"error": "data_hora_fim inválida"}), 400

    unidade = _parse_uuid(body.get("unidade_id"), "unidade") if body.get("unidade_id") else None
    if publico == "unidade" and not unidade:
        return jsonify({"error": "Selecione a unidade"}), 400
    if publico in ("toda_instituicao", "professores"):
        unidade = None

    descricao = _text(body.get("descricao")) or None
    gestor = session.get(SESSION_KEY) or {}
    gestor_id = _parse_uuid(gestor.get("id"), "gestor")

    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                INSERT INTO public.school_comunicacoes_eventos (
                    instituicao_id, unidade_id, titulo, descricao, tipo,
                    data_hora_inicio, data_hora_fim, publico_alvo,
                    status, criado_por_gestor_id
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
                RETURNING *
                """,
                (
                    inst,
                    str(unidade) if unidade else None,
                    titulo,
                    descricao,
                    tipo,
                    inicio,
                    fim,
                    publico,
                    status,
                    str(gestor_id) if gestor_id else None,
                ),
            )
            row = cur.fetchone()

    dispatch: dict[str, Any] = {"ok": False, "skipped": True}
    if status == "publicado":
        with get_conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                dispatch = _push_comunicacao_row(cur, row, inst)
                if dispatch.get("ok"):
                    cur.execute(
                        """
                        UPDATE public.school_comunicacoes_eventos
                        SET replicado_b2c = TRUE,
                            replicado_b2c_em = CURRENT_TIMESTAMP,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = %s
                        RETURNING *
                        """,
                        (str(row["id"]),),
                    )
                    row = cur.fetchone() or row

    return (
        jsonify(
            {
                "item": _serialize_comunicacao(row),
                "b2c_dispatch": dispatch,
                "message": (
                    "Comunicado publicado no mural dos professores."
                    if dispatch.get("ok")
                    else (
                        "Comunicado salvo."
                        + (
                            " Push ao mural pendente."
                            if status == "publicado"
                            else ""
                        )
                    )
                ),
            }
        ),
        201,
    )


@bp.patch("/api/secretaria/comunicacoes/<item_id>")
@require_gestor
def patch_comunicacao(item_id: str):
    inst = _instituicao_id()
    cid = _parse_uuid(item_id, "comunicação")
    if not cid:
        return jsonify({"error": "Identificador inválido"}), 400
    body = request.get_json(silent=True) or {}
    status = _text(body.get("status"))
    if status not in COM_STATUS:
        return jsonify({"error": "Status inválido"}), 400

    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                UPDATE public.school_comunicacoes_eventos
                SET status = %s, updated_at = CURRENT_TIMESTAMP
                WHERE id = %s AND instituicao_id = %s
                RETURNING *
                """,
                (status, str(cid), inst),
            )
            row = cur.fetchone()
            if not row:
                return jsonify({"error": "Comunicação não encontrada"}), 404

    dispatch: dict[str, Any] = {"ok": False, "skipped": True}
    if status in ("publicado", "cancelado"):
        with get_conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                dispatch = _push_comunicacao_row(cur, row, inst)
                if dispatch.get("ok") and status == "publicado":
                    cur.execute(
                        """
                        UPDATE public.school_comunicacoes_eventos
                        SET replicado_b2c = TRUE,
                            replicado_b2c_em = CURRENT_TIMESTAMP
                        WHERE id = %s
                        RETURNING *
                        """,
                        (str(cid),),
                    )
                    row = cur.fetchone() or row

    return jsonify(
        {
            "item": _serialize_comunicacao(row),
            "b2c_dispatch": dispatch,
        }
    )


# ---------------------------------------------------------------------------
# Planejamento Escolar (push Secretaria → B2C)
# ---------------------------------------------------------------------------
def _serialize_planejamento(r: dict) -> dict[str, Any]:
    resp = r.get("resposta_b2c_json")
    if isinstance(resp, str):
        try:
            resp = json.loads(resp)
        except Exception:
            pass
    return {
        "id": str(r["id"]),
        "turma_id": str(r["turma_id"]),
        "turma_nome": r.get("turma_nome"),
        "disciplina_id": str(r["disciplina_id"]),
        "disciplina_nome": r.get("disciplina_nome"),
        "professor_vinculo_id": str(r["professor_vinculo_id"]),
        "professor_email": r.get("professor_email"),
        "professor_b2c_id": int(r["professor_b2c_id"])
        if r.get("professor_b2c_id") is not None
        else None,
        "titulo": r["titulo"],
        "tipo": r["tipo"],
        "data": _iso(r.get("data")),
        "hora_inicio": _time_iso(r.get("hora_inicio")),
        "hora_fim": _time_iso(r.get("hora_fim")),
        "observacoes": r.get("observacoes") or "",
        "item_pai_id": str(r["item_pai_id"]) if r.get("item_pai_id") else None,
        "status_push": r["status_push"],
        "enviado_em": _iso(r.get("enviado_em")),
        "resposta_b2c_json": resp,
        "created_at": _iso(r.get("created_at")),
        "updated_at": _iso(r.get("updated_at")),
    }


def _resolve_alocacao_professor(
    cur, inst: str, turma_id: str, disciplina_id: str
) -> dict | None:
    cur.execute(
        """
        SELECT a.professor_vinculo_id, v.email_convite, v.professor_b2c_id
        FROM public.school_alocacoes_docentes a
        JOIN public.school_professores_vinculo v ON v.id = a.professor_vinculo_id
        WHERE a.instituicao_id = %s
          AND a.turma_id = %s
          AND a.disciplina_id = %s
          AND a.ativo = TRUE
          AND v.status_vinculo IN ('ativo', 'pendente')
        ORDER BY a.created_at DESC
        LIMIT 1
        """,
        (inst, turma_id, disciplina_id),
    )
    return cur.fetchone()


@bp.get("/api/secretaria/planejamento")
@require_gestor
def list_planejamento():
    inst = _instituicao_id()
    turma_id = _parse_uuid(request.args.get("turma_id"), "turma")
    status_push = _text(request.args.get("status_push")) or None
    if status_push and status_push not in PLAN_STATUS:
        return jsonify({"error": "status_push inválido"}), 400

    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            sql = """
                SELECT p.*,
                       t.nome AS turma_nome,
                       d.nome AS disciplina_nome,
                       v.email_convite AS professor_email,
                       v.professor_b2c_id
                FROM public.school_planejamento_escolar p
                JOIN public.school_turmas t ON t.id = p.turma_id
                JOIN public.school_disciplinas d ON d.id = p.disciplina_id
                JOIN public.school_professores_vinculo v
                  ON v.id = p.professor_vinculo_id
                WHERE p.instituicao_id = %s
            """
            params: list[Any] = [inst]
            if turma_id:
                sql += " AND p.turma_id = %s"
                params.append(str(turma_id))
            if status_push:
                sql += " AND p.status_push = %s"
                params.append(status_push)
            sql += " ORDER BY p.data ASC, p.hora_inicio ASC NULLS LAST, p.created_at ASC"
            cur.execute(sql, params)
            rows = cur.fetchall()
    return jsonify({"items": [_serialize_planejamento(r) for r in rows]})


@bp.post("/api/secretaria/planejamento")
@require_gestor
def create_planejamento():
    inst = _instituicao_id()
    body = request.get_json(silent=True) or {}
    turma_id = _parse_uuid(body.get("turma_id"), "turma")
    disciplina_id = _parse_uuid(body.get("disciplina_id"), "disciplina")
    titulo = _text(body.get("titulo"))
    tipo = _text(body.get("tipo")) or "aula"
    data_ref = _parse_date(body.get("data"))
    hora_inicio = _parse_time(body.get("hora_inicio"))
    hora_fim = _parse_time(body.get("hora_fim"))
    observacoes = _text(body.get("observacoes")) or None
    item_pai_id = None
    if body.get("item_pai_id") not in (None, ""):
        item_pai_id = _parse_uuid(body.get("item_pai_id"), "item_pai")
        if not item_pai_id:
            return jsonify({"error": "item_pai_id inválido"}), 400

    if not turma_id:
        return jsonify({"error": "turma_id é obrigatório"}), 400
    if not disciplina_id:
        return jsonify({"error": "disciplina_id é obrigatório"}), 400
    if not titulo:
        return jsonify({"error": "titulo é obrigatório"}), 400
    if tipo not in PLAN_TIPOS:
        return jsonify({"error": "tipo inválido"}), 400
    if not data_ref:
        return jsonify({"error": "data é obrigatória"}), 400

    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT 1 FROM public.school_turmas
                WHERE id = %s AND instituicao_id = %s
                """,
                (str(turma_id), inst),
            )
            if not cur.fetchone():
                return jsonify({"error": "turma inválida"}), 400

            cur.execute(
                """
                SELECT d.id
                FROM public.school_disciplinas d
                LEFT JOIN public.school_cursos c ON c.id = d.curso_id
                LEFT JOIN public.school_periodos_letivos p ON p.id = c.periodo_letivo_id
                WHERE d.id = %s
                  AND (d.instituicao_id = %s OR p.instituicao_id = %s)
                """,
                (str(disciplina_id), inst, inst),
            )
            if not cur.fetchone():
                return jsonify({"error": "disciplina inválida"}), 400

            aloc = _resolve_alocacao_professor(
                cur, inst, str(turma_id), str(disciplina_id)
            )
            if not aloc:
                return (
                    jsonify(
                        {
                            "error": (
                                "Nenhum professor alocado pra essa turma/disciplina ainda. "
                                "Faça a alocação docente na Estrutura Acadêmica."
                            )
                        }
                    ),
                    422,
                )

            if item_pai_id:
                cur.execute(
                    """
                    SELECT 1 FROM public.school_planejamento_escolar
                    WHERE id = %s AND instituicao_id = %s AND turma_id = %s
                    """,
                    (str(item_pai_id), inst, str(turma_id)),
                )
                if not cur.fetchone():
                    return jsonify({"error": "item_pai_id inválido para esta turma"}), 400

            cur.execute(
                """
                INSERT INTO public.school_planejamento_escolar (
                    instituicao_id, turma_id, disciplina_id, professor_vinculo_id,
                    titulo, tipo, data, hora_inicio, hora_fim, observacoes, item_pai_id
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    inst,
                    str(turma_id),
                    str(disciplina_id),
                    str(aloc["professor_vinculo_id"]),
                    titulo,
                    tipo,
                    data_ref,
                    hora_inicio,
                    hora_fim,
                    observacoes,
                    str(item_pai_id) if item_pai_id else None,
                ),
            )
            new_id = cur.fetchone()["id"]
            cur.execute(
                """
                SELECT p.*,
                       t.nome AS turma_nome,
                       d.nome AS disciplina_nome,
                       v.email_convite AS professor_email,
                       v.professor_b2c_id
                FROM public.school_planejamento_escolar p
                JOIN public.school_turmas t ON t.id = p.turma_id
                JOIN public.school_disciplinas d ON d.id = p.disciplina_id
                JOIN public.school_professores_vinculo v
                  ON v.id = p.professor_vinculo_id
                WHERE p.id = %s
                """,
                (str(new_id),),
            )
            row = cur.fetchone()
    return jsonify({"item": _serialize_planejamento(row)}), 201


@bp.put("/api/secretaria/planejamento/<item_id>")
@require_gestor
def update_planejamento(item_id: str):
    inst = _instituicao_id()
    pid = _parse_uuid(item_id, "planejamento")
    if not pid:
        return jsonify({"error": "Identificador inválido"}), 400
    body = request.get_json(silent=True) or {}

    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT * FROM public.school_planejamento_escolar
                WHERE id = %s AND instituicao_id = %s
                """,
                (str(pid), inst),
            )
            current = cur.fetchone()
            if not current:
                return jsonify({"error": "Item não encontrado"}), 404
            if current["status_push"] != "rascunho":
                return (
                    jsonify({"error": "Só é possível editar itens em rascunho"}),
                    409,
                )

            turma_id = current["turma_id"]
            disciplina_id = current["disciplina_id"]
            if body.get("turma_id") not in (None, ""):
                tid = _parse_uuid(body.get("turma_id"), "turma")
                if not tid:
                    return jsonify({"error": "turma_id inválido"}), 400
                turma_id = tid
            if body.get("disciplina_id") not in (None, ""):
                did = _parse_uuid(body.get("disciplina_id"), "disciplina")
                if not did:
                    return jsonify({"error": "disciplina_id inválido"}), 400
                disciplina_id = did

            aloc = _resolve_alocacao_professor(
                cur, inst, str(turma_id), str(disciplina_id)
            )
            if not aloc:
                return (
                    jsonify(
                        {
                            "error": (
                                "Nenhum professor alocado pra essa turma/disciplina ainda. "
                                "Faça a alocação docente na Estrutura Acadêmica."
                            )
                        }
                    ),
                    422,
                )

            tipo = _text(body.get("tipo")) if body.get("tipo") is not None else None
            if tipo is not None and tipo not in PLAN_TIPOS:
                return jsonify({"error": "tipo inválido"}), 400

            data_ref = None
            if "data" in body:
                data_ref = _parse_date(body.get("data"))
                if not data_ref:
                    return jsonify({"error": "data inválida"}), 400

            hora_inicio = current.get("hora_inicio")
            clear_hi = False
            if "hora_inicio" in body:
                if body.get("hora_inicio") in (None, ""):
                    clear_hi = True
                    hora_inicio = None
                else:
                    hora_inicio = _parse_time(body.get("hora_inicio"))
                    if hora_inicio is None:
                        return jsonify({"error": "hora_inicio inválida"}), 400

            hora_fim = current.get("hora_fim")
            clear_hf = False
            if "hora_fim" in body:
                if body.get("hora_fim") in (None, ""):
                    clear_hf = True
                    hora_fim = None
                else:
                    hora_fim = _parse_time(body.get("hora_fim"))
                    if hora_fim is None:
                        return jsonify({"error": "hora_fim inválida"}), 400

            item_pai_s = None
            clear_pai = False
            if "item_pai_id" in body:
                if body.get("item_pai_id") in (None, ""):
                    clear_pai = True
                else:
                    pai = _parse_uuid(body.get("item_pai_id"), "item_pai")
                    if not pai:
                        return jsonify({"error": "item_pai_id inválido"}), 400
                    if str(pai) == str(pid):
                        return jsonify({"error": "item não pode ser pai de si mesmo"}), 400
                    cur.execute(
                        """
                        SELECT 1 FROM public.school_planejamento_escolar
                        WHERE id = %s AND instituicao_id = %s AND turma_id = %s
                        """,
                        (str(pai), inst, str(turma_id)),
                    )
                    if not cur.fetchone():
                        return jsonify({"error": "item_pai_id inválido para esta turma"}), 400
                    item_pai_s = str(pai)

            cur.execute(
                """
                UPDATE public.school_planejamento_escolar
                SET turma_id = %s,
                    disciplina_id = %s,
                    professor_vinculo_id = %s,
                    titulo = COALESCE(%s, titulo),
                    tipo = COALESCE(%s, tipo),
                    data = COALESCE(%s, data),
                    hora_inicio = CASE
                        WHEN %s THEN NULL
                        WHEN %s THEN %s
                        ELSE hora_inicio
                    END,
                    hora_fim = CASE
                        WHEN %s THEN NULL
                        WHEN %s THEN %s
                        ELSE hora_fim
                    END,
                    observacoes = CASE WHEN %s THEN %s ELSE observacoes END,
                    item_pai_id = CASE
                        WHEN %s THEN NULL
                        WHEN %s IS NOT NULL THEN %s::uuid
                        ELSE item_pai_id
                    END,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s AND instituicao_id = %s
                RETURNING id
                """,
                (
                    str(turma_id),
                    str(disciplina_id),
                    str(aloc["professor_vinculo_id"]),
                    _text(body["titulo"]) if body.get("titulo") is not None else None,
                    tipo,
                    data_ref,
                    clear_hi,
                    "hora_inicio" in body and not clear_hi,
                    hora_inicio,
                    clear_hf,
                    "hora_fim" in body and not clear_hf,
                    hora_fim,
                    "observacoes" in body,
                    _text(body.get("observacoes")) or None,
                    clear_pai,
                    item_pai_s,
                    item_pai_s,
                    str(pid),
                    inst,
                ),
            )
            if not cur.fetchone():
                return jsonify({"error": "Item não encontrado"}), 404

            cur.execute(
                """
                SELECT p.*,
                       t.nome AS turma_nome,
                       d.nome AS disciplina_nome,
                       v.email_convite AS professor_email,
                       v.professor_b2c_id
                FROM public.school_planejamento_escolar p
                JOIN public.school_turmas t ON t.id = p.turma_id
                JOIN public.school_disciplinas d ON d.id = p.disciplina_id
                JOIN public.school_professores_vinculo v
                  ON v.id = p.professor_vinculo_id
                WHERE p.id = %s
                """,
                (str(pid),),
            )
            row = cur.fetchone()
    return jsonify({"item": _serialize_planejamento(row)})


@bp.delete("/api/secretaria/planejamento/<item_id>")
@require_gestor
def delete_planejamento(item_id: str):
    inst = _instituicao_id()
    pid = _parse_uuid(item_id, "planejamento")
    if not pid:
        return jsonify({"error": "Identificador inválido"}), 400
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT status_push FROM public.school_planejamento_escolar
                WHERE id = %s AND instituicao_id = %s
                """,
                (str(pid), inst),
            )
            row = cur.fetchone()
            if not row:
                return jsonify({"error": "Item não encontrado"}), 404
            if row["status_push"] != "rascunho":
                return (
                    jsonify({"error": "Só é possível excluir itens em rascunho"}),
                    409,
                )
            cur.execute(
                """
                DELETE FROM public.school_planejamento_escolar
                WHERE id = %s AND instituicao_id = %s
                """,
                (str(pid), inst),
            )
    return jsonify({"ok": True})


@bp.post("/api/secretaria/planejamento/enviar")
@require_gestor
def enviar_planejamento():
    """Envia rascunhos ao B2C. Aceita item_ids[] e/ou turma_id (todos os rascunhos da turma)."""
    inst = _instituicao_id()
    body = request.get_json(silent=True) or {}
    turma_id = _parse_uuid(body.get("turma_id"), "turma")
    raw_ids = body.get("item_ids") or []
    item_ids: list[str] = []
    if isinstance(raw_ids, list):
        for raw in raw_ids:
            uid = _parse_uuid(raw, "item")
            if uid:
                item_ids.append(str(uid))

    if not item_ids and not turma_id:
        return jsonify({"error": "Informe item_ids e/ou turma_id"}), 400

    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            sql = """
                SELECT p.*,
                       t.nome AS turma_nome,
                       d.nome AS disciplina_nome,
                       v.email_convite AS professor_email,
                       v.professor_b2c_id
                FROM public.school_planejamento_escolar p
                JOIN public.school_turmas t ON t.id = p.turma_id
                JOIN public.school_disciplinas d ON d.id = p.disciplina_id
                JOIN public.school_professores_vinculo v
                  ON v.id = p.professor_vinculo_id
                WHERE p.instituicao_id = %s
                  AND p.status_push IN ('rascunho', 'erro')
            """
            params: list[Any] = [inst]
            if item_ids:
                sql += " AND p.id = ANY(%s::uuid[])"
                params.append(item_ids)
            if turma_id:
                sql += " AND p.turma_id = %s"
                params.append(str(turma_id))
            sql += " ORDER BY p.data ASC, p.created_at ASC"
            cur.execute(sql, params)
            rows = cur.fetchall()

            if not rows:
                return jsonify({"error": "Nenhum item em rascunho/erro para enviar"}), 404

            # Agrupa por professor_b2c_id (contrato B2C: 1 professor por request)
            groups: dict[int | None, list[dict]] = {}
            for r in rows:
                try:
                    key = int(r["professor_b2c_id"]) if r.get("professor_b2c_id") is not None else None
                except (TypeError, ValueError):
                    key = None
                groups.setdefault(key, []).append(r)

            from b2c_integration_service import push_planejamento_to_b2c

            resultados: list[dict[str, Any]] = []
            for prof_id, group in groups.items():
                if prof_id is None or prof_id <= 0:
                    relatorio = {
                        "ok": False,
                        "error": (
                            "professor_b2c_id inválido ou provisório — "
                            "é necessário o id_clie real do B2C"
                        ),
                    }
                    for r in group:
                        cur.execute(
                            """
                            UPDATE public.school_planejamento_escolar
                            SET status_push = 'erro',
                                enviado_em = CURRENT_TIMESTAMP,
                                resposta_b2c_json = %s,
                                updated_at = CURRENT_TIMESTAMP
                            WHERE id = %s
                            """,
                            (Json(relatorio), str(r["id"])),
                        )
                        resultados.append(
                            {
                                "id": str(r["id"]),
                                "status_push": "erro",
                                "resposta": relatorio,
                            }
                        )
                    continue

                id_set = {str(r["id"]) for r in group}
                itens_payload = []
                for r in group:
                    pai = str(r["item_pai_id"]) if r.get("item_pai_id") else None
                    # Só envia vínculo pai se o pai está no mesmo lote
                    if pai and pai not in id_set:
                        pai = None
                    itens_payload.append(
                        {
                            "id_externo": str(r["id"]),
                            "titulo": r["titulo"],
                            "tipo": r["tipo"],
                            "data": _iso(r["data"]),
                            "hora_inicio": _time_iso(r.get("hora_inicio")),
                            "hora_fim": _time_iso(r.get("hora_fim")),
                            "vinculo_pai_id_externo": pai,
                            "observacoes": r.get("observacoes") or "",
                        }
                    )

                dispatch = push_planejamento_to_b2c(
                    {
                        "professor_b2c_id": prof_id,
                        "itens": itens_payload,
                    }
                )
                response = dispatch.get("response")
                per_item: dict[str, Any] = {}
                if isinstance(response, dict):
                    # Aceita {itens:[{id_externo, status/ok/...}]} ou {relatorio:[...]}
                    lista = (
                        response.get("itens")
                        or response.get("relatorio")
                        or response.get("items")
                        or response.get("resultados")
                    )
                    if isinstance(lista, list):
                        for entry in lista:
                            if not isinstance(entry, dict):
                                continue
                            ext = str(
                                entry.get("id_externo")
                                or entry.get("id")
                                or ""
                            )
                            if ext:
                                per_item[ext] = entry

                for r in group:
                    rid = str(r["id"])
                    item_rep = per_item.get(rid)
                    if dispatch.get("ok"):
                        # Sem relatório por item → sucesso do lote
                        if item_rep is None:
                            ok_item = True
                        else:
                            st = str(
                                item_rep.get("status")
                                or item_rep.get("resultado")
                                or ""
                            ).lower()
                            if "erro" in st or "error" in st or item_rep.get("ok") is False:
                                ok_item = False
                            else:
                                ok_item = True
                    else:
                        ok_item = False

                    status_push = "enviado" if ok_item else "erro"
                    resposta = {
                        "ok": bool(ok_item),
                        "http_ok": bool(dispatch.get("ok")),
                        "status_code": dispatch.get("status_code"),
                        "item": item_rep,
                        "lote": response if not item_rep else None,
                        "error": None if ok_item else (
                            dispatch.get("error")
                            or (item_rep or {}).get("error")
                            or (item_rep or {}).get("mensagem")
                            or "Falha no envio ao B2C"
                        ),
                    }
                    cur.execute(
                        """
                        UPDATE public.school_planejamento_escolar
                        SET status_push = %s,
                            enviado_em = CURRENT_TIMESTAMP,
                            resposta_b2c_json = %s,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = %s
                        """,
                        (status_push, Json(resposta), rid),
                    )
                    resultados.append(
                        {
                            "id": rid,
                            "status_push": status_push,
                            "resposta": resposta,
                        }
                    )

            # Retorna items atualizados
            ids_all = [str(r["id"]) for r in rows]
            cur.execute(
                """
                SELECT p.*,
                       t.nome AS turma_nome,
                       d.nome AS disciplina_nome,
                       v.email_convite AS professor_email,
                       v.professor_b2c_id
                FROM public.school_planejamento_escolar p
                JOIN public.school_turmas t ON t.id = p.turma_id
                JOIN public.school_disciplinas d ON d.id = p.disciplina_id
                JOIN public.school_professores_vinculo v
                  ON v.id = p.professor_vinculo_id
                WHERE p.id = ANY(%s::uuid[])
                ORDER BY p.data ASC, p.created_at ASC
                """,
                (ids_all,),
            )
            updated = cur.fetchall()

    enviados = sum(1 for x in resultados if x["status_push"] == "enviado")
    erros = sum(1 for x in resultados if x["status_push"] == "erro")
    return jsonify(
        {
            "ok": erros == 0 and enviados > 0,
            "enviados": enviados,
            "erros": erros,
            "resultados": resultados,
            "items": [_serialize_planejamento(r) for r in updated],
        }
    )

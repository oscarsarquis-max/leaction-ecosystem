"""Secretaria (zona operacional) — hierarquia alinhada ao B2C.

instituição → unidade → período letivo → curso → disciplina (ementa)
+ calendário letivo

Sem alunos (produto não controla dossiê de aluno na Secretaria).
Turmas/currículo antigo (série) ficam fora desta UI.
"""
from __future__ import annotations

import uuid
from datetime import date
from typing import Any

from flask import Blueprint, jsonify, request
from psycopg2.extras import RealDictCursor

from db import get_conn

bp = Blueprint("secretaria", __name__)

TIPOS_PERIODO = frozenset({"anual", "semestral", "trimestral", "modular"})
STATUS_PERIODO = frozenset({"planejamento", "em_andamento", "encerrado"})
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
CAL_TIPOS = frozenset({"letivo", "feriado", "avaliacao", "evento"})


def _parse_uuid(value: str | None, label: str, *, required: bool = True):
    if value is None or str(value).strip() == "":
        if required:
            return jsonify({"error": f"Identificador de {label} obrigatório"}), 400
        return None
    try:
        return uuid.UUID(str(value))
    except (ValueError, TypeError, AttributeError):
        return jsonify({"error": f"Identificador de {label} inválido"}), 400


def _parse_date(raw: Any, label: str, *, required: bool = True):
    if raw is None or str(raw).strip() == "":
        if required:
            return jsonify({"error": f"{label} obrigatório"}), 400
        return None
    try:
        return date.fromisoformat(str(raw)[:10])
    except ValueError:
        return jsonify({"error": f"Data inválida em {label}"}), 400


def _iso(d: Any) -> str | None:
    return d.isoformat() if d else None


# ---------------------------------------------------------------------------
# Unidades
# ---------------------------------------------------------------------------
@bp.get("/api/instituicoes/<instituicao_id>/unidades-gestao")
def list_unidades_gestao(instituicao_id: str):
    """Lista unidades com flag ativo (gestão Secretaria)."""
    inst = _parse_uuid(instituicao_id, "instituição")
    if isinstance(inst, tuple):
        return inst
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id, nome, codigo, cidade, uf, endereco, ativo
                FROM public.school_unidades
                WHERE instituicao_id = %s
                ORDER BY nome
                """,
                (str(inst),),
            )
            items = [
                {
                    "id": str(r["id"]),
                    "nome": r["nome"],
                    "codigo": r.get("codigo"),
                    "cidade": r.get("cidade"),
                    "uf": r.get("uf"),
                    "endereco": r.get("endereco"),
                    "ativo": bool(r["ativo"]),
                }
                for r in cur.fetchall()
            ]
    return jsonify({"items": items})


@bp.post("/api/instituicoes/<instituicao_id>/unidades")
def create_unidade(instituicao_id: str):
    inst = _parse_uuid(instituicao_id, "instituição")
    if isinstance(inst, tuple):
        return inst
    body = request.get_json(silent=True) or {}
    nome = str(body.get("nome") or "").strip()
    if not nome:
        return jsonify({"error": "Nome obrigatório"}), 400
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            try:
                cur.execute(
                    """
                    INSERT INTO public.school_unidades
                        (instituicao_id, nome, codigo, cidade, uf, endereco)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING id, nome, codigo, cidade, uf, endereco, ativo
                    """,
                    (
                        str(inst),
                        nome,
                        str(body.get("codigo") or "").strip() or None,
                        str(body.get("cidade") or "").strip() or None,
                        str(body.get("uf") or "").strip() or None,
                        str(body.get("endereco") or "").strip() or None,
                    ),
                )
            except Exception as exc:
                if "uq_" in str(exc) or "unique" in str(exc).lower():
                    return jsonify({"error": "Já existe unidade com este nome"}), 409
                raise
            r = cur.fetchone()
    return (
        jsonify(
            {
                "item": {
                    "id": str(r["id"]),
                    "nome": r["nome"],
                    "codigo": r.get("codigo"),
                    "cidade": r.get("cidade"),
                    "uf": r.get("uf"),
                    "endereco": r.get("endereco"),
                    "ativo": bool(r["ativo"]),
                }
            }
        ),
        201,
    )


@bp.put("/api/unidades/<unidade_id>")
def update_unidade(unidade_id: str):
    uid = _parse_uuid(unidade_id, "unidade")
    if isinstance(uid, tuple):
        return uid
    body = request.get_json(silent=True) or {}
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                UPDATE public.school_unidades
                SET nome = COALESCE(%s, nome),
                    codigo = COALESCE(%s, codigo),
                    cidade = COALESCE(%s, cidade),
                    uf = COALESCE(%s, uf),
                    endereco = COALESCE(%s, endereco),
                    ativo = COALESCE(%s, ativo),
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
                RETURNING id, nome, codigo, cidade, uf, endereco, ativo
                """,
                (
                    str(body["nome"]).strip() if body.get("nome") is not None else None,
                    str(body.get("codigo") or "").strip() or None
                    if "codigo" in body
                    else None,
                    str(body.get("cidade") or "").strip() or None
                    if "cidade" in body
                    else None,
                    str(body.get("uf") or "").strip() or None if "uf" in body else None,
                    str(body.get("endereco") or "").strip() or None
                    if "endereco" in body
                    else None,
                    bool(body["ativo"]) if "ativo" in body else None,
                    str(uid),
                ),
            )
            r = cur.fetchone()
            if not r:
                return jsonify({"error": "Unidade não encontrada"}), 404
    return jsonify(
        {
            "item": {
                "id": str(r["id"]),
                "nome": r["nome"],
                "codigo": r.get("codigo"),
                "cidade": r.get("cidade"),
                "uf": r.get("uf"),
                "endereco": r.get("endereco"),
                "ativo": bool(r["ativo"]),
            }
        }
    )


# ---------------------------------------------------------------------------
# Períodos letivos
# ---------------------------------------------------------------------------
@bp.get("/api/instituicoes/<instituicao_id>/periodos-letivos")
def list_periodos(instituicao_id: str):
    inst = _parse_uuid(instituicao_id, "instituição")
    if isinstance(inst, tuple):
        return inst
    unidade = _parse_uuid(request.args.get("unidade_id"), "unidade", required=False)
    if isinstance(unidade, tuple):
        return unidade
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            sql = """
                SELECT p.*, u.nome AS unidade_nome
                FROM public.school_periodos_letivos p
                LEFT JOIN public.school_unidades u ON u.id = p.unidade_id
                WHERE p.instituicao_id = %s
            """
            params: list[Any] = [str(inst)]
            if unidade:
                sql += " AND p.unidade_id = %s"
                params.append(str(unidade))
            sql += " ORDER BY p.ano_letivo DESC, p.data_inicio DESC"
            cur.execute(sql, params)
            items = [
                {
                    "id": str(r["id"]),
                    "unidade_id": str(r["unidade_id"]) if r.get("unidade_id") else None,
                    "unidade_nome": r.get("unidade_nome"),
                    "rotulo": r["rotulo"],
                    "ano_letivo": r["ano_letivo"],
                    "tipo_periodo": r["tipo_periodo"],
                    "etapa": r.get("etapa"),
                    "data_inicio": _iso(r["data_inicio"]),
                    "data_fim": _iso(r["data_fim"]),
                    "status": r["status"],
                    "em_curso": bool(r["em_curso"]),
                    "ativo": bool(r["ativo"]),
                }
                for r in cur.fetchall()
            ]
    return jsonify({"items": items})


@bp.post("/api/instituicoes/<instituicao_id>/periodos-letivos")
def create_periodo(instituicao_id: str):
    inst = _parse_uuid(instituicao_id, "instituição")
    if isinstance(inst, tuple):
        return inst
    body = request.get_json(silent=True) or {}
    rotulo = str(body.get("rotulo") or "").strip()
    tipo = str(body.get("tipo_periodo") or "semestral").strip()
    if not rotulo:
        return jsonify({"error": "Rótulo obrigatório"}), 400
    if tipo not in TIPOS_PERIODO:
        return jsonify({"error": "Tipo de período inválido"}), 400
    try:
        ano = int(body.get("ano_letivo") or date.today().year)
    except (TypeError, ValueError):
        return jsonify({"error": "Ano letivo inválido"}), 400
    di = _parse_date(body.get("data_inicio"), "data_inicio")
    if isinstance(di, tuple):
        return di
    df = _parse_date(body.get("data_fim"), "data_fim")
    if isinstance(df, tuple):
        return df
    unidade = _parse_uuid(body.get("unidade_id"), "unidade", required=False)
    if isinstance(unidade, tuple):
        return unidade
    status = str(body.get("status") or "planejamento").strip()
    if status not in STATUS_PERIODO:
        return jsonify({"error": "Status inválido"}), 400

    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                INSERT INTO public.school_periodos_letivos (
                    instituicao_id, unidade_id, rotulo, ano_letivo, tipo_periodo,
                    etapa, data_inicio, data_fim, status, em_curso
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                RETURNING *
                """,
                (
                    str(inst),
                    str(unidade) if unidade else None,
                    rotulo,
                    ano,
                    tipo,
                    str(body.get("etapa") or "").strip() or None,
                    di,
                    df,
                    status,
                    bool(body.get("em_curso")),
                ),
            )
            r = cur.fetchone()
    return (
        jsonify(
            {
                "item": {
                    "id": str(r["id"]),
                    "unidade_id": str(r["unidade_id"]) if r.get("unidade_id") else None,
                    "unidade_nome": None,
                    "rotulo": r["rotulo"],
                    "ano_letivo": r["ano_letivo"],
                    "tipo_periodo": r["tipo_periodo"],
                    "etapa": r.get("etapa"),
                    "data_inicio": _iso(r["data_inicio"]),
                    "data_fim": _iso(r["data_fim"]),
                    "status": r["status"],
                    "em_curso": bool(r["em_curso"]),
                    "ativo": bool(r["ativo"]),
                }
            }
        ),
        201,
    )


@bp.put("/api/periodos-letivos/<periodo_id>")
def update_periodo(periodo_id: str):
    pid = _parse_uuid(periodo_id, "período")
    if isinstance(pid, tuple):
        return pid
    body = request.get_json(silent=True) or {}
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                UPDATE public.school_periodos_letivos
                SET rotulo = COALESCE(%s, rotulo),
                    ano_letivo = COALESCE(%s, ano_letivo),
                    tipo_periodo = COALESCE(%s, tipo_periodo),
                    etapa = CASE WHEN %s THEN %s ELSE etapa END,
                    data_inicio = COALESCE(%s, data_inicio),
                    data_fim = COALESCE(%s, data_fim),
                    status = COALESCE(%s, status),
                    em_curso = COALESCE(%s, em_curso),
                    ativo = COALESCE(%s, ativo),
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
                RETURNING *
                """,
                (
                    str(body["rotulo"]).strip() if body.get("rotulo") else None,
                    int(body["ano_letivo"]) if body.get("ano_letivo") is not None else None,
                    str(body["tipo_periodo"]).strip()
                    if body.get("tipo_periodo")
                    else None,
                    "etapa" in body,
                    str(body.get("etapa") or "").strip() or None,
                    _parse_date(body.get("data_inicio"), "data_inicio", required=False)
                    if body.get("data_inicio")
                    else None,
                    _parse_date(body.get("data_fim"), "data_fim", required=False)
                    if body.get("data_fim")
                    else None,
                    str(body["status"]).strip() if body.get("status") else None,
                    bool(body["em_curso"]) if "em_curso" in body else None,
                    bool(body["ativo"]) if "ativo" in body else None,
                    str(pid),
                ),
            )
            r = cur.fetchone()
            if not r:
                return jsonify({"error": "Período não encontrado"}), 404
    return jsonify(
        {
            "item": {
                "id": str(r["id"]),
                "unidade_id": str(r["unidade_id"]) if r.get("unidade_id") else None,
                "rotulo": r["rotulo"],
                "ano_letivo": r["ano_letivo"],
                "tipo_periodo": r["tipo_periodo"],
                "etapa": r.get("etapa"),
                "data_inicio": _iso(r["data_inicio"]),
                "data_fim": _iso(r["data_fim"]),
                "status": r["status"],
                "em_curso": bool(r["em_curso"]),
                "ativo": bool(r["ativo"]),
            }
        }
    )


# ---------------------------------------------------------------------------
# Cursos
# ---------------------------------------------------------------------------
@bp.get("/api/periodos-letivos/<periodo_id>/cursos")
def list_cursos(periodo_id: str):
    pid = _parse_uuid(periodo_id, "período")
    if isinstance(pid, tuple):
        return pid
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id, nome, nivel, turma_turno, observacoes, ativo
                FROM public.school_cursos
                WHERE periodo_letivo_id = %s
                ORDER BY nome
                """,
                (str(pid),),
            )
            items = [
                {
                    "id": str(r["id"]),
                    "nome": r["nome"],
                    "nivel": r.get("nivel"),
                    "turma_turno": r.get("turma_turno"),
                    "observacoes": r.get("observacoes"),
                    "ativo": bool(r["ativo"]),
                }
                for r in cur.fetchall()
            ]
    return jsonify({"items": items})


@bp.post("/api/periodos-letivos/<periodo_id>/cursos")
def create_curso(periodo_id: str):
    pid = _parse_uuid(periodo_id, "período")
    if isinstance(pid, tuple):
        return pid
    body = request.get_json(silent=True) or {}
    nome = str(body.get("nome") or "").strip()
    if not nome:
        return jsonify({"error": "Nome do curso obrigatório"}), 400
    nivel = str(body.get("nivel") or "").strip() or None
    if nivel and nivel not in NIVEIS:
        return jsonify({"error": "Nível inválido"}), 400
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                INSERT INTO public.school_cursos
                    (periodo_letivo_id, nome, nivel, turma_turno, observacoes)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id, nome, nivel, turma_turno, observacoes, ativo
                """,
                (
                    str(pid),
                    nome,
                    nivel,
                    str(body.get("turma_turno") or "").strip() or None,
                    str(body.get("observacoes") or "").strip() or None,
                ),
            )
            r = cur.fetchone()
    return (
        jsonify(
            {
                "item": {
                    "id": str(r["id"]),
                    "nome": r["nome"],
                    "nivel": r.get("nivel"),
                    "turma_turno": r.get("turma_turno"),
                    "observacoes": r.get("observacoes"),
                    "ativo": bool(r["ativo"]),
                }
            }
        ),
        201,
    )


@bp.put("/api/cursos/<curso_id>")
def update_curso(curso_id: str):
    cid = _parse_uuid(curso_id, "curso")
    if isinstance(cid, tuple):
        return cid
    body = request.get_json(silent=True) or {}
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                UPDATE public.school_cursos
                SET nome = COALESCE(%s, nome),
                    nivel = CASE WHEN %s THEN %s ELSE nivel END,
                    turma_turno = CASE WHEN %s THEN %s ELSE turma_turno END,
                    observacoes = CASE WHEN %s THEN %s ELSE observacoes END,
                    ativo = COALESCE(%s, ativo),
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
                RETURNING id, nome, nivel, turma_turno, observacoes, ativo
                """,
                (
                    str(body["nome"]).strip() if body.get("nome") else None,
                    "nivel" in body,
                    str(body.get("nivel") or "").strip() or None,
                    "turma_turno" in body,
                    str(body.get("turma_turno") or "").strip() or None,
                    "observacoes" in body,
                    str(body.get("observacoes") or "").strip() or None,
                    bool(body["ativo"]) if "ativo" in body else None,
                    str(cid),
                ),
            )
            r = cur.fetchone()
            if not r:
                return jsonify({"error": "Curso não encontrado"}), 404
    return jsonify(
        {
            "item": {
                "id": str(r["id"]),
                "nome": r["nome"],
                "nivel": r.get("nivel"),
                "turma_turno": r.get("turma_turno"),
                "observacoes": r.get("observacoes"),
                "ativo": bool(r["ativo"]),
            }
        }
    )


# ---------------------------------------------------------------------------
# Disciplinas (+ ementa por curso)
# ---------------------------------------------------------------------------
@bp.get("/api/cursos/<curso_id>/disciplinas")
def list_disciplinas(curso_id: str):
    cid = _parse_uuid(curso_id, "curso")
    if isinstance(cid, tuple):
        return cid
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id, nome, codigo, carga_horaria_horas, ementa, ativo
                FROM public.school_disciplinas
                WHERE curso_id = %s
                ORDER BY nome
                """,
                (str(cid),),
            )
            items = [
                {
                    "id": str(r["id"]),
                    "nome": r["nome"],
                    "codigo": r.get("codigo"),
                    "carga_horaria_horas": float(r["carga_horaria_horas"])
                    if r.get("carga_horaria_horas") is not None
                    else None,
                    "ementa": r.get("ementa"),
                    "ativo": bool(r["ativo"]),
                }
                for r in cur.fetchall()
            ]
    return jsonify({"items": items})


@bp.post("/api/cursos/<curso_id>/disciplinas")
def create_disciplina(curso_id: str):
    cid = _parse_uuid(curso_id, "curso")
    if isinstance(cid, tuple):
        return cid
    body = request.get_json(silent=True) or {}
    nome = str(body.get("nome") or "").strip()
    if not nome:
        return jsonify({"error": "Nome da disciplina obrigatório"}), 400
    carga = body.get("carga_horaria_horas")
    try:
        carga_val = float(carga) if carga is not None and str(carga).strip() != "" else None
    except (TypeError, ValueError):
        return jsonify({"error": "Carga horária inválida"}), 400
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                INSERT INTO public.school_disciplinas
                    (curso_id, nome, codigo, carga_horaria_horas, ementa)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id, nome, codigo, carga_horaria_horas, ementa, ativo
                """,
                (
                    str(cid),
                    nome,
                    str(body.get("codigo") or "").strip() or None,
                    carga_val,
                    str(body.get("ementa") or "").strip() or None,
                ),
            )
            r = cur.fetchone()
    return (
        jsonify(
            {
                "item": {
                    "id": str(r["id"]),
                    "nome": r["nome"],
                    "codigo": r.get("codigo"),
                    "carga_horaria_horas": float(r["carga_horaria_horas"])
                    if r.get("carga_horaria_horas") is not None
                    else None,
                    "ementa": r.get("ementa"),
                    "ativo": bool(r["ativo"]),
                }
            }
        ),
        201,
    )


@bp.put("/api/disciplinas/<disciplina_id>")
def update_disciplina(disciplina_id: str):
    did = _parse_uuid(disciplina_id, "disciplina")
    if isinstance(did, tuple):
        return did
    body = request.get_json(silent=True) or {}
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                UPDATE public.school_disciplinas
                SET nome = COALESCE(%s, nome),
                    codigo = CASE WHEN %s THEN %s ELSE codigo END,
                    ementa = CASE WHEN %s THEN %s ELSE ementa END,
                    ativo = COALESCE(%s, ativo),
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
                RETURNING id, nome, codigo, carga_horaria_horas, ementa, ativo
                """,
                (
                    str(body["nome"]).strip() if body.get("nome") else None,
                    "codigo" in body,
                    str(body.get("codigo") or "").strip() or None,
                    "ementa" in body,
                    str(body.get("ementa") or "").strip() or None,
                    bool(body["ativo"]) if "ativo" in body else None,
                    str(did),
                ),
            )
            r = cur.fetchone()
            if not r:
                return jsonify({"error": "Disciplina não encontrada"}), 404
    return jsonify(
        {
            "item": {
                "id": str(r["id"]),
                "nome": r["nome"],
                "codigo": r.get("codigo"),
                "carga_horaria_horas": float(r["carga_horaria_horas"])
                if r.get("carga_horaria_horas") is not None
                else None,
                "ementa": r.get("ementa"),
                "ativo": bool(r["ativo"]),
            }
        }
    )


# ---------------------------------------------------------------------------
# Calendário letivo (mantido)
# ---------------------------------------------------------------------------
@bp.get("/api/instituicoes/<instituicao_id>/calendario-letivo")
def list_calendario(instituicao_id: str):
    inst = _parse_uuid(instituicao_id, "instituição")
    if isinstance(inst, tuple):
        return inst
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT c.id, c.titulo, c.tipo, c.data_inicio, c.data_fim, c.unidade_id,
                       u.nome AS unidade_nome
                FROM public.school_calendario_letivo c
                LEFT JOIN public.school_unidades u ON u.id = c.unidade_id
                WHERE c.instituicao_id = %s
                ORDER BY c.data_inicio DESC
                """,
                (str(inst),),
            )
            items = [
                {
                    "id": str(r["id"]),
                    "titulo": r["titulo"],
                    "tipo": r["tipo"],
                    "data_inicio": _iso(r["data_inicio"]),
                    "data_fim": _iso(r["data_fim"]),
                    "unidade_id": str(r["unidade_id"]) if r.get("unidade_id") else None,
                    "unidade_nome": r.get("unidade_nome"),
                }
                for r in cur.fetchall()
            ]
    return jsonify({"items": items})


@bp.post("/api/instituicoes/<instituicao_id>/calendario-letivo")
def create_calendario(instituicao_id: str):
    inst = _parse_uuid(instituicao_id, "instituição")
    if isinstance(inst, tuple):
        return inst
    body = request.get_json(silent=True) or {}
    titulo = str(body.get("titulo") or "").strip()
    tipo = str(body.get("tipo") or "").strip()
    if not titulo:
        return jsonify({"error": "Título obrigatório"}), 400
    if tipo not in CAL_TIPOS:
        return jsonify({"error": "Tipo inválido"}), 400
    di = _parse_date(body.get("data_inicio"), "data_inicio")
    if isinstance(di, tuple):
        return di
    df = _parse_date(body.get("data_fim"), "data_fim", required=False)
    if isinstance(df, tuple):
        return df
    unidade = _parse_uuid(body.get("unidade_id"), "unidade", required=False)
    if isinstance(unidade, tuple):
        return unidade
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                INSERT INTO public.school_calendario_letivo
                    (instituicao_id, titulo, tipo, data_inicio, data_fim, unidade_id)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id, titulo, tipo, data_inicio, data_fim, unidade_id
                """,
                (
                    str(inst),
                    titulo,
                    tipo,
                    di,
                    df,
                    str(unidade) if unidade else None,
                ),
            )
            r = cur.fetchone()
    return (
        jsonify(
            {
                "item": {
                    "id": str(r["id"]),
                    "titulo": r["titulo"],
                    "tipo": r["tipo"],
                    "data_inicio": _iso(r["data_inicio"]),
                    "data_fim": _iso(r["data_fim"]),
                    "unidade_id": str(r["unidade_id"]) if r.get("unidade_id") else None,
                    "unidade_nome": None,
                }
            }
        ),
        201,
    )

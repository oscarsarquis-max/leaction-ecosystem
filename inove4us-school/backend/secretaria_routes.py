"""Secretaria Acadêmica — CRUD operacional + alocação docente (TEACHER_ALLOCATED).

Superfície /api/secretaria/* para o painel operacional:
unidades, períodos, cursos, disciplinas, turmas, alunos, calendário,
alocações, comunicações e planejamento escolar.
"""
from __future__ import annotations

import csv
import io
import json
import os
import unicodedata
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

IMPORT_ALUNOS_MAX_LINHAS = 2000
IMPORT_NOME_ALIASES = frozenset({"nome", "name"})
IMPORT_MATRICULA_ALIASES = frozenset({"matricula", "ra"})
IMPORT_NASC_ALIASES = frozenset(
    {"data_nascimento", "nascimento", "data de nascimento", "dt_nasc"}
)


# Zona operacional — Secretaria Acadêmica (inclui planejamento escolar).
require_gestor = require_zona("operacional")


def _strip_accents(value: str) -> str:
    norm = unicodedata.normalize("NFKD", value or "")
    return "".join(ch for ch in norm if not unicodedata.combining(ch))


def _norm_header(value: str) -> str:
    raw = _strip_accents(str(value or "")).strip().lower()
    return " ".join(raw.split())


def _decode_csv_bytes(raw: bytes) -> str:
    for enc in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("latin-1", errors="replace")


def _detect_csv_delimiter(sample: str) -> str:
    first = ""
    for line in sample.splitlines():
        if line.strip():
            first = line
            break
    if first.count(";") > first.count(","):
        return ";"
    return ","


def _parse_import_date(value: Any) -> tuple[date | None, str | None]:
    """Retorna (date|None, erro|None). Vazio → (None, None)."""
    raw = _text(value)
    if not raw:
        return None, None
    if len(raw) >= 10 and raw[4] == "-" and raw[7] == "-":
        try:
            return date.fromisoformat(raw[:10]), None
        except ValueError:
            return None, "data_nascimento inválida"
    if len(raw) >= 10 and raw[2] == "/" and raw[5] == "/":
        try:
            d, m, y = raw[:10].split("/")
            return date(int(y), int(m), int(d)), None
        except (ValueError, TypeError):
            return None, "data_nascimento inválida"
    return None, "data_nascimento inválida"


def _parse_alunos_csv(text: str) -> tuple[list[dict[str, Any]] | None, str | None]:
    """Parse CSV → lista de dicts brutos {linha, nome, matricula, data_nascimento_raw}."""
    if not (text or "").strip():
        return None, "Arquivo CSV vazio"
    delim = _detect_csv_delimiter(text)
    reader = csv.reader(io.StringIO(text), delimiter=delim)
    try:
        header_row = next(reader)
    except StopIteration:
        return None, "Arquivo CSV vazio"

    headers = [_norm_header(h) for h in header_row]
    col_nome = next((i for i, h in enumerate(headers) if h in IMPORT_NOME_ALIASES), None)
    col_mat = next(
        (i for i, h in enumerate(headers) if h in IMPORT_MATRICULA_ALIASES), None
    )
    col_nasc = next((i for i, h in enumerate(headers) if h in IMPORT_NASC_ALIASES), None)
    if col_nome is None or col_mat is None:
        return None, "Cabeçalho inválido: é obrigatório ter colunas nome e matricula"

    rows: list[dict[str, Any]] = []
    for idx, cells in enumerate(reader, start=2):
        if not cells or all(not str(c or "").strip() for c in cells):
            continue
        def _cell(i: int | None) -> str:
            if i is None or i >= len(cells):
                return ""
            return str(cells[i] or "").strip()

        rows.append(
            {
                "linha": idx,
                "nome": _cell(col_nome),
                "matricula": _cell(col_mat),
                "data_nascimento_raw": _cell(col_nasc) if col_nasc is not None else "",
            }
        )
        if len(rows) > IMPORT_ALUNOS_MAX_LINHAS:
            return None, f"Limite de {IMPORT_ALUNOS_MAX_LINHAS} linhas úteis excedido"

    return rows, None


def _validate_alunos_import_rows(
    raw_rows: list[dict[str, Any]],
    existing_by_mat: dict[str, dict[str, Any]],
    turma_destino_id: str,
    turma_destino_nome: str | None = None,
) -> list[dict[str, Any]]:
    """Valida linhas; existing_by_mat: matricula_lower → {id, turma_id, turma_nome}."""
    dest_id = str(turma_destino_id)
    dest_nome = turma_destino_nome
    seen_mats: dict[str, int] = {}
    out: list[dict[str, Any]] = []
    for raw in raw_rows:
        linha = int(raw.get("linha") or 0)
        nome = _text(raw.get("nome"))
        matricula = _text(raw.get("matricula"))
        nasc_raw = raw.get("data_nascimento_raw")
        if nasc_raw is None and "data_nascimento" in raw:
            nasc_raw = raw.get("data_nascimento")
        nasc_date, nasc_err = _parse_import_date(nasc_raw)

        item: dict[str, Any] = {
            "linha": linha,
            "nome": nome or None,
            "matricula": matricula or None,
            "data_nascimento": nasc_date.isoformat() if nasc_date else None,
            "status": "ok",
            "acao": None,
            "erro": None,
            "aluno_id_existente": None,
            "turma_atual_id": None,
            "turma_atual_nome": None,
            "turma_nova_id": dest_id,
            "turma_nova_nome": dest_nome,
        }

        if not nome:
            item["status"] = "erro"
            item["erro"] = "nome vazio"
            out.append(item)
            continue
        if not matricula:
            item["status"] = "erro"
            item["erro"] = "matrícula vazia"
            out.append(item)
            continue
        if nasc_err:
            item["status"] = "erro"
            item["erro"] = nasc_err
            out.append(item)
            continue

        mat_key = matricula.casefold()
        if mat_key in seen_mats:
            item["status"] = "erro"
            item["erro"] = "matrícula duplicada no arquivo"
            out.append(item)
            continue
        seen_mats[mat_key] = linha

        existing = existing_by_mat.get(mat_key)
        if existing:
            item["aluno_id_existente"] = existing["id"]
            atual_id = existing.get("turma_id")
            item["turma_atual_id"] = atual_id
            item["turma_atual_nome"] = existing.get("turma_nome")
            if atual_id and str(atual_id) != dest_id:
                item["acao"] = "mudar_turma"
            else:
                item["acao"] = "atualizar"
        else:
            item["acao"] = "criar"
        out.append(item)
    return out


def _import_resumo(linhas: list[dict[str, Any]]) -> dict[str, int]:
    ok = sum(1 for L in linhas if L.get("status") == "ok")
    erro = sum(1 for L in linhas if L.get("status") == "erro")
    novos = sum(1 for L in linhas if L.get("acao") == "criar")
    atualizacoes = sum(1 for L in linhas if L.get("acao") == "atualizar")
    mudancas_turma = sum(1 for L in linhas if L.get("acao") == "mudar_turma")
    return {
        "total": len(linhas),
        "ok": ok,
        "erro": erro,
        "novos": novos,
        "atualizacoes": atualizacoes,
        "mudancas_turma": mudancas_turma,
    }


def _load_turma_contexto(cur: Any, inst: str, turma_id: uuid.UUID):
    cur.execute(
        """
        SELECT id, nome, unidade_id FROM public.school_turmas
        WHERE id = %s AND instituicao_id = %s
        """,
        (str(turma_id), inst),
    )
    return cur.fetchone()


def _import_flag(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    return str(value or "").strip().lower() in {"1", "true", "sim", "yes", "on"}


def _assert_turma_import_escopo(turma: dict[str, Any]):
    """Escopo de unidade via resolve_unidade_id (Etapa 14 / _unidade_no_escopo), sem middleware duplicado."""
    uid = turma.get("unidade_id")
    if not uid:
        escopo = _unidade_escopo()
        if isinstance(escopo, tuple):
            return escopo
        if escopo:
            return (
                jsonify(
                    {
                        "error": "Turma sem unidade definida — fora do escopo do gestor.",
                        "code": "FORBIDDEN_UNIDADE",
                    }
                ),
                403,
            )
        return None
    denied = _unidade_no_escopo(uuid.UUID(str(uid)))
    if not denied:
        return None
    _resp, status = denied
    if status == 403:
        return (
            jsonify(
                {
                    "error": (
                        "Esta turma pertence a outra unidade. "
                        "Só é possível importar alunos para turmas da unidade do gestor."
                    ),
                    "code": "FORBIDDEN_UNIDADE",
                }
            ),
            403,
        )
    return denied


def _load_matriculas_existentes(cur: Any, inst: str) -> dict[str, dict[str, Any]]:
    cur.execute(
        """
        SELECT a.id, a.matricula, a.turma_id, t.nome AS turma_nome
          FROM public.school_alunos a
          LEFT JOIN public.school_turmas t ON t.id = a.turma_id
         WHERE a.instituicao_id = %s
        """,
        (inst,),
    )
    out: dict[str, dict[str, Any]] = {}
    for r in cur.fetchall():
        key = _text(r["matricula"]).casefold()
        if not key:
            continue
        out[key] = {
            "id": str(r["id"]),
            "turma_id": str(r["turma_id"]) if r.get("turma_id") else None,
            "turma_nome": r.get("turma_nome"),
        }
    return out


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


EQUIPE_PAPEIS = frozenset({"gestor_principal", "gestor_academico", "coordenador"})


def _unidade_no_escopo(uid: uuid.UUID):
    """Valida escopo de unidade do gestor. Retorna None ou (response, status)."""
    escopo = _unidade_escopo()
    if isinstance(escopo, tuple):
        return escopo
    if escopo and str(uid) != str(escopo):
        return jsonify({"error": "Unidade fora do escopo"}), 403
    return None


def _equipe_unique_error(exc: Exception) -> str:
    cname = str(getattr(getattr(exc, "diag", None), "constraint_name", "") or "")
    if "um_principal" in cname:
        return "Já existe um gestor principal ativo nesta unidade"
    if "um_academico" in cname:
        return "Já existe um gestor acadêmico ativo nesta unidade"
    if "gestor_papel" in cname:
        return "Este gestor já está na equipe com este papel"
    return "Conflito de unicidade na equipe gestora"


def _serialize_unidade_lista(row: dict[str, Any]) -> dict[str, Any]:
    """Shape estável do GET lista / create / update (compatibilidade)."""
    return {
        "id": str(row["id"]),
        "nome": row["nome"],
        "endereco": row.get("endereco") or "",
        "codigo": row.get("codigo"),
        "cidade": row.get("cidade"),
        "uf": row.get("uf"),
        "ativo": bool(row["ativo"]),
    }


@bp.get("/api/secretaria/unidades/<item_id>")
@require_gestor
def get_unidade(item_id: str):
    """Ficha da unidade: institucional + equipe + cursos + resumo (1 CTE, sem N+1)."""
    inst = _instituicao_id()
    uid = _parse_uuid(item_id, "unidade")
    if not uid:
        return jsonify({"error": "Identificador inválido"}), 400
    denied = _unidade_no_escopo(uid)
    if denied:
        return denied

    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                WITH unidade AS (
                    SELECT
                        u.id,
                        u.nome,
                        u.codigo,
                        u.ativo,
                        u.cidade,
                        u.uf,
                        u.endereco,
                        u.logradouro,
                        u.numero,
                        u.bairro,
                        u.cep,
                        u.telefone,
                        u.email_institucional
                    FROM public.school_unidades u
                    WHERE u.id = %s AND u.instituicao_id = %s
                ),
                cursos_u AS (
                    SELECT
                        c.id,
                        c.nome,
                        c.periodo_letivo_id AS periodo_id,
                        p.rotulo AS periodo_rotulo
                    FROM public.school_cursos c
                    JOIN public.school_periodos_letivos p
                      ON p.id = c.periodo_letivo_id
                    JOIN unidade u ON p.unidade_id = u.id
                    WHERE c.ativo = TRUE
                ),
                curso_stats AS (
                    SELECT
                        cu.id,
                        cu.nome,
                        cu.periodo_id,
                        cu.periodo_rotulo,
                        (
                            SELECT count(*)::int
                            FROM public.school_turmas t
                            WHERE t.curso_id = cu.id
                              AND t.unidade_id = (SELECT id FROM unidade)
                              AND t.ativa = TRUE
                        ) AS n_turmas,
                        (
                            SELECT count(*)::int
                            FROM public.school_curso_disciplinas cd
                            JOIN public.school_disciplinas d ON d.id = cd.disciplina_id
                            WHERE cd.curso_id = cu.id
                              AND d.ativo = TRUE
                        ) AS n_disciplinas
                    FROM cursos_u cu
                ),
                disc_ids AS (
                    SELECT cd.disciplina_id AS id
                    FROM public.school_curso_disciplinas cd
                    WHERE cd.curso_id IN (SELECT id FROM cursos_u)
                    UNION
                    SELECT a.disciplina_id AS id
                    FROM public.school_alocacoes_docentes a
                    JOIN unidade u ON a.unidade_id = u.id
                    WHERE a.ativo = TRUE
                ),
                resumo AS (
                    SELECT
                        (SELECT count(*)::int FROM cursos_u) AS cursos,
                        (
                            SELECT count(*)::int
                            FROM public.school_turmas t
                            JOIN unidade u ON t.unidade_id = u.id
                            WHERE t.ativa = TRUE
                        ) AS turmas,
                        (SELECT count(*)::int FROM disc_ids) AS disciplinas,
                        (
                            SELECT count(*)::int
                            FROM public.school_alunos a
                            JOIN public.school_turmas t ON t.id = a.turma_id
                            JOIN unidade u ON t.unidade_id = u.id
                            WHERE a.ativo = TRUE
                        ) AS alunos,
                        (
                            SELECT count(DISTINCT a.professor_vinculo_id)::int
                            FROM public.school_alocacoes_docentes a
                            JOIN unidade u ON a.unidade_id = u.id
                            WHERE a.ativo = TRUE
                        ) AS professores_alocados
                ),
                equipe AS (
                    SELECT
                        e.id,
                        e.papel,
                        e.gestor_id,
                        COALESCE(g.nome, e.nome) AS nome,
                        COALESCE(g.email::text, e.email) AS email,
                        e.telefone,
                        e.area_coordenacao,
                        (e.gestor_id IS NOT NULL) AS tem_login,
                        CASE e.papel
                            WHEN 'gestor_principal' THEN 1
                            WHEN 'gestor_academico' THEN 2
                            ELSE 3
                        END AS papel_ord
                    FROM public.school_unidade_equipe e
                    LEFT JOIN public.school_gestores g ON g.id = e.gestor_id
                    JOIN unidade u ON e.unidade_id = u.id
                    WHERE e.ativo = TRUE
                )
                SELECT
                    (SELECT row_to_json(u) FROM unidade u) AS unidade,
                    (
                        SELECT COALESCE(
                            json_agg(
                                json_build_object(
                                    'id', cs.id,
                                    'nome', cs.nome,
                                    'periodo_id', cs.periodo_id,
                                    'periodo_rotulo', cs.periodo_rotulo,
                                    'n_turmas', cs.n_turmas,
                                    'n_disciplinas', cs.n_disciplinas
                                )
                                ORDER BY cs.nome
                            ),
                            '[]'::json
                        )
                        FROM curso_stats cs
                    ) AS cursos,
                    (SELECT row_to_json(r) FROM resumo r) AS resumo,
                    (
                        SELECT COALESCE(
                            json_agg(
                                json_build_object(
                                    'id', eq.id,
                                    'papel', eq.papel,
                                    'gestor_id', eq.gestor_id,
                                    'nome', eq.nome,
                                    'email', eq.email,
                                    'telefone', eq.telefone,
                                    'area_coordenacao', eq.area_coordenacao,
                                    'tem_login', eq.tem_login
                                )
                                ORDER BY eq.papel_ord, eq.nome
                            ),
                            '[]'::json
                        )
                        FROM equipe eq
                    ) AS equipe_gestora
                """,
                (str(uid), inst),
            )
            row = cur.fetchone()

    if not row or not row.get("unidade"):
        return jsonify({"error": "Unidade não encontrada"}), 404

    u = row["unidade"]
    equipe = row.get("equipe_gestora") or []
    cursos = row.get("cursos") or []
    resumo = row.get("resumo") or {}

    def _as_list(val: Any) -> list:
        if val is None:
            return []
        if isinstance(val, list):
            return val
        if isinstance(val, str):
            return json.loads(val)
        return list(val)

    equipe_list = _as_list(equipe)
    cursos_list = _as_list(cursos)
    if not isinstance(resumo, dict):
        resumo = json.loads(resumo) if isinstance(resumo, str) else dict(resumo or {})

    return jsonify(
        {
            "item": {
                "id": str(u["id"]),
                "nome": u.get("nome"),
                "codigo": u.get("codigo"),
                "ativo": bool(u.get("ativo")),
                "cidade": u.get("cidade"),
                "uf": u.get("uf"),
                "endereco": u.get("endereco") or "",
                "logradouro": u.get("logradouro"),
                "numero": u.get("numero"),
                "bairro": u.get("bairro"),
                "cep": u.get("cep"),
                "telefone": u.get("telefone"),
                "email_institucional": u.get("email_institucional"),
                "equipe_gestora": [
                    {
                        "id": str(e["id"]),
                        "papel": e.get("papel"),
                        "gestor_id": str(e["gestor_id"]) if e.get("gestor_id") else None,
                        "nome": e.get("nome"),
                        "email": e.get("email"),
                        "telefone": e.get("telefone"),
                        "area_coordenacao": e.get("area_coordenacao"),
                        "tem_login": bool(e.get("tem_login")),
                    }
                    for e in equipe_list
                ],
                "cursos": [
                    {
                        "id": str(c["id"]),
                        "nome": c.get("nome"),
                        "periodo_id": str(c["periodo_id"]) if c.get("periodo_id") else None,
                        "periodo_rotulo": c.get("periodo_rotulo"),
                        "n_turmas": int(c.get("n_turmas") or 0),
                        "n_disciplinas": int(c.get("n_disciplinas") or 0),
                    }
                    for c in cursos_list
                ],
                "resumo": {
                    "cursos": int(resumo.get("cursos") or 0),
                    "turmas": int(resumo.get("turmas") or 0),
                    "disciplinas": int(resumo.get("disciplinas") or 0),
                    "alunos": int(resumo.get("alunos") or 0),
                    "professores_alocados": int(resumo.get("professores_alocados") or 0),
                },
            }
        }
    )


@bp.put("/api/secretaria/unidades/<item_id>")
@bp.patch("/api/secretaria/unidades/<item_id>")
@require_gestor
def update_unidade(item_id: str):
    inst = _instituicao_id()
    uid = _parse_uuid(item_id, "unidade")
    if not uid:
        return jsonify({"error": "Identificador inválido"}), 400
    denied = _unidade_no_escopo(uid)
    if denied:
        return denied
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
                        logradouro = CASE WHEN %s THEN %s ELSE logradouro END,
                        numero = CASE WHEN %s THEN %s ELSE numero END,
                        bairro = CASE WHEN %s THEN %s ELSE bairro END,
                        cep = CASE WHEN %s THEN %s ELSE cep END,
                        telefone = CASE WHEN %s THEN %s ELSE telefone END,
                        email_institucional = CASE WHEN %s THEN %s ELSE email_institucional END,
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
                        "logradouro" in body,
                        _text(body.get("logradouro")) or None,
                        "numero" in body,
                        _text(body.get("numero")) or None,
                        "bairro" in body,
                        _text(body.get("bairro")) or None,
                        "cep" in body,
                        _text(body.get("cep")) or None,
                        "telefone" in body,
                        _text(body.get("telefone")) or None,
                        "email_institucional" in body,
                        _text(body.get("email_institucional")) or None,
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
    return jsonify({"item": _serialize_unidade_lista(row)})


@bp.get("/api/secretaria/gestores")
@require_gestor
def list_gestores_secretaria():
    """Picker leve para vincular gestor com login à equipe da unidade."""
    inst = _instituicao_id()
    q = _text(request.args.get("q"))
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            sql = """
                SELECT id, nome, email, cargo
                FROM public.school_gestores
                WHERE instituicao_id = %s AND ativo = TRUE
            """
            params: list[Any] = [inst]
            if q:
                sql += " AND (nome ILIKE %s OR email ILIKE %s)"
                like = f"%{q}%"
                params.extend([like, like])
            sql += " ORDER BY nome ASC LIMIT 100"
            cur.execute(sql, params)
            rows = cur.fetchall()
    return jsonify(
        {
            "items": [
                {
                    "id": str(r["id"]),
                    "nome": r["nome"],
                    "email": r["email"],
                    "cargo": r.get("cargo"),
                }
                for r in rows
            ]
        }
    )


@bp.post("/api/secretaria/unidades/<item_id>/equipe")
@require_gestor
def create_unidade_equipe(item_id: str):
    inst = _instituicao_id()
    uid = _parse_uuid(item_id, "unidade")
    if not uid:
        return jsonify({"error": "Identificador inválido"}), 400
    denied = _unidade_no_escopo(uid)
    if denied:
        return denied
    body = request.get_json(silent=True) or {}
    papel = _text(body.get("papel"))
    if papel not in EQUIPE_PAPEIS:
        return jsonify(
            {
                "error": "papel inválido (gestor_principal|gestor_academico|coordenador)",
            }
        ), 400

    gestor_id = None
    if body.get("gestor_id") not in (None, ""):
        gestor_id = _parse_uuid(body.get("gestor_id"), "gestor")
        if not gestor_id:
            return jsonify({"error": "gestor_id inválido"}), 400

    nome = _text(body.get("nome")) or None
    email = _text(body.get("email")) or None
    telefone = _text(body.get("telefone")) or None
    area = _text(body.get("area_coordenacao")) or None
    if papel != "coordenador":
        area = None

    if not gestor_id and not nome:
        return jsonify({"error": "Informe gestor_id ou nome do contato"}), 400

    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id FROM public.school_unidades
                WHERE id = %s AND instituicao_id = %s
                """,
                (str(uid), inst),
            )
            if not cur.fetchone():
                return jsonify({"error": "Unidade não encontrada"}), 404

            if gestor_id:
                cur.execute(
                    """
                    SELECT id, nome, email FROM public.school_gestores
                    WHERE id = %s AND instituicao_id = %s AND ativo = TRUE
                    """,
                    (str(gestor_id), inst),
                )
                g = cur.fetchone()
                if not g:
                    return jsonify({"error": "Gestor não encontrado nesta instituição"}), 404
                if not nome:
                    nome = g["nome"]
                if not email:
                    email = g["email"]

            try:
                cur.execute(
                    """
                    INSERT INTO public.school_unidade_equipe (
                        unidade_id, papel, gestor_id, nome, email, telefone, area_coordenacao
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING id, papel, gestor_id, nome, email, telefone, area_coordenacao, ativo
                    """,
                    (
                        str(uid),
                        papel,
                        str(gestor_id) if gestor_id else None,
                        nome,
                        email,
                        telefone,
                        area,
                    ),
                )
                row = cur.fetchone()
            except pg_errors.UniqueViolation as exc:
                conn.rollback()
                return jsonify({"error": _equipe_unique_error(exc)}), 409
            except pg_errors.CheckViolation:
                conn.rollback()
                return jsonify({"error": "Dados da equipe inválidos"}), 400

    return (
        jsonify(
            {
                "item": {
                    "id": str(row["id"]),
                    "papel": row["papel"],
                    "gestor_id": str(row["gestor_id"]) if row.get("gestor_id") else None,
                    "nome": row.get("nome"),
                    "email": row.get("email"),
                    "telefone": row.get("telefone"),
                    "area_coordenacao": row.get("area_coordenacao"),
                    "tem_login": bool(row.get("gestor_id")),
                    "ativo": bool(row["ativo"]),
                }
            }
        ),
        201,
    )


@bp.put("/api/secretaria/unidades/<item_id>/equipe/<equipe_id>")
@bp.patch("/api/secretaria/unidades/<item_id>/equipe/<equipe_id>")
@require_gestor
def update_unidade_equipe(item_id: str, equipe_id: str):
    inst = _instituicao_id()
    uid = _parse_uuid(item_id, "unidade")
    eid = _parse_uuid(equipe_id, "equipe")
    if not uid or not eid:
        return jsonify({"error": "Identificador inválido"}), 400
    denied = _unidade_no_escopo(uid)
    if denied:
        return denied
    body = request.get_json(silent=True) or {}

    papel = None
    if "papel" in body:
        papel = _text(body.get("papel"))
        if papel not in EQUIPE_PAPEIS:
            return jsonify({"error": "papel inválido"}), 400

    gestor_id_set = "gestor_id" in body
    gestor_id = None
    if gestor_id_set:
        if body.get("gestor_id") in (None, ""):
            gestor_id = None
        else:
            gestor_id = _parse_uuid(body.get("gestor_id"), "gestor")
            if not gestor_id:
                return jsonify({"error": "gestor_id inválido"}), 400

    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT e.id
                FROM public.school_unidade_equipe e
                JOIN public.school_unidades u ON u.id = e.unidade_id
                WHERE e.id = %s AND e.unidade_id = %s AND u.instituicao_id = %s
                """,
                (str(eid), str(uid), inst),
            )
            if not cur.fetchone():
                return jsonify({"error": "Membro da equipe não encontrado"}), 404

            if gestor_id:
                cur.execute(
                    """
                    SELECT id FROM public.school_gestores
                    WHERE id = %s AND instituicao_id = %s AND ativo = TRUE
                    """,
                    (str(gestor_id), inst),
                )
                if not cur.fetchone():
                    return jsonify({"error": "Gestor não encontrado nesta instituição"}), 404

            try:
                cur.execute(
                    """
                    UPDATE public.school_unidade_equipe
                    SET papel = COALESCE(%s, papel),
                        gestor_id = CASE WHEN %s THEN %s ELSE gestor_id END,
                        nome = CASE WHEN %s THEN %s ELSE nome END,
                        email = CASE WHEN %s THEN %s ELSE email END,
                        telefone = CASE WHEN %s THEN %s ELSE telefone END,
                        area_coordenacao = CASE WHEN %s THEN %s ELSE area_coordenacao END,
                        ativo = COALESCE(%s, ativo),
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s AND unidade_id = %s
                    RETURNING id, papel, gestor_id, nome, email, telefone, area_coordenacao, ativo
                    """,
                    (
                        papel,
                        gestor_id_set,
                        str(gestor_id) if gestor_id else None,
                        "nome" in body,
                        _text(body.get("nome")) or None if "nome" in body else None,
                        "email" in body,
                        _text(body.get("email")) or None if "email" in body else None,
                        "telefone" in body,
                        _text(body.get("telefone")) or None if "telefone" in body else None,
                        "area_coordenacao" in body,
                        _text(body.get("area_coordenacao")) or None
                        if "area_coordenacao" in body
                        else None,
                        bool(body["ativo"]) if "ativo" in body else None,
                        str(eid),
                        str(uid),
                    ),
                )
                row = cur.fetchone()
            except pg_errors.UniqueViolation as exc:
                conn.rollback()
                return jsonify({"error": _equipe_unique_error(exc)}), 409
            except pg_errors.CheckViolation:
                conn.rollback()
                return jsonify({"error": "Dados da equipe inválidos"}), 400

    if not row:
        return jsonify({"error": "Membro da equipe não encontrado"}), 404
    return jsonify(
        {
            "item": {
                "id": str(row["id"]),
                "papel": row["papel"],
                "gestor_id": str(row["gestor_id"]) if row.get("gestor_id") else None,
                "nome": row.get("nome"),
                "email": row.get("email"),
                "telefone": row.get("telefone"),
                "area_coordenacao": row.get("area_coordenacao"),
                "tem_login": bool(row.get("gestor_id")),
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
                         SELECT COUNT(*)::int FROM public.school_curso_disciplinas cd
                         JOIN public.school_disciplinas d ON d.id = cd.disciplina_id
                         WHERE cd.curso_id = c.id AND d.ativo = TRUE
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
# Disciplinas (catálogo institucional) + vínculo N:N com cursos
# ---------------------------------------------------------------------------
def _serialize_disciplina(r: dict) -> dict[str, Any]:
    cursos = r.get("cursos") or []
    if isinstance(cursos, str):
        try:
            cursos = json.loads(cursos)
        except Exception:
            cursos = []
    if not isinstance(cursos, list):
        cursos = []
    clean = []
    for c in cursos:
        if not isinstance(c, dict) or not c.get("id"):
            continue
        clean.append({"id": str(c["id"]), "nome": c.get("nome") or ""})
    return {
        "id": str(r["id"]),
        "nome": r["nome"],
        "ementa_macro": r.get("ementa") or "",
        "carga_horaria": float(r["carga_horaria_horas"])
        if r.get("carga_horaria_horas") is not None
        else None,
        "codigo": r.get("codigo"),
        "cursos": clean,
        "curso_ids": [c["id"] for c in clean],
        "ativo": bool(r["ativo"]),
    }


def _sql_disciplinas_cursos_agg() -> str:
    return """
        COALESCE((
            SELECT json_agg(
                json_build_object('id', c.id::text, 'nome', c.nome)
                ORDER BY c.nome
            )
            FROM public.school_curso_disciplinas cd
            JOIN public.school_cursos c ON c.id = cd.curso_id
            WHERE cd.disciplina_id = d.id
        ), '[]'::json) AS cursos
    """


def _assert_curso_instituicao(cur, inst: str, curso_id: str):
    cur.execute(
        """
        SELECT c.id
        FROM public.school_cursos c
        JOIN public.school_periodos_letivos p ON p.id = c.periodo_letivo_id
        WHERE c.id = %s AND p.instituicao_id = %s
        """,
        (curso_id, inst),
    )
    return cur.fetchone()


def _associate_curso_disciplina(cur, inst: str, curso_id: str, disciplina_id: str):
    if not _assert_curso_instituicao(cur, inst, curso_id):
        return jsonify({"error": "curso inválido"}), 400
    cur.execute(
        """
        SELECT 1 FROM public.school_disciplinas
        WHERE id = %s AND instituicao_id = %s
        """,
        (disciplina_id, inst),
    )
    if not cur.fetchone():
        return jsonify({"error": "disciplina inválida"}), 400
    try:
        cur.execute(
            """
            INSERT INTO public.school_curso_disciplinas (curso_id, disciplina_id)
            VALUES (%s, %s)
            ON CONFLICT (curso_id, disciplina_id) DO NOTHING
            """,
            (curso_id, disciplina_id),
        )
    except Exception:
        return jsonify({"error": "Não foi possível associar a disciplina ao curso"}), 400
    return None


def _disciplina_no_catalogo_turma(cur, inst: str, turma_id: str, disciplina_id: str) -> bool:
    cur.execute(
        """
        SELECT 1
        FROM public.school_turmas t
        JOIN public.school_curso_disciplinas cd ON cd.curso_id = t.curso_id
        WHERE t.id = %s
          AND t.instituicao_id = %s
          AND cd.disciplina_id = %s
        """,
        (turma_id, inst, disciplina_id),
    )
    return cur.fetchone() is not None


def _reject_disc_fora_catalogo():
    return (
        jsonify(
            {
                "error": "Esta disciplina não está no catálogo do curso desta turma.",
                "code": "DISCIPLINA_FORA_CATALOGO",
            }
        ),
        422,
    )


@bp.get("/api/secretaria/disciplinas")
@require_gestor
def list_disciplinas():
    inst = _instituicao_id()
    curso_id = _parse_uuid(request.args.get("curso_id"), "curso")
    periodo_id = _parse_uuid(
        request.args.get("periodo_letivo_id") or request.args.get("periodo_id"),
        "periodo",
    )
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            sql = f"""
                SELECT d.id, d.nome, d.ementa, d.carga_horaria_horas, d.codigo,
                       d.ativo, {_sql_disciplinas_cursos_agg()}
                FROM public.school_disciplinas d
                WHERE d.instituicao_id = %s
            """
            params: list[Any] = [inst]
            if curso_id:
                sql += """
                    AND EXISTS (
                        SELECT 1 FROM public.school_curso_disciplinas cd
                        WHERE cd.disciplina_id = d.id AND cd.curso_id = %s
                    )
                """
                params.append(str(curso_id))
            if periodo_id and not curso_id:
                sql += """
                    AND EXISTS (
                        SELECT 1
                        FROM public.school_curso_disciplinas cd
                        JOIN public.school_cursos c ON c.id = cd.curso_id
                        WHERE cd.disciplina_id = d.id
                          AND c.periodo_letivo_id = %s
                    )
                """
                params.append(str(periodo_id))
            sql += " ORDER BY d.nome ASC"
            cur.execute(sql, params)
            rows = cur.fetchall()
    return jsonify({"items": [_serialize_disciplina(r) for r in rows]})


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
            cur.execute(
                """
                INSERT INTO public.school_disciplinas (
                    instituicao_id, nome, ementa, carga_horaria_horas
                )
                VALUES (%s, %s, %s, %s)
                RETURNING id, nome, ementa, carga_horaria_horas, ativo
                """,
                (inst, nome, ementa, carga),
            )
            row = cur.fetchone()
            if curso_id:
                err = _associate_curso_disciplina(cur, inst, str(curso_id), str(row["id"]))
                if err:
                    return err
            cur.execute(
                f"""
                SELECT d.id, d.nome, d.ementa, d.carga_horaria_horas, d.codigo,
                       d.ativo, {_sql_disciplinas_cursos_agg()}
                FROM public.school_disciplinas d
                WHERE d.id = %s
                """,
                (str(row["id"]),),
            )
            row = cur.fetchone()
    return jsonify({"item": _serialize_disciplina(row)}), 201


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

    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                UPDATE public.school_disciplinas d
                SET nome = COALESCE(%s, d.nome),
                    ementa = CASE WHEN %s THEN %s ELSE d.ementa END,
                    carga_horaria_horas = CASE WHEN %s THEN %s ELSE d.carga_horaria_horas END,
                    ativo = COALESCE(%s, d.ativo),
                    updated_at = CURRENT_TIMESTAMP
                WHERE d.id = %s AND d.instituicao_id = %s
                RETURNING d.id
                """,
                (
                    _text(body["nome"]) if body.get("nome") is not None else None,
                    "ementa_macro" in body or "ementa" in body,
                    _text(body.get("ementa_macro") or body.get("ementa")) or None,
                    update_carga,
                    carga,
                    bool(body["ativo"]) if "ativo" in body else None,
                    str(did),
                    inst,
                ),
            )
            row = cur.fetchone()
            if not row:
                return jsonify({"error": "Disciplina não encontrada"}), 404
            if body.get("curso_id") not in (None, ""):
                cid = _parse_uuid(body.get("curso_id"), "curso")
                if not cid:
                    return jsonify({"error": "curso_id inválido"}), 400
                err = _associate_curso_disciplina(cur, inst, str(cid), str(did))
                if err:
                    return err
            cur.execute(
                f"""
                SELECT d.id, d.nome, d.ementa, d.carga_horaria_horas, d.codigo,
                       d.ativo, {_sql_disciplinas_cursos_agg()}
                FROM public.school_disciplinas d
                WHERE d.id = %s
                """,
                (str(did),),
            )
            row = cur.fetchone()
    return jsonify({"item": _serialize_disciplina(row)})


@bp.post("/api/secretaria/cursos/<curso_id>/disciplinas")
@require_gestor
def associate_disciplina_curso(curso_id: str):
    """Associa disciplina existente (ou cria nova) ao catálogo do curso."""
    inst = _instituicao_id()
    cid = _parse_uuid(curso_id, "curso")
    if not cid:
        return jsonify({"error": "curso inválido"}), 400
    body = request.get_json(silent=True) or {}
    disc_id = None
    if body.get("disciplina_id") not in (None, ""):
        disc_id = _parse_uuid(body.get("disciplina_id"), "disciplina")
        if not disc_id:
            return jsonify({"error": "disciplina_id inválido"}), 400

    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            if not _assert_curso_instituicao(cur, inst, str(cid)):
                return jsonify({"error": "curso inválido"}), 400
            if not disc_id:
                nome = _text(body.get("nome"))
                if not nome:
                    return jsonify({"error": "Informe disciplina_id ou o nome da nova disciplina"}), 400
                ementa = _text(body.get("ementa_macro") or body.get("ementa")) or None
                carga = None
                carga_raw = body.get("carga_horaria", body.get("carga_horaria_horas"))
                if carga_raw is not None and str(carga_raw).strip() != "":
                    try:
                        carga = float(carga_raw)
                    except (TypeError, ValueError):
                        return jsonify({"error": "carga_horaria inválida"}), 400
                cur.execute(
                    """
                    INSERT INTO public.school_disciplinas (
                        instituicao_id, nome, ementa, carga_horaria_horas
                    )
                    VALUES (%s, %s, %s, %s)
                    RETURNING id
                    """,
                    (inst, nome, ementa, carga),
                )
                disc_id = cur.fetchone()["id"]
            err = _associate_curso_disciplina(cur, inst, str(cid), str(disc_id))
            if err:
                return err
            cur.execute(
                f"""
                SELECT d.id, d.nome, d.ementa, d.carga_horaria_horas, d.codigo,
                       d.ativo, {_sql_disciplinas_cursos_agg()}
                FROM public.school_disciplinas d
                WHERE d.id = %s
                """,
                (str(disc_id),),
            )
            row = cur.fetchone()
    return jsonify({"item": _serialize_disciplina(row)}), 201


@bp.delete("/api/secretaria/cursos/<curso_id>/disciplinas/<disciplina_id>")
@require_gestor
def dissociate_disciplina_curso(curso_id: str, disciplina_id: str):
    inst = _instituicao_id()
    cid = _parse_uuid(curso_id, "curso")
    did = _parse_uuid(disciplina_id, "disciplina")
    if not cid or not did:
        return jsonify({"error": "Identificador inválido"}), 400
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            if not _assert_curso_instituicao(cur, inst, str(cid)):
                return jsonify({"error": "curso inválido"}), 400
            cur.execute(
                """
                DELETE FROM public.school_curso_disciplinas
                WHERE curso_id = %s AND disciplina_id = %s
                RETURNING id
                """,
                (str(cid), str(did)),
            )
            gone = cur.fetchone()
    if not gone:
        return jsonify({"error": "Associação não encontrada"}), 404
    return jsonify({"ok": True})


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

    curso_id = _parse_uuid(body.get("curso_id"), "curso") if body.get("curso_id") not in (None, "") else None
    if not curso_id:
        return jsonify({"error": "curso_id é obrigatório"}), 400

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
                        str(curso_id),
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

    curso_s = None
    if "curso_id" in body:
        if body.get("curso_id") in (None, ""):
            return jsonify({"error": "curso_id é obrigatório"}), 400
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
                        curso_id = COALESCE(%s, curso_id),
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
# Situação por período (corte do estado atual — não é histórico)
# ---------------------------------------------------------------------------
SITUACAO_AVISO = (
    "Corte do estado atual por período letivo; não é histórico de matrículas."
)


@bp.get("/api/secretaria/situacao-por-periodo")
@require_gestor
def situacao_por_periodo():
    """Agrega turmas/alunos/professores por período (estado atual)."""
    inst = _instituicao_id()
    unidade_raw = request.args.get("unidade_id")
    escopo = _unidade_escopo(unidade_raw)
    if isinstance(escopo, tuple):
        return escopo
    unidade_id = _parse_uuid(escopo or unidade_raw, "unidade") if (escopo or unidade_raw) else None
    if (escopo or unidade_raw) and not unidade_id:
        return jsonify({"error": "unidade_id inválido"}), 400

    curso_raw = request.args.get("curso_id")
    curso_id = None
    if curso_raw not in (None, ""):
        curso_id = _parse_uuid(curso_raw, "curso")
        if not curso_id:
            return jsonify({"error": "curso_id inválido"}), 400

    uid = str(unidade_id) if unidade_id else None
    cid = str(curso_id) if curso_id else None

    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                WITH periodos AS (
                    SELECT
                        p.id,
                        p.rotulo,
                        p.ano_letivo,
                        p.tipo_periodo,
                        p.status,
                        p.em_curso,
                        p.ativo,
                        p.data_inicio,
                        p.data_fim,
                        p.unidade_id,
                        u.nome AS unidade_nome
                    FROM public.school_periodos_letivos p
                    LEFT JOIN public.school_unidades u ON u.id = p.unidade_id
                    WHERE p.instituicao_id = %s
                      AND (
                        %s::uuid IS NULL
                        OR p.unidade_id = %s::uuid
                        OR p.unidade_id IS NULL
                      )
                ),
                cursos_c AS (
                    SELECT c.periodo_letivo_id AS periodo_id, count(*)::int AS n
                    FROM public.school_cursos c
                    JOIN periodos p ON p.id = c.periodo_letivo_id
                    WHERE c.ativo = TRUE
                      AND (%s::uuid IS NULL OR c.id = %s::uuid)
                    GROUP BY c.periodo_letivo_id
                ),
                turmas_c AS (
                    SELECT t.periodo_letivo_id AS periodo_id, count(*)::int AS n
                    FROM public.school_turmas t
                    JOIN periodos p ON p.id = t.periodo_letivo_id
                    WHERE t.ativa = TRUE
                      AND (%s::uuid IS NULL OR t.unidade_id = %s::uuid)
                      AND (%s::uuid IS NULL OR t.curso_id = %s::uuid)
                    GROUP BY t.periodo_letivo_id
                ),
                alunos_c AS (
                    SELECT t.periodo_letivo_id AS periodo_id, count(*)::int AS n
                    FROM public.school_alunos a
                    JOIN public.school_turmas t ON t.id = a.turma_id
                    JOIN periodos p ON p.id = t.periodo_letivo_id
                    WHERE a.ativo = TRUE
                      AND t.ativa = TRUE
                      AND (%s::uuid IS NULL OR t.unidade_id = %s::uuid)
                      AND (%s::uuid IS NULL OR t.curso_id = %s::uuid)
                    GROUP BY t.periodo_letivo_id
                ),
                profs_c AS (
                    SELECT a.periodo_id, count(DISTINCT a.professor_vinculo_id)::int AS n
                    FROM public.school_alocacoes_docentes a
                    JOIN periodos p ON p.id = a.periodo_id
                    WHERE a.ativo = TRUE
                      AND (%s::uuid IS NULL OR a.unidade_id = %s::uuid)
                      AND (
                        %s::uuid IS NULL
                        OR (
                          a.turma_id IS NOT NULL
                          AND EXISTS (
                            SELECT 1
                            FROM public.school_turmas t
                            WHERE t.id = a.turma_id
                              AND t.periodo_letivo_id = a.periodo_id
                              AND t.curso_id = %s::uuid
                              AND t.ativa = TRUE
                              AND (%s::uuid IS NULL OR t.unidade_id = %s::uuid)
                          )
                        )
                      )
                    GROUP BY a.periodo_id
                )
                SELECT
                    p.id AS periodo_id,
                    p.rotulo,
                    p.ano_letivo,
                    p.tipo_periodo,
                    p.status,
                    p.em_curso,
                    p.ativo,
                    p.data_inicio,
                    p.data_fim,
                    p.unidade_id,
                    p.unidade_nome,
                    COALESCE(cc.n, 0) AS n_cursos,
                    COALESCE(tc.n, 0) AS n_turmas,
                    COALESCE(ac.n, 0) AS n_alunos,
                    COALESCE(pc.n, 0) AS n_professores
                FROM periodos p
                LEFT JOIN cursos_c cc ON cc.periodo_id = p.id
                LEFT JOIN turmas_c tc ON tc.periodo_id = p.id
                LEFT JOIN alunos_c ac ON ac.periodo_id = p.id
                LEFT JOIN profs_c pc ON pc.periodo_id = p.id
                ORDER BY p.data_inicio DESC, p.rotulo ASC
                """,
                (
                    inst,
                    uid,
                    uid,
                    cid,
                    cid,
                    uid,
                    uid,
                    cid,
                    cid,
                    uid,
                    uid,
                    cid,
                    cid,
                    uid,
                    uid,
                    cid,
                    cid,
                    uid,
                    uid,
                ),
            )
            rows = cur.fetchall()

    return jsonify(
        {
            "meta": {
                "aviso": SITUACAO_AVISO,
                "filtros": {
                    "unidade_id": uid,
                    "curso_id": cid,
                },
            },
            "items": [
                {
                    "periodo_id": str(r["periodo_id"]),
                    "rotulo": r["rotulo"],
                    "ano_letivo": r["ano_letivo"],
                    "tipo_periodo": r.get("tipo_periodo"),
                    "status": r.get("status"),
                    "em_curso": bool(r.get("em_curso")),
                    "ativo": bool(r.get("ativo")),
                    "data_inicio": _iso(r.get("data_inicio")),
                    "data_fim": _iso(r.get("data_fim")),
                    "unidade_id": str(r["unidade_id"]) if r.get("unidade_id") else None,
                    "unidade_nome": r.get("unidade_nome"),
                    "n_cursos": int(r.get("n_cursos") or 0),
                    "n_turmas": int(r.get("n_turmas") or 0),
                    "n_alunos": int(r.get("n_alunos") or 0),
                    "n_professores": int(r.get("n_professores") or 0),
                }
                for r in rows
            ],
        }
    )


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


@bp.post("/api/secretaria/alunos/importar/preview")
@require_gestor
def importar_alunos_preview():
    """Dry-run: parse CSV + valida linhas sem gravar."""
    inst = _instituicao_id()
    turma_raw = request.form.get("turma_id") or request.args.get("turma_id")
    turma_id = _parse_uuid(turma_raw, "turma")
    if not turma_id:
        return jsonify({"error": "turma_id é obrigatório"}), 400

    upload = request.files.get("file")
    if not upload or not upload.filename:
        return jsonify({"error": "Arquivo CSV é obrigatório (campo file)"}), 400

    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            turma = _load_turma_contexto(cur, inst, turma_id)
            if not turma:
                return jsonify({"error": "turma inválida"}), 400
            denied = _assert_turma_import_escopo(turma)
            if denied:
                return denied
            existing = _load_matriculas_existentes(cur, inst)

    raw_bytes = upload.read()
    if not raw_bytes:
        return jsonify({"error": "Arquivo CSV vazio"}), 400

    text = _decode_csv_bytes(raw_bytes)
    parsed, parse_err = _parse_alunos_csv(text)
    if parse_err:
        return jsonify({"error": parse_err}), 400

    linhas = _validate_alunos_import_rows(
        parsed or [], existing, str(turma_id), turma.get("nome")
    )
    return jsonify(
        {
            "turma_id": str(turma_id),
            "turma_nome": turma["nome"],
            "resumo": _import_resumo(linhas),
            "linhas": linhas,
        }
    )


@bp.post("/api/secretaria/alunos/importar/confirmar")
@require_gestor
def importar_alunos_confirmar():
    """Aplica linhas ok do preview em transação atômica (criar + upsert)."""
    inst = _instituicao_id()
    body = request.get_json(silent=True) or {}
    turma_id = _parse_uuid(body.get("turma_id"), "turma")
    if not turma_id:
        return jsonify({"error": "turma_id é obrigatório"}), 400

    raw_linhas = body.get("linhas")
    if not isinstance(raw_linhas, list) or not raw_linhas:
        return jsonify({"error": "linhas deve ser uma lista não vazia"}), 400
    if len(raw_linhas) > IMPORT_ALUNOS_MAX_LINHAS:
        return jsonify(
            {"error": f"Limite de {IMPORT_ALUNOS_MAX_LINHAS} linhas úteis excedido"}
        ), 400

    permitir_geral = _import_flag(body.get("permitir_mudanca_turma"))
    auth_by_mat: dict[str, bool] = {}
    prepared: list[dict[str, Any]] = []
    for i, row in enumerate(raw_linhas, start=1):
        if not isinstance(row, dict):
            return jsonify({"error": f"Linha {i} inválida"}), 400
        mat_key = _text(row.get("matricula")).casefold()
        if mat_key:
            auth_by_mat[mat_key] = _import_flag(row.get("permitir_mudanca_turma"))
        prepared.append(
            {
                "linha": int(row.get("linha") or i),
                "nome": row.get("nome"),
                "matricula": row.get("matricula"),
                "data_nascimento": row.get("data_nascimento"),
                "data_nascimento_raw": row.get("data_nascimento"),
            }
        )

    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            turma = _load_turma_contexto(cur, inst, turma_id)
            if not turma:
                return jsonify({"error": "turma inválida"}), 400
            denied = _assert_turma_import_escopo(turma)
            if denied:
                return denied
            existing = _load_matriculas_existentes(cur, inst)
            validated = _validate_alunos_import_rows(
                prepared, existing, str(turma_id), turma.get("nome")
            )
            erros = [L for L in validated if L.get("status") == "erro"]
            if erros:
                first = erros[0]
                return (
                    jsonify(
                        {
                            "error": (
                                f"Revalidação falhou na linha {first.get('linha')}: "
                                f"{first.get('erro')}"
                            ),
                            "linhas": validated,
                            "resumo": _import_resumo(validated),
                        }
                    ),
                    400,
                )

            ok_linhas = [L for L in validated if L.get("status") == "ok"]
            if not ok_linhas:
                return jsonify({"error": "Nenhuma linha válida para importar"}), 400

            criados = 0
            atualizados = 0
            mudancas_turma = 0
            pulados: list[dict[str, Any]] = []
            try:
                for L in ok_linhas:
                    acao = L.get("acao")
                    if acao == "mudar_turma":
                        mat_key = _text(L.get("matricula")).casefold()
                        if not (permitir_geral or auth_by_mat.get(mat_key)):
                            pulados.append(
                                {
                                    "linha": L.get("linha"),
                                    "matricula": L.get("matricula"),
                                    "nome": L.get("nome"),
                                    "motivo": "mudança de turma não autorizada",
                                    "turma_atual_id": L.get("turma_atual_id"),
                                    "turma_atual_nome": L.get("turma_atual_nome"),
                                    "turma_nova_id": L.get("turma_nova_id")
                                    or str(turma_id),
                                    "turma_nova_nome": L.get("turma_nova_nome")
                                    or turma.get("nome"),
                                }
                            )
                            continue
                    nasc = None
                    if L.get("data_nascimento"):
                        nasc, _err = _parse_import_date(L.get("data_nascimento"))
                    if acao == "criar":
                        cur.execute(
                            """
                            INSERT INTO public.school_alunos (
                                instituicao_id, nome, matricula, turma_id, data_nascimento
                            )
                            VALUES (%s, %s, %s, %s, %s)
                            """,
                            (
                                inst,
                                L["nome"],
                                L["matricula"],
                                str(turma_id),
                                nasc,
                            ),
                        )
                        criados += 1
                    elif acao in ("atualizar", "mudar_turma"):
                        aluno_id = L.get("aluno_id_existente")
                        if not aluno_id:
                            raise RuntimeError("aluno_id_existente ausente no upsert")
                        # data_nascimento: só atualiza se enviada (não apaga com vazio)
                        cur.execute(
                            """
                            UPDATE public.school_alunos
                            SET nome = %s,
                                turma_id = %s,
                                data_nascimento = CASE
                                    WHEN %s::date IS NOT NULL THEN %s::date
                                    ELSE data_nascimento
                                END,
                                updated_at = CURRENT_TIMESTAMP
                            WHERE id = %s AND instituicao_id = %s
                            """,
                            (
                                L["nome"],
                                str(turma_id),
                                nasc,
                                nasc,
                                aluno_id,
                                inst,
                            ),
                        )
                        if cur.rowcount < 1:
                            raise RuntimeError("Aluno para atualização não encontrado")
                        if acao == "mudar_turma":
                            mudancas_turma += 1
                        else:
                            atualizados += 1
                    else:
                        raise RuntimeError(f"ação de importação desconhecida: {acao}")
            except pg_errors.UniqueViolation:
                conn.rollback()
                return jsonify(
                    {
                        "error": (
                            "Conflito de matrícula durante a importação "
                            "(outro processo pode ter criado a mesma matrícula). "
                            "Execute o preview novamente."
                        )
                    }
                ), 409
            except Exception as exc:
                conn.rollback()
                return jsonify({"error": f"Falha na importação: {exc}"}), 500

    return jsonify(
        {
            "criados": criados,
            "atualizados": atualizados,
            "mudancas_turma": mudancas_turma,
            "nao_aplicados": len(pulados),
            "pulados": pulados,
            "turma_id": str(turma_id),
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
                SELECT
                    v.id,
                    v.email_convite,
                    v.professor_b2c_id,
                    v.status_vinculo,
                    COALESCE(
                        (
                            SELECT json_agg(h.disciplina_id::text ORDER BY h.disciplina_id)
                            FROM public.school_professor_disciplina_habilitacao h
                            WHERE h.professor_vinculo_id = v.id
                        ),
                        '[]'::json
                    ) AS habilitacao_disciplina_ids
                FROM public.school_professores_vinculo v
                WHERE v.instituicao_id = %s
                  AND v.status_vinculo IN ('ativo', 'pendente')
                ORDER BY v.email_convite NULLS LAST, v.created_at ASC
                """,
                (inst,),
            )
            rows = cur.fetchall()
    items = []
    for r in rows:
        hab = r.get("habilitacao_disciplina_ids") or []
        if isinstance(hab, str):
            try:
                hab = json.loads(hab)
            except Exception:
                hab = []
        if not isinstance(hab, list):
            hab = []
        items.append(
            {
                "id": str(r["id"]),
                "professor_id": str(r["id"]),
                "email": r.get("email_convite") or "",
                "professor_b2c_id": str(r["professor_b2c_id"])
                if r.get("professor_b2c_id")
                else None,
                "status": r["status_vinculo"],
                "label": r.get("email_convite") or f"Professor {str(r['id'])[:8]}",
                "habilitacao_disciplina_ids": [str(x) for x in hab if x],
            }
        )
    return jsonify({"items": items})


@bp.get("/api/secretaria/professores/<vinculo_id>/habilitacoes")
@require_gestor
def list_habilitacoes_professor(vinculo_id: str):
    inst = _instituicao_id()
    vid = _parse_uuid(vinculo_id, "professor")
    if not vid:
        return jsonify({"error": "Identificador inválido"}), 400
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT 1 FROM public.school_professores_vinculo
                WHERE id = %s AND instituicao_id = %s
                """,
                (str(vid), inst),
            )
            if not cur.fetchone():
                return jsonify({"error": "Professor não encontrado"}), 404
            cur.execute(
                """
                SELECT h.disciplina_id, d.nome
                FROM public.school_professor_disciplina_habilitacao h
                JOIN public.school_disciplinas d ON d.id = h.disciplina_id
                WHERE h.professor_vinculo_id = %s
                ORDER BY d.nome
                """,
                (str(vid),),
            )
            rows = cur.fetchall()
    return jsonify(
        {
            "items": [
                {"disciplina_id": str(r["disciplina_id"]), "nome": r["nome"]}
                for r in rows
            ]
        }
    )


@bp.put("/api/secretaria/professores/<vinculo_id>/habilitacoes")
@require_gestor
def put_habilitacoes_professor(vinculo_id: str):
    """Cadastro informativo. Não afeta a regra de alocação."""
    inst = _instituicao_id()
    vid = _parse_uuid(vinculo_id, "professor")
    if not vid:
        return jsonify({"error": "Identificador inválido"}), 400
    body = request.get_json(silent=True) or {}
    raw_ids = body.get("disciplina_ids") or []
    if not isinstance(raw_ids, list):
        return jsonify({"error": "disciplina_ids deve ser uma lista"}), 400
    ids: list[str] = []
    for raw in raw_ids:
        uid = _parse_uuid(raw, "disciplina")
        if uid:
            ids.append(str(uid))
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT 1 FROM public.school_professores_vinculo
                WHERE id = %s AND instituicao_id = %s
                """,
                (str(vid), inst),
            )
            if not cur.fetchone():
                return jsonify({"error": "Professor não encontrado"}), 404
            if ids:
                cur.execute(
                    """
                    SELECT count(*)::int AS n
                    FROM public.school_disciplinas
                    WHERE instituicao_id = %s AND id = ANY(%s::uuid[])
                    """,
                    (inst, ids),
                )
                if int(cur.fetchone()["n"] or 0) != len(set(ids)):
                    return jsonify({"error": "disciplina inválida"}), 400
            cur.execute(
                """
                DELETE FROM public.school_professor_disciplina_habilitacao
                WHERE professor_vinculo_id = %s
                """,
                (str(vid),),
            )
            for did in set(ids):
                cur.execute(
                    """
                    INSERT INTO public.school_professor_disciplina_habilitacao (
                        professor_vinculo_id, disciplina_id
                    ) VALUES (%s, %s)
                    """,
                    (str(vid), did),
                )
    return jsonify({"ok": True, "disciplina_ids": list(set(ids))})


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
    curso_id = (turma or {}).get("curso_id") or disc.get("curso_id")
    curso_nome = (turma or {}).get("curso_nome") or disc.get("curso_nome")
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
                SELECT d.id, d.nome, d.ementa, d.instituicao_id
                FROM public.school_disciplinas d
                WHERE d.id = %s AND d.ativo = TRUE
                """,
                (str(disciplina_id),),
            )
            disc = cur.fetchone()
            if not disc:
                return jsonify({"error": "disciplina inválida"}), 400
            disc_inst = str(disc.get("instituicao_id") or "")
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
                "SELECT razao_social FROM public.school_instituicoes WHERE id = %s",
                (inst,),
            )
            inst_row = cur.fetchone() or {}
            instituicao_nome = str(inst_row.get("razao_social") or "").strip() or None

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
                if not _disciplina_no_catalogo_turma(
                    cur, inst, str(turma_id), str(disciplina_id)
                ):
                    return _reject_disc_fora_catalogo()

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
                "curso_id": (turma or {}).get("curso_id"),
                "curso_nome": (turma or {}).get("curso_nome"),
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
                    WHERE d.id = %s AND d.instituicao_id = %s
                    """,
                    (disciplina_s, inst),
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

            cur.execute(
                """
                SELECT turma_id, disciplina_id
                FROM public.school_alocacoes_docentes
                WHERE id = %s AND instituicao_id = %s
                """,
                (str(aid), inst),
            )
            current = cur.fetchone()
            if not current:
                return jsonify({"error": "Alocação não encontrada"}), 404
            final_turma = None if clear_turma else (turma_s or (
                str(current["turma_id"]) if current.get("turma_id") else None
            ))
            final_disc = disciplina_s or str(current["disciplina_id"])
            if final_turma and not _disciplina_no_catalogo_turma(
                cur, inst, final_turma, final_disc
            ):
                return _reject_disc_fora_catalogo()

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
                LEFT JOIN public.school_turmas t ON t.id = a.turma_id
                LEFT JOIN public.school_cursos c ON c.id = t.curso_id
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
                "curso_id": ctx.get("turma_curso_id"),
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
        "unidade_nome": row.get("unidade_nome"),
        "turma_id": str(row["turma_id"]) if row.get("turma_id") else None,
        "turma_nome": row.get("turma_nome"),
        "replicado_b2c": bool(row.get("replicado_b2c")),
        "replicado_b2c_em": _iso(row.get("replicado_b2c_em")),
        "created_at": _iso(row.get("created_at")),
    }


def _positive_professor_b2c_id(raw: Any) -> int | None:
    """id_clie real do B2C. Placeholder negativo (convite pendente, Etapa 13) → None."""
    try:
        n = int(raw)
    except (TypeError, ValueError):
        return None
    if n > 0:
        return n
    return None


def _targets_from_vinculo_rows(rows) -> tuple[list[str], list[int]]:
    emails: list[str] = []
    ids: list[int] = []
    for r in rows:
        bid = _positive_professor_b2c_id(r.get("professor_b2c_id"))
        if bid is None:
            continue
        if bid not in ids:
            ids.append(bid)
        email = str(r.get("email_convite") or "").strip().lower()
        if email and "@" in email and email not in emails:
            emails.append(email)
    return emails, ids


def _resolve_professor_targets(
    cur,
    inst: str,
    publico: str,
    unidade_id: str | None,
    turma_id: str | None,
) -> tuple[list[str], list[int]]:
    """Lista de professores-alvo. Só vínculo ativo + professor_b2c_id > 0.

    Recorte (mesma fonte da Alocação Docente / Planejamento Escolar):
      toda_instituicao / professores → vínculos ativos da instituição
      unidade → alocados a turmas daquela unidade
      turma → alocados à turma_id do comunicado
    """
    if publico == "turma" and turma_id:
        cur.execute(
            """
            SELECT DISTINCT v.email_convite, v.professor_b2c_id
            FROM public.school_alocacoes_docentes a
            JOIN public.school_professores_vinculo v
              ON v.id = a.professor_vinculo_id
            WHERE a.instituicao_id = %s
              AND a.turma_id = %s
              AND a.ativo = TRUE
              AND v.status_vinculo = 'ativo'
            """,
            (inst, turma_id),
        )
        return _targets_from_vinculo_rows(cur.fetchall())

    if publico == "unidade" and unidade_id:
        cur.execute(
            """
            SELECT DISTINCT v.email_convite, v.professor_b2c_id
            FROM public.school_alocacoes_docentes a
            JOIN public.school_professores_vinculo v
              ON v.id = a.professor_vinculo_id
            JOIN public.school_turmas t ON t.id = a.turma_id
            WHERE a.instituicao_id = %s
              AND a.ativo = TRUE
              AND v.status_vinculo = 'ativo'
              AND t.unidade_id = %s
            """,
            (inst, unidade_id),
        )
        return _targets_from_vinculo_rows(cur.fetchall())

    cur.execute(
        """
        SELECT email_convite, professor_b2c_id
        FROM public.school_professores_vinculo
        WHERE instituicao_id = %s
          AND status_vinculo = 'ativo'
        """,
        (inst,),
    )
    return _targets_from_vinculo_rows(cur.fetchall())


def _mark_comunicacao_replicado(cid: str, ok: bool) -> None:
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                if ok:
                    cur.execute(
                        """
                        UPDATE public.school_comunicacoes_eventos
                        SET replicado_b2c = TRUE,
                            replicado_b2c_em = CURRENT_TIMESTAMP,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = %s
                        """,
                        (cid,),
                    )
                else:
                    cur.execute(
                        """
                        UPDATE public.school_comunicacoes_eventos
                        SET replicado_b2c = FALSE,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = %s
                        """,
                        (cid,),
                    )
    except Exception as exc:
        print(
            f"[comunicacoes] falha ao gravar replicado_b2c: {exc}",
            file=sys.stderr,
            flush=True,
        )


def _dispatch_comunicacao_b2c(row: dict[str, Any], inst: str) -> dict[str, Any]:
    """Push fail-soft. Nunca levanta — o CRUD no School já foi gravado."""
    status = str(row.get("status") or "")
    cid = str(row["id"])
    if status not in ("publicado", "cancelado"):
        return {"ok": False, "skipped": True}
    try:
        with get_conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                emails, ids = _resolve_professor_targets(
                    cur,
                    inst,
                    str(row.get("publico_alvo") or ""),
                    str(row["unidade_id"]) if row.get("unidade_id") else None,
                    str(row["turma_id"]) if row.get("turma_id") else None,
                )
        if status == "publicado" and not ids:
            result = {
                "ok": False,
                "error": (
                    "Nenhum professor com conta no mural neste recorte. "
                    "Convites pendentes não recebem comunicado."
                ),
                "professor_b2c_ids": [],
            }
            _mark_comunicacao_replicado(cid, False)
            print(f"[comunicacoes] push id={cid} sem destinos B2C", flush=True)
            return result

        from b2c_integration_service import push_comunicado_to_b2c

        payload = {
            "origem_comunicado_school_id": cid,
            "instituicao_escola_id": inst,
            "titulo": row["titulo"],
            "descricao": row.get("descricao") or "",
            "tipo": row["tipo"],
            "data_hora_inicio": _iso(row.get("data_hora_inicio")),
            "data_hora_fim": _iso(row.get("data_hora_fim")),
            "status": status,
            "professor_b2c_ids": ids,
            "professor_emails": emails,
        }
        result = push_comunicado_to_b2c(payload)
        if not isinstance(result, dict):
            result = {"ok": False, "error": "resposta inválida do B2C"}
        result["professor_b2c_ids"] = ids
        ok = bool(result.get("ok"))
        _mark_comunicacao_replicado(cid, ok)
        print(
            f"[comunicacoes] push id={cid} status={status} n={len(ids)} ok={ok}",
            flush=True,
        )
        return result
    except Exception as exc:
        print(f"[comunicacoes] push falhou id={cid}: {exc}", file=sys.stderr, flush=True)
        _mark_comunicacao_replicado(cid, False)
        return {"ok": False, "error": str(exc)}


def _comunicacao_feedback(status: str, dispatch: dict[str, Any]) -> str:
    if status == "agendado":
        return "Comunicado agendado. Será enviado ao mural quando publicado."
    if status == "cancelado":
        if dispatch.get("ok"):
            return "Comunicado cancelado no mural dos professores."
        return (
            "Comunicado cancelado. Cancelamento ainda não replicado no mural dos professores."
        )
    if dispatch.get("ok"):
        return "Comunicado publicado no mural dos professores."
    err = str(dispatch.get("error") or "").strip()
    extra = f" {err}" if err else ""
    return f"Comunicado salvo. Não replicado no mural dos professores.{extra}"


def _fetch_comunicacao(cur, inst: str, cid: str):
    cur.execute(
        """
        SELECT e.*, u.nome AS unidade_nome, t.nome AS turma_nome
        FROM public.school_comunicacoes_eventos e
        LEFT JOIN public.school_unidades u ON u.id = e.unidade_id
        LEFT JOIN public.school_turmas t ON t.id = e.turma_id
        WHERE e.id = %s AND e.instituicao_id = %s
        """,
        (cid, inst),
    )
    return cur.fetchone()


def _resolver_alvo_comunicacao(
    cur, inst: str, publico: str, unidade_raw: Any, turma_raw: Any
):
    """Retorna (unidade_id|None, turma_id|None, erro|(None))."""
    turma_id = None
    unidade_id = None
    if turma_raw not in (None, ""):
        turma_id = _parse_uuid(turma_raw, "turma")
        if not turma_id:
            return None, None, (jsonify({"error": "turma_id inválido"}), 400)
    if unidade_raw not in (None, ""):
        unidade_id = _parse_uuid(unidade_raw, "unidade")
        if not unidade_id:
            return None, None, (jsonify({"error": "unidade_id inválido"}), 400)

    if publico == "turma":
        if not turma_id:
            return None, None, (jsonify({"error": "Selecione a turma"}), 400)
        turma = _load_turma_contexto(cur, inst, turma_id)
        if not turma:
            return None, None, (jsonify({"error": "Turma não encontrada"}), 404)
        denied = _assert_turma_import_escopo(turma)
        if denied:
            return None, None, denied
        uid = turma.get("unidade_id")
        return (str(uid) if uid else None, str(turma_id), None)

    if publico == "unidade":
        if not unidade_id:
            return None, None, (jsonify({"error": "Selecione a unidade"}), 400)
        denied = _unidade_no_escopo(unidade_id)
        if denied:
            return None, None, denied
        return str(unidade_id), None, None

    escopo = _unidade_escopo()
    if isinstance(escopo, tuple):
        return None, None, escopo
    if escopo:
        return None, None, (
            jsonify(
                {
                    "error": (
                        "Seu acesso é limitado à unidade. "
                        "Publique para a unidade ou para uma turma."
                    ),
                    "code": "FORBIDDEN_UNIDADE",
                }
            ),
            403,
        )
    return None, None, None


def _parse_comunicacao_body(body: dict[str, Any], *, existing: dict | None = None):
    """Campos de conteúdo. existing = merge em PATCH parcial (ex.: só status)."""
    src = existing or {}
    titulo = _text(body["titulo"]) if "titulo" in body else _text(src.get("titulo"))
    if not titulo:
        return None, (jsonify({"error": "Título obrigatório"}), 400)
    tipo = _text(body["tipo"]) if "tipo" in body else (_text(src.get("tipo")) or "reuniao_pedagogica")
    if tipo not in COM_TIPOS:
        return None, (jsonify({"error": "Tipo inválido"}), 400)
    publico = (
        _text(body["publico_alvo"])
        if "publico_alvo" in body
        else (_text(src.get("publico_alvo")) or "professores")
    )
    if publico not in COM_PUBLICOS:
        return None, (jsonify({"error": "Público-alvo inválido"}), 400)
    status = _text(body["status"]) if "status" in body else (_text(src.get("status")) or "publicado")
    if status not in COM_STATUS:
        return None, (jsonify({"error": "Status inválido"}), 400)

    if "data_hora_inicio" in body or not existing:
        inicio = _parse_dt_local(body.get("data_hora_inicio"), required=True)
        if inicio is False or inicio is None:
            return None, (jsonify({"error": "data_hora_inicio inválida ou obrigatória"}), 400)
    else:
        inicio = src.get("data_hora_inicio")

    if "data_hora_fim" in body or not existing:
        fim = _parse_dt_local(body.get("data_hora_fim"), required=False)
        if fim is False:
            return None, (jsonify({"error": "data_hora_fim inválida"}), 400)
    else:
        fim = src.get("data_hora_fim")

    descricao = (
        (_text(body.get("descricao")) or None)
        if "descricao" in body or not existing
        else (src.get("descricao") or None)
    )
    return {
        "titulo": titulo,
        "tipo": tipo,
        "publico": publico,
        "status": status,
        "inicio": inicio,
        "fim": fim,
        "descricao": descricao,
        "unidade_raw": body.get("unidade_id") if "unidade_id" in body else src.get("unidade_id"),
        "turma_raw": body.get("turma_id") if "turma_id" in body else src.get("turma_id"),
        "resolve_alvo": "publico_alvo" in body or "unidade_id" in body or "turma_id" in body or not existing,
    }, None


@bp.get("/api/secretaria/comunicacoes")
@require_gestor
def list_comunicacoes():
    inst = _instituicao_id()
    escopo = _unidade_escopo()
    if isinstance(escopo, tuple):
        return escopo
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            sql = """
                SELECT e.*, u.nome AS unidade_nome, t.nome AS turma_nome
                FROM public.school_comunicacoes_eventos e
                LEFT JOIN public.school_unidades u ON u.id = e.unidade_id
                LEFT JOIN public.school_turmas t ON t.id = e.turma_id
                WHERE e.instituicao_id = %s
            """
            params: list[Any] = [inst]
            if escopo:
                sql += " AND (e.unidade_id = %s OR t.unidade_id = %s)"
                params.extend([escopo, escopo])
            sql += " ORDER BY e.created_at DESC, e.data_hora_inicio DESC NULLS LAST"
            cur.execute(sql, params)
            rows = [_serialize_comunicacao(r) for r in cur.fetchall()]
    return jsonify({"items": rows})


@bp.post("/api/secretaria/comunicacoes")
@require_gestor
def create_comunicacao():
    inst = _instituicao_id()
    body = request.get_json(silent=True) or {}
    parsed, err = _parse_comunicacao_body(body)
    if err:
        return err
    gestor = session.get(SESSION_KEY) or {}
    gestor_id = _parse_uuid(gestor.get("id"), "gestor")

    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            unidade, turma, alvo_err = _resolver_alvo_comunicacao(
                cur, inst, parsed["publico"], parsed["unidade_raw"], parsed["turma_raw"]
            )
            if alvo_err:
                return alvo_err
            cur.execute(
                """
                INSERT INTO public.school_comunicacoes_eventos (
                    instituicao_id, unidade_id, turma_id, titulo, descricao, tipo,
                    data_hora_inicio, data_hora_fim, publico_alvo,
                    status, criado_por_gestor_id
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
                RETURNING *
                """,
                (
                    inst,
                    unidade,
                    turma,
                    parsed["titulo"],
                    parsed["descricao"],
                    parsed["tipo"],
                    parsed["inicio"],
                    parsed["fim"],
                    parsed["publico"],
                    parsed["status"],
                    str(gestor_id) if gestor_id else None,
                ),
            )
            row = cur.fetchone()

    dispatch = _dispatch_comunicacao_b2c(row, inst)
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            row = _fetch_comunicacao(cur, inst, str(row["id"])) or row

    return (
        jsonify(
            {
                "item": _serialize_comunicacao(row),
                "b2c_dispatch": dispatch,
                "message": _comunicacao_feedback(parsed["status"], dispatch),
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

    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            existing = _fetch_comunicacao(cur, inst, str(cid))
            if not existing:
                return jsonify({"error": "Comunicação não encontrada"}), 404
            parsed, err = _parse_comunicacao_body(body, existing=existing)
            if err:
                return err
            unidade = str(existing["unidade_id"]) if existing.get("unidade_id") else None
            turma = str(existing["turma_id"]) if existing.get("turma_id") else None
            if parsed["resolve_alvo"]:
                unidade, turma, alvo_err = _resolver_alvo_comunicacao(
                    cur, inst, parsed["publico"], parsed["unidade_raw"], parsed["turma_raw"]
                )
                if alvo_err:
                    return alvo_err
            cur.execute(
                """
                UPDATE public.school_comunicacoes_eventos
                SET titulo = %s,
                    descricao = %s,
                    tipo = %s,
                    publico_alvo = %s,
                    unidade_id = %s,
                    turma_id = %s,
                    data_hora_inicio = %s,
                    data_hora_fim = %s,
                    status = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s AND instituicao_id = %s
                RETURNING *
                """,
                (
                    parsed["titulo"],
                    parsed["descricao"],
                    parsed["tipo"],
                    parsed["publico"],
                    unidade,
                    turma,
                    parsed["inicio"],
                    parsed["fim"],
                    parsed["status"],
                    str(cid),
                    inst,
                ),
            )
            row = cur.fetchone()

    dispatch = _dispatch_comunicacao_b2c(row, inst)
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            row = _fetch_comunicacao(cur, inst, str(cid)) or row

    return jsonify(
        {
            "item": _serialize_comunicacao(row),
            "b2c_dispatch": dispatch,
            "message": _comunicacao_feedback(parsed["status"], dispatch),
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
                WHERE d.id = %s AND d.instituicao_id = %s
                """,
                (str(disciplina_id), inst),
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

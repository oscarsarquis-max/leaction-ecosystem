"""
Estruturação Pedagógica — Etapa 2/4: Cursos + Disciplinas.

Auth: sessão com id_clie; propriedade via JOIN
  disciplina → curso → periodo → instituicao.id_clie
(mesmo padrão da Etapa 1 nos períodos).

401 sem sessão; 404 se registro inexistente ou de outro professor.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from functools import wraps
from typing import Any

from flask import Blueprint, jsonify, request, session
from psycopg2 import errors as pg_errors
from psycopg2.extras import RealDictCursor

from db import get_conn

cursos_disciplinas_bp = Blueprint("cursos_disciplinas", __name__)

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


def require_session(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        user = session.get("user")
        if not user or not user.get("id_clie"):
            return jsonify({"error": "Não autenticado"}), 401
        return view(*args, **kwargs)

    return wrapped


def _id_clie() -> int:
    return int(session["user"]["id_clie"])


def _is_institutional_session() -> bool:
    user = session.get("user") or {}
    return bool(user.get("is_institutional") or user.get("instituicao_b2b_id"))


def _forbid_institutional_write():
    if _is_institutional_session():
        return jsonify({
            "error": (
                "Sua estrutura acadêmica é definida pela escola (Secretaria). "
                "Não é possível alterar curso, disciplina ou turma aqui."
            ),
            "code": "school_source_of_truth",
        }), 403
    return None


def _sql_escopo_curso(
    alias: str = "c", *, id_clie: int | None = None
) -> tuple[str, list[Any]]:
    """
    Solo: só curso cadastrado pelo próprio professor.
    Vinculado (escola): só cursos para os quais a Secretaria alocou o professor.
    Retorna (fragmento SQL, params extras).
    """
    cid = int(id_clie if id_clie is not None else _id_clie())
    if _is_institutional_session():
        return (
            f" AND {alias}.id IN ("
            f" SELECT a.curso_id FROM public.inove_alocacoes_escola a"
            f"  WHERE a.id_clie = %s AND a.ativo = TRUE"
            f"    AND a.curso_id IS NOT NULL"
            f" )",
            [cid],
        )
    return (
        f" AND COALESCE({alias}.origem_school, FALSE) = FALSE"
        f" AND {alias}.school_curso_id IS NULL",
        [],
    )


def _sql_escopo_disciplina(
    alias: str = "d", *, id_clie: int | None = None
) -> tuple[str, list[Any]]:
    cid = int(id_clie if id_clie is not None else _id_clie())
    if _is_institutional_session():
        return (
            f" AND {alias}.id IN ("
            f" SELECT a.disciplina_id FROM public.inove_alocacoes_escola a"
            f"  WHERE a.id_clie = %s AND a.ativo = TRUE"
            f"    AND a.disciplina_id IS NOT NULL"
            f" )",
            [cid],
        )
    return (
        f" AND COALESCE({alias}.origem_school, FALSE) = FALSE"
        f" AND {alias}.school_disciplina_id IS NULL",
        [],
    )


def _sql_escopo_turma(
    alias: str = "t", *, id_clie: int | None = None
) -> tuple[str, list[Any]]:
    cid = int(id_clie if id_clie is not None else _id_clie())
    if _is_institutional_session():
        return (
            f" AND {alias}.id IN ("
            f" SELECT a.turma_id FROM public.inove_alocacoes_escola a"
            f"  WHERE a.id_clie = %s AND a.ativo = TRUE"
            f"    AND a.turma_id IS NOT NULL"
            f" )",
            [cid],
        )
    return (
        f" AND COALESCE({alias}.origem_school, FALSE) = FALSE"
        f" AND {alias}.school_turma_id IS NULL",
        [],
    )


def _sql_disciplina_do_curso(disc_alias: str, curso_expr: str) -> str:
    """Disciplina no curso via dono legado (curso_id) ou catálogo N:N."""
    return (
        f"("
        f" {disc_alias}.curso_id = {curso_expr}"
        f" OR EXISTS ("
        f"   SELECT 1 FROM public.inove_curso_disciplinas _cd"
        f"    WHERE _cd.curso_id = {curso_expr}"
        f"      AND _cd.disciplina_id = {disc_alias}.id"
        f" )"
        f")"
    )


def _jsonable(row: dict | None) -> dict | None:
    if not row:
        return None
    out: dict[str, Any] = {}
    for key, value in row.items():
        if isinstance(value, datetime):
            out[key] = value.isoformat()
        elif isinstance(value, date):
            out[key] = value.isoformat()
        elif isinstance(value, Decimal):
            out[key] = float(value)
        else:
            out[key] = value
    return out


def _parse_carga(value: Any, field: str) -> Decimal | None:
    if value in (None, ""):
        return None
    try:
        carga = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"{field} inválida.") from exc
    if carga < 0:
        raise ValueError(f"{field} inválida.")
    return carga


def _get_periodo_owned(cur, periodo_id: int, id_clie: int):
    cur.execute(
        """
        SELECT p.*, i.id_clie, i.nome AS instituicao_nome, i.id AS instituicao_id
          FROM public.inove_periodos_letivos p
          JOIN public.inove_instituicoes i ON i.id = p.instituicao_id
         WHERE p.id = %s
           AND i.id_clie = %s
           AND p.ativo = TRUE
           AND i.ativo = TRUE
        """,
        (periodo_id, id_clie),
    )
    return cur.fetchone()


def _get_curso_owned(cur, curso_id: int, id_clie: int, *, include_inactive: bool = False):
    escopo_sql, escopo_params = _sql_escopo_curso("c", id_clie=id_clie)
    sql = f"""
        SELECT c.*,
               p.id AS periodo_letivo_id,
               p.rotulo AS periodo_rotulo,
               i.id AS instituicao_id,
               i.nome AS instituicao_nome,
               i.id_clie
          FROM public.inove_cursos c
          JOIN public.inove_periodos_letivos p ON p.id = c.periodo_letivo_id
          JOIN public.inove_instituicoes i ON i.id = p.instituicao_id
         WHERE c.id = %s AND i.id_clie = %s
               {escopo_sql}
    """
    if not include_inactive:
        sql += " AND c.ativo = TRUE AND p.ativo = TRUE AND i.ativo = TRUE"
    cur.execute(sql, (curso_id, id_clie, *escopo_params))
    return cur.fetchone()


def _get_disciplina_owned(cur, disciplina_id: int, id_clie: int, *, include_inactive: bool = False):
    escopo_sql, escopo_params = _sql_escopo_disciplina("d", id_clie=id_clie)
    sql = f"""
        SELECT d.*,
               c.id AS curso_id,
               c.nome AS curso_nome,
               p.id AS periodo_letivo_id,
               i.id AS instituicao_id,
               i.id_clie
          FROM public.inove_disciplinas d
          JOIN public.inove_cursos c ON c.id = d.curso_id
          JOIN public.inove_periodos_letivos p ON p.id = c.periodo_letivo_id
          JOIN public.inove_instituicoes i ON i.id = p.instituicao_id
         WHERE d.id = %s AND i.id_clie = %s
               {escopo_sql}
    """
    if not include_inactive:
        sql += " AND d.ativo = TRUE AND c.ativo = TRUE AND p.ativo = TRUE AND i.ativo = TRUE"
    cur.execute(sql, (disciplina_id, id_clie, *escopo_params))
    return cur.fetchone()


# ---------------------------------------------------------------------------
# Cursos
# ---------------------------------------------------------------------------


@cursos_disciplinas_bp.post("/api/periodos-letivos/<int:periodo_id>/cursos")
@require_session
def criar_curso(periodo_id: int):
    blocked = _forbid_institutional_write()
    if blocked:
        return blocked
    data = request.get_json(silent=True) or {}
    nome = str(data.get("nome") or "").strip()
    if not nome:
        return jsonify({"error": "Informe o nome do curso."}), 400

    nivel = data.get("nivel")
    if nivel not in (None, ""):
        nivel = str(nivel).strip().lower()
        if nivel not in NIVEIS:
            return jsonify({"error": "nivel inválido."}), 400
    else:
        nivel = None

    try:
        carga = _parse_carga(data.get("carga_horaria_total_horas"), "carga_horaria_total_horas")
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    try:
        with get_conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                periodo = _get_periodo_owned(cur, periodo_id, _id_clie())
                if not periodo:
                    return jsonify({"error": "Período letivo não encontrado."}), 404
                cur.execute(
                    """
                    INSERT INTO public.inove_cursos (
                        periodo_letivo_id, nome, nivel, turma_turno,
                        carga_horaria_total_horas, observacoes
                    ) VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING *
                    """,
                    (
                        periodo_id,
                        nome[:255],
                        nivel,
                        (str(data.get("turma_turno") or "").strip()[:120] or None),
                        carga,
                        (str(data.get("observacoes") or "").strip() or None),
                    ),
                )
                row = cur.fetchone()
                # Se veio turma_turno legado no create, materializa 1 turma (1:N).
                turma_nome = (str(data.get("turma_turno") or "").strip()[:120] or None)
                if turma_nome and row:
                    try:
                        cur.execute(
                            """
                            INSERT INTO public.inove_turmas (curso_id, nome)
                            SELECT %s, %s
                             WHERE NOT EXISTS (
                               SELECT 1 FROM public.inove_turmas t
                                WHERE t.curso_id = %s AND t.ativo = TRUE
                                  AND lower(t.nome) = lower(%s)
                             )
                            """,
                            (int(row["id"]), turma_nome, int(row["id"]), turma_nome),
                        )
                    except pg_errors.UndefinedTable:
                        pass
                conn.commit()
        return jsonify({"curso": _jsonable(row)}), 201
    except pg_errors.UndefinedTable:
        return jsonify({
            "error": "Schema pendente. Aplique a migration 009/027.",
            "code": "schema_pending",
        }), 503
    except Exception as exc:
        print(f"[cursos] criar: {exc}")
        return jsonify({"error": "Falha ao criar curso."}), 500


@cursos_disciplinas_bp.get("/api/periodos-letivos/<int:periodo_id>/cursos")
@require_session
def listar_cursos(periodo_id: int):
    try:
        with get_conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                periodo = _get_periodo_owned(cur, periodo_id, _id_clie())
                if not periodo:
                    return jsonify({"error": "Período letivo não encontrado."}), 404
                escopo_sql, escopo_params = _sql_escopo_curso("c")
                cur.execute(
                    f"""
                    SELECT c.*,
                           (
                             SELECT COUNT(*)::int
                               FROM public.inove_disciplinas d
                              WHERE d.ativo = TRUE
                                AND {_sql_disciplina_do_curso("d", "c.id")}
                           ) AS disciplinas_count,
                           (
                             SELECT COUNT(*)::int
                               FROM public.inove_turmas t
                              WHERE t.curso_id = c.id AND t.ativo = TRUE
                           ) AS turmas_count
                      FROM public.inove_cursos c
                      JOIN public.inove_periodos_letivos p ON p.id = c.periodo_letivo_id
                      JOIN public.inove_instituicoes i ON i.id = p.instituicao_id
                     WHERE c.periodo_letivo_id = %s
                       AND c.ativo = TRUE
                       AND i.id_clie = %s
                       AND i.ativo = TRUE
                       AND p.ativo = TRUE
                       {escopo_sql}
                     ORDER BY c.nome ASC, c.id ASC
                    """,
                    (periodo_id, _id_clie(), *escopo_params),
                )
                rows = cur.fetchall() or []
        return jsonify({
            "periodo_letivo_id": periodo_id,
            "cursos": [_jsonable(r) for r in rows],
            "source": "alocacoes_escola" if _is_institutional_session() else "professor",
        })
    except pg_errors.UndefinedTable:
        return jsonify({"error": "Schema pendente.", "code": "schema_pending"}), 503
    except Exception as exc:
        print(f"[cursos] listar: {exc}")
        return jsonify({"error": "Falha ao listar cursos."}), 500


@cursos_disciplinas_bp.get("/api/me/cursos")
@require_session
def listar_meus_cursos():
    """Cursos do professor: solo = cadastro próprio; vinculado = só alocados pela escola."""
    try:
        with get_conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                escopo_sql, escopo_params = _sql_escopo_curso("c")
                cur.execute(
                    f"""
                    SELECT c.id,
                           c.nome,
                           c.nivel,
                           c.periodo_letivo_id,
                           p.rotulo AS periodo_rotulo,
                           p.ano_letivo,
                           i.id AS instituicao_id,
                           i.nome AS instituicao_nome
                      FROM public.inove_cursos c
                      JOIN public.inove_periodos_letivos p ON p.id = c.periodo_letivo_id
                      JOIN public.inove_instituicoes i ON i.id = p.instituicao_id
                     WHERE i.id_clie = %s
                       AND c.ativo = TRUE
                       AND p.ativo = TRUE
                       AND i.ativo = TRUE
                       {escopo_sql}
                     ORDER BY i.nome, p.ano_letivo DESC, c.nome, c.id
                    """,
                    (_id_clie(), *escopo_params),
                )
                rows = cur.fetchall() or []
        return jsonify({
            "cursos": [_jsonable(r) for r in rows],
            "source": (
                "alocacoes_escola" if _is_institutional_session() else "professor"
            ),
        })
    except pg_errors.UndefinedTable:
        return jsonify({
            "error": "Schema pendente.",
            "code": "schema_pending",
            "cursos": [],
        }), 503
    except Exception as exc:
        print(f"[cursos] listar_meus: {exc}")
        return jsonify({"error": "Falha ao listar cursos."}), 500


@cursos_disciplinas_bp.get("/api/cursos/<int:curso_id>")
@require_session
def detalhe_curso(curso_id: int):
    try:
        with get_conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                row = _get_curso_owned(cur, curso_id, _id_clie())
                if not row:
                    return jsonify({"error": "Curso não encontrado."}), 404
        return jsonify({"curso": _jsonable(row)})
    except pg_errors.UndefinedTable:
        return jsonify({"error": "Schema pendente.", "code": "schema_pending"}), 503


@cursos_disciplinas_bp.put("/api/cursos/<int:curso_id>")
@require_session
def atualizar_curso(curso_id: int):
    blocked = _forbid_institutional_write()
    if blocked:
        return blocked
    data = request.get_json(silent=True) or {}
    try:
        with get_conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                current = _get_curso_owned(cur, curso_id, _id_clie())
                if not current:
                    return jsonify({"error": "Curso não encontrado."}), 404
                if current.get("origem_school") or current.get("school_curso_id"):
                    return jsonify({
                        "error": "Curso espelhado da escola — somente leitura.",
                        "code": "school_source_of_truth",
                    }), 403

                nome = str(data.get("nome", current["nome"]) or "").strip()
                if not nome:
                    return jsonify({"error": "Informe o nome do curso."}), 400

                if "nivel" in data:
                    nivel = data.get("nivel")
                    if nivel in (None, ""):
                        nivel = None
                    else:
                        nivel = str(nivel).strip().lower()
                        if nivel not in NIVEIS:
                            return jsonify({"error": "nivel inválido."}), 400
                else:
                    nivel = current.get("nivel")

                try:
                    if "carga_horaria_total_horas" in data:
                        carga = _parse_carga(
                            data.get("carga_horaria_total_horas"),
                            "carga_horaria_total_horas",
                        )
                    else:
                        carga = current.get("carga_horaria_total_horas")
                except ValueError as exc:
                    return jsonify({"error": str(exc)}), 400

                cur.execute(
                    """
                    UPDATE public.inove_cursos
                       SET nome = %s,
                           nivel = %s,
                           turma_turno = %s,
                           carga_horaria_total_horas = %s,
                           observacoes = %s,
                           updated_at = CURRENT_TIMESTAMP
                     WHERE id = %s
                    RETURNING *
                    """,
                    (
                        nome[:255],
                        nivel,
                        (
                            str(data.get("turma_turno", current.get("turma_turno") or ""))
                            .strip()[:120]
                            or None
                        ),
                        carga,
                        (
                            str(
                                data.get("observacoes", current.get("observacoes") or "")
                            ).strip()
                            or None
                        ),
                        curso_id,
                    ),
                )
                row = cur.fetchone()
                conn.commit()
        return jsonify({"curso": _jsonable(row)})
    except pg_errors.UndefinedTable:
        return jsonify({"error": "Schema pendente.", "code": "schema_pending"}), 503
    except Exception as exc:
        print(f"[cursos] atualizar: {exc}")
        return jsonify({"error": "Falha ao atualizar curso."}), 500


@cursos_disciplinas_bp.delete("/api/cursos/<int:curso_id>")
@require_session
def soft_delete_curso(curso_id: int):
    blocked = _forbid_institutional_write()
    if blocked:
        return blocked
    try:
        with get_conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                current = _get_curso_owned(cur, curso_id, _id_clie())
                if not current:
                    return jsonify({"error": "Curso não encontrado."}), 404
                if current.get("origem_school") or current.get("school_curso_id"):
                    return jsonify({
                        "error": "Curso espelhado da escola — somente leitura.",
                        "code": "school_source_of_truth",
                    }), 403

                cur.execute(
                    f"""
                    SELECT COUNT(*)::int AS n
                      FROM public.inove_disciplinas d
                     WHERE d.ativo = TRUE
                       AND {_sql_disciplina_do_curso("d", "%s")}
                    """,
                    (curso_id, curso_id),
                )
                n = int((cur.fetchone() or {}).get("n") or 0)
                if n > 0:
                    return jsonify({
                        "error": (
                            "Não é possível desativar: há disciplina ativa vinculada. "
                            "Desative as disciplinas antes."
                        ),
                        "code": "disciplina_ativa",
                    }), 409

                cur.execute(
                    """
                    UPDATE public.inove_cursos
                       SET ativo = FALSE,
                           updated_at = CURRENT_TIMESTAMP
                     WHERE id = %s
                    RETURNING id
                    """,
                    (curso_id,),
                )
                conn.commit()
        return jsonify({"ok": True, "id": curso_id})
    except pg_errors.UndefinedTable:
        return jsonify({"error": "Schema pendente.", "code": "schema_pending"}), 503
    except Exception as exc:
        print(f"[cursos] delete: {exc}")
        return jsonify({"error": "Falha ao desativar curso."}), 500


# ---------------------------------------------------------------------------
# Disciplinas
# ---------------------------------------------------------------------------


@cursos_disciplinas_bp.post("/api/cursos/<int:curso_id>/disciplinas")
@require_session
def criar_disciplina(curso_id: int):
    blocked = _forbid_institutional_write()
    if blocked:
        return blocked
    data = request.get_json(silent=True) or {}
    nome = str(data.get("nome") or "").strip()
    if not nome:
        return jsonify({"error": "Informe o nome da disciplina."}), 400
    try:
        carga = _parse_carga(data.get("carga_horaria_horas"), "carga_horaria_horas")
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    try:
        with get_conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                curso = _get_curso_owned(cur, curso_id, _id_clie())
                if not curso:
                    return jsonify({"error": "Curso não encontrado."}), 404
                cur.execute(
                    """
                    INSERT INTO public.inove_disciplinas (
                        curso_id, instituicao_id, nome, codigo, carga_horaria_horas, ementa
                    ) VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING *
                    """,
                    (
                        curso_id,
                        curso.get("instituicao_id"),
                        nome[:255],
                        (str(data.get("codigo") or "").strip()[:80] or None),
                        carga,
                        (str(data.get("ementa") or "").strip() or None),
                    ),
                )
                row = cur.fetchone()
                if row:
                    cur.execute(
                        """
                        INSERT INTO public.inove_curso_disciplinas (curso_id, disciplina_id)
                        VALUES (%s, %s)
                        ON CONFLICT (curso_id, disciplina_id) DO NOTHING
                        """,
                        (curso_id, int(row["id"])),
                    )
                conn.commit()
        return jsonify({"disciplina": _jsonable(row)}), 201
    except pg_errors.UndefinedTable:
        return jsonify({"error": "Schema pendente.", "code": "schema_pending"}), 503
    except Exception as exc:
        print(f"[disciplinas] criar: {exc}")
        return jsonify({"error": "Falha ao criar disciplina."}), 500


@cursos_disciplinas_bp.get("/api/cursos/<int:curso_id>/disciplinas")
@require_session
def listar_disciplinas(curso_id: int):
    try:
        with get_conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                curso = _get_curso_owned(cur, curso_id, _id_clie())
                if not curso:
                    return jsonify({"error": "Curso não encontrado."}), 404
                escopo_sql, escopo_params = _sql_escopo_disciplina("d")
                cur.execute(
                    f"""
                    SELECT DISTINCT d.*
                      FROM public.inove_disciplinas d
                     WHERE d.ativo = TRUE
                       AND {_sql_disciplina_do_curso("d", "%s")}
                       {escopo_sql}
                     ORDER BY d.nome ASC, d.id ASC
                    """,
                    (curso_id, curso_id, *escopo_params),
                )
                rows = cur.fetchall() or []
        return jsonify({
            "curso_id": curso_id,
            "disciplinas": [_jsonable(r) for r in rows],
            "source": "alocacoes_escola" if _is_institutional_session() else "professor",
        })
    except pg_errors.UndefinedTable:
        return jsonify({"error": "Schema pendente.", "code": "schema_pending"}), 503
    except Exception as exc:
        print(f"[disciplinas] listar: {exc}")
        return jsonify({"error": "Falha ao listar disciplinas."}), 500


@cursos_disciplinas_bp.get("/api/disciplinas/<int:disciplina_id>")
@require_session
def detalhe_disciplina(disciplina_id: int):
    try:
        with get_conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                row = _get_disciplina_owned(cur, disciplina_id, _id_clie())
                if not row:
                    return jsonify({"error": "Disciplina não encontrada."}), 404
        return jsonify({"disciplina": _jsonable(row)})
    except pg_errors.UndefinedTable:
        return jsonify({"error": "Schema pendente.", "code": "schema_pending"}), 503


@cursos_disciplinas_bp.put("/api/disciplinas/<int:disciplina_id>")
@require_session
def atualizar_disciplina(disciplina_id: int):
    blocked = _forbid_institutional_write()
    if blocked:
        return blocked
    data = request.get_json(silent=True) or {}
    try:
        with get_conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                current = _get_disciplina_owned(cur, disciplina_id, _id_clie())
                if not current:
                    return jsonify({"error": "Disciplina não encontrada."}), 404
                if current.get("origem_school") or current.get("school_disciplina_id"):
                    return jsonify({
                        "error": "Disciplina espelhada da escola — somente leitura.",
                        "code": "school_source_of_truth",
                    }), 403

                nome = str(data.get("nome", current["nome"]) or "").strip()
                if not nome:
                    return jsonify({"error": "Informe o nome da disciplina."}), 400

                try:
                    if "carga_horaria_horas" in data:
                        carga = _parse_carga(
                            data.get("carga_horaria_horas"), "carga_horaria_horas"
                        )
                    else:
                        carga = current.get("carga_horaria_horas")
                except ValueError as exc:
                    return jsonify({"error": str(exc)}), 400

                cur.execute(
                    """
                    UPDATE public.inove_disciplinas
                       SET nome = %s,
                           codigo = %s,
                           carga_horaria_horas = %s,
                           ementa = %s,
                           updated_at = CURRENT_TIMESTAMP
                     WHERE id = %s
                    RETURNING *
                    """,
                    (
                        nome[:255],
                        (
                            str(data.get("codigo", current.get("codigo") or ""))
                            .strip()[:80]
                            or None
                        ),
                        carga,
                        (
                            str(data.get("ementa", current.get("ementa") or "")).strip()
                            or None
                        ),
                        disciplina_id,
                    ),
                )
                row = cur.fetchone()
                conn.commit()
        return jsonify({"disciplina": _jsonable(row)})
    except pg_errors.UndefinedTable:
        return jsonify({"error": "Schema pendente.", "code": "schema_pending"}), 503
    except Exception as exc:
        print(f"[disciplinas] atualizar: {exc}")
        return jsonify({"error": "Falha ao atualizar disciplina."}), 500


@cursos_disciplinas_bp.delete("/api/disciplinas/<int:disciplina_id>")
@require_session
def soft_delete_disciplina(disciplina_id: int):
    blocked = _forbid_institutional_write()
    if blocked:
        return blocked
    try:
        with get_conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                current = _get_disciplina_owned(cur, disciplina_id, _id_clie())
                if not current:
                    return jsonify({"error": "Disciplina não encontrada."}), 404
                if current.get("origem_school") or current.get("school_disciplina_id"):
                    return jsonify({
                        "error": "Disciplina espelhada da escola — somente leitura.",
                        "code": "school_source_of_truth",
                    }), 403

                # Etapa 3: bloquear se houver aula/evento vinculado
                cur.execute(
                    """
                    SELECT
                      (SELECT COUNT(*)::int FROM public.inove_aulas_simples
                        WHERE disciplina_id = %s) AS aulas_simples,
                      (SELECT COUNT(*)::int FROM public.inove_agenda_eventos
                        WHERE disciplina_id = %s) AS agenda_eventos
                    """,
                    (disciplina_id, disciplina_id),
                )
                counts = cur.fetchone() or {}
                n_aulas = int(counts.get("aulas_simples") or 0)
                n_agenda = int(counts.get("agenda_eventos") or 0)
                if n_aulas + n_agenda > 0:
                    return jsonify({
                        "error": (
                            "Não é possível desativar: há aula ou evento vinculado a esta disciplina."
                        ),
                        "code": "aula_vinculada",
                        "aulas_simples": n_aulas,
                        "agenda_eventos": n_agenda,
                    }), 409

                cur.execute(
                    """
                    UPDATE public.inove_disciplinas
                       SET ativo = FALSE,
                           updated_at = CURRENT_TIMESTAMP
                     WHERE id = %s
                    RETURNING id
                    """,
                    (disciplina_id,),
                )
                conn.commit()
        return jsonify({"ok": True, "id": disciplina_id})
    except pg_errors.UndefinedTable:
        return jsonify({"error": "Schema pendente.", "code": "schema_pending"}), 503
    except Exception as exc:
        print(f"[disciplinas] delete: {exc}")
        return jsonify({"error": "Falha ao desativar disciplina."}), 500


# ---------------------------------------------------------------------------
# Turmas (1 curso → N turmas)
# ---------------------------------------------------------------------------


@cursos_disciplinas_bp.get("/api/cursos/<int:curso_id>/turmas")
@require_session
def listar_turmas(curso_id: int):
    try:
        with get_conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                curso = _get_curso_owned(cur, curso_id, _id_clie())
                if not curso:
                    return jsonify({"error": "Curso não encontrado."}), 404
                escopo_sql, escopo_params = _sql_escopo_turma("t")
                cur.execute(
                    f"""
                    SELECT t.*
                      FROM public.inove_turmas t
                     WHERE t.curso_id = %s AND t.ativo = TRUE
                       {escopo_sql}
                     ORDER BY t.nome ASC, t.id ASC
                    """,
                    (curso_id, *escopo_params),
                )
                rows = cur.fetchall() or []
        return jsonify({
            "curso_id": curso_id,
            "turmas": [_jsonable(r) for r in rows],
            "source": "alocacoes_escola" if _is_institutional_session() else "professor",
        })
    except pg_errors.UndefinedTable:
        return jsonify({
            "error": "Schema pendente. Aplique a migration 027.",
            "code": "schema_pending",
        }), 503
    except Exception as exc:
        print(f"[turmas] listar: {exc}")
        return jsonify({"error": "Falha ao listar turmas."}), 500


@cursos_disciplinas_bp.post("/api/cursos/<int:curso_id>/turmas")
@require_session
def criar_turma(curso_id: int):
    blocked = _forbid_institutional_write()
    if blocked:
        return blocked
    data = request.get_json(silent=True) or {}
    nome = str(data.get("nome") or "").strip()
    if not nome:
        return jsonify({"error": "Informe o nome da turma."}), 400
    turno = str(data.get("turno") or "").strip()[:40] or None
    try:
        with get_conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                curso = _get_curso_owned(cur, curso_id, _id_clie())
                if not curso:
                    return jsonify({"error": "Curso não encontrado."}), 404
                cur.execute(
                    """
                    INSERT INTO public.inove_turmas (curso_id, nome, turno)
                    VALUES (%s, %s, %s)
                    RETURNING *
                    """,
                    (curso_id, nome[:120], turno),
                )
                row = cur.fetchone()
                conn.commit()
        return jsonify({"turma": _jsonable(row)}), 201
    except pg_errors.UniqueViolation:
        return jsonify({"error": "Já existe uma turma com este nome neste curso."}), 409
    except pg_errors.UndefinedTable:
        return jsonify({
            "error": "Schema pendente. Aplique a migration 027.",
            "code": "schema_pending",
        }), 503
    except Exception as exc:
        print(f"[turmas] criar: {exc}")
        return jsonify({"error": "Falha ao criar turma."}), 500


@cursos_disciplinas_bp.put("/api/turmas/<int:turma_id>")
@require_session
def atualizar_turma(turma_id: int):
    blocked = _forbid_institutional_write()
    if blocked:
        return blocked
    data = request.get_json(silent=True) or {}
    try:
        with get_conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT t.*, c.id AS _curso_id
                      FROM public.inove_turmas t
                      JOIN public.inove_cursos c ON c.id = t.curso_id
                      JOIN public.inove_periodos_letivos p ON p.id = c.periodo_letivo_id
                      JOIN public.inove_instituicoes i ON i.id = p.instituicao_id
                     WHERE t.id = %s AND i.id_clie = %s AND t.ativo = TRUE
                       AND c.ativo = TRUE AND p.ativo = TRUE AND i.ativo = TRUE
                    """,
                    (turma_id, _id_clie()),
                )
                current = cur.fetchone()
                if not current:
                    return jsonify({"error": "Turma não encontrada."}), 404
                if current.get("origem_school") or current.get("school_turma_id"):
                    return jsonify({
                        "error": "Turma espelhada da escola — somente leitura.",
                        "code": "school_source_of_truth",
                    }), 403
                nome = str(data.get("nome", current["nome"]) or "").strip()
                if not nome:
                    return jsonify({"error": "Informe o nome da turma."}), 400
                if "turno" in data:
                    turno = str(data.get("turno") or "").strip()[:40] or None
                else:
                    turno = current.get("turno")
                cur.execute(
                    """
                    UPDATE public.inove_turmas
                       SET nome = %s,
                           turno = %s,
                           updated_at = CURRENT_TIMESTAMP
                     WHERE id = %s
                    RETURNING *
                    """,
                    (nome[:120], turno, turma_id),
                )
                row = cur.fetchone()
                conn.commit()
        return jsonify({"turma": _jsonable(row)})
    except pg_errors.UniqueViolation:
        return jsonify({"error": "Já existe uma turma com este nome neste curso."}), 409
    except pg_errors.UndefinedTable:
        return jsonify({"error": "Schema pendente.", "code": "schema_pending"}), 503
    except Exception as exc:
        print(f"[turmas] atualizar: {exc}")
        return jsonify({"error": "Falha ao atualizar turma."}), 500


@cursos_disciplinas_bp.delete("/api/turmas/<int:turma_id>")
@require_session
def soft_delete_turma(turma_id: int):
    blocked = _forbid_institutional_write()
    if blocked:
        return blocked
    try:
        with get_conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT t.id, t.origem_school, t.school_turma_id
                      FROM public.inove_turmas t
                      JOIN public.inove_cursos c ON c.id = t.curso_id
                      JOIN public.inove_periodos_letivos p ON p.id = c.periodo_letivo_id
                      JOIN public.inove_instituicoes i ON i.id = p.instituicao_id
                     WHERE t.id = %s AND i.id_clie = %s AND t.ativo = TRUE
                    """,
                    (turma_id, _id_clie()),
                )
                current = cur.fetchone()
                if not current:
                    return jsonify({"error": "Turma não encontrada."}), 404
                if current.get("origem_school") or current.get("school_turma_id"):
                    return jsonify({
                        "error": "Turma espelhada da escola — somente leitura.",
                        "code": "school_source_of_truth",
                    }), 403
                cur.execute(
                    """
                    UPDATE public.inove_turmas
                       SET ativo = FALSE, updated_at = CURRENT_TIMESTAMP
                     WHERE id = %s
                    RETURNING id
                    """,
                    (turma_id,),
                )
                conn.commit()
        return jsonify({"ok": True, "id": turma_id})
    except pg_errors.UndefinedTable:
        return jsonify({"error": "Schema pendente.", "code": "schema_pending"}), 503
    except Exception as exc:
        print(f"[turmas] delete: {exc}")
        return jsonify({"error": "Falha ao desativar turma."}), 500


@cursos_disciplinas_bp.get("/api/me/turmas")
@require_session
def listar_minhas_turmas():
    """Turmas ativas do professor (para selects ao registrar aula).

    Professor institucional: prioriza turmas das alocações School.
    """
    try:
        # Preferência institucional: alocações espelhadas
        if _is_institutional_session():
            try:
                from services.school_academic_mirror import list_alocacoes_escola

                alocs = list_alocacoes_escola(_id_clie())
                turmas_from_aloc = []
                seen = set()
                for a in alocs:
                    tid = a.get("turma_id")
                    nome = (a.get("turma_nome") or "").strip()
                    key = tid or nome
                    if not key or key in seen:
                        continue
                    seen.add(key)
                    turmas_from_aloc.append({
                        "id": tid,
                        "nome": nome or "Turma",
                        "turno": a.get("turma_turno"),
                        "curso_id": a.get("curso_id"),
                        "curso_nome": a.get("curso_nome"),
                        "periodo_letivo_id": a.get("periodo_id"),
                        "periodo_rotulo": a.get("periodo_nome"),
                        "instituicao_nome": a.get("instituicao_nome"),
                        "disciplina_id": a.get("disciplina_id"),
                        "disciplina_nome": a.get("disciplina_nome"),
                        "alocacao_escola_id": a.get("id"),
                        "origem_school": True,
                    })
                if turmas_from_aloc:
                    return jsonify({"turmas": turmas_from_aloc, "source": "alocacoes_escola"})
            except Exception as exc:
                print(f"[turmas] alocacoes_escola fallback: {exc}")

        with get_conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                escopo_t, params_t = _sql_escopo_turma("t")
                escopo_c, params_c = _sql_escopo_curso("c")
                cur.execute(
                    f"""
                    SELECT t.id,
                           t.nome,
                           t.turno,
                           t.curso_id,
                           c.nome AS curso_nome,
                           p.id AS periodo_letivo_id,
                           p.rotulo AS periodo_rotulo,
                           i.nome AS instituicao_nome
                      FROM public.inove_turmas t
                      JOIN public.inove_cursos c ON c.id = t.curso_id
                      JOIN public.inove_periodos_letivos p ON p.id = c.periodo_letivo_id
                      JOIN public.inove_instituicoes i ON i.id = p.instituicao_id
                     WHERE i.id_clie = %s
                       AND t.ativo = TRUE
                       AND c.ativo = TRUE
                       AND p.ativo = TRUE
                       AND i.ativo = TRUE
                       {escopo_t}
                       {escopo_c}
                     ORDER BY i.nome, p.ano_letivo DESC, c.nome, t.nome
                    """,
                    (_id_clie(), *params_t, *params_c),
                )
                rows = cur.fetchall() or []
        return jsonify({
            "turmas": [_jsonable(r) for r in rows],
            "source": "alocacoes_escola" if _is_institutional_session() else "professor",
        })
    except pg_errors.UndefinedTable:
        return jsonify({
            "error": "Schema pendente. Aplique a migration 027/029.",
            "code": "schema_pending",
            "turmas": [],
        }), 503
    except Exception as exc:
        print(f"[turmas] listar_minhas: {exc}")
        return jsonify({"error": "Falha ao listar turmas."}), 500

"""
Estruturação Pedagógica — Etapa 1/4: Instituição + Período Letivo.

Auth: sessão `inove4us_session` com `user.id_clie`.
Cadastro privado por professor (não compartilhado entre professores).
"""

from __future__ import annotations

import json
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from functools import wraps
from typing import Any

from flask import Blueprint, jsonify, request, session
from psycopg2 import errors as pg_errors
from psycopg2.extras import RealDictCursor

from db import get_conn

instituicoes_bp = Blueprint("instituicoes", __name__)

TIPOS_INSTITUICAO = frozenset(
    {
        "escola",
        "faculdade_universidade",
        "curso_tecnico",
        "curso_livre",
        "corporativo",
        "outro",
    }
)
REDES = frozenset({"publica", "privada", "nao_informado"})
TIPOS_PERIODO = frozenset({"anual", "semestral", "trimestral", "modular"})
STATUS_PERIODO = frozenset({"planejamento", "em_andamento", "encerrado"})
DIAS_SEMANA = frozenset({"seg", "ter", "qua", "qui", "sex", "sab", "dom"})


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
        elif isinstance(value, memoryview):
            out[key] = bytes(value).decode("utf-8", errors="replace")
        else:
            out[key] = value
    return out


def _parse_date(value: Any, field: str) -> date | None:
    if value in (None, ""):
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    text = str(value).strip()[:10]
    try:
        return date.fromisoformat(text)
    except ValueError as exc:
        raise ValueError(f"{field} inválida (use YYYY-MM-DD).") from exc


def _parse_dias(value: Any) -> list[str]:
    if value is None:
        return ["seg", "ter", "qua", "qui", "sex"]
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError as exc:
            raise ValueError("dias_semana_letivos inválido.") from exc
    if not isinstance(value, (list, tuple)):
        raise ValueError("dias_semana_letivos deve ser uma lista.")
    dias = [str(d).strip().lower()[:3] for d in value]
    if not dias:
        raise ValueError("Informe ao menos um dia letivo.")
    bad = [d for d in dias if d not in DIAS_SEMANA]
    if bad:
        raise ValueError(f"Dias inválidos: {', '.join(bad)}")
    return dias


def _get_instituicao(cur, instituicao_id: int, id_clie: int, *, include_inactive: bool = False):
    sql = """
        SELECT *
          FROM public.inove_instituicoes
         WHERE id = %s AND id_clie = %s
    """
    params: list[Any] = [instituicao_id, id_clie]
    if not include_inactive:
        sql += " AND ativo = TRUE"
    cur.execute(sql, params)
    return cur.fetchone()


def _get_periodo(cur, periodo_id: int, id_clie: int, *, include_inactive: bool = False):
    sql = """
        SELECT p.*, i.id_clie, i.nome AS instituicao_nome
          FROM public.inove_periodos_letivos p
          JOIN public.inove_instituicoes i ON i.id = p.instituicao_id
         WHERE p.id = %s AND i.id_clie = %s
    """
    params: list[Any] = [periodo_id, id_clie]
    if not include_inactive:
        sql += " AND p.ativo = TRUE AND i.ativo = TRUE"
    cur.execute(sql, params)
    return cur.fetchone()


# ---------------------------------------------------------------------------
# Instituições
# ---------------------------------------------------------------------------


@instituicoes_bp.post("/api/instituicoes")
@require_session
def criar_instituicao():
    data = request.get_json(silent=True) or {}
    nome = str(data.get("nome") or "").strip()
    tipo = str(data.get("tipo_instituicao") or "").strip().lower()
    if not nome:
        return jsonify({"error": "Informe o nome da instituição."}), 400
    if tipo not in TIPOS_INSTITUICAO:
        return jsonify({"error": "tipo_instituicao inválido."}), 400

    rede = str(data.get("rede") or "nao_informado").strip().lower()
    if rede not in REDES:
        return jsonify({"error": "rede inválida."}), 400

    payload = {
        "id_clie": _id_clie(),
        "nome": nome[:255],
        "tipo_instituicao": tipo,
        "segmento": (str(data.get("segmento") or "").strip() or None),
        "rede": rede,
        "cidade": (str(data.get("cidade") or "").strip() or None),
        "uf": (str(data.get("uf") or "").strip().upper()[:8] or None),
        "pais": (str(data.get("pais") or "BR").strip().upper()[:8] or "BR"),
        "observacoes": (str(data.get("observacoes") or "").strip() or None),
    }

    try:
        with get_conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    INSERT INTO public.inove_instituicoes (
                        id_clie, nome, tipo_instituicao, segmento, rede,
                        cidade, uf, pais, observacoes
                    ) VALUES (
                        %(id_clie)s, %(nome)s, %(tipo_instituicao)s, %(segmento)s, %(rede)s,
                        %(cidade)s, %(uf)s, %(pais)s, %(observacoes)s
                    )
                    RETURNING *
                    """,
                    payload,
                )
                row = cur.fetchone()
                conn.commit()
        return jsonify({"instituicao": _jsonable(row)}), 201
    except pg_errors.UndefinedTable:
        return jsonify({
            "error": "Schema pendente. Aplique a migration 008.",
            "code": "schema_pending",
        }), 503
    except Exception as exc:
        print(f"[instituicoes] criar: {exc}")
        return jsonify({"error": "Falha ao criar instituição."}), 500


@instituicoes_bp.get("/api/instituicoes")
@require_session
def listar_instituicoes():
    include_inactive = str(request.args.get("include_inactive") or "").lower() in (
        "1",
        "true",
        "yes",
    )
    try:
        with get_conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                sql = """
                    SELECT i.*,
                           (
                             SELECT COUNT(*)::int
                               FROM public.inove_periodos_letivos p
                              WHERE p.instituicao_id = i.id AND p.ativo = TRUE
                           ) AS periodos_count,
                           (
                             SELECT p.id
                               FROM public.inove_periodos_letivos p
                              WHERE p.instituicao_id = i.id
                                AND p.ativo = TRUE
                                AND p.em_curso = TRUE
                              LIMIT 1
                           ) AS periodo_em_curso_id
                      FROM public.inove_instituicoes i
                     WHERE i.id_clie = %s
                """
                if not include_inactive:
                    sql += " AND i.ativo = TRUE"
                sql += " ORDER BY i.nome ASC, i.id ASC"
                cur.execute(sql, (_id_clie(),))
                rows = cur.fetchall() or []
        return jsonify({"instituicoes": [_jsonable(r) for r in rows]})
    except pg_errors.UndefinedTable:
        return jsonify({
            "error": "Schema pendente. Aplique a migration 008.",
            "code": "schema_pending",
        }), 503
    except Exception as exc:
        print(f"[instituicoes] listar: {exc}")
        return jsonify({"error": "Falha ao listar instituições."}), 500


@instituicoes_bp.get("/api/instituicoes/<int:instituicao_id>")
@require_session
def detalhe_instituicao(instituicao_id: int):
    try:
        with get_conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                row = _get_instituicao(cur, instituicao_id, _id_clie())
                if not row:
                    return jsonify({"error": "Instituição não encontrada."}), 404
        return jsonify({"instituicao": _jsonable(row)})
    except pg_errors.UndefinedTable:
        return jsonify({"error": "Schema pendente.", "code": "schema_pending"}), 503


@instituicoes_bp.put("/api/instituicoes/<int:instituicao_id>")
@require_session
def atualizar_instituicao(instituicao_id: int):
    data = request.get_json(silent=True) or {}
    try:
        with get_conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                current = _get_instituicao(cur, instituicao_id, _id_clie())
                if not current:
                    return jsonify({"error": "Instituição não encontrada."}), 404

                nome = str(data.get("nome", current["nome"]) or "").strip()
                tipo = str(
                    data.get("tipo_instituicao", current["tipo_instituicao"]) or ""
                ).strip().lower()
                rede = str(data.get("rede", current["rede"]) or "nao_informado").strip().lower()
                if not nome:
                    return jsonify({"error": "Informe o nome da instituição."}), 400
                if tipo not in TIPOS_INSTITUICAO:
                    return jsonify({"error": "tipo_instituicao inválido."}), 400
                if rede not in REDES:
                    return jsonify({"error": "rede inválida."}), 400

                cur.execute(
                    """
                    UPDATE public.inove_instituicoes
                       SET nome = %s,
                           tipo_instituicao = %s,
                           segmento = %s,
                           rede = %s,
                           cidade = %s,
                           uf = %s,
                           pais = %s,
                           observacoes = %s,
                           updated_at = CURRENT_TIMESTAMP
                     WHERE id = %s AND id_clie = %s
                    RETURNING *
                    """,
                    (
                        nome[:255],
                        tipo,
                        (str(data.get("segmento", current.get("segmento") or "")).strip() or None),
                        rede,
                        (str(data.get("cidade", current.get("cidade") or "")).strip() or None),
                        (
                            str(data.get("uf", current.get("uf") or "")).strip().upper()[:8]
                            or None
                        ),
                        (
                            str(data.get("pais", current.get("pais") or "BR")).strip().upper()[:8]
                            or "BR"
                        ),
                        (
                            str(
                                data.get("observacoes", current.get("observacoes") or "")
                            ).strip()
                            or None
                        ),
                        instituicao_id,
                        _id_clie(),
                    ),
                )
                row = cur.fetchone()
                conn.commit()
        return jsonify({"instituicao": _jsonable(row)})
    except pg_errors.UndefinedTable:
        return jsonify({"error": "Schema pendente.", "code": "schema_pending"}), 503
    except Exception as exc:
        print(f"[instituicoes] atualizar: {exc}")
        return jsonify({"error": "Falha ao atualizar instituição."}), 500


@instituicoes_bp.delete("/api/instituicoes/<int:instituicao_id>")
@require_session
def soft_delete_instituicao(instituicao_id: int):
    try:
        with get_conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                current = _get_instituicao(cur, instituicao_id, _id_clie())
                if not current:
                    return jsonify({"error": "Instituição não encontrada."}), 404

                cur.execute(
                    """
                    SELECT COUNT(*)::int AS n
                      FROM public.inove_periodos_letivos
                     WHERE instituicao_id = %s
                       AND ativo = TRUE
                       AND status = 'em_andamento'
                    """,
                    (instituicao_id,),
                )
                n = int((cur.fetchone() or {}).get("n") or 0)
                if n > 0:
                    return jsonify({
                        "error": (
                            "Não é possível desativar: há período letivo em andamento. "
                            "Encerre ou desative o período antes."
                        ),
                        "code": "periodo_em_andamento",
                    }), 409

                cur.execute(
                    """
                    UPDATE public.inove_instituicoes
                       SET ativo = FALSE,
                           updated_at = CURRENT_TIMESTAMP
                     WHERE id = %s AND id_clie = %s
                    RETURNING id
                    """,
                    (instituicao_id, _id_clie()),
                )
                # Também desativa períodos e limpa em_curso
                cur.execute(
                    """
                    UPDATE public.inove_periodos_letivos
                       SET ativo = FALSE,
                           em_curso = FALSE,
                           updated_at = CURRENT_TIMESTAMP
                     WHERE instituicao_id = %s AND ativo = TRUE
                    """,
                    (instituicao_id,),
                )
                conn.commit()
        return jsonify({"ok": True, "id": instituicao_id})
    except pg_errors.UndefinedTable:
        return jsonify({"error": "Schema pendente.", "code": "schema_pending"}), 503
    except Exception as exc:
        print(f"[instituicoes] delete: {exc}")
        return jsonify({"error": "Falha ao desativar instituição."}), 500


# ---------------------------------------------------------------------------
# Períodos letivos
# ---------------------------------------------------------------------------


def _periodo_payload_from_body(data: dict, *, partial: bool = False, current: dict | None = None) -> dict:
    current = current or {}
    rotulo = str(data.get("rotulo", current.get("rotulo") or "")).strip()
    if not rotulo and not partial:
        raise ValueError("Informe o rótulo do período (ex.: Ano Letivo 2026).")

    ano_raw = data.get("ano_letivo", current.get("ano_letivo"))
    try:
        ano_letivo = int(ano_raw)
    except (TypeError, ValueError) as exc:
        raise ValueError("ano_letivo inválido.") from exc
    if ano_letivo < 1990 or ano_letivo > 2100:
        raise ValueError("ano_letivo fora da faixa permitida.")

    tipo = str(data.get("tipo_periodo", current.get("tipo_periodo") or "")).strip().lower()
    if tipo not in TIPOS_PERIODO:
        raise ValueError("tipo_periodo inválido.")

    status = str(data.get("status", current.get("status") or "planejamento")).strip().lower()
    if status not in STATUS_PERIODO:
        raise ValueError("status inválido.")

    data_inicio = _parse_date(data.get("data_inicio", current.get("data_inicio")), "data_inicio")
    data_fim = _parse_date(data.get("data_fim", current.get("data_fim")), "data_fim")
    if not data_inicio or not data_fim:
        raise ValueError("data_inicio e data_fim são obrigatórias.")
    if data_fim <= data_inicio:
        raise ValueError("data_fim deve ser posterior a data_inicio.")

    carga = data.get("carga_horaria_total_horas", current.get("carga_horaria_total_horas"))
    carga_val = None
    if carga not in (None, ""):
        try:
            carga_val = Decimal(str(carga))
            if carga_val < 0:
                raise ValueError("carga_horaria_total_horas inválida.")
        except (InvalidOperation, ValueError) as exc:
            raise ValueError("carga_horaria_total_horas inválida.") from exc

    dur_raw = data.get(
        "duracao_padrao_aula_min",
        current.get("duracao_padrao_aula_min", 50),
    )
    try:
        duracao = int(dur_raw)
    except (TypeError, ValueError) as exc:
        raise ValueError("duracao_padrao_aula_min inválida.") from exc
    if duracao < 5 or duracao > 480:
        raise ValueError("duracao_padrao_aula_min deve estar entre 5 e 480.")

    dias = _parse_dias(
        data.get("dias_semana_letivos", current.get("dias_semana_letivos"))
    )
    etapa = str(data.get("etapa", current.get("etapa") or "")).strip() or None
    if tipo == "anual":
        etapa = None

    em_curso = data.get("em_curso", current.get("em_curso", False))
    if isinstance(em_curso, str):
        em_curso = em_curso.strip().lower() in ("1", "true", "yes", "sim")
    else:
        em_curso = bool(em_curso)

    return {
        "rotulo": (rotulo or current.get("rotulo") or "")[:160],
        "ano_letivo": ano_letivo,
        "tipo_periodo": tipo,
        "etapa": (etapa[:80] if etapa else None),
        "data_inicio": data_inicio,
        "data_fim": data_fim,
        "carga_horaria_total_horas": carga_val,
        "duracao_padrao_aula_min": duracao,
        "dias_semana_letivos": json.dumps(dias),
        "status": status,
        "em_curso": em_curso,
    }


@instituicoes_bp.post("/api/instituicoes/<int:instituicao_id>/periodos-letivos")
@require_session
def criar_periodo(instituicao_id: int):
    data = request.get_json(silent=True) or {}
    try:
        payload = _periodo_payload_from_body(data)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    try:
        with get_conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                inst = _get_instituicao(cur, instituicao_id, _id_clie())
                if not inst:
                    return jsonify({"error": "Instituição não encontrada."}), 404

                if payload["em_curso"]:
                    cur.execute(
                        """
                        UPDATE public.inove_periodos_letivos
                           SET em_curso = FALSE,
                               updated_at = CURRENT_TIMESTAMP
                         WHERE instituicao_id = %s AND em_curso = TRUE AND ativo = TRUE
                        """,
                        (instituicao_id,),
                    )

                cur.execute(
                    """
                    INSERT INTO public.inove_periodos_letivos (
                        instituicao_id, rotulo, ano_letivo, tipo_periodo, etapa,
                        data_inicio, data_fim, carga_horaria_total_horas,
                        duracao_padrao_aula_min, dias_semana_letivos, status, em_curso
                    ) VALUES (
                        %s, %s, %s, %s, %s,
                        %s, %s, %s,
                        %s, %s::jsonb, %s, %s
                    )
                    RETURNING *
                    """,
                    (
                        instituicao_id,
                        payload["rotulo"],
                        payload["ano_letivo"],
                        payload["tipo_periodo"],
                        payload["etapa"],
                        payload["data_inicio"],
                        payload["data_fim"],
                        payload["carga_horaria_total_horas"],
                        payload["duracao_padrao_aula_min"],
                        payload["dias_semana_letivos"],
                        payload["status"],
                        payload["em_curso"],
                    ),
                )
                row = cur.fetchone()
                conn.commit()
        return jsonify({"periodo": _jsonable(row)}), 201
    except pg_errors.UniqueViolation:
        return jsonify({
            "error": "Já existe um período marcado como em curso nesta instituição.",
            "code": "em_curso_duplicado",
        }), 409
    except pg_errors.UndefinedTable:
        return jsonify({"error": "Schema pendente.", "code": "schema_pending"}), 503
    except Exception as exc:
        print(f"[periodos] criar: {exc}")
        return jsonify({"error": "Falha ao criar período letivo."}), 500


@instituicoes_bp.get("/api/instituicoes/<int:instituicao_id>/periodos-letivos")
@require_session
def listar_periodos(instituicao_id: int):
    try:
        with get_conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                inst = _get_instituicao(cur, instituicao_id, _id_clie())
                if not inst:
                    return jsonify({"error": "Instituição não encontrada."}), 404
                cur.execute(
                    """
                    SELECT *
                      FROM public.inove_periodos_letivos
                     WHERE instituicao_id = %s AND ativo = TRUE
                     ORDER BY em_curso DESC, ano_letivo DESC, data_inicio DESC, id DESC
                    """,
                    (instituicao_id,),
                )
                rows = cur.fetchall() or []
        return jsonify({
            "instituicao_id": instituicao_id,
            "periodos": [_jsonable(r) for r in rows],
        })
    except pg_errors.UndefinedTable:
        return jsonify({"error": "Schema pendente.", "code": "schema_pending"}), 503


@instituicoes_bp.get("/api/periodos-letivos/<int:periodo_id>")
@require_session
def detalhe_periodo(periodo_id: int):
    try:
        with get_conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                row = _get_periodo(cur, periodo_id, _id_clie())
                if not row:
                    return jsonify({"error": "Período letivo não encontrado."}), 404
        return jsonify({"periodo": _jsonable(row)})
    except pg_errors.UndefinedTable:
        return jsonify({"error": "Schema pendente.", "code": "schema_pending"}), 503


@instituicoes_bp.put("/api/periodos-letivos/<int:periodo_id>")
@require_session
def atualizar_periodo(periodo_id: int):
    data = request.get_json(silent=True) or {}
    try:
        with get_conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                current = _get_periodo(cur, periodo_id, _id_clie())
                if not current:
                    return jsonify({"error": "Período letivo não encontrado."}), 404
                try:
                    payload = _periodo_payload_from_body(data, partial=True, current=current)
                except ValueError as exc:
                    return jsonify({"error": str(exc)}), 400

                if payload["em_curso"]:
                    cur.execute(
                        """
                        UPDATE public.inove_periodos_letivos
                           SET em_curso = FALSE,
                               updated_at = CURRENT_TIMESTAMP
                         WHERE instituicao_id = %s
                           AND id <> %s
                           AND em_curso = TRUE
                           AND ativo = TRUE
                        """,
                        (current["instituicao_id"], periodo_id),
                    )

                cur.execute(
                    """
                    UPDATE public.inove_periodos_letivos
                       SET rotulo = %s,
                           ano_letivo = %s,
                           tipo_periodo = %s,
                           etapa = %s,
                           data_inicio = %s,
                           data_fim = %s,
                           carga_horaria_total_horas = %s,
                           duracao_padrao_aula_min = %s,
                           dias_semana_letivos = %s::jsonb,
                           status = %s,
                           em_curso = %s,
                           updated_at = CURRENT_TIMESTAMP
                     WHERE id = %s
                    RETURNING *
                    """,
                    (
                        payload["rotulo"],
                        payload["ano_letivo"],
                        payload["tipo_periodo"],
                        payload["etapa"],
                        payload["data_inicio"],
                        payload["data_fim"],
                        payload["carga_horaria_total_horas"],
                        payload["duracao_padrao_aula_min"],
                        payload["dias_semana_letivos"],
                        payload["status"],
                        payload["em_curso"],
                        periodo_id,
                    ),
                )
                row = cur.fetchone()
                conn.commit()
        return jsonify({"periodo": _jsonable(row)})
    except pg_errors.UniqueViolation:
        return jsonify({
            "error": "Já existe um período marcado como em curso nesta instituição.",
            "code": "em_curso_duplicado",
        }), 409
    except pg_errors.UndefinedTable:
        return jsonify({"error": "Schema pendente.", "code": "schema_pending"}), 503
    except Exception as exc:
        print(f"[periodos] atualizar: {exc}")
        return jsonify({"error": "Falha ao atualizar período letivo."}), 500


@instituicoes_bp.delete("/api/periodos-letivos/<int:periodo_id>")
@require_session
def soft_delete_periodo(periodo_id: int):
    try:
        with get_conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                current = _get_periodo(cur, periodo_id, _id_clie())
                if not current:
                    return jsonify({"error": "Período letivo não encontrado."}), 404
                if current.get("status") == "em_andamento" and current.get("em_curso"):
                    return jsonify({
                        "error": (
                            "Não é possível desativar o período em curso enquanto "
                            "o status for em_andamento. Encerre ou altere o status antes."
                        ),
                        "code": "periodo_em_andamento",
                    }), 409
                cur.execute(
                    """
                    UPDATE public.inove_periodos_letivos
                       SET ativo = FALSE,
                           em_curso = FALSE,
                           updated_at = CURRENT_TIMESTAMP
                     WHERE id = %s
                    RETURNING id
                    """,
                    (periodo_id,),
                )
                conn.commit()
        return jsonify({"ok": True, "id": periodo_id})
    except pg_errors.UndefinedTable:
        return jsonify({"error": "Schema pendente.", "code": "schema_pending"}), 503
    except Exception as exc:
        print(f"[periodos] delete: {exc}")
        return jsonify({"error": "Falha ao desativar período letivo."}), 500


@instituicoes_bp.post("/api/periodos-letivos/<int:periodo_id>/marcar-em-curso")
@require_session
def marcar_em_curso(periodo_id: int):
    try:
        with get_conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                current = _get_periodo(cur, periodo_id, _id_clie())
                if not current:
                    return jsonify({"error": "Período letivo não encontrado."}), 404

                cur.execute(
                    """
                    UPDATE public.inove_periodos_letivos
                       SET em_curso = FALSE,
                           updated_at = CURRENT_TIMESTAMP
                     WHERE instituicao_id = %s
                       AND em_curso = TRUE
                       AND ativo = TRUE
                       AND id <> %s
                    """,
                    (current["instituicao_id"], periodo_id),
                )
                # Se ainda em planejamento, sobe para em_andamento ao marcar como atual.
                new_status = current.get("status")
                if new_status == "planejamento":
                    new_status = "em_andamento"

                cur.execute(
                    """
                    UPDATE public.inove_periodos_letivos
                       SET em_curso = TRUE,
                           status = %s,
                           updated_at = CURRENT_TIMESTAMP
                     WHERE id = %s
                    RETURNING *
                    """,
                    (new_status, periodo_id),
                )
                row = cur.fetchone()
                conn.commit()
        return jsonify({"periodo": _jsonable(row), "ok": True})
    except pg_errors.UniqueViolation:
        return jsonify({
            "error": "Conflito ao marcar período em curso.",
            "code": "em_curso_duplicado",
        }), 409
    except pg_errors.UndefinedTable:
        return jsonify({"error": "Schema pendente.", "code": "schema_pending"}), 503
    except Exception as exc:
        print(f"[periodos] marcar-em-curso: {exc}")
        return jsonify({"error": "Falha ao marcar período em curso."}), 500

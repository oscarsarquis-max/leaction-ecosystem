"""Dashboard — calendário pedagógico consolidado.

Fonte: school_planos_aula_espelhados (espelho local). Sem sync B2C ainda.
Auth interina: instituicao_id / unidade_id na URL.
"""
from __future__ import annotations

import calendar
import uuid
from datetime import date, datetime, timedelta
from typing import Any

from flask import Blueprint, jsonify, request
from psycopg2.extras import RealDictCursor

from db import get_conn

bp = Blueprint("dashboard", __name__)

_PLANOS_SELECT = """
SELECT
    p.id,
    p.turma_id,
    t.nome AS turma_nome,
    t.unidade_id,
    u.nome AS unidade_nome,
    p.professor_vinculo_id,
    v.email_convite AS professor_email,
    m.nome AS metodologia_nome,
    p.tipo_aula,
    p.semana_referencia,
    p.status,
    p.conteudo_resumo,
    p.desafio_grupo_id,
    p.desafio_titulo,
    p.desafio_sequencia,
    p.mesa_payload_json,
    p.updated_at,
    EXISTS (
        SELECT 1
        FROM public.school_curadoria_metodologias c
        WHERE c.plano_espelhado_id = p.id
    ) AS has_curadoria_row,
    COALESCE(
        NULLIF(trim(p.mesa_payload_json->>'texto_sugestao'), ''),
        NULLIF(trim(p.mesa_payload_json->>'teacher_adaptation_text'), '')
    ) AS texto_sugestao
FROM public.school_planos_aula_espelhados p
JOIN public.school_turmas t
    ON t.id = p.turma_id
JOIN public.school_unidades u
    ON u.id = t.unidade_id
JOIN public.school_metodologias_catalogo m
    ON m.id = p.metodologia_catalogo_id
LEFT JOIN public.school_professores_vinculo v
    ON v.id = p.professor_vinculo_id
"""


def _parse_uuid(value: str, label: str):
    try:
        return uuid.UUID(str(value))
    except (ValueError, TypeError, AttributeError):
        return jsonify({"error": f"Identificador de {label} inválido"}), 400


def _parse_date(raw: str | None, label: str):
    if not raw:
        return None
    try:
        return date.fromisoformat(str(raw)[:10])
    except ValueError:
        return jsonify({"error": f"Data inválida em {label} (use AAAA-MM-DD)"}), 400


def _periodo_padrao() -> tuple[date, date]:
    hoje = date.today()
    inicio = date(hoje.year, hoje.month, 1)
    ultimo = calendar.monthrange(hoje.year, hoje.month)[1]
    fim = date(hoje.year, hoje.month, ultimo)
    return inicio, fim


def _resolver_periodo():
    di = _parse_date(request.args.get("data_inicio"), "data_inicio")
    if isinstance(di, tuple):
        return di
    df = _parse_date(request.args.get("data_fim"), "data_fim")
    if isinstance(df, tuple):
        return df
    if di is None and df is None:
        return _periodo_padrao()
    if di is None or df is None:
        return jsonify(
            {"error": "Informe data_inicio e data_fim juntos, ou nenhum dos dois"}
        ), 400
    if di > df:
        return jsonify({"error": "data_inicio não pode ser depois de data_fim"}), 400
    return di, df


def _unidade_exists(cur: Any, unidade_id: uuid.UUID) -> dict[str, Any] | None:
    cur.execute(
        """
        SELECT id, instituicao_id, nome, ativo
        FROM public.school_unidades
        WHERE id = %s
        """,
        (str(unidade_id),),
    )
    return cur.fetchone()


def _instituicao_exists(cur: Any, instituicao_id: uuid.UUID) -> bool:
    cur.execute(
        "SELECT 1 FROM public.school_instituicoes WHERE id = %s",
        (str(instituicao_id),),
    )
    return cur.fetchone() is not None


def _fmt_date(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, (date, datetime)):
        return value.isoformat()[:10]
    return str(value)


def _as_mesa(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str) and value.strip():
        try:
            import json

            parsed = json.loads(value)
            return parsed if isinstance(parsed, dict) else {}
        except Exception:
            return {}
    return {}


def _execucao_status(r: dict[str, Any]) -> str:
    """Classifica espelho: em_andamento | concluida (para Radar)."""
    mesa = _as_mesa(r.get("mesa_payload_json"))
    mesa_st = str(mesa.get("status") or "").strip().lower()
    if mesa_st in ("concluido", "concluído", "done", "finalizado"):
        return "concluida"
    if mesa_st in ("em_execucao", "em_andamento", "fazendo", "executando"):
        return "em_andamento"
    if str(r.get("status") or "").strip().lower() == "aprovado":
        return "concluida"
    return "em_andamento"


def _has_sugestao_curadoria(r: dict[str, Any]) -> bool:
    if r.get("has_curadoria_row"):
        return True
    if str(r.get("texto_sugestao") or "").strip():
        return True
    mesa = _as_mesa(r.get("mesa_payload_json"))
    if str(mesa.get("texto_sugestao") or mesa.get("teacher_adaptation_text") or "").strip():
        return True
    return bool(mesa.get("has_teacher_adaptations"))


def _diario_bordo(mesa: dict[str, Any]) -> list[dict[str, Any]]:
    """Extrai anotações de transição (historico) dos cards da mesa."""
    entries: list[dict[str, Any]] = []
    raw: Any = mesa.get("cards") or mesa.get("kanban_cards") or mesa.get("tarefas")
    if not raw:
        ks = mesa.get("kanban_state")
        if isinstance(ks, dict):
            raw = ks.get("tarefas")
        elif isinstance(ks, list):
            raw = ks
    cards = raw if isinstance(raw, list) else []
    for card in cards:
        if not isinstance(card, dict):
            continue
        titulo = str(card.get("titulo") or card.get("titulo_do_card") or "Card").strip()
        hist = card.get("historico")
        if isinstance(hist, list):
            for h in hist:
                if not isinstance(h, dict):
                    continue
                nota = str(h.get("nota") or "").strip()
                if not nota:
                    continue
                entries.append(
                    {
                        "card": titulo,
                        "de": h.get("de"),
                        "para": h.get("para"),
                        "nota": nota,
                        "em": h.get("em"),
                    }
                )
        obs = str(card.get("ultima_observacao") or "").strip()
        if obs and not any(e["nota"] == obs and e["card"] == titulo for e in entries):
            entries.append(
                {
                    "card": titulo,
                    "de": None,
                    "para": card.get("coluna"),
                    "nota": obs,
                    "em": None,
                }
            )
    return entries


def _plano_row(r: dict[str, Any]) -> dict[str, Any]:
    mesa = _as_mesa(r.get("mesa_payload_json"))
    sugestao = str(
        r.get("texto_sugestao")
        or mesa.get("texto_sugestao")
        or mesa.get("teacher_adaptation_text")
        or ""
    ).strip() or None
    return {
        "id": str(r["id"]),
        "turma_id": str(r["turma_id"]),
        "turma_nome": r["turma_nome"],
        "unidade_id": str(r["unidade_id"]),
        "unidade_nome": r["unidade_nome"],
        "professor_vinculo_id": str(r["professor_vinculo_id"]),
        "professor_email": r.get("professor_email"),
        "metodologia_nome": r["metodologia_nome"],
        "tipo_aula": r["tipo_aula"],
        "semana_referencia": _fmt_date(r["semana_referencia"]),
        "status": r["status"],
        "execucao_status": _execucao_status(r),
        "conteudo_resumo": r.get("conteudo_resumo"),
        "desafio_grupo_id": str(r["desafio_grupo_id"]) if r.get("desafio_grupo_id") else None,
        "desafio_titulo": r.get("desafio_titulo"),
        "desafio_sequencia": r.get("desafio_sequencia"),
        "has_sugestao_curadoria": _has_sugestao_curadoria(r),
        "texto_sugestao": sugestao,
        "updated_at": r["updated_at"].isoformat() if r.get("updated_at") else None,
        "aula_titulo": mesa.get("titulo") or r.get("conteudo_resumo"),
    }


def _resumo_payload(row: dict[str, Any], data_inicio: date, data_fim: date) -> dict[str, Any]:
    return {
        "total": int(row.get("total") or 0),
        "por_tipo_aula": {
            "dia_a_dia": int(row.get("dia_a_dia") or 0),
            "desafio": int(row.get("desafio") or 0),
        },
        "por_status": {
            "pendente": int(row.get("pendente") or 0),
            "aprovado": int(row.get("aprovado") or 0),
            "reprovado": int(row.get("reprovado") or 0),
        },
        "professores_ativos": int(row.get("professores_ativos") or 0),
        "data_inicio": data_inicio.isoformat(),
        "data_fim": data_fim.isoformat(),
    }


_RESUMO_SELECT = """
SELECT
    COUNT(*)::int AS total,
    COUNT(*) FILTER (WHERE p.tipo_aula = 'dia_a_dia')::int AS dia_a_dia,
    COUNT(*) FILTER (WHERE p.tipo_aula = 'desafio')::int AS desafio,
    COUNT(*) FILTER (WHERE p.status = 'pendente')::int AS pendente,
    COUNT(*) FILTER (WHERE p.status = 'aprovado')::int AS aprovado,
    COUNT(*) FILTER (WHERE p.status = 'reprovado')::int AS reprovado,
    COUNT(DISTINCT p.professor_vinculo_id)::int AS professores_ativos
FROM public.school_planos_aula_espelhados p
JOIN public.school_turmas t ON t.id = p.turma_id
JOIN public.school_unidades u ON u.id = t.unidade_id
"""


@bp.get("/api/instituicoes/<instituicao_id>/unidades")
def list_unidades(instituicao_id: str):
    parsed = _parse_uuid(instituicao_id, "instituição")
    if not isinstance(parsed, uuid.UUID):
        return parsed

    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            if not _instituicao_exists(cur, parsed):
                return jsonify({"error": "Instituição não encontrada"}), 404
            cur.execute(
                """
                SELECT id, nome, codigo, cidade, uf
                FROM public.school_unidades
                WHERE instituicao_id = %s AND ativo = TRUE
                ORDER BY nome
                """,
                (str(parsed),),
            )
            rows = cur.fetchall()

    return jsonify(
        [
            {
                "id": str(r["id"]),
                "nome": r["nome"],
                "codigo": r.get("codigo"),
                "cidade": r.get("cidade"),
                "uf": r.get("uf"),
            }
            for r in rows
        ]
    )


@bp.get("/api/unidades/<unidade_id>/calendario-pedagogico")
def calendario_pedagogico(unidade_id: str):
    parsed = _parse_uuid(unidade_id, "unidade")
    if not isinstance(parsed, uuid.UUID):
        return parsed
    periodo = _resolver_periodo()
    if not isinstance(periodo, tuple) or not isinstance(periodo[0], date):
        return periodo
    data_inicio, data_fim = periodo

    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            unidade = _unidade_exists(cur, parsed)
            if not unidade or not unidade["ativo"]:
                return jsonify({"error": "Unidade não encontrada"}), 404
            cur.execute(
                _PLANOS_SELECT
                + """
                WHERE t.unidade_id = %s
                  AND p.semana_referencia >= %s
                  AND p.semana_referencia <= %s
                ORDER BY p.semana_referencia, t.nome, m.nome
                """,
                (str(parsed), data_inicio, data_fim),
            )
            rows = cur.fetchall()

    return jsonify([_plano_row(r) for r in rows])


@bp.get("/api/unidades/<unidade_id>/calendario-pedagogico/resumo")
def calendario_pedagogico_resumo(unidade_id: str):
    parsed = _parse_uuid(unidade_id, "unidade")
    if not isinstance(parsed, uuid.UUID):
        return parsed
    periodo = _resolver_periodo()
    if not isinstance(periodo, tuple) or not isinstance(periodo[0], date):
        return periodo
    data_inicio, data_fim = periodo

    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            unidade = _unidade_exists(cur, parsed)
            if not unidade or not unidade["ativo"]:
                return jsonify({"error": "Unidade não encontrada"}), 404
            cur.execute(
                _RESUMO_SELECT
                + """
                WHERE t.unidade_id = %s
                  AND p.semana_referencia >= %s
                  AND p.semana_referencia <= %s
                """,
                (str(parsed), data_inicio, data_fim),
            )
            row = cur.fetchone() or {}

    return jsonify(_resumo_payload(row, data_inicio, data_fim))


@bp.get("/api/instituicoes/<instituicao_id>/calendario-pedagogico")
def calendario_instituicao(instituicao_id: str):
    parsed = _parse_uuid(instituicao_id, "instituição")
    if not isinstance(parsed, uuid.UUID):
        return parsed
    periodo = _resolver_periodo()
    if not isinstance(periodo, tuple) or not isinstance(periodo[0], date):
        return periodo
    data_inicio, data_fim = periodo

    unidade_raw = (request.args.get("unidade_id") or "").strip()
    unidade_id = None
    if unidade_raw:
        unidade_id = _parse_uuid(unidade_raw, "unidade")
        if not isinstance(unidade_id, uuid.UUID):
            return unidade_id

    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            if not _instituicao_exists(cur, parsed):
                return jsonify({"error": "Instituição não encontrada"}), 404

            if unidade_id is not None:
                unidade = _unidade_exists(cur, unidade_id)
                if (
                    not unidade
                    or not unidade["ativo"]
                    or str(unidade["instituicao_id"]) != str(parsed)
                ):
                    return jsonify({"error": "Unidade não encontrada"}), 404
                cur.execute(
                    _PLANOS_SELECT
                    + """
                    WHERE t.unidade_id = %s
                      AND p.semana_referencia >= %s
                      AND p.semana_referencia <= %s
                    ORDER BY p.semana_referencia, t.nome, m.nome
                    """,
                    (str(unidade_id), data_inicio, data_fim),
                )
            else:
                cur.execute(
                    _PLANOS_SELECT
                    + """
                    WHERE u.instituicao_id = %s
                      AND u.ativo = TRUE
                      AND p.semana_referencia >= %s
                      AND p.semana_referencia <= %s
                    ORDER BY u.nome, p.semana_referencia, t.nome, m.nome
                    """,
                    (str(parsed), data_inicio, data_fim),
                )
            rows = cur.fetchall()

    return jsonify([_plano_row(r) for r in rows])


@bp.get("/api/instituicoes/<instituicao_id>/calendario-pedagogico/resumo")
def calendario_instituicao_resumo(instituicao_id: str):
    parsed = _parse_uuid(instituicao_id, "instituição")
    if not isinstance(parsed, uuid.UUID):
        return parsed
    periodo = _resolver_periodo()
    if not isinstance(periodo, tuple) or not isinstance(periodo[0], date):
        return periodo
    data_inicio, data_fim = periodo

    unidade_raw = (request.args.get("unidade_id") or "").strip()
    unidade_id = None
    if unidade_raw:
        unidade_id = _parse_uuid(unidade_raw, "unidade")
        if not isinstance(unidade_id, uuid.UUID):
            return unidade_id

    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            if not _instituicao_exists(cur, parsed):
                return jsonify({"error": "Instituição não encontrada"}), 404

            if unidade_id is not None:
                unidade = _unidade_exists(cur, unidade_id)
                if (
                    not unidade
                    or not unidade["ativo"]
                    or str(unidade["instituicao_id"]) != str(parsed)
                ):
                    return jsonify({"error": "Unidade não encontrada"}), 404
                cur.execute(
                    _RESUMO_SELECT
                    + """
                    WHERE t.unidade_id = %s
                      AND p.semana_referencia >= %s
                      AND p.semana_referencia <= %s
                    """,
                    (str(unidade_id), data_inicio, data_fim),
                )
            else:
                cur.execute(
                    _RESUMO_SELECT
                    + """
                    WHERE u.instituicao_id = %s
                      AND u.ativo = TRUE
                      AND p.semana_referencia >= %s
                      AND p.semana_referencia <= %s
                    """,
                    (str(parsed), data_inicio, data_fim),
                )
            row = cur.fetchone() or {}

    return jsonify(_resumo_payload(row, data_inicio, data_fim))


@bp.get("/api/instituicoes/<instituicao_id>/planos-espelhados/<plano_id>")
def plano_espelhado_detail(instituicao_id: str, plano_id: str):
    """Detalhe do espelho: mesa completa + diário de bordo + flag de curadoria."""
    inst = _parse_uuid(instituicao_id, "instituição")
    if not isinstance(inst, uuid.UUID):
        return inst
    pid = _parse_uuid(plano_id, "plano")
    if not isinstance(pid, uuid.UUID):
        return pid

    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            if not _instituicao_exists(cur, inst):
                return jsonify({"error": "Instituição não encontrada"}), 404
            cur.execute(
                _PLANOS_SELECT
                + """
                WHERE p.id = %s AND u.instituicao_id = %s
                LIMIT 1
                """,
                (str(pid), str(inst)),
            )
            row = cur.fetchone()
            if not row:
                return jsonify({"error": "Plano espelhado não encontrado"}), 404

            avisos: list[dict[str, Any]] = []
            try:
                cur.execute(
                    """
                    SELECT a.id, a.texto, t.nome AS turma_nome, d.nome AS disciplina_nome
                    FROM public.school_avisos_mesa a
                    LEFT JOIN public.school_turmas t ON t.id = a.turma_id
                    LEFT JOIN public.school_disciplinas d ON d.id = a.disciplina_id
                    WHERE a.instituicao_id = %s AND a.ativo = TRUE
                      AND (
                        a.turma_id IS NULL
                        OR a.turma_id = %s
                      )
                    ORDER BY a.created_at DESC
                    LIMIT 20
                    """,
                    (str(inst), str(row["turma_id"])),
                )
                avisos = [
                    {
                        "id": str(a["id"]),
                        "texto": a["texto"],
                        "turma_nome": a.get("turma_nome"),
                        "disciplina_nome": a.get("disciplina_nome"),
                    }
                    for a in cur.fetchall()
                ]
            except Exception:
                avisos = []

    mesa = _as_mesa(row.get("mesa_payload_json"))
    base = _plano_row(row)
    return jsonify(
        {
            **base,
            "mesa": mesa,
            "diario_bordo": _diario_bordo(mesa),
            "relato_sala": mesa.get("relato_sala"),
            "participantes": mesa.get("participantes"),
            "avisos_fixados": avisos,
        }
    )


# ---------------------------------------------------------------------------
# Passo 0 (confirmado no DB):
# - school_curadoria_metodologias.status_analise:
#     pendente | em_analise | incorporada | incorporado | rejeitada | mantido_apenas_na_aula
# - school_curadoria_pei.status_analise:
#     pendente | incorporado | rejeitado | rejeitada | mantido_apenas_na_aula
# - Filtro de fila: status_analise = 'pendente' (2 queries somadas).
# - school_avisos_mesa: turma_id / disciplina_id NULL = todos; preenchidos = vínculo.
# - school_professores_vinculo: coluna status_vinculo (= 'ativo'), não "status".
# ---------------------------------------------------------------------------


@bp.get("/api/instituicoes/<instituicao_id>/resumo-consolidado")
def resumo_consolidado(instituicao_id: str):
    """Visão consolidada do Radar — contadores dos módulos da Torre."""
    parsed = _parse_uuid(instituicao_id, "instituição")
    if not isinstance(parsed, uuid.UUID):
        return parsed

    hoje = date.today()
    inicio_semana = hoje - timedelta(days=hoje.weekday())
    fim_semana = inicio_semana + timedelta(days=6)
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            if not _instituicao_exists(cur, parsed):
                return jsonify({"error": "Instituição não encontrada"}), 404

            cur.execute(
                """
                SELECT COUNT(*)::int AS n
                FROM public.school_unidades
                WHERE instituicao_id = %s AND ativo = TRUE
                """,
                (str(parsed),),
            )
            unidades = int((cur.fetchone() or {}).get("n") or 0)

            cur.execute(
                """
                SELECT COUNT(*)::int AS n
                FROM public.school_turmas t
                JOIN public.school_unidades u ON u.id = t.unidade_id
                WHERE u.instituicao_id = %s AND t.ativa = TRUE
                """,
                (str(parsed),),
            )
            turmas_ativas = int((cur.fetchone() or {}).get("n") or 0)

            cur.execute(
                """
                SELECT COUNT(*)::int AS n
                FROM public.school_professores_vinculo
                WHERE instituicao_id = %s AND status_vinculo = 'ativo'
                """,
                (str(parsed),),
            )
            professores_ativos = int((cur.fetchone() or {}).get("n") or 0)

            cur.execute(
                """
                SELECT COUNT(*)::int AS n
                FROM public.school_comunicacoes_eventos
                WHERE instituicao_id = %s
                  AND status <> 'cancelado'
                  AND (data_hora_inicio::date) >= %s
                  AND (data_hora_inicio::date) <= %s
                """,
                (str(parsed), inicio_semana, fim_semana),
            )
            eventos_semana = int((cur.fetchone() or {}).get("n") or 0)

            # Mesma lógica de merge do endpoint de metodologias (catálogo + org).
            cur.execute(
                """
                SELECT COUNT(*)::int AS n
                FROM public.school_metodologias_catalogo c
                LEFT JOIN public.school_metodologias_org org
                    ON org.metodologia_id_canonica = c.id
                   AND org.instituicao_id = %s
                WHERE c.ativo = TRUE
                  AND (
                        c.origem = 'padrao'
                        OR (c.origem = 'escola' AND c.instituicao_origem_id = %s)
                      )
                  AND COALESCE(org.is_active, TRUE) = TRUE
                """,
                (str(parsed), str(parsed)),
            )
            metodologias_ativas = int((cur.fetchone() or {}).get("n") or 0)

            cur.execute(
                """
                SELECT COUNT(*)::int AS n
                FROM public.school_pei_diretriz_base
                WHERE instituicao_id = %s AND ativo = TRUE
                """,
                (str(parsed),),
            )
            planos_pei = int((cur.fetchone() or {}).get("n") or 0)

    return jsonify(
        {
            "unidades": unidades,
            "turmas_ativas": turmas_ativas,
            "professores_ativos": professores_ativos,
            "eventos_semana": eventos_semana,
            "metodologias_ativas": metodologias_ativas,
            "planos_pei": planos_pei,
        }
    )


@bp.get("/api/instituicoes/<instituicao_id>/curadoria-pendente")
def curadoria_pendente(instituicao_id: str):
    """Fila unificada: curadoria metodologia + PEI com status_analise = pendente."""
    parsed = _parse_uuid(instituicao_id, "instituição")
    if not isinstance(parsed, uuid.UUID):
        return parsed

    unidade_raw = (request.args.get("unidade_id") or "").strip()
    unidade_id = None
    if unidade_raw:
        unidade_id = _parse_uuid(unidade_raw, "unidade")
        if not isinstance(unidade_id, uuid.UUID):
            return unidade_id

    itens: list[dict[str, Any]] = []
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            if not _instituicao_exists(cur, parsed):
                return jsonify({"error": "Instituição não encontrada"}), 404

            params_base: list[Any] = [str(parsed)]
            unidade_sql = ""
            if unidade_id is not None:
                unidade_sql = " AND t.unidade_id = %s"
                params_base.append(str(unidade_id))

            cur.execute(
                f"""
                SELECT COUNT(*)::int AS n
                FROM public.school_curadoria_metodologias c
                LEFT JOIN public.school_planos_aula_espelhados pe
                    ON pe.id = c.plano_espelhado_id
                LEFT JOIN public.school_turmas t ON t.id = pe.turma_id
                WHERE c.instituicao_id = %s
                  AND c.status_analise = 'pendente'
                  {unidade_sql}
                """,
                params_base,
            )
            n_met = int((cur.fetchone() or {}).get("n") or 0)

            cur.execute(
                f"""
                SELECT COUNT(*)::int AS n
                FROM public.school_curadoria_pei c
                LEFT JOIN public.school_planos_aula_espelhados pe
                    ON pe.id = c.plano_espelhado_id
                LEFT JOIN public.school_turmas t ON t.id = pe.turma_id
                WHERE c.instituicao_id = %s
                  AND c.status_analise = 'pendente'
                  {unidade_sql}
                """,
                params_base,
            )
            n_pei = int((cur.fetchone() or {}).get("n") or 0)

            cur.execute(
                f"""
                SELECT
                    c.id,
                    c.plano_espelhado_id,
                    c.created_at,
                    pe.semana_referencia,
                    t.nome AS turma_nome,
                    v.email_convite AS professor_email
                FROM public.school_curadoria_metodologias c
                LEFT JOIN public.school_planos_aula_espelhados pe
                    ON pe.id = c.plano_espelhado_id
                LEFT JOIN public.school_turmas t ON t.id = pe.turma_id
                LEFT JOIN public.school_professores_vinculo v
                    ON v.id = pe.professor_vinculo_id
                WHERE c.instituicao_id = %s
                  AND c.status_analise = 'pendente'
                  {unidade_sql}
                ORDER BY c.created_at DESC
                LIMIT 50
                """,
                params_base,
            )
            for r in cur.fetchall():
                email = str(r.get("professor_email") or "").strip()
                local = email.split("@")[0] if email else ""
                parts = [p for p in local.replace("_", ".").split(".") if p]
                if len(parts) >= 2:
                    label = f"Prof. {parts[0].title()} {parts[-1].title()}"
                elif parts:
                    label = f"Prof. {parts[0].title()}"
                else:
                    label = "Professor"
                itens.append(
                    {
                        "id": str(r["id"]),
                        "plano_id": str(r["plano_espelhado_id"])
                        if r.get("plano_espelhado_id")
                        else None,
                        "tipo": "metodologia",
                        "turma_nome": r.get("turma_nome") or "—",
                        "professor_label": label,
                        "data": _fmt_date(r.get("semana_referencia") or r.get("created_at")),
                    }
                )

            cur.execute(
                f"""
                SELECT
                    c.id,
                    c.plano_espelhado_id,
                    c.created_at,
                    pe.semana_referencia,
                    t.nome AS turma_nome,
                    v.email_convite AS professor_email
                FROM public.school_curadoria_pei c
                LEFT JOIN public.school_planos_aula_espelhados pe
                    ON pe.id = c.plano_espelhado_id
                LEFT JOIN public.school_turmas t ON t.id = pe.turma_id
                LEFT JOIN public.school_professores_vinculo v
                    ON v.id = pe.professor_vinculo_id
                WHERE c.instituicao_id = %s
                  AND c.status_analise = 'pendente'
                  {unidade_sql}
                ORDER BY c.created_at DESC
                LIMIT 50
                """,
                params_base,
            )
            for r in cur.fetchall():
                email = str(r.get("professor_email") or "").strip()
                local = email.split("@")[0] if email else ""
                parts = [p for p in local.replace("_", ".").split(".") if p]
                if len(parts) >= 2:
                    label = f"Prof. {parts[0].title()} {parts[-1].title()}"
                elif parts:
                    label = f"Prof. {parts[0].title()}"
                else:
                    label = "Professor"
                itens.append(
                    {
                        "id": str(r["id"]),
                        "plano_id": str(r["plano_espelhado_id"])
                        if r.get("plano_espelhado_id")
                        else None,
                        "tipo": "pei",
                        "turma_nome": r.get("turma_nome") or "—",
                        "professor_label": label,
                        "data": _fmt_date(r.get("semana_referencia") or r.get("created_at")),
                    }
                )

    itens.sort(key=lambda x: x.get("data") or "", reverse=True)

    return jsonify(
        {
            "total": n_met + n_pei,
            "metodologia": n_met,
            "pei": n_pei,
            "itens": itens,
        }
    )

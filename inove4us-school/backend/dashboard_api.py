"""Dashboard — calendário pedagógico consolidado (zona pedagógico).

Fonte: school_planos_aula_espelhados (espelho local).
Instituição/unidade vêm da sessão; UUID na URL só é aceito se bater com a sessão.
"""
from __future__ import annotations

import calendar
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Any

from flask import Blueprint, jsonify, request
from psycopg2.extras import RealDictCursor

from auth_guards import (
    require_zona,
    resolve_instituicao_id,
    resolve_unidade_id,
)
from contribuicao_agregada import (
    curadoria_foi_incorporada,
    montar_bloco_radar,
)
from db import get_conn

bp = Blueprint("dashboard", __name__)


@bp.before_request
@require_zona("pedagogico")
def _authz_dashboard():
    return None

def _bound_instituicao(instituicao_id: str):
    inst = resolve_instituicao_id(instituicao_id)
    if isinstance(inst, tuple):
        return inst
    parsed = _parse_uuid(inst, "instituição")
    if not isinstance(parsed, uuid.UUID):
        return parsed
    return parsed


def _bound_unidade(unidade_id: str):
    """Unidade deve pertencer à instituição da sessão e respeitar escopo do gestor."""
    parsed = _parse_uuid(unidade_id, "unidade")
    if not isinstance(parsed, uuid.UUID):
        return parsed
    escopo = resolve_unidade_id(str(parsed))
    if isinstance(escopo, tuple):
        return escopo
    inst = resolve_instituicao_id()
    if isinstance(inst, tuple):
        return inst
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id, instituicao_id FROM public.school_unidades
                WHERE id = %s AND ativo = TRUE
                """,
                (str(parsed),),
            )
            row = cur.fetchone()
            if not row:
                return jsonify({"error": "Unidade não encontrada"}), 404
            if str(row["instituicao_id"]) != inst:
                return (
                    jsonify(
                        {
                            "error": "Unidade fora do escopo da sessão.",
                            "code": "FORBIDDEN_INSTITUICAO",
                        }
                    ),
                    403,
                )
    return parsed


def _unidade_filtro_da_request():
    """Query unidade_id + escopo do gestor. Retorna uuid|None ou (resp, code)."""
    claimed = (request.args.get("unidade_id") or "").strip() or None
    resolved = resolve_unidade_id(claimed)
    if isinstance(resolved, tuple):
        return resolved
    if not resolved:
        return None
    return _parse_uuid(resolved, "unidade")


_PLANOS_SELECT = """
SELECT
    p.id,
    p.turma_id,
    t.nome AS turma_nome,
    t.turno AS turma_turno,
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
    aloc.disciplina_nome,
    aloc.disciplina_codigo,
    cur.nome AS curso_nome,
    pl.hora_inicio,
    pl.hora_fim,
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
LEFT JOIN public.school_cursos cur
    ON cur.id = t.curso_id
LEFT JOIN LATERAL (
    SELECT
        d.nome AS disciplina_nome,
        d.codigo AS disciplina_codigo
    FROM public.school_alocacoes_docentes a
    JOIN public.school_disciplinas d ON d.id = a.disciplina_id
    WHERE a.professor_vinculo_id = p.professor_vinculo_id
      AND a.ativo = TRUE
    ORDER BY (a.turma_id = p.turma_id) DESC NULLS LAST, a.updated_at DESC
    LIMIT 1
) aloc ON TRUE
LEFT JOIN LATERAL (
    SELECT pe.hora_inicio, pe.hora_fim
    FROM public.school_planejamento_escolar pe
    WHERE pe.turma_id = p.turma_id
      AND pe.professor_vinculo_id = p.professor_vinculo_id
      AND pe.data = p.semana_referencia
    ORDER BY pe.hora_inicio NULLS LAST
    LIMIT 1
) pl ON TRUE
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


_TURNO_HORARIO = {
    "manha": ("07:00", "Manhã"),
    "tarde": ("13:00", "Tarde"),
    "noite": ("18:00", "Noite"),
    "integral": ("08:00", "Integral"),
}


def _fmt_time(value: Any) -> str | None:
    if value is None:
        return None
    if hasattr(value, "strftime"):
        return value.strftime("%H:%M")
    text = str(value).strip()
    if not text:
        return None
    # time/datetime string → HH:MM
    if ":" in text:
        return text[:5]
    return text


def _codigo_disciplina(r: dict[str, Any]) -> str:
    code = str(r.get("disciplina_codigo") or "").strip()
    if code:
        return code.upper()
    nome = str(
        r.get("disciplina_nome") or r.get("curso_nome") or r.get("metodologia_nome") or ""
    ).strip()
    if not nome:
        return "—"
    parts = [p for p in nome.replace("-", " ").split() if p]
    if len(parts) == 1:
        return parts[0][:6].upper()
    return "".join(p[0] for p in parts[:4]).upper()


def _horario_fields(r: dict[str, Any]) -> tuple[str, str, str | None, str | None]:
    """Retorna (horario_sort, horario_label, hora_inicio, hora_fim)."""
    hi = _fmt_time(r.get("hora_inicio"))
    hf = _fmt_time(r.get("hora_fim"))
    if hi and hf:
        return hi, f"{hi}–{hf}", hi, hf
    if hi:
        return hi, hi, hi, hf
    turno = str(r.get("turma_turno") or "").strip().lower()
    sort_key, label = _TURNO_HORARIO.get(turno, ("99:99", "Sem horário"))
    return sort_key, label, None, None


def _iso_date(value: Any) -> str:
    text = str(value or "").strip()
    return text[:10] if len(text) >= 10 and text[4] == "-" else ""


def _data_br(value: Any) -> str:
    iso = _iso_date(value)
    if not iso:
        return ""
    y, m, d = iso.split("-")
    return f"{d}/{m}/{y}"


def _ocorrencia_vinculo_texto(occ: dict[str, Any]) -> str:
    """Texto passivo do link: unida com / continuação de / continuação em."""
    resolucao = str(occ.get("resolucao") or occ.get("status") or "").strip()
    dest = _data_br(occ.get("juncao_destino_data"))
    orig = _data_br(occ.get("juncao_origem_data"))
    cont_de = _data_br(occ.get("continuacao_origem_data"))
    cont_em = _data_br(occ.get("continuacao_destino_data"))
    if resolucao == "concluida_via_juncao" or dest:
        return f"Unida com a aula de {dest}" if dest else "Unida com outra aula"
    if orig:
        return f"Unida com a aula de {orig}"
    if cont_de:
        return f"Continuação de {cont_de}"
    if resolucao == "agendada_continuacao" or cont_em:
        return f"Continuação em {cont_em}" if cont_em else "Continuação agendada"
    return ""


def _ocorrencia_radar_fields(occ: dict[str, Any]) -> dict[str, Any]:
    resolucao = occ.get("resolucao") or occ.get("status")
    return {
        "ocorrencia_tipo": occ.get("tipo"),
        "ocorrencia_nota": occ.get("nota") or "",
        "ocorrencia_resolucao": resolucao,
        "aguardando_continuacao": bool(occ.get("aguardando_continuacao")),
        "ocorrencia_unida": bool(occ.get("unida")),
        "juncao_destino_id": occ.get("juncao_destino_id"),
        "juncao_destino_data": _iso_date(occ.get("juncao_destino_data")) or None,
        "juncao_origem_id": occ.get("juncao_origem_id"),
        "juncao_origem_data": _iso_date(occ.get("juncao_origem_data")) or None,
        "continuacao_origem_id": occ.get("continuacao_origem_id"),
        "continuacao_origem_data": _iso_date(occ.get("continuacao_origem_data")) or None,
        "continuacao_destino_id": occ.get("continuacao_destino_id"),
        "continuacao_destino_data": _iso_date(occ.get("continuacao_destino_data")) or None,
        "ocorrencia_vinculo": _ocorrencia_vinculo_texto(occ) or None,
    }


def _plano_row(r: dict[str, Any]) -> dict[str, Any]:
    mesa = _as_mesa(r.get("mesa_payload_json"))
    sugestao = str(
        r.get("texto_sugestao")
        or mesa.get("texto_sugestao")
        or mesa.get("teacher_adaptation_text")
        or ""
    ).strip() or None
    horario_sort, horario_label, hora_inicio, hora_fim = _horario_fields(r)
    codigo = _codigo_disciplina(r)
    ocorrencia = mesa.get("ocorrencia") if isinstance(mesa.get("ocorrencia"), dict) else {}
    occ_fields = _ocorrencia_radar_fields(ocorrencia)
    return {
        "id": str(r["id"]),
        "turma_id": str(r["turma_id"]),
        "turma_nome": r["turma_nome"],
        "turma_turno": r.get("turma_turno"),
        "unidade_id": str(r["unidade_id"]),
        "unidade_nome": r["unidade_nome"],
        "professor_vinculo_id": str(r["professor_vinculo_id"]),
        "professor_email": r.get("professor_email"),
        "professor_nome": mesa.get("professor_nome"),
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
        "disciplina_nome": r.get("disciplina_nome"),
        "disciplina_codigo": codigo,
        "curso_nome": r.get("curso_nome"),
        "hora_inicio": hora_inicio,
        "hora_fim": hora_fim,
        "horario_sort": horario_sort,
        "horario_label": horario_label,
        "item_kind": "aula",
        **occ_fields,
    }


def _evento_row(r: dict[str, Any]) -> dict[str, Any]:
    inicio = r.get("data_hora_inicio")
    fim = r.get("data_hora_fim")
    if hasattr(inicio, "astimezone"):
        try:
            inicio_local = inicio.astimezone()
        except Exception:
            inicio_local = inicio
    else:
        inicio_local = inicio
    ref = None
    hi = None
    if hasattr(inicio_local, "date"):
        ref = inicio_local.date().isoformat()
        hi = inicio_local.strftime("%H:%M")
    elif inicio_local:
        text = str(inicio_local)
        ref = text[:10]
        hi = text[11:16] if len(text) >= 16 else None
    hf = _fmt_time(fim) if fim else None
    if hi and hf:
        horario_label = f"{hi}–{hf}"
    else:
        horario_label = hi or "Evento"
    tipo = str(r.get("tipo") or "evento_escolar")
    reuniao = tipo == "reuniao_pedagogica"
    codigo = "REU" if reuniao else "EVT"
    now = datetime.now(timezone.utc)
    encerrado = False
    if isinstance(inicio, datetime):
        try:
            encerrado = (fim or inicio) < now
        except TypeError:
            encerrado = False
    return {
        "id": f"evt-{r['id']}",
        "item_kind": "evento",
        "tipo_aula": "evento",
        "evento_tipo": tipo,
        "turma_id": str(r["turma_id"]) if r.get("turma_id") else None,
        "turma_nome": r.get("turma_nome") or "Escola",
        "turma_turno": r.get("turma_turno"),
        "unidade_id": str(r["unidade_id"]) if r.get("unidade_id") else None,
        "unidade_nome": r.get("unidade_nome") or "Instituição",
        "professor_vinculo_id": None,
        "professor_email": None,
        "professor_nome": None,
        "metodologia_nome": None,
        "semana_referencia": ref,
        "status": r.get("status") or "agendado",
        "execucao_status": "concluida" if encerrado else "em_andamento",
        "conteudo_resumo": r.get("descricao"),
        "desafio_grupo_id": None,
        "desafio_titulo": None,
        "desafio_sequencia": None,
        "has_sugestao_curadoria": False,
        "texto_sugestao": None,
        "updated_at": r["updated_at"].isoformat() if r.get("updated_at") else None,
        "aula_titulo": r.get("titulo"),
        "disciplina_nome": "Reunião pedagógica" if reuniao else "Evento escolar",
        "disciplina_codigo": codigo,
        "curso_nome": None,
        "hora_inicio": hi,
        "hora_fim": hf,
        "horario_sort": hi or "12:00",
        "horario_label": horario_label,
    }


def _fetch_eventos(
    cur: Any,
    *,
    instituicao_id: str,
    data_inicio: date,
    data_fim: date,
    unidade_id: str | None = None,
) -> list[dict[str, Any]]:
    sql = """
        SELECT
            e.id,
            e.titulo,
            e.descricao,
            e.tipo,
            e.status,
            e.data_hora_inicio,
            e.data_hora_fim,
            e.turma_id,
            e.unidade_id,
            e.updated_at,
            t.nome AS turma_nome,
            t.turno AS turma_turno,
            u.nome AS unidade_nome
        FROM public.school_comunicacoes_eventos e
        LEFT JOIN public.school_turmas t ON t.id = e.turma_id
        LEFT JOIN public.school_unidades u ON u.id = COALESCE(e.unidade_id, t.unidade_id)
        WHERE e.instituicao_id = %s
          AND e.status <> 'cancelado'
          AND (e.data_hora_inicio::date) >= %s
          AND (e.data_hora_inicio::date) <= %s
    """
    params: list[Any] = [instituicao_id, data_inicio, data_fim]
    if unidade_id:
        sql += " AND (e.unidade_id = %s OR t.unidade_id = %s OR e.unidade_id IS NULL)"
        params.extend([unidade_id, unidade_id])
    sql += " ORDER BY e.data_hora_inicio"
    try:
        cur.execute(sql, params)
        return [_evento_row(r) for r in cur.fetchall()]
    except Exception:
        return []


def _resumo_payload(
    row: dict[str, Any],
    data_inicio: date,
    data_fim: date,
    contribuicao: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = {
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
    if contribuicao is not None:
        payload["contribuicao"] = contribuicao
    return payload


def _fetch_contribuicao_recorte(
    cur: Any,
    *,
    instituicao_id: str,
    data_inicio: date,
    data_fim: date,
    unidade_id: str | None = None,
) -> dict[str, Any]:
    """Agregado anônimo do recorte. Sem quebra por professor."""
    sql = """
        SELECT p.mesa_payload_json
        FROM public.school_planos_aula_espelhados p
        JOIN public.school_turmas t ON t.id = p.turma_id
        JOIN public.school_unidades u ON u.id = t.unidade_id
        WHERE u.instituicao_id = %s
          AND u.ativo = TRUE
          AND p.semana_referencia >= %s
          AND p.semana_referencia <= %s
    """
    params: list[Any] = [str(instituicao_id), data_inicio, data_fim]
    if unidade_id:
        sql += " AND t.unidade_id = %s"
        params.append(str(unidade_id))
    cur.execute(sql, params)
    mesas = [_as_mesa(r.get("mesa_payload_json")) for r in cur.fetchall()]

    sql_inc = """
        SELECT c.status_analise, c.resultado_analise
        FROM public.school_curadoria_metodologias c
        JOIN public.school_planos_aula_espelhados p ON p.id = c.plano_espelhado_id
        JOIN public.school_turmas t ON t.id = p.turma_id
        JOIN public.school_unidades u ON u.id = t.unidade_id
        WHERE u.instituicao_id = %s
          AND u.ativo = TRUE
          AND c.updated_at::date >= %s
          AND c.updated_at::date <= %s
    """
    params_inc: list[Any] = [str(instituicao_id), data_inicio, data_fim]
    if unidade_id:
        sql_inc += " AND t.unidade_id = %s"
        params_inc.append(str(unidade_id))
    try:
        cur.execute(sql_inc, params_inc)
        n_inc = sum(1 for r in cur.fetchall() if curadoria_foi_incorporada(dict(r)))
    except Exception:
        n_inc = 0
    return montar_bloco_radar(mesas=mesas, sugestoes_incorporadas=n_inc)


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
    inst = resolve_instituicao_id(instituicao_id)
    if isinstance(inst, tuple):
        return inst
    parsed = _parse_uuid(inst, "instituição")
    if not isinstance(parsed, uuid.UUID):
        return parsed
    escopo = resolve_unidade_id()
    if isinstance(escopo, tuple):
        return escopo

    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            if not _instituicao_exists(cur, parsed):
                return jsonify({"error": "Instituição não encontrada"}), 404
            sql = """
                SELECT id, nome, codigo, cidade, uf
                FROM public.school_unidades
                WHERE instituicao_id = %s AND ativo = TRUE
            """
            params: list[Any] = [str(parsed)]
            if escopo:
                sql += " AND id = %s"
                params.append(escopo)
            sql += " ORDER BY nome"
            cur.execute(sql, params)
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
    parsed = _bound_unidade(unidade_id)
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
            itens = [_plano_row(r) for r in rows]
            itens.extend(
                _fetch_eventos(
                    cur,
                    instituicao_id=str(unidade["instituicao_id"]),
                    data_inicio=data_inicio,
                    data_fim=data_fim,
                    unidade_id=str(parsed),
                )
            )

    return jsonify(itens)


@bp.get("/api/unidades/<unidade_id>/calendario-pedagogico/resumo")
def calendario_pedagogico_resumo(unidade_id: str):
    parsed = _bound_unidade(unidade_id)
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
            contribuicao = _fetch_contribuicao_recorte(
                cur,
                instituicao_id=str(unidade["instituicao_id"]),
                data_inicio=data_inicio,
                data_fim=data_fim,
                unidade_id=str(parsed),
            )

    return jsonify(_resumo_payload(row, data_inicio, data_fim, contribuicao))


@bp.get("/api/instituicoes/<instituicao_id>/calendario-pedagogico")
def calendario_instituicao(instituicao_id: str):
    parsed = _bound_instituicao(instituicao_id)
    if not isinstance(parsed, uuid.UUID):
        return parsed
    periodo = _resolver_periodo()
    if not isinstance(periodo, tuple) or not isinstance(periodo[0], date):
        return periodo
    data_inicio, data_fim = periodo

    unidade_id = _unidade_filtro_da_request()
    if isinstance(unidade_id, tuple):
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
            itens = [_plano_row(r) for r in rows]
            itens.extend(
                _fetch_eventos(
                    cur,
                    instituicao_id=str(parsed),
                    data_inicio=data_inicio,
                    data_fim=data_fim,
                    unidade_id=str(unidade_id) if unidade_id else None,
                )
            )

    return jsonify(itens)


@bp.get("/api/instituicoes/<instituicao_id>/calendario-pedagogico/resumo")
def calendario_instituicao_resumo(instituicao_id: str):
    parsed = _bound_instituicao(instituicao_id)
    if not isinstance(parsed, uuid.UUID):
        return parsed
    periodo = _resolver_periodo()
    if not isinstance(periodo, tuple) or not isinstance(periodo[0], date):
        return periodo
    data_inicio, data_fim = periodo

    unidade_id = _unidade_filtro_da_request()
    if isinstance(unidade_id, tuple):
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
            contribuicao = _fetch_contribuicao_recorte(
                cur,
                instituicao_id=str(parsed),
                data_inicio=data_inicio,
                data_fim=data_fim,
                unidade_id=str(unidade_id) if unidade_id else None,
            )

    return jsonify(_resumo_payload(row, data_inicio, data_fim, contribuicao))


@bp.get("/api/instituicoes/<instituicao_id>/planos-espelhados/<plano_id>")
def plano_espelhado_detail(instituicao_id: str, plano_id: str):
    """Detalhe do espelho: mesa completa + diário de bordo + flag de curadoria."""
    inst = _bound_instituicao(instituicao_id)
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
                    LEFT JOIN public.school_professores_vinculo v
                      ON v.id = %s
                    WHERE a.instituicao_id = %s AND a.ativo = TRUE
                      AND (
                        a.turma_id IS NULL
                        OR a.turma_id = %s
                      )
                      AND (
                        a.professor_b2c_id IS NULL
                        OR a.professor_b2c_id = v.professor_b2c_id
                      )
                    ORDER BY a.created_at DESC
                    LIMIT 20
                    """,
                    (
                        str(row["professor_vinculo_id"]),
                        str(inst),
                        str(row["turma_id"]),
                    ),
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
    parsed = _bound_instituicao(instituicao_id)
    if not isinstance(parsed, uuid.UUID):
        return parsed
    unidade_escopo = resolve_unidade_id()
    if isinstance(unidade_escopo, tuple):
        return unidade_escopo

    hoje = date.today()
    inicio_semana = hoje - timedelta(days=hoje.weekday())
    fim_semana = inicio_semana + timedelta(days=6)
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            if not _instituicao_exists(cur, parsed):
                return jsonify({"error": "Instituição não encontrada"}), 404

            if unidade_escopo:
                cur.execute(
                    """
                    SELECT COUNT(*)::int AS n
                    FROM public.school_unidades
                    WHERE instituicao_id = %s AND ativo = TRUE AND id = %s
                    """,
                    (str(parsed), unidade_escopo),
                )
            else:
                cur.execute(
                    """
                    SELECT COUNT(*)::int AS n
                    FROM public.school_unidades
                    WHERE instituicao_id = %s AND ativo = TRUE
                    """,
                    (str(parsed),),
                )
            unidades = int((cur.fetchone() or {}).get("n") or 0)

            if unidade_escopo:
                cur.execute(
                    """
                    SELECT COUNT(*)::int AS n
                    FROM public.school_turmas t
                    JOIN public.school_unidades u ON u.id = t.unidade_id
                    WHERE u.instituicao_id = %s AND t.ativa = TRUE
                      AND t.unidade_id = %s
                    """,
                    (str(parsed), unidade_escopo),
                )
            else:
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


def _professor_label_from_email(email: str | None) -> str:
    local = str(email or "").strip().split("@")[0] if email else ""
    parts = [p for p in local.replace("_", ".").split(".") if p]
    if len(parts) >= 2:
        return f"Prof. {parts[0].title()} {parts[-1].title()}"
    if parts:
        return f"Prof. {parts[0].title()}"
    return "Professor"


def _trecho_sugestao(payload: Any, limit: int = 140) -> str:
    if not isinstance(payload, dict):
        return ""
    text = str(
        payload.get("teacher_adaptation_text")
        or payload.get("texto_sugestao")
        or payload.get("texto")
        or ""
    ).strip()
    if not text:
        mesa = payload.get("mesa") if isinstance(payload.get("mesa"), dict) else {}
        text = str(mesa.get("teacher_adaptation_text") or "").strip()
    if not text:
        return ""
    compact = " ".join(text.split())
    if len(compact) <= limit:
        return compact
    return f"{compact[: limit - 1]}…"


def _item_curadoria(row: dict[str, Any], *, tipo: str) -> dict[str, Any]:
    created = row.get("created_at")
    return {
        "id": str(row["id"]),
        "plano_id": str(row["plano_espelhado_id"])
        if row.get("plano_espelhado_id")
        else None,
        "tipo": tipo,
        "metodologia_nome": (row.get("metodologia_nome") or "").strip() or "—",
        "turma_nome": row.get("turma_nome") or "—",
        "professor_label": _professor_label_from_email(row.get("professor_email")),
        "data": _fmt_date(row.get("semana_referencia") or created),
        "trecho": _trecho_sugestao(row.get("sugestao_professor_json")),
        "created_at": created.isoformat() if hasattr(created, "isoformat") else None,
    }


@bp.get("/api/instituicoes/<instituicao_id>/curadoria-pendente")
def curadoria_pendente(instituicao_id: str):
    """Fila unificada: curadoria metodologia + PEI com status_analise = pendente."""
    parsed = _bound_instituicao(instituicao_id)
    if not isinstance(parsed, uuid.UUID):
        return parsed

    unidade_id = _unidade_filtro_da_request()
    if isinstance(unidade_id, tuple):
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
                    c.metodologia_nome,
                    c.sugestao_professor_json,
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
                itens.append(_item_curadoria(r, tipo="metodologia"))

            cur.execute(
                f"""
                SELECT
                    c.id,
                    c.plano_espelhado_id,
                    c.metodologia_nome,
                    c.sugestao_professor_json,
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
                itens.append(_item_curadoria(r, tipo="pei"))

    itens.sort(
        key=lambda x: x.get("created_at") or x.get("data") or "",
        reverse=True,
    )

    return jsonify(
        {
            "total": n_met + n_pei,
            "metodologia": n_met,
            "pei": n_pei,
            "itens": itens,
        }
    )


def _sid_or_err():
    inst = resolve_instituicao_id()
    if isinstance(inst, tuple):
        return inst
    return inst


@bp.get("/api/pedagogico/unidades")
def list_unidades_sessao():
    inst = _sid_or_err()
    if isinstance(inst, tuple):
        return inst
    return list_unidades(inst)


@bp.get("/api/pedagogico/calendario-pedagogico")
def calendario_instituicao_sessao():
    inst = _sid_or_err()
    if isinstance(inst, tuple):
        return inst
    return calendario_instituicao(inst)


@bp.get("/api/pedagogico/calendario-pedagogico/resumo")
def calendario_instituicao_resumo_sessao():
    inst = _sid_or_err()
    if isinstance(inst, tuple):
        return inst
    return calendario_instituicao_resumo(inst)


@bp.get("/api/pedagogico/planos-espelhados/<plano_id>")
def plano_espelhado_detail_sessao(plano_id: str):
    inst = _sid_or_err()
    if isinstance(inst, tuple):
        return inst
    return plano_espelhado_detail(inst, plano_id)


@bp.get("/api/pedagogico/resumo-consolidado")
def resumo_consolidado_sessao():
    inst = _sid_or_err()
    if isinstance(inst, tuple):
        return inst
    return resumo_consolidado(inst)


@bp.get("/api/pedagogico/curadoria-pendente")
def curadoria_pendente_sessao():
    inst = _sid_or_err()
    if isinstance(inst, tuple):
        return inst
    return curadoria_pendente(inst)

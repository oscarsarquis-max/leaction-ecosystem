"""Agenda executiva — eventos/compromissos por cliente (id_clie)."""

from __future__ import annotations

import json
import sys

from flask import Blueprint, jsonify, request, session
from psycopg2.extras import RealDictCursor

from db import get_conn

agenda_bp = Blueprint("agenda", __name__)

_ensured = False

STATUSES = frozenset({"planejado", "em_execucao", "concluido"})
TIPOS = frozenset({"geral", "aula_eduscrum", "aula_dia"})
TURNOS = frozenset({"manha", "tarde", "noite"})
MODOS_EXECUCAO = frozenset({"continuidade", "reinicio"})

TURNO_HORA = {
    "manha": "08:00:00",
    "tarde": "14:00:00",
    "noite": "19:00:00",
}

SELECT_COLS = """
    id_evento, id_clie, data_evento, titulo, nota_texto, criado_em,
    status, tipo, meta_json, plano_session,
    id_evento_pai, relato_sala, participantes,
    plan_data, kanban_state,
    turma, turno, modo_execucao,
    disciplina_id, origem, id_externo_importacao, tema, desafio_id,
    id_clie_responsavel
"""

ORIGENS = frozenset({"manual", "wizard_ia", "importacao"})


def _require_user():
    user = session.get("user")
    if not user or not user.get("id_clie"):
        return None
    return user


def _ensure_table(conn):
    global _ensured
    if _ensured:
        return
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS public.inove_agenda_eventos (
                id_evento    SERIAL PRIMARY KEY,
                id_clie      INTEGER NOT NULL
                    REFERENCES public.ctdi_clie (id_clie) ON DELETE CASCADE,
                data_evento  TIMESTAMP WITHOUT TIME ZONE NOT NULL,
                titulo       VARCHAR(200) NOT NULL,
                nota_texto   TEXT,
                criado_em    TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_inove_agenda_eventos_clie_data
                ON public.inove_agenda_eventos (id_clie, data_evento);

            ALTER TABLE public.inove_agenda_eventos
                ADD COLUMN IF NOT EXISTS status VARCHAR(32) NOT NULL DEFAULT 'planejado';
            ALTER TABLE public.inove_agenda_eventos
                ADD COLUMN IF NOT EXISTS tipo VARCHAR(32) NOT NULL DEFAULT 'geral';
            ALTER TABLE public.inove_agenda_eventos
                ADD COLUMN IF NOT EXISTS meta_json JSONB;
            ALTER TABLE public.inove_agenda_eventos
                ADD COLUMN IF NOT EXISTS plano_session VARCHAR(64);
            ALTER TABLE public.inove_agenda_eventos
                ADD COLUMN IF NOT EXISTS id_evento_pai INTEGER
                    REFERENCES public.inove_agenda_eventos (id_evento) ON DELETE SET NULL;
            ALTER TABLE public.inove_agenda_eventos
                ADD COLUMN IF NOT EXISTS relato_sala TEXT;
            ALTER TABLE public.inove_agenda_eventos
                ADD COLUMN IF NOT EXISTS participantes TEXT;
            ALTER TABLE public.inove_agenda_eventos
                ADD COLUMN IF NOT EXISTS plan_data JSONB;
            ALTER TABLE public.inove_agenda_eventos
                ADD COLUMN IF NOT EXISTS kanban_state JSONB;
            ALTER TABLE public.inove_agenda_eventos
                ADD COLUMN IF NOT EXISTS turma VARCHAR(120);
            ALTER TABLE public.inove_agenda_eventos
                ADD COLUMN IF NOT EXISTS turno VARCHAR(32);
            ALTER TABLE public.inove_agenda_eventos
                ADD COLUMN IF NOT EXISTS modo_execucao VARCHAR(32);
            ALTER TABLE public.inove_agenda_eventos
                ADD COLUMN IF NOT EXISTS disciplina_id BIGINT;
            ALTER TABLE public.inove_agenda_eventos
                ADD COLUMN IF NOT EXISTS origem VARCHAR(20) NOT NULL DEFAULT 'manual';
            ALTER TABLE public.inove_agenda_eventos
                ADD COLUMN IF NOT EXISTS id_externo_importacao VARCHAR(160);

            CREATE INDEX IF NOT EXISTS idx_inove_agenda_eventos_session
                ON public.inove_agenda_eventos (id_clie, plano_session);
            CREATE INDEX IF NOT EXISTS idx_inove_agenda_eventos_pai
                ON public.inove_agenda_eventos (id_evento_pai);
            CREATE UNIQUE INDEX IF NOT EXISTS uq_inove_agenda_aula_dia_turma_turno
                ON public.inove_agenda_eventos (
                    id_clie,
                    (data_evento::date),
                    lower(trim(turma)),
                    lower(trim(turno))
                )
                WHERE tipo = 'aula_eduscrum'
                  AND turma IS NOT NULL
                  AND trim(turma) <> ''
                  AND turno IS NOT NULL
                  AND trim(turno) <> '';
            """
        )
    # desafio_id / inove_desafios — schema Fase 2 (idempotente)
    try:
        from desafios_routes import _ensure_desafios_schema

        _ensure_desafios_schema(conn)
    except Exception:
        pass
    _ensured = True


def _can_access_evento(cur, user_id_clie: int, ev: dict) -> tuple[bool, bool]:
    """
    Retorna (pode_ler, pode_editar).
    Isolamento multidisciplinar: um professor só lê/edita a própria execução.
    Compartilham o desafio (conteúdo), não o planejamento de aulas do outro.
    """
    from desafios_routes import _responsavel_evento

    resp = _responsavel_evento(ev)
    pode_editar = resp is not None and int(resp) == int(user_id_clie)
    if pode_editar:
        return True, True
    if int(ev.get("id_clie") or 0) == int(user_id_clie):
        return True, True
    return False, False


def _json_field(value):
    """Normaliza JSONB vindo do Postgres para dict/list/None na API."""
    if value is None:
        return None
    if isinstance(value, (dict, list)):
        return value
    if isinstance(value, (bytes, memoryview)):
        value = bytes(value).decode("utf-8", errors="replace")
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        try:
            return json.loads(text)
        except Exception:
            return None
    return None


def _serialize(row: dict) -> dict:
    out = dict(row)
    if out.get("data_evento"):
        out["data_evento"] = out["data_evento"].isoformat()
    if out.get("criado_em"):
        out["criado_em"] = out["criado_em"].isoformat()
    for key in ("meta_json", "plan_data", "kanban_state"):
        out[key] = _json_field(out.get(key))
    if out.get("desafio_id") is not None:
        out["desafio_id"] = str(out["desafio_id"])
    return out


def _parse_jsonb(value):
    """Serializa dict/list/str para string JSON aceita por %s::jsonb (None = SQL NULL)."""
    if value is None:
        return None
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, str) and value.strip():
        # valida JSON
        try:
            json.loads(value)
        except Exception as exc:
            raise ValueError("JSON inválido") from exc
        return value.strip()
    return None


def _parse_meta(value):
    return _parse_jsonb(value)


def _tarefas_from_kanban(kanban_state):
    """Extrai lista de cards de kanban_state (dict ou list legado)."""
    if isinstance(kanban_state, list):
        return [t for t in kanban_state if isinstance(t, dict)]
    if isinstance(kanban_state, dict):
        tarefas = kanban_state.get("tarefas")
        if isinstance(tarefas, list):
            return [t for t in tarefas if isinstance(t, dict)]
    return []


def _stamp_aula_id_on_tarefas(tarefas, aula_id):
    """Garante aula_id em cada card (legado → dono do board)."""
    aid = int(aula_id) if aula_id is not None else None
    out = []
    for t in tarefas or []:
        if not isinstance(t, dict):
            continue
        item = dict(t)
        raw = item.get("aula_id")
        if raw is None or raw == "":
            item["aula_id"] = aid
        else:
            try:
                item["aula_id"] = int(raw)
            except (TypeError, ValueError):
                item["aula_id"] = aid
        # Mantém aula_ids coerente com aula_id
        aids = []
        for x in item.get("aula_ids") or []:
            try:
                aids.append(int(x))
            except (TypeError, ValueError):
                continue
        if item.get("aula_id") is not None and int(item["aula_id"]) not in aids:
            aids.insert(0, int(item["aula_id"]))
        item["aula_ids"] = aids
        out.append(item)
    return out


def _merge_tarefas_by_card_id(tarefas: list) -> list:
    """Fund e cards com o mesmo id (mesmo card em várias turmas/aulas)."""
    rank = {"para_fazer": 0, "fazendo": 1, "pronto": 2}
    by_id: dict[str, dict] = {}
    orphans: list[dict] = []
    for t in tarefas or []:
        if not isinstance(t, dict):
            continue
        tid = str(t.get("id") or "").strip()
        if not tid:
            orphans.append(dict(t))
            continue
        if tid not in by_id:
            item = dict(t)
            aids: list[int] = []
            for x in item.get("aula_ids") or []:
                try:
                    aids.append(int(x))
                except (TypeError, ValueError):
                    pass
            if item.get("aula_id") is not None:
                try:
                    aid0 = int(item["aula_id"])
                    if aid0 not in aids:
                        aids.insert(0, aid0)
                except (TypeError, ValueError):
                    pass
            item["aula_ids"] = aids
            if aids and item.get("aula_id") is None:
                item["aula_id"] = aids[0]
            escopos = []
            for esc in item.get("escopos_turma") or []:
                if isinstance(esc, dict) and str(esc.get("nota") or "").strip():
                    escopos.append(dict(esc))
            item["escopos_turma"] = escopos
            by_id[tid] = item
            continue
        cur = by_id[tid]
        try:
            aid = int(t["aula_id"]) if t.get("aula_id") is not None else None
        except (TypeError, ValueError):
            aid = None
        if aid is not None and aid not in cur["aula_ids"]:
            cur["aula_ids"].append(aid)
        for esc in t.get("escopos_turma") or []:
            if not isinstance(esc, dict):
                continue
            eaid = esc.get("aula_id")
            try:
                eaid_i = int(eaid) if eaid is not None else None
            except (TypeError, ValueError):
                eaid_i = None
            already = any(
                int(x.get("aula_id")) == eaid_i
                for x in cur["escopos_turma"]
                if x.get("aula_id") is not None and eaid_i is not None
            )
            if not already and str(esc.get("nota") or "").strip():
                cur["escopos_turma"].append(dict(esc))
        if rank.get(str(t.get("coluna") or ""), 0) > rank.get(str(cur.get("coluna") or ""), 0):
            cur["coluna"] = t.get("coluna")
            if t.get("historico"):
                cur["historico"] = t.get("historico")
            if t.get("ultima_observacao"):
                cur["ultima_observacao"] = t.get("ultima_observacao")
    return list(by_id.values()) + orphans


def _kanban_para_aula_com_cards(
    *,
    plan_data_obj,
    kanban_base_obj,
    card_ids: list[str],
    aula_id: int,
    turma: str,
    escopos_by_card: dict[str, str],
) -> dict:
    """Monta kanban da aula só com os cards associados + escopo da turma.

    Ao registrar a aula, os cards entram em «Fazendo» (execução). O DoD
    (aulas concluídas) só bloqueia a migração para «Pronto».
    """
    base = _fresh_kanban_from_plan(plan_data_obj, kanban_base_obj)
    tarefas_src = _tarefas_from_kanban(base)
    wanted = {str(c).strip() for c in card_ids if str(c).strip()}
    out = []
    for t in tarefas_src:
        tid = str(t.get("id") or "").strip()
        if tid not in wanted:
            continue
        nota = str(escopos_by_card.get(tid) or "").strip()
        item = dict(t)
        item["coluna"] = "fazendo"
        item["historico"] = [
            {
                "de": "para_fazer",
                "para": "fazendo",
                "nota": "Aula registrada — em execução",
                "em": None,
            }
        ]
        item["ultima_observacao"] = None
        item["aula_id"] = int(aula_id)
        item["aula_ids"] = [int(aula_id)]
        item["escopos_turma"] = [
            {
                "aula_id": int(aula_id),
                "turma": turma,
                "nota": nota,
            }
        ]
        out.append(item)
    return {"tarefas": out}


def _kanban_continuidade_com_cards(
    *,
    prev_kanban,
    plan_data_obj,
    kanban_base_obj,
    card_ids: list[str],
    aula_id: int,
    turma: str,
    escopos_by_card: dict[str, str],
) -> dict:
    """Prosseguimento: mantém progresso dos cards escolhidos e carimba escopo da nova aula."""
    prev_map = {
        str(t.get("id") or "").strip(): dict(t)
        for t in _tarefas_from_kanban(prev_kanban)
        if str(t.get("id") or "").strip()
    }
    fresh = _kanban_para_aula_com_cards(
        plan_data_obj=plan_data_obj,
        kanban_base_obj=kanban_base_obj,
        card_ids=card_ids,
        aula_id=aula_id,
        turma=turma,
        escopos_by_card=escopos_by_card,
    )
    out = []
    for t in _tarefas_from_kanban(fresh):
        tid = str(t.get("id") or "").strip()
        item = dict(t)
        prev = prev_map.get(tid)
        if prev:
            item["coluna"] = prev.get("coluna") or "para_fazer"
            item["historico"] = list(prev.get("historico") or [])
            item["ultima_observacao"] = prev.get("ultima_observacao")
        out.append(item)
    return {"tarefas": out}


def _aula_ids_do_card(task: dict) -> list[int]:
    aids: list[int] = []
    for x in task.get("aula_ids") or []:
        try:
            aids.append(int(x))
        except (TypeError, ValueError):
            continue
    if task.get("aula_id") is not None:
        try:
            aid0 = int(task["aula_id"])
            if aid0 not in aids:
                aids.insert(0, aid0)
        except (TypeError, ValueError):
            pass
    return aids


def _expand_aula_ids_do_card_no_desafio(cur, id_clie: int, task: dict, anchor_evento: dict) -> list[int]:
    """Inclui aulas do desafio/turma que possuem o mesmo card_id (DoD de finalização)."""
    aids = _aula_ids_do_card(task)
    tid = str(task.get("id") or "").strip()
    if not tid:
        return aids
    plano_session = (anchor_evento.get("plano_session") or "").strip() or None
    owner = int(anchor_evento.get("id_clie") or id_clie)
    turma_anchor = (anchor_evento.get("turma") or "").strip().lower()
    if plano_session:
        cur.execute(
            """
            SELECT id_evento, kanban_state, turma
              FROM public.inove_agenda_eventos
             WHERE id_clie = %s
               AND plano_session = %s
               AND tipo = 'aula_eduscrum'
            """,
            (owner, plano_session),
        )
        for row in cur.fetchall():
            if turma_anchor:
                row_turma = (row.get("turma") or "").strip().lower()
                if row_turma and row_turma != turma_anchor:
                    continue
            for t in _tarefas_from_kanban(_json_field(row.get("kanban_state"))):
                if str(t.get("id") or "").strip() == tid:
                    try:
                        aid = int(row["id_evento"])
                    except (TypeError, ValueError):
                        continue
                    if aid not in aids:
                        aids.append(aid)
                    break
    return aids


def _card_pode_mover(
    cur,
    id_clie: int,
    task: dict,
    anchor_evento: dict | None = None,
    to_coluna: str | None = None,
):
    """Gate de coluna do Kanban.

    - Para Fazer ↔ Fazendo: livre na execução (card precisa ter aula vinculada).
    - Pronto: DoD — todas as aulas da turma vinculadas ao card concluídas.
    """
    aids = _aula_ids_do_card(task)
    dest = str(to_coluna or "").strip().lower()
    if not aids:
        return (
            False,
            "Card sem aula associada. Associe o card a uma aula (com escopo) antes de mover.",
        )
    # Execução: qualquer destino que não seja Pronto
    if dest and dest != "pronto":
        return True, None
    if anchor_evento is not None:
        aids = _expand_aula_ids_do_card_no_desafio(cur, id_clie, task, anchor_evento)
    cur.execute(
        """
        SELECT id_evento, status
          FROM public.inove_agenda_eventos
         WHERE id_clie = %s
           AND id_evento = ANY(%s)
        """,
        (id_clie, aids),
    )
    rows = {int(r["id_evento"]): r for r in cur.fetchall()}
    for aid in aids:
        row = rows.get(aid)
        if not row:
            return False, f"Aula #{aid} vinculada ao card não foi encontrada."
        if str(row.get("status") or "") != "concluido":
            return (
                False,
                "Para mover para Pronto, conclua a(s) aula(s) desta turma (relato). "
                "Durante a execução você pode mover entre Para Fazer e Fazendo.",
            )
    return True, None


def _normalize_kanban_state(kanban_state, aula_id=None):
    """Normaliza kanban_state e carimba aula_id nos cards quando informado."""
    if kanban_state is None:
        return None
    if isinstance(kanban_state, list):
        tarefas = _stamp_aula_id_on_tarefas(kanban_state, aula_id)
        return {"tarefas": tarefas}
    if isinstance(kanban_state, dict):
        out = dict(kanban_state)
        if "tarefas" in out or aula_id is not None:
            out["tarefas"] = _stamp_aula_id_on_tarefas(
                out.get("tarefas") if isinstance(out.get("tarefas"), list) else [],
                aula_id,
            )
        return out
    return kanban_state


def _cadeia_evento_ids(cur, id_clie: int, id_evento: int) -> list[int]:
    """IDs da cadeia id_evento_pai (sobe até a raiz e desce todos os filhos)."""
    current = id_evento
    visited: set[int] = set()
    while current and current not in visited:
        visited.add(current)
        cur.execute(
            """
            SELECT id_evento_pai
              FROM public.inove_agenda_eventos
             WHERE id_evento = %s AND id_clie = %s
            """,
            (current, id_clie),
        )
        row = cur.fetchone()
        if not row or row.get("id_evento_pai") is None:
            break
        current = int(row["id_evento_pai"])
    root = current
    ids: set[int] = {int(root)}
    frontier = [int(root)]
    while frontier:
        cur.execute(
            """
            SELECT id_evento
              FROM public.inove_agenda_eventos
             WHERE id_clie = %s
               AND id_evento_pai = ANY(%s)
            """,
            (id_clie, frontier),
        )
        kids = [int(r["id_evento"]) for r in cur.fetchall()]
        frontier = [k for k in kids if k not in ids]
        ids.update(frontier)
    return sorted(ids)


@agenda_bp.get("/api/agenda-eventos")
def list_eventos():
    user = _require_user()
    if not user:
        return jsonify({"success": False, "error": "Não autenticado"}), 401

    mes = (request.args.get("mes") or "").strip()
    plano_session = (request.args.get("plano_session") or "").strip()
    try:
        with get_conn() as conn:
            _ensure_table(conn)
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                sql = f"""
                    SELECT e.id_evento, e.id_clie, e.data_evento, e.titulo, e.nota_texto, e.criado_em,
                           e.status, e.tipo, e.meta_json, e.plano_session,
                           e.id_evento_pai, e.relato_sala, e.participantes,
                           e.plan_data, e.kanban_state,
                           e.turma, e.turno, e.modo_execucao,
                           e.disciplina_id, e.origem, e.id_externo_importacao
                    FROM public.inove_agenda_eventos e
                    LEFT JOIN public.inove_disciplinas d ON d.id = e.disciplina_id
                    LEFT JOIN public.inove_cursos c ON c.id = d.curso_id
                    WHERE e.id_clie = %s
                """
                params = [user["id_clie"]]
                if mes:
                    sql += " AND to_char(e.data_evento, 'YYYY-MM') = %s"
                    params.append(mes)
                if plano_session:
                    sql += " AND e.plano_session = %s"
                    params.append(plano_session)
                disc_f = (request.args.get("disciplina_id") or "").strip()
                if disc_f:
                    try:
                        sql += " AND e.disciplina_id = %s"
                        params.append(int(disc_f))
                    except (TypeError, ValueError):
                        return jsonify({"success": False, "error": "disciplina_id inválido"}), 400
                curso_f = (request.args.get("curso_id") or "").strip()
                if curso_f:
                    try:
                        sql += " AND c.id = %s"
                        params.append(int(curso_f))
                    except (TypeError, ValueError):
                        return jsonify({"success": False, "error": "curso_id inválido"}), 400
                periodo_f = (request.args.get("periodo_letivo_id") or "").strip()
                if periodo_f:
                    try:
                        sql += " AND c.periodo_letivo_id = %s"
                        params.append(int(periodo_f))
                    except (TypeError, ValueError):
                        return jsonify({"success": False, "error": "periodo_letivo_id inválido"}), 400
                origem_f = (request.args.get("origem") or "").strip().lower()
                if origem_f:
                    if origem_f not in ORIGENS:
                        return jsonify({"success": False, "error": "origem inválida"}), 400
                    sql += " AND e.origem = %s"
                    params.append(origem_f)
                sql += " ORDER BY e.data_evento ASC, e.id_evento ASC"
                cur.execute(sql, params)
                rows = [_serialize(dict(r)) for r in cur.fetchall()]
        return jsonify({"success": True, "eventos": rows})
    except Exception as exc:
        print(f"⚠️ agenda list: {exc}", file=sys.stderr)
        return jsonify({"success": False, "error": "Falha ao listar agenda"}), 500


@agenda_bp.get("/api/agenda-eventos/grafo")
def grafo_realizacoes():
    """
    Nós e arestas para o mapa de planejamento (id_evento_pai).
    Filtro opcional: periodo_letivo_id — inclui eventos da disciplina do período
    e eventos sem disciplina cuja data cai no intervalo do período.
    """
    user = _require_user()
    if not user:
        return jsonify({"success": False, "error": "Não autenticado"}), 401

    periodo_raw = (request.args.get("periodo_letivo_id") or "").strip()
    periodo_id = None
    if periodo_raw:
        try:
            periodo_id = int(periodo_raw)
        except (TypeError, ValueError):
            return jsonify({"success": False, "error": "periodo_letivo_id inválido"}), 400

    id_clie = user["id_clie"]
    try:
        with get_conn() as conn:
            _ensure_table(conn)
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                periodo_meta = None
                if periodo_id is not None:
                    cur.execute(
                        """
                        SELECT p.id, p.rotulo, p.ano_letivo, p.data_inicio, p.data_fim,
                               p.em_curso, p.instituicao_id, i.nome AS instituicao_nome
                          FROM public.inove_periodos_letivos p
                          JOIN public.inove_instituicoes i ON i.id = p.instituicao_id
                         WHERE p.id = %s
                           AND i.id_clie = %s
                           AND p.ativo = TRUE
                           AND i.ativo = TRUE
                        """,
                        (periodo_id, id_clie),
                    )
                    periodo_meta = cur.fetchone()
                    if not periodo_meta:
                        return jsonify({"success": False, "error": "Período letivo não encontrado"}), 404

                sql = """
                    SELECT e.id_evento, e.id_clie, e.data_evento, e.titulo, e.nota_texto,
                           e.status, e.tipo, e.meta_json, e.plano_session,
                           e.id_evento_pai, e.relato_sala, e.participantes,
                           e.plan_data, e.kanban_state,
                           e.disciplina_id, e.origem, e.id_externo_importacao, e.tema,
                           d.nome AS nome_disciplina,
                           c.id AS curso_id, c.nome AS nome_curso,
                           p.id AS periodo_letivo_id, p.rotulo AS periodo_rotulo,
                           p.data_inicio AS periodo_data_inicio, p.data_fim AS periodo_data_fim,
                           i.id AS instituicao_id, i.nome AS nome_instituicao
                      FROM public.inove_agenda_eventos e
                      LEFT JOIN public.inove_disciplinas d ON d.id = e.disciplina_id
                      LEFT JOIN public.inove_cursos c ON c.id = d.curso_id
                      LEFT JOIN public.inove_periodos_letivos p ON p.id = c.periodo_letivo_id
                      LEFT JOIN public.inove_instituicoes i ON i.id = p.instituicao_id
                     WHERE e.id_clie = %s
                """
                params: list = [id_clie]
                if periodo_meta is not None:
                    # Disciplina do período: só se a data cair no intervalo.
                    # Sem disciplina: mesma regra de data (antes sumiam fora do range
                    # enquanto eventos com disciplina apareciam mesmo fora — assimétrico).
                    sql += """
                       AND e.data_evento::date >= %s
                       AND e.data_evento::date <= %s
                       AND (
                            p.id = %s
                            OR e.disciplina_id IS NULL
                       )
                    """
                    params.extend(
                        [
                            periodo_meta["data_inicio"],
                            periodo_meta["data_fim"],
                            periodo_id,
                        ]
                    )
                sql += " ORDER BY e.data_evento ASC, e.id_evento ASC"
                cur.execute(sql, params)
                raw_rows = cur.fetchall()

        nodes = []
        edges = []
        id_set = set()
        for row in raw_rows:
            r = _serialize(dict(row))
            meta = r.get("meta_json") if isinstance(r.get("meta_json"), dict) else {}
            plan = r.get("plan_data")
            tem_plano = isinstance(plan, dict) and len(plan) > 0
            tema_col = r.get("tema") if isinstance(r.get("tema"), str) else None
            tema_meta = meta.get("tema") if isinstance(meta.get("tema"), str) else None
            tema = (tema_col or tema_meta or "").strip() or None
            status_ev = r.get("status") or "planejado"
            tarefas_kb = _tarefas_from_kanban(r.get("kanban_state"))
            cards_prontos = bool(tarefas_kb) and all(
                str(t.get("coluna") or "") == "pronto" for t in tarefas_kb
            )
            # Passado: relato concluído e/ou todos os cards da aula em Pronto
            no_passado = status_ev == "concluido" or cards_prontos
            node = {
                "id": r["id_evento"],
                "titulo": r["titulo"],
                "data": r.get("data_evento"),
                "data_evento": r.get("data_evento"),
                "status": status_ev,
                "tipo": r.get("tipo") or "geral",
                "id_evento_pai": r.get("id_evento_pai"),
                "disciplina_id": r.get("disciplina_id"),
                "nome_disciplina": r.get("nome_disciplina"),
                "curso_id": r.get("curso_id"),
                "nome_curso": r.get("nome_curso"),
                "periodo_letivo_id": r.get("periodo_letivo_id"),
                "instituicao_id": r.get("instituicao_id"),
                "nome_instituicao": r.get("nome_instituicao"),
                "tema": tema,
                "tem_relato": bool((r.get("relato_sala") or "").strip()),
                "relato_sala": r.get("relato_sala") or "",
                "participantes": r.get("participantes") or "",
                "nota_texto": r.get("nota_texto") or "",
                "meta_json": meta,
                "plan_data": plan if tem_plano else None,
                "kanban_state": r.get("kanban_state"),
                "tem_plano": tem_plano,
                "aula_simples_id": meta.get("aula_simples_id"),
                "origem": r.get("origem"),
                "cards_prontos": cards_prontos,
                "no_passado": no_passado,
            }
            nodes.append(node)
            id_set.add(r["id_evento"])

        for n in nodes:
            pai = n.get("id_evento_pai")
            if pai and pai in id_set:
                edges.append({"from": pai, "to": n["id"], "kind": "desdobramento"})

        periodo_out = None
        if periodo_meta is not None:
            periodo_out = {
                "id": int(periodo_meta["id"]),
                "rotulo": periodo_meta.get("rotulo"),
                "ano_letivo": periodo_meta.get("ano_letivo"),
                "data_inicio": (
                    periodo_meta["data_inicio"].isoformat()
                    if hasattr(periodo_meta["data_inicio"], "isoformat")
                    else str(periodo_meta["data_inicio"])
                ),
                "data_fim": (
                    periodo_meta["data_fim"].isoformat()
                    if hasattr(periodo_meta["data_fim"], "isoformat")
                    else str(periodo_meta["data_fim"])
                ),
                "em_curso": bool(periodo_meta.get("em_curso")),
                "instituicao_id": periodo_meta.get("instituicao_id"),
                "instituicao_nome": periodo_meta.get("instituicao_nome"),
            }

        return jsonify(
            {
                "success": True,
                "nodes": nodes,
                "edges": edges,
                "periodo": periodo_out,
            }
        )
    except Exception as exc:
        print(f"⚠️ agenda grafo: {exc}", file=sys.stderr)
        return jsonify({"success": False, "error": "Falha ao montar mapa de realizações"}), 500


@agenda_bp.post("/api/agenda-eventos")
def create_evento():
    user = _require_user()
    if not user:
        return jsonify({"success": False, "error": "Não autenticado"}), 401

    data = request.get_json(silent=True) or {}
    titulo = (data.get("titulo") or "").strip()
    data_evento = data.get("data_evento")
    nota_texto = (data.get("nota_texto") or "").strip() or None
    status = (data.get("status") or "planejado").strip().lower()
    tipo = (data.get("tipo") or "geral").strip().lower()
    plano_session = (data.get("plano_session") or "").strip() or None
    meta_json = _parse_meta(data.get("meta_json"))
    id_evento_pai = data.get("id_evento_pai")
    if id_evento_pai is not None:
        try:
            id_evento_pai = int(id_evento_pai)
        except (TypeError, ValueError):
            return jsonify({"success": False, "error": "id_evento_pai inválido"}), 400

    if status not in STATUSES:
        return jsonify({"success": False, "error": "status inválido"}), 400
    if tipo not in TIPOS:
        return jsonify({"success": False, "error": "tipo inválido"}), 400
    if not titulo or not data_evento:
        return jsonify({"success": False, "error": "titulo e data_evento são obrigatórios"}), 400

    origem = str(data.get("origem") or "manual").strip().lower()
    if origem not in ORIGENS:
        origem = "manual"
    disciplina_raw = data.get("disciplina_id")
    if disciplina_raw in ("", None):
        disciplina_raw = None

    try:
        with get_conn() as conn:
            _ensure_table(conn)
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                disciplina_id = None
                if disciplina_raw is not None:
                    try:
                        disciplina_id = int(disciplina_raw)
                    except (TypeError, ValueError):
                        return jsonify({"success": False, "error": "disciplina_id inválido"}), 400
                    cur.execute(
                        """
                        SELECT d.id
                          FROM public.inove_disciplinas d
                          JOIN public.inove_cursos c ON c.id = d.curso_id
                          JOIN public.inove_periodos_letivos p ON p.id = c.periodo_letivo_id
                          JOIN public.inove_instituicoes i ON i.id = p.instituicao_id
                         WHERE d.id = %s
                           AND i.id_clie = %s
                           AND d.ativo = TRUE
                           AND c.ativo = TRUE
                           AND p.ativo = TRUE
                           AND i.ativo = TRUE
                        """,
                        (disciplina_id, user["id_clie"]),
                    )
                    if not cur.fetchone():
                        return jsonify(
                            {"success": False, "error": "Disciplina não encontrada ou sem permissão"}
                        ), 404

                cur.execute(
                    f"""
                    INSERT INTO public.inove_agenda_eventos
                        (id_clie, data_evento, titulo, nota_texto, status, tipo,
                         meta_json, plano_session, id_evento_pai,
                         disciplina_id, origem)
                    VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s, %s, %s)
                    RETURNING {SELECT_COLS}
                    """,
                    (
                        user["id_clie"],
                        data_evento,
                        titulo[:200],
                        nota_texto,
                        status,
                        tipo,
                        meta_json,
                        plano_session,
                        id_evento_pai,
                        disciplina_id,
                        origem,
                    ),
                )
                row = cur.fetchone()
        return jsonify({"success": True, "evento": _serialize(dict(row))}), 201
    except Exception as exc:
        print(f"⚠️ agenda create: {exc}", file=sys.stderr)
        return jsonify({"success": False, "error": "Falha ao criar evento"}), 500


def _turno_label(turno: str) -> str:
    return {"manha": "Manhã", "tarde": "Tarde", "noite": "Noite"}.get(turno, turno)


def _modo_label(modo: str) -> str:
    return {
        "continuidade": "Prosseguimento",
        "reinicio": "Começar do início",
    }.get(modo, modo)


def _fresh_kanban_from_plan(plan_data, fallback_state):
    """Kanban do zero: tarefas do plano, coluna para_fazer, sem histórico."""
    plano = None
    if isinstance(plan_data, dict):
        plano = plan_data.get("plano") or plan_data.get("plano_eduscrum")
    tarefas_src = []
    if isinstance(plano, dict) and isinstance(plano.get("tarefas_kanban"), list):
        tarefas_src = plano["tarefas_kanban"]
    elif isinstance(fallback_state, dict) and isinstance(fallback_state.get("tarefas"), list):
        tarefas_src = fallback_state["tarefas"]
    elif isinstance(fallback_state, list):
        tarefas_src = fallback_state

    tarefas = []
    for t in tarefas_src:
        if not isinstance(t, dict):
            continue
        tarefas.append(
            {
                **t,
                "coluna": "para_fazer",
                "historico": [],
                "ultima_observacao": None,
            }
        )
    return {"tarefas": tarefas}


def _normalize_aulas_payload(data: dict):
    """
    Aceita:
      aulas: [{ data, turma, turno, modo_execucao }]
    ou legado:
      datas: ['YYYY-MM-DD', ...]  → exige turma/turno/modo no root
    """
    aulas_raw = data.get("aulas")
    if isinstance(aulas_raw, list) and aulas_raw:
        return aulas_raw

    datas = data.get("datas") or []
    if isinstance(datas, str):
        datas = [datas]
    datas = [str(d).strip()[:10] for d in datas if str(d).strip()]
    if not datas:
        return []

    turma = (data.get("turma") or "").strip()
    turno = (data.get("turno") or "manha").strip().lower()
    modo = (data.get("modo_execucao") or "reinicio").strip().lower()
    return [
        {"data": dia, "turma": turma, "turno": turno, "modo_execucao": modo}
        for dia in datas
    ]


@agenda_bp.post("/api/agenda-eventos/registrar-aulas")
def registrar_aulas():
    """
    Registra uma ou mais aulas EduScrum.
    Cada item pode ter data + turma + turno + modo_execucao:
      - continuidade: mesma turma/problema, herda kanban da última aula da turma
      - reinicio: mesma missão/problema, começa o Kanban do zero (outra turma ou reset)
    Vários eventos no mesmo dia são permitidos se turma e/ou turno forem diferentes.
    """
    user = _require_user()
    if not user:
        return jsonify({"success": False, "error": "Não autenticado"}), 401

    data = request.get_json(silent=True) or {}
    aulas_in = _normalize_aulas_payload(data)
    if not aulas_in:
        return jsonify({"success": False, "error": "Informe ao menos uma aula (data + turma + turno)."}), 400

    titulo_base = (data.get("titulo") or "Aula EduScrum").strip()[:140]
    nota_texto = (data.get("nota_texto") or "").strip() or None
    plano_session = (data.get("plano_session") or "").strip() or None
    desafio_id_req = str(data.get("desafio_id") or "").strip() or None
    disciplina_raw = data.get("disciplina_id")
    if disciplina_raw in ("", None):
        disciplina_raw = None

    plan_data_obj = data.get("plan_data")
    if isinstance(plan_data_obj, str) and plan_data_obj.strip():
        try:
            plan_data_obj = json.loads(plan_data_obj)
        except Exception:
            return jsonify({"success": False, "error": "plan_data inválido"}), 400
    if plan_data_obj is not None and not isinstance(plan_data_obj, (dict, list)):
        return jsonify({"success": False, "error": "plan_data inválido"}), 400

    kanban_base_obj = data.get("kanban_state")
    if isinstance(kanban_base_obj, str) and kanban_base_obj.strip():
        try:
            kanban_base_obj = json.loads(kanban_base_obj)
        except Exception:
            return jsonify({"success": False, "error": "kanban_state inválido"}), 400
    if kanban_base_obj is not None and not isinstance(kanban_base_obj, (dict, list)):
        return jsonify({"success": False, "error": "kanban_state inválido"}), 400

    try:
        meta_obj = data.get("meta_json")
        if isinstance(meta_obj, str) and meta_obj.strip():
            meta_obj = json.loads(meta_obj)
        if meta_obj is not None and not isinstance(meta_obj, dict):
            meta_obj = {}
        if meta_obj is None:
            meta_obj = {}
    except Exception:
        return jsonify({"success": False, "error": "meta_json inválido"}), 400

    causas_obj = data.get("causas")
    if causas_obj is None and isinstance(plan_data_obj, dict):
        causas_obj = plan_data_obj.get("causas")
    if causas_obj is None:
        causas_obj = meta_obj.get("causas")
    tema_obj = (data.get("tema") or meta_obj.get("tema") or "").strip() or None

    # Enrich plan_data with causas for persistence
    if isinstance(plan_data_obj, dict) and causas_obj is not None and "causas" not in plan_data_obj:
        plan_data_obj = {**plan_data_obj, "causas": causas_obj}
    if causas_obj is not None:
        meta_obj = {**meta_obj, "causas": causas_obj}
    if tema_obj:
        meta_obj = {**meta_obj, "tema": tema_obj}

    # valida e normaliza slots
    slots = []
    seen = set()
    for raw in aulas_in:
        if not isinstance(raw, dict):
            return jsonify({"success": False, "error": "Item de aula inválido"}), 400
        dia = str(raw.get("data") or "").strip()[:10]
        turma = str(raw.get("turma") or "").strip()
        turno = str(raw.get("turno") or "").strip().lower()
        modo = str(raw.get("modo_execucao") or "").strip().lower()
        if not dia or len(dia) < 10:
            return jsonify({"success": False, "error": "Cada aula precisa de uma data válida."}), 400
        if not turma:
            return jsonify({"success": False, "error": "Informe a turma de cada aula."}), 400
        if turno not in TURNOS:
            return jsonify({"success": False, "error": "Turno inválido (manha, tarde ou noite)."}), 400
        if modo not in MODOS_EXECUCAO:
            return jsonify(
                {
                    "success": False,
                    "error": "Modo inválido: use continuidade (prosseguimento) ou reinicio (começar do início).",
                }
            ), 400
        key = (dia, turma.lower(), turno)
        if key in seen:
            return jsonify(
                {
                    "success": False,
                    "error": f"Duplicado na lista: {dia} · {turma} · {_turno_label(turno)}.",
                }
            ), 400
        # Cards obrigatórios: o que cada turma realiza neste slot
        card_ids_raw = raw.get("card_ids") or raw.get("cards") or []
        if isinstance(card_ids_raw, str):
            card_ids_raw = [card_ids_raw]
        if not isinstance(card_ids_raw, list):
            return jsonify(
                {"success": False, "error": "card_ids deve ser uma lista de ids de cards."}
            ), 400
        card_ids: list[str] = []
        seen_cards: set[str] = set()
        for c in card_ids_raw:
            cid = str(c or "").strip()
            if not cid or cid in seen_cards:
                continue
            seen_cards.add(cid)
            card_ids.append(cid)
        if not card_ids:
            return jsonify(
                {
                    "success": False,
                    "error": (
                        f"Aula {turma} ({dia}): associe ao menos um card do plano. "
                        "Sem card vinculado a aula não tem o que realizar."
                    ),
                }
            ), 400

        escopos_by_card: dict[str, str] = {}
        escopos_raw = raw.get("escopos") or raw.get("escopos_turma") or {}
        if isinstance(escopos_raw, dict):
            for cid, nota in escopos_raw.items():
                escopos_by_card[str(cid).strip()] = str(nota or "").strip()
        elif isinstance(escopos_raw, list):
            for esc in escopos_raw:
                if not isinstance(esc, dict):
                    continue
                cid = str(esc.get("card_id") or esc.get("id") or "").strip()
                if not cid:
                    continue
                escopos_by_card[cid] = str(esc.get("nota") or esc.get("escopo") or "").strip()

        for cid in card_ids:
            nota = escopos_by_card.get(cid) or ""
            if not nota:
                return jsonify(
                    {
                        "success": False,
                        "error": (
                            f"Aula {turma} ({dia}): declare o que a turma vai realizar "
                            f"no card «{cid}» (escopo obrigatório). "
                            "O mesmo card pode ir a duas turmas — cada uma com seu escopo."
                        ),
                    }
                ), 400

        seen.add(key)
        slots.append(
            {
                "data": dia,
                "turma": turma[:120],
                "turno": turno,
                "modo_execucao": modo,
                "card_ids": card_ids,
                "escopos_by_card": {c: escopos_by_card[c] for c in card_ids},
            }
        )

    criados = []
    desafio_id_criado = None
    try:
        with get_conn() as conn:
            _ensure_table(conn)
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                disciplina_id = None
                if disciplina_raw is not None:
                    try:
                        disciplina_id = int(disciplina_raw)
                    except (TypeError, ValueError):
                        return jsonify({"success": False, "error": "disciplina_id inválido"}), 400
                    cur.execute(
                        """
                        SELECT d.id
                          FROM public.inove_disciplinas d
                          JOIN public.inove_cursos c ON c.id = d.curso_id
                          JOIN public.inove_periodos_letivos p ON p.id = c.periodo_letivo_id
                          JOIN public.inove_instituicoes i ON i.id = p.instituicao_id
                         WHERE d.id = %s
                           AND i.id_clie = %s
                           AND d.ativo = TRUE
                           AND c.ativo = TRUE
                           AND p.ativo = TRUE
                           AND i.ativo = TRUE
                        """,
                        (disciplina_id, user["id_clie"]),
                    )
                    if not cur.fetchone():
                        return jsonify(
                            {"success": False, "error": "Disciplina não encontrada ou sem permissão"}
                        ), 404

                # Desafio: reutiliza o informado (acrescentar/ratificar) ou cria um novo
                from desafios_routes import (
                    _ensure_desafios_schema,
                    _papel_acesso_desafio,
                    create_desafio_row,
                )

                hipotese_val = None
                problema_val = None
                if isinstance(plan_data_obj, dict):
                    hipotese_val = plan_data_obj.get("hipotese") or plan_data_obj.get("hipotese_teste")
                    problema_val = plan_data_obj.get("problema")
                if not hipotese_val:
                    hipotese_val = meta_obj.get("hipotese")
                if not problema_val:
                    problema_val = meta_obj.get("problema")

                if desafio_id_req:
                    _ensure_desafios_schema(conn)
                    papel, desafio_row = _papel_acesso_desafio(
                        cur, desafio_id_req, user["id_clie"]
                    )
                    if papel is None or not desafio_row:
                        return jsonify({"success": False, "error": "Desafio não encontrado"}), 404
                    desafio_id_criado = str(desafio_row["id"])
                    if plan_data_obj is None:
                        plan_data_obj = _json_field(desafio_row.get("plan_data"))
                    if not plano_session:
                        cur.execute(
                            """
                            SELECT plano_session
                              FROM public.inove_agenda_eventos
                             WHERE desafio_id = %s
                               AND id_clie = %s
                               AND plano_session IS NOT NULL
                               AND trim(plano_session) <> ''
                             ORDER BY id_evento ASC
                             LIMIT 1
                            """,
                            (desafio_id_criado, user["id_clie"]),
                        )
                        ps_row = cur.fetchone()
                        if ps_row and ps_row.get("plano_session"):
                            plano_session = str(ps_row["plano_session"]).strip()
                    if not titulo_base or titulo_base == "Aula EduScrum":
                        titulo_base = (desafio_row.get("titulo") or titulo_base)[:140]
                    if not tema_obj and desafio_row.get("tema"):
                        tema_obj = str(desafio_row["tema"]).strip() or None
                else:
                    desafio_row = create_desafio_row(
                        cur,
                        id_clie=user["id_clie"],
                        titulo=titulo_base,
                        problema=problema_val,
                        hipotese=hipotese_val,
                        causas=causas_obj,
                        tema=tema_obj,
                        plan_data=plan_data_obj,
                        meta_json=meta_obj,
                        disciplina_id=disciplina_id,
                    )
                    desafio_id_criado = str(desafio_row["id"])

                meta_obj = {**meta_obj, "desafio_id": desafio_id_criado}

                for slot in slots:
                    dia = slot["data"]
                    turma = slot["turma"]
                    turno = slot["turno"]
                    modo = slot["modo_execucao"]
                    hora = TURNO_HORA[turno]
                    data_evento = f"{dia}T{hora}"

                    # conflito no banco (mesmo dia+turma+turno)
                    cur.execute(
                        """
                        SELECT id_evento FROM public.inove_agenda_eventos
                        WHERE id_clie = %s
                          AND tipo = 'aula_eduscrum'
                          AND data_evento::date = %s::date
                          AND lower(trim(turma)) = lower(trim(%s))
                          AND lower(trim(turno)) = lower(trim(%s))
                        LIMIT 1
                        """,
                        (user["id_clie"], dia, turma, turno),
                    )
                    if cur.fetchone():
                        return (
                            jsonify(
                                {
                                    "success": False,
                                    "error": (
                                        f"Já existe aula em {dia} para {turma} "
                                        f"({_turno_label(turno)}). Use outro turno ou turma."
                                    ),
                                }
                            ),
                            409,
                        )

                    id_pai = None
                    prev_kanban = None
                    if modo == "continuidade":
                        cur.execute(
                            f"""
                            SELECT {SELECT_COLS}
                            FROM public.inove_agenda_eventos
                            WHERE id_clie = %s
                              AND tipo = 'aula_eduscrum'
                              AND lower(trim(turma)) = lower(trim(%s))
                              AND (%s::text IS NULL OR plano_session = %s)
                              AND (%s::uuid IS NULL OR desafio_id = %s::uuid)
                            ORDER BY data_evento DESC, id_evento DESC
                            LIMIT 1
                            """,
                            (
                                user["id_clie"],
                                turma,
                                plano_session,
                                plano_session,
                                desafio_id_criado,
                                desafio_id_criado,
                            ),
                        )
                        prev = cur.fetchone()
                        if prev and prev.get("kanban_state") is not None:
                            prev_kanban = _json_field(prev.get("kanban_state"))
                            if isinstance(prev_kanban, list):
                                prev_kanban = {"tarefas": prev_kanban}
                        id_pai = prev["id_evento"] if prev else None

                    # Placeholder — kanban definitivo após INSERT (precisa do id_evento)
                    kanban_state = {"tarefas": []}

                    titulo = f"{titulo_base} · {turma} · {_turno_label(turno)}"[:200]
                    nota_parts = [
                        nota_texto,
                        f"Turma: {turma}",
                        f"Turno: {_turno_label(turno)}",
                        f"Modo: {_modo_label(modo)}",
                        f"Cards: {', '.join(slot['card_ids'])}",
                    ]
                    nota_final = "\n".join(p for p in nota_parts if p)

                    meta_final = {
                        **meta_obj,
                        "turma": turma,
                        "turno": turno,
                        "modo_execucao": modo,
                        "modo_label": _modo_label(modo),
                        "card_ids": slot["card_ids"],
                        "escopos_by_card": slot["escopos_by_card"],
                    }

                    cur.execute(
                        f"""
                        INSERT INTO public.inove_agenda_eventos
                            (id_clie, data_evento, titulo, nota_texto, status, tipo,
                             meta_json, plano_session, plan_data, kanban_state,
                             turma, turno, modo_execucao, id_evento_pai,
                             disciplina_id, origem, tema, desafio_id, id_clie_responsavel)
                        VALUES (%s, %s, %s, %s, 'planejado', 'aula_eduscrum',
                                %s::jsonb, %s, %s::jsonb, %s::jsonb,
                                %s, %s, %s, %s,
                                %s, 'wizard_ia', %s, %s, %s)
                        RETURNING {SELECT_COLS}
                        """,
                        (
                            user["id_clie"],
                            data_evento,
                            titulo,
                            nota_final,
                            json.dumps(meta_final, ensure_ascii=False),
                            plano_session,
                            json.dumps(plan_data_obj, ensure_ascii=False)
                            if plan_data_obj is not None
                            else None,
                            json.dumps(kanban_state, ensure_ascii=False),
                            turma,
                            turno,
                            modo,
                            id_pai,
                            disciplina_id,
                            tema_obj,
                            desafio_id_criado,
                            user["id_clie"],
                        ),
                    )
                    row_ins = dict(cur.fetchone())
                    aula_id_novo = int(row_ins["id_evento"])

                    if modo == "continuidade" and prev_kanban is not None:
                        kanban_state = _kanban_continuidade_com_cards(
                            prev_kanban=prev_kanban,
                            plan_data_obj=plan_data_obj,
                            kanban_base_obj=kanban_base_obj,
                            card_ids=slot["card_ids"],
                            aula_id=aula_id_novo,
                            turma=turma,
                            escopos_by_card=slot["escopos_by_card"],
                        )
                    else:
                        kanban_state = _kanban_para_aula_com_cards(
                            plan_data_obj=plan_data_obj,
                            kanban_base_obj=kanban_base_obj,
                            card_ids=slot["card_ids"],
                            aula_id=aula_id_novo,
                            turma=turma,
                            escopos_by_card=slot["escopos_by_card"],
                        )

                    cur.execute(
                        f"""
                        UPDATE public.inove_agenda_eventos
                           SET kanban_state = %s::jsonb
                         WHERE id_evento = %s AND id_clie = %s
                        RETURNING {SELECT_COLS}
                        """,
                        (
                            json.dumps(kanban_state, ensure_ascii=False),
                            aula_id_novo,
                            user["id_clie"],
                        ),
                    )
                    criados.append(_serialize(dict(cur.fetchone())))
        return jsonify(
            {"success": True, "eventos": criados, "desafio_id": desafio_id_criado}
        ), 201
    except Exception as exc:
        print(f"⚠️ agenda registrar-aulas: {exc}", file=sys.stderr)
        err = str(exc)
        if "uq_inove_agenda_aula_dia_turma_turno" in err:
            return jsonify(
                {
                    "success": False,
                    "error": "Já existe aula neste dia para a mesma turma e turno.",
                }
            ), 409
        return jsonify({"success": False, "error": "Falha ao registrar aulas"}), 500


@agenda_bp.get("/api/agenda-eventos/<int:id_evento>/kanban")
def listar_kanban_desafio(id_evento: int):
    """
    Lista cards do desafio com aula_id anotado.
    Escopo: mesma plano_session (se houver) ∪ cadeia id_evento_pai.
    Query opcional: aula_id — filtra cards daquela aula (null = bucket geral).
    Sem aula_id: visão geral (todos os cards das aulas do desafio).
    """
    user = _require_user()
    if not user:
        return jsonify({"success": False, "error": "Não autenticado"}), 401

    aula_filtro_raw = (request.args.get("aula_id") or "").strip()
    aula_filtro = None
    if aula_filtro_raw:
        try:
            aula_filtro = int(aula_filtro_raw)
        except (TypeError, ValueError):
            return jsonify({"success": False, "error": "aula_id inválido"}), 400

    id_clie = user["id_clie"]
    try:
        with get_conn() as conn:
            _ensure_table(conn)
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    f"""
                    SELECT {SELECT_COLS}
                    FROM public.inove_agenda_eventos
                    WHERE id_evento = %s
                    """,
                    (id_evento,),
                )
                base = cur.fetchone()
                if not base:
                    return jsonify({"success": False, "error": "Evento não encontrado"}), 404
                base_d = dict(base)
                pode_ler, pode_editar = _can_access_evento(cur, id_clie, base_d)
                if not pode_ler:
                    return jsonify({"success": False, "error": "Evento não encontrado"}), 404

                owner_clie = int(base_d.get("id_clie") or id_clie)
                ids = set(_cadeia_evento_ids(cur, owner_clie, id_evento))
                plano_session = (base.get("plano_session") or "").strip() or None
                if plano_session:
                    cur.execute(
                        """
                        SELECT id_evento
                          FROM public.inove_agenda_eventos
                         WHERE id_clie = %s
                           AND plano_session = %s
                           AND tipo = 'aula_eduscrum'
                        """,
                        (owner_clie, plano_session),
                    )
                    ids.update(int(r["id_evento"]) for r in cur.fetchall())

                id_list = sorted(ids)
                cur.execute(
                    f"""
                    SELECT {SELECT_COLS}
                    FROM public.inove_agenda_eventos
                    WHERE id_clie = %s
                      AND id_evento = ANY(%s)
                    ORDER BY data_evento ASC, id_evento ASC
                    """,
                    (id_clie, id_list),
                )
                rows = [_serialize(dict(r)) for r in cur.fetchall()]

        aulas_out = []
        tarefas_all = []
        for ev in rows:
            aid = int(ev["id_evento"])
            stamped = _stamp_aula_id_on_tarefas(
                _tarefas_from_kanban(ev.get("kanban_state")),
                aid,
            )
            aulas_out.append(
                {
                    "id_evento": aid,
                    "titulo": ev.get("titulo"),
                    "data_evento": ev.get("data_evento"),
                    "turma": ev.get("turma"),
                    "turno": ev.get("turno"),
                    "status": ev.get("status"),
                    "modo_execucao": ev.get("modo_execucao"),
                    "id_evento_pai": ev.get("id_evento_pai"),
                }
            )
            for t in stamped:
                tarefas_all.append(t)

        if aula_filtro is not None:
            tarefas_all = [
                t
                for t in tarefas_all
                if t.get("aula_id") == aula_filtro
                or aula_filtro in _aula_ids_do_card(t)
                or (t.get("aula_id") is None and aula_filtro == id_evento)
            ]
            visao = "aula"
        else:
            # Mesmo card em várias turmas → um card com aula_ids + escopos_turma
            tarefas_all = _merge_tarefas_by_card_id(tarefas_all)
            visao = "todas"

        return jsonify(
            {
                "success": True,
                "visao": visao,
                "aula_id": aula_filtro,
                "aulas": aulas_out,
                "tarefas": tarefas_all,
                "pode_editar": pode_editar,
            }
        ), 200
    except Exception as exc:
        print(f"⚠️ agenda kanban: {exc}", file=sys.stderr)
        return jsonify({"success": False, "error": "Falha ao listar kanban do desafio"}), 500


@agenda_bp.put("/api/agenda-eventos/<int:id_evento>/estado")
def atualizar_estado(id_evento: int):
    """Persiste plan_data (plano IA) e/ou kanban_state (cards/colunas) do EduScrum."""
    user = _require_user()
    if not user:
        return jsonify({"success": False, "error": "Não autenticado"}), 401

    data = request.get_json(silent=True) or {}
    if "plan_data" not in data and "kanban_state" not in data:
        return (
            jsonify(
                {
                    "success": False,
                    "error": "Informe plan_data e/ou kanban_state no corpo JSON.",
                }
            ),
            400,
        )

    try:
        plan_data = _parse_jsonb(data["plan_data"]) if "plan_data" in data else None
        kanban_raw = data.get("kanban_state") if "kanban_state" in data else None
        # Carimba aula_id nos cards (default = evento sendo salvo); aceita override por card.
        if "kanban_state" in data:
            parsed_ks = kanban_raw
            if isinstance(kanban_raw, str) and kanban_raw.strip():
                try:
                    parsed_ks = json.loads(kanban_raw)
                except Exception as exc:
                    raise ValueError("kanban_state inválido") from exc
            normalized = _normalize_kanban_state(parsed_ks, id_evento)
            kanban_state = _parse_jsonb(normalized)
        else:
            kanban_state = None
    except ValueError as ve:
        return jsonify({"success": False, "error": str(ve)}), 400

    try:
        with get_conn() as conn:
            _ensure_table(conn)
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    f"""
                    SELECT {SELECT_COLS}
                    FROM public.inove_agenda_eventos
                    WHERE id_evento = %s
                    """,
                    (id_evento,),
                )
                atual = cur.fetchone()
                if not atual:
                    return jsonify({"success": False, "error": "Evento não encontrado"}), 404
                pode_ler, pode_editar = _can_access_evento(cur, user["id_clie"], dict(atual))
                if not pode_editar:
                    if pode_ler:
                        return jsonify(
                            {
                                "success": False,
                                "error": "Somente o responsável pela execução pode editar o Kanban.",
                            }
                        ), 403
                    return jsonify({"success": False, "error": "Evento não encontrado"}), 404

                # Bloqueia mudança de coluna se aulas vinculadas não estiverem concluídas
                if "kanban_state" in data and isinstance(kanban_state, dict):
                    prev_tarefas = {
                        str(t.get("id") or "").strip(): t
                        for t in _tarefas_from_kanban(_json_field(atual.get("kanban_state")))
                        if str(t.get("id") or "").strip()
                    }
                    for t_new in _tarefas_from_kanban(kanban_state):
                        tid = str(t_new.get("id") or "").strip()
                        if not tid:
                            continue
                        prev = prev_tarefas.get(tid) or {}
                        col_old = str(prev.get("coluna") or "para_fazer")
                        col_new = str(t_new.get("coluna") or "para_fazer")
                        if col_old == col_new:
                            continue
                        ok_move, err_move = _card_pode_mover(
                            cur,
                            int(atual["id_clie"]),
                            t_new,
                            dict(atual),
                            to_coluna=col_new,
                        )
                        if not ok_move:
                            return jsonify({"success": False, "error": err_move}), 400

                sets = []
                params = []
                if "plan_data" in data:
                    sets.append("plan_data = %s::jsonb")
                    params.append(plan_data)
                if "kanban_state" in data:
                    sets.append("kanban_state = %s::jsonb")
                    params.append(kanban_state)
                params.extend([id_evento, atual["id_clie"]])

                cur.execute(
                    f"""
                    UPDATE public.inove_agenda_eventos
                    SET {", ".join(sets)}
                    WHERE id_evento = %s AND id_clie = %s
                    RETURNING {SELECT_COLS}
                    """,
                    params,
                )
                row = cur.fetchone()
        return jsonify({"success": True, "evento": _serialize(dict(row))}), 200
    except Exception as exc:
        print(f"⚠️ agenda estado: {exc}", file=sys.stderr)
        return jsonify({"success": False, "error": "Falha ao atualizar estado da aula"}), 500


@agenda_bp.post("/api/agenda-eventos/<int:id_evento>/concluir-aula")
def concluir_aula(id_evento: int):
    """Fecha a aula com relato/participantes e opcionalmente cria evento filho vinculado."""
    user = _require_user()
    if not user:
        return jsonify({"success": False, "error": "Não autenticado"}), 401

    data = request.get_json(silent=True) or {}
    relato = (data.get("relato_sala") or "").strip()
    participantes = (data.get("participantes") or "").strip()
    if not relato:
        return jsonify({"success": False, "error": "Descreva o que houve na sala."}), 400
    if not participantes:
        return jsonify({"success": False, "error": "Informe quem participou."}), 400

    criar_proximo = bool(data.get("criar_proximo"))
    data_proximo = (data.get("data_proximo") or "").strip()
    titulo_proximo = (data.get("titulo_proximo") or "").strip()

    if criar_proximo and not data_proximo:
        return jsonify({"success": False, "error": "Informe a data do próximo evento."}), 400

    try:
        with get_conn() as conn:
            _ensure_table(conn)
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    f"""
                    SELECT {SELECT_COLS}
                    FROM public.inove_agenda_eventos
                    WHERE id_evento = %s AND id_clie = %s
                    """,
                    (id_evento, user["id_clie"]),
                )
                atual = cur.fetchone()
                if not atual:
                    return jsonify({"success": False, "error": "Evento não encontrado"}), 404

                nota = atual.get("nota_texto") or ""
                stamp = f"Concluída com relato em sala."
                nota_final = f"{nota}\n{stamp}".strip() if nota else stamp

                cur.execute(
                    f"""
                    UPDATE public.inove_agenda_eventos
                    SET status = 'concluido',
                        relato_sala = %s,
                        participantes = %s,
                        nota_texto = %s
                    WHERE id_evento = %s AND id_clie = %s
                    RETURNING {SELECT_COLS}
                    """,
                    (relato, participantes, nota_final, id_evento, user["id_clie"]),
                )
                concluido = _serialize(dict(cur.fetchone()))

                filho = None
                if criar_proximo:
                    dia = data_proximo[:10]
                    data_evento = f"{dia}T12:00:00"
                    titulo = titulo_proximo or f"Desdobramento · {atual['titulo']}"
                    titulo = titulo[:200]
                    cur.execute(
                        f"""
                        INSERT INTO public.inove_agenda_eventos
                            (id_clie, data_evento, titulo, nota_texto, status, tipo,
                             meta_json, plano_session, id_evento_pai)
                        VALUES (%s, %s, %s, %s, 'planejado', %s, %s::jsonb, %s, %s)
                        RETURNING {SELECT_COLS}
                        """,
                        (
                            user["id_clie"],
                            data_evento,
                            titulo,
                            f"Originado da aula #{id_evento}.",
                            atual.get("tipo") or "aula_eduscrum",
                            _parse_meta(atual.get("meta_json")),
                            atual.get("plano_session"),
                            id_evento,
                        ),
                    )
                    filho = _serialize(dict(cur.fetchone()))

        return jsonify({"success": True, "evento": concluido, "proximo": filho})
    except Exception as exc:
        print(f"⚠️ agenda concluir-aula: {exc}", file=sys.stderr)
        return jsonify({"success": False, "error": "Falha ao concluir a aula"}), 500


ENGAJAMENTO_OK = frozenset({"alto", "medio", "baixo"})
MAX_OBS_FEEDBACK = 8000
_feedback_ensured = False


def _ensure_aulas_feedback(conn) -> None:
    global _feedback_ensured
    if _feedback_ensured:
        return
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS public.inove_aulas_feedback (
                id                SERIAL PRIMARY KEY,
                id_evento         INTEGER NOT NULL
                    REFERENCES public.inove_agenda_eventos (id_evento) ON DELETE CASCADE,
                id_clie           INTEGER NOT NULL
                    REFERENCES public.ctdi_clie (id_clie) ON DELETE CASCADE,
                desafio_id        UUID,
                metodologia_ok    BOOLEAN NOT NULL,
                engajamento       VARCHAR(16) NOT NULL,
                estrutura_ok      BOOLEAN NOT NULL,
                observacoes       TEXT,
                criado_em         TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
            )
            """
        )
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_inove_aulas_feedback_evento
                ON public.inove_aulas_feedback (id_evento)
            """
        )
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_inove_aulas_feedback_clie
                ON public.inove_aulas_feedback (id_clie, criado_em DESC)
            """
        )
    _feedback_ensured = True


@agenda_bp.post("/api/agenda-eventos/<int:id_evento>/feedback")
def salvar_feedback_aula(id_evento: int):
    """Retroalimentação pós-aula (Feedback Loop) — dados estruturados + observações."""
    user = _require_user()
    if not user:
        return jsonify({"success": False, "error": "Não autenticado"}), 401

    data = request.get_json(silent=True) or {}
    if "metodologia_ok" not in data:
        return jsonify({"success": False, "error": "Informe se a sugestão metodológica funcionou."}), 400
    if "estrutura_ok" not in data:
        return jsonify({"success": False, "error": "Informe se a estrutura acomodou a sugestão."}), 400

    metodologia_ok = bool(data.get("metodologia_ok"))
    estrutura_ok = bool(data.get("estrutura_ok"))
    engajamento = str(data.get("engajamento") or "").strip().lower()
    if engajamento not in ENGAJAMENTO_OK:
        return (
            jsonify(
                {
                    "success": False,
                    "error": "Engajamento inválido. Use: alto, medio ou baixo.",
                }
            ),
            400,
        )
    observacoes = (data.get("observacoes") or "").strip()
    if len(observacoes) > MAX_OBS_FEEDBACK:
        observacoes = observacoes[:MAX_OBS_FEEDBACK]

    try:
        with get_conn() as conn:
            _ensure_table(conn)
            _ensure_aulas_feedback(conn)
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    f"""
                    SELECT {SELECT_COLS}
                    FROM public.inove_agenda_eventos
                    WHERE id_evento = %s AND id_clie = %s
                    """,
                    (id_evento, user["id_clie"]),
                )
                atual = cur.fetchone()
                if not atual:
                    return jsonify({"success": False, "error": "Evento não encontrado"}), 404

                pode_ler, pode_editar = _can_access_evento(cur, user["id_clie"], dict(atual))
                if not pode_editar:
                    if pode_ler:
                        return (
                            jsonify(
                                {
                                    "success": False,
                                    "error": "Somente o responsável pela execução pode registrar o feedback.",
                                }
                            ),
                            403,
                        )
                    return jsonify({"success": False, "error": "Evento não encontrado"}), 404

                desafio_id = atual.get("desafio_id")
                cur.execute(
                    """
                    INSERT INTO public.inove_aulas_feedback
                        (id_evento, id_clie, desafio_id, metodologia_ok,
                         engajamento, estrutura_ok, observacoes)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING id, id_evento, id_clie, desafio_id, metodologia_ok,
                              engajamento, estrutura_ok, observacoes, criado_em
                    """,
                    (
                        id_evento,
                        user["id_clie"],
                        desafio_id,
                        metodologia_ok,
                        engajamento,
                        estrutura_ok,
                        observacoes or None,
                    ),
                )
                row = dict(cur.fetchone())
                if row.get("desafio_id") is not None:
                    row["desafio_id"] = str(row["desafio_id"])
                if row.get("criado_em") is not None:
                    row["criado_em"] = row["criado_em"].isoformat()
                return jsonify({"success": True, "feedback": row})
    except Exception as exc:
        print(f"⚠️ agenda feedback-aula: {exc}", file=sys.stderr)
        return jsonify({"success": False, "error": "Falha ao salvar o feedback da aula"}), 500


@agenda_bp.route("/api/agenda-eventos/<int:id_evento>", methods=["GET", "PUT", "DELETE"])
def evento_detail(id_evento: int):
    user = _require_user()
    if not user:
        return jsonify({"success": False, "error": "Não autenticado"}), 401

    try:
        with get_conn() as conn:
            _ensure_table(conn)
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                if request.method == "GET":
                    cur.execute(
                        f"""
                        SELECT {SELECT_COLS}
                        FROM public.inove_agenda_eventos
                        WHERE id_evento = %s
                        """,
                        (id_evento,),
                    )
                    row = cur.fetchone()
                    if not row:
                        return jsonify({"success": False, "error": "Evento não encontrado"}), 404
                    pode_ler, pode_editar = _can_access_evento(cur, user["id_clie"], dict(row))
                    if not pode_ler:
                        return jsonify({"success": False, "error": "Evento não encontrado"}), 404
                    ev = _serialize(dict(row))
                    ev["pode_editar"] = pode_editar
                    ev["somente_leitura"] = not pode_editar
                    return jsonify({"success": True, "evento": ev})

                if request.method == "DELETE":
                    cur.execute(
                        f"""
                        SELECT {SELECT_COLS}
                        FROM public.inove_agenda_eventos
                        WHERE id_evento = %s
                        """,
                        (id_evento,),
                    )
                    row = cur.fetchone()
                    if not row:
                        return jsonify({"success": False, "error": "Evento não encontrado"}), 404
                    _pl, pode_editar = _can_access_evento(cur, user["id_clie"], dict(row))
                    if not pode_editar:
                        return jsonify({"success": False, "error": "Evento não encontrado"}), 404
                    cur.execute(
                        """
                        DELETE FROM public.inove_agenda_eventos
                        WHERE id_evento = %s AND id_clie = %s
                        """,
                        (id_evento, row["id_clie"]),
                    )
                    if cur.rowcount == 0:
                        return jsonify({"success": False, "error": "Evento não encontrado"}), 404
                    return jsonify({"success": True})

                data = request.get_json(silent=True) or {}
                cur.execute(
                    f"""
                    SELECT {SELECT_COLS}
                    FROM public.inove_agenda_eventos
                    WHERE id_evento = %s
                    """,
                    (id_evento,),
                )
                atual = cur.fetchone()
                if not atual:
                    return jsonify({"success": False, "error": "Evento não encontrado"}), 404
                _pl, pode_editar = _can_access_evento(cur, user["id_clie"], dict(atual))
                if not pode_editar:
                    return jsonify(
                        {
                            "success": False,
                            "error": "Somente o responsável pela execução pode alterar esta aula.",
                        }
                    ), 403

                titulo = (data.get("titulo") or atual["titulo"] or "").strip()
                if not titulo:
                    return jsonify({"success": False, "error": "titulo obrigatório"}), 400

                nota_texto = data.get("nota_texto")
                if nota_texto is not None:
                    nota_texto = str(nota_texto).strip() or None
                else:
                    nota_texto = atual.get("nota_texto")

                data_evento = data.get("data_evento") or atual["data_evento"]
                status = (data.get("status") or atual.get("status") or "planejado").strip().lower()
                if status not in STATUSES:
                    return jsonify({"success": False, "error": "status inválido"}), 400

                tipo = (data.get("tipo") or atual.get("tipo") or "geral").strip().lower()
                if tipo not in TIPOS:
                    return jsonify({"success": False, "error": "tipo inválido"}), 400

                relato = data.get("relato_sala")
                if relato is not None:
                    relato = str(relato).strip() or None
                else:
                    relato = atual.get("relato_sala")

                participantes = data.get("participantes")
                if participantes is not None:
                    participantes = str(participantes).strip() or None
                else:
                    participantes = atual.get("participantes")

                plano_session = data.get("plano_session")
                if plano_session is not None:
                    plano_session = str(plano_session).strip() or None
                else:
                    plano_session = atual.get("plano_session")

                cur.execute(
                    f"""
                    UPDATE public.inove_agenda_eventos
                    SET titulo = %s,
                        nota_texto = %s,
                        data_evento = %s,
                        status = %s,
                        tipo = %s,
                        relato_sala = %s,
                        participantes = %s,
                        plano_session = %s
                    WHERE id_evento = %s AND id_clie = %s
                    RETURNING {SELECT_COLS}
                    """,
                    (
                        titulo[:200],
                        nota_texto,
                        data_evento,
                        status,
                        tipo,
                        relato,
                        participantes,
                        plano_session,
                        id_evento,
                        atual["id_clie"],
                    ),
                )
                row = cur.fetchone()
                return jsonify({"success": True, "evento": _serialize(dict(row))})
    except Exception as exc:
        print(f"⚠️ agenda detail: {exc}", file=sys.stderr)
        return jsonify({"success": False, "error": "Falha na operação da agenda"}), 500

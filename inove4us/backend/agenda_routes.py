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
    turma, turno, modo_execucao
"""


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
    _ensured = True


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
                    SELECT {SELECT_COLS}
                    FROM public.inove_agenda_eventos
                    WHERE id_clie = %s
                """
                params = [user["id_clie"]]
                if mes:
                    sql += " AND to_char(data_evento, 'YYYY-MM') = %s"
                    params.append(mes)
                if plano_session:
                    sql += " AND plano_session = %s"
                    params.append(plano_session)
                sql += " ORDER BY data_evento ASC, id_evento ASC"
                cur.execute(sql, params)
                rows = [_serialize(dict(r)) for r in cur.fetchall()]
        return jsonify({"success": True, "eventos": rows})
    except Exception as exc:
        print(f"⚠️ agenda list: {exc}", file=sys.stderr)
        return jsonify({"success": False, "error": "Falha ao listar agenda"}), 500


@agenda_bp.get("/api/agenda-eventos/grafo")
def grafo_realizacoes():
    """Nós e arestas para o mapa de realizações (eventos vinculados)."""
    user = _require_user()
    if not user:
        return jsonify({"success": False, "error": "Não autenticado"}), 401

    try:
        with get_conn() as conn:
            _ensure_table(conn)
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    f"""
                    SELECT {SELECT_COLS}
                    FROM public.inove_agenda_eventos
                    WHERE id_clie = %s
                    ORDER BY data_evento ASC, id_evento ASC
                    """,
                    (user["id_clie"],),
                )
                rows = [_serialize(dict(r)) for r in cur.fetchall()]

        nodes = []
        edges = []
        for r in rows:
            nodes.append(
                {
                    "id": r["id_evento"],
                    "titulo": r["titulo"],
                    "status": r.get("status") or "planejado",
                    "tipo": r.get("tipo") or "geral",
                    "data_evento": r.get("data_evento"),
                    "id_evento_pai": r.get("id_evento_pai"),
                    "tem_relato": bool((r.get("relato_sala") or "").strip()),
                    "relato_sala": r.get("relato_sala") or "",
                    "participantes": r.get("participantes") or "",
                }
            )
            if r.get("id_evento_pai"):
                edges.append(
                    {
                        "from": r["id_evento_pai"],
                        "to": r["id_evento"],
                        "kind": "desdobramento",
                    }
                )
        return jsonify({"success": True, "nodes": nodes, "edges": edges})
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

    try:
        with get_conn() as conn:
            _ensure_table(conn)
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    f"""
                    INSERT INTO public.inove_agenda_eventos
                        (id_clie, data_evento, titulo, nota_texto, status, tipo,
                         meta_json, plano_session, id_evento_pai)
                    VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s)
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
        seen.add(key)
        slots.append({"data": dia, "turma": turma[:120], "turno": turno, "modo_execucao": modo})

    criados = []
    try:
        with get_conn() as conn:
            _ensure_table(conn)
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
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

                    if modo == "continuidade":
                        cur.execute(
                            f"""
                            SELECT {SELECT_COLS}
                            FROM public.inove_agenda_eventos
                            WHERE id_clie = %s
                              AND tipo = 'aula_eduscrum'
                              AND lower(trim(turma)) = lower(trim(%s))
                              AND (%s::text IS NULL OR plano_session = %s)
                            ORDER BY data_evento DESC, id_evento DESC
                            LIMIT 1
                            """,
                            (user["id_clie"], turma, plano_session, plano_session),
                        )
                        prev = cur.fetchone()
                        if prev and prev.get("kanban_state") is not None:
                            kanban_state = _json_field(prev.get("kanban_state"))
                        else:
                            kanban_state = (
                                kanban_base_obj
                                if isinstance(kanban_base_obj, (dict, list))
                                else _fresh_kanban_from_plan(plan_data_obj, kanban_base_obj)
                            )
                        if isinstance(kanban_state, list):
                            kanban_state = {"tarefas": kanban_state}
                        id_pai = prev["id_evento"] if prev else None
                    else:
                        kanban_state = _fresh_kanban_from_plan(plan_data_obj, kanban_base_obj)
                        id_pai = None

                    titulo = f"{titulo_base} · {turma} · {_turno_label(turno)}"[:200]
                    nota_parts = [
                        nota_texto,
                        f"Turma: {turma}",
                        f"Turno: {_turno_label(turno)}",
                        f"Modo: {_modo_label(modo)}",
                    ]
                    nota_final = "\n".join(p for p in nota_parts if p)

                    meta_final = {
                        **meta_obj,
                        "turma": turma,
                        "turno": turno,
                        "modo_execucao": modo,
                        "modo_label": _modo_label(modo),
                    }

                    cur.execute(
                        f"""
                        INSERT INTO public.inove_agenda_eventos
                            (id_clie, data_evento, titulo, nota_texto, status, tipo,
                             meta_json, plano_session, plan_data, kanban_state,
                             turma, turno, modo_execucao, id_evento_pai)
                        VALUES (%s, %s, %s, %s, 'planejado', 'aula_eduscrum',
                                %s::jsonb, %s, %s::jsonb, %s::jsonb,
                                %s, %s, %s, %s)
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
                            json.dumps(kanban_state, ensure_ascii=False)
                            if kanban_state is not None
                            else None,
                            turma,
                            turno,
                            modo,
                            id_pai,
                        ),
                    )
                    criados.append(_serialize(dict(cur.fetchone())))
        return jsonify({"success": True, "eventos": criados}), 201
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
        kanban_state = _parse_jsonb(data["kanban_state"]) if "kanban_state" in data else None
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
                    WHERE id_evento = %s AND id_clie = %s
                    """,
                    (id_evento, user["id_clie"]),
                )
                atual = cur.fetchone()
                if not atual:
                    return jsonify({"success": False, "error": "Evento não encontrado"}), 404

                sets = []
                params = []
                if "plan_data" in data:
                    sets.append("plan_data = %s::jsonb")
                    params.append(plan_data)
                if "kanban_state" in data:
                    sets.append("kanban_state = %s::jsonb")
                    params.append(kanban_state)
                params.extend([id_evento, user["id_clie"]])

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
                        WHERE id_evento = %s AND id_clie = %s
                        """,
                        (id_evento, user["id_clie"]),
                    )
                    row = cur.fetchone()
                    if not row:
                        return jsonify({"success": False, "error": "Evento não encontrado"}), 404
                    return jsonify({"success": True, "evento": _serialize(dict(row))})

                if request.method == "DELETE":
                    cur.execute(
                        """
                        DELETE FROM public.inove_agenda_eventos
                        WHERE id_evento = %s AND id_clie = %s
                        """,
                        (id_evento, user["id_clie"]),
                    )
                    if cur.rowcount == 0:
                        return jsonify({"success": False, "error": "Evento não encontrado"}), 404
                    return jsonify({"success": True})

                data = request.get_json(silent=True) or {}
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
                        user["id_clie"],
                    ),
                )
                row = cur.fetchone()
                return jsonify({"success": True, "evento": _serialize(dict(row))})
    except Exception as exc:
        print(f"⚠️ agenda detail: {exc}", file=sys.stderr)
        return jsonify({"success": False, "error": "Falha na operação da agenda"}), 500

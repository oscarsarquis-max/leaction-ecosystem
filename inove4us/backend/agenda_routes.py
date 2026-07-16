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
TIPOS = frozenset({"geral", "aula_eduscrum"})

SELECT_COLS = """
    id_evento, id_clie, data_evento, titulo, nota_texto, criado_em,
    status, tipo, meta_json, plano_session,
    id_evento_pai, relato_sala, participantes
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

            CREATE INDEX IF NOT EXISTS idx_inove_agenda_eventos_session
                ON public.inove_agenda_eventos (id_clie, plano_session);
            CREATE INDEX IF NOT EXISTS idx_inove_agenda_eventos_pai
                ON public.inove_agenda_eventos (id_evento_pai);
            """
        )
    _ensured = True


def _serialize(row: dict) -> dict:
    out = dict(row)
    if out.get("data_evento"):
        out["data_evento"] = out["data_evento"].isoformat()
    if out.get("criado_em"):
        out["criado_em"] = out["criado_em"].isoformat()
    meta = out.get("meta_json")
    if meta is not None and not isinstance(meta, (dict, list)):
        try:
            out["meta_json"] = json.loads(meta)
        except Exception:
            out["meta_json"] = None
    return out


def _parse_meta(value):
    if value is None:
        return None
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


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


@agenda_bp.post("/api/agenda-eventos/registrar-aulas")
def registrar_aulas():
    user = _require_user()
    if not user:
        return jsonify({"success": False, "error": "Não autenticado"}), 401

    data = request.get_json(silent=True) or {}
    datas = data.get("datas") or []
    if isinstance(datas, str):
        datas = [datas]
    datas = [str(d).strip()[:10] for d in datas if str(d).strip()]
    if not datas:
        return jsonify({"success": False, "error": "Informe ao menos uma data"}), 400

    titulo_base = (data.get("titulo") or "Aula EduScrum").strip()[:180]
    nota_texto = (data.get("nota_texto") or "").strip() or None
    plano_session = (data.get("plano_session") or "").strip() or None
    meta_json = _parse_meta(data.get("meta_json"))

    criados = []
    try:
        with get_conn() as conn:
            _ensure_table(conn)
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                for dia in datas:
                    data_evento = f"{dia}T12:00:00" if "T" not in dia else dia
                    cur.execute(
                        f"""
                        INSERT INTO public.inove_agenda_eventos
                            (id_clie, data_evento, titulo, nota_texto, status, tipo,
                             meta_json, plano_session)
                        VALUES (%s, %s, %s, %s, 'planejado', 'aula_eduscrum', %s::jsonb, %s)
                        RETURNING {SELECT_COLS}
                        """,
                        (
                            user["id_clie"],
                            data_evento,
                            titulo_base[:200],
                            nota_texto,
                            meta_json,
                            plano_session,
                        ),
                    )
                    criados.append(_serialize(dict(cur.fetchone())))
        return jsonify({"success": True, "eventos": criados}), 201
    except Exception as exc:
        print(f"⚠️ agenda registrar-aulas: {exc}", file=sys.stderr)
        return jsonify({"success": False, "error": "Falha ao registrar aulas"}), 500


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

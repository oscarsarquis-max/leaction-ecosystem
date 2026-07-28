"""Desafios — conteúdo canônico + replicação por turma (sem IA)."""

from __future__ import annotations

import copy
import json
import os
import secrets
import sys
import uuid
from collections import defaultdict

from flask import Blueprint, jsonify, request, session
from psycopg2.extras import RealDictCursor

from db import get_conn
from mail import send_desafio_convite_email

desafios_bp = Blueprint("desafios", __name__)

_ensured = False

TURNOS = frozenset({"manha", "tarde", "noite"})
TURNO_HORA = {
    "manha": "08:00:00",
    "tarde": "14:00:00",
    "noite": "19:00:00",
}
MODOS = frozenset({"continuidade", "reinicio"})

SELECT_EVENTO = """
    id_evento, id_clie, data_evento, titulo, nota_texto, criado_em,
    status, tipo, meta_json, plano_session,
    id_evento_pai, relato_sala, participantes,
    plan_data, kanban_state,
    turma, turno, modo_execucao,
    disciplina_id, origem, id_externo_importacao, tema, desafio_id,
    id_clie_responsavel
"""


def _require_user():
    user = session.get("user")
    if not user or not user.get("id_clie"):
        return None
    return user


def _json_field(value):
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


def _serialize_evento(row: dict) -> dict:
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


def _serialize_desafio(row: dict) -> dict:
    out = dict(row)
    if out.get("criado_em"):
        out["criado_em"] = out["criado_em"].isoformat()
    out["id"] = str(out["id"])
    for key in ("causas", "plan_data", "meta_json"):
        out[key] = _json_field(out.get(key))
    return out


def _ensure_desafios_schema(conn) -> None:
    global _ensured
    if _ensured:
        return
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS public.inove_desafios (
                id              UUID PRIMARY KEY,
                id_clie         INTEGER NOT NULL
                    REFERENCES public.ctdi_clie (id_clie) ON DELETE CASCADE,
                titulo          VARCHAR(200),
                problema        TEXT,
                hipotese        TEXT,
                causas          JSONB,
                tema            VARCHAR(200),
                plan_data       JSONB,
                meta_json       JSONB,
                disciplina_id   BIGINT,
                criado_em       TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_inove_desafios_clie
                ON public.inove_desafios (id_clie, criado_em DESC);

            ALTER TABLE public.inove_agenda_eventos
                ADD COLUMN IF NOT EXISTS desafio_id UUID
                    REFERENCES public.inove_desafios (id) ON DELETE SET NULL;
            CREATE INDEX IF NOT EXISTS idx_inove_agenda_eventos_desafio
                ON public.inove_agenda_eventos (desafio_id)
                WHERE desafio_id IS NOT NULL;

            ALTER TABLE public.inove_agenda_eventos
                ADD COLUMN IF NOT EXISTS id_clie_responsavel INTEGER
                    REFERENCES public.ctdi_clie (id_clie) ON DELETE SET NULL;
            UPDATE public.inove_agenda_eventos
               SET id_clie_responsavel = id_clie
             WHERE id_clie_responsavel IS NULL;
            CREATE INDEX IF NOT EXISTS idx_inove_agenda_eventos_responsavel
                ON public.inove_agenda_eventos (id_clie_responsavel)
                WHERE id_clie_responsavel IS NOT NULL;

            CREATE TABLE IF NOT EXISTS public.inove_desafio_colaboradores (
                id                  BIGSERIAL PRIMARY KEY,
                desafio_id          UUID NOT NULL
                    REFERENCES public.inove_desafios (id) ON DELETE CASCADE,
                email_convidado     VARCHAR(320) NOT NULL,
                id_clie_convidado   INTEGER
                    REFERENCES public.ctdi_clie (id_clie) ON DELETE SET NULL,
                papel_ou_parte      VARCHAR(200),
                token_convite       VARCHAR(64) NOT NULL,
                status              VARCHAR(20) NOT NULL DEFAULT 'pendente'
                    CHECK (status IN ('pendente', 'aceito', 'recusado')),
                convidado_por       INTEGER NOT NULL
                    REFERENCES public.ctdi_clie (id_clie) ON DELETE CASCADE,
                criado_em           TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
                aceito_em           TIMESTAMP WITHOUT TIME ZONE
            );
            CREATE UNIQUE INDEX IF NOT EXISTS uq_inove_desafio_colab_token
                ON public.inove_desafio_colaboradores (token_convite);
            CREATE INDEX IF NOT EXISTS idx_inove_desafio_colab_desafio
                ON public.inove_desafio_colaboradores (desafio_id, status);
            """
        )
    _ensured = True


def _papel_acesso_desafio(cur, desafio_id: str, id_clie: int) -> tuple[str | None, dict | None]:
    """
    Retorna ('dono'|'colaborador'|None, desafio_row).
    Colaborador = convite aceito para este id_clie ou e-mail da conta.
    """
    cur.execute(
        """
        SELECT d.*, c.nome_clie AS dono_nome, c.mail_clie AS dono_email
          FROM public.inove_desafios d
          LEFT JOIN public.ctdi_clie c ON c.id_clie = d.id_clie
         WHERE d.id = %s
        """,
        (desafio_id,),
    )
    desafio = cur.fetchone()
    if not desafio:
        return None, None
    desafio = dict(desafio)
    if int(desafio["id_clie"]) == int(id_clie):
        return "dono", desafio

    cur.execute(
        """
        SELECT mail_clie FROM public.ctdi_clie WHERE id_clie = %s
        """,
        (id_clie,),
    )
    me = cur.fetchone()
    email = (me["mail_clie"] if me else "") or ""
    email = email.strip().lower()

    cur.execute(
        """
        SELECT id, status, papel_ou_parte, email_convidado, id_clie_convidado
          FROM public.inove_desafio_colaboradores
         WHERE desafio_id = %s
           AND status = 'aceito'
           AND (
                id_clie_convidado = %s
                OR lower(trim(email_convidado)) = %s
           )
         LIMIT 1
        """,
        (desafio_id, id_clie, email),
    )
    colab = cur.fetchone()
    if colab:
        return "colaborador", desafio
    return None, desafio


def _responsavel_evento(ev: dict) -> int | None:
    raw = ev.get("id_clie_responsavel")
    if raw is None:
        raw = ev.get("id_clie")
    try:
        return int(raw) if raw is not None else None
    except (TypeError, ValueError):
        return None


def _cliente_resumo(cur, id_clie: int | None) -> dict | None:
    if id_clie is None:
        return None
    cur.execute(
        """
        SELECT id_clie, nome_clie, mail_clie
          FROM public.ctdi_clie WHERE id_clie = %s
        """,
        (id_clie,),
    )
    row = cur.fetchone()
    if not row:
        return {"id_clie": id_clie, "nome_clie": None, "mail_clie": None}
    return {
        "id_clie": int(row["id_clie"]),
        "nome_clie": row.get("nome_clie"),
        "mail_clie": row.get("mail_clie"),
    }

def _turno_label(turno: str) -> str:
    return {"manha": "Manhã", "tarde": "Tarde", "noite": "Noite"}.get(turno, turno)


def _fresh_kanban_from_plan(plan_data, kanban_base=None):
    if isinstance(kanban_base, dict) and isinstance(kanban_base.get("tarefas"), list):
        tarefas = []
        for t in kanban_base["tarefas"]:
            if not isinstance(t, dict):
                continue
            item = dict(t)
            item["coluna"] = "para_fazer"
            item.pop("historico", None)
            item.pop("ultima_observacao", None)
            item.pop("aula_id", None)
            tarefas.append(item)
        return {"tarefas": tarefas}
    if isinstance(kanban_base, list):
        return _fresh_kanban_from_plan(plan_data, {"tarefas": kanban_base})
    plano = None
    if isinstance(plan_data, dict):
        plano = plan_data.get("plano") or plan_data.get("plano_eduscrum")
    if isinstance(plano, dict) and isinstance(plano.get("tarefas_kanban"), list):
        return _fresh_kanban_from_plan(plan_data, {"tarefas": plano["tarefas_kanban"]})
    return {"tarefas": []}


def _cadeia_ids(cur, id_clie: int, id_evento: int) -> list[int]:
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
    root = int(current)
    ids: set[int] = {root}
    frontier = [root]
    while frontier:
        cur.execute(
            """
            SELECT id_evento FROM public.inove_agenda_eventos
             WHERE id_clie = %s AND id_evento_pai = ANY(%s)
            """,
            (id_clie, frontier),
        )
        kids = [int(r["id_evento"]) for r in cur.fetchall()]
        frontier = [k for k in kids if k not in ids]
        ids.update(frontier)
    return sorted(ids)


def _progresso_eventos(eventos: list[dict]) -> dict:
    n = len(eventos)
    por_status = defaultdict(int)
    for e in eventos:
        por_status[str(e.get("status") or "planejado")] += 1
    cards_total = 0
    cards_pronto = 0
    for e in eventos:
        ks = e.get("kanban_state")
        tarefas = []
        if isinstance(ks, dict) and isinstance(ks.get("tarefas"), list):
            tarefas = ks["tarefas"]
        elif isinstance(ks, list):
            tarefas = ks
        for t in tarefas:
            if not isinstance(t, dict):
                continue
            cards_total += 1
            if t.get("coluna") == "pronto":
                cards_pronto += 1
    pct = int(round(100 * cards_pronto / cards_total)) if cards_total else 0
    if not cards_total and n:
        pct = int(round(100 * por_status.get("concluido", 0) / n))
    return {
        "n_aulas": n,
        "n_planejado": por_status.get("planejado", 0),
        "n_em_execucao": por_status.get("em_execucao", 0),
        "n_concluido": por_status.get("concluido", 0),
        "cards_total": cards_total,
        "cards_pronto": cards_pronto,
        "progresso_pct": pct,
    }


def _ensure_desafio_from_evento(cur, id_clie: int, evento: dict) -> dict:
    """
    Garante registro inove_desafios para o evento (lazy backfill).
    Retorna o row do desafio.
    """
    existing = evento.get("desafio_id")
    if existing:
        cur.execute(
            """
            SELECT * FROM public.inove_desafios
             WHERE id = %s AND id_clie = %s
            """,
            (str(existing), id_clie),
        )
        row = cur.fetchone()
        if row:
            return dict(row)

    plan = _json_field(evento.get("plan_data")) or {}
    meta = _json_field(evento.get("meta_json")) or {}
    hipotese = (
        (plan.get("hipotese") if isinstance(plan, dict) else None)
        or (plan.get("hipotese_teste") if isinstance(plan, dict) else None)
        or meta.get("hipotese")
        or ""
    )
    problema = (
        (plan.get("problema") if isinstance(plan, dict) else None)
        or meta.get("problema")
        or ""
    )
    causas = None
    if isinstance(plan, dict) and plan.get("causas") is not None:
        causas = plan.get("causas")
    elif meta.get("causas") is not None:
        causas = meta.get("causas")
    tema = evento.get("tema") or meta.get("tema")
    titulo = (evento.get("titulo") or "Desafio")[:200]
    disciplina_id = evento.get("disciplina_id")
    desafio_id = str(uuid.uuid4())

    cur.execute(
        """
        INSERT INTO public.inove_desafios
            (id, id_clie, titulo, problema, hipotese, causas, tema,
             plan_data, meta_json, disciplina_id)
        VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s, %s::jsonb, %s::jsonb, %s)
        RETURNING *
        """,
        (
            desafio_id,
            id_clie,
            titulo,
            problema or None,
            hipotese or None,
            json.dumps(causas, ensure_ascii=False) if causas is not None else None,
            (str(tema)[:200] if tema else None),
            json.dumps(plan, ensure_ascii=False) if plan else None,
            json.dumps(meta, ensure_ascii=False) if meta else None,
            disciplina_id,
        ),
    )
    desafio = dict(cur.fetchone())

    # Estampa em toda a execução (session ∪ cadeia)
    ids = set(_cadeia_ids(cur, id_clie, int(evento["id_evento"])))
    session_key = (evento.get("plano_session") or "").strip() or None
    if session_key:
        cur.execute(
            """
            SELECT id_evento FROM public.inove_agenda_eventos
             WHERE id_clie = %s AND plano_session = %s AND tipo = 'aula_eduscrum'
            """,
            (id_clie, session_key),
        )
        ids.update(int(r["id_evento"]) for r in cur.fetchall())
    if ids:
        cur.execute(
            """
            UPDATE public.inove_agenda_eventos
               SET desafio_id = %s
             WHERE id_clie = %s
               AND id_evento = ANY(%s)
               AND desafio_id IS NULL
            """,
            (desafio_id, id_clie, sorted(ids)),
        )
    return desafio


def create_desafio_row(
    cur,
    *,
    id_clie: int,
    titulo: str | None,
    problema: str | None,
    hipotese: str | None,
    causas,
    tema: str | None,
    plan_data,
    meta_json,
    disciplina_id,
) -> dict:
    desafio_id = str(uuid.uuid4())
    cur.execute(
        """
        INSERT INTO public.inove_desafios
            (id, id_clie, titulo, problema, hipotese, causas, tema,
             plan_data, meta_json, disciplina_id)
        VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s, %s::jsonb, %s::jsonb, %s)
        RETURNING *
        """,
        (
            desafio_id,
            id_clie,
            (titulo or "Desafio")[:200],
            problema,
            hipotese,
            json.dumps(causas, ensure_ascii=False) if causas is not None else None,
            (str(tema)[:200] if tema else None),
            json.dumps(plan_data, ensure_ascii=False) if plan_data is not None else None,
            json.dumps(meta_json, ensure_ascii=False) if meta_json is not None else None,
            disciplina_id,
        ),
    )
    return dict(cur.fetchone())


@desafios_bp.get("/api/desafios/<desafio_id>")
def get_desafio(desafio_id: str):
    user = _require_user()
    if not user:
        return jsonify({"success": False, "error": "Não autenticado"}), 401
    try:
        uuid.UUID(str(desafio_id))
    except ValueError:
        return jsonify({"success": False, "error": "desafio_id inválido"}), 400

    try:
        with get_conn() as conn:
            _ensure_desafios_schema(conn)
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                papel, desafio = _papel_acesso_desafio(cur, desafio_id, user["id_clie"])
                if papel is None or not desafio:
                    return jsonify({"success": False, "error": "Desafio não encontrado"}), 404
        out = _serialize_desafio(desafio)
        out["papel_usuario"] = papel
        out["sou_dono"] = papel == "dono"
        return jsonify({"success": True, "desafio": out}), 200
    except Exception as exc:
        print(f"⚠️ desafios get: {exc}", file=sys.stderr)
        return jsonify({"success": False, "error": "Falha ao carregar desafio"}), 500


@desafios_bp.get("/api/agenda-eventos/<int:id_evento>/desafio")
def desafio_do_evento(id_evento: int):
    """Resolve/cria desafio a partir de um evento (backfill lazy)."""
    user = _require_user()
    if not user:
        return jsonify({"success": False, "error": "Não autenticado"}), 401
    id_clie = user["id_clie"]
    try:
        with get_conn() as conn:
            _ensure_desafios_schema(conn)
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    f"""
                    SELECT {SELECT_EVENTO}
                      FROM public.inove_agenda_eventos
                     WHERE id_evento = %s
                    """,
                    (id_evento,),
                )
                ev = cur.fetchone()
                if not ev:
                    return jsonify({"success": False, "error": "Evento não encontrado"}), 404
                ev = dict(ev)

                # Leitura: dono da aula, dono do desafio, ou colaborador aceito
                pode = int(ev.get("id_clie") or 0) == int(id_clie)
                desafio = None
                papel = None
                if ev.get("desafio_id"):
                    papel, desafio = _papel_acesso_desafio(cur, str(ev["desafio_id"]), id_clie)
                    if papel:
                        pode = True
                if not pode:
                    return jsonify({"success": False, "error": "Evento não encontrado"}), 404

                if not desafio:
                    # Só o responsável/dono da aula pode criar backfill
                    if int(ev.get("id_clie") or 0) != int(id_clie):
                        return jsonify({"success": False, "error": "Evento não encontrado"}), 404
                    desafio = _ensure_desafio_from_evento(cur, id_clie, ev)
                    papel = "dono"
                else:
                    papel = papel or (
                        "dono" if int(desafio["id_clie"]) == int(id_clie) else "colaborador"
                    )

        out = _serialize_desafio(desafio)
        out["papel_usuario"] = papel
        out["sou_dono"] = papel == "dono"
        return jsonify({"success": True, "desafio": out}), 200
    except Exception as exc:
        print(f"⚠️ desafios from evento: {exc}", file=sys.stderr)
        return jsonify({"success": False, "error": "Falha ao resolver desafio"}), 500


@desafios_bp.get("/api/desafios/<desafio_id>/execucoes")
def listar_execucoes(desafio_id: str):
    """Lista execuções do desafio com responsável e progresso."""
    user = _require_user()
    if not user:
        return jsonify({"success": False, "error": "Não autenticado"}), 401
    try:
        uuid.UUID(str(desafio_id))
    except ValueError:
        return jsonify({"success": False, "error": "desafio_id inválido"}), 400

    id_clie = user["id_clie"]
    try:
        with get_conn() as conn:
            _ensure_desafios_schema(conn)
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                papel, desafio = _papel_acesso_desafio(cur, desafio_id, id_clie)
                if papel is None or not desafio:
                    return jsonify({"success": False, "error": "Desafio não encontrado"}), 404

                # Todas as aulas do desafio (dono + colaboradores)
                cur.execute(
                    f"""
                    SELECT {SELECT_EVENTO}
                      FROM public.inove_agenda_eventos
                     WHERE desafio_id = %s
                       AND tipo = 'aula_eduscrum'
                     ORDER BY data_evento ASC, id_evento ASC
                    """,
                    (desafio_id,),
                )
                rows = [_serialize_evento(dict(r)) for r in cur.fetchall()]

                by_session: dict[str, list] = defaultdict(list)
                for ev in rows:
                    key = (ev.get("plano_session") or "").strip() or f"evt-{ev['id_evento']}"
                    by_session[key].append(ev)

                execucoes = []
                for session_key, eventos in by_session.items():
                    turmas = sorted(
                        {(e.get("turma") or "").strip() for e in eventos if (e.get("turma") or "").strip()}
                    )
                    turnos = sorted(
                        {(e.get("turno") or "").strip() for e in eventos if (e.get("turno") or "").strip()}
                    )
                    anchor = next(
                        (e for e in eventos if e.get("status") in ("em_execucao", "planejado")),
                        eventos[0],
                    )
                    resp_id = _responsavel_evento(anchor) or _responsavel_evento(eventos[0])
                    resp = _cliente_resumo(cur, resp_id)
                    eh_dono_desafio = resp_id is not None and int(resp_id) == int(desafio["id_clie"])
                    eh_minha = resp_id is not None and int(resp_id) == int(id_clie)
                    # Dono abre qualquer; colaborador só a própria
                    pode_abrir = eh_minha or papel == "dono"
                    pode_editar = eh_minha
                    prog = _progresso_eventos(eventos)

                    aulas_out = []
                    for e in eventos:
                        item = {
                            "id_evento": e["id_evento"],
                            "titulo": e.get("titulo"),
                            "data_evento": e.get("data_evento"),
                            "turma": e.get("turma"),
                            "turno": e.get("turno"),
                            "status": e.get("status"),
                            "modo_execucao": e.get("modo_execucao"),
                        }
                        aulas_out.append(item)

                    execucoes.append(
                        {
                            "plano_session": session_key if not session_key.startswith("evt-") else None,
                            "execucao_key": session_key,
                            "turma": turmas[0] if len(turmas) == 1 else (", ".join(turmas) if turmas else None),
                            "turmas": turmas,
                            "turno": turnos[0] if len(turnos) == 1 else None,
                            "turnos": turnos,
                            "id_evento_ancora": anchor["id_evento"] if pode_abrir else None,
                            "aulas": aulas_out if pode_abrir else [],
                            "responsavel": resp,
                            "eh_dono_desafio": eh_dono_desafio,
                            "eh_colaborador": not eh_dono_desafio,
                            "eh_minha": eh_minha,
                            "pode_abrir_kanban": pode_abrir,
                            "pode_editar": pode_editar,
                            **prog,
                        }
                    )

        execucoes.sort(key=lambda x: (x.get("aulas") or [{}] or [{}])[0].get("data_evento") or "")
        # fix sort when aulas empty — use progresso only
        execucoes.sort(
            key=lambda x: (
                (x.get("aulas") or [{}])[0].get("data_evento")
                if x.get("aulas")
                else ""
            )
            or ""
        )

        d_out = _serialize_desafio(dict(desafio))
        d_out["papel_usuario"] = papel
        d_out["sou_dono"] = papel == "dono"
        return jsonify(
            {
                "success": True,
                "desafio": d_out,
                "execucoes": execucoes,
            }
        ), 200
    except Exception as exc:
        print(f"⚠️ desafios execucoes: {exc}", file=sys.stderr)
        return jsonify({"success": False, "error": "Falha ao listar execuções"}), 500


@desafios_bp.post("/api/desafios/<desafio_id>/replicar")
def replicar_desafio(desafio_id: str):
    """
    Cria nova execução (nova plano_session + cadeia) para outra turma.
    Copia hipótese/causas/tema/plano do desafio — **não chama IA**.
    """
    user = _require_user()
    if not user:
        return jsonify({"success": False, "error": "Não autenticado"}), 401
    try:
        uuid.UUID(str(desafio_id))
    except ValueError:
        return jsonify({"success": False, "error": "desafio_id inválido"}), 400

    data = request.get_json(silent=True) or {}
    turma = str(data.get("turma") or "").strip()
    if not turma:
        return jsonify({"success": False, "error": "Informe a turma de destino."}), 400

    turno_padrao = str(data.get("turno") or "manha").strip().lower()
    if turno_padrao not in TURNOS:
        return jsonify({"success": False, "error": "Turno inválido (manha, tarde ou noite)."}), 400

    aulas_in = data.get("aulas")
    if not isinstance(aulas_in, list) or not aulas_in:
        return jsonify({"success": False, "error": "Informe ao menos uma aula com data."}), 400

    disciplina_raw = data.get("disciplina_id")
    if disciplina_raw in ("", None):
        disciplina_raw = None

    id_clie = user["id_clie"]
    nova_session = str(uuid.uuid4())

    try:
        with get_conn() as conn:
            _ensure_desafios_schema(conn)
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                papel, desafio = _papel_acesso_desafio(cur, desafio_id, id_clie)
                if papel is None or not desafio:
                    return jsonify({"success": False, "error": "Desafio não encontrado"}), 404
                # dono e colaborador aceito podem criar execução própria
                # (meta do desafio permanece do dono — só leitura de conteúdo)

                disciplina_id = desafio.get("disciplina_id")
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
                        (disciplina_id, id_clie),
                    )
                    if not cur.fetchone():
                        return jsonify(
                            {"success": False, "error": "Disciplina não encontrada ou sem permissão"}
                        ), 404

                plan_data = _json_field(desafio.get("plan_data")) or {}
                if not isinstance(plan_data, dict):
                    plan_data = {}
                plan_data = copy.deepcopy(plan_data)
                plan_data["plano_session"] = nova_session
                plan_data["hipotese"] = desafio.get("hipotese") or plan_data.get("hipotese") or ""
                plan_data["problema"] = desafio.get("problema") or plan_data.get("problema") or ""
                if desafio.get("causas") is not None:
                    plan_data["causas"] = _json_field(desafio.get("causas"))

                meta_base = _json_field(desafio.get("meta_json")) or {}
                if not isinstance(meta_base, dict):
                    meta_base = {}
                meta_base = copy.deepcopy(meta_base)
                meta_base["hipotese"] = plan_data.get("hipotese")
                meta_base["problema"] = (plan_data.get("problema") or "")[:500]
                if plan_data.get("causas") is not None:
                    meta_base["causas"] = plan_data["causas"]
                if desafio.get("tema"):
                    meta_base["tema"] = desafio.get("tema")
                meta_base["desafio_id"] = desafio_id
                meta_base["execucao_replicada"] = True
                if papel == "colaborador":
                    meta_base["execucao_colaborador"] = True

                kanban_template = _fresh_kanban_from_plan(plan_data)

                slots = []
                seen = set()
                for i, raw in enumerate(aulas_in):
                    if not isinstance(raw, dict):
                        return jsonify({"success": False, "error": "Item de aula inválido"}), 400
                    dia = str(raw.get("data") or "").strip()[:10]
                    turno = str(raw.get("turno") or turno_padrao).strip().lower()
                    modo = str(raw.get("modo_execucao") or ("reinicio" if i == 0 else "continuidade")).strip().lower()
                    titulo_aula = str(raw.get("titulo") or "").strip()
                    if not dia or len(dia) < 10:
                        return jsonify({"success": False, "error": "Cada aula precisa de uma data válida."}), 400
                    if turno not in TURNOS:
                        return jsonify({"success": False, "error": "Turno inválido."}), 400
                    if modo not in MODOS:
                        return jsonify({"success": False, "error": "Modo inválido."}), 400
                    key = (dia, turma.lower(), turno)
                    if key in seen:
                        return jsonify(
                            {
                                "success": False,
                                "error": f"Duplicado: {dia} · {turma} · {_turno_label(turno)}.",
                            }
                        ), 400
                    seen.add(key)
                    slots.append(
                        {
                            "data": dia,
                            "turno": turno,
                            "modo_execucao": modo,
                            "titulo": titulo_aula,
                        }
                    )

                criados = []
                id_pai = None
                titulo_desafio = (desafio.get("titulo") or "EduScrum")[:140]

                for i, slot in enumerate(slots):
                    dia = slot["data"]
                    turno = slot["turno"]
                    modo = slot["modo_execucao"]
                    hora = TURNO_HORA[turno]
                    data_evento = f"{dia}T{hora}"

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
                        (id_clie, dia, turma, turno),
                    )
                    if cur.fetchone():
                        return (
                            jsonify(
                                {
                                    "success": False,
                                    "error": (
                                        f"Já existe aula em {dia} para {turma} "
                                        f"({_turno_label(turno)})."
                                    ),
                                }
                            ),
                            409,
                        )

                    kanban_state = copy.deepcopy(kanban_template)
                    if i > 0 and modo == "continuidade":
                        id_pai = criados[-1]["id_evento"]
                    else:
                        id_pai = None

                    label_titulo = slot["titulo"] or titulo_desafio
                    titulo = f"{label_titulo} · {turma} · {_turno_label(turno)}"[:200]
                    meta_final = {
                        **meta_base,
                        "turma": turma,
                        "turno": turno,
                        "modo_execucao": modo,
                        "modo_label": "Prosseguimento" if modo == "continuidade" else "Começar do início",
                    }
                    nota = "\n".join(
                        [
                            f"Réplica do desafio {desafio_id}",
                            f"Turma: {turma}",
                            f"Turno: {_turno_label(turno)}",
                            f"Responsável id_clie={id_clie}",
                        ]
                    )

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
                        RETURNING {SELECT_EVENTO}
                        """,
                        (
                            id_clie,
                            data_evento,
                            titulo,
                            nota,
                            json.dumps(meta_final, ensure_ascii=False),
                            nova_session,
                            json.dumps(plan_data, ensure_ascii=False),
                            json.dumps(kanban_state, ensure_ascii=False),
                            turma[:120],
                            turno,
                            modo,
                            id_pai,
                            disciplina_id,
                            (desafio.get("tema") or None),
                            desafio_id,
                            id_clie,
                        ),
                    )
                    criados.append(_serialize_evento(dict(cur.fetchone())))

        return jsonify(
            {
                "success": True,
                "desafio_id": desafio_id,
                "plano_session": nova_session,
                "eventos": criados,
                "ia_chamada": False,
                "papel_usuario": papel,
            }
        ), 201
    except Exception as exc:
        print(f"⚠️ desafios replicar: {exc}", file=sys.stderr)
        err = str(exc)
        if "uq_inove_agenda_aula_dia_turma_turno" in err:
            return jsonify(
                {"success": False, "error": "Já existe aula neste dia para a mesma turma e turno."}
            ), 409
        return jsonify({"success": False, "error": "Falha ao replicar desafio"}), 500


@desafios_bp.post("/api/desafios/<desafio_id>/convidar")
def convidar_colaborador(desafio_id: str):
    """Dono convida professor por e-mail para este desafio (pontual, sem IA)."""
    user = _require_user()
    if not user:
        return jsonify({"success": False, "error": "Não autenticado"}), 401
    try:
        uuid.UUID(str(desafio_id))
    except ValueError:
        return jsonify({"success": False, "error": "desafio_id inválido"}), 400

    data = request.get_json(silent=True) or {}
    email = str(data.get("email") or "").strip().lower()
    papel = str(data.get("papel_ou_parte") or data.get("papel") or "").strip()[:200] or None
    if not email or "@" not in email:
        return jsonify({"success": False, "error": "Informe um e-mail válido."}), 400

    id_clie = user["id_clie"]
    if (user.get("mail_clie") or "").strip().lower() == email:
        return jsonify({"success": False, "error": "Você não pode convidar a si mesmo."}), 400

    try:
        with get_conn() as conn:
            _ensure_desafios_schema(conn)
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                papel_acesso, desafio = _papel_acesso_desafio(cur, desafio_id, id_clie)
                if papel_acesso != "dono" or not desafio:
                    return jsonify({"success": False, "error": "Desafio não encontrado"}), 404

                # Já aceito?
                cur.execute(
                    """
                    SELECT id, status FROM public.inove_desafio_colaboradores
                     WHERE desafio_id = %s
                       AND lower(trim(email_convidado)) = %s
                       AND status = 'aceito'
                     LIMIT 1
                    """,
                    (desafio_id, email),
                )
                if cur.fetchone():
                    return jsonify(
                        {"success": False, "error": "Este e-mail já é colaborador deste desafio."}
                    ), 409

                # Reaproveita pendente ou cria novo
                cur.execute(
                    """
                    SELECT id, token_convite, status FROM public.inove_desafio_colaboradores
                     WHERE desafio_id = %s
                       AND lower(trim(email_convidado)) = %s
                       AND status = 'pendente'
                     ORDER BY id DESC LIMIT 1
                    """,
                    (desafio_id, email),
                )
                pendente = cur.fetchone()
                token = secrets.token_urlsafe(32)
                if pendente:
                    cur.execute(
                        """
                        UPDATE public.inove_desafio_colaboradores
                           SET token_convite = %s,
                               papel_ou_parte = %s,
                               convidado_por = %s,
                               criado_em = CURRENT_TIMESTAMP
                         WHERE id = %s
                     RETURNING *
                        """,
                        (token, papel, id_clie, pendente["id"]),
                    )
                    colab = dict(cur.fetchone())
                else:
                    cur.execute(
                        """
                        INSERT INTO public.inove_desafio_colaboradores
                            (desafio_id, email_convidado, papel_ou_parte, token_convite,
                             status, convidado_por)
                        VALUES (%s, %s, %s, %s, 'pendente', %s)
                        RETURNING *
                        """,
                        (desafio_id, email, papel, token, id_clie),
                    )
                    colab = dict(cur.fetchone())

        frontend = os.environ.get("FRONTEND_ORIGIN", "http://localhost:5174").rstrip("/")
        convite_url = f"{frontend}/convite/{colab['token_convite']}"
        mail_info = send_desafio_convite_email(
            recipient=email,
            convidado_por_nome=user.get("nome_clie") or "Um professor",
            desafio_titulo=desafio.get("titulo") or "Desafio",
            papel_ou_parte=papel,
            convite_url=convite_url,
        )
        return jsonify(
            {
                "success": True,
                "colaborador": {
                    "id": colab["id"],
                    "email_convidado": colab["email_convidado"],
                    "papel_ou_parte": colab.get("papel_ou_parte"),
                    "status": colab["status"],
                    "token_convite": colab["token_convite"],
                },
                "convite_url": convite_url,
                "email": mail_info,
                "ia_chamada": False,
            }
        ), 201
    except Exception as exc:
        print(f"⚠️ desafios convidar: {exc}", file=sys.stderr)
        return jsonify({"success": False, "error": "Falha ao enviar convite"}), 500


@desafios_bp.get("/api/desafios/<desafio_id>/colaboradores")
def listar_colaboradores(desafio_id: str):
    user = _require_user()
    if not user:
        return jsonify({"success": False, "error": "Não autenticado"}), 401
    try:
        uuid.UUID(str(desafio_id))
    except ValueError:
        return jsonify({"success": False, "error": "desafio_id inválido"}), 400
    try:
        with get_conn() as conn:
            _ensure_desafios_schema(conn)
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                papel, desafio = _papel_acesso_desafio(cur, desafio_id, user["id_clie"])
                if papel != "dono" or not desafio:
                    return jsonify({"success": False, "error": "Desafio não encontrado"}), 404
                cur.execute(
                    """
                    SELECT id, email_convidado, id_clie_convidado, papel_ou_parte,
                           status, criado_em, aceito_em
                      FROM public.inove_desafio_colaboradores
                     WHERE desafio_id = %s
                     ORDER BY criado_em DESC
                    """,
                    (desafio_id,),
                )
                rows = []
                for r in cur.fetchall():
                    item = dict(r)
                    if item.get("criado_em"):
                        item["criado_em"] = item["criado_em"].isoformat()
                    if item.get("aceito_em"):
                        item["aceito_em"] = item["aceito_em"].isoformat()
                    rows.append(item)
        return jsonify({"success": True, "colaboradores": rows}), 200
    except Exception as exc:
        print(f"⚠️ desafios colaboradores: {exc}", file=sys.stderr)
        return jsonify({"success": False, "error": "Falha ao listar colaboradores"}), 500


@desafios_bp.get("/api/convites/<token>")
def get_convite(token: str):
    """Detalhes do convite (público autenticável) — hipótese/tema em leitura."""
    token = (token or "").strip()
    if not token or len(token) < 16:
        return jsonify({"success": False, "error": "Convite inválido"}), 404

    user = _require_user()
    try:
        with get_conn() as conn:
            _ensure_desafios_schema(conn)
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT col.*, d.titulo AS desafio_titulo, d.hipotese, d.causas, d.tema,
                           d.problema, d.id AS desafio_id_uuid, d.id_clie AS dono_id,
                           dono.nome_clie AS dono_nome, dono.mail_clie AS dono_email
                      FROM public.inove_desafio_colaboradores col
                      JOIN public.inove_desafios d ON d.id = col.desafio_id
                      LEFT JOIN public.ctdi_clie dono ON dono.id_clie = d.id_clie
                     WHERE col.token_convite = %s
                    """,
                    (token,),
                )
                row = cur.fetchone()
                if not row:
                    return jsonify({"success": False, "error": "Convite não encontrado"}), 404
                row = dict(row)

        email_match = False
        if user:
            email_match = (user.get("mail_clie") or "").strip().lower() == (
                row.get("email_convidado") or ""
            ).strip().lower()

        return jsonify(
            {
                "success": True,
                "convite": {
                    "status": row["status"],
                    "email_convidado": row["email_convidado"],
                    "papel_ou_parte": row.get("papel_ou_parte"),
                    "desafio_id": str(row["desafio_id"]),
                    "desafio": {
                        "id": str(row["desafio_id"]),
                        "titulo": row.get("desafio_titulo"),
                        "hipotese": row.get("hipotese"),
                        "causas": _json_field(row.get("causas")),
                        "tema": row.get("tema"),
                        "problema": row.get("problema"),
                        "dono_nome": row.get("dono_nome"),
                    },
                    "requer_login": user is None,
                    "email_bate": email_match if user else None,
                    "pode_aceitar": row["status"] == "pendente"
                    and user is not None
                    and email_match,
                },
            }
        ), 200
    except Exception as exc:
        print(f"⚠️ convite get: {exc}", file=sys.stderr)
        return jsonify({"success": False, "error": "Falha ao carregar convite"}), 500


@desafios_bp.post("/api/convites/<token>/aceitar")
def aceitar_convite(token: str):
    user = _require_user()
    if not user:
        return jsonify({"success": False, "error": "Não autenticado"}), 401
    token = (token or "").strip()
    if not token:
        return jsonify({"success": False, "error": "Convite inválido"}), 404

    email_user = (user.get("mail_clie") or "").strip().lower()
    try:
        with get_conn() as conn:
            _ensure_desafios_schema(conn)
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT * FROM public.inove_desafio_colaboradores
                     WHERE token_convite = %s
                    """,
                    (token,),
                )
                colab = cur.fetchone()
                if not colab:
                    return jsonify({"success": False, "error": "Convite não encontrado"}), 404
                colab = dict(colab)
                if colab["status"] == "aceito":
                    if colab.get("id_clie_convidado") == user["id_clie"]:
                        return jsonify(
                            {
                                "success": True,
                                "ja_aceito": True,
                                "desafio_id": str(colab["desafio_id"]),
                            }
                        ), 200
                    return jsonify({"success": False, "error": "Convite já utilizado."}), 409
                if colab["status"] == "recusado":
                    return jsonify({"success": False, "error": "Este convite foi recusado."}), 409

                email_conv = (colab.get("email_convidado") or "").strip().lower()
                if email_user != email_conv:
                    return jsonify(
                        {
                            "success": False,
                            "error": (
                                f"Entre com o e-mail convidado ({email_conv}) "
                                "para aceitar este convite."
                            ),
                        }
                    ), 403

                cur.execute(
                    """
                    UPDATE public.inove_desafio_colaboradores
                       SET status = 'aceito',
                           id_clie_convidado = %s,
                           aceito_em = CURRENT_TIMESTAMP
                     WHERE id = %s
                 RETURNING *
                    """,
                    (user["id_clie"], colab["id"]),
                )
                updated = dict(cur.fetchone())

        return jsonify(
            {
                "success": True,
                "desafio_id": str(updated["desafio_id"]),
                "colaborador": {
                    "id": updated["id"],
                    "status": updated["status"],
                    "papel_ou_parte": updated.get("papel_ou_parte"),
                },
                "ia_chamada": False,
                "proximo_passo": "criar_execucao",
            }
        ), 200
    except Exception as exc:
        print(f"⚠️ convite aceitar: {exc}", file=sys.stderr)
        return jsonify({"success": False, "error": "Falha ao aceitar convite"}), 500


@desafios_bp.post("/api/convites/<token>/recusar")
def recusar_convite(token: str):
    user = _require_user()
    if not user:
        return jsonify({"success": False, "error": "Não autenticado"}), 401
    token = (token or "").strip()
    email_user = (user.get("mail_clie") or "").strip().lower()
    try:
        with get_conn() as conn:
            _ensure_desafios_schema(conn)
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    "SELECT * FROM public.inove_desafio_colaboradores WHERE token_convite = %s",
                    (token,),
                )
                colab = cur.fetchone()
                if not colab:
                    return jsonify({"success": False, "error": "Convite não encontrado"}), 404
                colab = dict(colab)
                if (colab.get("email_convidado") or "").strip().lower() != email_user:
                    return jsonify({"success": False, "error": "Convite não encontrado"}), 404
                if colab["status"] != "pendente":
                    return jsonify({"success": False, "error": "Convite já processado."}), 409
                cur.execute(
                    """
                    UPDATE public.inove_desafio_colaboradores
                       SET status = 'recusado'
                     WHERE id = %s
                    """,
                    (colab["id"],),
                )
        return jsonify({"success": True, "status": "recusado"}), 200
    except Exception as exc:
        print(f"⚠️ convite recusar: {exc}", file=sys.stderr)
        return jsonify({"success": False, "error": "Falha ao recusar convite"}), 500

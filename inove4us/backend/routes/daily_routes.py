"""
Vetor Dia a Dia — Blueprint Flask de aulas simples (~50 min).

Framework: Flask (não FastAPI). Validação manual (sem Pydantic no projeto).
Auth: sessão `inove4us_session` com `user.id_clie`.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import date, datetime
from typing import Any

from flask import Blueprint, jsonify, request, session
from psycopg2 import errors as pg_errors
from psycopg2.extras import RealDictCursor

from aulas_simples_models import FONTES, ensure_aulas_simples_table, normalize_status
from db import get_conn
from services.methodology_service import (
    CACHE_VERSION,
    buscar_dinamicas_rapidas,
    get_dinamica_by_id,
    sugerir_dinamicas_para_contexto,
)

daily_bp = Blueprint("daily", __name__)

TEXT_LIMIT = 20_000
TEMA_LIMIT = 255
TURMA_LIMIT = 120
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100

# Status que permitem exclusão (não apagar aula em andamento/realizada)
DELETABLE_STATUSES = frozenset({"draft", "planejado"})

ESTACOES_IDS = (
    "est_alinhamento",
    "est_entrega",
    "est_campo",
    "est_retro",
)

ESTACOES_TITULOS = {
    "est_alinhamento": "1 · Acolhida",
    "est_entrega": "2 · Conteúdo",
    "est_campo": "3 · Dinâmica",
    "est_retro": "4 · Fechamento",
}


def _agenda_status_from_aula(aula_status: str) -> str:
    """Mapeia status da aula simples → status do evento na agenda."""
    s = normalize_status(aula_status) or "planejado"
    if s == "em_execucao":
        return "em_execucao"
    if s == "realizado":
        return "concluido"
    return "planejado"


def _move_all_cards(kanban: dict | None, *, to_coluna: str, nota: str) -> dict:
    """Move todas as estações do ciclo para a coluna alvo (lote)."""
    base = _normalize_kanban_state(kanban) or {"tarefas": []}
    tarefas = list(base.get("tarefas") or [])
    by_id = {
        str(t.get("id") or "").strip(): dict(t)
        for t in tarefas
        if isinstance(t, dict) and str(t.get("id") or "").strip()
    }
    agora = datetime.utcnow().isoformat() + "Z"
    out = []
    for est_id in ESTACOES_IDS:
        prev = by_id.get(est_id) or {
            "id": est_id,
            "titulo": ESTACOES_TITULOS.get(est_id, est_id),
        }
        from_col = str(prev.get("coluna") or "para_fazer")
        item = dict(prev)
        item["titulo"] = item.get("titulo") or ESTACOES_TITULOS.get(est_id, est_id)
        if from_col != to_coluna:
            entrada = {
                "de": from_col,
                "para": to_coluna,
                "nota": nota,
                "em": agora,
            }
            hist = list(item.get("historico") or [])
            hist.append(entrada)
            item["historico"] = hist
            item["ultima_observacao"] = nota
        item["coluna"] = to_coluna
        item["id"] = est_id
        out.append(item)
        by_id.pop(est_id, None)
    # preserva cards extras se houver
    for _tid, t in by_id.items():
        item = dict(t)
        from_col = str(item.get("coluna") or "para_fazer")
        if from_col != to_coluna:
            hist = list(item.get("historico") or [])
            hist.append(
                {"de": from_col, "para": to_coluna, "nota": nota, "em": agora}
            )
            item["historico"] = hist
            item["ultima_observacao"] = nota
        item["coluna"] = to_coluna
        out.append(item)
    return {"tarefas": out}


def _is_prod() -> bool:
    env = (os.environ.get("INOVE4US_ENV") or os.environ.get("FLASK_ENV") or "").lower()
    return env == "production"


def _schema_ensure_allowed() -> bool:
    """
    Em produção o schema fica congelado até o cutover financeiro + migration 007.
    Local/dev: ensure automático. Prod: só com INOVE_DAILY_SCHEMA_ENSURE=1.
    """
    flag = (os.environ.get("INOVE_DAILY_SCHEMA_ENSURE") or "").strip().lower()
    if flag in ("1", "true", "yes"):
        return True
    if flag in ("0", "false", "no"):
        return False
    return not _is_prod()


def _require_user() -> dict | None:
    user = session.get("user")
    if not user or not user.get("id_clie"):
        return None
    if not str(user.get("mail_clie") or "").strip():
        return None
    return user


def _iso(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


def _serialize(row: dict) -> dict:
    return {
        "id": row["id"],
        "id_clie": row["id_clie"],
        "data_planejada": _iso(row.get("data_planejada")),
        "turma_nome": row.get("turma_nome"),
        "tema_aula": row.get("tema_aula") or "",
        "ementa_topico": row.get("ementa_topico") or "",
        "objetivo_aprendizagem": row.get("objetivo_aprendizagem") or "",
        "acolhida": row.get("acolhida") or "",
        "conteudo_essencial": row.get("conteudo_essencial") or "",
        "dinamica_ativa_id": row.get("dinamica_ativa_id"),
        "dinamica_ativa_fonte": row.get("dinamica_ativa_fonte") or "mativas",
        "fechamento_checkout": row.get("fechamento_checkout") or "",
        "status": row.get("status") or "draft",
        "id_evento_agenda": row.get("id_evento_agenda"),
        "disciplina_id": row.get("disciplina_id"),
        "tipo_registro": row.get("tipo_registro") or "aula",
        "origem": row.get("origem") or "manual",
        "kanban_state": row.get("kanban_state")
        if isinstance(row.get("kanban_state"), (dict, list))
        else (_parse_json_field(row.get("kanban_state")) if row.get("kanban_state") else None),
        "data_inicio": _iso(row.get("data_inicio")),
        "data_conclusao": _iso(row.get("data_conclusao")),
        "feedback_json": _parse_json_field(row.get("feedback_json"))
        if row.get("feedback_json") is not None
        else None,
        "created_at": _iso(row.get("created_at")),
        "updated_at": _iso(row.get("updated_at")),
    }


def _parse_json_field(value: Any) -> Any:
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
        except json.JSONDecodeError:
            return None
    return None


def _normalize_kanban_state(raw: Any) -> dict | None:
    data = _parse_json_field(raw) if not isinstance(raw, (dict, list)) else raw
    if data is None:
        return None
    if isinstance(data, list):
        return {"tarefas": data}
    if isinstance(data, dict):
        tarefas = data.get("tarefas")
        if isinstance(tarefas, list):
            return {"tarefas": tarefas}
        return data
    return None


def _agenda_titulo(tema: str, turma: str | None) -> str:
    tema = (tema or "Aula do dia").strip()[:160]
    turma = (turma or "").strip()
    if turma:
        return f"Dia a Dia · {tema} · {turma}"[:200]
    return f"Dia a Dia · {tema}"[:200]


def _agenda_nota(row: dict) -> str:
    parts = [
        "Ciclo rápido (~50 min): alinhamento → entrega → atividade → retro.",
    ]
    obj = (row.get("objetivo_aprendizagem") or "").strip()
    if obj:
        parts.append(f"Meta: {obj[:400]}")
    din = (row.get("dinamica_ativa_id") or "").strip()
    if din:
        cached = get_dinamica_by_id(din)
        if cached:
            parts.append(f"Atividade: {cached.get('nome')}")
        else:
            parts.append(f"Atividade: {din}")
    return "\n".join(parts)[:4000]


def _sync_agenda_evento(cur, row: dict) -> int | None:
    """
    Cria ou atualiza evento na agenda executiva (tipo aula_dia).
    Retorna id_evento_agenda.
    """
    aula_id = int(row["id"])
    id_clie = int(row["id_clie"])
    data_p = row.get("data_planejada")
    if hasattr(data_p, "isoformat"):
        data_iso = data_p.isoformat()[:10]
    else:
        data_iso = str(data_p or "")[:10]
    if not data_iso:
        return row.get("id_evento_agenda")

    titulo = _agenda_titulo(row.get("tema_aula") or "", row.get("turma_nome"))
    nota = _agenda_nota(row)
    meta = json.dumps(
        {
            "origem": "dia_a_dia",
            "aula_simples_id": aula_id,
            "ciclo": "rapido_50min",
        },
        ensure_ascii=False,
    )
    data_evento = f"{data_iso}T12:00:00"
    turma = (row.get("turma_nome") or "").strip() or None
    id_evento = row.get("id_evento_agenda")
    kanban = _normalize_kanban_state(row.get("kanban_state"))
    kanban_json = json.dumps(kanban or {"tarefas": []}, ensure_ascii=False)
    agenda_status = _agenda_status_from_aula(str(row.get("status") or "planejado"))

    disciplina_id = row.get("disciplina_id")
    origem_aula = _parse_origem(row.get("origem"), default="manual")

    if id_evento:
        cur.execute(
            """
            UPDATE public.inove_agenda_eventos
               SET data_evento = %s,
                   titulo = %s,
                   nota_texto = %s,
                   status = %s,
                   tipo = 'aula_dia',
                   meta_json = %s::jsonb,
                   turma = %s,
                   kanban_state = %s::jsonb,
                   disciplina_id = %s,
                   origem = %s
             WHERE id_evento = %s AND id_clie = %s
         RETURNING id_evento
            """,
            (
                data_evento,
                titulo,
                nota,
                agenda_status,
                meta,
                turma,
                kanban_json,
                disciplina_id,
                origem_aula,
                int(id_evento),
                id_clie,
            ),
        )
        updated = cur.fetchone()
        if updated:
            return int(updated["id_evento"] if isinstance(updated, dict) else updated[0])

    cur.execute(
        """
        INSERT INTO public.inove_agenda_eventos
            (id_clie, data_evento, titulo, nota_texto, status, tipo, meta_json,
             turma, kanban_state, disciplina_id, origem)
        VALUES (%s, %s, %s, %s, %s, 'aula_dia', %s::jsonb,
                %s, %s::jsonb, %s, %s)
        RETURNING id_evento
        """,
        (
            id_clie,
            data_evento,
            titulo,
            nota,
            agenda_status,
            meta,
            turma,
            kanban_json,
            disciplina_id,
            origem_aula,
        ),
    )
    created = cur.fetchone()
    new_id = int(created["id_evento"] if isinstance(created, dict) else created[0])
    cur.execute(
        """
        UPDATE public.inove_aulas_simples
           SET id_evento_agenda = %s, updated_at = CURRENT_TIMESTAMP
         WHERE id = %s AND id_clie = %s
        """,
        (new_id, aula_id, id_clie),
    )
    return new_id


def _delete_agenda_evento(cur, row: dict) -> None:
    id_evento = row.get("id_evento_agenda")
    if not id_evento:
        return
    cur.execute(
        """
        DELETE FROM public.inove_agenda_eventos
         WHERE id_evento = %s AND id_clie = %s AND tipo = 'aula_dia'
        """,
        (int(id_evento), int(row["id_clie"])),
    )


def _parse_date(raw: Any) -> date | None:
    text = str(raw or "").strip()
    if not text:
        return None
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def _clip(value: Any, limit: int) -> str:
    return str(value or "")[:limit]


ORIGENS_AULA = frozenset({"manual", "wizard_ia", "importacao"})
TIPOS_REGISTRO_AULA = frozenset({"aula", "evento"})


def _parse_origem(raw: Any, *, default: str = "manual") -> str:
    value = str(raw if raw is not None else default).strip().lower()
    return value if value in ORIGENS_AULA else default


def _parse_tipo_registro(raw: Any, *, default: str = "aula") -> str:
    value = str(raw if raw is not None else default).strip().lower()
    return value if value in TIPOS_REGISTRO_AULA else default


def _resolve_disciplina_id(cur, id_clie: int, raw: Any) -> int | None:
    """Valida disciplina ativa do professor; None limpa o vínculo."""
    if raw in (None, "", 0, "0", "null"):
        return None
    try:
        disciplina_id = int(raw)
    except (TypeError, ValueError) as exc:
        raise ValueError("disciplina_id inválido") from exc
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
    row = cur.fetchone()
    if not row:
        raise ValueError("Disciplina não encontrada ou sem permissão")
    return int(row["id"] if isinstance(row, dict) else row[0])


def _prepare_conn(conn) -> None:
    if _schema_ensure_allowed():
        ensure_aulas_simples_table(conn)


def _table_missing_response():
    return (
        jsonify(
            {
                "success": False,
                "error": (
                    "Tabela inove_aulas_simples ainda não disponível. "
                    "Aguarde a migration 007 após validação financeira "
                    "(ou defina INOVE_DAILY_SCHEMA_ENSURE=1 em não-prod)."
                ),
                "code": "schema_pending",
            }
        ),
        503,
    )


def _parse_pagination() -> tuple[int, int, int]:
    """Retorna (page, page_size, offset). page é 1-based."""
    try:
        page = int(request.args.get("page") or 1)
    except (TypeError, ValueError):
        page = 1
    try:
        page_size = int(
            request.args.get("page_size")
            or request.args.get("limit")
            or DEFAULT_PAGE_SIZE
        )
    except (TypeError, ValueError):
        page_size = DEFAULT_PAGE_SIZE
    page = max(1, page)
    page_size = max(1, min(page_size, MAX_PAGE_SIZE))
    offset = (page - 1) * page_size
    return page, page_size, offset


def _fetch_aula_row(cur, aula_id: int) -> dict | None:
    cur.execute(
        """
        SELECT *
          FROM public.inove_aulas_simples
         WHERE id = %s
        """,
        (int(aula_id),),
    )
    row = cur.fetchone()
    return dict(row) if row else None


def _authorize_owner(row: dict | None, id_clie: int):
    """
    404 se não existe; 401 se existe mas não é do usuário logado
    (contrato pedido na API do vetor Dia a Dia).
    """
    if not row:
        return (
            jsonify({"success": False, "error": "Aula não encontrada"}),
            404,
        )
    if int(row["id_clie"]) != int(id_clie):
        return (
            jsonify({"success": False, "error": "Não autorizado — aula de outro usuário"}),
            401,
        )
    return None


# --- dinâmicas (rota estática ANTES de /<id>) ------------------------------------


@daily_bp.get("/api/daily/sugerir-dinamicas")
def sugerir_dinamicas():
    user = _require_user()
    if not user:
        return jsonify({"success": False, "error": "Não autenticado"}), 401

    termo = str(request.args.get("q") or request.args.get("termo") or "").strip()
    tema = str(request.args.get("tema") or "").strip()
    objetivo = str(request.args.get("objetivo") or "").strip()
    conteudo = str(request.args.get("conteudo") or "").strip()
    try:
        limite = int(request.args.get("limit") or "12")
    except (TypeError, ValueError):
        limite = 12
    limite = max(3, min(limite, 39))

    # Com contexto da aula: ranqueia as 39 + motivo. Sem contexto + filtro: lista filtrada.
    if tema or objetivo or conteudo:
        items = sugerir_dinamicas_para_contexto(
            tema=tema,
            objetivo=objetivo,
            conteudo=conteudo,
            termo=termo,
            limite=limite,
        )
        fonte = "catalogo_39_contextual"
    else:
        items = buscar_dinamicas_rapidas(termo)
        fonte = "cache_local_versionado"

    # Vetor Dia a Dia: escola pode desabilitar metodologias (fail-soft)
    try:
        from services.methodology_override_service import filter_dinamicas_by_vector

        items = filter_dinamicas_by_vector(
            items, user.get("id_clie"), "dia_a_dia"
        )
    except Exception as exc:
        print(f"[daily] override filter: {exc}", flush=True)

    return jsonify(
        {
            "success": True,
            "cache_version": CACHE_VERSION,
            "fonte": fonte,
            "termo": termo,
            "tema": tema,
            "dinamicas": items,
            "total": len(items),
        }
    )


# --- CRUD -----------------------------------------------------------------------


@daily_bp.post("/api/daily/planejar")
def planejar_aula():
    """Cria AulaSimples em status draft. Retorna id + payload."""
    user = _require_user()
    if not user:
        return jsonify({"success": False, "error": "Não autenticado"}), 401

    data = request.get_json(silent=True) or {}
    data_planejada = _parse_date(data.get("data_planejada"))
    tema = _clip(data.get("tema_aula"), TEMA_LIMIT).strip()
    if not data_planejada:
        return (
            jsonify({"success": False, "error": "data_planejada inválida (YYYY-MM-DD)"}),
            400,
        )
    if not tema:
        return jsonify({"success": False, "error": "tema_aula é obrigatório"}), 400

    turma = _clip(data.get("turma_nome"), TURMA_LIMIT).strip() or None
    objetivo = _clip(data.get("objetivo_aprendizagem"), TEXT_LIMIT)
    acolhida = _clip(data.get("acolhida"), TEXT_LIMIT)
    conteudo = _clip(data.get("conteudo_essencial"), TEXT_LIMIT)
    fechamento = _clip(
        data.get("fechamento_checkout") or data.get("fechamento_checkuout"),
        TEXT_LIMIT,
    )
    dinamica_id = _clip(data.get("dinamica_ativa_id"), 160).strip() or None
    fonte = str(data.get("dinamica_ativa_fonte") or "mativas").strip().lower()
    if fonte not in FONTES:
        fonte = "mativas"
    if dinamica_id:
        cached = get_dinamica_by_id(dinamica_id)
        if cached:
            dinamica_id = str(cached["id"])
            if "dinamica_ativa_fonte" not in data:
                fonte = "inove_local"
    kanban = _normalize_kanban_state(data.get("kanban_state"))
    origem = _parse_origem(data.get("origem"), default="manual")
    tipo_registro = _parse_tipo_registro(data.get("tipo_registro"), default="aula")

    id_clie = int(user["id_clie"])
    # Auditoria: versão da diretriz escolar aplicada nesta aula (fail-soft)
    try:
        if dinamica_id:
            from services.methodology_override_service import get_override_for_professor

            ov = get_override_for_professor(id_clie, dinamica_id)
            if ov and ov.get("versao"):
                base = dict(kanban) if isinstance(kanban, dict) else {}
                base["metodologia_override_versao_aplicada"] = int(ov["versao"])
                base["escola_override"] = {
                    "metodologia_key": ov.get("metodologia_key"),
                    "versao": int(ov["versao"]),
                    "mensagem": (ov.get("diretriz_customizada") or "")[:220] or None,
                }
                kanban = base
    except Exception as exc:
        print(f"[daily] override audit: {exc}", flush=True)

    kanban_json = json.dumps(kanban, ensure_ascii=False) if kanban is not None else None
    try:
        from db import aulas_simples_quota

        quota = aulas_simples_quota(id_clie)
        if quota.get("bloqueado"):
            return (
                jsonify(
                    {
                        "success": False,
                        "error": (
                            "No plano gratuito você pode navegar pelo Dia a Dia, "
                            "mas o registro de aulas exige o plano Profissional, Mentor "
                            "ou um pacote avulso."
                        ),
                        "code": "AULAS_MES_LIMIT",
                        "aulas_mes": quota,
                    }
                ),
                402,
            )
    except Exception as exc:
        print(f"[daily] aviso quota aulas: {exc}", file=sys.stderr)

    try:
        with get_conn() as conn:
            _prepare_conn(conn)
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                try:
                    disciplina_id = (
                        _resolve_disciplina_id(cur, id_clie, data.get("disciplina_id"))
                        if "disciplina_id" in data
                        else None
                    )
                except ValueError as exc:
                    return jsonify({"success": False, "error": str(exc)}), 400
                ementa_topico = _clip(data.get("ementa_topico"), TEMA_LIMIT).strip() or None
                cur.execute(
                    """
                    INSERT INTO public.inove_aulas_simples (
                        id_clie, data_planejada, turma_nome, tema_aula, ementa_topico,
                        objetivo_aprendizagem, acolhida, conteudo_essencial,
                        dinamica_ativa_id, dinamica_ativa_fonte,
                        fechamento_checkout, status, kanban_state,
                        disciplina_id, tipo_registro, origem
                    ) VALUES (
                        %s, %s, %s, %s, %s,
                        %s, %s, %s,
                        %s, %s,
                        %s, 'draft', %s::jsonb,
                        %s, %s, %s
                    )
                    RETURNING *
                    """,
                    (
                        id_clie,
                        data_planejada,
                        turma,
                        tema,
                        ementa_topico,
                        objetivo,
                        acolhida,
                        conteudo,
                        dinamica_id,
                        fonte,
                        fechamento,
                        kanban_json,
                        disciplina_id,
                        tipo_registro,
                        origem,
                    ),
                )
                row = dict(cur.fetchone())
                # Espelha na agenda executiva (Mesa)
                evento_id = _sync_agenda_evento(cur, row)
                if evento_id:
                    row["id_evento_agenda"] = evento_id
    except pg_errors.UndefinedTable:
        return _table_missing_response()
    except Exception as exc:
        print(f"[daily] planejar: {exc}", file=sys.stderr)
        return jsonify({"success": False, "error": "Falha ao criar aula"}), 500

    return (
        jsonify(
            {
                "success": True,
                "id": row["id"],
                "aula": _serialize(row),
            }
        ),
        201,
    )


@daily_bp.get("/api/daily/")
@daily_bp.get("/api/daily")
def listar_aulas():
    """Lista aulas do usuário logado — data desc, com paginação."""
    user = _require_user()
    if not user:
        return jsonify({"success": False, "error": "Não autenticado"}), 401

    page, page_size, offset = _parse_pagination()
    id_clie = int(user["id_clie"])

    filters = ["a.id_clie = %s"]
    params: list[Any] = [id_clie]
    join_sql = ""

    disc_raw = request.args.get("disciplina_id")
    if disc_raw not in (None, ""):
        try:
            filters.append("a.disciplina_id = %s")
            params.append(int(disc_raw))
        except (TypeError, ValueError):
            return jsonify({"success": False, "error": "disciplina_id inválido"}), 400

    curso_raw = request.args.get("curso_id")
    periodo_raw = request.args.get("periodo_letivo_id")
    if curso_raw not in (None, "") or periodo_raw not in (None, ""):
        join_sql = """
            LEFT JOIN public.inove_disciplinas d ON d.id = a.disciplina_id
            LEFT JOIN public.inove_cursos c ON c.id = d.curso_id
        """
        if curso_raw not in (None, ""):
            try:
                filters.append("c.id = %s")
                params.append(int(curso_raw))
            except (TypeError, ValueError):
                return jsonify({"success": False, "error": "curso_id inválido"}), 400
        if periodo_raw not in (None, ""):
            try:
                filters.append("c.periodo_letivo_id = %s")
                params.append(int(periodo_raw))
            except (TypeError, ValueError):
                return jsonify({"success": False, "error": "periodo_letivo_id inválido"}), 400

    origem_f = request.args.get("origem")
    if origem_f not in (None, ""):
        origem_f = str(origem_f).strip().lower()
        if origem_f not in ORIGENS_AULA:
            return jsonify({"success": False, "error": "origem inválida"}), 400
        filters.append("a.origem = %s")
        params.append(origem_f)

    where_sql = " AND ".join(filters)

    try:
        with get_conn() as conn:
            _prepare_conn(conn)
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    f"""
                    SELECT COUNT(*)::int AS total
                      FROM public.inove_aulas_simples a
                      {join_sql}
                     WHERE {where_sql}
                    """,
                    params,
                )
                total = int(cur.fetchone()["total"])
                list_params = list(params) + [page_size, offset]
                cur.execute(
                    f"""
                    SELECT a.*
                      FROM public.inove_aulas_simples a
                      {join_sql}
                     WHERE {where_sql}
                     ORDER BY a.data_planejada DESC, a.id DESC
                     LIMIT %s OFFSET %s
                    """,
                    list_params,
                )
                rows = [dict(r) for r in cur.fetchall()]
    except pg_errors.UndefinedTable:
        return _table_missing_response()
    except Exception as exc:
        print(f"[daily] list: {exc}", file=sys.stderr)
        return jsonify({"success": False, "error": "Falha ao listar aulas"}), 500

    total_pages = (total + page_size - 1) // page_size if page_size else 0
    return jsonify(
        {
            "success": True,
            "aulas": [_serialize(r) for r in rows],
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": total,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1,
            },
        }
    )


@daily_bp.get("/api/daily/<int:aula_id>")
def detalhe_aula(aula_id: int):
    user = _require_user()
    if not user:
        return jsonify({"success": False, "error": "Não autenticado"}), 401

    id_clie = int(user["id_clie"])
    try:
        with get_conn() as conn:
            _prepare_conn(conn)
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                row = _fetch_aula_row(cur, aula_id)
    except pg_errors.UndefinedTable:
        return _table_missing_response()
    except Exception as exc:
        print(f"[daily] get: {exc}", file=sys.stderr)
        return jsonify({"success": False, "error": "Falha ao buscar aula"}), 500

    denied = _authorize_owner(row, id_clie)
    if denied:
        return denied
    return jsonify({"success": True, "aula": _serialize(row)})


@daily_bp.put("/api/daily/<int:aula_id>")
def atualizar_aula(aula_id: int):
    """
    Atualiza campos de texto / dinâmica / fechamento.
    Permite status draft | planejado | em_execucao | realizado
    (aliases: in_progress → em_execucao, completed → realizado).
    """
    user = _require_user()
    if not user:
        return jsonify({"success": False, "error": "Não autenticado"}), 401

    data = request.get_json(silent=True)
    if data is None or not isinstance(data, dict):
        return jsonify({"success": False, "error": "JSON inválido no body"}), 400

    id_clie = int(user["id_clie"])

    try:
        with get_conn() as conn:
            _prepare_conn(conn)
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                existing = _fetch_aula_row(cur, aula_id)
                denied = _authorize_owner(existing, id_clie)
                if denied:
                    return denied

                fields: list[str] = []
                params: list[Any] = []

                if "data_planejada" in data:
                    parsed = _parse_date(data.get("data_planejada"))
                    if not parsed:
                        return (
                            jsonify({"success": False, "error": "data_planejada inválida"}),
                            400,
                        )
                    fields.append("data_planejada = %s")
                    params.append(parsed)

                if "turma_nome" in data:
                    turma = _clip(data.get("turma_nome"), TURMA_LIMIT).strip() or None
                    fields.append("turma_nome = %s")
                    params.append(turma)

                if "tema_aula" in data:
                    tema = _clip(data.get("tema_aula"), TEMA_LIMIT).strip()
                    if not tema:
                        return (
                            jsonify(
                                {"success": False, "error": "tema_aula não pode ser vazio"}
                            ),
                            400,
                        )
                    fields.append("tema_aula = %s")
                    params.append(tema)

                if "ementa_topico" in data:
                    fields.append("ementa_topico = %s")
                    params.append(
                        _clip(data.get("ementa_topico"), TEMA_LIMIT).strip() or None
                    )

                for key, col, limit in (
                    ("objetivo_aprendizagem", "objetivo_aprendizagem", TEXT_LIMIT),
                    ("acolhida", "acolhida", TEXT_LIMIT),
                    ("conteudo_essencial", "conteudo_essencial", TEXT_LIMIT),
                    ("fechamento_checkout", "fechamento_checkout", TEXT_LIMIT),
                    ("fechamento_checkuout", "fechamento_checkout", TEXT_LIMIT),
                ):
                    if key in data:
                        if col == "fechamento_checkout" and any(
                            f.startswith("fechamento_checkout") for f in fields
                        ):
                            continue
                        fields.append(f"{col} = %s")
                        params.append(_clip(data.get(key), limit))

                if "dinamica_ativa_id" in data:
                    din = _clip(data.get("dinamica_ativa_id"), 160).strip() or None
                    if din:
                        cached = get_dinamica_by_id(din)
                        if cached:
                            din = str(cached["id"])
                            if "dinamica_ativa_fonte" not in data:
                                fields.append("dinamica_ativa_fonte = %s")
                                params.append("inove_local")
                    fields.append("dinamica_ativa_id = %s")
                    params.append(din)

                if "dinamica_ativa_fonte" in data:
                    fonte = str(data.get("dinamica_ativa_fonte") or "").strip().lower()
                    if fonte not in FONTES:
                        return (
                            jsonify(
                                {
                                    "success": False,
                                    "error": "dinamica_ativa_fonte inválida",
                                }
                            ),
                            400,
                        )
                    fields.append("dinamica_ativa_fonte = %s")
                    params.append(fonte)

                if "status" in data:
                    status = normalize_status(data.get("status"))
                    if not status:
                        return (
                            jsonify(
                                {
                                    "success": False,
                                    "error": (
                                        "status inválido — use draft, planejado, "
                                        "em_execucao (in_progress) ou realizado (completed)"
                                    ),
                                }
                            ),
                            400,
                        )
                    fields.append("status = %s")
                    params.append(status)

                if "kanban_state" in data:
                    kanban = _normalize_kanban_state(data.get("kanban_state"))
                    fields.append("kanban_state = %s::jsonb")
                    params.append(
                        json.dumps(kanban, ensure_ascii=False) if kanban is not None else None
                    )

                if "disciplina_id" in data:
                    try:
                        disc_id = _resolve_disciplina_id(
                            cur, id_clie, data.get("disciplina_id")
                        )
                    except ValueError as exc:
                        return jsonify({"success": False, "error": str(exc)}), 400
                    fields.append("disciplina_id = %s")
                    params.append(disc_id)

                if "tipo_registro" in data:
                    tipo_reg = _parse_tipo_registro(data.get("tipo_registro"))
                    fields.append("tipo_registro = %s")
                    params.append(tipo_reg)

                if "origem" in data:
                    origem_val = _parse_origem(data.get("origem"))
                    fields.append("origem = %s")
                    params.append(origem_val)

                if not fields:
                    return (
                        jsonify({"success": False, "error": "Nenhum campo para atualizar"}),
                        400,
                    )

                fields.append("updated_at = CURRENT_TIMESTAMP")
                params.extend([int(aula_id), id_clie])
                cur.execute(
                    f"""
                    UPDATE public.inove_aulas_simples
                       SET {", ".join(fields)}
                     WHERE id = %s AND id_clie = %s
                 RETURNING *
                    """,
                    params,
                )
                row = cur.fetchone()
                if row:
                    row = dict(row)
                    evento_id = _sync_agenda_evento(cur, row)
                    if evento_id:
                        row["id_evento_agenda"] = evento_id
    except pg_errors.UndefinedTable:
        return _table_missing_response()
    except Exception as exc:
        print(f"[daily] put: {exc}", file=sys.stderr)
        return jsonify({"success": False, "error": "Falha ao atualizar aula"}), 500

    if not row:
        return jsonify({"success": False, "error": "Aula não encontrada"}), 404
    return jsonify({"success": True, "aula": _serialize(dict(row))})


@daily_bp.delete("/api/daily/<int:aula_id>")
def excluir_aula(aula_id: int):
    """Remove apenas se status for draft ou planejado."""
    user = _require_user()
    if not user:
        return jsonify({"success": False, "error": "Não autenticado"}), 401

    id_clie = int(user["id_clie"])
    try:
        with get_conn() as conn:
            _prepare_conn(conn)
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                existing = _fetch_aula_row(cur, aula_id)
                denied = _authorize_owner(existing, id_clie)
                if denied:
                    return denied

                status = str(existing.get("status") or "")
                if status not in DELETABLE_STATUSES:
                    return (
                        jsonify(
                            {
                                "success": False,
                                "error": (
                                    "Só é permitido excluir aulas em draft ou planejado"
                                ),
                                "status": status,
                            }
                        ),
                        409,
                    )

                _delete_agenda_evento(cur, existing)
                cur.execute(
                    """
                    DELETE FROM public.inove_aulas_simples
                     WHERE id = %s AND id_clie = %s
                    """,
                    (int(aula_id), id_clie),
                )
    except pg_errors.UndefinedTable:
        return _table_missing_response()
    except Exception as exc:
        print(f"[daily] delete: {exc}", file=sys.stderr)
        return jsonify({"success": False, "error": "Falha ao excluir aula"}), 500

    return jsonify({"success": True, "deleted_id": int(aula_id)})


@daily_bp.post("/api/daily/<int:aula_id>/iniciar")
def iniciar_aula(aula_id: int):
    """
    Modo Aula — Iniciar: status em_execucao + data_inicio + 4 cards → Fazendo.
    Idempotente se já estiver em_execucao (tolerante a fechar o notebook).
    """
    user = _require_user()
    if not user:
        return jsonify({"success": False, "error": "Não autenticado"}), 401

    id_clie = int(user["id_clie"])
    try:
        with get_conn() as conn:
            _prepare_conn(conn)
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                existing = _fetch_aula_row(cur, aula_id)
                denied = _authorize_owner(existing, id_clie)
                if denied:
                    return denied

                status = normalize_status(existing.get("status")) or "draft"
                if status == "realizado":
                    return (
                        jsonify(
                            {
                                "success": False,
                                "error": "Aula já encerrada — não é possível reiniciar",
                                "status": status,
                            }
                        ),
                        409,
                    )

                kanban = _move_all_cards(
                    existing.get("kanban_state"),
                    to_coluna="fazendo",
                    nota="Início da aula (lote)",
                )
                kanban_json = json.dumps(kanban, ensure_ascii=False)

                # Se já está em execução, só garante cards em Fazendo (sem resetar data_inicio)
                if status == "em_execucao":
                    cur.execute(
                        """
                        UPDATE public.inove_aulas_simples
                           SET kanban_state = %s::jsonb,
                               updated_at = CURRENT_TIMESTAMP
                         WHERE id = %s AND id_clie = %s
                     RETURNING *
                        """,
                        (kanban_json, int(aula_id), id_clie),
                    )
                else:
                    # draft | planejado → em_execucao (tolerante a rascunho já salvo)
                    cur.execute(
                        """
                        UPDATE public.inove_aulas_simples
                           SET status = 'em_execucao',
                               data_inicio = COALESCE(data_inicio, CURRENT_TIMESTAMP),
                               kanban_state = %s::jsonb,
                               updated_at = CURRENT_TIMESTAMP
                         WHERE id = %s AND id_clie = %s
                     RETURNING *
                        """,
                        (kanban_json, int(aula_id), id_clie),
                    )
                row = cur.fetchone()
                if row:
                    row = dict(row)
                    evento_id = _sync_agenda_evento(cur, row)
                    if evento_id:
                        row["id_evento_agenda"] = evento_id
                        cur.execute(
                            """
                            UPDATE public.inove_aulas_simples
                               SET id_evento_agenda = %s
                             WHERE id = %s AND id_clie = %s
                            """,
                            (evento_id, int(aula_id), id_clie),
                        )
                        row["id_evento_agenda"] = evento_id
    except pg_errors.UndefinedTable:
        return _table_missing_response()
    except Exception as exc:
        print(f"[daily] iniciar: {exc}", file=sys.stderr)
        return jsonify({"success": False, "error": "Falha ao iniciar aula"}), 500

    if not row:
        return jsonify({"success": False, "error": "Aula não encontrada"}), 404
    return jsonify({"success": True, "aula": _serialize(row)})


@daily_bp.post("/api/daily/<int:aula_id>/encerrar")
def encerrar_aula(aula_id: int):
    """
    Modo Aula — Encerrar: cards → Pronto, data_conclusao = agora, status realizado.
    Pode ser chamado horas/dias depois se o professor esqueceu de encerrar.
    """
    user = _require_user()
    if not user:
        return jsonify({"success": False, "error": "Não autenticado"}), 401

    id_clie = int(user["id_clie"])
    try:
        with get_conn() as conn:
            _prepare_conn(conn)
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                existing = _fetch_aula_row(cur, aula_id)
                denied = _authorize_owner(existing, id_clie)
                if denied:
                    return denied

                status = normalize_status(existing.get("status")) or "draft"
                if status == "realizado":
                    # Idempotente: devolve a aula já encerrada (FE abre feedback se preciso)
                    return jsonify({"success": True, "aula": _serialize(dict(existing))})
                if status != "em_execucao":
                    return (
                        jsonify(
                            {
                                "success": False,
                                "error": "Só é possível encerrar uma aula em execução",
                                "status": status,
                            }
                        ),
                        409,
                    )

                kanban = _move_all_cards(
                    existing.get("kanban_state"),
                    to_coluna="pronto",
                    nota="Encerramento da aula (lote)",
                )
                kanban_json = json.dumps(kanban, ensure_ascii=False)

                cur.execute(
                    """
                    UPDATE public.inove_aulas_simples
                       SET status = 'realizado',
                           data_conclusao = CURRENT_TIMESTAMP,
                           kanban_state = %s::jsonb,
                           updated_at = CURRENT_TIMESTAMP
                     WHERE id = %s AND id_clie = %s
                 RETURNING *
                    """,
                    (kanban_json, int(aula_id), id_clie),
                )
                row = cur.fetchone()
                if row:
                    row = dict(row)
                    evento_id = _sync_agenda_evento(cur, row)
                    if evento_id:
                        row["id_evento_agenda"] = evento_id
                        cur.execute(
                            """
                            UPDATE public.inove_aulas_simples
                               SET id_evento_agenda = %s
                             WHERE id = %s AND id_clie = %s
                            """,
                            (evento_id, int(aula_id), id_clie),
                        )
                        row["id_evento_agenda"] = evento_id
    except pg_errors.UndefinedTable:
        return _table_missing_response()
    except Exception as exc:
        print(f"[daily] encerrar: {exc}", file=sys.stderr)
        return jsonify({"success": False, "error": "Falha ao encerrar aula"}), 500

    if not row:
        return jsonify({"success": False, "error": "Aula não encontrada"}), 404
    return jsonify({"success": True, "aula": _serialize(row)})


@daily_bp.post("/api/daily/<int:aula_id>/feedback")
def feedback_aula(aula_id: int):
    """Retroalimentação pós-aula (Modo Aula / ClassFeedbackModal)."""
    user = _require_user()
    if not user:
        return jsonify({"success": False, "error": "Não autenticado"}), 401

    data = request.get_json(silent=True)
    if data is None or not isinstance(data, dict):
        return jsonify({"success": False, "error": "JSON inválido no body"}), 400

    id_clie = int(user["id_clie"])
    metodologia_ok = data.get("metodologia_ok")
    engajamento = str(data.get("engajamento") or "").strip().lower()
    estrutura_ok = data.get("estrutura_ok")
    observacoes = _clip(data.get("observacoes"), TEXT_LIMIT)

    if metodologia_ok is None or not isinstance(metodologia_ok, bool):
        return (
            jsonify({"success": False, "error": "metodologia_ok deve ser boolean"}),
            400,
        )
    if engajamento not in ("alto", "medio", "baixo"):
        return (
            jsonify(
                {"success": False, "error": "engajamento deve ser alto, medio ou baixo"}
            ),
            400,
        )
    if estrutura_ok is None or not isinstance(estrutura_ok, bool):
        return (
            jsonify({"success": False, "error": "estrutura_ok deve ser boolean"}),
            400,
        )

    feedback = {
        "metodologia_ok": metodologia_ok,
        "engajamento": engajamento,
        "estrutura_ok": estrutura_ok,
        "observacoes": observacoes,
        "registrado_em": datetime.utcnow().isoformat() + "Z",
    }

    try:
        with get_conn() as conn:
            _prepare_conn(conn)
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                existing = _fetch_aula_row(cur, aula_id)
                denied = _authorize_owner(existing, id_clie)
                if denied:
                    return denied

                status = normalize_status(existing.get("status")) or "draft"
                if status != "realizado":
                    return (
                        jsonify(
                            {
                                "success": False,
                                "error": "Feedback só após encerrar a aula",
                                "status": status,
                            }
                        ),
                        409,
                    )

                cur.execute(
                    """
                    UPDATE public.inove_aulas_simples
                       SET feedback_json = %s::jsonb,
                           updated_at = CURRENT_TIMESTAMP
                     WHERE id = %s AND id_clie = %s
                 RETURNING *
                    """,
                    (json.dumps(feedback, ensure_ascii=False), int(aula_id), id_clie),
                )
                row = cur.fetchone()
    except pg_errors.UndefinedTable:
        return _table_missing_response()
    except Exception as exc:
        print(f"[daily] feedback: {exc}", file=sys.stderr)
        return jsonify({"success": False, "error": "Falha ao salvar feedback"}), 500

    if not row:
        return jsonify({"success": False, "error": "Aula não encontrada"}), 404
    return jsonify({"success": True, "aula": _serialize(dict(row))})

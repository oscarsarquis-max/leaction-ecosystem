"""Integração S2S School → B2C: comunicados + planejamento escolar.

POST /api/integracoes/school/comunicados   — upsert mural (API key)
POST /api/integracoes/school/planejamento  — esqueleto aula/evento (mesmo upsert da importação)
GET  /api/mural                            — lista do professor autenticado
POST /api/mural/<id>/ciencia               — marca lido_em

Auth S2S: header X-School-Api-Key (ou Authorization: Bearer <key>)
  env SCHOOL_INTEGRATION_API_KEY (fallback INOVE4US_SCHOOL_API_KEY).
"""
from __future__ import annotations

import os
import sys
import uuid
from datetime import date, datetime, time
from typing import Any

from flask import Blueprint, jsonify, request, session
from psycopg2.extras import RealDictCursor, Json

from db import get_conn

school_integracao_bp = Blueprint("school_integracao", __name__)

TIPOS = frozenset({"reuniao_pedagogica", "evento_escolar"})
PLAN_TIPOS = frozenset({"aula", "evento"})
DEFAULT_DURACAO_MIN = 50
MAX_PLAN_ITENS = 500


def _api_key() -> str:
    return (
        os.environ.get("SCHOOL_INTEGRATION_API_KEY")
        or os.environ.get("INOVE4US_SCHOOL_API_KEY")
        or ""
    ).strip()


def _require_school_key():
    expected = _api_key()
    if not expected:
        return jsonify({"error": "SCHOOL_INTEGRATION_API_KEY não configurada"}), 503
    got = (request.headers.get("X-School-Api-Key") or "").strip()
    if not got:
        auth = (request.headers.get("Authorization") or "").strip()
        if auth.lower().startswith("bearer "):
            got = auth[7:].strip()
    if not got or got != expected:
        return jsonify({"error": "Não autorizado"}), 401
    return None


def _parse_uuid(value: Any, label: str):
    try:
        return uuid.UUID(str(value))
    except (ValueError, TypeError, AttributeError):
        return None


def _parse_dt(value: Any):
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value
    text = str(value).strip()
    if not text:
        return None
    # Aceita ISO com Z
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def _normalize_professor_ids(raw: Any) -> list[int]:
    """School envia professor_b2c_id = id_clie (inteiro) do B2C."""
    if raw is None:
        return []
    if isinstance(raw, (str, int)):
        raw = [raw]
    if not isinstance(raw, list):
        return []
    out: list[int] = []
    seen: set[int] = set()
    for item in raw:
        try:
            # UUID com só dígitos no final ou inteiro direto
            if isinstance(item, int):
                n = item
            else:
                s = str(item).strip()
                if not s:
                    continue
                # aceita UUID nil-padded? não — só int ou string numérica
                n = int(s)
            if n > 0 and n not in seen:
                seen.add(n)
                out.append(n)
        except (TypeError, ValueError):
            continue
    return out


def _ensure_schema(conn) -> None:
    """Idempotente se a migration ainda não rodou no ambiente."""
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS public.inove_comunicados_escola (
                id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                origem_comunicado_school_id UUID NOT NULL,
                instituicao_escola_id       UUID,
                titulo                      TEXT NOT NULL,
                descricao                   TEXT,
                tipo                        TEXT NOT NULL,
                data_hora_inicio            TIMESTAMPTZ,
                data_hora_fim               TIMESTAMPTZ,
                status                      TEXT NOT NULL DEFAULT 'ativo',
                created_at                  TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at                  TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT uq_inove_comunicados_origem_school
                    UNIQUE (origem_comunicado_school_id)
            );
            CREATE TABLE IF NOT EXISTS public.inove_comunicados_escola_destinatarios (
                id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                comunicado_id   UUID NOT NULL
                    REFERENCES public.inove_comunicados_escola (id) ON DELETE CASCADE,
                id_clie         INTEGER NOT NULL
                    REFERENCES public.ctdi_clie (id_clie) ON DELETE CASCADE,
                agenda_evento_id INTEGER
                    REFERENCES public.inove_agenda_eventos (id_evento) ON DELETE SET NULL,
                lido_em         TIMESTAMPTZ,
                created_at      TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at      TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT uq_inove_comunicados_dest_prof
                    UNIQUE (comunicado_id, id_clie)
            );
            ALTER TABLE public.inove_agenda_eventos
                ADD COLUMN IF NOT EXISTS comunicado_escola_id UUID;
            """
        )


def _upsert_agenda_for_professor(
    cur: Any,
    *,
    id_clie: int,
    comunicado_id: uuid.UUID,
    titulo: str,
    descricao: str | None,
    tipo_comunicado: str,
    data_inicio: datetime,
    data_fim: datetime | None,
    status_com: str,
) -> int | None:
    """Cria/atualiza evento na agenda. Retorna id_evento ou None se cancelado/sem data."""
    if status_com == "cancelado":
        cur.execute(
            """
            UPDATE public.inove_agenda_eventos
            SET status = 'cancelado',
                titulo = %s,
                nota_texto = %s
            WHERE comunicado_escola_id = %s AND id_clie = %s
            RETURNING id_evento
            """,
            (titulo, descricao or "", str(comunicado_id), int(id_clie)),
        )
        row = cur.fetchone()
        return int(row["id_evento"]) if row else None

    tipo_label = (
        "Reunião pedagógica"
        if tipo_comunicado == "reuniao_pedagogica"
        else "Evento escolar"
    )
    meta = {
        "comunicado_escola": True,
        "tipo_comunicado": tipo_comunicado,
        "tipo_label": tipo_label,
        "somente_leitura": True,
    }
    if data_fim:
        meta["data_hora_fim"] = data_fim.isoformat()

    cur.execute(
        """
        SELECT id_evento
        FROM public.inove_agenda_eventos
        WHERE comunicado_escola_id = %s AND id_clie = %s
        LIMIT 1
        """,
        (str(comunicado_id), int(id_clie)),
    )
    existing = cur.fetchone()
    if existing:
        cur.execute(
            """
            UPDATE public.inove_agenda_eventos
            SET data_evento = %s,
                titulo = %s,
                nota_texto = %s,
                tipo = 'geral',
                origem = 'comunicado_escola',
                status = 'planejado',
                meta_json = %s,
                comunicado_escola_id = %s
            WHERE id_evento = %s
            RETURNING id_evento
            """,
            (
                data_inicio.replace(tzinfo=None) if data_inicio.tzinfo else data_inicio,
                titulo[:200],
                descricao or "",
                Json(meta),
                str(comunicado_id),
                int(existing["id_evento"]),
            ),
        )
        return int(cur.fetchone()["id_evento"])

    cur.execute(
        """
        INSERT INTO public.inove_agenda_eventos (
            id_clie, data_evento, titulo, nota_texto, tipo, origem,
            status, meta_json, comunicado_escola_id
        )
        VALUES (%s, %s, %s, %s, 'geral', 'comunicado_escola', 'planejado', %s, %s)
        RETURNING id_evento
        """,
        (
            int(id_clie),
            data_inicio.replace(tzinfo=None) if data_inicio.tzinfo else data_inicio,
            titulo[:200],
            descricao or "",
            Json(meta),
            str(comunicado_id),
        ),
    )
    return int(cur.fetchone()["id_evento"])


@school_integracao_bp.post("/api/integracoes/school/comunicados")
def upsert_comunicado_school():
    denied = _require_school_key()
    if denied:
        return denied

    body = request.get_json(silent=True) or {}
    origem_id = _parse_uuid(
        body.get("origem_comunicado_school_id") or body.get("id"),
        "origem",
    )
    if not origem_id:
        return jsonify({"error": "origem_comunicado_school_id inválido"}), 400

    titulo = str(body.get("titulo") or "").strip()
    if not titulo:
        return jsonify({"error": "Informe o título"}), 400

    tipo = str(body.get("tipo") or "").strip()
    if tipo not in TIPOS:
        return jsonify({"error": "tipo inválido", "permitidos": sorted(TIPOS)}), 400

    status = str(body.get("status") or "ativo").strip().lower()
    if status in ("agendado", "publicado"):
        status = "ativo"
    if status not in ("ativo", "cancelado"):
        return jsonify({"error": "status inválido"}), 400

    descricao = str(body.get("descricao") or "").strip() or None
    inst_id = _parse_uuid(body.get("instituicao_escola_id"), "instituição")
    data_inicio = _parse_dt(body.get("data_hora_inicio"))
    data_fim = _parse_dt(body.get("data_hora_fim"))

    professor_ids = _normalize_professor_ids(
        body.get("professor_b2c_ids")
        or body.get("publico_alvo_professor_ids")
        or body.get("professores")
    )
    professor_emails = body.get("professor_emails") or body.get("emails") or []
    if isinstance(professor_emails, str):
        professor_emails = [professor_emails]
    if not isinstance(professor_emails, list):
        professor_emails = []

    if body.get("todos_vinculados") and not professor_ids and not professor_emails:
        return (
            jsonify(
                {
                    "error": (
                        "Envie professor_b2c_ids (id_clie) e/ou professor_emails; "
                        "este endpoint não consulta o School."
                    )
                }
            ),
            400,
        )
    if not professor_ids and not professor_emails and status != "cancelado":
        return jsonify(
            {"error": "Informe professor_b2c_ids (id_clie) e/ou professor_emails"}
        ), 400

    try:
        with get_conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                _ensure_schema(conn)

                # Resolve e-mails → id_clie (mesma chave usada em TEACHER_ALLOCATED).
                for raw_email in professor_emails:
                    email = str(raw_email or "").strip().lower()
                    if not email or "@" not in email:
                        continue
                    cur.execute(
                        """
                        SELECT id_clie
                        FROM public.ctdi_clie
                        WHERE LOWER(TRIM(mail_clie)) = %s
                        LIMIT 1
                        """,
                        (email,),
                    )
                    row_email = cur.fetchone()
                    if row_email and int(row_email["id_clie"]) not in professor_ids:
                        professor_ids.append(int(row_email["id_clie"]))

                cur.execute(
                    """
                    INSERT INTO public.inove_comunicados_escola (
                        origem_comunicado_school_id,
                        instituicao_escola_id,
                        titulo,
                        descricao,
                        tipo,
                        data_hora_inicio,
                        data_hora_fim,
                        status
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (origem_comunicado_school_id) DO UPDATE SET
                        instituicao_escola_id = EXCLUDED.instituicao_escola_id,
                        titulo = EXCLUDED.titulo,
                        descricao = EXCLUDED.descricao,
                        tipo = EXCLUDED.tipo,
                        data_hora_inicio = EXCLUDED.data_hora_inicio,
                        data_hora_fim = EXCLUDED.data_hora_fim,
                        status = EXCLUDED.status,
                        updated_at = CURRENT_TIMESTAMP
                    RETURNING *
                    """,
                    (
                        str(origem_id),
                        str(inst_id) if inst_id else None,
                        titulo,
                        descricao,
                        tipo,
                        data_inicio,
                        data_fim,
                        status,
                    ),
                )
                com = cur.fetchone()
                comunicado_id = uuid.UUID(str(com["id"]))

                # Valida professores existentes
                valid_ids: list[int] = []
                if professor_ids:
                    cur.execute(
                        "SELECT id_clie FROM public.ctdi_clie WHERE id_clie = ANY(%s)",
                        (professor_ids,),
                    )
                    valid_ids = [int(r["id_clie"]) for r in cur.fetchall()]

                missing = sorted(set(professor_ids) - set(valid_ids))
                agenda_ids: list[int] = []

                for id_clie in valid_ids:
                    evento_id = None
                    if data_inicio is not None:
                        evento_id = _upsert_agenda_for_professor(
                            cur,
                            id_clie=id_clie,
                            comunicado_id=comunicado_id,
                            titulo=titulo,
                            descricao=descricao,
                            tipo_comunicado=tipo,
                            data_inicio=data_inicio,
                            data_fim=data_fim,
                            status_com=status,
                        )
                        if evento_id:
                            agenda_ids.append(evento_id)

                    cur.execute(
                        """
                        INSERT INTO public.inove_comunicados_escola_destinatarios (
                            comunicado_id, id_clie, agenda_evento_id
                        )
                        VALUES (%s, %s, %s)
                        ON CONFLICT (comunicado_id, id_clie) DO UPDATE SET
                            agenda_evento_id = COALESCE(
                                EXCLUDED.agenda_evento_id,
                                inove_comunicados_escola_destinatarios.agenda_evento_id
                            ),
                            updated_at = CURRENT_TIMESTAMP
                        """,
                        (str(comunicado_id), int(id_clie), evento_id),
                    )

                # Remover destinatários que saíram da lista (exceto em cancelamento)
                if status == "ativo" and valid_ids:
                    cur.execute(
                        """
                        DELETE FROM public.inove_comunicados_escola_destinatarios
                        WHERE comunicado_id = %s
                          AND NOT (id_clie = ANY(%s))
                        """,
                        (str(comunicado_id), valid_ids),
                    )

        return (
            jsonify(
                {
                    "ok": True,
                    "id": str(comunicado_id),
                    "origem_comunicado_school_id": str(origem_id),
                    "status": status,
                    "destinatarios": len(valid_ids),
                    "professores_nao_encontrados": missing,
                    "agenda_eventos": agenda_ids,
                    "mural_only": data_inicio is None,
                }
            ),
            200,
        )
    except Exception as exc:
        print(f"⚠️ school comunicados: {exc}", file=sys.stderr)
        return jsonify({"error": "Falha ao gravar comunicado"}), 500


@school_integracao_bp.get("/api/mural")
def listar_mural():
    user = session.get("user") or {}
    id_clie = user.get("id_clie")
    if not id_clie:
        return jsonify({"error": "Não autenticado"}), 401

    include_lidos = request.args.get("include_lidos") in ("1", "true", "yes")

    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            _ensure_schema(conn)
            cur.execute(
                f"""
                SELECT
                    c.id,
                    c.origem_comunicado_school_id,
                    c.instituicao_escola_id,
                    c.titulo,
                    c.descricao,
                    c.tipo,
                    c.data_hora_inicio,
                    c.data_hora_fim,
                    c.status,
                    c.created_at,
                    c.updated_at,
                    d.lido_em,
                    d.agenda_evento_id
                FROM public.inove_comunicados_escola c
                JOIN public.inove_comunicados_escola_destinatarios d
                  ON d.comunicado_id = c.id
                WHERE d.id_clie = %s
                  AND c.status = 'ativo'
                  {"AND d.lido_em IS NULL" if not include_lidos else ""}
                ORDER BY
                    COALESCE(c.data_hora_inicio, c.created_at) DESC,
                    c.created_at DESC
                LIMIT 50
                """,
                (int(id_clie),),
            )
            rows = cur.fetchall()

    items = []
    for r in rows:
        items.append(
            {
                "id": str(r["id"]),
                "origem_comunicado_school_id": str(r["origem_comunicado_school_id"]),
                "instituicao_escola_id": (
                    str(r["instituicao_escola_id"]) if r.get("instituicao_escola_id") else None
                ),
                "titulo": r["titulo"],
                "descricao": r.get("descricao"),
                "tipo": r["tipo"],
                "tipo_label": (
                    "Reunião pedagógica"
                    if r["tipo"] == "reuniao_pedagogica"
                    else "Evento escolar"
                ),
                "data_hora_inicio": (
                    r["data_hora_inicio"].isoformat() if r.get("data_hora_inicio") else None
                ),
                "data_hora_fim": (
                    r["data_hora_fim"].isoformat() if r.get("data_hora_fim") else None
                ),
                "lido_em": r["lido_em"].isoformat() if r.get("lido_em") else None,
                "agenda_evento_id": r.get("agenda_evento_id"),
                "created_at": r["created_at"].isoformat() if r.get("created_at") else None,
            }
        )

    return jsonify({"items": items, "total": len(items)})


@school_integracao_bp.post("/api/mural/<comunicado_id>/ciencia")
def marcar_ciencia(comunicado_id: str):
    user = session.get("user") or {}
    id_clie = user.get("id_clie")
    if not id_clie:
        return jsonify({"error": "Não autenticado"}), 401
    cid = _parse_uuid(comunicado_id, "comunicado")
    if not cid:
        return jsonify({"error": "Identificador inválido"}), 400

    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                UPDATE public.inove_comunicados_escola_destinatarios
                SET lido_em = COALESCE(lido_em, CURRENT_TIMESTAMP),
                    updated_at = CURRENT_TIMESTAMP
                WHERE comunicado_id = %s AND id_clie = %s
                RETURNING lido_em
                """,
                (str(cid), int(id_clie)),
            )
            row = cur.fetchone()
            if not row:
                return jsonify({"error": "Comunicado não encontrado"}), 404

    return jsonify({"ok": True, "lido_em": row["lido_em"].isoformat()})


# ---------------------------------------------------------------------------
# Planejamento Escolar (School → mesmo destino da importação / pull)
# ---------------------------------------------------------------------------
def _parse_plan_date(value: Any) -> date | None:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    text = str(value or "").strip()[:10]
    if not text:
        return None
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def _parse_plan_time(value: Any) -> time | None:
    if value is None or value == "":
        return None
    if isinstance(value, time):
        return value
    if isinstance(value, datetime):
        return value.time().replace(microsecond=0)
    text = str(value).strip()
    if not text:
        return None
    if len(text) >= 8:
        try:
            return datetime.strptime(text[:8], "%H:%M:%S").time()
        except ValueError:
            pass
    try:
        return datetime.strptime(text[:5], "%H:%M").time()
    except ValueError:
        return None


@school_integracao_bp.post("/api/integracoes/school/planejamento")
def receber_planejamento_school():
    """Recebe lote da Secretaria e grava via upsert da importação (agenda + draft).

    Body:
      {
        "professor_b2c_id": 12345,
        "itens": [{
          "id_externo": "<uuid school>",
          "titulo": "...",
          "tipo": "aula"|"evento",
          "data": "YYYY-MM-DD",
          "hora_inicio": "HH:MM"|null,
          "hora_fim": "HH:MM"|null,
          "vinculo_pai_id_externo": "<id_externo>"|null,
          "observacoes": "..."
        }]
      }
    """
    denied = _require_school_key()
    if denied:
        return denied

    body = request.get_json(silent=True) or {}
    try:
        professor_b2c_id = int(body.get("professor_b2c_id"))
    except (TypeError, ValueError):
        professor_b2c_id = 0
    if professor_b2c_id <= 0:
        return jsonify({"error": "professor_b2c_id (id_clie) é obrigatório"}), 400

    itens_in = body.get("itens")
    if not isinstance(itens_in, list) or not itens_in:
        return jsonify({"error": "itens é obrigatório"}), 400
    if len(itens_in) > MAX_PLAN_ITENS:
        return jsonify({"error": f"Limite de {MAX_PLAN_ITENS} itens por lote"}), 400

    # Import lazy evita ciclo na carga do app
    from routes.importacoes_routes import (
        _ensure_import_schema,
        _find_agenda_by_externo,
        upsert_registro_importado,
    )

    relatorio: list[dict[str, Any]] = []
    prontos: list[dict[str, Any]] = []
    seen_ext: set[str] = set()

    for idx, raw in enumerate(itens_in, start=1):
        if not isinstance(raw, dict):
            relatorio.append(
                {
                    "linha": idx,
                    "id_externo": None,
                    "status": "erro",
                    "ok": False,
                    "mensagem": "item inválido",
                    "error": "item inválido",
                }
            )
            continue

        id_externo = str(raw.get("id_externo") or "").strip()[:160]
        titulo = str(raw.get("titulo") or "").strip()
        tipo = str(raw.get("tipo") or "aula").strip().lower()
        if tipo not in PLAN_TIPOS:
            tipo = "aula"
        data_val = _parse_plan_date(raw.get("data"))
        pai = str(raw.get("vinculo_pai_id_externo") or "").strip()[:160] or ""

        if not id_externo:
            relatorio.append(
                {
                    "linha": idx,
                    "id_externo": None,
                    "status": "erro",
                    "ok": False,
                    "mensagem": "id_externo ausente",
                    "error": "id_externo ausente",
                }
            )
            continue
        if id_externo in seen_ext:
            relatorio.append(
                {
                    "linha": idx,
                    "id_externo": id_externo,
                    "status": "erro",
                    "ok": False,
                    "mensagem": "id_externo duplicado no lote",
                    "error": "id_externo duplicado no lote",
                }
            )
            continue
        seen_ext.add(id_externo)
        if not titulo:
            relatorio.append(
                {
                    "linha": idx,
                    "id_externo": id_externo,
                    "status": "erro",
                    "ok": False,
                    "mensagem": "titulo ausente",
                    "error": "titulo ausente",
                }
            )
            continue
        if not data_val:
            relatorio.append(
                {
                    "linha": idx,
                    "id_externo": id_externo,
                    "status": "erro",
                    "ok": False,
                    "mensagem": "data inválida",
                    "error": "data inválida",
                }
            )
            continue

        prontos.append(
            {
                "line": idx,
                "id_externo": id_externo,
                "titulo": titulo[:200],
                "tipo": tipo,
                "data": data_val,
                "hora_inicio": _parse_plan_time(raw.get("hora_inicio")),
                "hora_fim": _parse_plan_time(raw.get("hora_fim")),
                "instituicao": "",
                "curso": "",
                "disciplina": "",
                "assunto": None,
                "vinculo_pai_id_externo": pai,
                "observacoes": str(raw.get("observacoes") or "").strip()[:4000] or None,
            }
        )

    total_sucesso = 0
    total_erro = len(relatorio)
    total_aviso = 0
    id_map: dict[str, int] = {}

    try:
        with get_conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    "SELECT id_clie FROM public.ctdi_clie WHERE id_clie = %s",
                    (professor_b2c_id,),
                )
                if not cur.fetchone():
                    return (
                        jsonify(
                            {
                                "error": "professor_b2c_id não encontrado no B2C",
                                "professor_b2c_id": professor_b2c_id,
                            }
                        ),
                        404,
                    )

                _ensure_import_schema(conn)
                # Reaproveita inove_importacoes_lote (canal=escola vs arquivo do professor).
                cur.execute(
                    """
                    INSERT INTO public.inove_importacoes_lote (
                        id_clie, nome_arquivo, formato, canal,
                        total_registros, total_sucesso, total_erro, total_aviso,
                        relatorio_json
                    ) VALUES (%s, %s, %s, 'escola', %s, 0, 0, 0, '[]'::jsonb)
                    RETURNING id
                    """,
                    (
                        professor_b2c_id,
                        "school-planejamento",
                        "json",
                        len(itens_in),
                    ),
                )
                lote_id = int(cur.fetchone()["id"])

                for row in prontos:
                    try:
                        id_evento, acao, aula_id = upsert_registro_importado(
                            cur,
                            id_clie=professor_b2c_id,
                            row=row,
                            disciplina_id=None,
                            duracao_min=DEFAULT_DURACAO_MIN,
                            lote_id=lote_id,
                            origem="planejamento_escola",
                            # is_from_school fica p/ alocação docente; aqui a origem já identifica.
                            is_from_school=False,
                        )
                        id_map[row["id_externo"]] = id_evento
                        cur.execute(
                            """
                            UPDATE public.inove_agenda_eventos
                               SET meta_json = COALESCE(meta_json, '{}'::jsonb)
                                 || %s::jsonb
                             WHERE id_evento = %s AND id_clie = %s
                            """,
                            (
                                Json({"school_lote_importacao_id": lote_id}),
                                id_evento,
                                professor_b2c_id,
                            ),
                        )
                        total_sucesso += 1
                        relatorio.append(
                            {
                                "linha": row["line"],
                                "id_externo": row["id_externo"],
                                "status": "sucesso",
                                "ok": True,
                                "acao": acao,
                                "id_evento": id_evento,
                                "aula_simples_id": aula_id,
                                "mensagem": "criado" if acao == "created" else "atualizado",
                            }
                        )
                    except Exception as exc:
                        print(
                            f"[school planejamento] item {row['id_externo']}: {exc}",
                            file=sys.stderr,
                        )
                        total_erro += 1
                        relatorio.append(
                            {
                                "linha": row["line"],
                                "id_externo": row["id_externo"],
                                "status": "erro",
                                "ok": False,
                                "mensagem": f"falha ao persistir: {exc}",
                                "error": str(exc),
                            }
                        )

                # Passada 2 — vínculos pai (igual importação)
                for row in prontos:
                    pai_ext = row.get("vinculo_pai_id_externo") or ""
                    if not pai_ext:
                        continue
                    id_evento = id_map.get(row["id_externo"])
                    if not id_evento:
                        continue
                    id_pai = id_map.get(pai_ext)
                    if not id_pai:
                        prev = _find_agenda_by_externo(cur, professor_b2c_id, pai_ext)
                        id_pai = int(prev["id_evento"]) if prev else None
                    if not id_pai or id_pai == id_evento:
                        if not id_pai:
                            total_aviso += 1
                            for item in relatorio:
                                if item.get("id_externo") == row["id_externo"] and item.get(
                                    "ok"
                                ):
                                    item["status"] = "aviso"
                                    item["mensagem"] = (
                                        (item.get("mensagem") or "")
                                        + f"; vinculo_pai '{pai_ext}' não resolvido"
                                    )
                                    break
                        continue
                    cur.execute(
                        """
                        UPDATE public.inove_agenda_eventos
                           SET id_evento_pai = %s
                         WHERE id_evento = %s AND id_clie = %s
                        """,
                        (id_pai, id_evento, professor_b2c_id),
                    )
                    for item in relatorio:
                        if item.get("id_externo") == row["id_externo"]:
                            item["id_evento_pai"] = id_pai
                            break

                relatorio.sort(key=lambda r: (r.get("linha") or 0,))
                cur.execute(
                    """
                    UPDATE public.inove_importacoes_lote
                       SET total_sucesso = %s,
                           total_erro = %s,
                           total_aviso = %s,
                           relatorio_json = %s
                     WHERE id = %s AND id_clie = %s
                    """,
                    (
                        total_sucesso,
                        total_erro,
                        total_aviso,
                        Json(relatorio),
                        lote_id,
                        professor_b2c_id,
                    ),
                )
    except Exception as exc:
        print(f"[school planejamento] lote: {exc}", file=sys.stderr)
        return jsonify({"error": str(exc)}), 500

    return jsonify(
        {
            "ok": total_erro == 0 and total_sucesso > 0,
            "professor_b2c_id": professor_b2c_id,
            "lote_id": lote_id,
            "total_sucesso": total_sucesso,
            "total_erro": total_erro,
            "total_aviso": total_aviso,
            "itens": relatorio,
            "relatorio": relatorio,
        }
    )

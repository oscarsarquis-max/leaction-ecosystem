"""153 — GET/POST/PATCH /api/secretaria/eventos. Dual-write nos pipelines 114/104."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from flask import Blueprint, jsonify, request, session
from psycopg2.extras import RealDictCursor

from auth_guards import SESSION_KEY, require_zona
from db import get_conn
from eventos_service import (
    BROADCAST_TIPOS,
    EVENTO_SELECT,
    com_tipo_for_evento,
    fetch_evento,
    gestor_ve_administradores,
    normalize_tipo_evento,
    serialize_evento,
    upsert_from_comunicado,
    upsert_from_planejamento,
)
from secretaria_routes import (
    _bloquear_se_conflito_plan,
    _dispatch_comunicacao_b2c,
    _fetch_comunicacao,
    _instituicao_id,
    _iso,
    _parse_dt_local,
    _parse_time,
    _parse_uuid,
    _resolver_alvo_comunicacao,
    _resolve_alocacao_professor,
    _text,
    _time_iso,
    _unidade_escopo,
)

bp = Blueprint("secretaria_eventos", __name__)
require_gestor = require_zona("operacional")


def _split_inicio(dt) -> tuple:
    if dt is None:
        return None, None
    local = dt
    if getattr(dt, "tzinfo", None):
        from eventos_service import TZ_ESCOLA

        local = dt.astimezone(TZ_ESCOLA)
    return local.date(), local.time().replace(microsecond=0)


def _push_aula(cur, inst: str, plan_id: str) -> dict[str, Any]:
    from secretaria_routes import _enviar_planejamento_rows

    cur.execute(
        """
        SELECT p.*,
               t.nome AS turma_nome,
               d.nome AS disciplina_nome,
               v.email_convite AS professor_email,
               v.professor_b2c_id
        FROM public.school_planejamento_escolar p
        JOIN public.school_turmas t ON t.id = p.turma_id
        JOIN public.school_disciplinas d ON d.id = p.disciplina_id
        JOIN public.school_professores_vinculo v ON v.id = p.professor_vinculo_id
        WHERE p.id = %s AND p.instituicao_id = %s
        """,
        (plan_id, inst),
    )
    row = cur.fetchone()
    if not row:
        return {"ok": False, "error": "planejamento não encontrado"}
    resultados = _enviar_planejamento_rows(cur, inst, [row])
    return resultados[0] if resultados else {"ok": False, "error": "envio vazio"}


@bp.get("/api/secretaria/eventos")
@require_gestor
def list_eventos():
    inst = _instituicao_id()
    escopo = _unidade_escopo()
    if isinstance(escopo, tuple):
        return escopo
    ve_admin = gestor_ve_administradores()
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            sql = EVENTO_SELECT + " WHERE e.instituicao_id = %s"
            params: list[Any] = [inst]
            if escopo:
                sql += " AND (e.unidade_id = %s OR t.unidade_id = %s OR e.tipo_evento = 'aula')"
                params.extend([escopo, escopo])
            if not ve_admin:
                sql += " AND (e.publico_alvo IS DISTINCT FROM 'administradores')"
            sql += " ORDER BY e.data_hora_inicio DESC, e.created_at DESC"
            cur.execute(sql, params)
            rows = [serialize_evento(r) for r in cur.fetchall()]
    return jsonify({"items": rows})


@bp.post("/api/secretaria/eventos")
@require_gestor
def create_evento():
    inst = _instituicao_id()
    body = request.get_json(silent=True) or {}
    tipo = normalize_tipo_evento(body.get("tipo_evento") or body.get("tipo"))
    if not tipo:
        return jsonify({"error": "tipo_evento inválido"}), 400
    titulo = _text(body.get("titulo"))
    if not titulo:
        return jsonify({"error": "Título obrigatório"}), 400
    inicio = _parse_dt_local(body.get("data_hora_inicio"), required=True)
    if inicio is False or inicio is None:
        return jsonify({"error": "data_hora_inicio inválida ou obrigatória"}), 400
    fim = _parse_dt_local(body.get("data_hora_fim"), required=False)
    if fim is False:
        return jsonify({"error": "data_hora_fim inválida"}), 400
    descricao = _text(body.get("descricao")) or None
    gestor = session.get(SESSION_KEY) or {}
    gestor_id = _parse_uuid(gestor.get("id"), "gestor")

    if tipo == "aula":
        return _create_aula(inst, body, titulo, descricao, inicio, fim, gestor_id)
    return _create_broadcast(
        inst, body, tipo, titulo, descricao, inicio, fim, gestor_id
    )


def _create_broadcast(inst, body, tipo, titulo, descricao, inicio, fim, gestor_id):
    publico = _text(body.get("publico_alvo")) or "professores"
    from secretaria_routes import COM_PUBLICOS

    if publico not in COM_PUBLICOS:
        return jsonify({"error": "Público-alvo inválido"}), 400
    if publico == "administradores" and not gestor_ve_administradores():
        return jsonify({"error": "Só administradores publicam para administradores"}), 403

    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            unidade, turma, disciplina, alvo_err = _resolver_alvo_comunicacao(
                cur,
                inst,
                publico,
                body.get("unidade_id"),
                body.get("turma_id"),
                body.get("disciplina_id"),
            )
            if alvo_err:
                return alvo_err
            cur.execute(
                """
                INSERT INTO public.school_comunicacoes_eventos (
                    instituicao_id, unidade_id, turma_id, disciplina_id, titulo, descricao,
                    tipo, tipo_evento, data_hora_inicio, data_hora_fim, publico_alvo,
                    status, criado_por_gestor_id
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'publicado', %s
                )
                RETURNING *
                """,
                (
                    inst,
                    unidade,
                    turma,
                    disciplina,
                    titulo,
                    descricao,
                    com_tipo_for_evento(tipo),
                    tipo,
                    inicio,
                    fim,
                    publico,
                    str(gestor_id) if gestor_id else None,
                ),
            )
            com = cur.fetchone()
            upsert_from_comunicado(cur, com, tipo_evento=tipo)
            cur.execute(
                "SELECT id FROM public.school_eventos WHERE origem_comunicado_id = %s",
                (str(com["id"]),),
            )
            ev_id = str(cur.fetchone()["id"])

    dispatch = {"ok": True, "skipped": True, "reason": "administradores_school_only"}
    if publico != "administradores":
        dispatch = _dispatch_comunicacao_b2c(com, inst)
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            if publico != "administradores":
                cur.execute(
                    """
                    UPDATE public.school_eventos e
                    SET replicado_b2c = c.replicado_b2c,
                        replicado_b2c_em = c.replicado_b2c_em,
                        updated_at = CURRENT_TIMESTAMP
                    FROM public.school_comunicacoes_eventos c
                    WHERE e.origem_comunicado_id = c.id AND e.id = %s
                    """,
                    (ev_id,),
                )
            row = fetch_evento(cur, inst, ev_id)

    return (
        jsonify(
            {
                "item": serialize_evento(row),
                "b2c_dispatch": dispatch,
                "message": _feedback_broadcast(publico, dispatch),
            }
        ),
        201,
    )


def _create_aula(inst, body, titulo, descricao, inicio, fim, gestor_id):
    turma_id = _parse_uuid(body.get("turma_id"), "turma")
    disciplina_id = _parse_uuid(body.get("disciplina_id"), "disciplina")
    if not turma_id or not disciplina_id:
        return jsonify({"error": "Aula exige turma e disciplina da alocação"}), 400
    data_ref, hora_inicio = _split_inicio(inicio)
    _, hora_fim = _split_inicio(fim) if fim else (None, None)
    if hora_fim is None:
        hora_fim = _parse_time(body.get("hora_fim"))

    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            aloc = _resolve_alocacao_professor(
                cur, inst, str(turma_id), str(disciplina_id)
            )
            if not aloc:
                return (
                    jsonify(
                        {
                            "error": (
                                "Nenhum professor alocado pra essa turma/disciplina ainda. "
                                "Faça a alocação docente na Estrutura Acadêmica."
                            )
                        }
                    ),
                    422,
                )
            denied_cf = _bloquear_se_conflito_plan(
                cur,
                inst=inst,
                data_ref=data_ref,
                hora_inicio=hora_inicio,
                hora_fim=hora_fim,
                turma_id=str(turma_id),
                professor_vinculo_id=str(aloc["professor_vinculo_id"]),
                titulo=titulo,
                substituicao=False,
            )
            if denied_cf:
                return denied_cf
            cur.execute(
                """
                INSERT INTO public.school_planejamento_escolar (
                    instituicao_id, turma_id, disciplina_id, professor_vinculo_id,
                    titulo, tipo, data, hora_inicio, hora_fim, observacoes
                )
                VALUES (%s, %s, %s, %s, %s, 'aula', %s, %s, %s, %s)
                RETURNING *
                """,
                (
                    inst,
                    str(turma_id),
                    str(disciplina_id),
                    str(aloc["professor_vinculo_id"]),
                    titulo,
                    data_ref,
                    hora_inicio,
                    hora_fim,
                    descricao,
                ),
            )
            plan = cur.fetchone()
            envio = _push_aula(cur, inst, str(plan["id"]))
            cur.execute(
                "SELECT * FROM public.school_planejamento_escolar WHERE id = %s",
                (str(plan["id"]),),
            )
            plan = cur.fetchone()
            upsert_from_planejamento(cur, plan)
            cur.execute(
                """
                UPDATE public.school_eventos
                SET criado_por_gestor_id = %s,
                    replicado_b2c = %s,
                    replicado_b2c_em = CASE WHEN %s THEN CURRENT_TIMESTAMP ELSE NULL END
                WHERE origem_planejamento_id = %s
                RETURNING id
                """,
                (
                    str(gestor_id) if gestor_id else None,
                    bool(envio.get("status_push") == "enviado" or envio.get("ok")),
                    bool(envio.get("status_push") == "enviado" or envio.get("ok")),
                    str(plan["id"]),
                ),
            )
            ev_id = str(cur.fetchone()["id"])
            row = fetch_evento(cur, inst, ev_id)

    code = 201
    if envio.get("status_push") == "erro" or envio.get("ok") is False:
        msg = "Aula gravada. Envio à agenda do professor falhou."
        if envio.get("resposta", {}).get("error") or envio.get("error"):
            msg += " " + str(envio.get("resposta", {}).get("error") or envio.get("error"))
    else:
        msg = "Aula criada na agenda do professor."
    return (
        jsonify({"item": serialize_evento(row), "b2c_dispatch": envio, "message": msg}),
        code,
    )


@bp.patch("/api/secretaria/eventos/<item_id>")
@require_gestor
def patch_evento(item_id: str):
    inst = _instituicao_id()
    eid = _parse_uuid(item_id, "evento")
    if not eid:
        return jsonify({"error": "Identificador inválido"}), 400
    body = request.get_json(silent=True) or {}

    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            existing = fetch_evento(cur, inst, str(eid))
            if not existing:
                return jsonify({"error": "Evento não encontrado"}), 404
            if (
                existing.get("publico_alvo") == "administradores"
                and not gestor_ve_administradores()
            ):
                return jsonify({"error": "Evento não encontrado"}), 404

    tipo = str(existing["tipo_evento"])
    if tipo == "aula":
        return _patch_aula(inst, str(eid), existing, body)
    return _patch_broadcast(inst, str(eid), existing, body)


def _patch_broadcast(inst, eid, existing, body):
    cid = existing.get("origem_comunicado_id")
    if not cid:
        return jsonify({"error": "Evento sem comunicado de origem"}), 409
    from secretaria_routes import COM_PUBLICOS, COM_STATUS, _parse_comunicacao_body

    if body.get("status") == "cancelado" and len(body) == 1:
        parsed_status = "cancelado"
        with get_conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                com = _fetch_comunicacao(cur, inst, str(cid))
                if not com:
                    return jsonify({"error": "Comunicado de origem não encontrado"}), 404
                cur.execute(
                    """
                    UPDATE public.school_comunicacoes_eventos
                    SET status = 'cancelado', updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s AND instituicao_id = %s
                    RETURNING *
                    """,
                    (str(cid), inst),
                )
                com = cur.fetchone()
                cur.execute(
                    """
                    UPDATE public.school_eventos
                    SET status = 'cancelado', updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                    """,
                    (eid,),
                )
        dispatch = {"ok": True, "skipped": True}
        if com.get("publico_alvo") != "administradores":
            dispatch = _dispatch_comunicacao_b2c(com, inst)
        with get_conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                row = fetch_evento(cur, inst, eid)
        return jsonify(
            {
                "item": serialize_evento(row),
                "b2c_dispatch": dispatch,
                "message": _feedback_broadcast(str(com.get("publico_alvo") or ""), dispatch)
                if parsed_status != "cancelado"
                else (
                    "Evento cancelado."
                    if dispatch.get("ok")
                    else "Evento cancelado. Agenda do mural ainda não foi limpa."
                ),
            }
        )

    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            com = _fetch_comunicacao(cur, inst, str(cid))
            if not com:
                return jsonify({"error": "Comunicado de origem não encontrado"}), 404
            merged = {
                "titulo": body["titulo"] if "titulo" in body else com["titulo"],
                "descricao": body["descricao"] if "descricao" in body else com.get("descricao"),
                "tipo": com_tipo_for_evento(
                    normalize_tipo_evento(body.get("tipo_evento")) or existing["tipo_evento"]
                ),
                "publico_alvo": body["publico_alvo"]
                if "publico_alvo" in body
                else com["publico_alvo"],
                "status": body["status"] if "status" in body else com["status"],
                "data_hora_inicio": body["data_hora_inicio"]
                if "data_hora_inicio" in body
                else _iso(com.get("data_hora_inicio")),
                "data_hora_fim": body["data_hora_fim"]
                if "data_hora_fim" in body
                else _iso(com.get("data_hora_fim")),
                "unidade_id": body["unidade_id"] if "unidade_id" in body else com.get("unidade_id"),
                "turma_id": body["turma_id"] if "turma_id" in body else com.get("turma_id"),
                "disciplina_id": body["disciplina_id"]
                if "disciplina_id" in body
                else com.get("disciplina_id"),
            }
            parsed, err = _parse_comunicacao_body(merged)
            if err:
                return err
            if parsed["publico"] not in COM_PUBLICOS:
                return jsonify({"error": "Público-alvo inválido"}), 400
            if parsed["status"] not in COM_STATUS:
                return jsonify({"error": "Status inválido"}), 400
            unidade, turma, disciplina, alvo_err = _resolver_alvo_comunicacao(
                cur,
                inst,
                parsed["publico"],
                parsed["unidade_raw"],
                parsed["turma_raw"],
                parsed.get("disciplina_raw"),
            )
            if alvo_err:
                return alvo_err
            tipo_ev = (
                normalize_tipo_evento(body.get("tipo_evento")) or existing["tipo_evento"]
            )
            if tipo_ev not in BROADCAST_TIPOS:
                return jsonify({"error": "tipo_evento inválido para broadcast"}), 400
            cur.execute(
                """
                UPDATE public.school_comunicacoes_eventos
                SET titulo = %s, descricao = %s, tipo = %s, tipo_evento = %s,
                    publico_alvo = %s, unidade_id = %s, turma_id = %s, disciplina_id = %s,
                    data_hora_inicio = %s, data_hora_fim = %s, status = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s AND instituicao_id = %s
                RETURNING *
                """,
                (
                    parsed["titulo"],
                    parsed["descricao"],
                    parsed["tipo"],
                    tipo_ev,
                    parsed["publico"],
                    unidade,
                    turma,
                    disciplina,
                    parsed["inicio"],
                    parsed["fim"],
                    parsed["status"],
                    str(cid),
                    inst,
                ),
            )
            com = cur.fetchone()
            upsert_from_comunicado(cur, com, tipo_evento=tipo_ev)

    dispatch = {"ok": True, "skipped": True, "reason": "administradores_school_only"}
    if com.get("publico_alvo") != "administradores":
        dispatch = _dispatch_comunicacao_b2c(com, inst)
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            row = fetch_evento(cur, inst, eid)
    return jsonify(
        {
            "item": serialize_evento(row),
            "b2c_dispatch": dispatch,
            "message": _feedback_broadcast(str(com.get("publico_alvo") or ""), dispatch),
        }
    )


def _patch_aula(inst, eid, existing, body):
    pid = existing.get("origem_planejamento_id")
    if not pid:
        return jsonify({"error": "Evento sem aula de origem"}), 409
    if body.get("status") == "cancelado":
        with get_conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT status_push FROM public.school_planejamento_escolar
                    WHERE id = %s AND instituicao_id = %s
                    """,
                    (str(pid), inst),
                )
                plan = cur.fetchone()
                if not plan:
                    return jsonify({"error": "Aula de origem não encontrada"}), 404
                if plan["status_push"] == "rascunho":
                    cur.execute(
                        "DELETE FROM public.school_planejamento_escolar WHERE id = %s",
                        (str(pid),),
                    )
                    cur.execute("DELETE FROM public.school_eventos WHERE id = %s", (eid,))
                    return jsonify({"ok": True, "message": "Aula em rascunho excluída."})
                cur.execute(
                    """
                    UPDATE public.school_eventos
                    SET status = 'cancelado', updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                    """,
                    (eid,),
                )
                row = fetch_evento(cur, inst, eid)
        return jsonify(
            {
                "item": serialize_evento(row),
                "message": (
                    "Evento cancelado na Agenda da Secretaria. "
                    "A aula já enviada ao professor permanece na agenda dele."
                ),
            }
        )

    titulo = _text(body["titulo"]) if "titulo" in body else existing["titulo"]
    if not titulo:
        return jsonify({"error": "Título obrigatório"}), 400
    descricao = (
        _text(body.get("descricao")) or None
        if "descricao" in body
        else existing.get("descricao")
    )
    if "data_hora_inicio" in body:
        inicio = _parse_dt_local(body.get("data_hora_inicio"), required=True)
        if inicio is False or inicio is None:
            return jsonify({"error": "data_hora_inicio inválida"}), 400
    else:
        inicio = existing.get("data_hora_inicio")
    if "data_hora_fim" in body:
        fim = _parse_dt_local(body.get("data_hora_fim"), required=False)
        if fim is False:
            return jsonify({"error": "data_hora_fim inválida"}), 400
    else:
        fim = existing.get("data_hora_fim")
    turma_id = _parse_uuid(body.get("turma_id"), "turma") if body.get("turma_id") else existing.get("turma_id")
    disciplina_id = (
        _parse_uuid(body.get("disciplina_id"), "disciplina")
        if body.get("disciplina_id")
        else existing.get("disciplina_id")
    )
    if not turma_id or not disciplina_id:
        return jsonify({"error": "Aula exige turma e disciplina"}), 400
    data_ref, hora_inicio = _split_inicio(inicio)
    _, hora_fim = _split_inicio(fim) if fim else (None, None)

    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            aloc = _resolve_alocacao_professor(
                cur, inst, str(turma_id), str(disciplina_id)
            )
            if not aloc:
                return (
                    jsonify(
                        {
                            "error": (
                                "Nenhum professor alocado pra essa turma/disciplina ainda."
                            )
                        }
                    ),
                    422,
                )
            denied_cf = _bloquear_se_conflito_plan(
                cur,
                inst=inst,
                data_ref=data_ref,
                hora_inicio=hora_inicio,
                hora_fim=hora_fim,
                turma_id=str(turma_id),
                professor_vinculo_id=str(aloc["professor_vinculo_id"]),
                exclude_id=str(pid),
                titulo=titulo,
                substituicao=False,
            )
            if denied_cf:
                return denied_cf
            cur.execute(
                """
                UPDATE public.school_planejamento_escolar
                SET turma_id = %s,
                    disciplina_id = %s,
                    professor_vinculo_id = %s,
                    titulo = %s,
                    data = %s,
                    hora_inicio = %s,
                    hora_fim = %s,
                    observacoes = %s,
                    status_push = CASE
                        WHEN status_push = 'enviado' THEN 'enviado'
                        ELSE 'rascunho'
                    END,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s AND instituicao_id = %s
                RETURNING *
                """,
                (
                    str(turma_id),
                    str(disciplina_id),
                    str(aloc["professor_vinculo_id"]),
                    titulo,
                    data_ref,
                    hora_inicio,
                    hora_fim,
                    descricao,
                    str(pid),
                    inst,
                ),
            )
            plan = cur.fetchone()
            envio = _push_aula(cur, inst, str(pid))
            cur.execute(
                "SELECT * FROM public.school_planejamento_escolar WHERE id = %s",
                (str(pid),),
            )
            plan = cur.fetchone()
            upsert_from_planejamento(cur, plan)
            row = fetch_evento(cur, inst, eid)

    return jsonify(
        {
            "item": serialize_evento(row),
            "b2c_dispatch": envio,
            "message": "Aula atualizada na agenda do professor."
            if envio.get("status_push") == "enviado" or envio.get("ok")
            else "Aula gravada. Reenvio à agenda falhou.",
        }
    )


def _feedback_broadcast(publico: str, dispatch: dict[str, Any]) -> str:
    if publico == "administradores":
        return "Evento publicado só para administradores da Secretaria."
    if dispatch.get("ok"):
        return "Evento publicado no mural dos professores."
    if dispatch.get("skipped"):
        return "Evento salvo."
    err = str(dispatch.get("error") or "").strip()
    extra = f" {err}" if err else ""
    return f"Evento salvo. Não replicado no mural.{extra}"

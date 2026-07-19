"""Rotas RBAC — execução, notificações e carteira consultor."""

from __future__ import annotations

from flask import Blueprint, jsonify, request
from psycopg2.extras import RealDictCursor

from rbac.constants import ROLE_CONSULTOR, ROLE_EXECUTOR, ROLE_LED, ROLE_SYSADMIN
from rbac.context import resolve_rbac_context
from rbac.decorators import require_role
from rbac.capacity import rbac_validar_capacidade_squad
from rbac.scope import rbac_filtro_atividades_sql

rbac_bp = Blueprint("rbac", __name__)


def _get_conn():
    from app import get_db_conn
    return get_db_conn()


@rbac_bp.route("/api/execucao/tarefas", methods=["GET"])
@require_role(ROLE_EXECUTOR, ROLE_SYSADMIN)
def rbac_listar_tarefas_executor():
    """Fila de atribuições do executor (Sala de Execução)."""
    ctx = resolve_rbac_context()
    conn = _get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        where_extra, params = rbac_filtro_atividades_sql(ctx, alias="a")
        cur.execute(
            f"""
            SELECT a.id_ativ, a.id_sprn, a.id_kr, a.nome_ativ, a.desc_ativ,
                   a.status_ativ, a.data_planejamento, a.data_conclusao, a.executor_id,
                   a.obs_encaminhamentos,
                   t.nome AS executor_nome, t.position AS executor_position,
                   s.name_sprn, s.stat_sprn
            FROM public.ctdi_okr_atividades a
            LEFT JOIN public.ctdi_team t ON t.id_member = a.executor_id
            LEFT JOIN public.ctdi_sprn s ON s.id_sprn = a.id_sprn
            WHERE COALESCE(a.status_ativ, '') NOT IN ('Entregue', 'Concluído', 'Concluido')
            {where_extra}
            ORDER BY a.data_planejamento NULLS LAST, a.id_ativ DESC;
            """,
            tuple(params),
        )
        rows = [dict(r) for r in cur.fetchall()]
        return jsonify({"status": "success", "data": rows}), 200
    except Exception as exc:
        return jsonify({"status": "error", "message": str(exc)}), 500
    finally:
        cur.close()
        conn.close()


@rbac_bp.route("/api/notificacoes", methods=["GET"])
@require_role(ROLE_EXECUTOR, ROLE_CONSULTOR, ROLE_LED, ROLE_SYSADMIN)
def rbac_listar_notificacoes():
    ctx = resolve_rbac_context()
    if not ctx.id_usuario:
        return jsonify({"status": "success", "data": [], "nao_lidas": 0}), 200

    conn = _get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        apenas_pendentes = request.args.get("pendentes", "1") == "1"
        if apenas_pendentes:
            cur.execute(
                """
                SELECT id, tipo, mensagem, lida_status, data_criacao, metadata
                FROM public.notificacoes
                WHERE user_id = %s AND lida_status = false
                ORDER BY data_criacao DESC
                LIMIT 50;
                """,
                (ctx.id_usuario,),
            )
        else:
            cur.execute(
                """
                SELECT id, tipo, mensagem, lida_status, data_criacao, metadata
                FROM public.notificacoes
                WHERE user_id = %s
                ORDER BY data_criacao DESC
                LIMIT 100;
                """,
                (ctx.id_usuario,),
            )
        rows = [dict(r) for r in cur.fetchall()]
        cur.execute(
            "SELECT COUNT(*) AS c FROM public.notificacoes WHERE user_id = %s AND lida_status = false;",
            (ctx.id_usuario,),
        )
        cnt = cur.fetchone()
        nao_lidas = int(cnt["c"] if cnt else 0)
        return jsonify({"status": "success", "data": rows, "nao_lidas": nao_lidas}), 200
    except Exception as exc:
        return jsonify({"status": "error", "message": str(exc)}), 500
    finally:
        cur.close()
        conn.close()


@rbac_bp.route("/api/notificacoes/<int:notif_id>/ler", methods=["PUT"])
@require_role(ROLE_EXECUTOR, ROLE_CONSULTOR, ROLE_LED, ROLE_SYSADMIN)
def rbac_marcar_notificacao_lida(notif_id: int):
    ctx = resolve_rbac_context()
    if not ctx.id_usuario:
        return jsonify({"status": "error", "message": "Sem usuário associado."}), 400

    conn = _get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            UPDATE public.notificacoes
            SET lida_status = true
            WHERE id = %s AND user_id = %s;
            """,
            (notif_id, ctx.id_usuario),
        )
        conn.commit()
        return jsonify({"status": "success", "atualizados": cur.rowcount}), 200
    except Exception as exc:
        conn.rollback()
        return jsonify({"status": "error", "message": str(exc)}), 500
    finally:
        cur.close()
        conn.close()


@rbac_bp.route("/api/consultor/associacoes", methods=["GET"])
@require_role(ROLE_CONSULTOR, ROLE_SYSADMIN)
def rbac_listar_associacoes_consultor():
    """Depreciado — carteira via dx_contratos (Portal do Parceiro /api/bff/consultor/clientes)."""
    return jsonify({
        "status": "error",
        "message": (
            "Endpoint depreciado. A carteira do consultor é definida por "
            "id_consultor_origem e id_consultor_tecnico em dx_contratos. "
            "Use GET /api/bff/consultor/clientes."
        ),
        "deprecated": True,
        "replacement": "/api/bff/consultor/clientes",
    }), 410


@rbac_bp.route("/api/rbac/capacidade", methods=["GET"])
def rbac_consultar_capacidade():
    """Consulta limite de squads por e-mail (mapa de calor / UX LED)."""
    email = (request.args.get("email") or "").strip()
    if not email:
        return jsonify({"status": "error", "message": "Parâmetro email obrigatório."}), 400

    id_squad_raw = request.args.get("id_squad")
    id_member_raw = request.args.get("id_member")
    id_squad = int(id_squad_raw) if id_squad_raw else None
    id_member = int(id_member_raw) if id_member_raw else None

    conn = _get_conn()
    cur = conn.cursor()
    try:
        info = rbac_validar_capacidade_squad(
            cur,
            email=email,
            id_squad=id_squad,
            id_member_excluir=id_member,
        )
        return jsonify({"status": "success", **info}), 200
    except Exception as exc:
        return jsonify({"status": "error", "message": str(exc)}), 500
    finally:
        cur.close()
        conn.close()


def register_rbac_routes(flask_app) -> None:
    flask_app.register_blueprint(rbac_bp)

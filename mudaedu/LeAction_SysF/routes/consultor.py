"""Rotas BFF do Portal do Parceiro (Consultor)."""

from __future__ import annotations

from flask import Blueprint, jsonify, request
from psycopg2.extras import RealDictCursor

from rbac.constants import ROLE_CONSULTOR, ROLE_SYSADMIN
from rbac.context import resolve_rbac_context
from rbac.decorators import require_role
from services.conciliacao_engine import (
    DEMANDA_STATUSES,
    montar_dashboard_consultor,
)

consultor_bp = Blueprint("consultor_portal", __name__)

SPRINT_STATUS_ATIVOS = ("em_andamento", "ativa", "planejada", "planejada_backlog")


def _get_conn():
    from app import get_db_conn
    return get_db_conn()


def _serializar_consultor(row: dict) -> dict:
    return {
        "id": row["id"],
        "user_id": row["user_id"],
        "tipo": row.get("tipo"),
        "id_agencia_pai": row.get("id_agencia_pai"),
        "nome_agencia_pai": row.get("nome_agencia_pai"),
        "nome": row.get("nome"),
        "email": row.get("email"),
        "taxa_comissao_venda": float(row.get("taxa_comissao_venda") or 0),
        "taxa_comissao_tecnica": float(row.get("taxa_comissao_tecnica") or 0),
        "ativo": bool(row.get("ativo", True)),
    }


def _carregar_consultor_por_usuario(cur, id_usuario: int) -> dict | None:
    cur.execute(
        """
        SELECT c.id, c.user_id, c.tipo, c.id_agencia_pai,
               c.taxa_comissao_venda, c.taxa_comissao_tecnica, c.ativo,
               u.nome, u.email,
               pai.nome AS nome_agencia_pai
        FROM public.dx_consultores c
        INNER JOIN public.paneldx_usuarios u ON u.id_usuario = c.user_id
        LEFT JOIN public.dx_consultores ag ON ag.id = c.id_agencia_pai
        LEFT JOIN public.paneldx_usuarios pai ON pai.id_usuario = ag.user_id
        WHERE c.user_id = %s AND c.ativo = TRUE
        LIMIT 1;
        """,
        (id_usuario,),
    )
    row = cur.fetchone()
    return dict(row) if row else None


def _carregar_membros_agencia(cur, id_agencia: int) -> list[dict]:
    cur.execute(
        """
        SELECT c.id, c.user_id, c.tipo, c.id_agencia_pai,
               c.taxa_comissao_venda, c.taxa_comissao_tecnica, c.ativo,
               u.nome, u.email
        FROM public.dx_consultores c
        INNER JOIN public.paneldx_usuarios u ON u.id_usuario = c.user_id
        WHERE c.id_agencia_pai = %s AND c.ativo = TRUE
        ORDER BY u.nome ASC;
        """,
        (id_agencia,),
    )
    return [dict(r) for r in cur.fetchall()]


def _carregar_consultores_map(cur, ids: list[int]) -> dict[int, dict]:
    if not ids:
        return {}
    cur.execute(
        """
        SELECT c.id, c.user_id, c.tipo, c.id_agencia_pai,
               c.taxa_comissao_venda, c.taxa_comissao_tecnica, c.ativo,
               u.nome, u.email
        FROM public.dx_consultores c
        INNER JOIN public.paneldx_usuarios u ON u.id_usuario = c.user_id
        WHERE c.id = ANY(%s);
        """,
        (ids,),
    )
    return {int(r["id"]): dict(r) for r in cur.fetchall()}


def _ids_carteira_sql(ids: list[int]) -> tuple[str, list]:
    if not ids:
        return "FALSE", []
    placeholders = ", ".join(["%s"] * len(ids))
    clause = f"(ct.id_consultor_origem IN ({placeholders}) OR ct.id_consultor_tecnico IN ({placeholders}))"
    return clause, ids + ids


def _listar_contratos_carteira(cur, ids_carteira: list[int]) -> list[dict]:
    where, params = _ids_carteira_sql(ids_carteira)
    cur.execute(
        f"""
        SELECT ct.id, ct.id_clie, ct.id_plano, ct.valor_negociado, ct.status,
               ct.data_inicio, ct.data_vencimento,
               ct.id_consultor_origem, ct.id_consultor_tecnico,
               c.nome_clie, c.mail_clie,
               p.nome AS nome_plano, p.direito_consultoria_tecnica
        FROM public.dx_contratos ct
        INNER JOIN public.ctdi_clie c ON c.id_clie = ct.id_clie
        INNER JOIN public.dx_planos p ON p.id = ct.id_plano
        WHERE ct.status IN ('ativo', 'trial', 'inadimplente')
          AND {where}
        ORDER BY c.nome_clie ASC, ct.id DESC;
        """,
        tuple(params),
    )
    return [dict(r) for r in cur.fetchall()]


def _resolver_consultor_sessao(cur) -> tuple[dict | None, str | None]:
    ctx = resolve_rbac_context()
    if not ctx.id_usuario:
        return None, "Usuário não autenticado."
    consultor = _carregar_consultor_por_usuario(cur, int(ctx.id_usuario))
    if not consultor:
        return None, "Perfil de consultor não cadastrado. Solicite ao administrador."
    return consultor, None


def _resolver_escopo_carteira(
    cur,
) -> tuple[dict | None, list[dict], list[int], str | None]:
    consultor, err = _resolver_consultor_sessao(cur)
    if err:
        return None, [], [], err

    membros: list[dict] = []
    if consultor.get("tipo") == "agencia":
        membros = _carregar_membros_agencia(cur, int(consultor["id"]))

    from services.conciliacao_engine import ids_consultores_carteira

    ids_carteira = ids_consultores_carteira(consultor, membros)
    return consultor, membros, ids_carteira, None


@consultor_bp.route("/api/bff/consultor/dashboard", methods=["GET"])
@require_role(ROLE_CONSULTOR, ROLE_SYSADMIN)
def consultor_dashboard():
    conn = _get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        consultor, membros, ids_carteira, err = _resolver_escopo_carteira(cur)
        if err:
            return jsonify({"status": "error", "error": err}), 404

        contratos = _listar_contratos_carteira(cur, ids_carteira)

        all_ids = set(ids_carteira)
        for c in contratos:
            if c.get("id_consultor_origem"):
                all_ids.add(int(c["id_consultor_origem"]))
            if c.get("id_consultor_tecnico"):
                all_ids.add(int(c["id_consultor_tecnico"]))
        consultores_map = _carregar_consultores_map(cur, list(all_ids))

        cur.execute(
            """
            SELECT COUNT(*) AS c
            FROM public.dx_demandas_consultor d
            WHERE d.id_consultor = ANY(%s)
              AND d.status IN ('aberta', 'em_andamento');
            """,
            (ids_carteira,),
        )
        demandas_abertas = int(cur.fetchone()["c"])

        cur.execute(
            """
            SELECT COUNT(DISTINCT s.id_sprn) AS c
            FROM public.ctdi_sprn s
            INNER JOIN public.ctdi_itera i ON i.id_itera = s.id_itera
            INNER JOIN public.ctdi_main m ON m.id_ctdi = i.id_ctdi
            INNER JOIN public.ctdi_matu mat ON mat.id_matu = m.id_matu
            INNER JOIN public.dx_contratos ct ON ct.id_clie = mat.id_clie
            WHERE ct.status IN ('ativo', 'trial')
              AND s.stat_sprn = ANY(%s)
              AND (ct.id_consultor_origem = ANY(%s) OR ct.id_consultor_tecnico = ANY(%s));
            """,
            (list(SPRINT_STATUS_ATIVOS), ids_carteira, ids_carteira),
        )
        sprints_ativas = int(cur.fetchone()["c"])

        payload = montar_dashboard_consultor(
            consultor,
            membros,
            contratos,
            consultores_map,
            demandas_abertas=demandas_abertas,
            sprints_ativas=sprints_ativas,
        )
        payload["consultor"] = _serializar_consultor(consultor)
        return jsonify({"status": "success", "data": payload}), 200
    except Exception as exc:
        return jsonify({"status": "error", "error": str(exc)}), 500
    finally:
        cur.close()
        conn.close()


@consultor_bp.route("/api/bff/consultor/clientes", methods=["GET"])
@require_role(ROLE_CONSULTOR, ROLE_SYSADMIN)
def consultor_clientes():
    conn = _get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        consultor, membros, ids_carteira, err = _resolver_escopo_carteira(cur)
        if err:
            return jsonify({"status": "error", "error": err}), 404

        where, where_params = _ids_carteira_sql(ids_carteira)
        sql_params = [ids_carteira, ids_carteira, ids_carteira, ids_carteira] + where_params

        cur.execute(
            f"""
            SELECT DISTINCT ON (c.id_clie)
                c.id_clie, c.nome_clie, c.mail_clie, c.fone_clie,
                ct.id AS id_contrato, ct.status AS status_contrato,
                ct.valor_negociado, ct.data_inicio, ct.data_vencimento,
                p.id AS id_plano, p.nome AS nome_plano,
                p.direito_consultoria_tecnica,
                ct.id_consultor_origem, ct.id_consultor_tecnico,
                co.nome AS consultor_origem_nome,
                ct2.nome AS consultor_tecnico_nome,
                CASE
                    WHEN ct.id_consultor_origem = ANY(%s) AND ct.id_consultor_tecnico = ANY(%s) THEN 'origem_tecnico'
                    WHEN ct.id_consultor_origem = ANY(%s) THEN 'origem'
                    WHEN ct.id_consultor_tecnico = ANY(%s) THEN 'tecnico'
                    ELSE 'carteira'
                END AS papel_consultor
            FROM public.ctdi_clie c
            INNER JOIN public.dx_contratos ct ON ct.id_clie = c.id_clie
            INNER JOIN public.dx_planos p ON p.id = ct.id_plano
            LEFT JOIN public.dx_consultores cso ON cso.id = ct.id_consultor_origem
            LEFT JOIN public.paneldx_usuarios co ON co.id_usuario = cso.user_id
            LEFT JOIN public.dx_consultores cst ON cst.id = ct.id_consultor_tecnico
            LEFT JOIN public.paneldx_usuarios ct2 ON ct2.id_usuario = cst.user_id
            WHERE ct.status IN ('ativo', 'trial', 'inadimplente')
              AND {where}
            ORDER BY c.id_clie, ct.id DESC;
            """,
            tuple(sql_params),
        )
        rows = []
        for r in cur.fetchall():
            item = dict(r)
            for key in ("data_inicio", "data_vencimento"):
                if item.get(key) is not None and hasattr(item[key], "isoformat"):
                    item[key] = item[key].isoformat()
            item["valor_negociado"] = float(item.get("valor_negociado") or 0)
            rows.append(item)

        return jsonify({"status": "success", "data": rows}), 200
    except Exception as exc:
        return jsonify({"status": "error", "error": str(exc)}), 500
    finally:
        cur.close()
        conn.close()


@consultor_bp.route("/api/bff/consultor/sprints", methods=["GET"])
@require_role(ROLE_CONSULTOR, ROLE_SYSADMIN)
def consultor_sprints():
    conn = _get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        _, _, ids_carteira, err = _resolver_escopo_carteira(cur)
        if err:
            return jsonify({"status": "error", "error": err}), 404

        cur.execute(
            """
            SELECT DISTINCT s.id_sprn, s.name_sprn, s.desc_sprn, s.stat_sprn,
                   s.ordr_sprn, s.id_itera,
                   c.id_clie, c.nome_clie,
                   i.id_itera AS iteracao_id
            FROM public.ctdi_sprn s
            INNER JOIN public.ctdi_itera i ON i.id_itera = s.id_itera
            INNER JOIN public.ctdi_main m ON m.id_ctdi = i.id_ctdi
            INNER JOIN public.ctdi_matu mat ON mat.id_matu = m.id_matu
            INNER JOIN public.ctdi_clie c ON c.id_clie = mat.id_clie
            INNER JOIN public.dx_contratos ct ON ct.id_clie = c.id_clie
            WHERE ct.status IN ('ativo', 'trial')
              AND s.stat_sprn = ANY(%s)
              AND (ct.id_consultor_origem = ANY(%s) OR ct.id_consultor_tecnico = ANY(%s))
            ORDER BY c.nome_clie ASC, s.ordr_sprn ASC NULLS LAST, s.id_sprn ASC;
            """,
            (list(SPRINT_STATUS_ATIVOS), ids_carteira, ids_carteira),
        )
        return jsonify({"status": "success", "data": [dict(r) for r in cur.fetchall()]}), 200
    except Exception as exc:
        return jsonify({"status": "error", "error": str(exc)}), 500
    finally:
        cur.close()
        conn.close()


def _validar_cliente_carteira(cur, id_clie: int, ids_carteira: list[int]) -> bool:
    if not ids_carteira:
        return False
    cur.execute(
        """
        SELECT 1
        FROM public.dx_contratos ct
        WHERE ct.id_clie = %s
          AND ct.status IN ('ativo', 'trial', 'inadimplente')
          AND (ct.id_consultor_origem = ANY(%s) OR ct.id_consultor_tecnico = ANY(%s))
        LIMIT 1;
        """,
        (id_clie, ids_carteira, ids_carteira),
    )
    return cur.fetchone() is not None


@consultor_bp.route("/api/bff/consultor/demandas", methods=["GET"])
@require_role(ROLE_CONSULTOR, ROLE_SYSADMIN)
def consultor_listar_demandas():
    conn = _get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        consultor, _, ids_carteira, err = _resolver_escopo_carteira(cur)
        if err:
            return jsonify({"status": "error", "error": err}), 404

        if not ids_carteira:
            return jsonify({"status": "success", "data": []}), 200

        status_filter = (request.args.get("status") or "").strip().lower()
        params: list = [ids_carteira]
        status_clause = ""
        if status_filter and status_filter in DEMANDA_STATUSES:
            status_clause = "AND d.status = %s"
            params.append(status_filter)

        cur.execute(
            f"""
            SELECT d.id, d.id_clie, d.id_consultor, d.titulo, d.descricao, d.status,
                   d.criado_em, d.atualizado_em,
                   c.nome_clie, c.mail_clie,
                   u.nome AS consultor_responsavel_nome
            FROM public.dx_demandas_consultor d
            INNER JOIN public.ctdi_clie c ON c.id_clie = d.id_clie
            INNER JOIN public.dx_consultores dc ON dc.id = d.id_consultor
            INNER JOIN public.paneldx_usuarios u ON u.id_usuario = dc.user_id
            WHERE d.id_consultor = ANY(%s) {status_clause}
            ORDER BY
                CASE d.status
                    WHEN 'aberta' THEN 1
                    WHEN 'em_andamento' THEN 2
                    ELSE 3
                END,
                d.criado_em DESC;
            """,
            tuple(params),
        )
        rows = []
        for r in cur.fetchall():
            item = dict(r)
            for key in ("criado_em", "atualizado_em"):
                if item.get(key) is not None and hasattr(item[key], "isoformat"):
                    item[key] = item[key].isoformat()
            rows.append(item)
        return jsonify({"status": "success", "data": rows}), 200
    except Exception as exc:
        return jsonify({"status": "error", "error": str(exc)}), 500
    finally:
        cur.close()
        conn.close()


@consultor_bp.route("/api/bff/consultor/demandas", methods=["POST"])
@require_role(ROLE_CONSULTOR, ROLE_SYSADMIN)
def consultor_criar_demanda():
    body = request.get_json(silent=True) or {}
    id_clie = body.get("id_clie")
    titulo = (body.get("titulo") or "").strip()
    descricao = (body.get("descricao") or "").strip() or None
    status = (body.get("status") or "aberta").strip().lower()

    if not id_clie or not titulo:
        return jsonify({"status": "error", "error": "id_clie e titulo são obrigatórios."}), 400
    if status not in DEMANDA_STATUSES:
        return jsonify({"status": "error", "error": "Status inválido."}), 400

    conn = _get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        consultor, _, ids_carteira, err = _resolver_escopo_carteira(cur)
        if err:
            return jsonify({"status": "error", "error": err}), 404

        if not _validar_cliente_carteira(cur, int(id_clie), ids_carteira):
            return jsonify({
                "status": "error",
                "error": "Cliente fora da carteira deste consultor.",
            }), 403

        cur.execute(
            """
            INSERT INTO public.dx_demandas_consultor
                (id_clie, id_consultor, titulo, descricao, status)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id, id_clie, id_consultor, titulo, descricao, status, criado_em, atualizado_em;
            """,
            (int(id_clie), int(consultor["id"]), titulo[:200], descricao, status),
        )
        row = dict(cur.fetchone())
        conn.commit()
        for key in ("criado_em", "atualizado_em"):
            if row.get(key) is not None and hasattr(row[key], "isoformat"):
                row[key] = row[key].isoformat()
        return jsonify({"status": "success", "data": row}), 201
    except Exception as exc:
        conn.rollback()
        return jsonify({"status": "error", "error": str(exc)}), 500
    finally:
        cur.close()
        conn.close()


@consultor_bp.route("/api/bff/consultor/demandas/<int:demanda_id>", methods=["PUT"])
@require_role(ROLE_CONSULTOR, ROLE_SYSADMIN)
def consultor_atualizar_demanda(demanda_id: int):
    body = request.get_json(silent=True) or {}
    conn = _get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        consultor, _, ids_carteira, err = _resolver_escopo_carteira(cur)
        if err:
            return jsonify({"status": "error", "error": err}), 404

        cur.execute(
            """
            SELECT id, id_consultor FROM public.dx_demandas_consultor WHERE id = %s;
            """,
            (demanda_id,),
        )
        existing = cur.fetchone()
        if not existing:
            return jsonify({"status": "error", "error": "Demanda não encontrada."}), 404
        if int(existing["id_consultor"]) not in ids_carteira:
            return jsonify({"status": "error", "error": "Demanda fora do escopo da carteira."}), 403

        sets = []
        values = []
        if "titulo" in body:
            titulo = (body.get("titulo") or "").strip()
            if not titulo:
                return jsonify({"status": "error", "error": "titulo não pode ser vazio."}), 400
            sets.append("titulo = %s")
            values.append(titulo[:200])
        if "descricao" in body:
            sets.append("descricao = %s")
            values.append((body.get("descricao") or "").strip() or None)
        if "status" in body:
            status = (body.get("status") or "").strip().lower()
            if status not in DEMANDA_STATUSES:
                return jsonify({"status": "error", "error": "Status inválido."}), 400
            sets.append("status = %s")
            values.append(status)

        if not sets:
            return jsonify({"status": "error", "error": "Nenhum campo para atualizar."}), 400

        sets.append("atualizado_em = NOW()")
        values.append(demanda_id)
        cur.execute(
            f"""
            UPDATE public.dx_demandas_consultor
            SET {", ".join(sets)}
            WHERE id = %s
            RETURNING id, id_clie, id_consultor, titulo, descricao, status, criado_em, atualizado_em;
            """,
            tuple(values),
        )
        row = dict(cur.fetchone())
        conn.commit()
        for key in ("criado_em", "atualizado_em"):
            if row.get(key) is not None and hasattr(row[key], "isoformat"):
                row[key] = row[key].isoformat()
        return jsonify({"status": "success", "data": row}), 200
    except Exception as exc:
        conn.rollback()
        return jsonify({"status": "error", "error": str(exc)}), 500
    finally:
        cur.close()
        conn.close()


@consultor_bp.route("/api/bff/consultor/vincular-lead", methods=["POST"])
@require_role(ROLE_CONSULTOR, ROLE_SYSADMIN)
def consultor_vincular_lead():
    """Prospecção reativa: captura lead órfão pelo ID Matu."""
    from services.funil_engine import FunilError, vincular_lead_por_matu

    body = request.get_json(silent=True) or {}
    raw_matu = body.get("id_matu")
    try:
        id_matu = int(str(raw_matu).strip())
    except (TypeError, ValueError, AttributeError):
        return jsonify({"status": "error", "error": "id_matu inválido."}), 400
    if id_matu <= 0:
        return jsonify({"status": "error", "error": "id_matu inválido."}), 400

    conn = _get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        consultor, err = _resolver_consultor_sessao(cur)
        if err:
            return jsonify({"status": "error", "error": err}), 404
        oportunidade = vincular_lead_por_matu(
            cur,
            id_matu=id_matu,
            id_consultor=int(consultor["id"]),
        )
        conn.commit()
        return jsonify({"status": "success", "data": oportunidade}), 200
    except FunilError as exc:
        conn.rollback()
        msg = str(exc)
        code = 403 if "outro consultor" in msg.lower() else 400
        return jsonify({"status": "error", "error": msg}), code
    except Exception as exc:
        conn.rollback()
        return jsonify({"status": "error", "error": str(exc)}), 500
    finally:
        cur.close()
        conn.close()


@consultor_bp.route("/api/bff/consultor/prospectos", methods=["GET", "POST"])
@require_role(ROLE_CONSULTOR, ROLE_SYSADMIN)
def consultor_prospectos():
    """Prospecção ativa: lista ou cadastra prospecto + link de convite."""
    from services.funil_engine import (
        FunilError,
        criar_prospecto,
        listar_oportunidades_consultor,
    )
    import os

    conn = _get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        consultor, membros, ids_carteira, err = _resolver_escopo_carteira(cur)
        if err:
            return jsonify({"status": "error", "error": err}), 404

        if request.method == "GET":
            itens = listar_oportunidades_consultor(cur, ids_carteira)
            return jsonify({"status": "success", "data": {"oportunidades": itens}}), 200

        body = request.get_json(silent=True) or {}
        public_base = (
            (body.get("public_base_url") or "").strip()
            or os.environ.get("PANELDX_PUBLIC_URL")
            or "http://localhost:3000"
        )
        oportunidade = criar_prospecto(
            cur,
            id_consultor=int(consultor["id"]),
            nome=body.get("nome") or "",
            email=body.get("email") or "",
            telefone=body.get("telefone"),
            empresa=body.get("empresa"),
            public_base_url=public_base,
        )
        conn.commit()
        return jsonify({"status": "success", "data": oportunidade}), 201
    except FunilError as exc:
        conn.rollback()
        return jsonify({"status": "error", "error": str(exc)}), 400
    except Exception as exc:
        conn.rollback()
        return jsonify({"status": "error", "error": str(exc)}), 500
    finally:
        cur.close()
        conn.close()


def register_consultor_routes(flask_app) -> None:
    flask_app.register_blueprint(consultor_bp)

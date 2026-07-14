"""Rotas administrativas — gestão global de usuários (paneldx_usuarios)."""

from __future__ import annotations

from flask import Blueprint, jsonify, request
from psycopg2.extras import RealDictCursor
from werkzeug.security import generate_password_hash

from rbac.constants import ROLE_CONSULTOR, ROLE_EXECUTOR, ROLE_LED, ROLE_SYSADMIN, SYSTEM_ROLES
from services.consultor_repository import ensure_consultor_profile
from rbac.decorators import require_role
from rbac.users import (
    rbac_buscar_usuario_por_email,
    rbac_buscar_usuario_por_id,
    rbac_criar_ou_atualizar_usuario,
    rbac_formatar_empresa_grupo,
    rbac_listar_opcoes_empresa_grupo,
    rbac_listar_usuarios,
    rbac_listar_usuarios_por_cliente,
    rbac_normalizar_email,
    _scalar,
)

admin_users_bp = Blueprint("admin_users", __name__)

# Referência local (dev) — SysAdmin pode visualizar via olho na Gestão Global
_CREDENCIAIS_DEV_LOCAL: dict[str, str] = {
    "executor@peneldx.com.br": "PanelDX1!",
    "executor@paneldx.com.br": "PanelDX1!",
}


def _credencial_dev_local(email: str | None) -> str | None:
    import os
    host = (os.getenv("DB_HOST") or "127.0.0.1").lower()
    if host not in ("127.0.0.1", "localhost", "::1"):
        return None
    chave = (email or "").strip().lower()
    return _CREDENCIAIS_DEV_LOCAL.get(chave)


def _get_conn():
    from app import get_db_conn
    return get_db_conn()


def _serializar_usuario(row: dict) -> dict:
    empresa_grupo = row.get("empresa_grupo") or rbac_formatar_empresa_grupo(row)
    return {
        "id_usuario": row["id_usuario"],
        "nome": row["nome"],
        "email": row["email"],
        "system_role": row["system_role"],
        "ativo": row["ativo"],
        "id_clie": row.get("id_clie"),
        "nome_clie": row.get("nome_clie"),
        "empresa_clie": row.get("empresa_clie"),
        "id_rede": row.get("id_rede"),
        "is_holding": bool(row.get("is_holding")) if row.get("is_holding") is not None else None,
        "empresa_grupo": empresa_grupo,
        "criado_em": row["criado_em"].isoformat() if row.get("criado_em") else None,
    }


def _validar_payload_usuario(data: dict, *, criar: bool) -> tuple[dict | None, str | None]:
    if not isinstance(data, dict):
        return None, "JSON inválido."

    nome = (data.get("nome") or "").strip()
    email = rbac_normalizar_email(data.get("email"))
    system_role = (data.get("system_role") or "").strip().lower()
    senha = data.get("senha") or data.get("password") or data.get("password_hash")

    if criar:
        if not nome:
            return None, "Nome é obrigatório."
        if not email:
            return None, "E-mail é obrigatório."
        if not senha:
            return None, "Senha é obrigatória."
        if system_role not in SYSTEM_ROLES:
            return None, "system_role inválido (sysadmin, gestor, consultor, executor)."

    payload: dict = {}
    if nome:
        payload["nome"] = nome
    if email:
        payload["email"] = email
    if system_role:
        if system_role not in SYSTEM_ROLES:
            return None, "system_role inválido."
        payload["system_role"] = system_role
    if senha:
        payload["password_hash"] = generate_password_hash(str(senha))
    if "ativo" in data:
        payload["ativo"] = bool(data["ativo"])
    if "id_clie" in data:
        raw = data.get("id_clie")
        payload["id_clie"] = int(raw) if raw not in (None, "", "null") else None

    return payload, None


@admin_users_bp.route("/api/admin/usuarios/opcoes-empresa", methods=["GET"])
@require_role(ROLE_SYSADMIN)
def admin_opcoes_empresa_grupo():
    conn = _get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        opcoes = rbac_listar_opcoes_empresa_grupo(cur)
        return jsonify({"status": "success", **opcoes}), 200
    except Exception as exc:
        return jsonify({"status": "error", "error": str(exc)}), 500
    finally:
        cur.close()
        conn.close()


@admin_users_bp.route("/api/admin/usuarios", methods=["GET"])
@require_role(ROLE_SYSADMIN)
def admin_listar_usuarios():
    incluir_inativos = request.args.get("incluir_inativos", "1") == "1"
    busca = (request.args.get("q") or request.args.get("busca") or "").strip()
    system_role = (request.args.get("system_role") or request.args.get("role") or "").strip().lower()
    id_clie_raw = request.args.get("id_clie")
    id_rede = (request.args.get("id_rede") or request.args.get("grupo") or "").strip().upper()
    id_clie = None
    if id_clie_raw not in (None, "", "null"):
        try:
            id_clie = int(id_clie_raw)
        except (TypeError, ValueError):
            return jsonify({"status": "error", "error": "id_clie inválido."}), 400

    conn = _get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        rows = rbac_listar_usuarios(
            cur,
            incluir_inativos=incluir_inativos,
            busca=busca or None,
            system_role=system_role or None,
            id_clie=id_clie,
            id_rede=id_rede or None,
        )
        data = [_serializar_usuario(dict(r)) for r in rows]
        return jsonify({
            "status": "success",
            "data": data,
            "total": len(data),
            "filtros": {
                "q": busca or None,
                "system_role": system_role or None,
                "id_clie": id_clie,
                "id_rede": id_rede or None,
                "incluir_inativos": incluir_inativos,
            },
        }), 200
    except Exception as exc:
        return jsonify({"status": "error", "error": str(exc)}), 500
    finally:
        cur.close()
        conn.close()


@admin_users_bp.route("/api/admin/usuarios/<int:id_usuario>/acesso", methods=["GET"])
@require_role(ROLE_SYSADMIN)
def admin_obter_credenciais_acesso(id_usuario: int):
    """Expõe ao SysAdmin código LA-* (lead) e indica se há senha — nunca retorna o hash."""
    conn = _get_conn()
    cur = conn.cursor()
    try:
        usuario = rbac_buscar_usuario_por_id(cur, id_usuario)
        if not usuario:
            return jsonify({"status": "error", "error": "Usuário não encontrado."}), 404

        codigo_acesso = None
        id_clie = usuario.get("id_clie")
        if id_clie:
            cur.execute(
                "SELECT access_code FROM public.ctdi_lead_access WHERE id_clie = %s LIMIT 1;",
                (id_clie,),
            )
            row = cur.fetchone()
            if row:
                codigo_acesso = row[0] if not isinstance(row, dict) else row.get("access_code")

        cur.execute(
            "SELECT COUNT(*) FROM public.ctdi_team WHERE id_usuario = %s AND ativo = true;",
            (id_usuario,),
        )
        row_team = cur.fetchone()
        qtd_team = int(_scalar(row_team) or 0)

        email = (usuario.get("email") or "").strip().lower()
        role = (usuario.get("system_role") or "").strip().lower()
        dev_hint = _credencial_dev_local(email)

        if role == "led" and codigo_acesso:
            credencial_visivel = codigo_acesso
            tipo_credencial = "codigo_lead"
        elif dev_hint:
            credencial_visivel = dev_hint
            tipo_credencial = "senha_dev"
        else:
            credencial_visivel = None
            tipo_credencial = None

        return jsonify({
            "status": "success",
            "data": {
                "id_usuario": id_usuario,
                "email": usuario.get("email"),
                "system_role": usuario.get("system_role"),
                "tem_senha": bool(usuario.get("password_hash")),
                "codigo_acesso": codigo_acesso,
                "credencial_visivel": credencial_visivel,
                "tipo_credencial": tipo_credencial,
                "id_clie": id_clie,
                "vinculo_squad": qtd_team > 0,
            },
        }), 200
    except Exception as exc:
        return jsonify({"status": "error", "error": str(exc)}), 500
    finally:
        cur.close()
        conn.close()


@admin_users_bp.route("/api/admin/usuarios", methods=["POST"])
@require_role(ROLE_SYSADMIN)
def admin_criar_usuario():
    payload, erro = _validar_payload_usuario(request.get_json(silent=True) or {}, criar=True)
    if erro:
        return jsonify({"status": "error", "error": erro}), 400

    conn = _get_conn()
    cur = conn.cursor()
    try:
        if rbac_buscar_usuario_por_email(cur, payload["email"]):
            return jsonify({"status": "error", "error": "E-mail já cadastrado."}), 409

        id_usuario = rbac_criar_ou_atualizar_usuario(
            cur,
            email=payload["email"],
            nome=payload["nome"],
            system_role=payload["system_role"],
            password_hash=payload["password_hash"],
            id_clie=payload.get("id_clie"),
        )
        if payload["system_role"] == ROLE_CONSULTOR:
            data = request.get_json(silent=True) or {}
            id_agencia_raw = data.get("id_agencia_pai")
            id_agencia_pai = int(id_agencia_raw) if id_agencia_raw not in (None, "", "null") else None
            ensure_consultor_profile(
                cur,
                id_usuario,
                tipo=(data.get("tipo") or "individual").strip().lower(),
                id_agencia_pai=id_agencia_pai,
                taxa_comissao_venda=float(data.get("taxa_comissao_venda", 10)),
                taxa_comissao_tecnica=float(data.get("taxa_comissao_tecnica", 15)),
            )
        conn.commit()
        usuario = rbac_buscar_usuario_por_id(cur, id_usuario)
        return jsonify({
            "status": "success",
            "data": _serializar_usuario(usuario) if usuario else {"id_usuario": id_usuario},
        }), 201
    except Exception as exc:
        conn.rollback()
        return jsonify({"status": "error", "error": str(exc)}), 500
    finally:
        cur.close()
        conn.close()


@admin_users_bp.route("/api/admin/usuarios/<int:id_usuario>", methods=["PUT"])
@require_role(ROLE_SYSADMIN)
def admin_atualizar_usuario(id_usuario: int):
    payload, erro = _validar_payload_usuario(request.get_json(silent=True) or {}, criar=False)
    if erro:
        return jsonify({"status": "error", "error": erro}), 400
    if not payload:
        return jsonify({"status": "error", "error": "Nenhum campo para atualizar."}), 400

    conn = _get_conn()
    cur = conn.cursor()
    try:
        existente = rbac_buscar_usuario_por_id(cur, id_usuario)
        if not existente:
            return jsonify({"status": "error", "error": "Usuário não encontrado."}), 404

        novo_email = payload.get("email")
        if novo_email and novo_email != rbac_normalizar_email(existente["email"]):
            outro = rbac_buscar_usuario_por_email(cur, novo_email)
            if outro and outro["id_usuario"] != id_usuario:
                return jsonify({"status": "error", "error": "E-mail já utilizado por outro usuário."}), 409

        sets = []
        params = []
        for campo, coluna in (
            ("nome", "nome"),
            ("email", "email"),
            ("system_role", "system_role"),
            ("password_hash", "password_hash"),
            ("ativo", "ativo"),
            ("id_clie", "id_clie"),
        ):
            if campo in payload:
                sets.append(f"{coluna} = %s")
                params.append(payload[campo])

        params.append(id_usuario)
        cur.execute(
            f"UPDATE public.paneldx_usuarios SET {', '.join(sets)} WHERE id_usuario = %s RETURNING id_usuario;",
            tuple(params),
        )
        role_final = payload.get("system_role") or existente.get("system_role")
        if role_final == ROLE_CONSULTOR:
            data = request.get_json(silent=True) or {}
            id_agencia_raw = data.get("id_agencia_pai")
            id_agencia_pai = int(id_agencia_raw) if id_agencia_raw not in (None, "", "null") else None
            ensure_consultor_profile(
                cur,
                id_usuario,
                tipo=(data.get("tipo") or "individual").strip().lower(),
                id_agencia_pai=id_agencia_pai,
                taxa_comissao_venda=float(data.get("taxa_comissao_venda", 10)),
                taxa_comissao_tecnica=float(data.get("taxa_comissao_tecnica", 15)),
            )
        if "password_hash" in payload:
            cur.execute(
                """
                UPDATE public.ctdi_team
                SET password_hash = %s
                WHERE id_usuario = %s;
                """,
                (payload["password_hash"], id_usuario),
            )
            cur.execute(
                """
                UPDATE public.ctdi_team
                SET password_hash = %s
                WHERE LOWER(TRIM(email)) = LOWER(TRIM(%s)) AND ativo = true;
                """,
                (payload["password_hash"], existente.get("email")),
            )
        conn.commit()
        usuario = rbac_buscar_usuario_por_id(cur, id_usuario)
        return jsonify({"status": "success", "data": _serializar_usuario(usuario)}), 200
    except Exception as exc:
        conn.rollback()
        return jsonify({"status": "error", "error": str(exc)}), 500
    finally:
        cur.close()
        conn.close()


@admin_users_bp.route("/api/admin/usuarios/<int:id_usuario>", methods=["DELETE"])
@require_role(ROLE_SYSADMIN)
def admin_desativar_usuario(id_usuario: int):
    conn = _get_conn()
    cur = conn.cursor()
    try:
        existente = rbac_buscar_usuario_por_id(cur, id_usuario)
        if not existente:
            return jsonify({"status": "error", "error": "Usuário não encontrado."}), 404

        cur.execute(
            "UPDATE public.paneldx_usuarios SET ativo = false WHERE id_usuario = %s;",
            (id_usuario,),
        )
        conn.commit()
        return jsonify({"status": "success", "message": "Usuário desativado."}), 200
    except Exception as exc:
        conn.rollback()
        return jsonify({"status": "error", "error": str(exc)}), 500
    finally:
        cur.close()
        conn.close()


@admin_users_bp.route("/api/led/usuarios-disponiveis", methods=["GET"])
@require_role(ROLE_LED, ROLE_SYSADMIN)
def led_listar_usuarios_disponiveis():
    """Usuários globais elegíveis para alocação em squad pelo LED."""
    from rbac.context import resolve_rbac_context

    ctx = resolve_rbac_context()
    id_clie_raw = request.args.get("id_clie") or ctx.id_clie
    if not id_clie_raw:
        return jsonify({"status": "error", "error": "id_clie obrigatório."}), 400

    id_clie = int(id_clie_raw)
    if ctx.system_role == ROLE_LED and ctx.id_clie and ctx.id_clie != id_clie:
        return jsonify({"status": "error", "error": "Acesso negado a usuários de outro cliente."}), 403

    conn = _get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        rows = rbac_listar_usuarios_por_cliente(cur, id_clie=id_clie, apenas_empresa=True)
        data = [
            {
                "id_usuario": r["id_usuario"],
                "nome": r["nome"],
                "email": r["email"],
                "system_role": r["system_role"],
                "ativo": r["ativo"],
            }
            for r in rows
            if r.get("ativo")
        ]
        return jsonify({"status": "success", "data": data}), 200
    except Exception as exc:
        return jsonify({"status": "error", "error": str(exc)}), 500
    finally:
        cur.close()
        conn.close()


LED_ROLES_CRIAVEIS = frozenset({ROLE_EXECUTOR, ROLE_LED})


@admin_users_bp.route("/api/led/cota-usuarios", methods=["GET"])
@require_role(ROLE_LED, ROLE_SYSADMIN)
def led_obter_cota_usuarios():
    """Cota de licenças (seat-based) do cliente da sessão ou id_clie informado."""
    from rbac.context import resolve_rbac_context
    from services.seat_limits import obter_cota_usuarios

    ctx = resolve_rbac_context()
    id_clie_raw = request.args.get("id_clie") or ctx.id_clie
    if not id_clie_raw:
        return jsonify({"status": "error", "error": "id_clie obrigatório."}), 400

    id_clie = int(id_clie_raw)
    if ctx.system_role == ROLE_LED and ctx.id_clie and int(ctx.id_clie) != id_clie:
        return jsonify({"status": "error", "error": "Acesso negado a cota de outro cliente."}), 403

    conn = _get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cota = obter_cota_usuarios(cur, id_clie)
        return jsonify({"status": "success", "data": cota}), 200
    except Exception as exc:
        return jsonify({"status": "error", "error": str(exc)}), 500
    finally:
        cur.close()
        conn.close()


@admin_users_bp.route("/api/led/meu-contrato", methods=["GET"])
@require_role(ROLE_LED, ROLE_SYSADMIN)
def led_obter_meu_contrato():
    """Contrato, planos, aditivos e histórico comercial do cliente autenticado."""
    from rbac.context import resolve_rbac_context
    from services.addon_engine import obter_detalhe_comercial_cliente

    ctx = resolve_rbac_context()
    id_clie_raw = request.args.get("id_clie") or ctx.id_clie
    if not id_clie_raw:
        return jsonify({"status": "error", "error": "id_clie obrigatório."}), 400

    id_clie = int(id_clie_raw)
    if ctx.system_role == ROLE_LED and ctx.id_clie and int(ctx.id_clie) != id_clie:
        return jsonify({"status": "error", "error": "Acesso negado ao contrato de outro cliente."}), 403

    conn = _get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        detalhe = obter_detalhe_comercial_cliente(cur, id_clie)
        return jsonify({"status": "success", "data": detalhe}), 200
    except Exception as exc:
        return jsonify({"status": "error", "error": str(exc)}), 500
    finally:
        cur.close()
        conn.close()


@admin_users_bp.route("/api/led/usuarios", methods=["POST"])
@require_role(ROLE_LED)
def led_criar_usuario():
    """Gestor cadastra membros da própria empresa (executor ou gestor). Consultores: só SysAdmin."""
    from rbac.context import resolve_rbac_context

    ctx = resolve_rbac_context()
    if not ctx.id_clie:
        return jsonify({"status": "error", "error": "Cliente da sessão não identificado."}), 400

    payload, erro = _validar_payload_usuario(request.get_json(silent=True) or {}, criar=True)
    if erro:
        return jsonify({"status": "error", "error": erro}), 400

    role = (payload.get("system_role") or ROLE_EXECUTOR).strip().lower()
    if role not in LED_ROLES_CRIAVEIS:
        return jsonify({
            "status": "error",
            "error": "Gestor pode cadastrar apenas executor ou gestor da empresa. Consultores são exclusivos do SysAdmin.",
        }), 403

    payload["system_role"] = role
    payload["id_clie"] = int(ctx.id_clie)

    conn = _get_conn()
    cur = conn.cursor()
    try:
        from services.seat_limits import validar_pode_adicionar_usuario, SEAT_LIMIT_MESSAGE

        pode, msg_limite = validar_pode_adicionar_usuario(cur, int(ctx.id_clie))
        if not pode:
            return jsonify({"status": "error", "error": msg_limite or SEAT_LIMIT_MESSAGE}), 403

        if rbac_buscar_usuario_por_email(cur, payload["email"]):
            return jsonify({"status": "error", "error": "E-mail já cadastrado."}), 409

        id_usuario = rbac_criar_ou_atualizar_usuario(
            cur,
            email=payload["email"],
            nome=payload["nome"],
            system_role=payload["system_role"],
            password_hash=payload["password_hash"],
            id_clie=payload["id_clie"],
        )
        conn.commit()
        usuario = rbac_buscar_usuario_por_id(cur, id_usuario)
        return jsonify({
            "status": "success",
            "data": _serializar_usuario(usuario) if usuario else {"id_usuario": id_usuario},
        }), 201
    except Exception as exc:
        conn.rollback()
        return jsonify({"status": "error", "error": str(exc)}), 500
    finally:
        cur.close()
        conn.close()


def register_admin_users_routes(flask_app) -> None:
    flask_app.register_blueprint(admin_users_bp)

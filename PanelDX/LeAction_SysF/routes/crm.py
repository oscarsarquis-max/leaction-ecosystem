"""Rotas administrativas CRM — planos, contratos e dashboard MRR."""

from __future__ import annotations

from datetime import date

from flask import Blueprint, jsonify, request
from psycopg2.extras import Json, RealDictCursor

from rbac.constants import ROLE_SYSADMIN
from rbac.decorators import require_role
from services.consultor_repository import (
    atualizar_consultor,
    buscar_consultor_por_id,
    criar_consultor,
    desativar_consultor,
    listar_consultores,
    listar_usuarios_sem_perfil_consultor,
    serializar_consultor,
    validar_payload_consultor,
)
from services.crm_engine import (
    CONTRACT_STATUSES,
    PLANO_PERIODICIDADES,
    PLANO_TIPOS,
    beneficios_from_db,
    beneficios_to_jsonb,
    calc_percentual_execucao,
    montar_dashboard_payload,
    normalizar_periodicidade,
    parse_beneficios_input,
)

crm_bp = Blueprint("crm", __name__)


def _get_conn():
    from app import get_db_conn
    return get_db_conn()


def _decimal_to_float(value) -> float:
    if value is None:
        return 0.0
    return float(value)


def _serializar_plano(row: dict, *, vitrine: bool = False) -> dict:
    beneficios = beneficios_from_db(row.get("descricao_beneficios"))
    max_usuarios = row.get("max_usuarios")
    if max_usuarios is None:
        max_usuarios = 5
    base = {
        "id": row["id"],
        "nome": row["nome"],
        "valor_mensal": _decimal_to_float(row.get("valor_mensal")),
        "periodicidade": row.get("periodicidade") or "Mensal",
        "descricao_beneficios": beneficios,
        "max_usuarios": int(max_usuarios),
        "tipo_plano": (row.get("tipo_plano") or "base"),
        "ativo": bool(row.get("ativo", True)),
    }
    if vitrine:
        return base
    base["criado_em"] = row["criado_em"].isoformat() if row.get("criado_em") else None
    base["atualizado_em"] = row["atualizado_em"].isoformat() if row.get("atualizado_em") else None
    base["descricao_beneficios_texto"] = "\n".join(beneficios)
    return base


def _beneficios_json_value(raw) -> Json:
    if isinstance(raw, list):
        items = parse_beneficios_input(raw)
    else:
        items = parse_beneficios_input(raw)
    return Json(items)


def _persistir_plano(cur, payload: dict, plano_id: int | None = None) -> dict:
    """INSERT ou UPDATE de um plano (inclui descricao_beneficios como JSONB)."""
    if plano_id:
        sets = []
        values = []
        for key in ("nome", "valor_mensal", "ativo", "periodicidade", "max_usuarios", "tipo_plano"):
            if key in payload:
                sets.append(f"{key} = %s")
                values.append(payload[key])
        if "descricao_beneficios" in payload:
            sets.append("descricao_beneficios = %s")
            values.append(_beneficios_json_value(payload["descricao_beneficios"]))
        sets.append("atualizado_em = NOW()")
        values.append(plano_id)
        cur.execute(
            f"""
            UPDATE public.dx_planos
            SET {", ".join(sets)}
            WHERE id = %s
            RETURNING id, nome, valor_mensal, periodicidade, descricao_beneficios,
                      max_usuarios, tipo_plano, ativo, criado_em, atualizado_em;
            """,
            tuple(values),
        )
    else:
        cur.execute(
            """
            INSERT INTO public.dx_planos
                (nome, valor_mensal, periodicidade, descricao_beneficios, max_usuarios, tipo_plano, ativo)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id, nome, valor_mensal, periodicidade, descricao_beneficios,
                      max_usuarios, tipo_plano, ativo, criado_em, atualizado_em;
            """,
            (
                payload["nome"],
                payload.get("valor_mensal", 0),
                payload.get("periodicidade", "Mensal"),
                _beneficios_json_value(payload.get("descricao_beneficios", [])),
                int(payload.get("max_usuarios", 5)),
                payload.get("tipo_plano", "base"),
                payload.get("ativo", True),
            ),
        )
    row = cur.fetchone()
    if not row:
        raise ValueError("Plano não encontrado." if plano_id else "Falha ao criar plano.")
    return _serializar_plano(row)


def _listar_addons_vitrine(cur) -> list[dict]:
    cur.execute(
        """
        SELECT id, nome, valor_mensal, periodicidade, descricao_beneficios,
               max_usuarios, tipo_plano, ativo
        FROM public.dx_planos
        WHERE ativo = TRUE
          AND COALESCE(tipo_plano, 'base') = 'addon'
        ORDER BY valor_mensal ASC, nome ASC;
        """
    )
    rows = []
    for r in cur.fetchall():
        item = _serializar_plano(r, vitrine=True)
        item["tipo_plano"] = "addon"
        rows.append(item)
    return rows


def _listar_planos_vitrine(cur) -> list[dict]:
    cur.execute(
        """
        SELECT id, nome, valor_mensal, periodicidade, descricao_beneficios,
               max_usuarios, tipo_plano, ativo
        FROM public.dx_planos
        WHERE ativo = TRUE
          AND COALESCE(tipo_plano, 'base') = 'base'
        ORDER BY valor_mensal ASC, nome ASC;
        """
    )
    return [_serializar_plano(r, vitrine=True) for r in cur.fetchall()]


def _parse_date(raw, field_name: str) -> tuple[date | None, str | None]:
    if raw is None or raw == "":
        return None, f"{field_name} é obrigatório."
    try:
        return date.fromisoformat(str(raw).strip()[:10]), None
    except ValueError:
        return None, f"{field_name} inválido (use YYYY-MM-DD)."


def _serializar_contrato(row: dict) -> dict:
    inicio = row.get("data_inicio")
    vencimento = row.get("data_vencimento")
    return {
        "id": row["id"],
        "id_clie": row["id_clie"],
        "nome_clie": row.get("nome_clie"),
        "mail_clie": row.get("mail_clie"),
        "id_plano": row["id_plano"],
        "nome_plano": row.get("nome_plano"),
        "valor_negociado": _decimal_to_float(row.get("valor_negociado")),
        "status": row.get("status"),
        "data_inicio": inicio.isoformat() if hasattr(inicio, "isoformat") else inicio,
        "data_vencimento": vencimento.isoformat() if hasattr(vencimento, "isoformat") else vencimento,
        "id_consultor_origem": row.get("id_consultor_origem"),
        "id_consultor_tecnico": row.get("id_consultor_tecnico"),
        "consultor_origem_nome": row.get("consultor_origem_nome"),
        "consultor_tecnico_nome": row.get("consultor_tecnico_nome"),
        "percentual_execucao": calc_percentual_execucao(inicio, vencimento),
        "criado_em": row["criado_em"].isoformat() if row.get("criado_em") else None,
        "atualizado_em": row["atualizado_em"].isoformat() if row.get("atualizado_em") else None,
    }


_CONTRATO_FROM_SQL = """
    FROM public.dx_contratos c
    JOIN public.ctdi_clie cl ON cl.id_clie = c.id_clie
    JOIN public.dx_planos p ON p.id = c.id_plano
    LEFT JOIN public.dx_consultores cso ON cso.id = c.id_consultor_origem
    LEFT JOIN public.paneldx_usuarios uo ON uo.id_usuario = cso.user_id
    LEFT JOIN public.dx_consultores cst ON cst.id = c.id_consultor_tecnico
    LEFT JOIN public.paneldx_usuarios ut ON ut.id_usuario = cst.user_id
"""

_CONTRATO_SELECT_SQL = """
    SELECT
        c.id, c.id_clie, c.id_plano, c.valor_negociado, c.status,
        c.data_inicio, c.data_vencimento, c.criado_em, c.atualizado_em,
        c.id_consultor_origem, c.id_consultor_tecnico,
        cl.nome_clie, cl.mail_clie,
        p.nome AS nome_plano,
        uo.nome AS consultor_origem_nome,
        ut.nome AS consultor_tecnico_nome
"""


def _parse_consultor_opcional(data: dict, field: str, payload: dict) -> str | None:
    if field not in data:
        return None
    raw = data.get(field)
    if raw is None or raw == "":
        payload[field] = None
        return None
    try:
        payload[field] = int(raw)
    except (TypeError, ValueError):
        return f"{field} inválido."
    return None


def _validar_consultores_payload(cur, payload: dict) -> str | None:
    for field in ("id_consultor_origem", "id_consultor_tecnico"):
        cid = payload.get(field)
        if cid is None:
            continue
        cur.execute(
            "SELECT id FROM public.dx_consultores WHERE id = %s AND ativo = TRUE;",
            (cid,),
        )
        if not cur.fetchone():
            return f"Consultor informado em {field} não encontrado ou inativo."
    return None


def _validar_payload_plano(data: dict, *, criar: bool) -> tuple[dict | None, str | None]:
    if not isinstance(data, dict):
        return None, "JSON inválido."

    nome = (data.get("nome") or "").strip()
    if criar and not nome:
        return None, "Nome do plano é obrigatório."

    payload: dict = {}
    if nome:
        payload["nome"] = nome

    if "valor_mensal" in data or criar:
        try:
            payload["valor_mensal"] = float(data.get("valor_mensal", 0))
        except (TypeError, ValueError):
            return None, "valor_mensal inválido."

    if "ativo" in data:
        payload["ativo"] = bool(data["ativo"])

    if "periodicidade" in data or criar:
        periodicidade = normalizar_periodicidade(data.get("periodicidade", "Mensal"))
        if periodicidade not in PLANO_PERIODICIDADES:
            return None, "periodicidade inválida (Mensal, Semestral, Anual)."
        payload["periodicidade"] = periodicidade

    if criar:
        raw_beneficios = data.get("descricao_beneficios")
        if raw_beneficios is None:
            raw_beneficios = data.get("beneficios", "")
        payload["descricao_beneficios"] = parse_beneficios_input(raw_beneficios)
    elif "descricao_beneficios" in data or "beneficios" in data:
        raw_beneficios = data.get("descricao_beneficios")
        if raw_beneficios is None:
            raw_beneficios = data.get("beneficios", "")
        payload["descricao_beneficios"] = parse_beneficios_input(raw_beneficios)

    if "max_usuarios" in data or criar:
        try:
            max_usuarios = int(data.get("max_usuarios", 5))
        except (TypeError, ValueError):
            return None, "max_usuarios inválido (informe um número inteiro)."
        if max_usuarios < 1:
            return None, "max_usuarios deve ser pelo menos 1."
        payload["max_usuarios"] = max_usuarios

    if "tipo_plano" in data or criar:
        tipo = (data.get("tipo_plano") or "base").strip().lower()
        if tipo not in PLANO_TIPOS:
            return None, "tipo_plano inválido (base ou addon)."
        payload["tipo_plano"] = tipo

    return payload, None


def _validar_payload_contrato(data: dict, *, criar: bool) -> tuple[dict | None, str | None]:
    if not isinstance(data, dict):
        return None, "JSON inválido."

    payload: dict = {}

    if criar or "id_clie" in data:
        try:
            payload["id_clie"] = int(data.get("id_clie"))
        except (TypeError, ValueError):
            return None, "id_clie inválido."

    if criar or "id_plano" in data:
        try:
            payload["id_plano"] = int(data.get("id_plano"))
        except (TypeError, ValueError):
            return None, "id_plano inválido."

    if criar or "valor_negociado" in data:
        try:
            payload["valor_negociado"] = float(data.get("valor_negociado"))
        except (TypeError, ValueError):
            return None, "valor_negociado inválido."

    if criar or "status" in data:
        status = (data.get("status") or "").strip().lower()
        if status and status not in CONTRACT_STATUSES:
            return None, "status inválido (ativo, inadimplente, cancelado, trial)."
        if status:
            payload["status"] = status
    elif criar:
        payload["status"] = "trial"

    if criar or "data_inicio" in data:
        inicio, err = _parse_date(data.get("data_inicio"), "data_inicio")
        if err:
            return None, err
        payload["data_inicio"] = inicio

    if criar or "data_vencimento" in data:
        vencimento, err = _parse_date(data.get("data_vencimento"), "data_vencimento")
        if err:
            return None, err
        payload["data_vencimento"] = vencimento

    if (
        payload.get("data_inicio")
        and payload.get("data_vencimento")
        and payload["data_vencimento"] < payload["data_inicio"]
    ):
        return None, "data_vencimento deve ser >= data_inicio."

    for field in ("id_consultor_origem", "id_consultor_tecnico"):
        err_field = _parse_consultor_opcional(data, field, payload)
        if err_field:
            return None, err_field

    return payload, None


# ---------------------------------------------------------------------------
# Vitrine pública (ActionHub / pricing)
# ---------------------------------------------------------------------------
@crm_bp.route("/api/public/vitrine/planos", methods=["GET"])
def crm_vitrine_planos_publicos():
    conn = _get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cur.execute(
            """
            SELECT id, nome, valor_mensal, periodicidade, descricao_beneficios,
                   max_usuarios, ativo
            FROM public.dx_planos
            WHERE ativo = TRUE
              AND COALESCE(tipo_plano, 'base') = 'base'
            ORDER BY valor_mensal ASC, nome ASC;
            """
        )
        planos = [_serializar_plano(r, vitrine=True) for r in cur.fetchall()]
        resp = jsonify({"status": "success", "planos": planos})
        resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
        return resp, 200
    except Exception as exc:
        return jsonify({"status": "error", "error": str(exc)}), 500
    finally:
        cur.close()
        conn.close()


@crm_bp.route("/api/public/planos-addon/<int:addon_id>", methods=["GET"])
def crm_obter_plano_addon_publico(addon_id: int):
    from services.addon_engine import obter_plano_addon

    conn = _get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        plano = obter_plano_addon(cur, addon_id)
        if not plano or not plano.get("ativo"):
            return jsonify({"status": "error", "error": "Pacote add-on não encontrado."}), 404
        return jsonify({
            "status": "success",
            "addon": {
                "id": plano["id"],
                "nome": plano["nome"],
                "valor_mensal": _decimal_to_float(plano.get("valor_mensal")),
                "periodicidade": plano.get("periodicidade") or "Mensal",
                "max_usuarios": int(plano.get("max_usuarios") or 0),
                "tipo_plano": "addon",
            },
        }), 200
    except Exception as exc:
        return jsonify({"status": "error", "error": str(exc)}), 500
    finally:
        cur.close()
        conn.close()


# ---------------------------------------------------------------------------
# Planos (admin)
# ---------------------------------------------------------------------------
@crm_bp.route("/api/admin/crm/planos", methods=["GET"])
@require_role(ROLE_SYSADMIN)
def crm_listar_planos():
    conn = _get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        apenas_ativos = request.args.get("apenas_ativos", "").lower() in ("1", "true", "yes")
        sql = """
            SELECT id, nome, valor_mensal, periodicidade, descricao_beneficios,
                   max_usuarios, tipo_plano, ativo, criado_em, atualizado_em
            FROM public.dx_planos
        """
        if apenas_ativos:
            sql += " WHERE ativo = TRUE"
        sql += " ORDER BY valor_mensal ASC, nome ASC;"
        cur.execute(sql)
        planos = [_serializar_plano(r) for r in cur.fetchall()]
        return jsonify({"status": "success", "planos": planos}), 200
    except Exception as exc:
        return jsonify({"status": "error", "error": str(exc)}), 500
    finally:
        cur.close()
        conn.close()


@crm_bp.route("/api/admin/crm/planos", methods=["POST"])
@require_role(ROLE_SYSADMIN)
def crm_criar_plano():
    data = request.get_json(silent=True) or {}
    payload, err = _validar_payload_plano(data, criar=True)
    if err:
        return jsonify({"status": "error", "error": err}), 400

    conn = _get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        plano = _persistir_plano(cur, payload, plano_id=None)
        conn.commit()
        return jsonify({"status": "success", "plano": plano}), 201
    except Exception as exc:
        conn.rollback()
        return jsonify({"status": "error", "error": str(exc)}), 500
    finally:
        cur.close()
        conn.close()


@crm_bp.route("/api/admin/crm/planos/<int:plano_id>", methods=["PUT"])
@require_role(ROLE_SYSADMIN)
def crm_atualizar_plano(plano_id: int):
    data = request.get_json(silent=True) or {}
    payload, err = _validar_payload_plano(data, criar=False)
    if err:
        return jsonify({"status": "error", "error": err}), 400
    if not payload:
        return jsonify({"status": "error", "error": "Nenhum campo para atualizar."}), 400

    conn = _get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        plano = _persistir_plano(cur, payload, plano_id=plano_id)
        conn.commit()
        return jsonify({"status": "success", "plano": plano}), 200
    except ValueError as exc:
        conn.rollback()
        return jsonify({"status": "error", "error": str(exc)}), 404
    except Exception as exc:
        conn.rollback()
        return jsonify({"status": "error", "error": str(exc)}), 500
    finally:
        cur.close()
        conn.close()


@crm_bp.route("/api/admin/crm/vitrine/publicar", methods=["POST"])
@require_role(ROLE_SYSADMIN)
def crm_publicar_vitrine_lote():
    """Persiste todos os planos em lote e publica catálogo ativo no ActionHub."""
    from services.vitrine_sync import publicar_vitrine_actionhub

    data = request.get_json(silent=True) or {}
    items = data.get("planos")
    if not isinstance(items, list) or not items:
        return jsonify({"status": "error", "error": "Envie planos[] para salvar e publicar."}), 400

    conn = _get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    salvos: list[dict] = []
    try:
        for idx, item in enumerate(items):
            if not isinstance(item, dict):
                return jsonify({"status": "error", "error": f"Plano #{idx + 1} inválido."}), 400
            criar = not item.get("id")
            payload, err = _validar_payload_plano(item, criar=criar)
            if err:
                return jsonify({"status": "error", "error": f"Plano #{idx + 1}: {err}"}), 400
            plano_id = int(item["id"]) if item.get("id") else None
            salvos.append(_persistir_plano(cur, payload, plano_id=plano_id))

        vitrine = _listar_planos_vitrine(cur)
        addons = _listar_addons_vitrine(cur)
        conn.commit()

        hub_receipt = publicar_vitrine_actionhub(vitrine, addons=addons)

        cur.execute(
            """
            INSERT INTO public.dx_vitrine_publicacoes
                (sync_id, planos_count, hub_received, hub_received_at, hub_response)
            VALUES (%s::uuid, %s, TRUE, NOW(), %s::jsonb)
            RETURNING id, sync_id, hub_received_at, criado_em;
            """,
            (
                hub_receipt.get("sync_id"),
                hub_receipt.get("planos_count", len(vitrine)),
                Json(hub_receipt),
            ),
        )
        log_row = cur.fetchone()
        conn.commit()

        return jsonify({
            "status": "success",
            "planos": salvos,
            "vitrine": vitrine,
            "hub": hub_receipt,
            "publicacao": {
                "id": log_row["id"],
                "sync_id": str(log_row["sync_id"]),
                "hub_received_at": log_row["hub_received_at"].isoformat()
                if log_row.get("hub_received_at")
                else hub_receipt.get("received_at"),
                "criado_em": log_row["criado_em"].isoformat() if log_row.get("criado_em") else None,
            },
        }), 200
    except Exception as exc:
        conn.rollback()
        return jsonify({"status": "error", "error": str(exc)}), 500
    finally:
        cur.close()
        conn.close()


@crm_bp.route("/api/admin/crm/vitrine/ultima-publicacao", methods=["GET"])
@require_role(ROLE_SYSADMIN)
def crm_ultima_publicacao_vitrine():
    conn = _get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cur.execute(
            """
            SELECT id, sync_id, planos_count, hub_received, hub_received_at, hub_response, criado_em
            FROM public.dx_vitrine_publicacoes
            ORDER BY id DESC
            LIMIT 1;
            """
        )
        row = cur.fetchone()
        if not row:
            return jsonify({"status": "success", "publicacao": None}), 200
        return jsonify({
            "status": "success",
            "publicacao": {
                "id": row["id"],
                "sync_id": str(row["sync_id"]),
                "planos_count": row["planos_count"],
                "hub_received": row["hub_received"],
                "hub_received_at": row["hub_received_at"].isoformat() if row.get("hub_received_at") else None,
                "hub_response": row.get("hub_response"),
                "criado_em": row["criado_em"].isoformat() if row.get("criado_em") else None,
            },
        }), 200
    except Exception as exc:
        return jsonify({"status": "error", "error": str(exc)}), 500
    finally:
        cur.close()
        conn.close()


# ---------------------------------------------------------------------------
# Consultores (parceiros)
# ---------------------------------------------------------------------------
@crm_bp.route("/api/admin/crm/consultores", methods=["GET"])
@require_role(ROLE_SYSADMIN)
def crm_listar_consultores():
    incluir_inativos = request.args.get("incluir_inativos", "0") == "1"
    conn = _get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        consultores = listar_consultores(cur, incluir_inativos=incluir_inativos)
        return jsonify({"status": "success", "consultores": consultores}), 200
    except Exception as exc:
        return jsonify({"status": "error", "error": str(exc)}), 500
    finally:
        cur.close()
        conn.close()


@crm_bp.route("/api/admin/crm/consultores/usuarios-sem-perfil", methods=["GET"])
@require_role(ROLE_SYSADMIN)
def crm_listar_usuarios_sem_perfil_consultor():
    conn = _get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        usuarios = listar_usuarios_sem_perfil_consultor(cur)
        return jsonify({"status": "success", "usuarios": usuarios}), 200
    except Exception as exc:
        return jsonify({"status": "error", "error": str(exc)}), 500
    finally:
        cur.close()
        conn.close()


@crm_bp.route("/api/admin/crm/consultores/<int:consultor_id>", methods=["GET"])
@require_role(ROLE_SYSADMIN)
def crm_obter_consultor(consultor_id: int):
    conn = _get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        row = buscar_consultor_por_id(cur, consultor_id)
        if not row:
            return jsonify({"status": "error", "error": "Consultor não encontrado."}), 404
        return jsonify({"status": "success", "consultor": serializar_consultor(row)}), 200
    except Exception as exc:
        return jsonify({"status": "error", "error": str(exc)}), 500
    finally:
        cur.close()
        conn.close()


@crm_bp.route("/api/admin/crm/consultores", methods=["POST"])
@crm_bp.route("/api/admin/consultores", methods=["POST"])
@require_role(ROLE_SYSADMIN)
def crm_criar_consultor():
    data = request.get_json(silent=True) or {}
    conn = _get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        payload, erro = validar_payload_consultor(cur, data, criar=True)
        if erro:
            return jsonify({"status": "error", "error": erro}), 400
        consultor = criar_consultor(cur, payload)
        conn.commit()
        return jsonify({"status": "success", "consultor": consultor}), 201
    except Exception as exc:
        conn.rollback()
        return jsonify({"status": "error", "error": str(exc)}), 500
    finally:
        cur.close()
        conn.close()


@crm_bp.route("/api/admin/crm/consultores/<int:consultor_id>", methods=["PUT"])
@crm_bp.route("/api/admin/consultores/<int:consultor_id>", methods=["PUT"])
@require_role(ROLE_SYSADMIN)
def crm_atualizar_consultor(consultor_id: int):
    data = request.get_json(silent=True) or {}
    conn = _get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        if not buscar_consultor_por_id(cur, consultor_id):
            return jsonify({"status": "error", "error": "Consultor não encontrado."}), 404
        payload, erro = validar_payload_consultor(
            cur, data, criar=False, consultor_id=consultor_id
        )
        if erro:
            return jsonify({"status": "error", "error": erro}), 400
        if not payload:
            return jsonify({"status": "error", "error": "Nenhum campo para atualizar."}), 400
        consultor = atualizar_consultor(cur, consultor_id, payload)
        conn.commit()
        return jsonify({"status": "success", "consultor": consultor}), 200
    except ValueError as exc:
        conn.rollback()
        return jsonify({"status": "error", "error": str(exc)}), 404
    except Exception as exc:
        conn.rollback()
        return jsonify({"status": "error", "error": str(exc)}), 500
    finally:
        cur.close()
        conn.close()


@crm_bp.route("/api/admin/crm/consultores/<int:consultor_id>", methods=["DELETE"])
@crm_bp.route("/api/admin/consultores/<int:consultor_id>", methods=["DELETE"])
@require_role(ROLE_SYSADMIN)
def crm_desativar_consultor(consultor_id: int):
    conn = _get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        desativar_consultor(cur, consultor_id)
        conn.commit()
        return jsonify({"status": "success", "message": "Consultor desativado."}), 200
    except ValueError as exc:
        conn.rollback()
        return jsonify({"status": "error", "error": str(exc)}), 404
    except Exception as exc:
        conn.rollback()
        return jsonify({"status": "error", "error": str(exc)}), 500
    finally:
        cur.close()
        conn.close()


# ---------------------------------------------------------------------------
# Contratos
# ---------------------------------------------------------------------------
@crm_bp.route("/api/admin/crm/contratos", methods=["GET"])
@require_role(ROLE_SYSADMIN)
def crm_listar_contratos():
    conn = _get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        status_filter = (request.args.get("status") or "").strip().lower()
        id_clie = request.args.get("id_clie")

        sql = f"""
            {_CONTRATO_SELECT_SQL}
            {_CONTRATO_FROM_SQL}
            WHERE 1=1
        """
        params: list = []
        if status_filter:
            sql += " AND c.status = %s"
            params.append(status_filter)
        if id_clie:
            sql += " AND c.id_clie = %s"
            params.append(int(id_clie))
        sql += " ORDER BY c.data_inicio DESC, c.id DESC;"

        cur.execute(sql, tuple(params))
        contratos = [_serializar_contrato(r) for r in cur.fetchall()]
        return jsonify({"status": "success", "contratos": contratos}), 200
    except Exception as exc:
        return jsonify({"status": "error", "error": str(exc)}), 500
    finally:
        cur.close()
        conn.close()


@crm_bp.route("/api/admin/crm/contratos/<int:contrato_id>", methods=["GET"])
@require_role(ROLE_SYSADMIN)
def crm_obter_contrato(contrato_id: int):
    conn = _get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cur.execute(
            f"""
            {_CONTRATO_SELECT_SQL}
            {_CONTRATO_FROM_SQL}
            WHERE c.id = %s;
            """,
            (contrato_id,),
        )
        row = cur.fetchone()
        if not row:
            return jsonify({"status": "error", "error": "Contrato não encontrado."}), 404
        from services.addon_engine import listar_addons_contrato

        contrato = _serializar_contrato(row)
        contrato["addons"] = listar_addons_contrato(cur, contrato_id)
        return jsonify({"status": "success", "contrato": contrato}), 200
    except Exception as exc:
        return jsonify({"status": "error", "error": str(exc)}), 500
    finally:
        cur.close()
        conn.close()


@crm_bp.route("/api/admin/crm/contratos", methods=["POST"])
@require_role(ROLE_SYSADMIN)
def crm_criar_contrato():
    data = request.get_json(silent=True) or {}
    payload, err = _validar_payload_contrato(data, criar=True)
    if err:
        return jsonify({"status": "error", "error": err}), 400

    conn = _get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cur.execute("SELECT id FROM public.ctdi_clie WHERE id_clie = %s;", (payload["id_clie"],))
        if not cur.fetchone():
            return jsonify({"status": "error", "error": "Cliente não encontrado."}), 404

        cur.execute("SELECT id, valor_mensal FROM public.dx_planos WHERE id = %s;", (payload["id_plano"],))
        plano = cur.fetchone()
        if not plano:
            return jsonify({"status": "error", "error": "Plano não encontrado."}), 404

        err_cons = _validar_consultores_payload(cur, payload)
        if err_cons:
            return jsonify({"status": "error", "error": err_cons}), 400

        valor = payload.get("valor_negociado")
        if valor is None:
            valor = float(plano["valor_mensal"])

        cur.execute(
            """
            INSERT INTO public.dx_contratos
                (id_clie, id_plano, valor_negociado, status, data_inicio, data_vencimento,
                 id_consultor_origem, id_consultor_tecnico)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id;
            """,
            (
                payload["id_clie"],
                payload["id_plano"],
                valor,
                payload.get("status", "trial"),
                payload["data_inicio"],
                payload["data_vencimento"],
                payload.get("id_consultor_origem"),
                payload.get("id_consultor_tecnico"),
            ),
        )
        new_id = cur.fetchone()["id"]
        conn.commit()

        cur.execute(
            f"""
            {_CONTRATO_SELECT_SQL}
            {_CONTRATO_FROM_SQL}
            WHERE c.id = %s;
            """,
            (new_id,),
        )
        row = cur.fetchone()
        return jsonify({"status": "success", "contrato": _serializar_contrato(row)}), 201
    except Exception as exc:
        conn.rollback()
        return jsonify({"status": "error", "error": str(exc)}), 500
    finally:
        cur.close()
        conn.close()


@crm_bp.route("/api/admin/crm/contratos/<int:contrato_id>", methods=["PUT"])
@require_role(ROLE_SYSADMIN)
def crm_atualizar_contrato(contrato_id: int):
    data = request.get_json(silent=True) or {}
    payload, err = _validar_payload_contrato(data, criar=False)
    if err:
        return jsonify({"status": "error", "error": err}), 400
    if not payload:
        return jsonify({"status": "error", "error": "Nenhum campo para atualizar."}), 400

    conn = _get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        if "id_plano" in payload:
            cur.execute("SELECT id FROM public.dx_planos WHERE id = %s;", (payload["id_plano"],))
            if not cur.fetchone():
                return jsonify({"status": "error", "error": "Plano não encontrado."}), 404

        if "id_clie" in payload:
            cur.execute("SELECT id_clie FROM public.ctdi_clie WHERE id_clie = %s;", (payload["id_clie"],))
            if not cur.fetchone():
                return jsonify({"status": "error", "error": "Cliente não encontrado."}), 404

        err_cons = _validar_consultores_payload(cur, payload)
        if err_cons:
            return jsonify({"status": "error", "error": err_cons}), 400

        sets = []
        values = []
        for key in (
            "id_clie", "id_plano", "valor_negociado", "status", "data_inicio", "data_vencimento",
            "id_consultor_origem", "id_consultor_tecnico",
        ):
            if key in payload:
                sets.append(f"{key} = %s")
                values.append(payload[key])
        sets.append("atualizado_em = NOW()")
        values.append(contrato_id)

        cur.execute(
            f"""
            UPDATE public.dx_contratos
            SET {", ".join(sets)}
            WHERE id = %s
            RETURNING id;
            """,
            tuple(values),
        )
        if not cur.fetchone():
            return jsonify({"status": "error", "error": "Contrato não encontrado."}), 404
        conn.commit()

        cur.execute(
            f"""
            {_CONTRATO_SELECT_SQL}
            {_CONTRATO_FROM_SQL}
            WHERE c.id = %s;
            """,
            (contrato_id,),
        )
        row = cur.fetchone()
        return jsonify({"status": "success", "contrato": _serializar_contrato(row)}), 200
    except Exception as exc:
        conn.rollback()
        return jsonify({"status": "error", "error": str(exc)}), 500
    finally:
        cur.close()
        conn.close()


# ---------------------------------------------------------------------------
# Dashboard MRR
# ---------------------------------------------------------------------------
@crm_bp.route("/api/admin/crm/dashboard", methods=["GET"])
@require_role(ROLE_SYSADMIN)
def crm_dashboard():
    conn = _get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cur.execute(
            """
            SELECT
                c.id, c.id_clie, c.id_plano, c.valor_negociado, c.status,
                c.data_inicio, c.data_vencimento,
                cl.nome_clie, cl.mail_clie,
                p.nome AS nome_plano
            FROM public.dx_contratos c
            JOIN public.ctdi_clie cl ON cl.id_clie = c.id_clie
            JOIN public.dx_planos p ON p.id = c.id_plano
            WHERE c.status = 'ativo'
            ORDER BY c.data_vencimento ASC, c.id ASC;
            """
        )
        contratos_ativos = cur.fetchall()

        cur.execute(
            """
            SELECT
                p.id AS id_plano,
                p.nome AS nome_plano,
                p.tipo_plano,
                COALESCE(SUM(c.valor_negociado), 0) AS mrr,
                COUNT(c.id) AS contratos_ativos
            FROM public.dx_planos p
            LEFT JOIN public.dx_contratos c
                ON c.id_plano = p.id AND c.status = 'ativo'
            WHERE COALESCE(p.tipo_plano, 'base') = 'base'
            GROUP BY p.id, p.nome, p.tipo_plano
            ORDER BY p.valor_mensal ASC, p.nome ASC;
            """
        )
        receita_por_plano = cur.fetchall()

        cur.execute(
            """
            SELECT
                p.id AS id_plano,
                p.nome AS nome_plano,
                'addon' AS tipo_plano,
                COALESCE(SUM(p.valor_mensal * a.quantidade), 0) AS mrr,
                COUNT(a.id) AS contratos_ativos
            FROM public.dx_planos p
            JOIN public.dx_contratos_addons a ON a.id_plano_addon = p.id AND a.status = 'ativo'
            JOIN public.dx_contratos c ON c.id = a.id_contrato AND c.status = 'ativo'
            WHERE p.tipo_plano = 'addon'
            GROUP BY p.id, p.nome
            ORDER BY p.valor_mensal ASC, p.nome ASC;
            """
        )
        receita_addons = cur.fetchall()
        receita_por_plano = list(receita_por_plano) + list(receita_addons)

        from services.addon_engine import somar_mrr_addons_ativos

        dashboard = montar_dashboard_payload(
            contratos_ativos,
            receita_por_plano,
            mrr_addons=somar_mrr_addons_ativos(cur),
        )
        return jsonify({"status": "success", **dashboard}), 200
    except Exception as exc:
        return jsonify({"status": "error", "error": str(exc)}), 500
    finally:
        cur.close()
        conn.close()


@crm_bp.route("/api/admin/crm/contratos/<int:contrato_id>/addons", methods=["GET"])
@require_role(ROLE_SYSADMIN)
def crm_listar_addons_contrato(contrato_id: int):
    from services.addon_engine import listar_addons_contrato

    conn = _get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cur.execute("SELECT id FROM public.dx_contratos WHERE id = %s;", (contrato_id,))
        if not cur.fetchone():
            return jsonify({"status": "error", "error": "Contrato não encontrado."}), 404
        addons = listar_addons_contrato(cur, contrato_id)
        return jsonify({"status": "success", "addons": addons}), 200
    except Exception as exc:
        return jsonify({"status": "error", "error": str(exc)}), 500
    finally:
        cur.close()
        conn.close()


@crm_bp.route("/api/admin/crm/contratos/<int:contrato_id>/addons", methods=["POST"])
@require_role(ROLE_SYSADMIN)
def crm_adicionar_addon_contrato(contrato_id: int):
    from services.addon_engine import obter_plano_addon

    data = request.get_json(silent=True) or {}
    try:
        id_plano_addon = int(data.get("id_plano_addon"))
        quantidade = int(data.get("quantidade", 1))
    except (TypeError, ValueError):
        return jsonify({"status": "error", "error": "id_plano_addon e quantidade inválidos."}), 400

    conn = _get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cur.execute("SELECT id FROM public.dx_contratos WHERE id = %s;", (contrato_id,))
        if not cur.fetchone():
            return jsonify({"status": "error", "error": "Contrato não encontrado."}), 404
        if not obter_plano_addon(cur, id_plano_addon):
            return jsonify({"status": "error", "error": "Pacote add-on inválido."}), 400

        qty = max(1, quantidade)
        hub_key = f"admin:{contrato_id}:{id_plano_addon}:{qty}"
        cur.execute(
            """
            INSERT INTO public.dx_contratos_addons
                (id_contrato, id_plano_addon, quantidade, status, hub_order_id)
            VALUES (%s, %s, %s, 'ativo', %s)
            RETURNING id, id_contrato, id_plano_addon, quantidade, status;
            """,
            (contrato_id, id_plano_addon, qty, hub_key),
        )
        row = cur.fetchone()
        conn.commit()
        return jsonify({"status": "success", "addon": dict(row)}), 201
    except ValueError as exc:
        conn.rollback()
        return jsonify({"status": "error", "error": str(exc)}), 400
    except Exception as exc:
        conn.rollback()
        return jsonify({"status": "error", "error": str(exc)}), 500
    finally:
        cur.close()
        conn.close()


@crm_bp.route("/api/admin/crm/contratos/<int:contrato_id>/addons/<int:addon_id>", methods=["DELETE"])
@require_role(ROLE_SYSADMIN)
def crm_cancelar_addon_contrato(contrato_id: int, addon_id: int):
    from services.addon_engine import cancelar_addon_contrato

    conn = _get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT id FROM public.dx_contratos_addons WHERE id = %s AND id_contrato = %s;",
            (addon_id, contrato_id),
        )
        if not cur.fetchone():
            return jsonify({"status": "error", "error": "Add-on não encontrado neste contrato."}), 404
        if not cancelar_addon_contrato(cur, addon_id):
            return jsonify({"status": "error", "error": "Add-on já estava cancelado."}), 409
        conn.commit()
        return jsonify({"status": "success", "message": "Pacote add-on cancelado."}), 200
    except Exception as exc:
        conn.rollback()
        return jsonify({"status": "error", "error": str(exc)}), 500
    finally:
        cur.close()
        conn.close()


def register_crm_routes(flask_app) -> None:
    flask_app.register_blueprint(crm_bp)

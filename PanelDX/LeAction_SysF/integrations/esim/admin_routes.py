"""Rotas administrativas eSIM — catálogo e provedores."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any

from flask import Blueprint, jsonify, request
from psycopg2.extras import Json, RealDictCursor

from integrations.esim.processor import esim_processar_webhook
from integrations.esim.repository import esim_ensure_schema, esim_get_db_connection

esim_admin_bp = Blueprint("esim_admin", __name__)

_CODIGO_RE = re.compile(r"^[A-Z0-9_]{3,64}$")

# Cliente padrão para simulação admin → Mesa (seed dev / QA)
_ESIM_DISPARO_CLIENTE_EMAILS = (
    "sistema@paneldx.com.br",
    "sistesma@paneldx.com.br",
)


def _esim_admin_resolver_cliente_disparo(cursor) -> tuple[int, str, str]:
    """Resolve id_clie do cliente sistema PanelDX para disparos de QA."""
    cursor.execute(
        """
        SELECT id_clie, nome_clie, mail_clie
        FROM public.ctdi_clie
        WHERE LOWER(TRIM(mail_clie)) = ANY(%s)
        ORDER BY id_clie ASC
        LIMIT 1;
        """,
        ([e.lower() for e in _ESIM_DISPARO_CLIENTE_EMAILS],),
    )
    row = cursor.fetchone()
    if not row:
        emails = " ou ".join(_ESIM_DISPARO_CLIENTE_EMAILS)
        raise ValueError(f"Cliente de disparo não encontrado ({emails}). Execute o seed de desenvolvimento.")
    return int(row["id_clie"]), row.get("nome_clie") or "", row.get("mail_clie") or ""


def _esim_admin_row_catalog(row: dict) -> dict:
    blocos = row.get("blocos_candidatos") or []
    if isinstance(blocos, str):
        try:
            blocos = json.loads(blocos)
        except (TypeError, json.JSONDecodeError):
            blocos = []
    return {
        "id": row["id"],
        "codigo_evento": row.get("codigo_evento"),
        "descricao_tecnica": row.get("descricao_tecnica"),
        "dimensao_fixada": row.get("dimensao_fixada"),
        "dominio_fixado": row.get("dominio_fixado"),
        "blocos_candidatos": list(blocos),
        "provedor_id": row.get("provedor_id"),
        "provedor_nome": row.get("provedor_nome"),
    }


def _esim_admin_row_provedor(row: dict) -> dict:
    cfg = row.get("config_json") or {}
    if isinstance(cfg, str):
        try:
            cfg = json.loads(cfg)
        except (TypeError, json.JSONDecodeError):
            cfg = {}
    return {
        "id": row["id"],
        "nome": row.get("nome"),
        "criado_em": row.get("criado_em").isoformat() if row.get("criado_em") else None,
        "webhook_path": cfg.get("webhook_path") or "",
        "upload_endpoint": cfg.get("upload_endpoint") or "",
        "slug": cfg.get("slug") or "",
        "config_json": cfg,
    }


def _esim_admin_validar_catalog_payload(data: dict[str, Any], *, parcial: bool = False) -> tuple[dict | None, str | None]:
    if not data or not isinstance(data, dict):
        return None, "Corpo JSON inválido."

    out: dict[str, Any] = {}

    if "codigo_evento" in data or not parcial:
        codigo = (data.get("codigo_evento") or "").strip().upper()
        if not codigo:
            return None, "codigo_evento é obrigatório."
        if not _CODIGO_RE.match(codigo):
            return None, "codigo_evento deve conter apenas A-Z, 0-9 e underscore (3–64 caracteres)."
        out["codigo_evento"] = codigo

    for campo in ("descricao_tecnica", "dimensao_fixada", "dominio_fixado"):
        if campo in data or not parcial:
            valor = (data.get(campo) or "").strip()
            if not valor:
                return None, f"{campo} é obrigatório."
            out[campo] = valor

    if "blocos_candidatos" in data or not parcial:
        blocos = data.get("blocos_candidatos")
        if not isinstance(blocos, list) or not blocos:
            return None, "Selecione ao menos um bloco candidato do framework."
        normalizados = []
        for item in blocos:
            nome = str(item).strip()
            if nome:
                normalizados.append(nome)
        if not normalizados:
            return None, "Selecione ao menos um bloco candidato do framework."
        out["blocos_candidatos"] = normalizados

    if "provedor_id" in data or not parcial:
        try:
            out["provedor_id"] = int(data.get("provedor_id"))
        except (TypeError, ValueError):
            return None, "provedor_id deve ser numérico."

    return out, None


def _esim_admin_validar_provedor_payload(data: dict[str, Any], *, parcial: bool = False) -> tuple[dict | None, str | None]:
    if not data or not isinstance(data, dict):
        return None, "Corpo JSON inválido."

    out: dict[str, Any] = {"config_json": dict(data.get("config_json") or {})}

    if "nome" in data or not parcial:
        nome = (data.get("nome") or "").strip()
        if not nome:
            return None, "nome é obrigatório."
        out["nome"] = nome

    for campo in ("webhook_path", "upload_endpoint", "slug"):
        if campo in data:
            out["config_json"][campo] = (data.get(campo) or "").strip()

    if not parcial:
        if not out["config_json"].get("webhook_path"):
            out["config_json"]["webhook_path"] = "/api/webhooks/esim"

    return out, None


@esim_admin_bp.route("/api/admin/esim/catalog", methods=["GET"])
def esim_admin_listar_catalog():
    conn = esim_get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        esim_ensure_schema(conn)
        cursor.execute(
            """
            SELECT c.id, c.codigo_evento, c.descricao_tecnica, c.dimensao_fixada,
                   c.dominio_fixado, c.blocos_candidatos, c.provedor_id, p.nome AS provedor_nome
            FROM public.esim_eventos_catalog c
            JOIN public.esim_provedores p ON p.id = c.provedor_id
            ORDER BY c.codigo_evento ASC;
            """
        )
        items = [_esim_admin_row_catalog(dict(r)) for r in cursor.fetchall()]
        return jsonify({"status": "success", "data": items}), 200
    except Exception as exc:
        return jsonify({"status": "error", "message": str(exc)}), 500
    finally:
        cursor.close()
        conn.close()


@esim_admin_bp.route("/api/admin/esim/catalog", methods=["POST"])
def esim_admin_criar_catalog():
    payload, erro = _esim_admin_validar_catalog_payload(request.get_json(silent=True) or {})
    if erro:
        return jsonify({"status": "error", "message": erro}), 400

    conn = esim_get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        esim_ensure_schema(conn)
        cursor.execute("SELECT id FROM public.esim_provedores WHERE id = %s;", (payload["provedor_id"],))
        if not cursor.fetchone():
            return jsonify({"status": "error", "message": "Provedor não encontrado."}), 400

        cursor.execute(
            """
            INSERT INTO public.esim_eventos_catalog
                (codigo_evento, descricao_tecnica, dimensao_fixada, dominio_fixado, blocos_candidatos, provedor_id)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id;
            """,
            (
                payload["codigo_evento"],
                payload["descricao_tecnica"],
                payload["dimensao_fixada"],
                payload["dominio_fixado"],
                Json(payload["blocos_candidatos"]),
                payload["provedor_id"],
            ),
        )
        new_id = cursor.fetchone()["id"]
        conn.commit()
        return jsonify({"status": "success", "id": new_id, "message": "Evento cadastrado no catálogo."}), 201
    except Exception as exc:
        conn.rollback()
        if "unique" in str(exc).lower() or "duplicate" in str(exc).lower():
            return jsonify({"status": "error", "message": "codigo_evento já existe no catálogo."}), 409
        return jsonify({"status": "error", "message": str(exc)}), 500
    finally:
        cursor.close()
        conn.close()


@esim_admin_bp.route("/api/admin/esim/catalog/<int:item_id>", methods=["PUT"])
def esim_admin_atualizar_catalog(item_id: int):
    payload, erro = _esim_admin_validar_catalog_payload(request.get_json(silent=True) or {}, parcial=True)
    if erro:
        return jsonify({"status": "error", "message": erro}), 400
    if not payload:
        return jsonify({"status": "error", "message": "Nenhum campo para atualizar."}), 400

    conn = esim_get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        esim_ensure_schema(conn)
        if "provedor_id" in payload:
            cursor.execute("SELECT id FROM public.esim_provedores WHERE id = %s;", (payload["provedor_id"],))
            if not cursor.fetchone():
                return jsonify({"status": "error", "message": "Provedor não encontrado."}), 400

        sets = []
        values: list[Any] = []
        for key, val in payload.items():
            if key == "blocos_candidatos":
                sets.append("blocos_candidatos = %s")
                values.append(Json(val))
            else:
                sets.append(f"{key} = %s")
                values.append(val)
        values.append(item_id)

        cursor.execute(
            f"""
            UPDATE public.esim_eventos_catalog
            SET {', '.join(sets)}
            WHERE id = %s
            RETURNING id;
            """,
            tuple(values),
        )
        row = cursor.fetchone()
        if not row:
            conn.rollback()
            return jsonify({"status": "error", "message": "Registro não encontrado."}), 404
        conn.commit()
        return jsonify({"status": "success", "message": "Catálogo atualizado."}), 200
    except Exception as exc:
        conn.rollback()
        if "unique" in str(exc).lower() or "duplicate" in str(exc).lower():
            return jsonify({"status": "error", "message": "codigo_evento já existe no catálogo."}), 409
        return jsonify({"status": "error", "message": str(exc)}), 500
    finally:
        cursor.close()
        conn.close()


def _esim_admin_montar_payload_simulacao(catalog_row: dict, cliente_id: int) -> dict[str, Any]:
    """Monta telemetria bruta de QA a partir do catálogo (sem expor framework à operadora)."""
    codigo = (catalog_row.get("codigo_evento") or "").strip().upper()
    dominio_fixado = (catalog_row.get("dominio_fixado") or "Operações").strip()
    dimensao = (catalog_row.get("dimensao_fixada") or dominio_fixado).strip()
    descricao = (catalog_row.get("descricao_tecnica") or "").strip()
    if not descricao:
        descricao = (
            f"Simulação administrativa do evento {codigo} para validação na Mesa de Inovação. "
            f"Dimensão {dimensao}, domínio {dominio_fixado}."
        )

    dominio_acessado = dominio_fixado.lower().replace(" ", "-")
    if "." not in dominio_acessado:
        dominio_acessado += ".escola.com.br"

    return {
        "cliente_id": str(cliente_id),
        "codigo_evento": codigo,
        "iccid": f"8944SIM{cliente_id:04d}ADMIN",
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "grupo_acesso": dominio_fixado,
        "dominio_acessado": dominio_acessado,
        "titulo_alerta": f"[QA Admin] {codigo}",
        "descricao_evento": descricao,
        "trafego_mb_7dias": 35,
        "status_anomalia": "queda_critica",
        "variacao_percentual": -30,
    }


@esim_admin_bp.route("/api/admin/esim/catalog/<int:item_id>/disparar-mesa", methods=["POST"])
def esim_admin_disparar_evento_mesa(item_id: int):
    """Simula telemetria do catálogo e materializa alerta na Mesa de Inovação."""
    conn = esim_get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        esim_ensure_schema(conn)
        try:
            cliente_id, cliente_nome, cliente_email = _esim_admin_resolver_cliente_disparo(cursor)
        except ValueError as exc:
            return jsonify({"status": "error", "message": str(exc)}), 404

        cursor.execute(
            """
            SELECT c.id, c.codigo_evento, c.descricao_tecnica, c.dimensao_fixada,
                   c.dominio_fixado, c.blocos_candidatos, c.provedor_id, p.nome AS provedor_nome
            FROM public.esim_eventos_catalog c
            JOIN public.esim_provedores p ON p.id = c.provedor_id
            WHERE c.id = %s
            LIMIT 1;
            """,
            (item_id,),
        )
        row = cursor.fetchone()
        if not row:
            return jsonify({"status": "error", "message": "Evento do catálogo não encontrado."}), 404
    finally:
        cursor.close()
        conn.close()

    payload = _esim_admin_montar_payload_simulacao(dict(row), cliente_id)
    payload["cliente_id"] = str(cliente_id)

    try:
        resultado = esim_processar_webhook(payload, skip_auth=True)
    except Exception as exc:
        return jsonify({"status": "error", "message": str(exc)}), 500

    http_status = int(resultado.pop("http_status", 200))
    if resultado.get("status") == "error":
        return jsonify(resultado), http_status

    return jsonify({
        **resultado,
        "simulacao_admin": True,
        "cliente_disparo": {
            "id_clie": cliente_id,
            "nome_clie": cliente_nome,
            "mail_clie": cliente_email,
        },
        "message": (
            resultado.get("message")
            or f"Evento disparado na Mesa de Inovação ({cliente_email})."
        ),
    }), http_status


@esim_admin_bp.route("/api/admin/esim/catalog/<int:item_id>", methods=["DELETE"])
def esim_admin_excluir_catalog(item_id: int):
    conn = esim_get_db_connection()
    cursor = conn.cursor()
    try:
        esim_ensure_schema(conn)
        cursor.execute("DELETE FROM public.esim_eventos_catalog WHERE id = %s RETURNING id;", (item_id,))
        if not cursor.fetchone():
            conn.rollback()
            return jsonify({"status": "error", "message": "Registro não encontrado."}), 404
        conn.commit()
        return jsonify({"status": "success", "message": "Evento removido do catálogo."}), 200
    except Exception as exc:
        conn.rollback()
        if "restrict" in str(exc).lower() or "foreign" in str(exc).lower():
            return jsonify({
                "status": "error",
                "message": "Não é possível excluir: existem eventos vinculados a este código.",
            }), 409
        return jsonify({"status": "error", "message": str(exc)}), 500
    finally:
        cursor.close()
        conn.close()


@esim_admin_bp.route("/api/admin/esim/provedores", methods=["GET"])
def esim_admin_listar_provedores():
    conn = esim_get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        esim_ensure_schema(conn)
        cursor.execute(
            """
            SELECT id, nome, config_json, criado_em
            FROM public.esim_provedores
            ORDER BY nome ASC;
            """
        )
        items = [_esim_admin_row_provedor(dict(r)) for r in cursor.fetchall()]
        return jsonify({"status": "success", "data": items}), 200
    except Exception as exc:
        return jsonify({"status": "error", "message": str(exc)}), 500
    finally:
        cursor.close()
        conn.close()


@esim_admin_bp.route("/api/admin/esim/provedores", methods=["POST"])
def esim_admin_criar_provedor():
    payload, erro = _esim_admin_validar_provedor_payload(request.get_json(silent=True) or {})
    if erro:
        return jsonify({"status": "error", "message": erro}), 400

    conn = esim_get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        esim_ensure_schema(conn)
        cursor.execute(
            """
            INSERT INTO public.esim_provedores (nome, config_json)
            VALUES (%s, %s)
            RETURNING id;
            """,
            (payload["nome"], Json(payload["config_json"])),
        )
        new_id = cursor.fetchone()["id"]
        conn.commit()
        return jsonify({"status": "success", "id": new_id, "message": "Provedor cadastrado."}), 201
    except Exception as exc:
        conn.rollback()
        if "unique" in str(exc).lower():
            return jsonify({"status": "error", "message": "Já existe um provedor com este nome."}), 409
        return jsonify({"status": "error", "message": str(exc)}), 500
    finally:
        cursor.close()
        conn.close()


@esim_admin_bp.route("/api/admin/esim/provedores/<int:item_id>", methods=["PUT"])
def esim_admin_atualizar_provedor(item_id: int):
    body = request.get_json(silent=True) or {}
    conn = esim_get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        esim_ensure_schema(conn)
        cursor.execute(
            "SELECT id, nome, config_json FROM public.esim_provedores WHERE id = %s;",
            (item_id,),
        )
        atual = cursor.fetchone()
        if not atual:
            return jsonify({"status": "error", "message": "Provedor não encontrado."}), 404

        cfg_atual = atual.get("config_json") or {}
        if isinstance(cfg_atual, str):
            try:
                cfg_atual = json.loads(cfg_atual)
            except (TypeError, json.JSONDecodeError):
                cfg_atual = {}

        merged = {**cfg_atual, **(body.get("config_json") or {})}
        for campo in ("webhook_path", "upload_endpoint", "slug"):
            if campo in body:
                merged[campo] = (body.get(campo) or "").strip()

        payload, erro = _esim_admin_validar_provedor_payload(
            {
                "nome": body.get("nome", atual.get("nome")),
                "config_json": merged,
                "webhook_path": merged.get("webhook_path"),
                "upload_endpoint": merged.get("upload_endpoint"),
                "slug": merged.get("slug"),
            },
            parcial=True,
        )
        if erro:
            return jsonify({"status": "error", "message": erro}), 400

        nome = payload.get("nome", atual.get("nome"))
        cursor.execute(
            """
            UPDATE public.esim_provedores
            SET nome = %s, config_json = %s
            WHERE id = %s
            RETURNING id;
            """,
            (nome, Json(payload["config_json"]), item_id),
        )
        conn.commit()
        return jsonify({"status": "success", "message": "Provedor atualizado."}), 200
    except Exception as exc:
        conn.rollback()
        if "unique" in str(exc).lower():
            return jsonify({"status": "error", "message": "Já existe um provedor com este nome."}), 409
        return jsonify({"status": "error", "message": str(exc)}), 500
    finally:
        cursor.close()
        conn.close()


@esim_admin_bp.route("/api/admin/esim/provedores/<int:item_id>", methods=["DELETE"])
def esim_admin_excluir_provedor(item_id: int):
    conn = esim_get_db_connection()
    cursor = conn.cursor()
    try:
        esim_ensure_schema(conn)
        cursor.execute("DELETE FROM public.esim_provedores WHERE id = %s RETURNING id;", (item_id,))
        if not cursor.fetchone():
            conn.rollback()
            return jsonify({"status": "error", "message": "Provedor não encontrado."}), 404
        conn.commit()
        return jsonify({"status": "success", "message": "Provedor removido."}), 200
    except Exception as exc:
        conn.rollback()
        if "restrict" in str(exc).lower() or "foreign" in str(exc).lower():
            return jsonify({
                "status": "error",
                "message": "Não é possível excluir: existem eventos no catálogo vinculados a este provedor.",
            }), 409
        return jsonify({"status": "error", "message": str(exc)}), 500
    finally:
        cursor.close()
        conn.close()


@esim_admin_bp.route("/api/admin/esim/framework-options", methods=["GET"])
def esim_admin_framework_options():
    """Dimensões e domínios do framework para os formulários admin."""
    conn = esim_get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cursor.execute(
            "SELECT id_dime, name_dime FROM public.leaf_dime ORDER BY name_dime ASC;"
        )
        dimensoes = [dict(r) for r in cursor.fetchall()]
        cursor.execute(
            "SELECT id_doma, name_doma FROM public.leaf_doma ORDER BY name_doma ASC;"
        )
        dominios = [dict(r) for r in cursor.fetchall()]
        return jsonify({"status": "success", "dimensoes": dimensoes, "dominios": dominios}), 200
    except Exception as exc:
        return jsonify({"status": "error", "message": str(exc)}), 500
    finally:
        cursor.close()
        conn.close()


@esim_admin_bp.route("/api/admin/esim/blocos", methods=["GET"])
def esim_admin_buscar_blocos():
    """Busca blocos do framework (leaf_bloc) para seleção de candidatos."""
    termo = (request.args.get("q") or "").strip()
    limite = min(int(request.args.get("limit") or 80), 200)
    conn = esim_get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        if termo:
            like = f"%{termo}%"
            cursor.execute(
                """
                SELECT b.id_bloc, b.name_bloc, b.desc_bloc,
                       d.name_dime, dom.name_doma
                FROM public.leaf_bloc b
                JOIN public.leaf_dime d ON b.id_dime = d.id_dime
                JOIN public.leaf_doma dom ON b.id_doma = dom.id_doma
                WHERE b.name_bloc ILIKE %s OR b.desc_bloc ILIKE %s
                ORDER BY b.name_bloc ASC
                LIMIT %s;
                """,
                (like, like, limite),
            )
        else:
            cursor.execute(
                """
                SELECT b.id_bloc, b.name_bloc, b.desc_bloc,
                       d.name_dime, dom.name_doma
                FROM public.leaf_bloc b
                JOIN public.leaf_dime d ON b.id_dime = d.id_dime
                JOIN public.leaf_doma dom ON b.id_doma = dom.id_doma
                ORDER BY d.name_dime, dom.name_doma, b.name_bloc ASC
                LIMIT %s;
                """,
                (limite,),
            )
        return jsonify({"status": "success", "data": [dict(r) for r in cursor.fetchall()]}), 200
    except Exception as exc:
        return jsonify({"status": "error", "message": str(exc)}), 500
    finally:
        cursor.close()
        conn.close()


def register_esim_admin_routes(flask_app) -> None:
    flask_app.register_blueprint(esim_admin_bp)

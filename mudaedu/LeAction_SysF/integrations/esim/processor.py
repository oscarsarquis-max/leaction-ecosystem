"""Orquestração da esteira eSIM → catálogo DB → IA → backlog → Mesa."""

from __future__ import annotations

import os
from typing import Any

from psycopg2.extras import RealDictCursor

from integrations.esim.catalog import EsimCatalogEntry, esim_buscar_catalogo
from integrations.esim.observability import (
    esim_log_evento_nao_classificado,
    esim_log_webhook_processado,
    esim_log_webhook_recebido,
)
from integrations.esim.repository import (
    esim_atualizar_associacoes_evento,
    esim_ensure_schema,
    esim_extrair_associacoes,
    esim_get_db_connection,
    esim_inserir_backlog_mesa,
    esim_inserir_evento,
    esim_materializar_postit_mesa,
    esim_resolver_id_matu_ativo,
)
from integrations.esim.schemas import (
    ESIM_CLASSIFICACAO_NAO_CLASSIFICADO,
    EsimPayloadError,
    esim_parse_telemetry_payload,
)
from integrations.esim.telemetry_agent import esim_analisar_anomalia_telemetria


def esim_webhook_autorizado(headers: dict[str, str]) -> bool:
    secret = (
        os.environ.get("ESIM_WEBHOOK_SECRET")
        or os.environ.get("BASEMOBILE_WEBHOOK_SECRET")
        or ""
    ).strip()
    if not secret:
        return True
    token = (
        headers.get("X-ESIM-Token")
        or headers.get("X-BaseMobile-Token")
        or headers.get("X-Webhook-Token")
        or headers.get("Authorization", "").replace("Bearer ", "", 1).strip()
    )
    return token == secret


def esim_resolver_catalogo(
    codigo_evento: str,
    cursor,
) -> EsimCatalogEntry | None:
    """Busca metadados do framework em esim_eventos_catalog."""
    return esim_buscar_catalogo(codigo_evento, cursor=cursor)


def esim_processar_evento_nao_classificado(
    cursor,
    payload,
    *,
    conn,
) -> dict[str, Any]:
    """Persiste evento sem catálogo; não aciona IA nem Mesa."""
    id_evento = esim_inserir_evento(
        cursor,
        payload,
        catalog_id=None,
        classificacao_status=ESIM_CLASSIFICACAO_NAO_CLASSIFICADO,
    )
    conn.commit()
    esim_log_evento_nao_classificado(
        id_evento=id_evento,
        codigo_evento=payload.codigo_evento,
        cliente_id=payload.cliente_id,
    )
    return {
        "status": "accepted",
        "classificacao_status": ESIM_CLASSIFICACAO_NAO_CLASSIFICADO,
        "id_evento": id_evento,
        "id_clie": payload.cliente_id,
        "codigo_evento": payload.codigo_evento,
        "codigo_evento_padrao": payload.codigo_evento_padrao,
        "ia_processada": False,
        "message": (
            f"Evento registrado como não classificado — "
            f"código '{payload.codigo_evento}' ausente de esim_eventos_catalog."
        ),
        "http_status": 202,
    }


def esim_processar_webhook(
    body: dict | None,
    headers: dict[str, str] | None = None,
    *,
    skip_auth: bool = False,
) -> dict[str, Any]:
    headers = headers or {}
    if not skip_auth and not esim_webhook_autorizado(headers):
        return {"status": "error", "message": "Token de webhook inválido.", "http_status": 401}

    try:
        payload = esim_parse_telemetry_payload(body)
    except EsimPayloadError as exc:
        return {"status": "error", "message": str(exc), "http_status": 400}

    esim_log_webhook_recebido(
        {
            "cliente_id": payload.cliente_id,
            "codigo_evento": payload.codigo_evento,
            "codigo_evento_padrao": payload.codigo_evento_padrao,
            "status_anomalia": payload.status_anomalia,
            "grupo_acesso": payload.grupo_acesso,
        }
    )

    conn = esim_get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        esim_ensure_schema(conn)

        cursor.execute(
            "SELECT id_clie FROM public.ctdi_clie WHERE id_clie = %s LIMIT 1;",
            (payload.cliente_id,),
        )
        if not cursor.fetchone():
            return {
                "status": "error",
                "message": f"Cliente {payload.cliente_id} não encontrado.",
                "http_status": 404,
            }

        catalog = esim_resolver_catalogo(payload.codigo_evento, cursor)
        if catalog is None:
            return esim_processar_evento_nao_classificado(cursor, payload, conn=conn)

        id_evento = esim_inserir_evento(
            cursor,
            payload,
            catalog_id=catalog.id,
        )
        id_matu = esim_resolver_id_matu_ativo(cursor, payload.cliente_id)
        conn.commit()

        analise_ia = esim_analisar_anomalia_telemetria(
            payload,
            codigo_evento=catalog.codigo_evento,
            dimensao_fixada=catalog.dimensao_fixada,
            dominio_fixado=catalog.dominio_fixado,
            blocos_candidatos_restritos=list(catalog.blocos_candidatos),
            interpretacao_leaction=catalog.descricao_tecnica,
            catalog_id=catalog.id,
        )

        dominio_associado, bloco_associado = esim_extrair_associacoes(analise_ia, catalog)
        esim_atualizar_associacoes_evento(
            cursor,
            id_evento,
            dominio_associado=dominio_associado,
            bloco_associado=bloco_associado,
        )

        id_item = esim_inserir_backlog_mesa(
            cursor,
            id_evento=id_evento,
            id_clie=payload.cliente_id,
            id_matu=id_matu,
            analise_ia=analise_ia,
            catalog=catalog,
        )

        id_nota_mesa = None
        if id_matu is not None:
            id_nota_mesa = esim_materializar_postit_mesa(
                cursor,
                id_clie=payload.cliente_id,
                id_matu=id_matu,
                payload=payload,
                analise_ia=analise_ia,
                id_item_backlog=id_item,
                catalog=catalog,
            )

        conn.commit()

        resultado = {
            "status": "success",
            "classificacao_status": "classificado",
            "id_evento": id_evento,
            "id_clie": payload.cliente_id,
            "id_matu": id_matu,
            "catalog_id": catalog.id,
            "codigo_evento": catalog.codigo_evento,
            "codigo_evento_padrao": catalog.codigo_evento,
            "dimensao_fixada": catalog.dimensao_fixada,
            "dominio_fixado": catalog.dominio_fixado,
            "blocos_candidatos_restritos": list(catalog.blocos_candidatos),
            "bloco_escolhido": analise_ia.get("bloco_escolhido"),
            "dominio_associado": dominio_associado,
            "bloco_associado": bloco_associado,
            "titulo_alerta": payload.titulo_alerta,
            "status_anomalia": payload.status_anomalia,
            "ia_processada": True,
            "id_item_backlog": id_item,
            "id_nota_mesa": id_nota_mesa,
            "hipotese": analise_ia.get("hipotese") or analise_ia.get("hipotese_negocio"),
            "hipotese_negocio": analise_ia.get("hipotese_negocio"),
            "subtasks": analise_ia.get("subtasks") or analise_ia.get("subtasks_investigacao"),
            "subtasks_investigacao": analise_ia.get("subtasks_investigacao"),
            "ia_fallback": bool(analise_ia.get("fallback")),
            "message": "Webhook processado — IA Master acionada com contexto LeAction, backlog e Mesa atualizados.",
            "http_status": 201,
        }
        esim_log_webhook_processado(
            {
                "id_evento": id_evento,
                "id_item_backlog": id_item,
                "catalog_id": catalog.id,
                "codigo_evento": catalog.codigo_evento,
                "bloco_associado": bloco_associado,
                "ia_fallback": bool(analise_ia.get("fallback")),
            }
        )
        return resultado

    except Exception as exc:
        conn.rollback()
        raise exc
    finally:
        cursor.close()
        conn.close()


processar_webhook_basemobile = esim_processar_webhook

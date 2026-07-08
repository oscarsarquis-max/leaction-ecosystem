"""Persistência eSIM — telemetria agnóstica a provedores + Mesa Org."""

from __future__ import annotations

import json
from typing import Any

from psycopg2.extras import Json, RealDictCursor

from integrations.esim.catalog import EsimCatalogEntry
from integrations.esim.schemas import (
    ESIM_CLASSIFICACAO_CLASSIFICADO,
    ESIM_CLASSIFICACAO_NAO_CLASSIFICADO,
    EsimTelemetryPayload,
)

TBL_EVENTOS = "esim_eventos"
TBL_BACKLOG = "esim_mesa_backlog"
TBL_CATALOG = "esim_eventos_catalog"
TBL_PROVEDORES = "esim_provedores"


def esim_get_db_connection():
    from app import DB_CONFIG
    import psycopg2

    return psycopg2.connect(**DB_CONFIG)


def _esim_ensure_column(cur, table: str, column: str, ddl: str) -> None:
    cur.execute(
        """
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = %s
          AND column_name = %s
        LIMIT 1;
        """,
        (table, column),
    )
    if not cur.fetchone():
        cur.execute(f"ALTER TABLE public.{table} ADD COLUMN {ddl};")


def esim_extrair_associacoes(
    analise_ia: dict[str, Any],
    catalog: EsimCatalogEntry | None = None,
) -> tuple[str | None, str | None]:
    """Resolve domínio/bloco CTDI escolhidos pela IA (ou catálogo LeAction)."""
    dominio = (
        (analise_ia.get("dominio_fixado") or "").strip()
        or (catalog.dominio_fixado if catalog else None)
        or None
    )
    bloco = (analise_ia.get("bloco_escolhido") or "").strip() or None
    return dominio, bloco


def esim_ensure_schema(conn) -> None:
    """Garante schema eSIM (dev / primeira execução sem migration explícita)."""
    cur = conn.cursor()
    try:
        cur.execute(
            f"""
            CREATE TABLE IF NOT EXISTS public.{TBL_PROVEDORES} (
                id SERIAL PRIMARY KEY,
                nome VARCHAR(120) NOT NULL UNIQUE,
                config_json JSONB NOT NULL DEFAULT '{{}}'::jsonb,
                criado_em TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
            );
            """
        )
        cur.execute(
            f"""
            CREATE TABLE IF NOT EXISTS public.{TBL_CATALOG} (
                id SERIAL PRIMARY KEY,
                codigo_evento VARCHAR(64) NOT NULL UNIQUE,
                descricao_tecnica TEXT NOT NULL,
                dimensao_fixada VARCHAR(255) NOT NULL,
                dominio_fixado VARCHAR(255) NOT NULL,
                blocos_candidatos JSONB NOT NULL DEFAULT '[]'::jsonb,
                provedor_id INTEGER NOT NULL REFERENCES public.{TBL_PROVEDORES}(id) ON DELETE RESTRICT
            );
            """
        )
        cur.execute(
            f"""
            CREATE TABLE IF NOT EXISTS public.{TBL_EVENTOS} (
                id_evento SERIAL PRIMARY KEY,
                id_clie INTEGER NOT NULL REFERENCES public.ctdi_clie(id_clie) ON DELETE CASCADE,
                catalog_id INTEGER REFERENCES public.{TBL_CATALOG}(id) ON DELETE RESTRICT,
                grupo_acesso VARCHAR(120),
                dominio_acessado VARCHAR(255),
                trafego_mb_7dias NUMERIC(12, 2),
                status_anomalia VARCHAR(64) NOT NULL,
                dominio_associado VARCHAR(255),
                bloco_associado VARCHAR(255),
                classificacao_status VARCHAR(32) NOT NULL DEFAULT 'classificado',
                payload_bruto JSONB,
                recebido_em TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
            );
            """
        )
        cur.execute(
            f"""
            CREATE TABLE IF NOT EXISTS public.{TBL_BACKLOG} (
                id_item SERIAL PRIMARY KEY,
                id_evento INTEGER NOT NULL REFERENCES public.{TBL_EVENTOS}(id_evento) ON DELETE CASCADE,
                id_clie INTEGER NOT NULL REFERENCES public.ctdi_clie(id_clie) ON DELETE CASCADE,
                id_matu INTEGER,
                origem VARCHAR(32) NOT NULL DEFAULT 'telemetria',
                is_alerta BOOLEAN NOT NULL DEFAULT TRUE,
                status VARCHAR(32) NOT NULL DEFAULT 'pendente',
                hipotese_negocio TEXT,
                subtasks JSONB,
                ia_resposta JSONB,
                dominio_associado VARCHAR(255),
                bloco_associado VARCHAR(255),
                id_nota_mesa INTEGER REFERENCES public.inov_agenda_notas(id_nota) ON DELETE SET NULL,
                criado_em TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
                consumido_em TIMESTAMP WITHOUT TIME ZONE
            );
            """
        )
        _esim_ensure_column(
            cur, TBL_EVENTOS, "catalog_id",
            f"catalog_id INTEGER REFERENCES public.{TBL_CATALOG}(id) ON DELETE RESTRICT",
        )
        _esim_ensure_column(cur, TBL_EVENTOS, "dominio_associado", "dominio_associado VARCHAR(255)")
        _esim_ensure_column(cur, TBL_EVENTOS, "bloco_associado", "bloco_associado VARCHAR(255)")
        _esim_ensure_column(
            cur, TBL_EVENTOS, "classificacao_status",
            "classificacao_status VARCHAR(32) NOT NULL DEFAULT 'classificado'",
        )
        _esim_ensure_column(cur, TBL_BACKLOG, "dominio_associado", "dominio_associado VARCHAR(255)")
        _esim_ensure_column(cur, TBL_BACKLOG, "bloco_associado", "bloco_associado VARCHAR(255)")
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()


def esim_resolver_id_matu_ativo(cursor, id_clie: int) -> int | None:
    cursor.execute(
        """
        SELECT id_matu
        FROM public.ctdi_matu
        WHERE id_clie = %s
        ORDER BY id_matu DESC
        LIMIT 1;
        """,
        (id_clie,),
    )
    row = cursor.fetchone()
    return row["id_matu"] if row else None


def esim_inserir_evento(
    cursor,
    payload: EsimTelemetryPayload,
    *,
    catalog_id: int | None = None,
    dominio_associado: str | None = None,
    bloco_associado: str | None = None,
    classificacao_status: str = ESIM_CLASSIFICACAO_CLASSIFICADO,
) -> int:
    cursor.execute(
        f"""
        INSERT INTO public.{TBL_EVENTOS}
            (id_clie, catalog_id, grupo_acesso, dominio_acessado, trafego_mb_7dias, status_anomalia,
             dominio_associado, bloco_associado, classificacao_status, payload_bruto)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id_evento;
        """,
        (
            payload.cliente_id,
            catalog_id,
            payload.grupo_acesso,
            payload.dominio_acessado,
            payload.trafego_mb_7dias,
            payload.status_anomalia,
            dominio_associado,
            bloco_associado,
            classificacao_status,
            Json(payload.raw),
        ),
    )
    return cursor.fetchone()["id_evento"]


def esim_atualizar_associacoes_evento(
    cursor,
    id_evento: int,
    *,
    dominio_associado: str | None,
    bloco_associado: str | None,
) -> None:
    cursor.execute(
        f"""
        UPDATE public.{TBL_EVENTOS}
        SET dominio_associado = COALESCE(%s, dominio_associado),
            bloco_associado = COALESCE(%s, bloco_associado)
        WHERE id_evento = %s;
        """,
        (dominio_associado, bloco_associado, id_evento),
    )


def esim_inserir_backlog_mesa(
    cursor,
    *,
    id_evento: int,
    id_clie: int,
    id_matu: int | None,
    analise_ia: dict[str, Any],
    catalog: EsimCatalogEntry | None = None,
) -> int:
    dominio_associado, bloco_associado = esim_extrair_associacoes(analise_ia, catalog)
    cursor.execute(
        f"""
        INSERT INTO public.{TBL_BACKLOG}
            (id_evento, id_clie, id_matu, origem, is_alerta, status,
             hipotese_negocio, subtasks, ia_resposta,
             dominio_associado, bloco_associado)
        VALUES (%s, %s, %s, 'telemetria', TRUE, 'pendente', %s, %s, %s, %s, %s)
        RETURNING id_item;
        """,
        (
            id_evento,
            id_clie,
            id_matu,
            analise_ia.get("hipotese_negocio"),
            Json(analise_ia.get("subtasks_investigacao") or analise_ia.get("subtasks") or []),
            Json(analise_ia),
            dominio_associado,
            bloco_associado,
        ),
    )
    return cursor.fetchone()["id_item"]


def _esim_mesa_org_rotina_titulo(id_matu: int) -> str:
    return f"Mesa Org · Matu #{id_matu}"


def _esim_get_or_create_rotina_mesa(cursor, id_clie: int, id_matu: int) -> int:
    titulo = _esim_mesa_org_rotina_titulo(id_matu)
    cursor.execute(
        "SELECT id_rotina FROM public.inov_agenda_rotina WHERE id_clie = %s AND titulo_atividade = %s LIMIT 1;",
        (id_clie, titulo),
    )
    row = cursor.fetchone()
    if row:
        return row["id_rotina"]
    cursor.execute(
        "INSERT INTO public.inov_agenda_rotina (id_clie, titulo_atividade) VALUES (%s, %s) RETURNING id_rotina;",
        (id_clie, titulo),
    )
    return cursor.fetchone()["id_rotina"]


def esim_materializar_postit_mesa(
    cursor,
    *,
    id_clie: int,
    id_matu: int,
    payload: EsimTelemetryPayload,
    analise_ia: dict[str, Any],
    id_item_backlog: int,
    catalog: EsimCatalogEntry | None = None,
) -> int:
    """Publica post-it na Mesa Org (inov_agenda_notas) sem acoplar rotas da Mesa."""
    subtasks = analise_ia.get("subtasks_investigacao") or analise_ia.get("subtasks") or []
    dominio_associado, bloco_associado = esim_extrair_associacoes(analise_ia, catalog)
    texto_postit = (
        f"[ALERTA TELEMETRIA · {payload.titulo_alerta}] "
        f"{analise_ia.get('hipotese_negocio', '')}\n\n"
        f"{payload.descricao_evento}\n\n"
        f"Framework LeAction — Domínio: {dominio_associado or '—'} | Bloco: {bloco_associado or '—'}\n\n"
        "Investigação sugerida:\n"
        + "\n".join(f"• {s}" for s in subtasks)
    )

    conteudo_json = json.dumps(
        {
            "v": 1,
            "texto": texto_postit.strip(),
            "contexto": f"🚨 {payload.titulo_alerta}",
            "origem_gap": None,
            "meta": {
                "origem": "telemetria",
                "is_alerta": True,
                "id_item_backlog": id_item_backlog,
                "status_anomalia": payload.status_anomalia,
                "codigo_evento_padrao": payload.codigo_evento_padrao,
                "catalog_id": catalog.id if catalog else analise_ia.get("catalog_id"),
                "dimensao_fixada": analise_ia.get("dimensao_fixada") or (catalog.dimensao_fixada if catalog else None),
                "dominio_associado": dominio_associado,
                "bloco_associado": bloco_associado,
                "hipotese_negocio": analise_ia.get("hipotese_negocio"),
                "subtasks": subtasks,
            },
        },
        ensure_ascii=False,
    )

    id_rotina = _esim_get_or_create_rotina_mesa(cursor, id_clie, id_matu)
    cursor.execute(
        """
        INSERT INTO public.inov_agenda_notas
            (id_clie, id_rotina, conteudo_bruto, tipo_observacao, status_nota)
        VALUES (%s, %s, %s, 'Telemetria_eSIM', 'Pendente')
        RETURNING id_nota;
        """,
        (id_clie, id_rotina, conteudo_json),
    )
    id_nota = cursor.fetchone()["id_nota"]

    cursor.execute(
        f"""
        UPDATE public.{TBL_BACKLOG}
        SET id_nota_mesa = %s
        WHERE id_item = %s;
        """,
        (id_nota, id_item_backlog),
    )
    return id_nota


def esim_listar_backlog_pendente(id_clie: int, id_matu: int | None = None) -> list[dict]:
    conn = esim_get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        esim_ensure_schema(conn)
        if id_matu:
            cursor.execute(
                f"""
                SELECT id_item, id_evento, id_clie, id_matu, origem, is_alerta, status,
                       hipotese_negocio, subtasks, dominio_associado, bloco_associado,
                       ia_resposta, id_nota_mesa, criado_em
                FROM public.{TBL_BACKLOG}
                WHERE id_clie = %s AND id_matu = %s AND status = 'pendente'
                ORDER BY criado_em DESC;
                """,
                (id_clie, id_matu),
            )
        else:
            cursor.execute(
                f"""
                SELECT id_item, id_evento, id_clie, id_matu, origem, is_alerta, status,
                       hipotese_negocio, subtasks, dominio_associado, bloco_associado,
                       ia_resposta, id_nota_mesa, criado_em
                FROM public.{TBL_BACKLOG}
                WHERE id_clie = %s AND status = 'pendente'
                ORDER BY criado_em DESC;
                """,
                (id_clie,),
            )
        return [_esim_enriquecer_item_backlog(dict(r)) for r in cursor.fetchall()]
    finally:
        cursor.close()
        conn.close()


def _esim_enriquecer_item_backlog(row: dict) -> dict:
    item = dict(row)
    ia = item.get("ia_resposta")
    if isinstance(ia, str):
        try:
            ia = json.loads(ia)
        except (TypeError, json.JSONDecodeError):
            ia = {}
    if isinstance(ia, dict):
        item.setdefault("codigo_evento_padrao", ia.get("codigo_evento_padrao"))
        item.setdefault("dimensao_fixada", ia.get("dimensao_fixada"))
        item.setdefault("catalog_id", ia.get("catalog_id"))
    subtasks = item.get("subtasks")
    if isinstance(subtasks, str):
        try:
            item["subtasks"] = json.loads(subtasks)
        except (TypeError, json.JSONDecodeError):
            item["subtasks"] = []
    return item


def esim_marcar_backlog_consumido(
    cursor,
    *,
    id_item: int | None = None,
    id_nota_mesa: int | None = None,
) -> int:
    if id_item is not None:
        cursor.execute(
            f"""
            UPDATE public.{TBL_BACKLOG}
            SET status = 'consumido', consumido_em = NOW()
            WHERE id_item = %s AND status = 'pendente';
            """,
            (id_item,),
        )
        return cursor.rowcount

    if id_nota_mesa is not None:
        cursor.execute(
            f"""
            UPDATE public.{TBL_BACKLOG}
            SET status = 'consumido', consumido_em = NOW()
            WHERE id_nota_mesa = %s AND status = 'pendente';
            """,
            (id_nota_mesa,),
        )
        return cursor.rowcount

    return 0


def esim_marcar_backlog_consumido_por_notas(cursor, ids_notas: list[int]) -> int:
    if not ids_notas:
        return 0
    cursor.execute(
        f"""
        UPDATE public.{TBL_BACKLOG}
        SET status = 'consumido', consumido_em = NOW()
        WHERE id_nota_mesa = ANY(%s) AND status = 'pendente';
        """,
        (ids_notas,),
    )
    return cursor.rowcount


def esim_consumir_backlog_item(id_item: int | None = None, id_nota: int | None = None) -> dict[str, Any]:
    conn = esim_get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        esim_ensure_schema(conn)
        afetados = esim_marcar_backlog_consumido(cursor, id_item=id_item, id_nota_mesa=id_nota)
        conn.commit()
        return {"status": "success", "consumidos": afetados}
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()


# Aliases legados (basemobile)
get_db_connection = esim_get_db_connection
ensure_esim_schema = esim_ensure_schema
ensure_basemobile_schema = esim_ensure_schema
extrair_associacoes_leaction = esim_extrair_associacoes
resolver_id_matu_ativo = esim_resolver_id_matu_ativo
inserir_evento = esim_inserir_evento
atualizar_associacoes_evento = esim_atualizar_associacoes_evento
inserir_backlog_mesa = esim_inserir_backlog_mesa
materializar_postit_mesa = esim_materializar_postit_mesa
listar_backlog_pendente = esim_listar_backlog_pendente
marcar_backlog_consumido = esim_marcar_backlog_consumido
marcar_backlog_consumido_por_notas = esim_marcar_backlog_consumido_por_notas
consumir_backlog_item = esim_consumir_backlog_item

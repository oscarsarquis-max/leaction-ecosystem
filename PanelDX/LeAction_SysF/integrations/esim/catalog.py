"""Catálogo eSIM — consulta exclusiva em esim_eventos_catalog (sem arquivo estático)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from psycopg2.extras import RealDictCursor


@dataclass(frozen=True)
class EsimCatalogEntry:
    id: int
    codigo_evento: str
    descricao_tecnica: str
    dimensao_fixada: str
    dominio_fixado: str
    blocos_candidatos: tuple[str, ...]
    provedor_id: int | None = None

    @property
    def blocos_candidatos_restritos(self) -> tuple[str, ...]:
        return self.blocos_candidatos


def esim_get_db_connection():
    from app import DB_CONFIG
    import psycopg2

    return psycopg2.connect(**DB_CONFIG)


def _esim_row_para_entry(row: dict[str, Any]) -> EsimCatalogEntry:
    blocos = row.get("blocos_candidatos") or []
    if isinstance(blocos, str):
        try:
            blocos = json.loads(blocos)
        except (TypeError, json.JSONDecodeError):
            blocos = []
    return EsimCatalogEntry(
        id=int(row["id"]),
        codigo_evento=str(row.get("codigo_evento") or "").strip().upper(),
        descricao_tecnica=str(row.get("descricao_tecnica") or "").strip(),
        dimensao_fixada=str(row.get("dimensao_fixada") or "").strip(),
        dominio_fixado=str(row.get("dominio_fixado") or "").strip(),
        blocos_candidatos=tuple(str(b) for b in blocos),
        provedor_id=row.get("provedor_id"),
    )


def esim_buscar_catalogo(
    codigo: str,
    *,
    provedor_id: int | None = None,
    cursor=None,
) -> EsimCatalogEntry | None:
    """Busca metadados do framework em esim_eventos_catalog. Retorna None se não existir."""
    chave = (codigo or "").strip().upper()
    if not chave:
        return None

    own_conn = None
    own_cursor = None
    try:
        if cursor is None:
            own_conn = esim_get_db_connection()
            own_cursor = own_conn.cursor(cursor_factory=RealDictCursor)
            cursor = own_cursor

        if provedor_id is not None:
            cursor.execute(
                """
                SELECT id, codigo_evento, descricao_tecnica, dimensao_fixada,
                       dominio_fixado, blocos_candidatos, provedor_id
                FROM public.esim_eventos_catalog
                WHERE UPPER(codigo_evento) = %s AND provedor_id = %s
                LIMIT 1;
                """,
                (chave, provedor_id),
            )
        else:
            cursor.execute(
                """
                SELECT id, codigo_evento, descricao_tecnica, dimensao_fixada,
                       dominio_fixado, blocos_candidatos, provedor_id
                FROM public.esim_eventos_catalog
                WHERE UPPER(codigo_evento) = %s
                LIMIT 1;
                """,
                (chave,),
            )
        row = cursor.fetchone()
        if not row:
            return None
        return _esim_row_para_entry(dict(row))
    finally:
        if own_cursor:
            own_cursor.close()
        if own_conn:
            own_conn.close()


def esim_listar_codigos_catalogo(*, provedor_id: int | None = None) -> list[str]:
    conn = esim_get_db_connection()
    cursor = conn.cursor()
    try:
        if provedor_id is not None:
            cursor.execute(
                """
                SELECT codigo_evento
                FROM public.esim_eventos_catalog
                WHERE provedor_id = %s
                ORDER BY codigo_evento;
                """,
                (provedor_id,),
            )
        else:
            cursor.execute(
                """
                SELECT codigo_evento
                FROM public.esim_eventos_catalog
                ORDER BY codigo_evento;
                """
            )
        return [str(r[0]) for r in cursor.fetchall()]
    finally:
        cursor.close()
        conn.close()

"""Motor de add-ons de licenças — pacotes extras vinculados ao contrato base."""

from __future__ import annotations

from typing import Any

from services.seat_limits import (
    DEFAULT_MAX_USUARIOS_SEM_CONTRATO,
    _CONTRATO_VIGENTE_ORDER,
    _row_val,
)

ADDON_STATUSES = frozenset({"ativo", "cancelado"})
PLANO_TIPOS = frozenset({"base", "addon"})


def obter_contrato_vigente_row(cursor, id_clie: int) -> dict | None:
    cursor.execute(
        f"""
        SELECT c.id AS id_contrato,
               c.id_clie,
               c.id_plano,
               c.status,
               p.nome AS nome_plano,
               COALESCE(p.max_usuarios, %s) AS max_usuarios
        FROM public.dx_contratos c
        JOIN public.dx_planos p ON p.id = c.id_plano
        WHERE c.id_clie = %s
        {_CONTRATO_VIGENTE_ORDER};
        """,
        (DEFAULT_MAX_USUARIOS_SEM_CONTRATO, int(id_clie)),
    )
    row = cursor.fetchone()
    if not row:
        return None
    if isinstance(row, dict):
        return dict(row)
    return {
        "id_contrato": row[0],
        "id_clie": row[1],
        "id_plano": row[2],
        "status": row[3],
        "nome_plano": row[4],
        "max_usuarios": int(row[5]),
    }


def somar_usuarios_addons_ativos(cursor, id_contrato: int) -> int:
    cursor.execute(
        """
        SELECT COALESCE(
            SUM(COALESCE(p.max_usuarios, 0) * COALESCE(a.quantidade, 1)),
            0
        )::int AS total
        FROM public.dx_contratos_addons a
        JOIN public.dx_planos p ON p.id = a.id_plano_addon
        WHERE a.id_contrato = %s
          AND a.status = 'ativo';
        """,
        (int(id_contrato),),
    )
    row = cursor.fetchone()
    return int(_row_val(row, "total", 0) or 0)


def somar_mrr_addons_ativos(cursor) -> float:
    cursor.execute(
        """
        SELECT COALESCE(
            SUM(COALESCE(p.valor_mensal, 0) * COALESCE(a.quantidade, 1)),
            0
        )::numeric AS mrr_addons
        FROM public.dx_contratos_addons a
        JOIN public.dx_planos p ON p.id = a.id_plano_addon
        JOIN public.dx_contratos c ON c.id = a.id_contrato
        WHERE a.status = 'ativo'
          AND c.status = 'ativo';
        """
    )
    row = cursor.fetchone()
    val = _row_val(row, "mrr_addons", 0)
    return float(val or 0)


def obter_addon_padrao(cursor) -> dict | None:
    cursor.execute(
        """
        SELECT id, nome, valor_mensal, periodicidade, max_usuarios, tipo_plano, ativo
        FROM public.dx_planos
        WHERE tipo_plano = 'addon'
          AND ativo = TRUE
        ORDER BY valor_mensal ASC, id ASC
        LIMIT 1;
        """
    )
    row = cursor.fetchone()
    if not row:
        return None
    if isinstance(row, dict):
        return dict(row)
    return {
        "id": row[0],
        "nome": row[1],
        "valor_mensal": float(row[2]),
        "periodicidade": row[3],
        "max_usuarios": int(row[4]),
        "tipo_plano": row[5],
        "ativo": row[6],
    }


def obter_plano_addon(cursor, id_plano_addon: int) -> dict | None:
    cursor.execute(
        """
        SELECT id, nome, valor_mensal, periodicidade, max_usuarios, tipo_plano, ativo,
               descricao_beneficios
        FROM public.dx_planos
        WHERE id = %s AND tipo_plano = 'addon';
        """,
        (int(id_plano_addon),),
    )
    row = cursor.fetchone()
    if not row:
        return None
    if isinstance(row, dict):
        return dict(row)
    return {
        "id": row[0],
        "nome": row[1],
        "valor_mensal": float(row[2]),
        "periodicidade": row[3],
        "max_usuarios": int(row[4]),
        "tipo_plano": row[5],
        "ativo": bool(row[6]),
        "descricao_beneficios": row[7],
    }


def listar_addons_contrato(cursor, id_contrato: int) -> list[dict[str, Any]]:
    cursor.execute(
        """
        SELECT a.id, a.id_contrato, a.id_plano_addon, a.quantidade, a.status,
               a.hub_order_id, a.criado_em, a.atualizado_em,
               p.nome AS nome_addon,
               p.max_usuarios,
               p.valor_mensal
        FROM public.dx_contratos_addons a
        JOIN public.dx_planos p ON p.id = a.id_plano_addon
        WHERE a.id_contrato = %s
        ORDER BY a.status ASC, a.criado_em DESC, a.id DESC;
        """,
        (int(id_contrato),),
    )
    rows = cursor.fetchall()
    result = []
    for row in rows:
        if isinstance(row, dict):
            item = dict(row)
        else:
            item = {
                "id": row[0],
                "id_contrato": row[1],
                "id_plano_addon": row[2],
                "quantidade": row[3],
                "status": row[4],
                "hub_order_id": row[5],
                "criado_em": row[6],
                "atualizado_em": row[7],
                "nome_addon": row[8],
                "max_usuarios": row[9],
                "valor_mensal": float(row[10]),
            }
        item["usuarios_extra"] = int(item.get("max_usuarios") or 0) * int(item.get("quantidade") or 1)
        item["mrr_linha"] = float(item.get("valor_mensal") or 0) * int(item.get("quantidade") or 1)
        if item.get("criado_em") and hasattr(item["criado_em"], "isoformat"):
            item["criado_em"] = item["criado_em"].isoformat()
        if item.get("atualizado_em") and hasattr(item["atualizado_em"], "isoformat"):
            item["atualizado_em"] = item["atualizado_em"].isoformat()
        result.append(item)
    return result


def ativar_addon_contrato(
    cursor,
    *,
    id_clie: int,
    id_plano_addon: int,
    quantidade: int = 1,
    hub_order_id: str | None = None,
) -> dict[str, Any]:
    contrato = obter_contrato_vigente_row(cursor, int(id_clie))
    if not contrato:
        raise ValueError("Cliente sem contrato vigente para vincular o add-on.")

    plano = obter_plano_addon(cursor, int(id_plano_addon))
    if not plano or not plano.get("ativo"):
        raise ValueError("Pacote add-on inválido ou inativo.")

    qty = max(1, int(quantidade))
    order_key = (hub_order_id or "").strip() or None

    if order_key:
        cursor.execute(
            """
            SELECT id, id_contrato, id_plano_addon, quantidade, status
            FROM public.dx_contratos_addons
            WHERE hub_order_id = %s
            LIMIT 1;
            """,
            (order_key,),
        )
        existente = cursor.fetchone()
        if existente:
            if isinstance(existente, dict):
                return {
                    "id": existente["id"],
                    "status": "already_active",
                    "id_contrato": existente["id_contrato"],
                }
            return {
                "id": existente[0],
                "status": "already_active",
                "id_contrato": existente[1],
            }

    cursor.execute(
        """
        INSERT INTO public.dx_contratos_addons
            (id_contrato, id_plano_addon, quantidade, status, hub_order_id)
        VALUES (%s, %s, %s, 'ativo', %s)
        RETURNING id, id_contrato, id_plano_addon, quantidade, status, hub_order_id;
        """,
        (int(contrato["id_contrato"]), int(id_plano_addon), qty, order_key),
    )
    row = cursor.fetchone()
    if isinstance(row, dict):
        return {"status": "activated", **row}
    return {
        "status": "activated",
        "id": row[0],
        "id_contrato": row[1],
        "id_plano_addon": row[2],
        "quantidade": row[3],
        "addon_status": row[4],
        "hub_order_id": row[5],
    }


def cancelar_addon_contrato(cursor, addon_id: int) -> bool:
    cursor.execute(
        """
        UPDATE public.dx_contratos_addons
        SET status = 'cancelado', atualizado_em = NOW()
        WHERE id = %s AND status = 'ativo'
        RETURNING id;
        """,
        (int(addon_id),),
    )
    return bool(cursor.fetchone())

"""Filtros de escopo por papel RBAC."""

from __future__ import annotations

from rbac.constants import ROLE_CONSULTOR, ROLE_EXECUTOR, ROLE_LED, ROLE_SYSADMIN
from rbac.consultor_scope import sql_cliente_na_carteira_consultor
from rbac.context import RbacContext


def rbac_filtro_atividades_sql(ctx: RbacContext, *, alias: str = "a") -> tuple[str, list]:
    """Retorna cláusula WHERE extra e parâmetros para ctdi_okr_atividades."""
    if ctx.system_role == ROLE_SYSADMIN:
        return "", []

    if ctx.system_role == ROLE_EXECUTOR and ctx.id_member:
        return f" AND {alias}.executor_id = %s", [ctx.id_member]

    if ctx.system_role == ROLE_CONSULTOR and ctx.id_usuario:
        cliente_scope = sql_cliente_na_carteira_consultor(clie_column="p.id_clie")
        return (
            f"""
            AND EXISTS (
                SELECT 1
                FROM public.ctdi_sprn s
                JOIN public.ctdi_squads sq ON sq.id_squad = s.id_squad
                JOIN public.ctdi_projetos p ON p.id_proj = sq.id_proj
                WHERE s.id_sprn = {alias}.id_sprn
                  AND {cliente_scope}
            )
            """,
            [ctx.id_usuario],
        )

    if ctx.system_role == ROLE_LED and ctx.id_clie:
        return (
            f"""
            AND EXISTS (
                SELECT 1
                FROM public.ctdi_sprn s
                JOIN public.ctdi_squads sq ON sq.id_squad = s.id_squad
                JOIN public.ctdi_projetos p ON p.id_proj = sq.id_proj
                WHERE s.id_sprn = {alias}.id_sprn AND p.id_clie = %s
            )
            """,
            [ctx.id_clie],
        )

    return " AND 1=0", []


def rbac_filtro_sprints_sql(ctx: RbacContext, *, alias_sprn: str = "s") -> tuple[str, list]:
    if ctx.system_role == ROLE_SYSADMIN:
        return "", []

    if ctx.system_role == ROLE_EXECUTOR and ctx.id_squad:
        return f" AND {alias_sprn}.id_squad = %s", [ctx.id_squad]

    if ctx.system_role == ROLE_CONSULTOR and ctx.id_usuario:
        cliente_scope = sql_cliente_na_carteira_consultor(clie_column="p.id_clie")
        return (
            f"""
            AND EXISTS (
                SELECT 1
                FROM public.ctdi_squads sq
                JOIN public.ctdi_projetos p ON p.id_proj = sq.id_proj
                WHERE sq.id_squad = {alias_sprn}.id_squad
                  AND {cliente_scope}
            )
            """,
            [ctx.id_usuario],
        )

    if ctx.system_role == ROLE_LED and ctx.id_clie:
        return (
            f"""
            AND EXISTS (
                SELECT 1 FROM public.ctdi_squads sq
                JOIN public.ctdi_projetos p ON p.id_proj = sq.id_proj
                WHERE sq.id_squad = {alias_sprn}.id_squad AND p.id_clie = %s
            )
            """,
            [ctx.id_clie],
        )

    return " AND 1=0", []

"""Validação de capacidade — máximo de squads por membro."""

from __future__ import annotations

import sys

from rbac.constants import MAX_SQUADS_POR_MEMBRO

CAPACIDADE_MSG_PADRAO = (
    "Capacidade máxima atingida: Este membro já atua em 3 squads."
)


def rbac_contar_squads_ativas(cursor, *, email: str, id_squad_nova: int | None = None) -> int:
    """Conta squads distintas em que o e-mail está ativo."""
    cursor.execute(
        """
        SELECT COUNT(DISTINCT id_squad) AS total
        FROM public.ctdi_team
        WHERE LOWER(TRIM(email)) = LOWER(TRIM(%s))
          AND ativo = true
          AND id_squad IS NOT NULL;
        """,
        (email,),
    )
    row = cursor.fetchone()
    total = int(row[0] if not isinstance(row, dict) else row.get("total") or 0)

    if id_squad_nova is not None:
        cursor.execute(
            """
            SELECT 1
            FROM public.ctdi_team
            WHERE LOWER(TRIM(email)) = LOWER(TRIM(%s))
              AND ativo = true
              AND id_squad = %s
            LIMIT 1;
            """,
            (email, id_squad_nova),
        )
        if not cursor.fetchone():
            total += 1

    return total


def rbac_validar_capacidade_squad(
    cursor,
    *,
    email: str,
    id_squad: int | None,
    id_member_excluir: int | None = None,
) -> dict:
    """
    Valida limite de squads. Se excedido, retorna bloqueado=True (HTTP 409 no POST).
    """
    if not email or not id_squad:
        return {
            "bloqueado": False,
            "alerta_capacidade": False,
            "squads_ativas": 0,
            "limite_squads": MAX_SQUADS_POR_MEMBRO,
        }

    if id_member_excluir:
        cursor.execute(
            """
            SELECT id_squad FROM public.ctdi_team
            WHERE id_member = %s AND ativo = true LIMIT 1;
            """,
            (id_member_excluir,),
        )
        row = cursor.fetchone()
        squad_atual = row[0] if row and not isinstance(row, dict) else (row.get("id_squad") if row else None)
        if squad_atual == id_squad:
            return {
                "bloqueado": False,
                "alerta_capacidade": False,
                "squads_ativas": rbac_contar_squads_ativas(cursor, email=email),
                "limite_squads": MAX_SQUADS_POR_MEMBRO,
            }

    total = rbac_contar_squads_ativas(cursor, email=email, id_squad_nova=id_squad)
    bloqueado = total > MAX_SQUADS_POR_MEMBRO
    alerta = total >= MAX_SQUADS_POR_MEMBRO

    if bloqueado:
        print(
            f"🚫 [RBAC Capacidade] {email} bloqueado — {total} squads (limite {MAX_SQUADS_POR_MEMBRO})",
            file=sys.stderr,
        )

    return {
        "bloqueado": bloqueado,
        "alerta_capacidade": alerta,
        "squads_ativas": total,
        "limite_squads": MAX_SQUADS_POR_MEMBRO,
        "error": CAPACIDADE_MSG_PADRAO if bloqueado else None,
        "mensagem": CAPACIDADE_MSG_PADRAO if bloqueado else None,
    }

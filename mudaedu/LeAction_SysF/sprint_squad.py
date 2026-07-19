"""Criação de Squads vazias vinculadas a Sprints (Regra 4 — governança LeAction)."""

from __future__ import annotations

from typing import Any


def format_nome_squad(nome_sprint: str, id_sprn: int | None = None) -> str:
    base = (nome_sprint or "Sprint").strip()
    if not base:
        base = "Sprint"
    if id_sprn:
        return f"Squad - {base} (#{id_sprn})"[:250]
    return f"Squad - {base}"[:250]


def _row_val(row: Any, key: str = "id"):
    if row is None:
        return None
    if isinstance(row, dict):
        return row.get(key)
    return row[0]


def resolver_ou_criar_projeto_cliente(cursor, id_clie: int) -> int:
    """Garante projeto ATIVO do cliente para vincular squads."""
    cursor.execute(
        "SELECT id_proj FROM public.ctdi_projetos WHERE id_clie = %s ORDER BY id_proj DESC LIMIT 1;",
        (id_clie,),
    )
    row = cursor.fetchone()
    if row:
        return int(_row_val(row, "id_proj"))

    cursor.execute(
        """
        INSERT INTO public.ctdi_projetos (id_clie, status, fase_atual)
        VALUES (%s, 'ATIVO', 'Squad auto — aguardando gestor')
        RETURNING id_proj;
        """,
        (id_clie,),
    )
    return int(_row_val(cursor.fetchone(), "id_proj"))


def resolver_ou_criar_projeto_ctdi(cursor, id_ctdi: int) -> int:
    """Resolve id_proj a partir do ciclo CTDI (Gênese IA Master)."""
    cursor.execute(
        """
        SELECT m.id_clie
        FROM public.ctdi_main cm
        JOIN public.ctdi_matu m ON m.id_matu = cm.id_matu
        WHERE cm.id_ctdi = %s
        LIMIT 1;
        """,
        (id_ctdi,),
    )
    row = cursor.fetchone()
    if not row:
        raise ValueError(f"Ciclo CTDI #{id_ctdi} não encontrado.")

    id_clie = int(_row_val(row, "id_clie"))
    cursor.execute(
        "SELECT id_proj FROM public.ctdi_projetos WHERE id_clie = %s LIMIT 1;",
        (id_clie,),
    )
    proj = cursor.fetchone()
    if proj:
        id_proj = int(_row_val(proj, "id_proj"))
        cursor.execute(
            "UPDATE public.ctdi_projetos SET id_ctdi = %s WHERE id_proj = %s AND id_ctdi IS NULL;",
            (id_ctdi, id_proj),
        )
        return id_proj

    cursor.execute(
        """
        INSERT INTO public.ctdi_projetos (id_clie, id_ctdi, status, fase_atual)
        VALUES (%s, %s, 'ATIVO', 'Plano Estratégico — Gênese')
        RETURNING id_proj;
        """,
        (id_clie, id_ctdi),
    )
    return int(_row_val(cursor.fetchone(), "id_proj"))


def criar_squad_vazia_para_sprint(
    cursor,
    *,
    id_proj: int,
    nome_sprint: str,
    id_sprn: int | None = None,
) -> int:
    """
    Cria registro em ctdi_squads sem membros em ctdi_team (casca vazia).
    A alocação de pessoas é exclusiva do Gestor em Gestão de Time.
    """
    nome = format_nome_squad(nome_sprint, id_sprn)
    cursor.execute(
        """
        INSERT INTO public.ctdi_squads (nome_squad, id_proj)
        VALUES (%s, %s)
        RETURNING id_squad;
        """,
        (nome, id_proj),
    )
    return int(_row_val(cursor.fetchone(), "id_squad"))


def atualizar_nome_squad_pos_sprint(cursor, id_squad: int, nome_sprint: str, id_sprn: int) -> None:
    cursor.execute(
        "UPDATE public.ctdi_squads SET nome_squad = %s WHERE id_squad = %s;",
        (format_nome_squad(nome_sprint, id_sprn), id_squad),
    )

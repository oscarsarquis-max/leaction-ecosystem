"""Escopo de carteira do consultor via dx_contratos (substitui consultor_associacoes)."""

from __future__ import annotations


def sql_cliente_na_carteira_consultor(*, clie_column: str) -> str:
    """
    Fragmento EXISTS: cliente vinculado ao consultor logado por id_consultor_origem/tecnico.
    Agências incluem contratos dos consultores filhos (id_agencia_pai).
    Parâmetro único: paneldx_usuarios.id_usuario do consultor.
    """
    return f"""
    EXISTS (
        SELECT 1
        FROM public.dx_contratos ct
        INNER JOIN public.dx_consultores dc
            ON dc.user_id = %s AND dc.ativo = TRUE
        WHERE ct.id_clie = {clie_column}
          AND ct.status IN ('ativo', 'trial', 'inadimplente')
          AND (
            ct.id_consultor_origem = dc.id
            OR ct.id_consultor_tecnico = dc.id
            OR (
              dc.tipo = 'agencia'
              AND (
                ct.id_consultor_origem IN (
                    SELECT m.id FROM public.dx_consultores m
                    WHERE m.id_agencia_pai = dc.id AND m.ativo = TRUE
                )
                OR ct.id_consultor_tecnico IN (
                    SELECT m.id FROM public.dx_consultores m
                    WHERE m.id_agencia_pai = dc.id AND m.ativo = TRUE
                )
              )
            )
          )
    )
    """

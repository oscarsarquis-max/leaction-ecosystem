"""Chave de aula na curadoria — uma entrada por evento B2C, não por desafio.

O plano espelhado continua chaveado em origem_plano_b2c_id (= desafio_id na
cadeia). A fila da Central é por item: cada aula que envia sugestão gera
(ou atualiza) a própria pendente, identificada por id_evento.
"""
from __future__ import annotations

from typing import Any


def aula_key_do_sync(payload: dict[str, Any] | None, mesa: dict[str, Any] | None) -> str:
    """Identificador estável da aula/evento B2C no LESSON_RECORD_SYNC."""
    body = payload if isinstance(payload, dict) else {}
    desk = mesa if isinstance(mesa, dict) else {}
    nested = desk.get("evento") if isinstance(desk.get("evento"), dict) else {}
    for src in (
        body.get("origem_aula_b2c_id"),
        body.get("id_evento"),
        desk.get("origem_aula_b2c_id"),
        desk.get("id"),
        desk.get("id_evento"),
        nested.get("id_evento"),
        nested.get("id"),
    ):
        val = str(src or "").strip()
        if val:
            return val
    return ""


def sql_match_pendente_da_aula() -> str:
    """SQL fragment: pending row of the same aula inside one plano espelhado."""
    return """
        SELECT id FROM public.school_curadoria_metodologias
        WHERE plano_espelhado_id = %s
          AND status_analise = 'pendente'
          AND (
            COALESCE(sugestao_professor_json->>'origem_aula_b2c_id', '') = %s
            OR COALESCE(sugestao_professor_json->>'id_evento', '') = %s
            OR COALESCE(sugestao_professor_json->'mesa'->>'id', '') = %s
          )
        ORDER BY updated_at DESC
        LIMIT 1
    """

"""Agregado de contribuição metodológica — só escola/turma, nunca professor.

Mesma fonte do B2C: carimbo origem_card/editado e mesa.contribuicao
no LESSON_RECORD_SYNC. Sem faixa, sem ranking.
"""

from __future__ import annotations

from typing import Any

ORIGEM_CATALOGO = "catalogo"
ORIGEM_CUSTOM = "custom"

STATUS_INCORPORADO = frozenset({"incorporado", "incorporada"})
RESULTADOS_INCORPORADOS = frozenset({"aprovada", "adaptada"})


def _eh_subcard_pei(card: dict[str, Any]) -> bool:
    return bool(card.get("parent_card_id") or card.get("perfil_inclusao"))


def classificar_card(card: Any) -> str | None:
    if not isinstance(card, dict) or _eh_subcard_pei(card):
        return None
    origem = str(card.get("origem_card") or "").strip().lower()
    if origem not in (ORIGEM_CATALOGO, ORIGEM_CUSTOM):
        return None
    if origem == ORIGEM_CUSTOM:
        return "personalizado"
    if card.get("editado") is True:
        return "personalizado"
    if str(card.get("editado") or "").strip().lower() in {"true", "1", "sim"}:
        return "personalizado"
    return "canonico"


def classificar_aula(mesa: Any) -> str | None:
    """canonica | personalizada | None (sem carimbo — não usa proxy)."""
    if not isinstance(mesa, dict):
        return None
    bloco = mesa.get("contribuicao")
    if isinstance(bloco, dict) and bloco.get("tem_carimbos"):
        if bloco.get("aula_personalizada"):
            return "personalizada"
        return "canonica"
    cards = mesa.get("cards") or mesa.get("kanban_cards") or []
    if not isinstance(cards, list):
        return None
    viu = False
    personalizada = False
    for c in cards:
        kind = classificar_card(c)
        if kind is None:
            continue
        viu = True
        if kind == "personalizado":
            personalizada = True
    if not viu:
        return None
    return "personalizada" if personalizada else "canonica"


def agregar_aulas(mesas: list[Any]) -> dict[str, Any]:
    canonicas = 0
    personalizadas = 0
    for mesa in mesas or []:
        kind = classificar_aula(mesa)
        if kind == "canonica":
            canonicas += 1
        elif kind == "personalizada":
            personalizadas += 1
    com_carimbo = canonicas + personalizadas
    pct_canonica = round(100 * canonicas / com_carimbo) if com_carimbo else None
    pct_personalizada = (
        round(100 * personalizadas / com_carimbo) if com_carimbo else None
    )
    return {
        "aulas_com_carimbo": com_carimbo,
        "aulas_canonica": canonicas,
        "aulas_personalizada": personalizadas,
        "percentual_roteiro_base": pct_canonica,
        "percentual_personalizacao": pct_personalizada,
    }


def curadoria_foi_incorporada(row: Any) -> bool:
    if not isinstance(row, dict):
        return False
    status = str(row.get("status_analise") or "").strip().lower()
    if status not in STATUS_INCORPORADO:
        return False
    resultado = str(row.get("resultado_analise") or "").strip().lower()
    if not resultado:
        return True
    return resultado in RESULTADOS_INCORPORADOS


def montar_bloco_radar(
    *,
    mesas: list[Any],
    sugestoes_incorporadas: int,
) -> dict[str, Any]:
    agg = agregar_aulas(mesas)
    return {
        **agg,
        "sugestoes_incorporadas": int(sugestoes_incorporadas or 0),
    }

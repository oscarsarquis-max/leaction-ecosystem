"""Consulta livre é uma resposta. Refinar a mesma recomendação pede crédito, sem debitar."""

from __future__ import annotations

import re

from app.domain.accompaniment_context import (
    _asks_table,
    _fold,
    _is_guide_score_turn,
    _is_support_turn,
    infer_categories_from_text,
    infer_dishes_from_text,
)
from app.domain.gigio.intent import _complaint, _short_social

FREE_ONCE = (
    "Consulta livre: responda uma vez, de forma completa, com o que a pessoa já disse e com as "
    "fichas realmente disponíveis. Se faltar preparo, orçamento ou preferência, declare a condição "
    "assumida. Não pergunte orçamento, preparo, nem convide a refinar de graça. "
    "Não use ponto de interrogação. Cada item de lista fica em uma linha iniciada por hífen."
)

DEEPEN_OFFER_REPLY = (
    "A resposta anterior já fecha esta consulta livre com o que está disponível. "
    "Continuar a mesma recomendação — preparo, preferência, ocasião ou orçamento — é o aprofundamento. "
    "Cada envio nesse modo usa 1 crédito de IA. Nada foi debitado agora."
)

REFINE_MARKERS = (
    "prefiro",
    "e se",
    "mais leve",
    "mais encorpado",
    "orcamento",
    "faixa",
    "e um brasileiro",
    "e uma brasileira",
    "refine",
    "refinar",
    "aprofund",
    "detalha",
    "detalhe",
    "e para beber",
    "e as bebidas",
    "so tinto",
    "sem alcool",
    "quero que voce",
    "pode elaborar",
)

FREE_INVITES = (
    "qual seu orcamento",
    "qual o seu orcamento",
    "como vai preparar",
    "como voce vai preparar",
    "quer que eu refine",
    "quer que eu aprofunde",
    "posso refinar",
    "qual o preparo",
    "quer que eu",
    "me contar",
    "me diga",
    "me fala",
    "posso afinar",
    "posso ajustar",
    "posso detalhar",
    "se quiser me",
    "se quiser",
    "posso sugerir",
)


def is_culinary_refinement(user_text: str, history: list[dict] | None) -> bool:
    prior = [item for item in (history or [])[:-1] if item.get("role") == "user"]
    if not prior:
        return False
    if _is_support_turn(user_text) or _is_guide_score_turn(user_text) or _complaint(user_text) or _short_social(user_text):
        return False
    folded = _fold(user_text, limit=2000)
    if any(token in folded for token in ("vitrine", "fusca", "meu pedido", "pix")):
        return False
    prior_blob = " ".join(str(item.get("content") or "") for item in prior)
    new_dish = set(infer_dishes_from_text(user_text)) - set(infer_dishes_from_text(prior_blob))
    full_question = folded.startswith(("qual ", "quais ", "que ", "como ")) or " que " in f" {folded} "
    if new_dish and full_question and "e se" not in folded and "prefiro" not in folded:
        return False
    prior_culinary = any(
        infer_dishes_from_text(str(item.get("content") or ""))
        or infer_categories_from_text(str(item.get("content") or ""))
        or _asks_table(str(item.get("content") or ""))
        or _is_guide_score_turn(str(item.get("content") or ""))
        for item in prior
    )
    if not prior_culinary:
        return False
    return any(token in folded for token in REFINE_MARKERS)


def drop_phantom_click(reply: str, *, has_cta: bool) -> str:
    if has_cta:
        return reply
    parts = re.split(r"(?<=[.!])\s+", reply.strip())
    kept = [
        part
        for part in parts
        if not ("abaixo" in _fold(part, limit=500) and "clic" in _fold(part, limit=500))
    ]
    cleaned = " ".join(kept).strip()
    return cleaned or reply


def free_reply_invites_refinement(reply: str) -> bool:
    folded = _fold(reply, limit=4000)
    if any(token in folded for token in FREE_INVITES):
        return True
    return folded.rstrip().endswith("?")


def deepen_offer() -> dict:
    return {
        "reply": DEEPEN_OFFER_REPLY,
        "links": [],
        "cta": None,
        "builder_cta": None,
        "sources": [],
        "suggestions": [],
        "notice": "Aprofundar com o Gigio · Usar 1 crédito de IA",
        "access": {
            "authorized": True,
            "deepen_offer": True,
            "needs_confirm": True,
            "charged": False,
            "cost_label": "Usar 1 crédito de IA",
            "action_label": "Aprofundar com o Gigio",
        },
        "unavailable": False,
    }

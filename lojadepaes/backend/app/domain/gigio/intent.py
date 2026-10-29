"""Intenção do turno atual para CTA e ferramentas comerciais.

A mensagem atual decide. O histórico só continua uma refeição real.
Não usa a resposta do modelo como prova de intenção nem uma lista de assuntos proibidos.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.domain.accompaniment_context import (
    infer_categories_from_text,
    infer_dishes_from_text,
    _asks_table,
    _fold,
    _is_guide_score_turn,
    _is_support_turn,
)

SOCIAL = (
    "obrigado",
    "obrigada",
    "valeu",
    "thanks",
    "agradec",
    "grato",
    "grata",
)
ASSISTANT_META = (
    "quem e voce",
    "quem é você",
    "o que voce e",
    "voce e o gigio",
    "você é o gigio",
    "voce e um robo",
    "é um assistente",
    "e um assistente",
)
GREETING = ("oi", "ola", "olá", "bom dia", "boa tarde", "boa noite", "e ai", "e aí")
COMPLAINT = ("reclam", "veio errado", "nao gostei", "não gostei", "problema com o pedido", "faltou")
RESUME_TABLE = (
    "voltando",
    "voltar ao",
    "voltar pro",
    "voltar para",
    "retomar",
    "retoma",
    "mostre os acompanhamentos",
    "mostra os acompanhamentos",
    "mostrar os acompanhamentos",
    "quero os acompanhamentos",
)
CONTINUE_TABLE = (
    "prefiro",
    "prefira",
    "somente",
    "apenas",
    "so queijo",
    "só queijo",
    "so vinho",
    "só vinho",
    "so as bebidas",
    "só as bebidas",
    "sem alcool",
    "sem álcool",
    "sem vinho",
    "sem cerveja",
    "sem queijo",
    "e para beber",
    "para beber",
    "e beber",
    "e as batatas",
    "e a batata",
)
BUILDER_ASK = (
    "montar esse pao",
    "montar esse pão",
    "montar o pao",
    "montar o pão",
    "aplicar sugestao",
    "aplicar sugestão",
    "criador de paes",
    "criador de pães",
    "no criador",
    "proposta",
)
BUILDER_CONTINUE = (
    "e se for",
    "troca a farinha",
    "trocar a farinha",
    "outra farinha",
    "outro formato",
    "muda o formato",
    "sem nozes",
    "com nozes",
    "integral",
)


@dataclass(frozen=True)
class TurnDecision:
    kind: str
    accompaniments: bool
    builder: bool


def _current_fold(text: str) -> str:
    return _fold(text, limit=2000)


def _short_social(text: str) -> bool:
    folded = _current_fold(text)
    if len(folded.split()) > 8:
        return False
    if _asks_table(text) or infer_categories_from_text(text) or infer_dishes_from_text(text):
        return False
    if any(token in folded for token in SOCIAL + ASSISTANT_META):
        return True
    stripped = folded.strip(" !.?,")
    return stripped in GREETING


def _complaint(text: str) -> bool:
    folded = _current_fold(text)
    if _asks_table(text) or infer_categories_from_text(text):
        return False
    return any(token in folded for token in COMPLAINT)


def _builder_ask(text: str) -> bool:
    folded = _current_fold(text)
    if any(token in folded for token in BUILDER_ASK):
        return True
    if "farinha" in folded or "formato" in folded or "fermentacao" in folded or "fermentação" in folded:
        return "pao" in folded or "pão" in folded or "massa" in folded or "montar" in folded
    return False


def _history_had_table(history: list[dict] | None) -> bool:
    for item in history or []:
        if item.get("role") != "user":
            continue
        content = str(item.get("content") or "")
        if (
            _asks_table(content)
            or infer_dishes_from_text(content)
            or infer_categories_from_text(content)
        ):
            return True
    return False


def _history_had_builder(history: list[dict] | None) -> bool:
    for item in history or []:
        content = str(item.get("content") or "")
        if _builder_ask(content):
            return True
        if item.get("role") == "user" and any(
            token in _current_fold(content) for token in ("sanduiche", "sanduíche", "pão de forma", "pao de forma")
        ):
            return True
    return False


def _table_continuation(text: str, history: list[dict] | None) -> bool:
    if not _history_had_table(history):
        return False
    folded = _current_fold(text)
    if any(token in folded for token in RESUME_TABLE + CONTINUE_TABLE):
        return True
    if infer_categories_from_text(text) and len(folded.split()) <= 10:
        return True
    return False


def decide_turn(user_text: str, history: list[dict] | None = None) -> TurnDecision:
    if _is_support_turn(user_text) or _is_guide_score_turn(user_text):
        return TurnDecision("support", False, False)
    if _complaint(user_text):
        return TurnDecision("complaint", False, False)
    if _short_social(user_text):
        return TurnDecision("social", False, False)

    table_now = bool(
        _asks_table(user_text)
        or infer_dishes_from_text(user_text)
        or infer_categories_from_text(user_text)
        or any(token in _current_fold(user_text) for token in RESUME_TABLE)
    )
    continue_table = _table_continuation(user_text, history)
    builder_now = _builder_ask(user_text)
    builder_continue = _history_had_builder(history) and any(
        token in _current_fold(user_text) for token in BUILDER_CONTINUE
    )

    if table_now or continue_table:
        return TurnDecision("table", True, builder_now or builder_continue)
    if builder_now or builder_continue:
        return TurnDecision("builder", False, True)
    return TurnDecision("other", False, False)


def skip_accompaniments_result() -> dict:
    return {
        "available": False,
        "cta": None,
        "items": [],
        "hub_status": "skipped",
        "notice": "",
        "reason": "A pergunta atual não pede seleção de acompanhamentos.",
    }


def skip_builder_result() -> dict:
    return {
        "accepted": False,
        "cta": None,
        "reason": "A pergunta atual não pede montar um pão.",
    }


def skip_pairing_result() -> dict:
    return {
        "available": False,
        "enabled": True,
        "references": [],
        "evaluations": [],
        "catalogs": [],
        "reason": "A pergunta atual não pede harmonização.",
    }

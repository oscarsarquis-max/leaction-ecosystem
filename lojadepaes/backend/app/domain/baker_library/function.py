"""Classifica a função do turno: atendimento, Fazedor ou aprofundamento da Biblioteca."""

from __future__ import annotations

from typing import Any, Literal

from app.domain.gigio.intent import TurnDecision

FunctionName = Literal["atendimento", "fazedor", "biblioteca"]


def classify_function(page: dict[str, Any] | None, decision: TurnDecision) -> FunctionName:
    """Função e contexto da página, não palavra-chave nem rota trocada pelo cliente."""
    if decision.builder or decision.kind == "builder":
        return "fazedor"
    if decision.kind in {"support", "complaint"}:
        return "atendimento"
    consult = ""
    if isinstance(page, dict):
        consult = str(page.get("consult") or "").strip().casefold()
    if consult == "deepen" and decision.kind != "social":
        return "biblioteca"
    if decision.kind in {"table", "support", "complaint"} or decision.accompaniments:
        return "atendimento"
    library = page.get("library") if isinstance(page, dict) and isinstance(page.get("library"), dict) else {}
    intent = str(library.get("intent") or "").strip().casefold()
    if intent == "deepen":
        return "biblioteca"
    return "atendimento"


def deepening_required(function: FunctionName) -> bool:
    return function == "biblioteca"

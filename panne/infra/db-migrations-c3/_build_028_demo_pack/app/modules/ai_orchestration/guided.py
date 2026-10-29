"""Entrada guiada do assistente. Sem chat livre."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal
from uuid import UUID

from pydantic import Field, field_validator

from app.modules.ai_orchestration.guardrails import scan_payload
from app.modules.ai_orchestration.limits import MAX_ITEM_CHARS, MAX_LIST_ITEMS, MAX_NOTES_CHARS, MAX_OBJECTIVE_CHARS
from app.modules.ai_orchestration.schema import StrictModel
from app.modules.production_planning.errors import ValidationError

Intent = Literal["create_recipe", "adapt_recipe"]


class GuidedProposalInput(StrictModel):
    intent: Intent
    base_formulation_version_id: str | None = None
    objective: str = Field(min_length=3, max_length=MAX_OBJECTIVE_CHARS)
    product_type: str | None = Field(default=None, max_length=MAX_ITEM_CHARS)
    yield_units: int | None = Field(default=None, ge=1, le=100_000)
    target_quantity: str | None = Field(default=None, max_length=40)
    technical_traits: list[str] = Field(default_factory=list, max_length=MAX_LIST_ITEMS)
    required_components: list[str] = Field(default_factory=list, max_length=MAX_LIST_ITEMS)
    forbidden_components: list[str] = Field(default_factory=list, max_length=MAX_LIST_ITEMS)
    allergens_to_avoid: list[str] = Field(default_factory=list, max_length=MAX_LIST_ITEMS)
    process_limits: list[str] = Field(default_factory=list, max_length=MAX_LIST_ITEMS)
    selected_reference_ids: list[str] = Field(default_factory=list, max_length=MAX_LIST_ITEMS)
    selected_knowledge_source_ids: list[str] = Field(
        default_factory=list, max_length=MAX_LIST_ITEMS
    )
    allowed_ingredient_version_ids: list[str] = Field(
        default_factory=list, max_length=MAX_LIST_ITEMS
    )
    jurisdiction: str | None = Field(default=None, max_length=80)
    regulatory_purpose: str | None = Field(default=None, max_length=200)
    notes: str | None = Field(default=None, max_length=MAX_NOTES_CHARS)

    @field_validator(
        "technical_traits",
        "required_components",
        "forbidden_components",
        "allergens_to_avoid",
        "process_limits",
        mode="before",
    )
    @classmethod
    def _trim_list(cls, value):
        if value is None:
            return []
        cleaned = []
        for item in value:
            text = str(item).strip()
            if not text:
                continue
            if len(text) > MAX_ITEM_CHARS:
                raise ValueError("item excede o limite")
            cleaned.append(text)
        return cleaned


@dataclass(frozen=True)
class SanitizedGuidedInput:
    intent: Intent
    objective: str
    product_type: str | None
    yield_units: int | None
    target_quantity: str | None
    technical_traits: tuple[str, ...]
    required_components: tuple[str, ...]
    forbidden_components: tuple[str, ...]
    allergens_to_avoid: tuple[str, ...]
    process_limits: tuple[str, ...]
    selected_reference_ids: tuple[UUID, ...]
    selected_knowledge_source_ids: tuple[UUID, ...]
    allowed_ingredient_version_ids: tuple[UUID, ...]
    base_formulation_version_id: UUID | None
    jurisdiction: str | None
    regulatory_purpose: str | None
    notes: str | None
    alerts: tuple[dict, ...] = field(default_factory=tuple)

    def as_canonical(self) -> dict[str, Any]:
        return {
            "intent": self.intent,
            "objective": self.objective,
            "product_type": self.product_type,
            "yield_units": self.yield_units,
            "target_quantity": self.target_quantity,
            "technical_traits": list(self.technical_traits),
            "required_components": list(self.required_components),
            "forbidden_components": list(self.forbidden_components),
            "allergens_to_avoid": list(self.allergens_to_avoid),
            "process_limits": list(self.process_limits),
            "selected_reference_ids": [str(item) for item in self.selected_reference_ids],
            "selected_knowledge_source_ids": [
                str(item) for item in self.selected_knowledge_source_ids
            ],
            "allowed_ingredient_version_ids": [
                str(item) for item in self.allowed_ingredient_version_ids
            ],
            "base_formulation_version_id": (
                None
                if self.base_formulation_version_id is None
                else str(self.base_formulation_version_id)
            ),
            "jurisdiction": self.jurisdiction,
            "regulatory_purpose": self.regulatory_purpose,
            "notes": self.notes,
        }


def _as_uuids(values: list[str], label: str) -> tuple[UUID, ...]:
    parsed: list[UUID] = []
    for item in values:
        try:
            parsed.append(UUID(str(item)))
        except ValueError as exc:
            raise ValidationError(f"{label} inválido") from exc
    return tuple(parsed)


def sanitize_guided_input(payload: dict) -> SanitizedGuidedInput:
    parsed = GuidedProposalInput.model_validate(payload)
    if parsed.intent == "adapt_recipe" and not parsed.base_formulation_version_id:
        raise ValidationError("adaptação exige versão-base")
    if parsed.intent == "create_recipe" and parsed.base_formulation_version_id:
        raise ValidationError("criação não deve apontar versão-base")
    alerts = scan_payload(parsed.model_dump())
    base_id = None
    if parsed.base_formulation_version_id:
        try:
            base_id = UUID(parsed.base_formulation_version_id)
        except ValueError as exc:
            raise ValidationError("versão-base inválida") from exc
    return SanitizedGuidedInput(
        intent=parsed.intent,
        objective=parsed.objective.strip(),
        product_type=None if parsed.product_type is None else parsed.product_type.strip() or None,
        yield_units=parsed.yield_units,
        target_quantity=parsed.target_quantity,
        technical_traits=tuple(parsed.technical_traits),
        required_components=tuple(parsed.required_components),
        forbidden_components=tuple(parsed.forbidden_components),
        allergens_to_avoid=tuple(parsed.allergens_to_avoid),
        process_limits=tuple(parsed.process_limits),
        selected_reference_ids=_as_uuids(parsed.selected_reference_ids, "referência"),
        selected_knowledge_source_ids=_as_uuids(
            parsed.selected_knowledge_source_ids, "fonte"
        ),
        allowed_ingredient_version_ids=_as_uuids(
            parsed.allowed_ingredient_version_ids, "ingrediente"
        ),
        base_formulation_version_id=base_id,
        jurisdiction=parsed.jurisdiction,
        regulatory_purpose=parsed.regulatory_purpose,
        notes=None if parsed.notes is None else parsed.notes.strip() or None,
        alerts=tuple(alerts),
    )

"""Schema Pydantic da proposta assistiva. extra=forbid. Sem parsing de Markdown."""

from __future__ import annotations

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ASSISTIVE_DISCLAIMER = (
    "Sugestão assistiva da Panne; não é formulação oficial, aprovada ou publicada."
)


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ProposedItem(StrictModel):
    sequence: int = Field(ge=1)
    ingredient_version_id: str | None = None
    proposed_ingredient_name: str = Field(min_length=1, max_length=200)
    net_quantity_g: Decimal | None = None
    correction_factor: Decimal | None = None
    is_flour_basis: bool
    role: str = Field(min_length=1, max_length=80)
    rationale: str = Field(min_length=1, max_length=2_000)
    confidence_note: str = Field(min_length=1, max_length=500)
    cited_evidence_tokens: list[str] = Field(default_factory=list)


class ProposedStep(StrictModel):
    sequence: int = Field(ge=1)
    title: str = Field(min_length=1, max_length=200)
    instructions: str = Field(min_length=1, max_length=4_000)
    duration_seconds: int | None = Field(default=None, ge=1, le=604_800)
    temperature_celsius: Decimal | None = Field(default=None, ge=-20, le=400)
    rationale: str = Field(min_length=1, max_length=2_000)
    cited_evidence_tokens: list[str] = Field(default_factory=list)


class ProposalOutput(StrictModel):
    proposal_type: Literal["create", "adapt"]
    title: str = Field(min_length=1, max_length=200)
    objective: str = Field(min_length=1, max_length=2_000)
    assistive_disclaimer: str
    items: list[ProposedItem] = Field(min_length=1)
    steps: list[ProposedStep] = Field(default_factory=list)
    assumptions: list[str]
    unresolved_questions: list[str]
    warnings: list[str]
    cited_evidence_tokens: list[str]


class ExplanationOutput(StrictModel):
    summary: str = Field(min_length=1, max_length=4_000)
    assistive_disclaimer: str
    cited_evidence_tokens: list[str]
    warnings: list[str]


def proposal_json_schema() -> dict:
    return ProposalOutput.model_json_schema()


def explanation_json_schema() -> dict:
    return ExplanationOutput.model_json_schema()

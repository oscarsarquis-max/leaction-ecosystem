"""Pydantic schemas — Evolution Map packages and suggestions."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.enums import (
    EvolutionCategory,
    EvolutionConfidence,
    EvolutionEffort,
    EvolutionGenerationMode,
    EvolutionImpact,
    EvolutionPackageStatus,
    EvolutionPriority,
    EvolutionSuggestionStatus,
)


class SourceReference(BaseModel):
    kind: Literal[
        "question",
        "guided_answer",
        "evidence",
        "finding",
        "maturity_assessment",
        "maturity_score",
        "action_item",
        "wizard_context",
    ]
    id: str | None = None
    question_id: str | None = None
    question_version: str | None = None
    label: str | None = None
    detail: str | None = None


class EvolutionSuggestionOut(BaseModel):
    id: UUID
    organization_id: UUID
    assessment_id: UUID
    package_id: UUID
    package_version: int
    rule_id: str
    rule_version: str
    category: EvolutionCategory
    title: str
    observation: str
    business_rationale: str
    suggested_evolution: str
    expected_benefit: str
    first_step: str
    impact: EvolutionImpact
    effort: EvolutionEffort
    priority: EvolutionPriority
    confidence: EvolutionConfidence
    is_priority: bool
    source_references: list[SourceReference] = Field(default_factory=list)
    status: EvolutionSuggestionStatus
    dismiss_reason: str | None = None
    generated_at: datetime
    generated_by: UUID
    reviewed_at: datetime | None = None
    reviewed_by: UUID | None = None


class EvolutionPackageOut(BaseModel):
    id: UUID
    organization_id: UUID
    assessment_id: UUID
    package_version: int
    generation_mode: EvolutionGenerationMode
    status: EvolutionPackageStatus
    supersedes_id: UUID | None = None
    source_fingerprint: str
    source_snapshot: dict[str, Any] = Field(default_factory=dict)
    catalog_version: str
    generated_at: datetime
    generated_by: UUID
    priority_suggestions: list[EvolutionSuggestionOut] = Field(default_factory=list)
    secondary_suggestions: list[EvolutionSuggestionOut] = Field(default_factory=list)


class EvolutionGenerateIn(BaseModel):
    mode: EvolutionGenerationMode | None = None
    """If omitted, preliminary for draft/planned; analysis_ready from analysis onward."""


class DismissSuggestionIn(BaseModel):
    reason: str = Field(..., min_length=3, max_length=2000)


class InvestigateSuggestionIn(BaseModel):
    note: str | None = Field(default=None, max_length=2000)

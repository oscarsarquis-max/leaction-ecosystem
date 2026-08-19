from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

ImprovementCaseStatus = Literal[
    "open", "analyzing", "acting", "reviewing", "closed"
]

_MAX_TEXT = 4000


def _require_nonblank(v: str) -> str:
    cleaned = (v or "").strip()
    if not cleaned:
        raise ValueError("must not be blank")
    return cleaned


class ImprovementCaseCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    problem_statement: str = Field(min_length=1, max_length=_MAX_TEXT)
    impact_statement: str = Field(min_length=1, max_length=_MAX_TEXT)
    related_process: str = Field(min_length=1, max_length=_MAX_TEXT)

    @field_validator("problem_statement", "impact_statement", "related_process")
    @classmethod
    def strip_required(cls, v: str) -> str:
        return _require_nonblank(v)


class ImprovementCasePatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    problem_statement: str | None = Field(default=None, min_length=1, max_length=_MAX_TEXT)
    impact_statement: str | None = Field(default=None, min_length=1, max_length=_MAX_TEXT)
    related_process: str | None = Field(default=None, min_length=1, max_length=_MAX_TEXT)
    status: ImprovementCaseStatus | None = None

    @field_validator("problem_statement", "impact_statement", "related_process")
    @classmethod
    def strip_optional(cls, v: str | None) -> str | None:
        if v is None:
            return None
        return _require_nonblank(v)


class ImprovementCaseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    problem_statement: str
    impact_statement: str
    related_process: str
    status: ImprovementCaseStatus
    created_by: UUID
    created_at: datetime
    updated_at: datetime

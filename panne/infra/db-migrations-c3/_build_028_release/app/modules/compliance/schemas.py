"""Schemas declarativos fechados. extra=forbid. Sem eval."""

from __future__ import annotations

from decimal import Decimal
from typing import Annotated, Literal, Union

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

from app.modules.compliance.constants import COMPOUND_OPERATORS, NUMERIC_OPERATORS


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class EvidencePresenceParams(StrictModel):
    type: Literal["evidence_presence"]
    evidence_key: str = Field(min_length=1, max_length=120)


class NumericComparisonParams(StrictModel):
    type: Literal["numeric_comparison"]
    input_key: str = Field(min_length=1, max_length=120)
    operator: Literal["eq", "ne", "gt", "gte", "lt", "lte"]
    threshold: Decimal

    def model_post_init(self, __context) -> None:
        if self.operator not in NUMERIC_OPERATORS:
            raise ValueError("operador numérico não autorizado")


class BooleanConditionParams(StrictModel):
    type: Literal["boolean_condition"]
    input_key: str = Field(min_length=1, max_length=120)
    expected: bool


class CatalogMembershipParams(StrictModel):
    type: Literal["catalog_membership"]
    input_key: str = Field(min_length=1, max_length=120)
    catalog: list[str] = Field(min_length=1)
    mode: Literal["in", "not_in"] = "in"


class MandatoryManualReviewParams(StrictModel):
    type: Literal["mandatory_manual_review"]
    reason: str = Field(min_length=1, max_length=500)


LeafParams = Annotated[
    Union[
        EvidencePresenceParams,
        NumericComparisonParams,
        BooleanConditionParams,
        CatalogMembershipParams,
        MandatoryManualReviewParams,
    ],
    Field(discriminator="type"),
]


class CompoundParams(StrictModel):
    type: Literal["compound"]
    operator: Literal["and", "or"]
    clauses: list[LeafParams] = Field(min_length=2)

    def model_post_init(self, __context) -> None:
        if self.operator not in COMPOUND_OPERATORS:
            raise ValueError("operador composto não autorizado")


EvaluationParams = Annotated[
    Union[
        EvidencePresenceParams,
        NumericComparisonParams,
        BooleanConditionParams,
        CatalogMembershipParams,
        MandatoryManualReviewParams,
        CompoundParams,
    ],
    Field(discriminator="type"),
]


class ApplicabilityCriteria(StrictModel):
    jurisdictions: list[str] | None = None
    activities: list[str] | None = None
    product_categories: list[str] | None = None
    sale_forms: list[str] | None = None
    packaging: list[str] | None = None
    processes: list[str] | None = None
    equipment: list[str] | None = None
    required_context_keys: list[str] | None = None


_PARAMS_ADAPTER = TypeAdapter(EvaluationParams)
_APPLICABILITY_ADAPTER = TypeAdapter(ApplicabilityCriteria)


def parse_evaluation_params(payload: dict) -> EvaluationParams:
    if not isinstance(payload, dict) or "type" not in payload:
        raise ValueError("tipo de avaliação ausente")
    return _PARAMS_ADAPTER.validate_python(payload)


def parse_applicability(payload: dict | None) -> ApplicabilityCriteria:
    return _APPLICABILITY_ADAPTER.validate_python(payload or {})

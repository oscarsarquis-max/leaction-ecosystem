"""Motor declarativo fechado. Sem eval e sem zero implícito."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any

from app.modules.compliance.schemas import (
    BooleanConditionParams,
    CatalogMembershipParams,
    CompoundParams,
    EvaluationParams,
    EvidencePresenceParams,
    MandatoryManualReviewParams,
    NumericComparisonParams,
    parse_evaluation_params,
)

_COMPARE = {
    "eq": lambda left, right: left == right,
    "ne": lambda left, right: left != right,
    "gt": lambda left, right: left > right,
    "gte": lambda left, right: left >= right,
    "lt": lambda left, right: left < right,
    "lte": lambda left, right: left <= right,
}


@dataclass(frozen=True)
class EngineInputs:
    values: dict[str, Any]
    evidence_keys: frozenset[str]


@dataclass(frozen=True)
class EngineOutcome:
    result: str
    message: str
    used_inputs: dict[str, Any]


class EngineError(ValueError):
    """Parâmetro de avaliação recusado."""


def evaluate_parameters(parameters: dict, inputs: EngineInputs) -> EngineOutcome:
    parsed = parse_evaluation_params(parameters)
    return _evaluate(parsed, inputs)


def _evaluate(params: EvaluationParams, inputs: EngineInputs) -> EngineOutcome:
    if isinstance(params, EvidencePresenceParams):
        present = params.evidence_key in inputs.evidence_keys
        used = {"evidence_key": params.evidence_key, "present": present}
        if not present:
            return EngineOutcome(
                "insufficient_data",
                "Evidência obrigatória ausente; ausência não aprova.",
                used,
            )
        return EngineOutcome("pass", "Evidência obrigatória presente.", used)
    if isinstance(params, NumericComparisonParams):
        raw = inputs.values.get(params.input_key, None)
        if raw is None or raw == "":
            return EngineOutcome(
                "insufficient_data",
                "Valor numérico ausente; ausência não é zero nem aprovação.",
                {"input_key": params.input_key},
            )
        try:
            value = Decimal(str(raw))
        except (InvalidOperation, ValueError) as exc:
            raise EngineError("valor numérico inválido") from exc
        matched = _COMPARE[params.operator](value, params.threshold)
        used = {
            "input_key": params.input_key,
            "value": str(value),
            "operator": params.operator,
            "threshold": str(params.threshold),
        }
        if matched:
            return EngineOutcome("pass", "Comparação numérica satisfeita.", used)
        return EngineOutcome("fail", "Comparação numérica não satisfeita.", used)
    if isinstance(params, BooleanConditionParams):
        if params.input_key not in inputs.values:
            return EngineOutcome(
                "insufficient_data",
                "Condição booleana sem valor declarado.",
                {"input_key": params.input_key},
            )
        raw = inputs.values[params.input_key]
        if not isinstance(raw, bool):
            raise EngineError("valor booleano inválido")
        used = {"input_key": params.input_key, "value": raw, "expected": params.expected}
        if raw is params.expected:
            return EngineOutcome("pass", "Condição booleana satisfeita.", used)
        return EngineOutcome("fail", "Condição booleana não satisfeita.", used)
    if isinstance(params, CatalogMembershipParams):
        if params.input_key not in inputs.values:
            return EngineOutcome(
                "insufficient_data",
                "Valor de catálogo ausente.",
                {"input_key": params.input_key},
            )
        raw = inputs.values[params.input_key]
        values = raw if isinstance(raw, list) else [raw]
        catalog = set(params.catalog)
        present = {str(item) for item in values}
        matched = bool(present & catalog)
        used = {"input_key": params.input_key, "values": sorted(present), "mode": params.mode}
        ok = matched if params.mode == "in" else not matched
        if ok:
            return EngineOutcome("pass", "Pertencimento ao catálogo satisfeito.", used)
        return EngineOutcome("fail", "Pertencimento ao catálogo não satisfeito.", used)
    if isinstance(params, MandatoryManualReviewParams):
        return EngineOutcome(
            "manual_review",
            f"Revisão humana obrigatória: {params.reason}",
            {"reason": params.reason},
        )
    if isinstance(params, CompoundParams):
        outcomes = [_evaluate(clause, inputs) for clause in params.clauses]
        results = [row.result for row in outcomes]
        used = {"operator": params.operator, "clauses": [row.used_inputs for row in outcomes]}
        if "insufficient_data" in results:
            return EngineOutcome(
                "insufficient_data",
                "Cláusula composta com dado ausente.",
                used,
            )
        if "manual_review" in results:
            return EngineOutcome("manual_review", "Cláusula composta exige revisão humana.", used)
        if params.operator == "and":
            if all(result == "pass" for result in results):
                return EngineOutcome("pass", "Todas as cláusulas compostas passaram.", used)
            return EngineOutcome("fail", "Uma cláusula composta falhou.", used)
        if any(result == "pass" for result in results):
            return EngineOutcome("pass", "Uma cláusula composta passou.", used)
        return EngineOutcome("fail", "Nenhuma cláusula composta passou.", used)
    raise EngineError("tipo de avaliação desconhecido")

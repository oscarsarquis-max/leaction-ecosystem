"""Filtro determinístico de aplicabilidade. Sem inferência por nome."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from app.modules.compliance.models import ComplianceFrameworkVersion, ComplianceProfile
from app.modules.compliance.schemas import ApplicabilityCriteria, parse_applicability


@dataclass(frozen=True)
class ApplicabilityDecision:
    status: str
    reason: str


def _declared(values: list[str] | None) -> list[str]:
    return [item.strip() for item in values or [] if item and item.strip()]


def _profile_jurisdictions(profile: ComplianceProfile) -> list[str]:
    items = [profile.country]
    if profile.state:
        items.append(f"{profile.country}-{profile.state}")
    if profile.state and profile.municipality:
        items.append(f"{profile.country}-{profile.state}-{profile.municipality}")
    return items


def version_applies(version: ComplianceFrameworkVersion, profile: ComplianceProfile) -> bool:
    when = profile.reference_date
    if when < version.effective_from:
        return False
    if version.effective_until is not None and when > version.effective_until:
        return False
    path = "-".join(
        part
        for part in (profile.country, profile.state, profile.municipality)
        if part
    )
    root = version.jurisdiction
    return path == root or path.startswith(f"{root}-") or root == profile.country


def decide_requirement(
    criteria: ApplicabilityCriteria | dict,
    profile: ComplianceProfile,
    *,
    assessed_on: date,
) -> ApplicabilityDecision:
    if isinstance(criteria, ApplicabilityCriteria):
        parsed = criteria
    else:
        parsed = parse_applicability(criteria)
    if assessed_on != profile.reference_date:
        if assessed_on < profile.reference_date:
            return ApplicabilityDecision(
                "insufficient_context",
                "data de avaliação anterior ao perfil",
            )
    categories = list(profile.product_categories or [])
    checks = (
        ("jurisdictions", parsed.jurisdictions, _profile_jurisdictions(profile), True),
        ("activities", parsed.activities, [profile.activity] if profile.activity else [], False),
        ("product_categories", parsed.product_categories, categories, False),
        ("sale_forms", parsed.sale_forms, [profile.sale_form] if profile.sale_form else [], False),
        ("packaging", parsed.packaging, [profile.packaging] if profile.packaging else [], False),
        ("processes", parsed.processes, list(profile.processes or []), False),
        ("equipment", parsed.equipment, list(profile.equipment or []), False),
    )
    for name, required, actual, allow_prefix in checks:
        needed = _declared(required)
        if not needed:
            continue
        have = _declared([str(item) for item in actual])
        if not have:
            return ApplicabilityDecision(
                "insufficient_context",
                f"critério {name} declarado no requisito sem valor no perfil",
            )
        if allow_prefix:
            matched = any(
                any(item == need or item.startswith(need) or need.startswith(item) for item in have)
                for need in needed
            )
        else:
            matched = any(item in needed for item in have)
        if not matched:
            return ApplicabilityDecision("not_applicable", f"perfil fora do critério {name}")
    for key in parsed.required_context_keys or []:
        extra = profile.extra_context or {}
        if key not in extra:
            return ApplicabilityDecision(
                "insufficient_context",
                f"contexto adicional {key} não declarado no perfil",
            )
    return ApplicabilityDecision("applicable", "critérios satisfeitos")

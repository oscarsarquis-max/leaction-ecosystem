"""Validação de completude do diagnóstico — 18 questões por dimensão (9 domínios × P/F)."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from app.core.framework_definitions import CANONICAL_DOMAIN_KEYS, normalize_domain_key
from app.core.sector_constants import LEGACY_DOMAIN_ID_TO_KEY
from app.database.models import AssessmentItem, AssessmentResponse
from app.services.paneldx_maturity_calculator import normalize_prefu

REQUIRED_DOMAINS_PER_DIMENSION = len(CANONICAL_DOMAIN_KEYS)  # 9
REQUIRED_QUESTIONS_PER_DIMENSION = REQUIRED_DOMAINS_PER_DIMENSION * 2  # 18
TEMPORAL_LABELS = {"P": "Presente", "F": "Futuro"}


def _safe_grad(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, str) and value.strip().lower() in ("na", "null", ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _dimension_label(item: AssessmentItem) -> str:
    meta = item.item_metadata or {}
    dim_key = str(meta.get("dimension_key") or "").upper()
    if dim_key:
        return dim_key
    legacy_dime = meta.get("legacy_id_dime")
    if legacy_dime is not None:
        try:
            from app.core.sector_constants import LEGACY_DIME_ID_TO_KEY

            return LEGACY_DIME_ID_TO_KEY.get(int(legacy_dime), str(legacy_dime))
        except (TypeError, ValueError):
            return str(legacy_dime)
    return "—"


def _domain_key_for_item(item: AssessmentItem) -> str:
    meta = item.item_metadata or {}
    dom = normalize_domain_key(meta.get("domain_key"))
    if dom:
        return dom
    legacy_doma = meta.get("legacy_id_doma")
    if legacy_doma is not None:
        try:
            return LEGACY_DOMAIN_ID_TO_KEY.get(int(legacy_doma), str(legacy_doma))
        except (TypeError, ValueError):
            return str(legacy_doma)
    return ""


def _prefu_for_item(item: AssessmentItem) -> str:
    meta = item.item_metadata or {}
    prefu = normalize_prefu(meta.get("prefu_ques"))
    if prefu:
        return prefu
    if "(Futuro)" in (item.axis or ""):
        return "F"
    return "P"


def catalog_slots_by_dimension(
    catalog_items: list[AssessmentItem],
) -> dict[str, set[tuple[str, str]]]:
    slots: dict[str, set[tuple[str, str]]] = defaultdict(set)
    for item in catalog_items:
        dim = _dimension_label(item)
        dom = _domain_key_for_item(item)
        prefu = _prefu_for_item(item)
        if dim and dom and prefu in ("P", "F"):
            slots[dim].add((dom, prefu))
    return dict(slots)


def answered_slots_by_dimension(
    responses: list[AssessmentResponse],
    items_by_id: dict[Any, AssessmentItem],
) -> dict[str, set[tuple[str, str]]]:
    slots: dict[str, set[tuple[str, str]]] = defaultdict(set)
    for resp in responses:
        item = items_by_id.get(resp.assessment_item_id)
        if not item or _safe_grad(resp.selected_value) is None:
            continue
        dim = _dimension_label(item)
        dom = _domain_key_for_item(item)
        prefu = _prefu_for_item(item)
        if dim and dom and prefu in ("P", "F"):
            slots[dim].add((dom, prefu))
    return dict(slots)


def validate_diagnostic_completeness(
    catalog_items: list[AssessmentItem],
    responses: list[AssessmentResponse],
    items_by_id: dict[Any, AssessmentItem],
) -> None:
    """
    Exige 18 questões respondidas por dimensão: 9 domínios (Presente) + 9 (Futuro).
    """
    expected = catalog_slots_by_dimension(catalog_items)
    answered = answered_slots_by_dimension(responses, items_by_id)

    if not expected:
        raise ValueError("Catálogo de questões do framework vazio ou sem metadados de dimensão/domínio.")

    errors: list[str] = []

    for dim in sorted(expected.keys()):
        expected_slots = expected[dim]
        answered_slots = answered.get(dim, set())

        if len(expected_slots) < REQUIRED_QUESTIONS_PER_DIMENSION:
            errors.append(
                f"Dimensão {dim}: catálogo incompleto "
                f"({len(expected_slots)}/{REQUIRED_QUESTIONS_PER_DIMENSION} questões — "
                f"esperado 9 domínios × Presente/Futuro)."
            )

        missing = expected_slots - answered_slots
        if missing:
            for dom, prefu in sorted(missing)[:6]:
                errors.append(
                    f"Dimensão {dim}: falta domínio «{dom}» ({TEMPORAL_LABELS.get(prefu, prefu)})."
                )
            if len(missing) > 6:
                errors.append(f"Dimensão {dim}: +{len(missing) - 6} questão(ões) ainda pendentes.")

        for prefu in ("P", "F"):
            n_answered = len({dom for dom, p in answered_slots if p == prefu})
            if n_answered < REQUIRED_DOMAINS_PER_DIMENSION:
                label = TEMPORAL_LABELS[prefu]
                errors.append(
                    f"Dimensão {dim} ({label}): {n_answered}/{REQUIRED_DOMAINS_PER_DIMENSION} domínios respondidos."
                )

    if errors:
        raise ValueError(
            "O diagnóstico exige 18 questões por dimensão (9 domínios no Presente e 9 no Futuro). "
            + " ".join(errors[:10])
        )


def completeness_summary(
    catalog_items: list[AssessmentItem],
    responses: list[AssessmentResponse],
    items_by_id: dict[Any, AssessmentItem],
) -> dict[str, Any]:
    expected = catalog_slots_by_dimension(catalog_items)
    answered = answered_slots_by_dimension(responses, items_by_id)
    dimensions: list[dict[str, Any]] = []

    for dim in sorted(expected.keys()):
        exp = expected[dim]
        ans = answered.get(dim, set())
        dimensions.append(
            {
                "dimension": dim,
                "expected_count": len(exp),
                "answered_count": len(ans),
                "required_per_dimension": REQUIRED_QUESTIONS_PER_DIMENSION,
                "present_domains_answered": len({d for d, p in ans if p == "P"}),
                "future_domains_answered": len({d for d, p in ans if p == "F"}),
                "is_complete": len(ans) >= len(exp)
                and len(ans) >= REQUIRED_QUESTIONS_PER_DIMENSION,
            }
        )

    total_expected = sum(len(slots) for slots in expected.values())
    total_answered = sum(len(slots) for slots in answered.values())

    return {
        "required_questions_per_dimension": REQUIRED_QUESTIONS_PER_DIMENSION,
        "required_domains_per_temporal": REQUIRED_DOMAINS_PER_DIMENSION,
        "dimension_count": len(expected),
        "total_expected": total_expected,
        "total_answered": total_answered,
        "is_complete": total_answered >= total_expected
        and all(d["is_complete"] for d in dimensions),
        "dimensions": dimensions,
    }

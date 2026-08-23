from hashlib import sha256
from json import dumps

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.formula_lab.models import Formulation, FormulationVersion
from app.modules.formula_lab.queries import (
    approvals_of,
    bakers_view,
    completeness_of,
    ingredient_label,
    items_of,
    latest_nutrition,
    nutrition_items_of,
    product_of,
    scales_of,
    steps_of,
    trials_of,
)
from app.modules.formula_lab.rules import derived_gross_quantity
from app.modules.formula_lab.version_references import version_references_of
from app.modules.nutrition_calculation.models import CalculationEvidence
from app.modules.production_http.schemas import decimal_str

TECHNICAL_DISCLAIMER = (
    "Prévia técnica incompleta e não validada regulatoriamente."
)


def _canonical(payload: dict) -> str:
    return dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def project_technical_sheet(
    session: Session,
    recipe: Formulation,
    version: FormulationVersion,
    *,
    organization_name: str,
    actor_name: str | None,
) -> dict:
    product = product_of(session, recipe.technical_product_id)
    items = items_of(session, version.id)
    bakers = bakers_view(session, version.id)
    percents = {row["id"]: row["bakers_percentage"] for row in bakers["items"]}
    nutrition = latest_nutrition(session, version.id)
    latest_scale = scales_of(session, version.id)
    latest_decision = approvals_of(session, version.id)
    body = {
        "kind": "ficha_tecnica_derivada",
        "disclaimer": TECHNICAL_DISCLAIMER,
        "identity": {
            "recipe_id": str(recipe.id),
            "code": recipe.code,
            "display_name": recipe.display_name,
            "status": recipe.status,
            "product_id": str(recipe.technical_product_id),
            "product_code": None if product is None else product.code,
            "product_name": None if product is None else product.display_name,
        },
        "version": {
            "id": str(version.id),
            "version_number": version.version_number,
            "status": version.status,
            "published_at": (
                None if version.published_at is None else version.published_at.isoformat()
            ),
            "notes": version.notes,
        },
        "organization": {
            "id": str(recipe.organization_id),
            "display_name": organization_name,
        },
        "responsible": {"display_name": actor_name},
        "approval": None
        if not latest_decision
        else {
            "decision": latest_decision[0].decision,
            "occurred_at": latest_decision[0].occurred_at.isoformat(),
        },
        "components": [
            {
                "sequence": item.sequence,
                "label": ingredient_label(session, item.ingredient_version_id),
                "role": item.role,
                "net_quantity": decimal_str(item.net_quantity),
                "gross_quantity": decimal_str(
                    derived_gross_quantity(item.net_quantity, item.correction_factor)
                ),
                "correction_factor": decimal_str(item.correction_factor),
                "is_flour_basis": item.is_flour_basis,
                "bakers_percentage": percents.get(str(item.id)),
                "measurement_unit_id": str(item.measurement_unit_id),
            }
            for item in items
        ],
        "bakers_percentage": {
            "flour_mass": bakers["flour_mass"],
            "explained_absence": bakers["explained_absence"],
        },
        "steps": [
            {
                "sequence": step.sequence,
                "title": step.title,
                "instructions": step.instructions,
                "duration_seconds": step.duration_seconds,
                "temperature_celsius": decimal_str(step.temperature_celsius),
            }
            for step in steps_of(session, version.id)
        ],
        "yield": {
            "yield_units": version.yield_units,
            "target_unit_weight_g": decimal_str(version.target_unit_weight_g),
            "expected_bake_loss_rate": decimal_str(version.expected_bake_loss_rate),
            "portion_mass_g": None
            if nutrition is None
            else decimal_str(nutrition.portion_mass_g),
        },
        "scale": None
        if not latest_scale
        else {
            "id": str(latest_scale[0].id),
            "mode": latest_scale[0].calculation_mode,
            "scale_factor": decimal_str(latest_scale[0].scale_factor),
            "algorithm": f"{latest_scale[0].algorithm_code} {latest_scale[0].algorithm_version}",
        },
        "nutrition": None
        if nutrition is None
        else {
            "id": str(nutrition.id),
            "status": nutrition.status,
            "formula_net_mass_g": decimal_str(nutrition.formula_net_mass_g),
            "expected_final_mass_g": decimal_str(nutrition.expected_final_mass_g),
            "portion_mass_g": decimal_str(nutrition.portion_mass_g),
            "items": [
                {
                    "nutrient_definition_id": str(item.nutrient_definition_id),
                    "whole_formula_amount": decimal_str(item.whole_formula_amount),
                    "per_100g_amount": decimal_str(item.per_100g_amount),
                    "technical_portion_amount": decimal_str(item.technical_portion_amount),
                    "completeness_status": item.completeness_status,
                }
                for item in nutrition_items_of(session, nutrition.id)
            ],
            "evidences": [
                {
                    "evidence_type": row.evidence_type,
                    "status": row.status,
                    "message": row.message,
                }
                for row in session.scalars(
                    select(CalculationEvidence).where(
                        CalculationEvidence.nutrition_calculation_id == nutrition.id
                    )
                )
            ],
        },
        "references": [
            {
                "id": str(link.id),
                "recipe_reference_id": None
                if link.recipe_reference_id is None
                else str(link.recipe_reference_id),
                "role": link.role,
                "source_version_label": link.source_version_label,
                "locator_type": link.locator_type,
                "locator_value": link.locator_value,
                "content_hash": link.content_hash,
                "accessed_at": None if link.accessed_at is None else link.accessed_at.isoformat(),
                "snapshot": link.snapshot,
            }
            for link in version_references_of(session, version.id)
        ],
        "trials": [
            {"code": trial.code, "status": trial.status}
            for trial in trials_of(session, version.id)
        ],
        "completeness": completeness_of(session, recipe, version),
        "dates": {
            "created_at": version.created_at.isoformat(),
            "published_at": None
            if version.published_at is None
            else version.published_at.isoformat(),
        },
    }
    digest = sha256(_canonical(body).encode("utf-8")).hexdigest()
    return {**body, "payload_sha256": digest}

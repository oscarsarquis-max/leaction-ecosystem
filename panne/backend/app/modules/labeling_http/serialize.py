"""Serialização de rotulagem. Sem selo de conformidade."""

from decimal import Decimal

from app.modules.labeling_compliance.models import LabelingDossier, LabelingDossierVersion


def _dec(value) -> str | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return format(value, "f")
    return str(value)


def _iso(value) -> str | None:
    return None if value is None else value.isoformat()


def dossier_card(row: LabelingDossier) -> dict:
    return {
        "id": str(row.id),
        "status": row.status,
        "formulation_id": str(row.formulation_id),
        "formulation_version_id": str(row.formulation_version_id),
        "nutrition_calculation_id": None
        if row.nutrition_calculation_id is None
        else str(row.nutrition_calculation_id),
        "row_version": row.row_version,
        "created_at": _iso(row.created_at),
        "disclaimer": "Proposta técnica para revisão. Não é declaração de conformidade.",
        "certified": False,
        "conforme_anvisa": False,
    }


def version_card(row: LabelingDossierVersion) -> dict:
    return {
        "id": str(row.id),
        "version_number": row.version_number,
        "status": row.status,
        "algorithm_name": row.algorithm_name,
        "algorithm_version": row.algorithm_version,
        "content_hash": row.content_hash,
        "created_at": _iso(row.created_at),
    }


def finding_out(row) -> dict:
    return {
        "id": str(row.id),
        "rule_code": row.rule_code,
        "result": row.result,
        "fact": row.fact,
        "expected_value": row.expected_value,
        "found_value": row.found_value,
        "source_code": row.source_code,
        "source_locator": row.source_locator,
        "source_version": row.source_version,
        "accessed_at": row.accessed_at,
        "explanation": row.explanation,
        "action_needed": row.action_needed,
    }


def nutrition_out(nutrition, lines) -> dict | None:
    if nutrition is None:
        return None
    return {
        "portion_g": _dec(nutrition.portion_g),
        "household_measure": nutrition.household_measure,
        "servings_per_package": nutrition.servings_per_package,
        "table_format": nutrition.table_format,
        "footnotes": nutrition.footnotes,
        "lines": [
            {
                "nutrient_code": line.nutrient_code,
                "technical_per_100g": _dec(line.technical_per_100g),
                "regulatory_per_100g": _dec(line.regulatory_per_100g),
                "declared_per_100g": _dec(line.declared_per_100g),
                "declared_per_serving": _dec(line.declared_per_serving),
                "daily_value_percent": _dec(line.daily_value_percent),
                "completeness": line.completeness,
                "presented": line.presented,
            }
            for line in lines
        ],
    }


def front_out(row) -> dict | None:
    if row is None:
        return None
    return {
        "added_sugars_result": row.added_sugars_result,
        "saturated_fat_result": row.saturated_fat_result,
        "sodium_result": row.sodium_result,
        "magnifier_required": row.magnifier_required,
        "nutrients_high": row.nutrients_high,
        "compared": row.compared,
        "disclaimer": "Representação candidata da lupa. Não é arte-final certificada.",
    }


def bundle_out(bundle: dict) -> dict:
    version = bundle["version"]
    assessment = bundle["assessment"]
    candidate = bundle["candidate"]
    return {
        "version": version_card(version),
        "assessment": None
        if assessment is None
        else {
            "id": str(assessment.id),
            "status": assessment.status,
            "proposal_summary": assessment.proposal_summary,
        },
        "findings": [finding_out(row) for row in bundle["findings"]],
        "nutrition": nutrition_out(bundle["nutrition"], bundle["lines"]),
        "front_of_pack": front_out(bundle["front"]),
        "ingredients": [
            {
                "sequence": row.sequence,
                "display_name": row.display_name,
                "ingredient_version_id": None
                if row.ingredient_version_id is None
                else str(row.ingredient_version_id),
                "net_quantity_g": _dec(row.net_quantity_g),
                "compound": row.compound,
                "components": row.components,
                "gap": row.gap,
            }
            for row in bundle["ingredients"]
        ],
        "warnings": [
            {
                "code": row.code,
                "kind": row.kind,
                "statement": row.statement,
                "result": row.result,
                "evidence": row.evidence,
            }
            for row in bundle["warnings"]
        ],
        "mandatory": [
            {
                "code": row.code,
                "label": row.label,
                "value": row.value,
                "status": row.status,
                "claim": row.claim,
            }
            for row in bundle["mandatory"]
        ],
        "candidate": None
        if candidate is None
        else {
            "id": str(candidate.id),
            "watermark": candidate.watermark,
            "payload": candidate.payload,
            "payload_sha256": candidate.payload_sha256,
        },
        "reviews": [
            {
                "id": str(row.id),
                "decision": row.decision,
                "notes": row.notes,
                "created_at": _iso(row.created_at),
            }
            for row in bundle["reviews"]
        ],
        "certified": False,
        "conforme_anvisa": False,
    }


def dossier_detail(payload: dict) -> dict:
    dossier = payload["dossier"]
    data = dossier_card(dossier)
    data["profile"] = payload["profile_payload"]
    data["versions"] = [version_card(row) for row in payload["versions"]]
    data["current"] = None if payload["bundle"] is None else bundle_out(payload["bundle"])
    return data

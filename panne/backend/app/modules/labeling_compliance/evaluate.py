"""Avaliação determinística. Reusa o motor fechado. Sem selo Anvisa."""

from __future__ import annotations

import hashlib
import json
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.compliance.engine import EngineInputs, evaluate_parameters
from app.modules.formula_lab.models import Formulation, FormulationVersion, TechnicalProduct
from app.modules.labeling_compliance.applicability import front_labeling_scope, profile_payload
from app.modules.labeling_compliance.constants import (
    ALGORITHM_NAME,
    ALGORITHM_VERSION,
    ENGINE_RESULT_MAP,
    MANDATORY_ITEMS,
    SOLID_ADDED_SUGARS_G,
    SOLID_SATURATED_FAT_G,
    SOLID_SODIUM_MG,
    WATERMARKS,
)
from app.modules.labeling_compliance.ingredients import candidate_ingredients
from app.modules.labeling_compliance.models import (
    LabelingAssessment,
    LabelingDossier,
    LabelingDossierVersion,
    LabelingEvidence,
    LabelingFinding,
    LabelingFrontOfPack,
    LabelingIngredientCandidate,
    LabelingLabelCandidate,
    LabelingMandatoryItem,
    LabelingNutritionCandidate,
    LabelingNutritionLine,
    LabelingWarningCandidate,
)
from app.modules.labeling_compliance.nutrition_declaration import project_declaration
from app.modules.labeling_compliance.portions import get_portion
from app.modules.labeling_compliance.sources import source_by_code
from app.modules.labeling_compliance.warnings import candidate_warnings
from app.modules.nutrition_calculation.models import NutritionCalculation


def _map_result(raw: str) -> str:
    return ENGINE_RESULT_MAP.get(raw, "manual_review_required")


def _finding(
    session: Session,
    *,
    organization_id,
    assessment_id,
    rule_code: str,
    result: str,
    fact: str,
    expected: str | None,
    found: str | None,
    source_code: str,
    explanation: str,
    action: bool,
    evidence: dict | None = None,
) -> LabelingFinding:
    source = source_by_code(source_code)
    row = LabelingFinding(
        organization_id=organization_id,
        labeling_assessment_id=assessment_id,
        rule_code=rule_code,
        result=result,
        fact=fact,
        expected_value=expected,
        found_value=found,
        source_code=source_code,
        source_locator=source["locator"],
        source_version=source["effective_from"],
        accessed_at=source["accessed_at"],
        explanation=explanation,
        action_needed=action,
    )
    session.add(row)
    session.flush()
    session.add(
        LabelingEvidence(
            organization_id=organization_id,
            labeling_finding_id=row.id,
            evidence_key=rule_code,
            detail=evidence or {},
        )
    )
    return row


def _compare(code: str, value: Decimal | None, threshold: Decimal) -> str:
    if value is None:
        return "insufficient_evidence"
    outcome = evaluate_parameters(
        {
            "type": "numeric_comparison",
            "input_key": code,
            "operator": "gte",
            "threshold": threshold,
        },
        EngineInputs(values={code: value}, evidence_keys=frozenset({code})),
    )
    mapped = _map_result(outcome.result)
    if mapped == "pass":
        return "high"
    if mapped == "fail":
        return "below"
    return mapped


def evaluate_dossier(session: Session, dossier: LabelingDossier, *, actor_user_id, profile) -> LabelingDossierVersion:
    version = session.get(FormulationVersion, dossier.formulation_version_id)
    if version is None or version.organization_id != dossier.organization_id:
        raise ValueError("recurso_nao_encontrado")
    recipe = session.get(Formulation, version.formulation_id)
    product = None if recipe is None else session.get(TechnicalProduct, recipe.technical_product_id)
    calculation = None
    if dossier.nutrition_calculation_id:
        calculation = session.get(NutritionCalculation, dossier.nutrition_calculation_id)
        if calculation is not None and calculation.organization_id != dossier.organization_id:
            calculation = None
    lines = project_declaration(
        session,
        calculation,
        category_code=None if profile is None else profile.regulatory_category_code,
        servings=None if profile is None else profile.servings_per_package,
    )
    by_code = {row["nutrient_code"]: row for row in lines}
    scope = front_labeling_scope(profile)
    number = int(
        session.scalar(
            select(func.max(LabelingDossierVersion.version_number)).where(
                LabelingDossierVersion.labeling_dossier_id == dossier.id
            )
        )
        or 0
    ) + 1
    snapshot = {
        "profile": profile_payload(profile),
        "formulation_version_id": str(version.id),
        "nutrition_calculation_id": None
        if calculation is None
        else str(calculation.id),
        "product": None if product is None else product.display_name,
    }
    digest = hashlib.sha256(
        json.dumps(snapshot, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()
    dossier_version = LabelingDossierVersion(
        organization_id=dossier.organization_id,
        labeling_dossier_id=dossier.id,
        version_number=number,
        status="evaluated",
        algorithm_name=ALGORITHM_NAME,
        algorithm_version=ALGORITHM_VERSION,
        content_hash=digest,
        snapshot=snapshot,
        created_by_user_id=actor_user_id,
    )
    session.add(dossier_version)
    session.flush()
    assessment = LabelingAssessment(
        organization_id=dossier.organization_id,
        labeling_dossier_version_id=dossier_version.id,
        status="evaluated",
        proposal_summary="Proposta técnica para revisão humana. Não é declaração de conformidade.",
    )
    session.add(assessment)
    session.flush()

    _finding(
        session,
        organization_id=dossier.organization_id,
        assessment_id=assessment.id,
        rule_code="applicability_complete",
        result="pass" if profile is not None and profile.completeness == "complete" else "insufficient_context",
        fact="perfil de aplicabilidade",
        expected="completo e confirmado",
        found=None if profile is None else profile.completeness,
        source_code="rdc-429-2020",
        explanation="Aplicabilidade não é inferida pelo nome do produto.",
        action=profile is None or profile.completeness != "complete",
    )
    if scope == "not_applicable":
        _finding(
            session,
            organization_id=dossier.organization_id,
            assessment_id=assessment.id,
            rule_code="fop_scope",
            result="not_applicable",
            fact="embalagem na ausência do consumidor",
            expected="comprovada a inaplicabilidade",
            found="não embalado na ausência do consumidor",
            source_code="rdc-429-2020",
            explanation="Inaplicabilidade da lupa somente com contexto comprovado.",
            action=False,
        )
    elif scope == "insufficient_context":
        _finding(
            session,
            organization_id=dossier.organization_id,
            assessment_id=assessment.id,
            rule_code="fop_scope",
            result="insufficient_context",
            fact="embalagem e canal",
            expected="contexto completo",
            found="contexto ausente",
            source_code="rdc-429-2020",
            explanation="Contexto ausente não gera isenção.",
            action=True,
        )

    sugars = (by_code.get("added_sugars") or {}).get("declared_per_100g")
    sat = (by_code.get("saturated_fat") or {}).get("declared_per_100g")
    sodium = (by_code.get("sodium") or {}).get("declared_per_100g")
    sugar_res = _compare("added_sugars", sugars, SOLID_ADDED_SUGARS_G) if scope == "applicable" else scope
    sat_res = _compare("saturated_fat", sat, SOLID_SATURATED_FAT_G) if scope == "applicable" else scope
    sod_res = _compare("sodium", sodium, SOLID_SODIUM_MG) if scope == "applicable" else scope
    high = [
        name
        for name, result in (
            ("açúcares adicionados", sugar_res),
            ("gordura saturada", sat_res),
            ("sódio", sod_res),
        )
        if result == "high"
    ]
    incomplete = any(
        result in {"insufficient_evidence", "insufficient_context"}
        for result in (sugar_res, sat_res, sod_res)
    )
    magnifier = None if incomplete or scope != "applicable" else bool(high)
    compared = {
        "added_sugars": None if sugars is None else format(sugars, "f"),
        "saturated_fat": None if sat is None else format(sat, "f"),
        "sodium": None if sodium is None else format(sodium, "f"),
        "thresholds": {
            "added_sugars": format(SOLID_ADDED_SUGARS_G, "f"),
            "saturated_fat": format(SOLID_SATURATED_FAT_G, "f"),
            "sodium": format(SOLID_SODIUM_MG, "f"),
        },
    }
    session.add(
        LabelingFrontOfPack(
            organization_id=dossier.organization_id,
            labeling_dossier_version_id=dossier_version.id,
            added_sugars_result=sugar_res,
            saturated_fat_result=sat_res,
            sodium_result=sod_res,
            magnifier_required=magnifier,
            nutrients_high=high,
            compared=compared,
        )
    )
    for code, result, found, threshold, locator in (
        ("fop_added_sugars", sugar_res, compared["added_sugars"], format(SOLID_ADDED_SUGARS_G, "f"), "Anexo XV IN 75"),
        ("fop_saturated_fat", sat_res, compared["saturated_fat"], format(SOLID_SATURATED_FAT_G, "f"), "Anexo XV IN 75"),
        ("fop_sodium", sod_res, compared["sodium"], format(SOLID_SODIUM_MG, "f"), "Anexo XV IN 75"),
    ):
        mapped = (
            "fail"
            if result == "high"
            else "pass"
            if result == "below"
            else result
        )
        _finding(
            session,
            organization_id=dossier.organization_id,
            assessment_id=assessment.id,
            rule_code=code,
            result=mapped,
            fact="limite da lupa para sólido/semissólido",
            expected=f">= {threshold} por 100 g implica lupa",
            found=found,
            source_code="in-75-2020",
            explanation=f"{locator}. Ausência de nutriente não presume ausência de lupa.",
            action=mapped in {"fail", "insufficient_evidence", "insufficient_context"},
            evidence=compared,
        )

    nutrition = LabelingNutritionCandidate(
        organization_id=dossier.organization_id,
        labeling_dossier_version_id=dossier_version.id,
        portion_g=None if (portion := get_portion(None if profile is None else profile.regulatory_category_code)) is None else portion["reference_g"],
        household_measure=None if portion is None else portion["household_measure"],
        servings_per_package=None if profile is None else profile.servings_per_package,
        footnotes=["Valores declarados são projeção regulatória, não certificado."],
    )
    session.add(nutrition)
    session.flush()
    for line in lines:
        session.add(
            LabelingNutritionLine(
                organization_id=dossier.organization_id,
                labeling_nutrition_candidate_id=nutrition.id,
                **line,
            )
        )
        if line["completeness"] != "complete":
            _finding(
                session,
                organization_id=dossier.organization_id,
                assessment_id=assessment.id,
                rule_code=f"nutrient_{line['nutrient_code']}",
                result="insufficient_evidence",
                fact=line["nutrient_code"],
                expected="valor técnico completo",
                found=None,
                source_code="in-75-2020",
                explanation="Nutriente obrigatório ausente nunca equivale a zero.",
                action=True,
            )

    for item in candidate_ingredients(session, version.id):
        session.add(
            LabelingIngredientCandidate(
                organization_id=dossier.organization_id,
                labeling_dossier_version_id=dossier_version.id,
                **item,
            )
        )
    for warning in candidate_warnings(session, version.id):
        session.add(
            LabelingWarningCandidate(
                organization_id=dossier.organization_id,
                labeling_dossier_version_id=dossier_version.id,
                **warning,
            )
        )
        _finding(
            session,
            organization_id=dossier.organization_id,
            assessment_id=assessment.id,
            rule_code=warning["code"],
            result=warning["result"],
            fact=warning["kind"],
            expected="evidência rastreável",
            found=warning["statement"],
            source_code="lei-10674-2003" if warning["kind"] == "gluten" else "rdc-727-2022",
            explanation="Advertência candidata exige revisão humana.",
            action=warning["result"] != "pass",
            evidence=warning["evidence"],
        )

    labels = {
        "denominacao_venda": "Denominação de venda",
        "lista_ingredientes": "Lista de ingredientes",
        "advertencias": "Advertências",
        "conteudo_liquido": "Conteúdo líquido",
        "origem": "Origem",
        "lote": "Lote",
        "prazo_validade": "Prazo de validade",
        "conservacao": "Conservação",
        "preparo": "Preparo e instruções de uso",
        "identificacao_responsavel": "Identificação do responsável",
        "registro": "Registro ou autorização",
    }
    prefilled = {
        "lista_ingredientes": "lista gerada do snapshot da formulação",
        "advertencias": "pendente",
        "conteudo_liquido": None if profile is None or profile.net_content_g is None else format(profile.net_content_g, "f"),
        "denominacao_venda": None if product is None else product.display_name,
    }
    for code in MANDATORY_ITEMS:
        value = prefilled.get(code)
        status = "filled" if value not in (None, "pendente") else "pending"
        session.add(
            LabelingMandatoryItem(
                organization_id=dossier.organization_id,
                labeling_dossier_version_id=dossier_version.id,
                code=code,
                label=labels[code],
                value=None if value == "pendente" else value,
                status=status,
            )
        )
        if status == "pending":
            _finding(
                session,
                organization_id=dossier.organization_id,
                assessment_id=assessment.id,
                rule_code=f"mandatory_{code}",
                result="insufficient_evidence",
                fact=labels[code],
                expected="dado informado",
                found=None,
                source_code="rdc-727-2022",
                explanation="Item obrigatório sem dado permanece pendente.",
                action=True,
            )

    payload = {
        "watermark": WATERMARKS["evaluated"],
        "title": None if product is None else product.display_name,
        "disclaimer": "Candidato para conferência. Não é rótulo final nem declaração de conformidade.",
        "hash": digest,
        "version_number": number,
    }
    session.add(
        LabelingLabelCandidate(
            organization_id=dossier.organization_id,
            labeling_dossier_version_id=dossier_version.id,
            watermark=WATERMARKS["evaluated"],
            payload=payload,
            payload_sha256=digest,
        )
    )
    dossier.status = "evaluated"
    dossier.row_version = int(dossier.row_version or 1) + 1
    session.flush()
    return dossier_version

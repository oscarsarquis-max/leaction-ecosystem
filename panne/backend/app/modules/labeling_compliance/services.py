"""Casos de uso HTTP. Sem certificação automática."""

from __future__ import annotations

import hashlib
import json
from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.formula_lab.models import Formulation, FormulationVersion
from app.modules.identity_organization.authorization import (
    PERMISSION_LABELING_CANDIDATE_EDIT,
    PERMISSION_LABELING_DOSSIER_CREATE,
    PERMISSION_LABELING_EVALUATE,
    PERMISSION_LABELING_INVALIDATE,
    PERMISSION_LABELING_READ,
    PERMISSION_LABELING_RENDER,
    PERMISSION_LABELING_REVIEW,
    PERMISSION_REGULATORY_SOURCE_READ,
    Principal,
    require_permission,
)
from app.modules.identity_organization.models import AuditEvent
from app.modules.labeling_compliance.applicability import classify_profile, profile_payload
from app.modules.labeling_compliance.evaluate import evaluate_dossier
from app.modules.labeling_compliance.models import (
    LabelingApplicabilityProfile,
    LabelingAssessment,
    LabelingCommand,
    LabelingDossier,
    LabelingDossierVersion,
    LabelingFinding,
    LabelingFrontOfPack,
    LabelingIngredientCandidate,
    LabelingInvalidation,
    LabelingLabelCandidate,
    LabelingMandatoryItem,
    LabelingNutritionCandidate,
    LabelingNutritionLine,
    LabelingReview,
    LabelingWarningCandidate,
)
from app.modules.labeling_compliance.portions import serialize_portions
from app.modules.labeling_compliance.sources import official_sources
from app.modules.production_planning.errors import (
    ConcurrencyError,
    IdempotencyConflictError,
    InvalidStateError,
    ValidationError,
)


def _org(principal: Principal) -> UUID:
    if principal.selected is None:
        raise ValidationError("organizacao_nao_selecionada")
    return principal.selected.organization_id


def _digest(payload: dict) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()


def _replay(session: Session, organization_id, key, command: str, payload: dict):
    if key is None:
        return None
    row = session.scalar(
        select(LabelingCommand).where(
            LabelingCommand.organization_id == organization_id,
            LabelingCommand.idempotency_key == key,
        )
    )
    if row is None:
        return None
    if row.command != command or row.payload_digest != _digest(payload):
        raise IdempotencyConflictError("idempotencia_conflito")
    return row


def _remember(session, *, organization_id, key, command, payload, resource_type, resource_id, actor_user_id):
    if key is None:
        return
    session.add(
        LabelingCommand(
            organization_id=organization_id,
            idempotency_key=key,
            command=command,
            payload_digest=_digest(payload),
            resource_type=resource_type,
            resource_id=resource_id,
            actor_user_id=actor_user_id,
        )
    )


def _dossier(session: Session, organization_id: UUID, dossier_id: UUID) -> LabelingDossier:
    row = session.get(LabelingDossier, dossier_id)
    if row is None or row.organization_id != organization_id:
        raise ValidationError("recurso_nao_encontrado")
    return row


def _profile(session: Session, dossier_id: UUID) -> LabelingApplicabilityProfile | None:
    return session.scalar(
        select(LabelingApplicabilityProfile)
        .where(LabelingApplicabilityProfile.labeling_dossier_id == dossier_id)
        .order_by(LabelingApplicabilityProfile.created_at.desc())
    )


def _latest_version(session: Session, dossier_id: UUID) -> LabelingDossierVersion | None:
    return session.scalar(
        select(LabelingDossierVersion)
        .where(LabelingDossierVersion.labeling_dossier_id == dossier_id)
        .order_by(LabelingDossierVersion.version_number.desc())
    )


def create_dossier(session: Session, principal: Principal, payload: dict, *, idempotency_key) -> LabelingDossier:
    require_permission(principal, PERMISSION_LABELING_DOSSIER_CREATE)
    organization_id = _org(principal)
    replay = _replay(session, organization_id, idempotency_key, "labeling.dossier.create", payload)
    if replay is not None:
        return _dossier(session, organization_id, replay.resource_id)
    version = session.get(FormulationVersion, payload["formulation_version_id"])
    if version is None or version.organization_id != organization_id:
        raise ValidationError("recurso_nao_encontrado")
    recipe = session.get(Formulation, version.formulation_id)
    row = LabelingDossier(
        organization_id=organization_id,
        establishment_id=payload.get("establishment_id"),
        technical_product_id=None if recipe is None else recipe.technical_product_id,
        formulation_id=version.formulation_id,
        formulation_version_id=version.id,
        nutrition_calculation_id=payload.get("nutrition_calculation_id"),
        created_by_user_id=principal.user_id,
    )
    session.add(row)
    session.flush()
    _remember(
        session,
        organization_id=organization_id,
        key=idempotency_key,
        command="labeling.dossier.create",
        payload=payload,
        resource_type="labeling_dossier",
        resource_id=row.id,
        actor_user_id=principal.user_id,
    )
    session.add(
        AuditEvent(
            organization_id=organization_id,
            actor_user_id=principal.user_id,
            event_type="labeling_dossier_created",
            aggregate_type="labeling_dossier",
            aggregate_id=row.id,
            payload={"certified": False},
        )
    )
    return row


def save_profile(session: Session, principal: Principal, dossier_id: UUID, payload: dict, *, expected_version: int | None):
    require_permission(principal, PERMISSION_LABELING_CANDIDATE_EDIT)
    dossier = _dossier(session, _org(principal), dossier_id)
    if expected_version is not None and int(dossier.row_version or 1) != expected_version:
        raise ConcurrencyError("versao_conflito")
    if dossier.status == "invalidated":
        raise InvalidStateError("transicao_invalida")
    data = dict(payload)
    if data.get("evaluation_date"):
        data["evaluation_date"] = date.fromisoformat(str(data["evaluation_date"]))
    for field in ("net_content_g", "package_area_cm2"):
        if data.get(field) not in (None, ""):
            data[field] = Decimal(str(data[field]))
    completeness = classify_profile(data | {"category_confirmed": bool(data.get("category_confirmed"))})
    row = LabelingApplicabilityProfile(
        organization_id=dossier.organization_id,
        labeling_dossier_id=dossier.id,
        jurisdiction=data.get("jurisdiction"),
        evaluation_date=data.get("evaluation_date"),
        packed_food=data.get("packed_food"),
        packed_away_from_consumer=data.get("packed_away_from_consumer"),
        packed_at_point_of_sale=data.get("packed_at_point_of_sale"),
        packed_on_request=data.get("packed_on_request"),
        same_establishment=data.get("same_establishment"),
        sales_channel=data.get("sales_channel"),
        food_service=data.get("food_service"),
        physical_state=data.get("physical_state"),
        ready_to_eat=data.get("ready_to_eat"),
        regulatory_category_code=data.get("regulatory_category_code"),
        category_confirmed=bool(data.get("category_confirmed")),
        package_area_cm2=data.get("package_area_cm2"),
        net_content_g=data.get("net_content_g"),
        servings_per_package=data.get("servings_per_package"),
        purpose=data.get("purpose"),
        destination_market=data.get("destination_market"),
        completeness=completeness,
    )
    session.add(row)
    dossier.establishment_id = data.get("establishment_id") or dossier.establishment_id
    dossier.row_version = int(dossier.row_version or 1) + 1
    session.flush()
    return row


def run_evaluation(session: Session, principal: Principal, dossier_id: UUID, *, idempotency_key, expected_version: int | None):
    require_permission(principal, PERMISSION_LABELING_EVALUATE)
    organization_id = _org(principal)
    dossier = _dossier(session, organization_id, dossier_id)
    if expected_version is not None and int(dossier.row_version or 1) != expected_version:
        raise ConcurrencyError("versao_conflito")
    if dossier.status == "invalidated":
        raise InvalidStateError("transicao_invalida")
    payload = {"dossier_id": str(dossier_id)}
    replay = _replay(session, organization_id, idempotency_key, "labeling.evaluate", payload)
    if replay is not None:
        return session.get(LabelingDossierVersion, replay.resource_id)
    version = evaluate_dossier(session, dossier, actor_user_id=principal.user_id, profile=_profile(session, dossier.id))
    _remember(
        session,
        organization_id=organization_id,
        key=idempotency_key,
        command="labeling.evaluate",
        payload=payload,
        resource_type="labeling_dossier_version",
        resource_id=version.id,
        actor_user_id=principal.user_id,
    )
    return version


def review_version(session: Session, principal: Principal, dossier_id: UUID, payload: dict, *, idempotency_key, expected_version: int | None):
    require_permission(principal, PERMISSION_LABELING_REVIEW)
    organization_id = _org(principal)
    dossier = _dossier(session, organization_id, dossier_id)
    if expected_version is not None and int(dossier.row_version or 1) != expected_version:
        raise ConcurrencyError("versao_conflito")
    version = _latest_version(session, dossier.id)
    if version is None:
        raise InvalidStateError("transicao_invalida")
    if version.status == "invalidated":
        raise InvalidStateError("transicao_invalida")
    decision = payload.get("decision")
    if decision not in {"accepted", "rejected", "needs_changes"}:
        raise ValidationError("contrato_invalido")
    replay = _replay(session, organization_id, idempotency_key, "labeling.review", payload)
    if replay is not None:
        return session.get(LabelingDossierVersion, replay.resource_id)
    session.add(
        LabelingReview(
            organization_id=organization_id,
            labeling_dossier_version_id=version.id,
            actor_user_id=principal.user_id,
            decision=decision,
            notes=payload.get("notes"),
        )
    )
    version.status = "reviewed"
    dossier.status = "reviewed"
    dossier.row_version = int(dossier.row_version or 1) + 1
    session.add(
        AuditEvent(
            organization_id=organization_id,
            actor_user_id=principal.user_id,
            event_type="labeling_reviewed",
            aggregate_type="labeling_dossier",
            aggregate_id=dossier.id,
            payload={"decision": decision, "certified": False, "conforme_anvisa": False},
        )
    )
    _remember(
        session,
        organization_id=organization_id,
        key=idempotency_key,
        command="labeling.review",
        payload=payload,
        resource_type="labeling_dossier_version",
        resource_id=version.id,
        actor_user_id=principal.user_id,
    )
    session.flush()
    return version


def edit_mandatory(session: Session, principal: Principal, dossier_id: UUID, items: list[dict], *, expected_version: int | None):
    require_permission(principal, PERMISSION_LABELING_CANDIDATE_EDIT)
    dossier = _dossier(session, _org(principal), dossier_id)
    if expected_version is not None and int(dossier.row_version or 1) != expected_version:
        raise ConcurrencyError("versao_conflito")
    version = _latest_version(session, dossier.id)
    if version is None or version.status in {"reviewed", "invalidated"}:
        raise InvalidStateError("transicao_invalida")
    index = {
        row.code: row
        for row in session.scalars(
            select(LabelingMandatoryItem).where(
                LabelingMandatoryItem.labeling_dossier_version_id == version.id
            )
        )
    }
    for item in items:
        row = index.get(item.get("code"))
        if row is None:
            raise ValidationError("recurso_nao_encontrado")
        if item.get("claim"):
            row.claim = True
            row.status = "manual_review_required"
            row.value = item.get("value")
            continue
        row.value = item.get("value")
        row.status = "filled" if item.get("value") else "pending"
    dossier.row_version = int(dossier.row_version or 1) + 1
    session.flush()
    return version


def invalidate_version(session: Session, principal: Principal, dossier_id: UUID, reason: str, *, expected_version: int | None):
    require_permission(principal, PERMISSION_LABELING_INVALIDATE)
    dossier = _dossier(session, _org(principal), dossier_id)
    if expected_version is not None and int(dossier.row_version or 1) != expected_version:
        raise ConcurrencyError("versao_conflito")
    version = _latest_version(session, dossier.id)
    if version is None:
        raise InvalidStateError("transicao_invalida")
    session.add(
        LabelingInvalidation(
            organization_id=dossier.organization_id,
            labeling_dossier_version_id=version.id,
            actor_user_id=principal.user_id,
            reason=reason,
        )
    )
    version.status = "invalidated"
    dossier.status = "invalidated"
    dossier.row_version = int(dossier.row_version or 1) + 1
    session.flush()
    return version


def list_dossiers(session: Session, principal: Principal) -> list[LabelingDossier]:
    require_permission(principal, PERMISSION_LABELING_READ)
    return list(
        session.scalars(
            select(LabelingDossier)
            .where(LabelingDossier.organization_id == _org(principal))
            .order_by(LabelingDossier.created_at.desc())
        )
    )


def get_dossier(session: Session, principal: Principal, dossier_id: UUID) -> LabelingDossier:
    require_permission(principal, PERMISSION_LABELING_READ)
    return _dossier(session, _org(principal), dossier_id)


def list_sources(principal: Principal) -> list[dict]:
    require_permission(principal, PERMISSION_REGULATORY_SOURCE_READ)
    return official_sources()


def list_portions(principal: Principal) -> list[dict]:
    require_permission(principal, PERMISSION_LABELING_READ)
    return serialize_portions()


def require_render(principal: Principal) -> None:
    require_permission(principal, PERMISSION_LABELING_RENDER)


def list_versions(session: Session, principal: Principal, dossier_id: UUID) -> list[LabelingDossierVersion]:
    require_permission(principal, PERMISSION_LABELING_READ)
    dossier = _dossier(session, _org(principal), dossier_id)
    return list(
        session.scalars(
            select(LabelingDossierVersion)
            .where(LabelingDossierVersion.labeling_dossier_id == dossier.id)
            .order_by(LabelingDossierVersion.version_number.desc())
        )
    )


def get_version(session: Session, principal: Principal, dossier_id: UUID, version_id: UUID) -> LabelingDossierVersion:
    require_permission(principal, PERMISSION_LABELING_READ)
    dossier = _dossier(session, _org(principal), dossier_id)
    row = session.get(LabelingDossierVersion, version_id)
    if row is None or row.organization_id != dossier.organization_id or row.labeling_dossier_id != dossier.id:
        raise ValidationError("recurso_nao_encontrado")
    return row


def list_assessments(session: Session, principal: Principal) -> list[LabelingAssessment]:
    require_permission(principal, PERMISSION_LABELING_READ)
    return list(
        session.scalars(
            select(LabelingAssessment)
            .where(LabelingAssessment.organization_id == _org(principal))
            .order_by(LabelingAssessment.created_at.desc())
        )
    )


def list_candidates(session: Session, principal: Principal) -> list[LabelingLabelCandidate]:
    require_permission(principal, PERMISSION_LABELING_READ)
    return list(
        session.scalars(
            select(LabelingLabelCandidate)
            .where(LabelingLabelCandidate.organization_id == _org(principal))
            .order_by(LabelingLabelCandidate.created_at.desc())
        )
    )


def version_bundle(session: Session, version: LabelingDossierVersion) -> dict:
    assessment = session.scalar(
        select(LabelingAssessment)
        .where(LabelingAssessment.labeling_dossier_version_id == version.id)
        .order_by(LabelingAssessment.created_at.desc())
    )
    findings = []
    if assessment is not None:
        findings = list(
            session.scalars(
                select(LabelingFinding)
                .where(LabelingFinding.labeling_assessment_id == assessment.id)
                .order_by(LabelingFinding.created_at)
            )
        )
    nutrition = session.scalar(
        select(LabelingNutritionCandidate).where(
            LabelingNutritionCandidate.labeling_dossier_version_id == version.id
        )
    )
    lines = []
    if nutrition is not None:
        lines = list(
            session.scalars(
                select(LabelingNutritionLine).where(
                    LabelingNutritionLine.labeling_nutrition_candidate_id == nutrition.id
                )
            )
        )
    return {
        "version": version,
        "assessment": assessment,
        "findings": findings,
        "nutrition": nutrition,
        "lines": lines,
        "front": session.scalar(
            select(LabelingFrontOfPack).where(
                LabelingFrontOfPack.labeling_dossier_version_id == version.id
            )
        ),
        "ingredients": list(
            session.scalars(
                select(LabelingIngredientCandidate)
                .where(LabelingIngredientCandidate.labeling_dossier_version_id == version.id)
                .order_by(LabelingIngredientCandidate.sequence)
            )
        ),
        "warnings": list(
            session.scalars(
                select(LabelingWarningCandidate).where(
                    LabelingWarningCandidate.labeling_dossier_version_id == version.id
                )
            )
        ),
        "mandatory": list(
            session.scalars(
                select(LabelingMandatoryItem).where(
                    LabelingMandatoryItem.labeling_dossier_version_id == version.id
                )
            )
        ),
        "candidate": session.scalar(
            select(LabelingLabelCandidate).where(
                LabelingLabelCandidate.labeling_dossier_version_id == version.id
            )
        ),
        "reviews": list(
            session.scalars(
                select(LabelingReview)
                .where(LabelingReview.labeling_dossier_version_id == version.id)
                .order_by(LabelingReview.created_at)
            )
        ),
    }


def compare_versions(
    session: Session, principal: Principal, dossier_id: UUID, left_id: UUID, right_id: UUID
) -> dict:
    return {
        "left": version_bundle(session, get_version(session, principal, dossier_id, left_id)),
        "right": version_bundle(session, get_version(session, principal, dossier_id, right_id)),
    }


def latest_bundle(session: Session, principal: Principal, dossier_id: UUID) -> dict:
    require_permission(principal, PERMISSION_LABELING_READ)
    dossier = _dossier(session, _org(principal), dossier_id)
    version = _latest_version(session, dossier.id)
    return {
        "dossier": dossier,
        "profile": _profile(session, dossier.id),
        "profile_payload": profile_payload(_profile(session, dossier.id)),
        "versions": list_versions(session, principal, dossier_id),
        "bundle": None if version is None else version_bundle(session, version),
    }

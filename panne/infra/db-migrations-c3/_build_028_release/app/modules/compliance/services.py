"""Serviços de governança. Sem HTTP, Bedrock, parecer ou publicação."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.compliance.applicability import decide_requirement, version_applies
from app.modules.compliance.constants import (
    ALGORITHM_NAME,
    ALGORITHM_VERSION,
    CITATION_ROLES,
    EDITABLE_VERSION_STATUSES,
    EVALUATION_TYPES,
    FRAMEWORK_SCOPES,
    NORMATIVE_FORCES,
    REGULATORY_DOMAINS,
    REQUIREMENT_REVIEW_STATUSES,
    REVIEW_DECISIONS,
    SEVERITIES,
    TARGET_TYPES,
)
from app.modules.compliance.engine import EngineInputs, evaluate_parameters
from app.modules.compliance.grounding import (
    ClassifiedSource,
    RegulatoryGroundingError,
    assert_linkable,
    can_found_current_obligation,
    source_snapshot,
)
from app.modules.compliance.models import (
    ComplianceAssessment,
    ComplianceEvidence,
    ComplianceFinding,
    ComplianceFramework,
    ComplianceFrameworkVersion,
    ComplianceProfile,
    ComplianceRequirement,
    ComplianceRequirementSource,
    ComplianceReview,
)
from app.modules.compliance.schemas import parse_applicability, parse_evaluation_params
from app.modules.formula_lab.models import FormulationVersion, TechnicalProduct
from app.modules.identity_organization.models import AuditEvent, Establishment, Organization
from app.modules.ingredient_catalog.models import IngredientVersion
from app.modules.knowledge_grounding.models import (
    KnowledgeFragment,
    KnowledgeSource,
    KnowledgeSourceVersion,
)


class ComplianceError(ValueError):
    """Operação de governança recusada."""


@dataclass(frozen=True)
class RequirementDraft:
    code: str
    title: str
    description: str
    regulatory_domain: str
    normative_force: str
    severity: str
    evaluation_type: str
    parameters: dict
    applicability: dict
    sequence: int
    review_status: str = "pending"


@dataclass(frozen=True)
class ProfileDraft:
    organization_id: UUID
    country: str
    activity: str
    reference_date: date
    establishment_id: UUID | None = None
    state: str | None = None
    municipality: str | None = None
    product_categories: tuple[str, ...] = ()
    sale_form: str | None = None
    packaging: str | None = None
    processes: tuple[str, ...] = ()
    equipment: tuple[str, ...] = ()
    extra_context: dict | None = None
    created_by_user_id: UUID | None = None


@dataclass(frozen=True)
class AssessmentCommand:
    organization_id: UUID
    profile: ComplianceProfile
    framework_version: ComplianceFrameworkVersion
    inputs: EngineInputs
    assessed_on: date | None = None
    target_type: str | None = None
    target_id: UUID | None = None
    created_by_user_id: UUID | None = None


def _audit(
    session: Session,
    *,
    organization_id,
    actor,
    event_type,
    aggregate_type,
    aggregate_id,
    payload,
):
    session.add(
        AuditEvent(
            organization_id=organization_id,
            actor_user_id=actor,
            event_type=event_type,
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            payload=payload,
        )
    )


def create_framework(
    session: Session,
    *,
    code: str,
    name: str,
    purpose: str,
    regulatory_domain: str,
    scope: str,
    organization_id: UUID | None = None,
    created_by_user_id: UUID | None = None,
) -> ComplianceFramework:
    if scope not in FRAMEWORK_SCOPES:
        raise ComplianceError("escopo de framework inválido")
    if regulatory_domain not in REGULATORY_DOMAINS:
        raise ComplianceError("domínio regulatório inválido")
    if scope == "global" and organization_id is not None:
        raise ComplianceError("framework global não tem organização dona")
    if scope == "organizational":
        if organization_id is None:
            raise ComplianceError("framework organizacional exige organização")
        organization = session.get(Organization, organization_id)
        if organization is None or organization.status != "active":
            raise ComplianceError("organização inválida")
    row = ComplianceFramework(
        organization_id=organization_id,
        code=code.strip(),
        name=name.strip(),
        purpose=purpose.strip(),
        regulatory_domain=regulatory_domain,
        scope=scope,
        status="draft",
        created_by_user_id=created_by_user_id,
    )
    session.add(row)
    session.flush()
    return row


def create_framework_version(
    session: Session,
    framework: ComplianceFramework,
    *,
    jurisdiction: str,
    authorities: list[str],
    effective_from: date,
    knowledge_cutoff_date: date,
    effective_until: date | None = None,
    created_by_user_id: UUID | None = None,
) -> ComplianceFrameworkVersion:
    if framework.status == "archived":
        raise ComplianceError("framework arquivado")
    if not jurisdiction.strip():
        raise ComplianceError("jurisdição obrigatória")
    if effective_until is not None and effective_until < effective_from:
        raise ComplianceError("vigência final anterior à inicial")
    current = session.scalar(
        select(func.max(ComplianceFrameworkVersion.version_number)).where(
            ComplianceFrameworkVersion.compliance_framework_id == framework.id
        )
    )
    row = ComplianceFrameworkVersion(
        organization_id=framework.organization_id,
        compliance_framework_id=framework.id,
        version_number=int(current or 0) + 1,
        jurisdiction=jurisdiction.strip(),
        authorities=list(authorities),
        effective_from=effective_from,
        effective_until=effective_until,
        status="draft",
        knowledge_cutoff_date=knowledge_cutoff_date,
        created_by_user_id=created_by_user_id,
    )
    session.add(row)
    session.flush()
    return row


def add_requirement(
    session: Session,
    version: ComplianceFrameworkVersion,
    draft: RequirementDraft,
) -> ComplianceRequirement:
    if version.status not in EDITABLE_VERSION_STATUSES:
        raise ComplianceError("versão não editável")
    if draft.regulatory_domain not in REGULATORY_DOMAINS:
        raise ComplianceError("domínio regulatório inválido")
    if draft.normative_force not in NORMATIVE_FORCES:
        raise ComplianceError("força normativa inválida")
    if draft.severity not in SEVERITIES:
        raise ComplianceError("severidade inválida")
    if draft.evaluation_type not in EVALUATION_TYPES:
        raise ComplianceError("tipo de avaliação inválido")
    if draft.review_status not in REQUIREMENT_REVIEW_STATUSES:
        raise ComplianceError("revisão de requisito inválida")
    parsed = parse_evaluation_params(draft.parameters)
    if parsed.type != draft.evaluation_type:
        raise ComplianceError("tipo de avaliação incompatível com parâmetros")
    parse_applicability(draft.applicability)
    row = ComplianceRequirement(
        organization_id=version.organization_id,
        compliance_framework_version_id=version.id,
        code=draft.code.strip(),
        title=draft.title.strip(),
        description=draft.description.strip(),
        regulatory_domain=draft.regulatory_domain,
        normative_force=draft.normative_force,
        severity=draft.severity,
        evaluation_type=draft.evaluation_type,
        parameters=draft.parameters,
        applicability=draft.applicability,
        review_status=draft.review_status,
        sequence=draft.sequence,
    )
    session.add(row)
    session.flush()
    return row


def link_requirement_source(
    session: Session,
    requirement: ComplianceRequirement,
    *,
    fragment: KnowledgeFragment,
    citation_role: str,
    organization_id: UUID | None,
    when: date,
    declared_class: str | None = None,
) -> ComplianceRequirementSource:
    version = session.get(ComplianceFrameworkVersion, requirement.compliance_framework_version_id)
    if version is None or version.status not in EDITABLE_VERSION_STATUSES:
        raise ComplianceError("versão não editável")
    if citation_role not in CITATION_ROLES:
        raise ComplianceError("papel de citação inválido")
    source_version = session.get(KnowledgeSourceVersion, fragment.knowledge_source_version_id)
    source = None
    if source_version is not None:
        source = session.get(KnowledgeSource, source_version.knowledge_source_id)
    if source is None or source_version is None:
        raise ComplianceError("fonte de conhecimento inválida")
    try:
        classified = assert_linkable(
            source,
            source_version,
            fragment,
            organization_id=organization_id,
            when=when,
            declared_class=declared_class,
            citation_role=citation_role,
        )
    except RegulatoryGroundingError as exc:
        raise ComplianceError(str(exc)) from exc
    row = ComplianceRequirementSource(
        organization_id=requirement.organization_id,
        compliance_requirement_id=requirement.id,
        knowledge_fragment_id=fragment.id,
        knowledge_source_version_id=source_version.id,
        citation_role=citation_role,
        normative_class=classified.normative_class,
        snapshot=source_snapshot(classified),
    )
    session.add(row)
    session.flush()
    return row


def _mandatory_sources_are_valid(
    session: Session,
    version: ComplianceFrameworkVersion,
) -> None:
    requirements = list(
        session.scalars(
            select(ComplianceRequirement)
            .where(ComplianceRequirement.compliance_framework_version_id == version.id)
            .order_by(ComplianceRequirement.sequence, ComplianceRequirement.code)
        )
    )
    for requirement in requirements:
        if requirement.normative_force != "mandatory":
            continue
        sources = list(
            session.scalars(
                select(ComplianceRequirementSource).where(
                    ComplianceRequirementSource.compliance_requirement_id == requirement.id,
                    ComplianceRequirementSource.citation_role == "foundation",
                )
            )
        )
        if not sources:
            raise ComplianceError("requisito obrigatório sem fonte válida")
        ok = False
        for row in sources:
            fragment = session.get(KnowledgeFragment, row.knowledge_fragment_id)
            source_version = session.get(KnowledgeSourceVersion, row.knowledge_source_version_id)
            source = session.get(KnowledgeSource, source_version.knowledge_source_id)
            classified = ClassifiedSource(source, source_version, fragment, row.normative_class)
            if can_found_current_obligation(
                classified,
                organization_id=version.organization_id,
                when=version.effective_from,
            ):
                ok = True
                break
        if not ok:
            raise ComplianceError("requisito obrigatório sem fonte válida")


def submit_framework_version(
    session: Session,
    version: ComplianceFrameworkVersion,
    *,
    actor_user_id: UUID,
) -> ComplianceFrameworkVersion:
    if version.status != "draft":
        raise ComplianceError("somente rascunho pode ser submetido")
    version.status = "pending_review"
    version.reviewed_at = None
    _audit(
        session,
        organization_id=version.organization_id,
        actor=actor_user_id,
        event_type="compliance_framework_version_submitted",
        aggregate_type="compliance_framework_version",
        aggregate_id=version.id,
        payload={"from": "draft", "to": "pending_review"},
    )
    session.flush()
    return version


def activate_framework_version(
    session: Session,
    version: ComplianceFrameworkVersion,
    *,
    actor_user_id: UUID,
    notes: str | None = None,
) -> ComplianceFrameworkVersion:
    if version.status != "pending_review":
        raise ComplianceError("ativação exige revisão humana pendente")
    _mandatory_sources_are_valid(session, version)
    previous = session.scalars(
        select(ComplianceFrameworkVersion).where(
            ComplianceFrameworkVersion.compliance_framework_id == version.compliance_framework_id,
            ComplianceFrameworkVersion.status == "active",
            ComplianceFrameworkVersion.id != version.id,
        )
    ).first()
    if previous is not None:
        previous.status = "superseded"
    version.status = "active"
    version.reviewed_at = datetime.now(timezone.utc)
    version.reviewed_by_user_id = actor_user_id
    version.activated_at = version.reviewed_at
    version.activated_by_user_id = actor_user_id
    version.review_notes = notes
    framework = session.get(ComplianceFramework, version.compliance_framework_id)
    if framework is not None and framework.status == "draft":
        framework.status = "active"
    _audit(
        session,
        organization_id=version.organization_id,
        actor=actor_user_id,
        event_type="compliance_framework_version_activated",
        aggregate_type="compliance_framework_version",
        aggregate_id=version.id,
        payload={"status": "active"},
    )
    session.flush()
    return version


def revoke_framework_version(
    session: Session,
    version: ComplianceFrameworkVersion,
    *,
    actor_user_id: UUID,
    notes: str,
) -> ComplianceFrameworkVersion:
    if version.status not in {"active", "pending_review"}:
        raise ComplianceError("versão não revogável")
    version.status = "revoked"
    version.review_notes = notes
    _audit(
        session,
        organization_id=version.organization_id,
        actor=actor_user_id,
        event_type="compliance_framework_version_revoked",
        aggregate_type="compliance_framework_version",
        aggregate_id=version.id,
        payload={"status": "revoked"},
    )
    session.flush()
    return version


def create_profile(session: Session, draft: ProfileDraft) -> ComplianceProfile:
    from app.modules.compliance.constants import ACTIVITIES

    organization = session.get(Organization, draft.organization_id)
    if organization is None or organization.status != "active":
        raise ComplianceError("organização inválida")
    if draft.activity not in ACTIVITIES:
        raise ComplianceError("atividade deve ser declarada; não é inferida pelo nome")
    if draft.establishment_id:
        establishment = session.get(Establishment, draft.establishment_id)
        if establishment is None or establishment.organization_id != draft.organization_id:
            raise ComplianceError("estabelecimento de outra organização")
    row = ComplianceProfile(
        organization_id=draft.organization_id,
        establishment_id=draft.establishment_id,
        country=draft.country.strip(),
        state=draft.state,
        municipality=draft.municipality,
        activity=draft.activity,
        product_categories=list(draft.product_categories),
        sale_form=draft.sale_form,
        packaging=draft.packaging,
        processes=list(draft.processes),
        equipment=list(draft.equipment),
        reference_date=draft.reference_date,
        extra_context=dict(draft.extra_context or {}),
        is_snapshot=False,
        created_by_user_id=draft.created_by_user_id,
    )
    session.add(row)
    session.flush()
    return row


def snapshot_profile(session: Session, profile: ComplianceProfile) -> ComplianceProfile:
    if profile.is_snapshot:
        return profile
    row = ComplianceProfile(
        organization_id=profile.organization_id,
        establishment_id=profile.establishment_id,
        country=profile.country,
        state=profile.state,
        municipality=profile.municipality,
        activity=profile.activity,
        product_categories=list(profile.product_categories),
        sale_form=profile.sale_form,
        packaging=profile.packaging,
        processes=list(profile.processes),
        equipment=list(profile.equipment),
        reference_date=profile.reference_date,
        extra_context=dict(profile.extra_context or {}),
        is_snapshot=True,
        source_profile_id=profile.id,
        frozen_at=datetime.now(timezone.utc),
        created_by_user_id=profile.created_by_user_id,
    )
    session.add(row)
    session.flush()
    return row


def _assert_target(session: Session, command: AssessmentCommand) -> None:
    if command.target_type is None and command.target_id is None:
        return
    if command.target_type not in TARGET_TYPES or command.target_id is None:
        raise ComplianceError("alvo de avaliação inválido")
    if command.target_type == "formulation_version":
        row = session.get(FormulationVersion, command.target_id)
    elif command.target_type == "ingredient_version":
        row = session.get(IngredientVersion, command.target_id)
    elif command.target_type == "establishment":
        row = session.get(Establishment, command.target_id)
    else:
        row = session.get(TechnicalProduct, command.target_id)
    if row is None or getattr(row, "organization_id", None) != command.organization_id:
        raise ComplianceError("alvo pertence a outra organização")


def _assert_framework_visible(version: ComplianceFrameworkVersion, organization_id: UUID) -> None:
    if version.organization_id not in {None, organization_id}:
        raise ComplianceError("framework de outra organização")


def evaluate_assessment(session: Session, command: AssessmentCommand) -> ComplianceAssessment:
    organization = session.get(Organization, command.organization_id)
    if organization is None or organization.status != "active":
        raise ComplianceError("organização inválida")
    if not command.profile.is_snapshot:
        raise ComplianceError("avaliação exige snapshot de perfil")
    if command.profile.organization_id != command.organization_id:
        raise ComplianceError("perfil de outra organização")
    if command.framework_version.status != "active":
        raise ComplianceError("somente versão ativa pode ser avaliada")
    _assert_framework_visible(command.framework_version, command.organization_id)
    _assert_target(session, command)
    assessed_on = command.assessed_on or command.profile.reference_date
    if not version_applies(command.framework_version, command.profile):
        raise ComplianceError("versão fora da jurisdição ou vigência do perfil")
    requirements = list(
        session.scalars(
            select(ComplianceRequirement)
            .where(
                ComplianceRequirement.compliance_framework_version_id
                == command.framework_version.id
            )
            .order_by(ComplianceRequirement.sequence, ComplianceRequirement.code)
        )
    )
    assessment = ComplianceAssessment(
        organization_id=command.organization_id,
        compliance_profile_id=command.profile.id,
        compliance_framework_version_id=command.framework_version.id,
        target_type=command.target_type,
        target_id=command.target_id,
        assessed_on=assessed_on,
        algorithm_name=ALGORITHM_NAME,
        algorithm_version=ALGORITHM_VERSION,
        status="evaluated",
        completeness="complete",
        created_by_user_id=command.created_by_user_id,
    )
    session.add(assessment)
    session.flush()
    findings_results: list[str] = []
    for requirement in requirements:
        decision = decide_requirement(
            requirement.applicability, command.profile, assessed_on=assessed_on
        )
        if decision.status == "insufficient_context":
            result = "insufficient_data"
            message = (
                "Contexto insuficiente; não convertido em não aplicável. " + decision.reason
            )
            used = {"applicability": decision.reason}
        elif decision.status == "not_applicable":
            result = "not_applicable"
            message = decision.reason
            used = {"applicability": decision.reason}
        else:
            outcome = evaluate_parameters(requirement.parameters, command.inputs)
            result = outcome.result
            message = outcome.message
            used = outcome.used_inputs
        findings_results.append(result)
        finding = ComplianceFinding(
            organization_id=command.organization_id,
            compliance_assessment_id=assessment.id,
            compliance_requirement_id=requirement.id,
            result=result,
            severity=requirement.severity,
            technical_message=message,
            input_snapshot=used,
            parameter_snapshot=dict(requirement.parameters),
            sequence=requirement.sequence,
        )
        session.add(finding)
        session.flush()
        if result != "not_applicable":
            session.add(
                ComplianceEvidence(
                    organization_id=command.organization_id,
                    compliance_finding_id=finding.id,
                    evidence_kind="technical",
                    origin="assessment_input",
                    value=str(used),
                    snapshot={"result": result, "no_legal_opinion": True},
                )
            )
    if any(item == "insufficient_data" for item in findings_results):
        if all(item in {"insufficient_data", "not_applicable"} for item in findings_results):
            assessment.completeness = "insufficient_context"
        else:
            assessment.completeness = "incomplete"
    session.flush()
    _audit(
        session,
        organization_id=command.organization_id,
        actor=command.created_by_user_id,
        event_type="compliance_assessment_evaluated",
        aggregate_type="compliance_assessment",
        aggregate_id=assessment.id,
        payload={
            "algorithm": ALGORITHM_NAME,
            "version": ALGORITHM_VERSION,
            "certified": False,
            "legal_opinion": False,
        },
    )
    return assessment


def review_assessment(
    session: Session,
    assessment: ComplianceAssessment,
    *,
    actor_user_id: UUID,
    decision: str,
    justification: str,
) -> ComplianceReview:
    if decision not in REVIEW_DECISIONS:
        raise ComplianceError("decisão de revisão inválida")
    if assessment.status == "invalidated" and decision != "revoked":
        raise ComplianceError("avaliação invalidada")
    row = ComplianceReview(
        organization_id=assessment.organization_id,
        compliance_assessment_id=assessment.id,
        actor_user_id=actor_user_id,
        decision=decision,
        justification=justification.strip(),
    )
    session.add(row)
    if decision == "accepted":
        assessment.status = "reviewed"
    elif decision == "rejected":
        assessment.status = "evaluated"
    elif decision == "needs_changes":
        assessment.status = "evaluated"
    elif decision == "revoked":
        assessment.status = "invalidated"
    _audit(
        session,
        organization_id=assessment.organization_id,
        actor=actor_user_id,
        event_type="compliance_assessment_reviewed",
        aggregate_type="compliance_assessment",
        aggregate_id=assessment.id,
        payload={"decision": decision},
    )
    session.flush()
    return row

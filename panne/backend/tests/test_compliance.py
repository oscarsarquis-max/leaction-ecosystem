from datetime import date
from decimal import Decimal
from inspect import getsource

import pytest
from app.modules.compliance.engine import EngineInputs, evaluate_parameters
from app.modules.compliance.models import ComplianceFinding
from app.modules.compliance.schemas import parse_evaluation_params
from app.modules.compliance.services import (
    AssessmentCommand,
    ComplianceError,
    ProfileDraft,
    RequirementDraft,
    activate_framework_version,
    add_requirement,
    create_framework,
    create_framework_version,
    create_profile,
    evaluate_assessment,
    link_requirement_source,
    review_assessment,
    snapshot_profile,
    submit_framework_version,
)
from app.modules.knowledge_grounding.ingest import (
    IngestRequest,
    ingest,
    release_global_source,
    review_source_version,
    revoke_source_version,
)
from pydantic import ValidationError
from sqlalchemy.orm import Session
from tests import helpers


def _official(
    session: Session,
    *,
    title: str,
    content: str,
    status: str = "in_force",
    effective_from: date | None = None,
):
    result = ingest(
        session,
        IngestRequest(
            source_kind="normative",
            authority_level="official",
            title=title,
            content=content,
            issuer_or_author="Autoridade fictícia de teste",
            jurisdiction="BR",
            regulatory_status=status,
            effective_from=effective_from or date(2020, 1, 1),
        ),
    )
    release_global_source(result.source)
    actor = helpers.user(session, f"{title[:12].replace(' ', '-')}@panne.test")
    review_source_version(result.version, decision="reviewed", reviewed_by_user_id=actor.id)
    session.flush()
    return result


def _numeric_req(code: str, sequence: int, *, activities=None) -> RequirementDraft:
    appl = {}
    if activities:
        appl["activities"] = list(activities)
    return RequirementDraft(
        code=code,
        title="Limiar fictício de teste",
        description="Requisito sintético. Não é norma real.",
        regulatory_domain="nutrition",
        normative_force="mandatory",
        severity="major",
        evaluation_type="numeric_comparison",
        parameters={
            "type": "numeric_comparison",
            "input_key": "sodium_mg",
            "operator": "lte",
            "threshold": "400",
        },
        applicability=appl,
        sequence=sequence,
        review_status="reviewed",
    )


def test_engine_schemas_and_missing_data_are_conservative() -> None:
    with pytest.raises(ValidationError):
        parse_evaluation_params({"type": "unknown_type"})
    with pytest.raises(ValidationError):
        parse_evaluation_params(
            {"type": "numeric_comparison", "input_key": "x", "operator": "lte", "extra": 1}
        )
    missing = evaluate_parameters(
        {
            "type": "numeric_comparison",
            "input_key": "sodium_mg",
            "operator": "lte",
            "threshold": "10",
        },
        EngineInputs({}, frozenset()),
    )
    assert missing.result == "insufficient_data"
    zero_is_not_implicit = evaluate_parameters(
        {
            "type": "numeric_comparison",
            "input_key": "sodium_mg",
            "operator": "lte",
            "threshold": "10",
        },
        EngineInputs({"sodium_mg": Decimal("0")}, frozenset()),
    )
    assert zero_is_not_implicit.result == "pass"


def test_framework_isolation_versioning_and_official_source(db_session: Session) -> None:
    org_a = helpers.org(db_session, "org-cg-a")
    org_b = helpers.org(db_session, "org-cg-b")
    actor = helpers.user(db_session, "gov-a@panne.test")
    official = _official(
        db_session, title="Norma fictícia NF-1", content="Texto sintético de fundamento."
    )
    framework = create_framework(
        db_session,
        code="CG-A",
        name="Pacote fictício A",
        purpose="teste",
        regulatory_domain="nutrition",
        scope="organizational",
        organization_id=org_a.id,
        created_by_user_id=actor.id,
    )
    version = create_framework_version(
        db_session,
        framework,
        jurisdiction="BR",
        authorities=["Autoridade fictícia"],
        effective_from=date(2024, 1, 1),
        knowledge_cutoff_date=date(2024, 1, 1),
        created_by_user_id=actor.id,
    )
    requirement = add_requirement(db_session, version, _numeric_req("N1", 1))
    link_requirement_source(
        db_session,
        requirement,
        fragment=official.fragments[0],
        citation_role="foundation",
        organization_id=org_a.id,
        when=date(2024, 6, 1),
    )
    submit_framework_version(db_session, version, actor_user_id=actor.id)
    activate_framework_version(db_session, version, actor_user_id=actor.id)
    assert version.status == "active"
    foreign = create_profile(
        db_session,
        ProfileDraft(
            organization_id=org_b.id,
            country="BR",
            activity="producer_processor",
            reference_date=date(2024, 6, 1),
        ),
    )
    snap = snapshot_profile(db_session, foreign)
    with pytest.raises(ComplianceError, match="outra organização"):
        evaluate_assessment(
            db_session,
            AssessmentCommand(
                organization_id=org_b.id,
                profile=snap,
                framework_version=version,
                inputs=EngineInputs({"sodium_mg": "100"}, frozenset()),
            ),
        )


def test_rejects_proposal_future_revoked_and_unlicensed_private(db_session: Session) -> None:
    org = helpers.org(db_session, "org-cg-src")
    actor = helpers.user(db_session, "gov-src@panne.test")
    framework = create_framework(
        db_session,
        code="CG-SRC",
        name="Fontes",
        purpose="teste",
        regulatory_domain="gmp",
        scope="organizational",
        organization_id=org.id,
    )
    version = create_framework_version(
        db_session,
        framework,
        jurisdiction="BR",
        authorities=["X"],
        effective_from=date(2024, 1, 1),
        knowledge_cutoff_date=date(2024, 1, 1),
    )
    requirement = add_requirement(db_session, version, _numeric_req("N1", 1))
    consultation = ingest(
        db_session,
        IngestRequest(
            source_kind="normative",
            authority_level="official",
            title="Minuta fictícia 2026",
            content="Consulta pública fictícia, não é obrigação.",
            issuer_or_author="Autoridade fictícia",
            jurisdiction="BR",
            regulatory_status="public_consultation",
        ),
    )
    release_global_source(consultation.source)
    review_source_version(consultation.version, decision="reviewed", reviewed_by_user_id=actor.id)
    with pytest.raises(ComplianceError, match="não fundamenta"):
        link_requirement_source(
            db_session,
            requirement,
            fragment=consultation.fragments[0],
            citation_role="foundation",
            organization_id=org.id,
            when=date(2024, 6, 1),
        )
    future = _official(
        db_session,
        title="Ato futuro fictício",
        content="Vigência futura fictícia.",
        status="future",
        effective_from=date(2090, 1, 1),
    )
    with pytest.raises(ComplianceError, match="não fundamenta"):
        link_requirement_source(
            db_session,
            requirement,
            fragment=future.fragments[0],
            citation_role="foundation",
            organization_id=org.id,
            when=date(2024, 6, 1),
        )
    revoked = _official(db_session, title="Ato revogado fictício", content="Revogado sintético.")
    revoke_source_version(revoked.version)
    with pytest.raises(ComplianceError, match="não fundamenta"):
        link_requirement_source(
            db_session,
            requirement,
            fragment=revoked.fragments[0],
            citation_role="foundation",
            organization_id=org.id,
            when=date(2024, 6, 1),
        )
    private = ingest(
        db_session,
        IngestRequest(
            source_kind="technical",
            authority_level="curated",
            title="Norma privada sem licença",
            content="Texto técnico privado fictício.",
            organization_id=org.id,
        ),
    )
    review_source_version(private.version, decision="reviewed", reviewed_by_user_id=actor.id)
    with pytest.raises(ComplianceError, match="não fundamenta"):
        link_requirement_source(
            db_session,
            requirement,
            fragment=private.fragments[0],
            citation_role="foundation",
            organization_id=org.id,
            when=date(2024, 6, 1),
        )


def test_applicability_and_deterministic_order(db_session: Session) -> None:
    org = helpers.org(db_session, "org-cg-app")
    actor = helpers.user(db_session, "gov-app@panne.test")
    official = _official(db_session, title="Norma fictícia NF-2", content="Fundamento sintético.")
    framework = create_framework(
        db_session,
        code="CG-APP",
        name="Aplicabilidade",
        purpose="teste",
        regulatory_domain="nutrition",
        scope="organizational",
        organization_id=org.id,
    )
    version = create_framework_version(
        db_session,
        framework,
        jurisdiction="BR",
        authorities=["X"],
        effective_from=date(2024, 1, 1),
        knowledge_cutoff_date=date(2024, 1, 1),
    )
    first = add_requirement(
        db_session, version, _numeric_req("Z9", 2, activities=["producer_processor"])
    )
    second = add_requirement(
        db_session, version, _numeric_req("A1", 1, activities=["producer_processor"])
    )
    for row in (first, second):
        link_requirement_source(
            db_session,
            row,
            fragment=official.fragments[0],
            citation_role="foundation",
            organization_id=org.id,
            when=date(2024, 6, 1),
        )
    submit_framework_version(db_session, version, actor_user_id=actor.id)
    activate_framework_version(db_session, version, actor_user_id=actor.id)
    service_profile = snapshot_profile(
        db_session,
        create_profile(
            db_session,
            ProfileDraft(
                organization_id=org.id,
                country="BR",
                activity="food_service",
                reference_date=date(2024, 6, 1),
            ),
        ),
    )
    service_result = evaluate_assessment(
        db_session,
        AssessmentCommand(
            organization_id=org.id,
            profile=service_profile,
            framework_version=version,
            inputs=EngineInputs({"sodium_mg": "100"}, frozenset()),
        ),
    )
    service_findings = list(
        db_session.query(ComplianceFinding)
        .filter_by(compliance_assessment_id=service_result.id)
        .order_by(ComplianceFinding.sequence)
    )
    assert [row.result for row in service_findings] == ["not_applicable", "not_applicable"]
    incomplete = snapshot_profile(
        db_session,
        create_profile(
            db_session,
            ProfileDraft(
                organization_id=org.id,
                country="BR",
                activity="producer_processor",
                reference_date=date(2024, 6, 1),
                extra_context={},
            ),
        ),
    )
    producer = snapshot_profile(
        db_session,
        create_profile(
            db_session,
            ProfileDraft(
                organization_id=org.id,
                country="BR",
                activity="producer_processor",
                reference_date=date(2024, 6, 1),
            ),
        ),
    )
    missing = evaluate_assessment(
        db_session,
        AssessmentCommand(
            organization_id=org.id,
            profile=producer,
            framework_version=version,
            inputs=EngineInputs({}, frozenset()),
        ),
    )
    assert missing.completeness == "insufficient_context"
    complete = evaluate_assessment(
        db_session,
        AssessmentCommand(
            organization_id=org.id,
            profile=producer,
            framework_version=version,
            inputs=EngineInputs({"sodium_mg": "100"}, frozenset()),
        ),
    )
    findings = list(
        db_session.query(ComplianceFinding)
        .filter_by(compliance_assessment_id=complete.id)
        .order_by(ComplianceFinding.sequence)
    )
    assert [row.sequence for row in findings] == [1, 2]
    assert {row.result for row in findings} == {"pass"}
    review = review_assessment(
        db_session,
        complete,
        actor_user_id=actor.id,
        decision="accepted",
        justification="revisão humana de teste; sem parecer jurídico",
    )
    assert review.decision == "accepted"
    assert complete.status == "reviewed"
    review_assessment(
        db_session,
        complete,
        actor_user_id=actor.id,
        decision="revoked",
        justification="revoga por novo evento",
    )
    assert complete.status == "invalidated"
    assert incomplete.id != producer.id


def test_immutability_and_no_side_effects(db_session: Session) -> None:
    org = helpers.org(db_session, "org-cg-im")
    actor = helpers.user(db_session, "gov-im@panne.test")
    official = _official(db_session, title="Norma fictícia NF-3", content="Fundamento sintético.")
    framework = create_framework(
        db_session,
        code="CG-IM",
        name="Imutável",
        purpose="teste",
        regulatory_domain="labeling",
        scope="organizational",
        organization_id=org.id,
    )
    version = create_framework_version(
        db_session,
        framework,
        jurisdiction="BR",
        authorities=["X"],
        effective_from=date(2024, 1, 1),
        knowledge_cutoff_date=date(2024, 1, 1),
    )
    requirement = add_requirement(db_session, version, _numeric_req("N1", 1))
    link_requirement_source(
        db_session,
        requirement,
        fragment=official.fragments[0],
        citation_role="foundation",
        organization_id=org.id,
        when=date(2024, 6, 1),
    )
    submit_framework_version(db_session, version, actor_user_id=actor.id)
    activate_framework_version(db_session, version, actor_user_id=actor.id)
    requirement.title = "alterado"
    with pytest.raises(Exception, match="append_only"):
        db_session.flush()
    blob = getsource(evaluate_assessment) + getsource(activate_framework_version)
    assert "publish_formulation_version" not in blob
    assert "calculate_nutrition" not in blob
    assert "boto3" not in blob


def test_licensed_private_standard_can_found(db_session: Session) -> None:
    org = helpers.org(db_session, "org-cg-lic")
    actor = helpers.user(db_session, "gov-lic@panne.test")
    licensed = ingest(
        db_session,
        IngestRequest(
            source_kind="technical",
            authority_level="curated",
            title="Norma técnica privada licenciada fictícia",
            content="Texto classificado e licenciado só para teste.",
            organization_id=org.id,
            license_or_usage_notes="licença de teste, uso interno",
            content_usage_kind="citation",
        ),
    )
    review_source_version(licensed.version, decision="reviewed", reviewed_by_user_id=actor.id)
    framework = create_framework(
        db_session,
        code="CG-LIC",
        name="Privada",
        purpose="teste",
        regulatory_domain="private_technical_standards",
        scope="organizational",
        organization_id=org.id,
    )
    version = create_framework_version(
        db_session,
        framework,
        jurisdiction="BR",
        authorities=["Entidade privada fictícia"],
        effective_from=date(2024, 1, 1),
        knowledge_cutoff_date=date(2024, 1, 1),
    )
    requirement = add_requirement(db_session, version, _numeric_req("N1", 1))
    link_requirement_source(
        db_session,
        requirement,
        fragment=licensed.fragments[0],
        citation_role="foundation",
        organization_id=org.id,
        when=date(2024, 6, 1),
    )
    submit_framework_version(db_session, version, actor_user_id=actor.id)
    activate_framework_version(db_session, version, actor_user_id=actor.id)
    assert version.status == "active"


def test_missing_context_is_not_not_applicable(db_session: Session) -> None:
    org = helpers.org(db_session, "org-cg-ctx")
    actor = helpers.user(db_session, "gov-ctx@panne.test")
    framework = create_framework(
        db_session,
        code="CG-CTX",
        name="Contexto",
        purpose="teste",
        regulatory_domain="sop",
        scope="organizational",
        organization_id=org.id,
    )
    version = create_framework_version(
        db_session,
        framework,
        jurisdiction="BR",
        authorities=["X"],
        effective_from=date(2024, 1, 1),
        knowledge_cutoff_date=date(2024, 1, 1),
    )
    add_requirement(
        db_session,
        version,
        RequirementDraft(
            code="CTX",
            title="Processo declarado",
            description="Requisito sintético de contexto.",
            regulatory_domain="sop",
            normative_force="recommended",
            severity="info",
            evaluation_type="boolean_condition",
            parameters={"type": "boolean_condition", "input_key": "ok", "expected": True},
            applicability={"required_context_keys": ["declared_process"]},
            sequence=1,
        ),
    )
    submit_framework_version(db_session, version, actor_user_id=actor.id)
    activate_framework_version(db_session, version, actor_user_id=actor.id)
    snap = snapshot_profile(
        db_session,
        create_profile(
            db_session,
            ProfileDraft(
                organization_id=org.id,
                country="BR",
                activity="hybrid",
                reference_date=date(2024, 6, 1),
            ),
        ),
    )
    result = evaluate_assessment(
        db_session,
        AssessmentCommand(
            organization_id=org.id,
            profile=snap,
            framework_version=version,
            inputs=EngineInputs({"ok": True}, frozenset()),
        ),
    )
    finding = (
        db_session.query(ComplianceFinding)
        .filter_by(compliance_assessment_id=result.id)
        .one()
    )
    assert finding.result == "insufficient_data"
    assert "não aplicável" in finding.technical_message
    assert result.completeness == "insufficient_context"


def test_activation_fails_without_official_source(db_session: Session) -> None:
    org = helpers.org(db_session, "org-cg-nosrc")
    actor = helpers.user(db_session, "gov-nosrc@panne.test")
    framework = create_framework(
        db_session,
        code="CG-NOS",
        name="Sem fonte",
        purpose="teste",
        regulatory_domain="labeling",
        scope="organizational",
        organization_id=org.id,
    )
    version = create_framework_version(
        db_session,
        framework,
        jurisdiction="BR",
        authorities=["X"],
        effective_from=date(2024, 1, 1),
        knowledge_cutoff_date=date(2024, 1, 1),
    )
    add_requirement(db_session, version, _numeric_req("N1", 1))
    submit_framework_version(db_session, version, actor_user_id=actor.id)
    with pytest.raises(ComplianceError, match="fonte válida"):
        activate_framework_version(db_session, version, actor_user_id=actor.id)


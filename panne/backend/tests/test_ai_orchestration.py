from decimal import Decimal
from inspect import getsource
from pathlib import Path
from uuid import uuid4

import pytest
from app.modules.ai_orchestration import orchestrate as orch_mod
from app.modules.ai_orchestration.fake_gateway import FakeModelGateway, default_proposal_payload
from app.modules.ai_orchestration.orchestrate import ProposalCommand, run_proposal
from app.modules.ai_orchestration.review import review_proposal
from app.modules.ai_orchestration.schema import ASSISTIVE_DISCLAIMER
from app.modules.formula_lab.models import FormulationVersion
from app.modules.knowledge_grounding.ingest import (
    IngestRequest,
    ingest,
    review_source_version,
)
from sqlalchemy.orm import Session
from tests import helpers


def _reviewed_technical(session: Session, organization, title: str, content: str):
    result = ingest(
        session,
        IngestRequest(
            source_kind="technical",
            authority_level="curated",
            title=title,
            content=content,
            organization_id=organization.id,
        ),
    )
    actor = helpers.user(session, f"rev-{title[:8]}@panne.test")
    review_source_version(result.version, decision="reviewed", reviewed_by_user_id=actor.id)
    session.flush()
    return result


def test_create_and_accept_materializes_draft_only(db_session: Session) -> None:
    organization = helpers.org(db_session, "org-ai-1")
    unit = helpers.gram(db_session)
    product = helpers.technical_product(db_session, organization, "PAO-AI")
    flour = helpers.published_ingredient(db_session, organization, unit, "FAR-AI")
    _reviewed_technical(
        db_session,
        organization,
        "Manual de pão",
        "Criar pão com farinha de trigo. A farinha de trigo é a base da massa do pão.",
    )
    actor = helpers.user(db_session, "aceite-ai@panne.test")
    result = run_proposal(
        db_session,
        ProposalCommand(
            organization_id=organization.id,
            objective="Criar pão com farinha de trigo",
            interaction_type="create_formulation_proposal",
            allowed_ingredient_version_ids=(flour.id,),
            technical_product_id=product.id,
            created_by_user_id=actor.id,
        ),
        FakeModelGateway(),
    )
    assert result.proposal is not None
    assert result.interaction.status == "completed"
    assert result.proposal.status == "draft"
    assert ASSISTIVE_DISCLAIMER in result.proposal.objective_summary
    version = review_proposal(
        db_session,
        result.proposal,
        actor_user_id=actor.id,
        decision="accepted",
        technical_product_id=product.id,
    )
    assert version is not None
    assert version.status == "draft"
    assert version.id != result.proposal.base_formulation_version_id
    again = review_proposal(
        db_session,
        result.proposal,
        actor_user_id=actor.id,
        decision="accepted",
        technical_product_id=product.id,
    )
    assert again is not None
    assert again.id == version.id


def test_adapt_preserves_base_version(db_session: Session) -> None:
    organization = helpers.org(db_session, "org-ai-ad")
    unit = helpers.gram(db_session)
    product = helpers.technical_product(db_session, organization, "PAO-AD")
    recipe = helpers.formulation(db_session, product, "REC-AD")
    base = helpers.formulation_version(db_session, recipe)
    flour = helpers.published_ingredient(db_session, organization, unit, "FAR-AD")
    helpers.formulation_item(db_session, base, flour, unit, 1, Decimal("80"))
    _reviewed_technical(
        db_session,
        organization,
        "Manual adaptação",
        "Adaptar a massa com farinha. A massa pode receber mais água.",
    )
    actor = helpers.user(db_session, "adapt-ai@panne.test")
    result = run_proposal(
        db_session,
        ProposalCommand(
            organization_id=organization.id,
            objective="Adaptar a massa com farinha",
            interaction_type="adapt_formulation_proposal",
            allowed_ingredient_version_ids=(flour.id,),
            base_formulation_version_id=base.id,
            created_by_user_id=actor.id,
        ),
        FakeModelGateway(),
    )
    assert result.proposal is not None
    assert result.proposal.proposal_type == "adapt"
    created = review_proposal(
        db_session, result.proposal, actor_user_id=actor.id, decision="accepted"
    )
    db_session.refresh(base)
    assert created is not None
    assert created.id != base.id
    assert created.status == "draft"
    assert base.status == "draft"
    assert db_session.get(FormulationVersion, base.id).notes is None


def test_unresolved_item_and_pending_accept_rejected(db_session: Session) -> None:
    organization = helpers.org(db_session, "org-ai-u")
    unit = helpers.gram(db_session)
    product = helpers.technical_product(db_session, organization, "PAO-U")
    flour = helpers.published_ingredient(db_session, organization, unit, "FAR-U")
    _reviewed_technical(
        db_session,
        organization,
        "Manual U",
        "Criar massa com farinha. Use farinha e água na massa.",
    )

    def unnamed(request):
        payload = default_proposal_payload(request)
        payload["items"][0]["ingredient_version_id"] = None
        payload["items"][0]["proposed_ingredient_name"] = "ingrediente desconhecido"
        return payload

    result = run_proposal(
        db_session,
        ProposalCommand(
            organization_id=organization.id,
            objective="Criar massa com farinha",
            interaction_type="create_formulation_proposal",
            allowed_ingredient_version_ids=(flour.id,),
            technical_product_id=product.id,
        ),
        FakeModelGateway(unnamed),
    )
    assert result.proposal is not None
    from app.modules.ai_orchestration.models import AiProposalItem

    item = db_session.query(AiProposalItem).one()
    assert item.resolution_status == "unresolved"
    actor = helpers.user(db_session, "pendente-ai@panne.test")
    with pytest.raises(Exception, match="pendentes"):
        review_proposal(
            db_session,
            result.proposal,
            actor_user_id=actor.id,
            decision="accepted",
            technical_product_id=product.id,
        )


def test_invented_ingredient_and_citation_rejected(db_session: Session) -> None:
    organization = helpers.org(db_session, "org-ai-inv")
    unit = helpers.gram(db_session)
    flour = helpers.published_ingredient(db_session, organization, unit, "FAR-INV")
    _reviewed_technical(
        db_session,
        organization,
        "Manual INV",
        "Criar pão com farinha. Farinha na massa do pão.",
    )

    def invented_id(request):
        payload = default_proposal_payload(request)
        payload["items"][0]["ingredient_version_id"] = str(uuid4())
        return payload

    result = run_proposal(
        db_session,
        ProposalCommand(
            organization_id=organization.id,
            objective="Criar pão com farinha",
            interaction_type="create_formulation_proposal",
            allowed_ingredient_version_ids=(flour.id,),
        ),
        FakeModelGateway(invented_id),
    )
    assert result.proposal is None
    assert result.interaction.status == "rejected_by_validation"

    def invented_cite(request):
        payload = default_proposal_payload(request)
        payload["cited_evidence_tokens"] = ["e999"]
        payload["items"][0]["cited_evidence_tokens"] = ["e999"]
        return payload

    result2 = run_proposal(
        db_session,
        ProposalCommand(
            organization_id=organization.id,
            objective="Criar pão com farinha",
            interaction_type="create_formulation_proposal",
            allowed_ingredient_version_ids=(flour.id,),
        ),
        FakeModelGateway(invented_cite),
    )
    assert result2.proposal is None
    assert "citação inventada" in (result2.error_code or "")


def test_rejected_source_and_foreign_org_excluded(db_session: Session) -> None:
    organization = helpers.org(db_session, "org-ai-iso")
    other = helpers.org(db_session, "org-ai-iso-b")
    unit = helpers.gram(db_session)
    flour = helpers.published_ingredient(db_session, organization, unit, "FAR-ISO")
    rejected = ingest(
        db_session,
        IngestRequest(
            source_kind="technical",
            authority_level="curated",
            title="Manual rejeitado",
            content="Texto rejeitado sobre pão.",
            organization_id=organization.id,
        ),
    )
    actor = helpers.user(db_session, "rej-ai@panne.test")
    review_source_version(rejected.version, decision="rejected", reviewed_by_user_id=actor.id)
    foreign = ingest(
        db_session,
        IngestRequest(
            source_kind="internal_document",
            authority_level="user_provided",
            title="Caderno alheio",
            content="Procedimento privado de pão da outra casa.",
            organization_id=other.id,
        ),
    )
    review_source_version(foreign.version, decision="reviewed", reviewed_by_user_id=actor.id)
    db_session.flush()
    result = run_proposal(
        db_session,
        ProposalCommand(
            organization_id=organization.id,
            objective="pão procedimento privado",
            interaction_type="create_formulation_proposal",
            allowed_ingredient_version_ids=(flour.id,),
        ),
        FakeModelGateway(),
    )
    assert result.error_code == "grounding_insufficient"


def test_invalid_values_and_immutability(db_session: Session) -> None:
    organization = helpers.org(db_session, "org-ai-val")
    unit = helpers.gram(db_session)
    flour = helpers.published_ingredient(db_session, organization, unit, "FAR-VAL")
    _reviewed_technical(
        db_session, organization, "Manual VAL", "Criar pão com farinha. Farinha e água no pão."
    )

    def negative(request):
        payload = default_proposal_payload(request)
        payload["items"][0]["net_quantity_g"] = "-1"
        return payload

    result = run_proposal(
        db_session,
        ProposalCommand(
            organization_id=organization.id,
            objective="Criar pão com farinha",
            interaction_type="create_formulation_proposal",
            allowed_ingredient_version_ids=(flour.id,),
        ),
        FakeModelGateway(negative),
    )
    assert result.proposal is None
    good = run_proposal(
        db_session,
        ProposalCommand(
            organization_id=organization.id,
            objective="Criar pão com farinha",
            interaction_type="create_formulation_proposal",
            allowed_ingredient_version_ids=(flour.id,),
        ),
        FakeModelGateway(),
    )
    assert good.proposal is not None
    good.proposal.title = "alterado"
    with pytest.raises(Exception, match="append_only"):
        db_session.flush()


def test_domain_does_not_import_boto3() -> None:
    blob = (
        getsource(orch_mod)
        + Path("app/modules/ai_orchestration/models.py").read_text(encoding="utf-8")
        + Path("app/modules/ai_orchestration/review.py").read_text(encoding="utf-8")
        + Path("app/modules/ai_orchestration/schema.py").read_text(encoding="utf-8")
    )
    assert "import boto3" not in blob
    assert "bedrock-mantle" not in blob

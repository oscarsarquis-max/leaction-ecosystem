"""Revisão humana e materialização em draft. Sem endpoint e sem publicação."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.ai_orchestration.models import (
    AiProposal,
    AiProposalCitation,
    AiProposalItem,
    AiProposalProcessStep,
    AiProposalReview,
)
from app.modules.ai_orchestration.orchestrate import OrchestrationError
from app.modules.formula_lab.models import (
    Formulation,
    FormulationItem,
    FormulationVersion,
    ProcessStep,
    TechnicalProduct,
)
from app.modules.identity_organization.models import AuditEvent
from app.modules.ingredient_catalog.models import MeasurementUnit


def _gram(session: Session) -> MeasurementUnit:
    unit = session.scalars(select(MeasurementUnit).where(MeasurementUnit.code == "g")).first()
    if unit is None or unit.dimension != "mass":
        raise OrchestrationError("unidade de massa g ausente")
    return unit


def _next_version_number(session: Session, formulation_id) -> int:
    current = session.scalar(
        select(func.max(FormulationVersion.version_number)).where(
            FormulationVersion.formulation_id == formulation_id
        )
    )
    return int(current or 0) + 1


def _materialize(
    session: Session,
    proposal: AiProposal,
    actor_user_id,
    technical_product_id=None,
) -> FormulationVersion:
    items = list(
        session.scalars(
            select(AiProposalItem)
            .where(AiProposalItem.ai_proposal_id == proposal.id)
            .order_by(AiProposalItem.sequence)
        )
    )
    if not items:
        raise OrchestrationError("proposta sem itens")
    for item in items:
        if item.resolution_status != "resolved":
            raise OrchestrationError("aceitação recusa itens pendentes")
        if item.ingredient_version_id is None or item.net_quantity_g is None:
            raise OrchestrationError("aceitação recusa itens pendentes")
    citations = list(
        session.scalars(
            select(AiProposalCitation).where(AiProposalCitation.ai_proposal_id == proposal.id)
        )
    )
    if any(not row.knowledge_fragment_id or not row.grounding_citation_id for row in citations):
        raise OrchestrationError("citação inválida")
    gram = _gram(session)
    if proposal.proposal_type == "adapt":
        if proposal.base_formulation_version_id is None:
            raise OrchestrationError("adaptação exige versão-base")
        base = session.get(FormulationVersion, proposal.base_formulation_version_id)
        if base is None or base.organization_id != proposal.organization_id:
            raise OrchestrationError("versão-base inválida")
        version = FormulationVersion(
            organization_id=proposal.organization_id,
            formulation_id=base.formulation_id,
            version_number=_next_version_number(session, base.formulation_id),
            status="draft",
            notes="Sugestão assistiva materializada; não publicada e não aprovada.",
            created_by_user_id=actor_user_id,
        )
        session.add(version)
        session.flush()
    else:
        if proposal.base_formulation_version_id is not None:
            raise OrchestrationError("criação não deve apontar versão-base")
        if technical_product_id is None:
            raise OrchestrationError("criação exige produto técnico")
        product = session.get(TechnicalProduct, technical_product_id)
        if product is None or product.organization_id != proposal.organization_id:
            raise OrchestrationError("produto técnico inválido")
        recipe = Formulation(
            organization_id=proposal.organization_id,
            technical_product_id=product.id,
            code=f"AI-{proposal.id.hex[:8]}",
            display_name=proposal.title,
            status="development",
        )
        session.add(recipe)
        session.flush()
        version = FormulationVersion(
            organization_id=proposal.organization_id,
            formulation_id=recipe.id,
            version_number=1,
            status="draft",
            notes="Sugestão assistiva materializada; não publicada e não aprovada.",
            created_by_user_id=actor_user_id,
        )
        session.add(version)
        session.flush()
    if version.status != "draft":
        raise OrchestrationError("materialização só cria draft")
    for item in items:
        session.add(
            FormulationItem(
                organization_id=proposal.organization_id,
                formulation_version_id=version.id,
                ingredient_version_id=item.ingredient_version_id,
                sequence=item.sequence,
                net_quantity=item.net_quantity_g,
                measurement_unit_id=gram.id,
                correction_factor=item.correction_factor or Decimal("1"),
                is_flour_basis=item.is_flour_basis,
                role=item.role,
                notes=item.rationale,
            )
        )
    for step in session.scalars(
        select(AiProposalProcessStep)
        .where(AiProposalProcessStep.ai_proposal_id == proposal.id)
        .order_by(AiProposalProcessStep.sequence)
    ):
        session.add(
            ProcessStep(
                organization_id=proposal.organization_id,
                formulation_version_id=version.id,
                sequence=step.sequence,
                title=step.title,
                instructions=step.instructions,
                duration_seconds=step.duration_seconds,
                temperature_celsius=step.temperature_celsius,
            )
        )
    proposal.status = "accepted"
    proposal.materialized_formulation_version_id = version.id
    session.add(
        AuditEvent(
            organization_id=proposal.organization_id,
            actor_user_id=actor_user_id,
            event_type="ai_proposal_materialized",
            aggregate_type="ai_proposal",
            aggregate_id=proposal.id,
            payload={
                "formulation_version_id": str(version.id),
                "proposal_type": proposal.proposal_type,
                "published": False,
                "approved": False,
            },
        )
    )
    session.flush()
    return version


def review_proposal(
    session: Session,
    proposal: AiProposal,
    *,
    actor_user_id,
    decision: str,
    notes: str | None = None,
    technical_product_id=None,
) -> FormulationVersion | None:
    if decision not in {"accepted", "rejected", "revision_requested"}:
        raise OrchestrationError("decisão inválida")
    if proposal.status == "accepted" and proposal.materialized_formulation_version_id:
        return session.get(FormulationVersion, proposal.materialized_formulation_version_id)
    if proposal.status not in {"draft", "accepted"}:
        raise OrchestrationError("proposta não revisável")
    session.add(
        AiProposalReview(
            organization_id=proposal.organization_id,
            ai_proposal_id=proposal.id,
            actor_user_id=actor_user_id,
            decision=decision,
            notes=notes,
        )
    )
    session.flush()
    if decision == "rejected":
        proposal.status = "rejected"
        session.flush()
        return None
    if decision == "revision_requested":
        return None
    return _materialize(
        session, proposal, actor_user_id, technical_product_id=technical_product_id
    )

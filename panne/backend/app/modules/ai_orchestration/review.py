"""Revisão humana e materialização em draft. Sem endpoint e sem publicação."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.ai_orchestration.models import (
    AiProposal,
    AiProposalChange,
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
    FormulationVersionRecipeReference,
    ProcessStep,
    RecipeReference,
    TechnicalProduct,
)
from app.modules.formula_lab.version_references import attach_reference_to_version
from app.modules.identity_organization.models import AuditEvent
from app.modules.ingredient_catalog.models import MeasurementUnit
from app.modules.knowledge_grounding.models import KnowledgeFragment, KnowledgeSourceVersion


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


def _changes(session: Session, proposal_id) -> list[AiProposalChange]:
    return list(
        session.scalars(
            select(AiProposalChange).where(AiProposalChange.ai_proposal_id == proposal_id)
        )
    )


def _accepted_items(session: Session, proposal: AiProposal) -> list[AiProposalItem]:
    items = list(
        session.scalars(
            select(AiProposalItem)
            .where(AiProposalItem.ai_proposal_id == proposal.id)
            .order_by(AiProposalItem.sequence)
        )
    )
    if not items:
        raise OrchestrationError("proposta sem itens")
    rejected = {
        row.change_key
        for row in _changes(session, proposal.id)
        if row.decision == "rejected"
    }
    kept: list[AiProposalItem] = []
    for item in items:
        if item.resolution_status != "resolved":
            raise OrchestrationError("aceitação recusa itens pendentes")
        if item.ingredient_version_id is None or item.net_quantity_g is None:
            raise OrchestrationError("aceitação recusa itens pendentes")
        key = f"added:{item.ingredient_version_id}"
        changed = f"changed:{item.ingredient_version_id}"
        if key in rejected or changed in rejected:
            continue
        kept.append(item)
    if not kept:
        raise OrchestrationError("nenhuma alteração aceita")
    return kept


def _link_evidence(session: Session, proposal: AiProposal, version: FormulationVersion) -> None:
    selected = (proposal.guided_input or {}).get("selected_reference_ids") or []
    for raw_id in selected:
        reference = session.get(RecipeReference, raw_id)
        if reference is None or reference.organization_id != proposal.organization_id:
            continue
        attach_reference_to_version(session, version, reference, role="source")
    for citation in session.scalars(
        select(AiProposalCitation).where(AiProposalCitation.ai_proposal_id == proposal.id)
    ):
        fragment = session.get(KnowledgeFragment, citation.knowledge_fragment_id)
        if fragment is None:
            continue
        source_version = session.get(KnowledgeSourceVersion, fragment.knowledge_source_version_id)
        already = session.scalar(
            select(FormulationVersionRecipeReference).where(
                FormulationVersionRecipeReference.formulation_version_id == version.id,
                FormulationVersionRecipeReference.knowledge_fragment_id == fragment.id,
            )
        )
        if already is not None:
            continue
        session.add(
            FormulationVersionRecipeReference(
                organization_id=proposal.organization_id,
                formulation_version_id=version.id,
                recipe_reference_id=None,
                knowledge_source_version_id=None if source_version is None else source_version.id,
                knowledge_fragment_id=fragment.id,
                role="source",
                source_version_label=None if source_version is None else source_version.version_label,
                locator_type=fragment.locator_type,
                locator_value=fragment.locator_value,
                content_hash=fragment.content_hash,
                accessed_at=None if source_version is None else source_version.retrieved_at,
                snapshot={
                    "heading": fragment.heading,
                    "locator": f"{fragment.locator_type}:{fragment.locator_value}",
                },
            )
        )


def _materialize(
    session: Session,
    proposal: AiProposal,
    actor_user_id,
    technical_product_id=None,
) -> FormulationVersion:
    if proposal.status == "materialized" and proposal.materialized_formulation_version_id:
        version = session.get(FormulationVersion, proposal.materialized_formulation_version_id)
        if version is not None:
            return version
    if proposal.status not in {"draft", "accepted", "awaiting_review"}:
        raise OrchestrationError("proposta não materializável")
    items = _accepted_items(session, proposal)
    pending_changes = [
        row
        for row in _changes(session, proposal.id)
        if row.decision == "pending" and row.change_kind == "unresolved"
    ]
    if pending_changes:
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
        frozen_status = base.status
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
        if session.get(FormulationVersion, base.id).status != frozen_status:
            raise OrchestrationError("versão-base inválida")
    else:
        if proposal.base_formulation_version_id is not None:
            raise OrchestrationError("criação não deve apontar versão-base")
        product = None
        if technical_product_id is not None:
            product = session.get(TechnicalProduct, technical_product_id)
            if product is None or product.organization_id != proposal.organization_id:
                raise OrchestrationError("produto técnico inválido")
        if product is None:
            product = TechnicalProduct(
                organization_id=proposal.organization_id,
                code=f"AI-P-{proposal.id.hex[:8]}",
                display_name=proposal.title,
                status="development",
            )
            session.add(product)
            session.flush()
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
    _link_evidence(session, proposal, version)
    proposal.status = "accepted"
    session.flush()
    proposal.materialized_formulation_version_id = version.id
    proposal.status = "materialized"
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
                "ingredient_created": False,
                "compliance_declared": False,
                "production_commanded": False,
            },
        )
    )
    session.flush()
    return version


def decide_changes(
    session: Session,
    proposal: AiProposal,
    *,
    decisions: list[dict],
    actor_user_id,
) -> list[AiProposalChange]:
    if proposal.status not in {"draft", "awaiting_review", "accepted"}:
        raise OrchestrationError("proposta não revisável")
    if proposal.status == "materialized" or proposal.materialized_formulation_version_id:
        raise OrchestrationError("proposta já materializada")
    index = {row.change_key: row for row in _changes(session, proposal.id)}
    accepted: list[str] = []
    rejected: list[str] = []
    for item in decisions:
        key = str(item.get("change_key") or "")
        decision = str(item.get("decision") or "")
        row = index.get(key)
        if row is None:
            raise OrchestrationError("alteração inexistente")
        if decision not in {"accepted", "rejected"}:
            raise OrchestrationError("decisão inválida")
        row.decision = decision
        row.notes = item.get("notes")
        if decision == "accepted":
            accepted.append(key)
        else:
            rejected.append(key)
    proposal.accepted_changes = accepted
    proposal.rejected_changes = rejected
    proposal.human_decisions = [
        {"actor_user_id": str(actor_user_id), "accepted": accepted, "rejected": rejected}
    ]
    proposal.row_version = int(proposal.row_version or 1) + 1
    session.flush()
    return list(index.values())


def materialize_proposal(
    session: Session,
    proposal: AiProposal,
    *,
    actor_user_id,
    technical_product_id=None,
) -> FormulationVersion:
    if proposal.materialized_formulation_version_id:
        version = session.get(FormulationVersion, proposal.materialized_formulation_version_id)
        if version is not None:
            return version
    if proposal.status not in {"draft", "accepted", "awaiting_review"}:
        raise OrchestrationError("proposta não materializável")
    return _materialize(
        session, proposal, actor_user_id, technical_product_id=technical_product_id
    )


def review_proposal(
    session: Session,
    proposal: AiProposal,
    *,
    actor_user_id,
    decision: str,
    notes: str | None = None,
    technical_product_id=None,
    materialize: bool = True,
) -> FormulationVersion | None:
    if decision not in {"accepted", "rejected", "revision_requested", "cancelled"}:
        raise OrchestrationError("decisão inválida")
    if proposal.status == "materialized" and proposal.materialized_formulation_version_id:
        return session.get(FormulationVersion, proposal.materialized_formulation_version_id)
    if proposal.status not in {"draft", "accepted", "awaiting_review"}:
        raise OrchestrationError("proposta não revisável")
    session.add(
        AiProposalReview(
            organization_id=proposal.organization_id,
            ai_proposal_id=proposal.id,
            actor_user_id=actor_user_id,
            decision="accepted" if decision == "accepted" else (
                "rejected" if decision in {"rejected", "cancelled"} else "revision_requested"
            ),
            notes=notes,
        )
    )
    session.flush()
    if decision in {"rejected", "cancelled"}:
        proposal.status = "cancelled" if decision == "cancelled" else "rejected"
        session.flush()
        return None
    if decision == "revision_requested":
        return None
    if proposal.status == "draft":
        proposal.status = "accepted"
        session.flush()
    if not materialize:
        return None
    return _materialize(
        session, proposal, actor_user_id, technical_product_id=technical_product_id
    )

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.ai_orchestration.models import (
    AiInteraction,
    AiProposal,
    AiProposalChange,
    AiProposalCitation,
    AiProposalItem,
    AiProposalProcessStep,
)
from app.modules.formula_lab.models import FormulationVersion
from app.modules.knowledge_grounding.models import (
    GroundingQuery,
    GroundingResult,
    KnowledgeFragment,
    KnowledgeSource,
)


def _status_label(status: str) -> str:
    labels = {
        "requested": "solicitado",
        "retrieving_evidence": "buscando evidências",
        "grounding_insufficient": "grounding insuficiente",
        "generating": "gerando",
        "validation_failed": "validação falhou",
        "awaiting_review": "aguardando revisão",
        "draft": "aguardando revisão",
        "accepted": "aceito",
        "rejected": "rejeitado",
        "materialized": "materializado",
        "cancelled": "cancelado",
        "expired": "expirado",
        "invalid": "inválido",
    }
    return labels.get(status, status)


def proposal_card(row: AiProposal, interaction: AiInteraction | None = None) -> dict:
    return {
        "id": str(row.id),
        "intent": row.intent or ("adapt_recipe" if row.proposal_type == "adapt" else "create_recipe"),
        "proposal_type": row.proposal_type,
        "title": row.title,
        "objective_summary": row.objective_summary,
        "status": row.status,
        "status_label": _status_label(row.status),
        "assisted_by_ai": True,
        "base_formulation_version_id": (
            None
            if row.base_formulation_version_id is None
            else str(row.base_formulation_version_id)
        ),
        "materialized_formulation_version_id": (
            None
            if row.materialized_formulation_version_id is None
            else str(row.materialized_formulation_version_id)
        ),
        "warnings": row.warnings,
        "missing_data": row.missing_data,
        "row_version": row.row_version,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "latency_ms": None if interaction is None else interaction.latency_ms,
        "input_token_count": None if interaction is None else interaction.input_token_count,
        "output_token_count": None if interaction is None else interaction.output_token_count,
        "model_id": None if interaction is None else interaction.model_id,
    }


def proposal_detail(session: Session, row: AiProposal) -> dict:
    interaction = session.get(AiInteraction, row.ai_interaction_id)
    items = list(
        session.scalars(
            select(AiProposalItem)
            .where(AiProposalItem.ai_proposal_id == row.id)
            .order_by(AiProposalItem.sequence)
        )
    )
    steps = list(
        session.scalars(
            select(AiProposalProcessStep)
            .where(AiProposalProcessStep.ai_proposal_id == row.id)
            .order_by(AiProposalProcessStep.sequence)
        )
    )
    citations = list(
        session.scalars(
            select(AiProposalCitation).where(AiProposalCitation.ai_proposal_id == row.id)
        )
    )
    changes = list(
        session.scalars(
            select(AiProposalChange).where(AiProposalChange.ai_proposal_id == row.id)
        )
    )
    materialized = None
    if row.materialized_formulation_version_id:
        version = session.get(FormulationVersion, row.materialized_formulation_version_id)
        if version is not None:
            materialized = {
                "formulation_id": str(version.formulation_id),
                "version_id": str(version.id),
                "status": version.status,
            }
    return {
        **proposal_card(row, interaction),
        "guided_input": row.guided_input,
        "constraints": row.constraints,
        "assumptions": row.assumptions,
        "unresolved_questions": row.unresolved_questions,
        "human_decisions": row.human_decisions,
        "accepted_changes": row.accepted_changes,
        "rejected_changes": row.rejected_changes,
        "output_canonical": row.output_canonical,
        "guardrail_result": row.guardrail_result,
        "items": [
            {
                "id": str(item.id),
                "sequence": item.sequence,
                "ingredient_version_id": (
                    None
                    if item.ingredient_version_id is None
                    else str(item.ingredient_version_id)
                ),
                "proposed_ingredient_name": item.proposed_ingredient_name,
                "resolution_status": item.resolution_status,
                "net_quantity_g": None if item.net_quantity_g is None else str(item.net_quantity_g),
                "is_flour_basis": item.is_flour_basis,
                "role": item.role,
                "rationale": item.rationale,
            }
            for item in items
        ],
        "steps": [
            {
                "id": str(step.id),
                "sequence": step.sequence,
                "title": step.title,
                "instructions": step.instructions,
            }
            for step in steps
        ],
        "citations": [
            {
                "id": str(item.id),
                "knowledge_fragment_id": str(item.knowledge_fragment_id),
                "claim_path": item.claim_path,
            }
            for item in citations
        ],
        "changes": [
            {
                "change_key": item.change_key,
                "change_kind": item.change_kind,
                "path": item.path,
                "before_value": item.before_value,
                "after_value": item.after_value,
                "decision": item.decision,
            }
            for item in changes
        ],
        "materialized": materialized,
    }


def grounding_out(session: Session, row: AiProposal) -> dict:
    interaction = session.get(AiInteraction, row.ai_interaction_id)
    if interaction is None or interaction.grounding_query_id is None:
        return {"query": None, "results": []}
    query = session.get(GroundingQuery, interaction.grounding_query_id)
    results = []
    if query is not None:
        for item in session.scalars(
            select(GroundingResult)
            .where(GroundingResult.grounding_query_id == query.id)
            .order_by(GroundingResult.rank)
        ):
            fragment = session.get(KnowledgeFragment, item.knowledge_fragment_id)
            source = None
            if fragment is not None:
                from app.modules.knowledge_grounding.models import KnowledgeSourceVersion

                version = session.get(KnowledgeSourceVersion, fragment.knowledge_source_version_id)
                if version is not None:
                    source = session.get(KnowledgeSource, version.knowledge_source_id)
            results.append(
                {
                    "rank": item.rank,
                    "score": None if item.score is None else str(item.score),
                    "source_kind": None if source is None else source.source_kind,
                    "authority_level": None if source is None else source.authority_level,
                    "title": None if source is None else source.title,
                    "locator": None
                    if fragment is None
                    else f"{fragment.locator_type}:{fragment.locator_value}",
                    "content_hash": None if fragment is None else fragment.content_hash,
                    "excerpt": None if fragment is None else fragment.content[:240],
                }
            )
    return {
        "query": None
        if query is None
        else {"id": str(query.id), "algorithm": query.retrieval_algorithm},
        "results": results,
    }

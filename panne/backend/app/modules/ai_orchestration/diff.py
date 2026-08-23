"""Comparação determinística entre versão-base e proposta."""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.ai_orchestration.models import AiProposal, AiProposalChange, AiProposalItem
from app.modules.formula_lab.models import FormulationItem, FormulationVersion


def _qty(value) -> str | None:
    if value is None:
        return None
    return format(Decimal(value), "f")


def build_proposal_diff(session: Session, proposal: AiProposal) -> list[AiProposalChange]:
    existing = list(
        session.scalars(
            select(AiProposalChange).where(AiProposalChange.ai_proposal_id == proposal.id)
        )
    )
    if existing:
        return existing
    proposed = list(
        session.scalars(
            select(AiProposalItem)
            .where(AiProposalItem.ai_proposal_id == proposal.id)
            .order_by(AiProposalItem.sequence)
        )
    )
    base_items: dict[UUID, FormulationItem] = {}
    if proposal.base_formulation_version_id:
        base = session.get(FormulationVersion, proposal.base_formulation_version_id)
        if base is not None and base.organization_id == proposal.organization_id:
            for item in session.scalars(
                select(FormulationItem).where(FormulationItem.formulation_version_id == base.id)
            ):
                base_items[item.ingredient_version_id] = item
    created: list[AiProposalChange] = []
    seen: set[UUID] = set()
    for item in proposed:
        if item.resolution_status != "resolved" or item.ingredient_version_id is None:
            created.append(
                AiProposalChange(
                    organization_id=proposal.organization_id,
                    ai_proposal_id=proposal.id,
                    change_key=f"unresolved:{item.sequence}",
                    change_kind="unresolved",
                    path=f"items[{item.sequence}]",
                    before_value=None,
                    after_value={
                        "name": item.proposed_ingredient_name,
                        "net_quantity_g": _qty(item.net_quantity_g),
                    },
                    citation_tokens=[],
                    decision="pending",
                )
            )
            continue
        seen.add(item.ingredient_version_id)
        previous = base_items.get(item.ingredient_version_id)
        after = {
            "ingredient_version_id": str(item.ingredient_version_id),
            "name": item.proposed_ingredient_name,
            "net_quantity_g": _qty(item.net_quantity_g),
            "correction_factor": _qty(item.correction_factor),
            "is_flour_basis": item.is_flour_basis,
            "role": item.role,
        }
        if previous is None:
            created.append(
                AiProposalChange(
                    organization_id=proposal.organization_id,
                    ai_proposal_id=proposal.id,
                    change_key=f"added:{item.ingredient_version_id}",
                    change_kind="added",
                    path=f"items[{item.sequence}]",
                    before_value=None,
                    after_value=after,
                    citation_tokens=[],
                    decision="pending",
                )
            )
            continue
        before = {
            "ingredient_version_id": str(previous.ingredient_version_id),
            "net_quantity_g": _qty(previous.net_quantity),
            "correction_factor": _qty(previous.correction_factor),
            "is_flour_basis": previous.is_flour_basis,
            "role": previous.role,
        }
        if before != {**after, "name": after["name"]}:
            comparable_after = {key: after[key] for key in before}
            if before != comparable_after:
                created.append(
                    AiProposalChange(
                        organization_id=proposal.organization_id,
                        ai_proposal_id=proposal.id,
                        change_key=f"changed:{item.ingredient_version_id}",
                        change_kind="changed",
                        path=f"items[{item.sequence}]",
                        before_value=before,
                        after_value=after,
                        citation_tokens=[],
                        decision="pending",
                    )
                )
    if proposal.proposal_type == "adapt":
        for ingredient_id, previous in base_items.items():
            if ingredient_id in seen:
                continue
            created.append(
                AiProposalChange(
                    organization_id=proposal.organization_id,
                    ai_proposal_id=proposal.id,
                    change_key=f"removed:{ingredient_id}",
                    change_kind="removed",
                    path=f"base_items[{previous.sequence}]",
                    before_value={
                        "ingredient_version_id": str(ingredient_id),
                        "net_quantity_g": _qty(previous.net_quantity),
                    },
                    after_value=None,
                    citation_tokens=[],
                    decision="pending",
                )
            )
    for row in created:
        session.add(row)
    session.flush()
    return created

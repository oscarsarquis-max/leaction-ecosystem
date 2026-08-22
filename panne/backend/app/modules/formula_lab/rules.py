"""Regras da formulação. Sem HTTP, IA ou nutrição."""

from collections.abc import Sequence
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.calculation_engine.precision import QUANTITY_QUANTUM, quantize_quantity
from app.modules.formula_lab.models import Approval, FormulationItem, FormulationVersion
from app.modules.ingredient_catalog.models import IngredientVersion


class PublishedFormulationFrozenError(ValueError):
    """Versão publicada (ou aposentada) não pode ser alterada pela camada normal."""


class PublishRequiresApprovalError(ValueError):
    """Publicação exige decisão approved na mesma versão."""


class IngredientVersionNotPublishedError(ValueError):
    """Item oficial deve apontar versão de ingrediente publicada."""


class FlourBasisEmptyError(ValueError):
    """Há farinha-base marcada, mas a soma líquida não é positiva."""


def ensure_formulation_version_editable(version: FormulationVersion) -> None:
    if version.status in {"published", "retired"}:
        raise PublishedFormulationFrozenError("versão publicada é imutável; crie outra versão")


def derived_gross_quantity(net_quantity: Decimal, correction_factor: Decimal) -> Decimal:
    if net_quantity <= 0:
        raise ValueError("quantidade líquida deve ser positiva")
    if correction_factor <= 0:
        raise ValueError("fator de correção deve ser positivo")
    return quantize_quantity(net_quantity * correction_factor)


def total_flour_mass(items: Sequence[FormulationItem]) -> Decimal | None:
    marked = [item for item in items if item.is_flour_basis]
    if not marked:
        return None
    total = sum((item.net_quantity for item in marked), Decimal("0"))
    if total <= 0:
        raise FlourBasisEmptyError("base de farinha deve ser maior que zero")
    return total


def bakers_percentage(net_quantity: Decimal, flour_mass: Decimal) -> Decimal:
    if flour_mass <= 0:
        raise FlourBasisEmptyError("base de farinha deve ser maior que zero")
    return (net_quantity / flour_mass) * Decimal("100")


def bakers_percentages(items: Sequence[FormulationItem]) -> dict[UUID, Decimal] | None:
    flour = total_flour_mass(items)
    if flour is None:
        return None
    return {item.id: bakers_percentage(item.net_quantity, flour) for item in items}


def latest_approval_decision(session: Session, formulation_version_id: UUID) -> str | None:
    return session.scalar(
        select(Approval.decision)
        .where(Approval.formulation_version_id == formulation_version_id)
        .order_by(Approval.occurred_at.desc(), Approval.id.desc())
        .limit(1)
    )


def has_valid_approval(session: Session, formulation_version_id: UUID) -> bool:
    return latest_approval_decision(session, formulation_version_id) == "approved"


def publish_formulation_version(session: Session, version: FormulationVersion) -> None:
    ensure_formulation_version_editable(version)
    if not has_valid_approval(session, version.id):
        raise PublishRequiresApprovalError("publicação exige aprovação válida")
    items = session.scalars(
        select(FormulationItem).where(FormulationItem.formulation_version_id == version.id)
    ).all()
    for item in items:
        ingredient_version = session.get(IngredientVersion, item.ingredient_version_id)
        if ingredient_version is None or ingredient_version.status != "published":
            raise IngredientVersionNotPublishedError(
                "item deve apontar versão publicada de ingrediente"
            )
    total_flour_mass(items)
    version.status = "published"
    version.published_at = datetime.now(UTC)


def retire_published_version(version: FormulationVersion) -> None:
    if version.status != "published":
        raise ValueError("somente versão publicada pode ser aposentada")
    version.status = "retired"


QUANTITY_SCALE = QUANTITY_QUANTUM

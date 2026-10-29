"""Regras de domínio da camada normal. Sem CRUD HTTP."""

from collections.abc import Iterable
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.ingredient_catalog.models import IngredientComposition, IngredientVersion


class PublishedVersionFrozenError(ValueError):
    """Versão publicada não pode ser alterada pela camada normal."""


class CompositionCycleError(ValueError):
    """Composição formaria um ciclo."""


def ensure_version_editable(version: IngredientVersion) -> None:
    if version.status == "published":
        raise PublishedVersionFrozenError("versão publicada é imutável; crie outra versão")


def composition_would_cycle(
    rows: Iterable[IngredientComposition],
    parent_version_id: UUID,
    component_version_id: UUID,
) -> bool:
    if parent_version_id == component_version_id:
        return True
    children: dict[UUID, list[UUID]] = {}
    for row in rows:
        children.setdefault(row.parent_ingredient_version_id, []).append(
            row.component_ingredient_version_id
        )
    children.setdefault(parent_version_id, []).append(component_version_id)
    seen: set[UUID] = set()
    stack = [component_version_id]
    while stack:
        current = stack.pop()
        if current == parent_version_id:
            return True
        if current in seen:
            continue
        seen.add(current)
        stack.extend(children.get(current, []))
    return False


def assert_acyclic_composition(
    session: Session,
    parent_version_id: UUID,
    component_version_id: UUID,
    organization_id: UUID | None = None,
) -> None:
    query = select(IngredientComposition)
    if organization_id is not None:
        query = query.where(IngredientComposition.organization_id == organization_id)
    rows = session.scalars(query).all()
    if composition_would_cycle(rows, parent_version_id, component_version_id):
        raise CompositionCycleError("composição cíclica rejeitada")

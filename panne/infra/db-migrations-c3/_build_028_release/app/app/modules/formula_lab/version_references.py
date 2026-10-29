"""Referências e evidências por versão. A identidade guarda só o que é geral."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.formula_lab.models import (
    FormulationRecipeReference,
    FormulationVersion,
    FormulationVersionRecipeReference,
    RecipeReference,
)
from app.modules.knowledge_grounding.models import KnowledgeFragment, KnowledgeSourceVersion
from app.modules.production_planning.errors import ImmutableError, ValidationError


def snapshot_of(reference: RecipeReference) -> dict:
    return {
        "title": reference.title,
        "source_type": reference.source_type,
        "source_url": reference.source_url,
        "author": reference.author,
        "notes": reference.notes,
        "accessed_at": None if reference.accessed_at is None else reference.accessed_at.isoformat(),
    }


def version_references_of(
    session: Session, version_id: UUID
) -> list[FormulationVersionRecipeReference]:
    return list(
        session.scalars(
            select(FormulationVersionRecipeReference).where(
                FormulationVersionRecipeReference.formulation_version_id == version_id
            )
        )
    )


def attach_reference_to_version(
    session: Session,
    version: FormulationVersion,
    reference: RecipeReference,
    *,
    role: str,
    copied_from_version_id: UUID | None = None,
    knowledge_source_version_id: UUID | None = None,
    knowledge_fragment_id: UUID | None = None,
    source_version_label: str | None = None,
    locator_type: str | None = None,
    locator_value: str | None = None,
    content_hash: str | None = None,
    accessed_at: datetime | None = None,
) -> FormulationVersionRecipeReference:
    if version.status == "published":
        raise ImmutableError("published_frozen")
    if version.organization_id != reference.organization_id:
        raise ValidationError("recurso_nao_encontrado")
    existing = session.scalar(
        select(FormulationVersionRecipeReference).where(
            FormulationVersionRecipeReference.formulation_version_id == version.id,
            FormulationVersionRecipeReference.recipe_reference_id == reference.id,
        )
    )
    if existing is not None:
        return existing
    fragment = None
    source_version = None
    if knowledge_fragment_id is not None:
        fragment = session.get(KnowledgeFragment, knowledge_fragment_id)
        if fragment is None:
            raise ValidationError("recurso_nao_encontrado")
        source_version = session.get(KnowledgeSourceVersion, fragment.knowledge_source_version_id)
    elif knowledge_source_version_id is not None:
        source_version = session.get(KnowledgeSourceVersion, knowledge_source_version_id)
    row = FormulationVersionRecipeReference(
        organization_id=version.organization_id,
        formulation_version_id=version.id,
        recipe_reference_id=reference.id,
        knowledge_source_version_id=(
            knowledge_source_version_id
            if knowledge_source_version_id is not None
            else None
            if source_version is None
            else source_version.id
        ),
        knowledge_fragment_id=None if fragment is None else fragment.id,
        role=role,
        source_version_label=source_version_label
        or (None if source_version is None else source_version.version_label),
        locator_type=locator_type or (None if fragment is None else fragment.locator_type),
        locator_value=locator_value or (None if fragment is None else fragment.locator_value),
        content_hash=content_hash
        or (None if fragment is None else fragment.content_hash)
        or (None if source_version is None else source_version.content_hash),
        accessed_at=accessed_at
        or reference.accessed_at
        or (None if source_version is None else source_version.retrieved_at),
        snapshot=snapshot_of(reference),
        copied_from_version_id=copied_from_version_id,
    )
    session.add(row)
    session.flush()
    return row


def copy_version_references(
    session: Session,
    source: FormulationVersion,
    target: FormulationVersion,
) -> list[FormulationVersionRecipeReference]:
    copied: list[FormulationVersionRecipeReference] = []
    source_links = version_references_of(session, source.id)
    if not source_links:
        identity_links = list(
            session.scalars(
                select(FormulationRecipeReference).where(
                    FormulationRecipeReference.formulation_id == source.formulation_id
                )
            )
        )
        for link in identity_links:
            reference = session.get(RecipeReference, link.recipe_reference_id)
            if reference is None:
                continue
            copied.append(
                attach_reference_to_version(
                    session,
                    target,
                    reference,
                    role=link.role,
                    copied_from_version_id=source.id,
                )
            )
        return copied
    for link in source_links:
        if link.recipe_reference_id is None:
            row = FormulationVersionRecipeReference(
                organization_id=target.organization_id,
                formulation_version_id=target.id,
                recipe_reference_id=None,
                knowledge_source_version_id=link.knowledge_source_version_id,
                knowledge_fragment_id=link.knowledge_fragment_id,
                role=link.role,
                source_version_label=link.source_version_label,
                locator_type=link.locator_type,
                locator_value=link.locator_value,
                content_hash=link.content_hash,
                accessed_at=link.accessed_at,
                snapshot=dict(link.snapshot or {}),
                copied_from_version_id=source.id,
            )
            session.add(row)
            session.flush()
            copied.append(row)
            continue
        reference = session.get(RecipeReference, link.recipe_reference_id)
        if reference is None:
            continue
        copied.append(
            attach_reference_to_version(
                session,
                target,
                reference,
                role=link.role,
                copied_from_version_id=source.id,
                knowledge_source_version_id=link.knowledge_source_version_id,
                knowledge_fragment_id=link.knowledge_fragment_id,
                source_version_label=link.source_version_label,
                locator_type=link.locator_type,
                locator_value=link.locator_value,
                content_hash=link.content_hash,
                accessed_at=link.accessed_at,
            )
        )
    return copied


def attach_identity_reference_to_current_draft(
    session: Session,
    formulation_id: UUID,
    reference: RecipeReference,
    role: str,
) -> None:
    draft = session.scalar(
        select(FormulationVersion)
        .where(
            FormulationVersion.formulation_id == formulation_id,
            FormulationVersion.status == "draft",
        )
        .order_by(FormulationVersion.version_number.desc())
    )
    if draft is None:
        return
    attach_reference_to_version(session, draft, reference, role=role)

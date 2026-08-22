"""Política de grounding regulatório. Sem LLM e sem parecer jurídico."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone

from app.modules.compliance.constants import FOUNDATION_CLASSES, PROPOSAL_STATUSES
from app.modules.knowledge_grounding.models import (
    KnowledgeFragment,
    KnowledgeSource,
    KnowledgeSourceVersion,
)
from app.modules.knowledge_grounding.rules import source_visible_to, version_is_effective_on


class RegulatoryGroundingError(ValueError):
    """Fonte incompatível com obrigação vigente."""


@dataclass(frozen=True)
class ClassifiedSource:
    source: KnowledgeSource
    version: KnowledgeSourceVersion
    fragment: KnowledgeFragment
    normative_class: str


def classify_normative_class(source: KnowledgeSource, version: KnowledgeSourceVersion) -> str:
    if version.regulatory_status in PROPOSAL_STATUSES:
        return "proposal"
    if version.regulatory_status in {"superseded", "revoked"}:
        return "revoked_or_superseded"
    if version.regulatory_status == "future":
        return "future_act"
    if source.source_kind == "normative" and source.authority_level == "official":
        if version.regulatory_status == "in_force":
            return "in_force_act"
        return "official_guidance"
    if source.source_kind == "normative":
        return "official_guidance"
    licensed = bool(source.license_or_usage_notes and source.license_or_usage_notes.strip())
    if licensed and source.source_kind in {"technical", "internal_document"}:
        return "private_standard"
    return "non_normative_technical"


def reconcile_class(declared: str | None, inferred: str) -> str:
    if declared is None or declared == inferred:
        return inferred
    if declared == "official_guidance" and inferred == "in_force_act":
        return "official_guidance"
    if declared == "proposal" and inferred in {"proposal", "future_act"}:
        return "proposal"
    raise RegulatoryGroundingError("classe normativa incompatível com a fonte")


def can_found_current_obligation(
    classified: ClassifiedSource,
    *,
    organization_id,
    when: date,
) -> bool:
    if classified.normative_class not in FOUNDATION_CLASSES:
        return False
    if classified.normative_class == "proposal":
        return False
    if classified.version.regulatory_status in PROPOSAL_STATUSES:
        return False
    if classified.version.review_status != "reviewed":
        return False
    if not version_is_effective_on(classified.version, when):
        return False
    if not source_visible_to(classified.source, organization_id):
        return False
    if (
        classified.source.organization_id is not None
        and classified.source.organization_id != organization_id
    ):
        return False
    if classified.normative_class == "in_force_act":
        return (
            classified.source.source_kind == "normative"
            and classified.source.authority_level == "official"
            and classified.version.regulatory_status == "in_force"
        )
    licensed = bool(
        classified.source.license_or_usage_notes
        and classified.source.license_or_usage_notes.strip()
    )
    return licensed and classified.source.source_kind != "normative"


def assert_linkable(
    source: KnowledgeSource,
    version: KnowledgeSourceVersion,
    fragment: KnowledgeFragment,
    *,
    organization_id,
    when: date,
    declared_class: str | None,
    citation_role: str,
) -> ClassifiedSource:
    if fragment.knowledge_source_version_id != version.id:
        raise RegulatoryGroundingError("fragmento não pertence à versão")
    inferred = classify_normative_class(source, version)
    normative_class = reconcile_class(declared_class, inferred)
    classified = ClassifiedSource(source, version, fragment, normative_class)
    if citation_role == "foundation":
        if not can_found_current_obligation(
            classified, organization_id=organization_id, when=when
        ):
            raise RegulatoryGroundingError("fonte não fundamenta obrigação vigente")
    if not source_visible_to(source, organization_id):
        raise RegulatoryGroundingError("fonte invisível para a organização")
    if not fragment.content_hash or not version.content_hash:
        raise RegulatoryGroundingError("hash do fragmento ou da versão ausente")
    return classified


def source_snapshot(classified: ClassifiedSource) -> dict:
    source = classified.source
    version = classified.version
    fragment = classified.fragment
    return {
        "source_id": str(source.id),
        "source_title": source.title,
        "source_kind": source.source_kind,
        "authority_level": source.authority_level,
        "issuer_or_author": source.issuer_or_author,
        "jurisdiction": source.jurisdiction,
        "canonical_url": source.canonical_url,
        "license_or_usage_notes": source.license_or_usage_notes,
        "release_state": source.release_state,
        "version_id": str(version.id),
        "version_label": version.version_label,
        "regulatory_status": version.regulatory_status,
        "review_status": version.review_status,
        "effective_from": version.effective_from.isoformat() if version.effective_from else None,
        "effective_until": version.effective_until.isoformat() if version.effective_until else None,
        "version_content_hash": version.content_hash,
        "fragment_id": str(fragment.id),
        "locator_type": fragment.locator_type,
        "locator_value": fragment.locator_value,
        "fragment_content_hash": fragment.content_hash,
        "normative_class": classified.normative_class,
        "accessed_at": datetime.now(timezone.utc).isoformat(),
    }

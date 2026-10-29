"""Regras de autoridade, vigência e isolamento. Sem interpretação normativa."""

from datetime import date
from uuid import UUID

from app.modules.knowledge_grounding.models import KnowledgeSource, KnowledgeSourceVersion

SOURCE_KINDS = frozenset(
    {"recipe", "normative", "technical", "nutritional_database", "internal_document"}
)
AUTHORITY_LEVELS = frozenset({"official", "curated", "user_provided", "unverified"})
REGULATORY_STATUSES = frozenset(
    {
        "not_applicable",
        "draft",
        "public_consultation",
        "in_force",
        "superseded",
        "revoked",
        "future",
    }
)
REVIEW_STATUSES = frozenset({"pending", "reviewed", "rejected"})
LOCATOR_TYPES = frozenset(
    {"page", "section", "article", "clause", "annex", "paragraph", "block", "url_fragment"}
)
TAG_CATEGORIES = frozenset(
    {
        "product",
        "process",
        "ingredient",
        "nutrient",
        "allergen",
        "norm",
        "jurisdiction",
        "technique",
    }
)
CONTENT_USAGE_KINDS = frozenset(
    {"citation", "summary", "extracted_structure", "not_applicable"}
)
PROFILE_PURPOSES = frozenset({"technical", "regulatory_candidate", "custom"})
VALUE_STATUSES = frozenset(
    {"measured", "known_zero", "below_loq", "not_detected", "unknown"}
)
AUTHORITY_RANK = {
    "official": 4,
    "curated": 3,
    "user_provided": 2,
    "unverified": 1,
}
REVIEW_RANK = {"reviewed": 2, "pending": 1, "rejected": 0}
REGULATORY_RANK = {
    "in_force": 5,
    "future": 4,
    "public_consultation": 3,
    "draft": 2,
    "superseded": 1,
    "revoked": 1,
    "not_applicable": 0,
}

DEFAULT_NORMATIVE_AUTHORITY = ("official",)
DEFAULT_NORMATIVE_REVIEW = ("reviewed",)
DEFAULT_NORMATIVE_REGULATORY = ("in_force",)


class KnowledgeError(ValueError):
    """Entrada inválida na biblioteca de conhecimento."""


def assert_source_identity(source: KnowledgeSource) -> None:
    if source.source_kind not in SOURCE_KINDS:
        raise KnowledgeError("tipo de fonte inválido")
    if source.authority_level not in AUTHORITY_LEVELS:
        raise KnowledgeError("nível de autoridade inválido")
    if source.organization_id is None and source.release_state not in {"restricted", "released"}:
        raise KnowledgeError("fonte global exige estado de liberação")
    if source.organization_id is not None and source.release_state != "private":
        raise KnowledgeError("fonte privada deve permanecer privada")
    if source.source_kind == "normative" and source.authority_level == "official":
        if not (source.issuer_or_author and source.issuer_or_author.strip()):
            raise KnowledgeError("norma oficial exige órgão emissor")
        if not (source.jurisdiction and source.jurisdiction.strip()):
            raise KnowledgeError("norma oficial exige jurisdição")
    if source.source_kind == "recipe" and source.authority_level == "official":
        raise KnowledgeError("receita não é norma oficial")


def version_is_effective_on(version: KnowledgeSourceVersion, when: date) -> bool:
    if version.effective_from is not None and when < version.effective_from:
        return False
    if version.effective_until is not None and when > version.effective_until:
        return False
    return True


def source_visible_to(source: KnowledgeSource, organization_id: UUID | None) -> bool:
    if source.organization_id is None:
        return source.release_state == "released"
    return source.organization_id == organization_id


def fragment_visible_to(
    source: KnowledgeSource, organization_id: UUID | None
) -> bool:
    return source_visible_to(source, organization_id)

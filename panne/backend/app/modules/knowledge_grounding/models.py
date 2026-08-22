"""Fontes, fragmentos, grounding e perfis nutricionais. Sem CRUD HTTP."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    Text,
    Uuid,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


def _uuid_pk():
    return mapped_column(Uuid, primary_key=True, server_default=text("gen_random_uuid()"))


def _created_at():
    return mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class KnowledgeSource(Base):
    __tablename__ = "knowledge_source"
    __table_args__ = (
        Index("ix_knowledge_source_org_kind", "organization_id", "source_kind"),
        Index("ix_knowledge_source_jurisdiction", "jurisdiction", "authority_level"),
    )

    id: Mapped[UUID] = _uuid_pk()
    organization_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("organization.id", ondelete="RESTRICT")
    )
    source_kind: Mapped[str] = mapped_column(Text, nullable=False)
    authority_level: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    issuer_or_author: Mapped[str | None] = mapped_column(Text)
    jurisdiction: Mapped[str | None] = mapped_column(Text)
    canonical_url: Mapped[str | None] = mapped_column(Text)
    language: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'pt-BR'"))
    license_or_usage_notes: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'active'"))
    release_state: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = _created_at()
    created_by_user_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("app_user.id", ondelete="RESTRICT")
    )


class KnowledgeSourceVersion(Base):
    __tablename__ = "knowledge_source_version"
    __table_args__ = (
        Index(
            "uq_knowledge_source_version_label",
            "knowledge_source_id",
            "version_label",
            unique=True,
        ),
        Index(
            "ix_knowledge_source_version_status",
            "regulatory_status",
            "review_status",
            "effective_from",
        ),
    )

    id: Mapped[UUID] = _uuid_pk()
    knowledge_source_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("knowledge_source.id", ondelete="RESTRICT"), nullable=False
    )
    organization_id: Mapped[UUID | None] = mapped_column(Uuid)
    version_label: Mapped[str] = mapped_column(Text, nullable=False)
    publication_date: Mapped[date | None] = mapped_column(Date)
    effective_from: Mapped[date | None] = mapped_column(Date)
    effective_until: Mapped[date | None] = mapped_column(Date)
    regulatory_status: Mapped[str] = mapped_column(Text, nullable=False)
    retrieved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("clock_timestamp()")
    )
    content_hash: Mapped[str | None] = mapped_column(Text)
    mime_type: Mapped[str | None] = mapped_column(Text)
    language: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'pt-BR'"))
    storage_key: Mapped[str | None] = mapped_column(Text)
    content_usage_kind: Mapped[str] = mapped_column(
        Text, nullable=False, server_default=text("'not_applicable'")
    )
    review_status: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'pending'"))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reviewed_by_user_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("app_user.id", ondelete="RESTRICT")
    )
    created_at: Mapped[datetime] = _created_at()


class KnowledgeFragment(Base):
    __tablename__ = "knowledge_fragment"
    __table_args__ = (
        Index(
            "uq_knowledge_fragment_sequence",
            "knowledge_source_version_id",
            "sequence",
            unique=True,
        ),
        Index("ix_knowledge_fragment_fts", "search_vector", postgresql_using="gin"),
    )

    id: Mapped[UUID] = _uuid_pk()
    knowledge_source_version_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("knowledge_source_version.id", ondelete="RESTRICT"), nullable=False
    )
    organization_id: Mapped[UUID | None] = mapped_column(Uuid)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    locator_type: Mapped[str] = mapped_column(Text, nullable=False)
    locator_value: Mapped[str] = mapped_column(Text, nullable=False)
    heading: Mapped[str | None] = mapped_column(Text)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(Text, nullable=False)
    search_vector: Mapped[str | None] = mapped_column(TSVECTOR)
    created_at: Mapped[datetime] = _created_at()


class KnowledgeTag(Base):
    __tablename__ = "knowledge_tag"

    id: Mapped[UUID] = _uuid_pk()
    code: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    display_name: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'active'"))


class KnowledgeSourceTag(Base):
    __tablename__ = "knowledge_source_tag"
    __table_args__ = (
        Index(
            "uq_knowledge_source_tag",
            "knowledge_source_id",
            "knowledge_tag_id",
            unique=True,
        ),
    )

    id: Mapped[UUID] = _uuid_pk()
    knowledge_source_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("knowledge_source.id", ondelete="RESTRICT"), nullable=False
    )
    knowledge_tag_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("knowledge_tag.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = _created_at()


class NutritionExpectationProfile(Base):
    __tablename__ = "nutrition_expectation_profile"

    id: Mapped[UUID] = _uuid_pk()
    organization_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("organization.id", ondelete="RESTRICT")
    )
    code: Mapped[str] = mapped_column(Text, nullable=False)
    display_name: Mapped[str] = mapped_column(Text, nullable=False)
    purpose: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'active'"))
    knowledge_source_version_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("knowledge_source_version.id", ondelete="RESTRICT")
    )
    created_at: Mapped[datetime] = _created_at()


class NutritionExpectationProfileItem(Base):
    __tablename__ = "nutrition_expectation_profile_item"
    __table_args__ = (
        Index(
            "uq_nutrition_expectation_profile_item_nutrient",
            "profile_id",
            "nutrient_definition_id",
            unique=True,
        ),
        Index(
            "uq_nutrition_expectation_profile_item_sequence",
            "profile_id",
            "sequence",
            unique=True,
        ),
    )

    id: Mapped[UUID] = _uuid_pk()
    profile_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("nutrition_expectation_profile.id", ondelete="RESTRICT"), nullable=False
    )
    nutrient_definition_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("nutrient_definition.id", ondelete="RESTRICT"), nullable=False
    )
    required: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = _created_at()


class GroundingQuery(Base):
    __tablename__ = "grounding_query"

    id: Mapped[UUID] = _uuid_pk()
    organization_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("organization.id", ondelete="RESTRICT")
    )
    query_text: Mapped[str | None] = mapped_column(Text)
    filters: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    retrieval_algorithm: Mapped[str] = mapped_column(Text, nullable=False)
    retrieval_version: Mapped[str] = mapped_column(Text, nullable=False)
    applicability_date: Mapped[date | None] = mapped_column(Date)
    created_at: Mapped[datetime] = _created_at()
    created_by_user_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("app_user.id", ondelete="RESTRICT")
    )


class GroundingResult(Base):
    __tablename__ = "grounding_result"
    __table_args__ = (
        Index("uq_grounding_result_rank", "grounding_query_id", "rank", unique=True),
        Index(
            "uq_grounding_result_fragment",
            "grounding_query_id",
            "knowledge_fragment_id",
            unique=True,
        ),
    )

    id: Mapped[UUID] = _uuid_pk()
    grounding_query_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("grounding_query.id", ondelete="RESTRICT"), nullable=False
    )
    knowledge_fragment_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("knowledge_fragment.id", ondelete="RESTRICT"), nullable=False
    )
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    score: Mapped[Decimal] = mapped_column(Numeric(14, 6), nullable=False)
    selection_reason: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = _created_at()


class GroundingCitation(Base):
    __tablename__ = "grounding_citation"
    __table_args__ = (Index("uq_grounding_citation_result", "grounding_result_id", unique=True),)

    id: Mapped[UUID] = _uuid_pk()
    grounding_result_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("grounding_result.id", ondelete="RESTRICT"), nullable=False
    )
    source_title: Mapped[str] = mapped_column(Text, nullable=False)
    version_label: Mapped[str] = mapped_column(Text, nullable=False)
    issuer_or_author: Mapped[str | None] = mapped_column(Text)
    canonical_url: Mapped[str | None] = mapped_column(Text)
    locator_type: Mapped[str] = mapped_column(Text, nullable=False)
    locator_value: Mapped[str] = mapped_column(Text, nullable=False)
    version_content_hash: Mapped[str | None] = mapped_column(Text)
    fragment_content_hash: Mapped[str] = mapped_column(Text, nullable=False)
    accessed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = _created_at()

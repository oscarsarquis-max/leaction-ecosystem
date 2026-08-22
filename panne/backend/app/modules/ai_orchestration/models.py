"""Persistência da orquestração assistiva. Sem credenciais e sem CRUD HTTP."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    Numeric,
    Text,
    Uuid,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


def _uuid_pk():
    return mapped_column(Uuid, primary_key=True, server_default=text("gen_random_uuid()"))


def _created_at():
    return mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class AiInteraction(Base):
    __tablename__ = "ai_interaction"
    __table_args__ = (
        Index("uq_ai_interaction_id_org", "id", "organization_id", unique=True),
        Index("ix_ai_interaction_org_created", "organization_id", "created_at"),
    )

    id: Mapped[UUID] = _uuid_pk()
    organization_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("organization.id", ondelete="RESTRICT"), nullable=False
    )
    interaction_type: Mapped[str] = mapped_column(Text, nullable=False)
    provider: Mapped[str] = mapped_column(Text, nullable=False)
    model_id: Mapped[str] = mapped_column(Text, nullable=False)
    region: Mapped[str] = mapped_column(Text, nullable=False)
    prompt_template_version: Mapped[str] = mapped_column(Text, nullable=False)
    request_hash: Mapped[str] = mapped_column(Text, nullable=False)
    grounding_query_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("grounding_query.id", ondelete="RESTRICT")
    )
    status: Mapped[str] = mapped_column(Text, nullable=False)
    input_token_count: Mapped[int | None] = mapped_column(Integer)
    output_token_count: Mapped[int | None] = mapped_column(Integer)
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    stop_reason: Mapped[str | None] = mapped_column(Text)
    error_code: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = _created_at()
    created_by_user_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("app_user.id", ondelete="RESTRICT")
    )


class AiProposal(Base):
    __tablename__ = "ai_proposal"
    __table_args__ = (
        Index("uq_ai_proposal_id_org", "id", "organization_id", unique=True),
        Index("uq_ai_proposal_interaction", "ai_interaction_id", unique=True),
        ForeignKeyConstraint(
            ["ai_interaction_id", "organization_id"],
            ["ai_interaction.id", "ai_interaction.organization_id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["base_formulation_version_id", "organization_id"],
            ["formulation_version.id", "formulation_version.organization_id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["materialized_formulation_version_id", "organization_id"],
            ["formulation_version.id", "formulation_version.organization_id"],
            ondelete="RESTRICT",
        ),
    )

    id: Mapped[UUID] = _uuid_pk()
    organization_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    ai_interaction_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    proposal_type: Mapped[str] = mapped_column(Text, nullable=False)
    base_formulation_version_id: Mapped[UUID | None] = mapped_column(Uuid)
    materialized_formulation_version_id: Mapped[UUID | None] = mapped_column(Uuid)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    objective_summary: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    assumptions: Mapped[list] = mapped_column(
        JSONB, nullable=False, server_default=text("'[]'::jsonb")
    )
    unresolved_questions: Mapped[list] = mapped_column(
        JSONB, nullable=False, server_default=text("'[]'::jsonb")
    )
    warnings: Mapped[list] = mapped_column(
        JSONB, nullable=False, server_default=text("'[]'::jsonb")
    )
    created_at: Mapped[datetime] = _created_at()
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AiProposalItem(Base):
    __tablename__ = "ai_proposal_item"
    __table_args__ = (
        Index("uq_ai_proposal_item_sequence", "ai_proposal_id", "sequence", unique=True),
        ForeignKeyConstraint(
            ["ai_proposal_id", "organization_id"],
            ["ai_proposal.id", "ai_proposal.organization_id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["ingredient_version_id", "organization_id"],
            ["ingredient_version.id", "ingredient_version.organization_id"],
            ondelete="RESTRICT",
        ),
    )

    id: Mapped[UUID] = _uuid_pk()
    organization_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    ai_proposal_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    ingredient_version_id: Mapped[UUID | None] = mapped_column(Uuid)
    proposed_ingredient_name: Mapped[str] = mapped_column(Text, nullable=False)
    resolution_status: Mapped[str] = mapped_column(Text, nullable=False)
    net_quantity_g: Mapped[Decimal | None] = mapped_column(Numeric(14, 6))
    correction_factor: Mapped[Decimal | None] = mapped_column(Numeric(20, 10))
    is_flour_basis: Mapped[bool] = mapped_column(Boolean, nullable=False)
    role: Mapped[str] = mapped_column(Text, nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    confidence_note: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = _created_at()


class AiProposalProcessStep(Base):
    __tablename__ = "ai_proposal_process_step"
    __table_args__ = (
        Index("uq_ai_proposal_step_sequence", "ai_proposal_id", "sequence", unique=True),
        ForeignKeyConstraint(
            ["ai_proposal_id", "organization_id"],
            ["ai_proposal.id", "ai_proposal.organization_id"],
            ondelete="RESTRICT",
        ),
    )

    id: Mapped[UUID] = _uuid_pk()
    organization_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    ai_proposal_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    instructions: Mapped[str] = mapped_column(Text, nullable=False)
    duration_seconds: Mapped[int | None] = mapped_column(Integer)
    temperature_celsius: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = _created_at()


class AiProposalCitation(Base):
    __tablename__ = "ai_proposal_citation"
    __table_args__ = (
        Index(
            "uq_ai_proposal_citation_claim",
            "ai_proposal_id",
            "knowledge_fragment_id",
            "claim_path",
            unique=True,
        ),
        ForeignKeyConstraint(
            ["ai_proposal_id", "organization_id"],
            ["ai_proposal.id", "ai_proposal.organization_id"],
            ondelete="RESTRICT",
        ),
    )

    id: Mapped[UUID] = _uuid_pk()
    organization_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    ai_proposal_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    knowledge_fragment_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("knowledge_fragment.id", ondelete="RESTRICT"), nullable=False
    )
    grounding_citation_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("grounding_citation.id", ondelete="RESTRICT"), nullable=False
    )
    claim_path: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = _created_at()


class AiProposalReview(Base):
    __tablename__ = "ai_proposal_review"
    __table_args__ = (
        Index(
            "uq_ai_proposal_review_accepted",
            "ai_proposal_id",
            unique=True,
            postgresql_where=text("decision = 'accepted'"),
        ),
        ForeignKeyConstraint(
            ["ai_proposal_id", "organization_id"],
            ["ai_proposal.id", "ai_proposal.organization_id"],
            ondelete="RESTRICT",
        ),
    )

    id: Mapped[UUID] = _uuid_pk()
    organization_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    ai_proposal_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    actor_user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("app_user.id", ondelete="RESTRICT"), nullable=False
    )
    decision: Mapped[str] = mapped_column(Text, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("clock_timestamp()")
    )
    notes: Mapped[str | None] = mapped_column(Text)

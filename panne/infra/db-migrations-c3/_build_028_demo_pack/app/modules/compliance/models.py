"""Persistência da governança regulatória. Sem CRUD HTTP e sem código executável."""

from datetime import date, datetime
from uuid import UUID

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
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


class ComplianceFramework(Base):
    __tablename__ = "compliance_framework"
    __table_args__ = (
        Index("uq_compliance_framework_id_org", "id", "organization_id", unique=True),
        Index(
            "uq_compliance_framework_global_code",
            "code",
            unique=True,
            postgresql_where=text("organization_id IS NULL"),
        ),
        Index(
            "uq_compliance_framework_org_code",
            "organization_id",
            "code",
            unique=True,
            postgresql_where=text("organization_id IS NOT NULL"),
        ),
    )

    id: Mapped[UUID] = _uuid_pk()
    organization_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("organization.id", ondelete="RESTRICT")
    )
    code: Mapped[str] = mapped_column(Text, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    purpose: Mapped[str] = mapped_column(Text, nullable=False)
    regulatory_domain: Mapped[str] = mapped_column(Text, nullable=False)
    scope: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = _created_at()
    created_by_user_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("app_user.id", ondelete="RESTRICT")
    )


class ComplianceFrameworkVersion(Base):
    __tablename__ = "compliance_framework_version"
    __table_args__ = (
        Index(
            "uq_compliance_framework_version_number",
            "compliance_framework_id",
            "version_number",
            unique=True,
        ),
        Index(
            "uq_compliance_framework_one_active",
            "compliance_framework_id",
            unique=True,
            postgresql_where=text("status = 'active'"),
        ),
    )

    id: Mapped[UUID] = _uuid_pk()
    organization_id: Mapped[UUID | None] = mapped_column(Uuid)
    compliance_framework_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("compliance_framework.id", ondelete="RESTRICT"), nullable=False
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    jurisdiction: Mapped[str] = mapped_column(Text, nullable=False)
    authorities: Mapped[list] = mapped_column(
        JSONB, nullable=False, server_default=text("'[]'::jsonb")
    )
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_until: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    knowledge_cutoff_date: Mapped[date] = mapped_column(Date, nullable=False)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reviewed_by_user_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("app_user.id", ondelete="RESTRICT")
    )
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    activated_by_user_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("app_user.id", ondelete="RESTRICT")
    )
    review_notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = _created_at()
    created_by_user_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("app_user.id", ondelete="RESTRICT")
    )


class ComplianceRequirement(Base):
    __tablename__ = "compliance_requirement"
    __table_args__ = (
        Index(
            "uq_compliance_requirement_code",
            "compliance_framework_version_id",
            "code",
            unique=True,
        ),
        Index(
            "uq_compliance_requirement_sequence",
            "compliance_framework_version_id",
            "sequence",
            unique=True,
        ),
    )

    id: Mapped[UUID] = _uuid_pk()
    organization_id: Mapped[UUID | None] = mapped_column(Uuid)
    compliance_framework_version_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("compliance_framework_version.id", ondelete="RESTRICT"),
        nullable=False,
    )
    code: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    regulatory_domain: Mapped[str] = mapped_column(Text, nullable=False)
    normative_force: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(Text, nullable=False)
    evaluation_type: Mapped[str] = mapped_column(Text, nullable=False)
    parameters: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    applicability: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    review_status: Mapped[str] = mapped_column(Text, nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = _created_at()


class ComplianceRequirementSource(Base):
    __tablename__ = "compliance_requirement_source"
    __table_args__ = (
        Index(
            "uq_compliance_requirement_source",
            "compliance_requirement_id",
            "knowledge_fragment_id",
            "citation_role",
            unique=True,
        ),
    )

    id: Mapped[UUID] = _uuid_pk()
    organization_id: Mapped[UUID | None] = mapped_column(Uuid)
    compliance_requirement_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("compliance_requirement.id", ondelete="RESTRICT"), nullable=False
    )
    knowledge_fragment_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("knowledge_fragment.id", ondelete="RESTRICT"), nullable=False
    )
    knowledge_source_version_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("knowledge_source_version.id", ondelete="RESTRICT"), nullable=False
    )
    citation_role: Mapped[str] = mapped_column(Text, nullable=False)
    normative_class: Mapped[str] = mapped_column(Text, nullable=False)
    snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = _created_at()


class ComplianceProfile(Base):
    __tablename__ = "compliance_profile"
    __table_args__ = (
        Index("uq_compliance_profile_id_org", "id", "organization_id", unique=True),
        ForeignKeyConstraint(
            ["establishment_id", "organization_id"],
            ["establishment.id", "establishment.organization_id"],
            ondelete="RESTRICT",
        ),
    )

    id: Mapped[UUID] = _uuid_pk()
    organization_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("organization.id", ondelete="RESTRICT"), nullable=False
    )
    establishment_id: Mapped[UUID | None] = mapped_column(Uuid)
    country: Mapped[str] = mapped_column(Text, nullable=False)
    state: Mapped[str | None] = mapped_column(Text)
    municipality: Mapped[str | None] = mapped_column(Text)
    activity: Mapped[str] = mapped_column(Text, nullable=False)
    product_categories: Mapped[list] = mapped_column(
        JSONB, nullable=False, server_default=text("'[]'::jsonb")
    )
    sale_form: Mapped[str | None] = mapped_column(Text)
    packaging: Mapped[str | None] = mapped_column(Text)
    processes: Mapped[list] = mapped_column(
        JSONB, nullable=False, server_default=text("'[]'::jsonb")
    )
    equipment: Mapped[list] = mapped_column(
        JSONB, nullable=False, server_default=text("'[]'::jsonb")
    )
    reference_date: Mapped[date] = mapped_column(Date, nullable=False)
    extra_context: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    is_snapshot: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    source_profile_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("compliance_profile.id", ondelete="RESTRICT")
    )
    frozen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = _created_at()
    created_by_user_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("app_user.id", ondelete="RESTRICT")
    )


class ComplianceAssessment(Base):
    __tablename__ = "compliance_assessment"
    __table_args__ = (
        Index("uq_compliance_assessment_id_org", "id", "organization_id", unique=True),
        ForeignKeyConstraint(
            ["compliance_profile_id", "organization_id"],
            ["compliance_profile.id", "compliance_profile.organization_id"],
            ondelete="RESTRICT",
        ),
    )

    id: Mapped[UUID] = _uuid_pk()
    organization_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    compliance_profile_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    compliance_framework_version_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("compliance_framework_version.id", ondelete="RESTRICT"),
        nullable=False,
    )
    target_type: Mapped[str | None] = mapped_column(Text)
    target_id: Mapped[UUID | None] = mapped_column(Uuid)
    assessed_on: Mapped[date] = mapped_column(Date, nullable=False)
    algorithm_name: Mapped[str] = mapped_column(Text, nullable=False)
    algorithm_version: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    completeness: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = _created_at()
    created_by_user_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("app_user.id", ondelete="RESTRICT")
    )


class ComplianceFinding(Base):
    __tablename__ = "compliance_finding"
    __table_args__ = (
        Index(
            "uq_compliance_finding_requirement",
            "compliance_assessment_id",
            "compliance_requirement_id",
            unique=True,
        ),
        Index(
            "uq_compliance_finding_sequence",
            "compliance_assessment_id",
            "sequence",
            unique=True,
        ),
        Index("uq_compliance_finding_id_org", "id", "organization_id", unique=True),
        ForeignKeyConstraint(
            ["compliance_assessment_id", "organization_id"],
            ["compliance_assessment.id", "compliance_assessment.organization_id"],
            ondelete="RESTRICT",
        ),
    )

    id: Mapped[UUID] = _uuid_pk()
    organization_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    compliance_assessment_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    compliance_requirement_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("compliance_requirement.id", ondelete="RESTRICT"), nullable=False
    )
    result: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(Text, nullable=False)
    technical_message: Mapped[str] = mapped_column(Text, nullable=False)
    input_snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False)
    parameter_snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = _created_at()


class ComplianceEvidence(Base):
    __tablename__ = "compliance_evidence"
    __table_args__ = (
        ForeignKeyConstraint(
            ["compliance_finding_id", "organization_id"],
            ["compliance_finding.id", "compliance_finding.organization_id"],
            ondelete="RESTRICT",
        ),
    )

    id: Mapped[UUID] = _uuid_pk()
    organization_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    compliance_finding_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    evidence_kind: Mapped[str] = mapped_column(Text, nullable=False)
    origin: Mapped[str] = mapped_column(Text, nullable=False)
    value: Mapped[str | None] = mapped_column(Text)
    unit: Mapped[str | None] = mapped_column(Text)
    knowledge_fragment_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("knowledge_fragment.id", ondelete="RESTRICT")
    )
    content_hash: Mapped[str | None] = mapped_column(Text)
    locator: Mapped[str | None] = mapped_column(Text)
    snapshot: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    created_at: Mapped[datetime] = _created_at()


class ComplianceReview(Base):
    __tablename__ = "compliance_review"
    __table_args__ = (
        ForeignKeyConstraint(
            ["compliance_assessment_id", "organization_id"],
            ["compliance_assessment.id", "compliance_assessment.organization_id"],
            ondelete="RESTRICT",
        ),
    )

    id: Mapped[UUID] = _uuid_pk()
    organization_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    compliance_assessment_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    actor_user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("app_user.id", ondelete="RESTRICT"), nullable=False
    )
    decision: Mapped[str] = mapped_column(Text, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("clock_timestamp()")
    )
    justification: Mapped[str] = mapped_column(Text, nullable=False)

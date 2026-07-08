"""Modelos SQLAlchemy — domínios Core, Framework e Execução."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

db = SQLAlchemy()


# ---------------------------------------------------------------------------
# DOMÍNIO CORE — Identidade e Multitenancy
# ---------------------------------------------------------------------------


class Tenant(db.Model):
    __tablename__ = "tenants"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    document: Mapped[str | None] = mapped_column(String(32), unique=True, index=True)
    journey_status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="AGUARDANDO CONTEXTO"
    )
    has_active_project: Mapped[bool] = mapped_column(default=False, nullable=False)
    context_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    memberships: Mapped[list[TenantUser]] = relationship(
        back_populates="tenant", cascade="all, delete-orphan"
    )
    tenant_frameworks: Mapped[list[TenantFramework]] = relationship(
        back_populates="tenant", cascade="all, delete-orphan"
    )
    assessment_responses: Mapped[list[AssessmentResponse]] = relationship(
        back_populates="tenant", cascade="all, delete-orphan"
    )
    assessment_submissions: Mapped[list[AssessmentSubmission]] = relationship(
        back_populates="tenant", cascade="all, delete-orphan"
    )
    action_plans: Mapped[list[ActionPlan]] = relationship(
        back_populates="tenant", cascade="all, delete-orphan"
    )


class User(db.Model):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    memberships: Mapped[list[TenantUser]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    assessment_responses: Mapped[list[AssessmentResponse]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    assessment_submissions: Mapped[list[AssessmentSubmission]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class TenantUser(db.Model):
    __tablename__ = "tenant_users"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    operational_site_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("operational_sites.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    tenant: Mapped[Tenant] = relationship(back_populates="memberships")
    user: Mapped[User] = relationship(back_populates="memberships")


class LeadAccess(db.Model):
    """Código de acesso LA-* vinculado ao tenant e ao utilizador lead."""

    __tablename__ = "lead_access"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    access_code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    tenant: Mapped[Tenant] = relationship()
    user: Mapped[User] = relationship()


# ---------------------------------------------------------------------------
# DOMÍNIO FRAMEWORK — Catálogo agnóstico
# ---------------------------------------------------------------------------


class Framework(db.Model):
    __tablename__ = "frameworks"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    industry: Mapped[str | None] = mapped_column(String(128))
    version: Mapped[str | None] = mapped_column(String(32))
    rules_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    maturity_levels: Mapped[list[MaturityLevel]] = relationship(
        back_populates="framework", cascade="all, delete-orphan"
    )
    assessment_items: Mapped[list[AssessmentItem]] = relationship(
        back_populates="framework", cascade="all, delete-orphan"
    )
    journeys: Mapped[list[Journey]] = relationship(
        back_populates="framework", cascade="all, delete-orphan"
    )
    tenant_frameworks: Mapped[list[TenantFramework]] = relationship(
        back_populates="framework", cascade="all, delete-orphan"
    )
    action_plans: Mapped[list[ActionPlan]] = relationship(
        back_populates="framework", cascade="all, delete-orphan"
    )
    dimensions: Mapped[list[FrameworkDimension]] = relationship(
        back_populates="framework", cascade="all, delete-orphan"
    )
    domains: Mapped[list[FrameworkDomain]] = relationship(
        back_populates="framework", cascade="all, delete-orphan"
    )
    blocks: Mapped[list[FrameworkBlock]] = relationship(
        back_populates="framework", cascade="all, delete-orphan"
    )
    deliverables: Mapped[list[FrameworkDeliverable]] = relationship(
        back_populates="framework", cascade="all, delete-orphan"
    )


class FrameworkDimension(db.Model):
    """Dimensão metodológica — espelho leaf_dime."""

    __tablename__ = "framework_dimensions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    framework_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("frameworks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    legacy_id_dime: Mapped[int | None] = mapped_column(Integer, index=True)
    dimension_key: Mapped[str | None] = mapped_column(String(16))
    name_dime: Mapped[str] = mapped_column(Text, nullable=False)
    desc_dime: Mapped[str | None] = mapped_column(Text)
    long_description: Mapped[str | None] = mapped_column(Text)
    code_dime: Mapped[str | None] = mapped_column(String(16))
    perspective_dime: Mapped[str | None] = mapped_column(Text)
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    framework: Mapped[Framework] = relationship(back_populates="dimensions")
    blocks: Mapped[list[FrameworkBlock]] = relationship(back_populates="dimension")


class FrameworkDomain(db.Model):
    """Domínio operacional — espelho leaf_doma."""

    __tablename__ = "framework_domains"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    framework_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("frameworks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    legacy_id_doma: Mapped[int | None] = mapped_column(Integer, index=True)
    domain_key: Mapped[str | None] = mapped_column(String(32))
    name_doma: Mapped[str] = mapped_column(Text, nullable=False)
    desc_doma: Mapped[str | None] = mapped_column(Text)
    vetor_estrategico: Mapped[str | None] = mapped_column(String(255))
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    framework: Mapped[Framework] = relationship(back_populates="domains")
    blocks: Mapped[list[FrameworkBlock]] = relationship(back_populates="domain")


class FrameworkBlock(db.Model):
    """Bloco de implementação — espelho leaf_bloc."""

    __tablename__ = "framework_blocks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    framework_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("frameworks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    dimension_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("framework_dimensions.id", ondelete="SET NULL"), index=True
    )
    domain_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("framework_domains.id", ondelete="SET NULL"), index=True
    )
    legacy_id_bloc: Mapped[int | None] = mapped_column(Integer, index=True)
    name_bloc: Mapped[str] = mapped_column(Text, nullable=False)
    desc_bloc: Mapped[str | None] = mapped_column(Text)
    level_bloc: Mapped[int | None] = mapped_column(Integer)
    quali_bloc: Mapped[str | None] = mapped_column(Text)

    framework: Mapped[Framework] = relationship(back_populates="blocks")
    dimension: Mapped[FrameworkDimension | None] = relationship(back_populates="blocks")
    domain: Mapped[FrameworkDomain | None] = relationship(back_populates="blocks")
    deliverables: Mapped[list[FrameworkDeliverable]] = relationship(
        back_populates="block", cascade="all, delete-orphan"
    )


class FrameworkDeliverable(db.Model):
    """Entregável metodológico — espelho leaf_derv."""

    __tablename__ = "framework_deliverables"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    framework_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("frameworks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    block_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("framework_blocks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    legacy_id_derv: Mapped[int | None] = mapped_column(Integer, index=True)
    name_derv: Mapped[str] = mapped_column(Text, nullable=False)
    desc_derv: Mapped[str | None] = mapped_column(Text)
    derv_defi: Mapped[str | None] = mapped_column(Text)
    derv_comp: Mapped[str | None] = mapped_column(Text)
    derv_metr: Mapped[str | None] = mapped_column(Text)
    criteria_dod: Mapped[dict[str, Any] | None] = mapped_column(JSONB)

    framework: Mapped[Framework] = relationship(back_populates="deliverables")
    block: Mapped[FrameworkBlock] = relationship(back_populates="deliverables")


class MaturityLevel(db.Model):
    __tablename__ = "maturity_levels"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    framework_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("frameworks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    level: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)

    framework: Mapped[Framework] = relationship(back_populates="maturity_levels")


class AssessmentItem(db.Model):
    __tablename__ = "assessment_items"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    framework_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("frameworks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    axis: Mapped[str] = mapped_column(String(128), nullable=False)
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    question_type: Mapped[str] = mapped_column(String(64), nullable=False)
    options: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB)
    item_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSONB)

    framework: Mapped[Framework] = relationship(back_populates="assessment_items")
    responses: Mapped[list[AssessmentResponse]] = relationship(
        back_populates="assessment_item", cascade="all, delete-orphan"
    )


class Journey(db.Model):
    __tablename__ = "journeys"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    framework_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("frameworks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content_md: Mapped[str] = mapped_column(Text, nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    framework: Mapped[Framework] = relationship(back_populates="journeys")


# ---------------------------------------------------------------------------
# DOMÍNIO EXECUÇÃO — Core + Framework
# ---------------------------------------------------------------------------


class TenantFramework(db.Model):
    __tablename__ = "tenant_frameworks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    framework_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("frameworks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    status: Mapped[str] = mapped_column(String(64), nullable=False, default="active")

    tenant: Mapped[Tenant] = relationship(back_populates="tenant_frameworks")
    framework: Mapped[Framework] = relationship(back_populates="tenant_frameworks")


class AssessmentResponse(db.Model):
    __tablename__ = "assessment_responses"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    submission_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("assessment_submissions.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    assessment_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("assessment_items.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    selected_value: Mapped[float | None] = mapped_column(Float)
    raw_response: Mapped[dict[str, Any] | None] = mapped_column(JSONB)

    tenant: Mapped[Tenant] = relationship(back_populates="assessment_responses")
    submission: Mapped[AssessmentSubmission | None] = relationship(back_populates="responses")
    assessment_item: Mapped[AssessmentItem] = relationship(back_populates="responses")
    user: Mapped[User] = relationship(back_populates="assessment_responses")


class AssessmentSubmission(db.Model):
    """Cabeçalho de survey/diagnóstico — equivalente ao ctdi_matu + sessão ctdi_surv."""

    __tablename__ = "assessment_submissions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    framework_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("frameworks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    score_global: Mapped[float | None] = mapped_column(Float)
    maturity_level_name: Mapped[str | None] = mapped_column(String(255))
    scores_por_eixo: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    # Scores PanelDX (ctdi_matu) — Presente / Futuro / Gap
    pdom_pres: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    pdim_pres: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    pgen_pres: Mapped[float | None] = mapped_column(Float)
    pdom_fut: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    pdim_fut: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    pgen_fut: Mapped[float | None] = mapped_column(Float)
    pdom_gap: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    pdim_gap: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    pgen_gap: Mapped[float | None] = mapped_column(Float)
    pdom_sect_pres: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    pdim_sect_pres: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    pgen_sect_pres: Mapped[float | None] = mapped_column(Float)
    pdom_sect_fut: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    pdim_sect_fut: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    pgen_sect_fut: Mapped[float | None] = mapped_column(Float)
    pdom_sect_gap: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    pdim_sect_gap: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    pgen_sect_gap: Mapped[float | None] = mapped_column(Float)
    matrix_domain_stats: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    matrix_meta: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    diagnostic_status: Mapped[str | None] = mapped_column(String(32))
    evaluated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    report_data: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    action_plan_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("action_plans.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(64), nullable=False, default="completed")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    tenant: Mapped[Tenant] = relationship(back_populates="assessment_submissions")
    user: Mapped[User] = relationship(back_populates="assessment_submissions")
    framework: Mapped[Framework] = relationship()
    action_plan: Mapped[ActionPlan | None] = relationship()
    responses: Mapped[list[AssessmentResponse]] = relationship(
        back_populates="submission", cascade="all, delete-orphan"
    )


class ActionPlan(db.Model):
    __tablename__ = "action_plans"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    framework_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("frameworks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    ai_generated_md: Mapped[str] = mapped_column(Text, nullable=False)
    structured_plan: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    tenant: Mapped[Tenant] = relationship(back_populates="action_plans")
    framework: Mapped[Framework] = relationship(back_populates="action_plans")

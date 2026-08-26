"""Persistência analítica. Sem cópia dos fatos operacionais."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKeyConstraint, Index, Integer, Text, Uuid, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


def _uuid_pk():
    return mapped_column(Uuid, primary_key=True, server_default=text("gen_random_uuid()"))


def _created_at():
    return mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class ReportingSavedView(Base):
    __tablename__ = "reporting_saved_view"
    __table_args__ = (
        Index("uq_reporting_saved_view_id_org", "id", "organization_id", unique=True),
        Index("uq_reporting_saved_view_org_code", "organization_id", "code", unique=True),
    )

    id: Mapped[UUID] = _uuid_pk()
    organization_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    code: Mapped[str] = mapped_column(Text, nullable=False)
    display_name: Mapped[str] = mapped_column(Text, nullable=False)
    report_code: Mapped[str] = mapped_column(Text, nullable=False)
    filters: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    created_by_user_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    row_version: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    created_at: Mapped[datetime] = _created_at()


class ReportingDashboardPreference(Base):
    __tablename__ = "reporting_dashboard_preference"
    __table_args__ = (
        Index("uq_reporting_pref_id_org", "id", "organization_id", unique=True),
        Index(
            "uq_reporting_pref_user_report",
            "organization_id",
            "user_id",
            "report_code",
            unique=True,
        ),
    )

    id: Mapped[UUID] = _uuid_pk()
    organization_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    user_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    report_code: Mapped[str] = mapped_column(Text, nullable=False)
    layout: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    row_version: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    created_at: Mapped[datetime] = _created_at()


class ReportingExecution(Base):
    __tablename__ = "reporting_execution"
    __table_args__ = (
        Index("uq_reporting_execution_id_org", "id", "organization_id", unique=True),
        Index("ix_reporting_execution_org_created", "organization_id", "created_at"),
    )

    id: Mapped[UUID] = _uuid_pk()
    organization_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    report_code: Mapped[str] = mapped_column(Text, nullable=False)
    report_version: Mapped[str] = mapped_column(Text, nullable=False)
    query_version: Mapped[str] = mapped_column(Text, nullable=False)
    metrics_version: Mapped[str] = mapped_column(Text, nullable=False)
    filters: Mapped[dict] = mapped_column(JSONB, nullable=False)
    timezone: Mapped[str] = mapped_column(Text, nullable=False)
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    data_cutoff_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completeness: Mapped[str] = mapped_column(Text, nullable=False)
    coverage: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    content_hash: Mapped[str] = mapped_column(Text, nullable=False)
    actor_user_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    created_at: Mapped[datetime] = _created_at()


class ReportingSnapshot(Base):
    __tablename__ = "reporting_snapshot"
    __table_args__ = (
        Index("uq_reporting_snapshot_id_org", "id", "organization_id", unique=True),
        Index("uq_reporting_snapshot_execution", "reporting_execution_id", unique=True),
        ForeignKeyConstraint(
            ["reporting_execution_id", "organization_id"],
            ["reporting_execution.id", "reporting_execution.organization_id"],
            ondelete="RESTRICT",
        ),
    )

    id: Mapped[UUID] = _uuid_pk()
    organization_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    reporting_execution_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    content_hash: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = _created_at()


class ReportingCoverageItem(Base):
    __tablename__ = "reporting_coverage_item"
    __table_args__ = (
        Index("uq_reporting_coverage_id_org", "id", "organization_id", unique=True),
        ForeignKeyConstraint(
            ["reporting_execution_id", "organization_id"],
            ["reporting_execution.id", "reporting_execution.organization_id"],
            ondelete="RESTRICT",
        ),
    )

    id: Mapped[UUID] = _uuid_pk()
    organization_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    reporting_execution_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    domain: Mapped[str] = mapped_column(Text, nullable=False)
    universe: Mapped[int] = mapped_column(Integer, nullable=False)
    valid_count: Mapped[int] = mapped_column(Integer, nullable=False)
    missing_count: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = _created_at()


class ReportingExport(Base):
    __tablename__ = "reporting_export"
    __table_args__ = (
        Index("uq_reporting_export_id_org", "id", "organization_id", unique=True),
        ForeignKeyConstraint(
            ["reporting_execution_id", "organization_id"],
            ["reporting_execution.id", "reporting_execution.organization_id"],
            ondelete="RESTRICT",
        ),
    )

    id: Mapped[UUID] = _uuid_pk()
    organization_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    reporting_execution_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    kind: Mapped[str] = mapped_column(Text, nullable=False)
    row_count: Mapped[int] = mapped_column(Integer, nullable=False)
    content_hash: Mapped[str] = mapped_column(Text, nullable=False)
    created_by_user_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    created_at: Mapped[datetime] = _created_at()


class ReportingCommand(Base):
    __tablename__ = "reporting_command"
    __table_args__ = (
        Index("uq_reporting_command_id_org", "id", "organization_id", unique=True),
        Index("uq_reporting_command_idempotency", "organization_id", "idempotency_key", unique=True),
    )

    id: Mapped[UUID] = _uuid_pk()
    organization_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    idempotency_key: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    command: Mapped[str] = mapped_column(Text, nullable=False)
    payload_digest: Mapped[str] = mapped_column(Text, nullable=False)
    resource_type: Mapped[str] = mapped_column(Text, nullable=False)
    resource_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    actor_user_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    created_at: Mapped[datetime] = _created_at()

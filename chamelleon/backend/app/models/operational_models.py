"""Modelos do módulo operacional — unidades, planejamento e execução Gemba."""

from __future__ import annotations

import enum
import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.models import db


class IndustryType(str, enum.Enum):
    CONSTRUCAO = "Construcao"
    VAREJO = "Varejo"
    TI = "TI"
    TELECOM = "Telecom"
    INDUSTRIAL = "Industrial"
    EDUCACAO = "Educacao"
    SAUDE = "Saude"
    OUTRO = "Outro"


INDUSTRY_CONSTRUCAO = IndustryType.CONSTRUCAO.value


class OperationalSite(db.Model):
    """Unidade operacional do tenant — espelhada no satélite quando aplicável."""

    __tablename__ = "operational_sites"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    location: Mapped[str | None] = mapped_column(String(512))
    # VARCHAR (não enum nativo PostgreSQL) — aceita valores legados e novos sem migração destrutiva.
    industry_type: Mapped[str] = mapped_column(
        String(64), nullable=False, default=INDUSTRY_CONSTRUCAO
    )
    manager_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    satellite_site_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    # Cache local do planejamento semanal { "YYYY-MM-DD": "meta..." }
    weekly_goals: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    def to_dict(self) -> dict[str, Any]:
        industry = str(self.industry_type or INDUSTRY_CONSTRUCAO)
        return {
            "id": str(self.id),
            "tenant_id": str(self.tenant_id),
            "name": self.name,
            "location": self.location,
            "industry_type": industry,
            "manager_id": str(self.manager_id) if self.manager_id else None,
            "satellite_site_id": self.satellite_site_id,
            "is_active": self.is_active,
            "weekly_goals": self.weekly_goals or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class DailyExecutionReport(db.Model):
    """Consolidação bottom-up da Daily Ágil assinada no satélite."""

    __tablename__ = "daily_execution_reports"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    operational_site_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("operational_sites.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    gemba_event_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    report_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    sprint_daily_goal: Mapped[str | None] = mapped_column(Text)
    goal_achieved: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    impediment_details: Mapped[str | None] = mapped_column(Text)
    mitigation_action: Mapped[str | None] = mapped_column(Text)
    preventive_action: Mapped[str | None] = mapped_column(Text)
    raw_payload: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    def to_dict(self) -> dict[str, Any]:
        site_id = str(self.operational_site_id) if self.operational_site_id else None
        return {
            "id": str(self.id),
            "tenant_id": str(self.tenant_id),
            "site_id": site_id,
            "operational_site_id": site_id,
            "gemba_event_id": str(self.gemba_event_id) if self.gemba_event_id else None,
            "date": self.report_date.isoformat(),
            "report_date": self.report_date.isoformat(),
            "sprint_daily_goal": self.sprint_daily_goal,
            "goal_achieved": self.goal_achieved,
            "impediment_details": self.impediment_details,
            "mitigation_action": self.mitigation_action,
            "preventive_action": self.preventive_action,
            "raw_payload": self.raw_payload,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

"""OKR / Planejamento Estratégico — Direcionadores, Objetivos, KRs e KPIs."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.models import db


class OkrDriver(db.Model):
    """Direcionador canônico do Planejamento Estratégico (OKR)."""

    __tablename__ = "okr_drivers"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    objectives: Mapped[list[OkrObjective]] = relationship(
        back_populates="driver",
        cascade="all, delete-orphan",
        order_by="OkrObjective.created_at",
    )
    kpis: Mapped[list[OkrKpi]] = relationship(
        back_populates="driver",
        cascade="all, delete-orphan",
        order_by="OkrKpi.created_at",
    )

    def to_dict(self, *, include_tree: bool = False) -> dict[str, Any]:
        data: dict[str, Any] = {
            "id": str(self.id),
            "tenant_id": str(self.tenant_id),
            "name": self.name,
            "sort_order": self.sort_order,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_tree:
            data["objectives"] = [obj.to_dict(include_krs=True) for obj in self.objectives]
            data["kpis"] = [kpi.to_dict() for kpi in self.kpis]
        return data


class OkrObjective(db.Model):
    """Objetivo associado a um Direcionador."""

    __tablename__ = "okr_objectives"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    driver_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("okr_drivers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    driver: Mapped[OkrDriver] = relationship(back_populates="objectives")
    key_results: Mapped[list[OkrKeyResult]] = relationship(
        back_populates="objective",
        cascade="all, delete-orphan",
        order_by="OkrKeyResult.created_at",
    )

    def to_dict(self, *, include_krs: bool = False) -> dict[str, Any]:
        data: dict[str, Any] = {
            "id": str(self.id),
            "tenant_id": str(self.tenant_id),
            "driver_id": str(self.driver_id),
            "description": self.description,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_krs:
            data["key_results"] = [kr.to_dict() for kr in self.key_results]
        return data


class OkrKeyResult(db.Model):
    """Key Result mensurável de um Objetivo."""

    __tablename__ = "okr_key_results"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    objective_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("okr_objectives.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    target_value: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    current_value: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    metric_unit: Mapped[str] = mapped_column(String(64), nullable=False, default="%")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    objective: Mapped[OkrObjective] = relationship(back_populates="key_results")

    def progress_pct(self) -> float:
        if not self.target_value:
            return 0.0
        return round(min(100.0, max(0.0, (self.current_value / self.target_value) * 100.0)), 1)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": str(self.id),
            "tenant_id": str(self.tenant_id),
            "objective_id": str(self.objective_id),
            "description": self.description,
            "target_value": self.target_value,
            "current_value": self.current_value,
            "metric_unit": self.metric_unit,
            "progress_pct": self.progress_pct(),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class OkrKpi(db.Model):
    """KPI associado a um Direcionador (financeiro ou operacional)."""

    __tablename__ = "okr_kpis"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    driver_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("okr_drivers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    target_value: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    current_value: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    is_financial: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    metric_unit: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    driver: Mapped[OkrDriver] = relationship(back_populates="kpis")

    def progress_pct(self) -> float:
        if not self.target_value:
            return 0.0
        return round(min(100.0, max(0.0, (self.current_value / self.target_value) * 100.0)), 1)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": str(self.id),
            "tenant_id": str(self.tenant_id),
            "driver_id": str(self.driver_id),
            "name": self.name,
            "target_value": self.target_value,
            "current_value": self.current_value,
            "is_financial": bool(self.is_financial),
            "metric_unit": self.metric_unit,
            "progress_pct": self.progress_pct(),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

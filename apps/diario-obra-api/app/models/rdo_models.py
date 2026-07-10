"""Modelos RDO — Gemba / canteiro de obras (mobile-first)."""

from __future__ import annotations

import enum
import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import Boolean, Date, DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db


class WeatherPeriod(str, enum.Enum):
    SOL = "SOL"
    CHUVA = "CHUVA"
    NUBLADO = "NUBLADO"


class DailyLogStatus(str, enum.Enum):
    RASCUNHO = "Rascunho"
    ASSINADO = "Assinado"
    SINCRONIZADO = "Sincronizado"


class WorkforceType(str, enum.Enum):
    PROPRIA = "Propria"
    TERCEIRIZADA = "Terceirizada"


class EquipmentOperationalStatus(str, enum.Enum):
    OPERANDO = "Operando"
    PARADO_POR_QUEBRA = "Parado por Quebra"
    CHEGOU = "Chegou"
    SAIU = "Saiu"


class OccurrenceType(str, enum.Enum):
    ACIDENTE = "Acidente"
    FALTA_MATERIAL = "Falta_Material"
    QUEDA_ENERGIA = "Queda_Energia"
    CHUVA_FORTE = "Chuva_Forte"
    GERAL = "Geral"


class ProjectSite(db.Model):
    """Canteiro de obra vinculado a um tenant (referência lógica)."""

    __tablename__ = "project_sites"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    location: Mapped[str | None] = mapped_column(String(512))
    rt_engineer_name: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    daily_logs: Mapped[list[DailyLog]] = relationship(
        "DailyLog", back_populates="project", cascade="all, delete-orphan"
    )


class DailyLog(db.Model):
    """Relatório Diário de Obra (RDO) — registro principal do Gemba."""

    __tablename__ = "daily_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("project_sites.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    log_date: Mapped[date] = mapped_column("date", Date, nullable=False, index=True)
    weather_morning: Mapped[WeatherPeriod | None] = mapped_column(
        Enum(WeatherPeriod, name="weather_period_enum", native_enum=False)
    )
    weather_afternoon: Mapped[WeatherPeriod | None] = mapped_column(
        Enum(WeatherPeriod, name="weather_period_enum", native_enum=False)
    )
    status: Mapped[DailyLogStatus] = mapped_column(
        Enum(DailyLogStatus, name="daily_log_status_enum", native_enum=False),
        nullable=False,
        default=DailyLogStatus.RASCUNHO,
    )
    technical_comments: Mapped[str | None] = mapped_column(Text)
    is_signed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    signed_by: Mapped[str | None] = mapped_column(String(255))
    signed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ppe_compliant: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    ppe_compliant_details: Mapped[str | None] = mapped_column(Text)
    supplies_data: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB, default=list)
    delay_waiting_material: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    delay_rework: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    delay_lack_of_front: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    end_shift_clean: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    end_shift_tools_stored: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    end_shift_loose_materials: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    sprint_daily_goal: Mapped[str | None] = mapped_column(Text)
    sprint_goal_locked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    goal_achieved: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    impediment_details: Mapped[str | None] = mapped_column(Text)
    mitigation_action: Mapped[str | None] = mapped_column(Text)
    preventive_action: Mapped[str | None] = mapped_column(Text)
    reopened_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reopened_by: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    project: Mapped[ProjectSite] = relationship("ProjectSite", back_populates="daily_logs")
    workforce: Mapped[list[Workforce]] = relationship(
        "Workforce", back_populates="daily_log", cascade="all, delete-orphan"
    )
    equipment_statuses: Mapped[list[EquipmentStatus]] = relationship(
        "EquipmentStatus", back_populates="daily_log", cascade="all, delete-orphan"
    )
    executed_services: Mapped[list[ExecutedService]] = relationship(
        "ExecutedService", back_populates="daily_log", cascade="all, delete-orphan"
    )
    occurrences: Mapped[list[Occurrence]] = relationship(
        "Occurrence", back_populates="daily_log", cascade="all, delete-orphan"
    )


class Workforce(db.Model):
    """Mão de obra presente no canteiro no dia do RDO."""

    __tablename__ = "workforce"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    daily_log_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("daily_logs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(String(120), nullable=False)
    headcount: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    workforce_type: Mapped[WorkforceType] = mapped_column(
        "type",
        Enum(WorkforceType, name="workforce_type_enum", native_enum=False),
        nullable=False,
        default=WorkforceType.PROPRIA,
    )
    company_name: Mapped[str | None] = mapped_column(String(255))
    presence_details: Mapped[str | None] = mapped_column(Text)
    absences_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    absences_details: Mapped[str | None] = mapped_column(Text)
    extra_hours_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    extra_hours_details: Mapped[str | None] = mapped_column(Text)
    general_remarks: Mapped[str | None] = mapped_column(Text)
    # legado — mantidos para migração; preferir absences_count / extra_hours_count
    overtime_hours: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    absences: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    daily_log: Mapped[DailyLog] = relationship("DailyLog", back_populates="workforce")


class EquipmentStatus(db.Model):
    """Situação de maquinário no dia do RDO."""

    __tablename__ = "equipment_statuses"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    daily_log_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("daily_logs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    equipment_name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[EquipmentOperationalStatus] = mapped_column(
        Enum(EquipmentOperationalStatus, name="equipment_status_enum", native_enum=False),
        nullable=False,
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    remarks: Mapped[str | None] = mapped_column(Text)

    daily_log: Mapped[DailyLog] = relationship("DailyLog", back_populates="equipment_statuses")


class ExecutedService(db.Model):
    """Avanço físico / serviços executados no dia."""

    __tablename__ = "executed_services"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    daily_log_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("daily_logs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    location_on_site: Mapped[str | None] = mapped_column(String(255))
    remarks: Mapped[str | None] = mapped_column(Text)

    daily_log: Mapped[DailyLog] = relationship("DailyLog", back_populates="executed_services")


class Occurrence(db.Model):
    """Eventos críticos, segurança e impedimentos de campo."""

    __tablename__ = "occurrences"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    daily_log_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("daily_logs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    type: Mapped[OccurrenceType] = mapped_column(
        Enum(OccurrenceType, name="occurrence_type_enum", native_enum=False),
        nullable=False,
    )
    exact_location: Mapped[str] = mapped_column(Text, nullable=False)
    what_happened: Mapped[str] = mapped_column(Text, nullable=False)
    immediate_action_taken: Mapped[str | None] = mapped_column(Text, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)  # legado — espelha what_happened
    photo_url: Mapped[str | None] = mapped_column(String(2048))
    safety_ppe_notes: Mapped[str | None] = mapped_column(Text)

    daily_log: Mapped[DailyLog] = relationship("DailyLog", back_populates="occurrences")


class ProjectDirectives(db.Model):
    """Diretrizes operacionais recebidas do Chamelleon (integração desacoplada)."""

    __tablename__ = "project_directives"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    framework_id: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    framework_version: Mapped[str | None] = mapped_column(String(64))
    source_system: Mapped[str] = mapped_column(String(64), nullable=False, default="chamelleon")
    directives_payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

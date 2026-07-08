"""Módulo Gemba-Kaizen — eventos, tickets Lean e Gemba Walks (5 Regras de Ouro / Imai)."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.models import db

# --- Ingestão (micro-serviços satélites) ---
SOURCE_APP_DIARIO_OBRA = "diario_obra"
EVENT_TYPE_RDO_FINALIZED = "rdo_finalized"

# --- Insights legados (Kanban IA — fase futura) ---
PRIORITY_ALTA = "Alta"
PRIORITY_MEDIA = "Media"
PRIORITY_BAIXA = "Baixa"
KAIZEN_PRIORITIES = (PRIORITY_ALTA, PRIORITY_MEDIA, PRIORITY_BAIXA)

STATUS_BACKLOG = "Backlog"
STATUS_DOING = "Doing"
STATUS_DONE = "Done"
KAIZEN_STATUSES = (STATUS_BACKLOG, STATUS_DOING, STATUS_DONE)

# --- Jornada Lean do ticket Kaizen ---
STAGE_ALERTA = "Alerta"
STAGE_CONTENCAO = "Contencao"
STAGE_CINCO_PORQUES = "Cinco_Porques"
STAGE_PADRONIZACAO = "Padronizacao"
STAGE_CONCLUIDO = "Concluido"
KAIZEN_WORKFLOW_STAGES = (
    STAGE_ALERTA,
    STAGE_CONTENCAO,
    STAGE_CINCO_PORQUES,
    STAGE_PADRONIZACAO,
    STAGE_CONCLUIDO,
)

DEFAULT_ROOT_CAUSE_ANALYSIS: dict[str, str] = {
    "why_1": "",
    "why_2": "",
    "why_3": "",
    "why_4": "",
    "why_5": "",
    "root_cause": "",
}

# --- Gemba Walk ---
FOCUS_5S = "5S"
FOCUS_STANDARD_WORK = "Standard_Work"
FOCUS_SAFETY = "Safety"
FOCUS_MUDA_WASTE = "Muda_Waste"
GEMBA_FOCUS_AREAS = (FOCUS_5S, FOCUS_STANDARD_WORK, FOCUS_SAFETY, FOCUS_MUDA_WASTE)

WALK_AGENDADO = "Agendado"
WALK_EM_ANDAMENTO = "Em_Andamento"
WALK_CONCLUIDO = "Concluido"
GEMBA_WALK_STATUSES = (WALK_AGENDADO, WALK_EM_ANDAMENTO, WALK_CONCLUIDO)


class GembaEvent(db.Model):
    """Evento operacional ingerido de micro-serviços satélites (ex.: RDO finalizado)."""

    __tablename__ = "gemba_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source_app: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    event_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    raw_payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    processed_by_ai: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    kaizen_tickets: Mapped[list[KaizenTicket]] = relationship(
        back_populates="origin_event",
        foreign_keys="KaizenTicket.origin_event_id",
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": str(self.id),
            "tenant_id": str(self.tenant_id),
            "source_app": self.source_app,
            "event_date": self.event_date.isoformat(),
            "event_type": self.event_type,
            "raw_payload": self.raw_payload,
            "processed_by_ai": self.processed_by_ai,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class KaizenInsight(db.Model):
    """Insight derivado de eventos Gemba — futuro insumo para Kanban / IA."""

    __tablename__ = "kaizen_insights"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    priority: Mapped[str] = mapped_column(String(16), nullable=False, default=PRIORITY_MEDIA)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default=STATUS_BACKLOG)
    related_events: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": str(self.id),
            "tenant_id": str(self.tenant_id),
            "title": self.title,
            "description": self.description,
            "priority": self.priority,
            "status": self.status,
            "related_events": self.related_events or [],
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class KaizenTicket(db.Model):
    """Ticket Kaizen — jornada Lean desde o alerta até a padronização (POP)."""

    __tablename__ = "kaizen_tickets"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    origin_event_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("gemba_events.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    workflow_stage: Mapped[str] = mapped_column(
        String(32), nullable=False, default=STAGE_ALERTA, index=True
    )
    temporary_containment_action: Mapped[str | None] = mapped_column(Text, nullable=True)
    root_cause_analysis: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=lambda: dict(DEFAULT_ROOT_CAUSE_ANALYSIS)
    )
    standardization_action: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_operator_retrained: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    origin_event: Mapped[GembaEvent | None] = relationship(
        back_populates="kaizen_tickets",
        foreign_keys=[origin_event_id],
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": str(self.id),
            "tenant_id": str(self.tenant_id),
            "origin_event_id": str(self.origin_event_id) if self.origin_event_id else None,
            "title": self.title,
            "description": self.description,
            "workflow_stage": self.workflow_stage,
            "temporary_containment_action": self.temporary_containment_action,
            "root_cause_analysis": self.root_cause_analysis or dict(DEFAULT_ROOT_CAUSE_ANALYSIS),
            "standardization_action": self.standardization_action,
            "is_operator_retrained": self.is_operator_retrained,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class GembaWalk(db.Model):
    """Gemba Walk agendada — observação no gemba (5S, Standard Work, Safety, Muda)."""

    __tablename__ = "gemba_walks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    scheduled_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    focus_area: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default=WALK_AGENDADO, index=True
    )
    conducted_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    checklist_items: Mapped[list[GembaChecklistItem]] = relationship(
        back_populates="gemba_walk",
        cascade="all, delete-orphan",
        order_by="GembaChecklistItem.created_at",
    )

    def to_dict(self, *, include_checklist: bool = False) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "id": str(self.id),
            "tenant_id": str(self.tenant_id),
            "scheduled_date": self.scheduled_date.isoformat(),
            "focus_area": self.focus_area,
            "status": self.status,
            "conducted_by": str(self.conducted_by) if self.conducted_by else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_checklist:
            payload["checklist_items"] = [item.to_dict() for item in self.checklist_items]
        return payload


class GembaChecklistItem(db.Model):
    """Item de checklist executado durante um Gemba Walk."""

    __tablename__ = "gemba_checklist_items"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    gemba_walk_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("gemba_walks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    question: Mapped[str] = mapped_column(Text, nullable=False)
    is_compliant: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    immediate_action_taken: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    gemba_walk: Mapped[GembaWalk] = relationship(back_populates="checklist_items")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": str(self.id),
            "gemba_walk_id": str(self.gemba_walk_id),
            "question": self.question,
            "is_compliant": self.is_compliant,
            "immediate_action_taken": self.immediate_action_taken,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

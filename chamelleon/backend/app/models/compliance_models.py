"""Conformidade operacional — treinamento, ASO e não-conformidade (NR-18 / SiAC)."""

from __future__ import annotations

import enum
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Any

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.models import db


class TrainingType(str, enum.Enum):
    ADMISSIONAL = "Admissional"
    PERIODICO = "Periodico"
    NR35 = "NR-35"
    NR10 = "NR-10"
    NR12 = "NR-12"
    NR33 = "NR-33"
    OUTRO = "Outro"


class ExamType(str, enum.Enum):
    ADMISSIONAL = "Admissional"
    PERIODICO = "Periodico"
    DEMISSIONAL = "Demissional"
    MUDANCA_RISCO = "Mudanca_Risco"
    RETORNO_TRABALHO = "Retorno_Trabalho"


class ExamResult(str, enum.Enum):
    APTO = "Apto"
    INAPTO = "Inapto"


class NonConformityCategory(str, enum.Enum):
    SEGURANCA = "Seguranca"
    QUALIDADE = "Qualidade"


class NonConformityStatus(str, enum.Enum):
    ABERTA = "Aberta"
    EM_TRATATIVA = "Em_Tratativa"
    FECHADA = "Fechada"


class NcOwnerSource(str, enum.Enum):
    HERDADO = "Herdado"
    MANUAL = "Manual"


class RecurrenceSignalStatus(str, enum.Enum):
    NOVO = "Novo"
    VISTO = "Visto"
    CONVERTIDO = "Convertido"
    DISPENSADO = "Dispensado"


class CorrectiveActionProjectStatus(str, enum.Enum):
    ABERTO = "Aberto"
    EM_ANDAMENTO = "Em_Andamento"
    CONCLUIDO = "Concluido"


TRAINING_TYPES = tuple(t.value for t in TrainingType)
EXAM_TYPES = tuple(t.value for t in ExamType)
EXAM_RESULTS = tuple(t.value for t in ExamResult)
NC_CATEGORIES = tuple(t.value for t in NonConformityCategory)
NC_STATUSES = tuple(t.value for t in NonConformityStatus)
NC_OWNER_SOURCES = tuple(s.value for s in NcOwnerSource)
RECURRENCE_SIGNAL_STATUSES = tuple(s.value for s in RecurrenceSignalStatus)
CORRECTIVE_ACTION_PROJECT_STATUSES = tuple(s.value for s in CorrectiveActionProjectStatus)

# Rubricas operacionais derivadas do Andon (além de Seguranca/Qualidade).
NC_OPERATIONAL_RUBRICS = (
    "EPI",
    "Acidente",
    "Absenteismo",
    "Equipamento",
    "Material",
    "Frente",
    "Energia",
    "Clima",
    "Geral",
)


def _validity_status(expires_at: date | None, *, today: date | None = None) -> str:
    if expires_at is None:
        return "sem_validade"
    ref = today or date.today()
    if expires_at < ref:
        return "vencido"
    if expires_at <= ref + timedelta(days=30):
        return "a_vencer"
    return "valido"


class TrainingRecord(db.Model):
    """Treinamento de segurança vinculado a um Professional."""

    __tablename__ = "training_records"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    professional_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("professionals.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    training_type: Mapped[str] = mapped_column(String(32), nullable=False)
    custom_label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    completed_at: Mapped[date] = mapped_column(Date, nullable=False)
    expires_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    hours: Mapped[int | None] = mapped_column(Integer, nullable=True)
    certificate_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": str(self.id),
            "tenant_id": str(self.tenant_id),
            "professional_id": str(self.professional_id),
            "training_type": self.training_type,
            "custom_label": self.custom_label,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "hours": self.hours,
            "certificate_url": self.certificate_url,
            "notes": self.notes,
            "status": _validity_status(self.expires_at),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class HealthRecord(db.Model):
    """ASO / exame ocupacional vinculado a um Professional."""

    __tablename__ = "health_records"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    professional_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("professionals.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    exam_type: Mapped[str] = mapped_column(String(32), nullable=False)
    exam_date: Mapped[date] = mapped_column(Date, nullable=False)
    expires_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    result: Mapped[str] = mapped_column(
        String(16), nullable=False, default=ExamResult.APTO.value
    )
    attachment_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    def to_dict(self) -> dict[str, Any]:
        status = (
            "vencido"
            if self.result == ExamResult.INAPTO.value
            else _validity_status(self.expires_at)
        )
        return {
            "id": str(self.id),
            "tenant_id": str(self.tenant_id),
            "professional_id": str(self.professional_id),
            "exam_type": self.exam_type,
            "exam_date": self.exam_date.isoformat() if self.exam_date else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "result": self.result,
            "attachment_url": self.attachment_url,
            "notes": self.notes,
            "status": status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class NonConformity(db.Model):
    """Não-conformidade formal (NR-18 / SiAC) — espelhada de KaizenTicket crítico."""

    __tablename__ = "non_conformities"
    __table_args__ = (
        UniqueConstraint("source_kaizen_ticket_id", name="uq_nc_source_kaizen_ticket"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    operational_site_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("operational_sites.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    source_kaizen_ticket_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("kaizen_tickets.id", ondelete="SET NULL"),
        nullable=True,
        unique=True,
    )
    category: Mapped[str] = mapped_column(
        String(64), nullable=False, default=NonConformityCategory.SEGURANCA.value, index=True
    )
    severity: Mapped[str | None] = mapped_column(String(16), nullable=True)
    norm_refs: Mapped[list[Any] | None] = mapped_column(JSONB, nullable=True, default=list)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    corrective_action: Mapped[str | None] = mapped_column(Text, nullable=True)
    owner_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    owner_source: Mapped[str] = mapped_column(
        String(16), nullable=False, default=NcOwnerSource.HERDADO.value
    )
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default=NonConformityStatus.ABERTA.value
    )
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_evidence: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": str(self.id),
            "tenant_id": str(self.tenant_id),
            "operational_site_id": (
                str(self.operational_site_id) if self.operational_site_id else None
            ),
            "source_kaizen_ticket_id": (
                str(self.source_kaizen_ticket_id) if self.source_kaizen_ticket_id else None
            ),
            "category": self.category,
            "severity": self.severity,
            "norm_refs": list(self.norm_refs or []),
            "title": self.title,
            "description": self.description,
            "corrective_action": self.corrective_action,
            "owner_user_id": str(self.owner_user_id) if self.owner_user_id else None,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "owner_source": self.owner_source or NcOwnerSource.HERDADO.value,
            "status": self.status,
            "closed_at": self.closed_at.isoformat() if self.closed_at else None,
            "closed_evidence": self.closed_evidence,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class CorrectiveActionProject(db.Model):
    """Projeto de ação corretiva — aberto manualmente a partir de um sinal de recorrência."""

    __tablename__ = "corrective_action_projects"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    operational_site_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("operational_sites.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    root_cause_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    owner_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default=CorrectiveActionProjectStatus.ABERTO.value, index=True
    )
    closed_evidence: Mapped[str | None] = mapped_column(Text, nullable=True)
    linked_non_conformity_ids: Mapped[list[Any] | None] = mapped_column(
        JSONB, nullable=True, default=list
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": str(self.id),
            "tenant_id": str(self.tenant_id),
            "title": self.title,
            "category": self.category,
            "operational_site_id": (
                str(self.operational_site_id) if self.operational_site_id else None
            ),
            "root_cause_notes": self.root_cause_notes,
            "owner_user_id": str(self.owner_user_id) if self.owner_user_id else None,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "status": self.status,
            "closed_evidence": self.closed_evidence,
            "linked_non_conformity_ids": list(self.linked_non_conformity_ids or []),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class RecurrenceSignal(db.Model):
    """Sinal de recorrência — padrão operacional (categoria + canteiro) repetido na janela."""

    __tablename__ = "recurrence_signals"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    operational_site_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("operational_sites.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    category: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    non_conformity_ids: Mapped[list[Any] | None] = mapped_column(
        JSONB, nullable=True, default=list
    )
    occurrence_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    window_start: Mapped[date] = mapped_column(Date, nullable=False)
    window_end: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default=RecurrenceSignalStatus.NOVO.value, index=True
    )
    corrective_action_project_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("corrective_action_projects.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": str(self.id),
            "tenant_id": str(self.tenant_id),
            "operational_site_id": (
                str(self.operational_site_id) if self.operational_site_id else None
            ),
            "category": self.category,
            "non_conformity_ids": list(self.non_conformity_ids or []),
            "occurrence_count": self.occurrence_count,
            "window_start": self.window_start.isoformat() if self.window_start else None,
            "window_end": self.window_end.isoformat() if self.window_end else None,
            "status": self.status,
            "corrective_action_project_id": (
                str(self.corrective_action_project_id)
                if self.corrective_action_project_id
                else None
            ),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

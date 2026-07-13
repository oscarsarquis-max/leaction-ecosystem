"""Capacity Planning — Pool de Talentos e Squad 1:1 por Sprint TD."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, Table, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.models import db


class ProfessionalRole(str, enum.Enum):
    PO = "PO"
    SCRUM_MASTER = "Scrum_Master"
    DEV = "Dev"
    QA = "QA"
    ANALISTA_TI = "Analista_TI"
    ANALISTA_NEGOCIO = "Analista_Negocio"
    GERENTE_PROJETO = "Gerente_Projeto"
    OUTRO = "Outro"


PROFESSIONAL_ROLES = tuple(role.value for role in ProfessionalRole)

SQUAD_MAX_TOTAL_MEMBERS = 8
SQUAD_MAX_SPECIALISTS = 6
SQUAD_MAX_EXECUTION_ALLOCATIONS = 3
# Quota temporária do plano básico (licenças de profissionais ativos).
PROFESSIONAL_LICENSE_LIMIT = 8

sprintsquad_members = Table(
    "sprintsquad_members",
    db.metadata,
    Column(
        "sprintsquad_id",
        UUID(as_uuid=True),
        ForeignKey("sprint_squads.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "professional_id",
        UUID(as_uuid=True),
        ForeignKey("professionals.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class Professional(db.Model):
    """Pool de talentos do tenant — profissionais disponíveis para Task Forces."""

    __tablename__ = "professionals"
    __table_args__ = (
        UniqueConstraint("tenant_id", "email", name="uq_professionals_tenant_email"),
    )

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
    email: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    observations: Mapped[str | None] = mapped_column(Text, nullable=True)
    role: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
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

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": str(self.id),
            "tenant_id": str(self.tenant_id),
            "name": self.name,
            "email": self.email,
            "observations": self.observations,
            "role": self.role,
            "user_id": str(self.user_id) if self.user_id else None,
            "is_active": bool(self.is_active),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class SprintSquad(db.Model):
    """Task Force dedicada 1:1 a uma Sprint de TD."""

    __tablename__ = "sprint_squads"
    __table_args__ = (UniqueConstraint("sprint_id", name="uq_sprint_squads_sprint_id"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sprint_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("td_sprints.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    po_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("professionals.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    sm_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("professionals.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
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

    sprint = relationship(
        "TdSprint",
        backref=db.backref("squad", uselist=False, cascade="all, delete-orphan"),
    )
    po: Mapped[Professional] = relationship(foreign_keys=[po_id])
    sm: Mapped[Professional] = relationship(foreign_keys=[sm_id])
    members: Mapped[list[Professional]] = relationship(
        secondary=sprintsquad_members,
        lazy="selectin",
    )

    def is_complete(self) -> bool:
        return bool(self.po_id and self.sm_id)

    def all_professional_ids(self) -> set[uuid.UUID]:
        ids = {self.po_id, self.sm_id}
        for member in self.members or []:
            ids.add(member.id)
        return ids

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": str(self.id),
            "tenant_id": str(self.tenant_id),
            "sprint_id": str(self.sprint_id),
            "po_id": str(self.po_id),
            "sm_id": str(self.sm_id),
            "po": self.po.to_dict() if self.po else None,
            "sm": self.sm.to_dict() if self.sm else None,
            "members": [m.to_dict() for m in (self.members or [])],
            "member_ids": [str(m.id) for m in (self.members or [])],
            "is_complete": self.is_complete(),
            "size": len(self.all_professional_ids()),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

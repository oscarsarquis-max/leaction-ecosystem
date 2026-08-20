"""Unidades organizacionais não-operacionais — filiais, escritórios, depósitos."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.models import db


class OrganizationalUnitType(str, enum.Enum):
    FILIAL = "Filial"
    ESCRITORIO = "Escritorio"
    DEPOSITO = "Deposito"
    MATRIZ = "Matriz"
    OUTRO = "Outro"


ORGANIZATIONAL_UNIT_TYPES = tuple(t.value for t in OrganizationalUnitType)


class OrganizationalUnit(db.Model):
    """Unidade administrativa do tenant (filial, escritório, depósito) — não operacional."""

    __tablename__ = "organizational_units"

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
    unit_type: Mapped[str] = mapped_column(
        String(32), nullable=False, default=OrganizationalUnitType.FILIAL.value
    )
    address: Mapped[str | None] = mapped_column(String(512), nullable=True)
    responsible_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    responsible_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    responsible_phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
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
            "name": self.name,
            "unit_type": self.unit_type,
            "address": self.address,
            "responsible_name": self.responsible_name,
            "responsible_email": self.responsible_email,
            "responsible_phone": self.responsible_phone,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

"""Módulo Transformação Digital Inteligente (PanelDX) — Plano e Sprints."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.models import db


class TdKanbanStage(str, enum.Enum):
    BACKLOG = "Backlog"
    KAIZEN_ENTRADA = "Kaizen_Entrada"
    PLANEJADA = "Planejada"
    EXECUCAO = "Execucao"
    CONCLUIDA = "Concluida"


class TdOriginType(str, enum.Enum):
    BASELINE = "baseline"
    KAIZEN_EMERGENT = "kaizen_emergent"


TD_KANBAN_STAGES = tuple(stage.value for stage in TdKanbanStage)
TD_ORIGIN_TYPES = tuple(item.value for item in TdOriginType)

# Colunas do Kanban de Implementação (sem Backlog — fica no Plano Diretor)
TD_KANBAN_BOARD_STAGES = (
    TdKanbanStage.KAIZEN_ENTRADA.value,
    TdKanbanStage.PLANEJADA.value,
    TdKanbanStage.EXECUCAO.value,
    TdKanbanStage.CONCLUIDA.value,
)


class TdPlan(db.Model):
    """Plano ativo de Transformação Digital do tenant (snapshot PanelDX + sprints)."""

    __tablename__ = "td_plans"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    survey_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    sprints: Mapped[list[TdSprint]] = relationship(
        back_populates="plan",
        cascade="all, delete-orphan",
        order_by="TdSprint.created_at.asc()",
    )

    def to_dict(self, *, include_sprints: bool = False) -> dict[str, Any]:
        data: dict[str, Any] = {
            "id": str(self.id),
            "tenant_id": str(self.tenant_id),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "survey_snapshot": self.survey_snapshot or {},
            "is_active": bool(self.is_active),
        }
        if include_sprints:
            data["sprints"] = [sprint.to_dict() for sprint in self.sprints]
        return data


class TdSprint(db.Model):
    """Sprint / iniciativa do Plano de TD (Backlog → Kanban de implementação)."""

    __tablename__ = "td_sprints"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    plan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("td_plans.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    paneldx_domain: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    framework_block_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("framework_blocks.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    framework_deliverable_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("framework_deliverables.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    gap_fp: Mapped[float | None] = mapped_column(Float, nullable=True)
    origin_type: Mapped[str] = mapped_column(
        String(64), nullable=False, default=TdOriginType.BASELINE.value, index=True
    )
    # VARCHAR (não native PG enum) — mesmo padrão de industry_type / workflow_stage
    kanban_stage: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default=TdKanbanStage.BACKLOG.value,
        index=True,
    )
    goals_payload: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    origin_ref_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("kaizen_tickets.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    current_state_gap: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    plan: Mapped[TdPlan] = relationship(back_populates="sprints")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": str(self.id),
            "tenant_id": str(self.tenant_id),
            "plan_id": str(self.plan_id),
            "title": self.title,
            "description": self.description,
            "paneldx_domain": self.paneldx_domain,
            "framework_block_id": str(self.framework_block_id) if self.framework_block_id else None,
            "framework_deliverable_id": (
                str(self.framework_deliverable_id) if self.framework_deliverable_id else None
            ),
            "gap_fp": self.gap_fp,
            "block_linkage": self._block_linkage_summary(),
            "origin_type": self.origin_type,
            "kanban_stage": self.kanban_stage,
            "goals_payload": self.goals_payload or {},
            "origin_ref_id": str(self.origin_ref_id) if self.origin_ref_id else None,
            "current_state_gap": self.current_state_gap,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "is_emergent": self.origin_type == TdOriginType.KAIZEN_EMERGENT.value
            or self.kanban_stage == TdKanbanStage.KAIZEN_ENTRADA.value,
        }

    def _block_linkage_summary(self) -> dict[str, Any]:
        goals = self.goals_payload or {}
        return {
            "dimension_name": goals.get("dimension_name"),
            "domain_name": goals.get("domain_name"),
            "dimension_num": goals.get("dimension_num"),
            "name_bloc": goals.get("name_bloc"),
            "name_derv": goals.get("name_derv"),
            "legacy_id_bloc": goals.get("legacy_id_bloc"),
        }

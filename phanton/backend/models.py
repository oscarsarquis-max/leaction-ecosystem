import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class PipelineRun(Base):
    __tablename__ = "pipeline_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    spec: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )
    project_key: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    project_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    version: Mapped[Optional[str]] = mapped_column(String, nullable=True, default="1.0")
    acceptance_status: Mapped[str] = mapped_column(
        String, nullable=False, default="open", server_default="open"
    )
    accepted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    parent_run_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("pipeline_runs.id", ondelete="SET NULL"),
        nullable=True,
    )
    retorno_markdown: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    lineage_kind: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    phases: Mapped[list["PhaseExecution"]] = relationship(
        back_populates="run",
        cascade="all, delete-orphan",
        foreign_keys="PhaseExecution.run_id",
    )


class PhaseExecution(Base):
    __tablename__ = "phase_executions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("pipeline_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    phase_id: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    artifact_data: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    approver: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    comments: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    task_token: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    run: Mapped["PipelineRun"] = relationship(
        back_populates="phases",
        foreign_keys=[run_id],
    )


class PhantonImprovementProposal(Base):
    """Melhoria proposta no Phanton a partir de um retorno (decisão humana)."""

    __tablename__ = "phanton_improvement_proposals"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    source_run_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("pipeline_runs.id", ondelete="SET NULL"),
        nullable=True,
    )
    substitute_run_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("pipeline_runs.id", ondelete="SET NULL"),
        nullable=True,
    )
    title: Mapped[str] = mapped_column(String, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    items: Mapped[Optional[list[Any]]] = mapped_column(JSONB, nullable=True)
    raw_section: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False, default="pending")
    source: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    decided_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

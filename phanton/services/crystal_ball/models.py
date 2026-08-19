"""Crystal Ball ORM — tabelas dedicadas (isolamento total dos runs oficiais)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class CrystalShadowRun(Base):
    __tablename__ = "crystal_shadow_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    # Nullable: experimentos Crystal Ball puros (ex.: Mativas) sem run oficial.
    source_run_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("pipeline_runs.id", ondelete="CASCADE"),
        nullable=True,
    )
    fork_phase_id: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="forked")
    spec: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    edited_phase_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )
    predicted_quality_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    final_prompt_excerpt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # Dono do shadow (Simulação / forks). Null = legado ou admin local.
    # FK física em database/04_auth.sql (users.id) — sem ForeignKey ORM
    # para não acoplar services/crystal_ball → auth no import.
    owned_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )

    phases: Mapped[list["CrystalShadowPhase"]] = relationship(
        back_populates="shadow_run",
        cascade="all, delete-orphan",
    )


class CrystalShadowPhase(Base):
    __tablename__ = "crystal_shadow_phases"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    shadow_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("crystal_shadow_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    phase_id: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="copied")
    origin: Mapped[str] = mapped_column(String, nullable=False, default="copied")
    artifact_data: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    quality_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )

    shadow_run: Mapped["CrystalShadowRun"] = relationship(back_populates="phases")


class CrystalPrediction(Base):
    __tablename__ = "crystal_predictions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    source_run_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("pipeline_runs.id", ondelete="SET NULL"),
        nullable=True,
    )
    shadow_run_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("crystal_shadow_runs.id", ondelete="SET NULL"),
        nullable=True,
    )
    kind: Mapped[str] = mapped_column(String, nullable=False)
    predicted_quality_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    actual_quality_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    prediction_error: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    preview_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    confidence: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    calibrated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class CrystalCorpus(Base):
    __tablename__ = "crystal_corpora"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    slug: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    nome: Mapped[str] = mapped_column(String, nullable=False)
    tipo_fonte: Mapped[str] = mapped_column(String, nullable=False)
    schema_config: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    aplicacao_origem: Mapped[str] = mapped_column(
        String, nullable=False, default="Mativas"
    )
    versao_atual: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )


class CrystalSugestaoArtifact(Base):
    __tablename__ = "crystal_sugestao_artifacts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    corpus_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("crystal_corpora.id", ondelete="CASCADE"),
        nullable=False,
    )
    markdown: Mapped[str] = mapped_column(Text, nullable=False)
    meta: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )


class CrystalCicloMelhoria(Base):
    __tablename__ = "crystal_ciclos_melhoria"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    corpus_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("crystal_corpora.id", ondelete="CASCADE"),
        nullable=False,
    )
    numero_ciclo: Mapped[int] = mapped_column(Integer, nullable=False)
    data: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    nota_agregada: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    nota_por_campo: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSONB, nullable=True
    )
    sugestao_artifact_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("crystal_sugestao_artifacts.id", ondelete="SET NULL"),
        nullable=True,
    )
    shadow_run_ids: Mapped[Optional[list[Any]]] = mapped_column(JSONB, nullable=True)


class CrystalResultadoReal(Base):
    __tablename__ = "crystal_resultados_reais"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    corpus_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("crystal_corpora.id", ondelete="CASCADE"),
        nullable=False,
    )
    chave_valor: Mapped[str] = mapped_column(String, nullable=False)
    desafio_texto: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    comparison: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    numero_ciclo: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    versao_corpus: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    versao_prompt_origem: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )

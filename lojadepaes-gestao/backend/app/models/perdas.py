"""Perdas de processo, cocção e a reserva comercial.

A referência é global. O padrão e a medição pertencem à organização.
O tipo comercial fica no modelo para a etapa de Produção e Vendas; não tem tela agora.
"""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.escopo import OrgScoped
from app.models.produtos import _agora, _pk

FORMATOS = ("forma", "forma_enriquecida", "livre", "assadeira", "pequeno")
TIPOS_PERDA = ("processo", "coccao", "comercial")
ORIGENS_PERDA = ("medido", "padrao", "referencia", "manual")
FUNCOES_LINHA = ("massa", "recheio", "cobertura", "finalizacao")


class PerdaReferencia(Base):
    """Tabela curada, global. Nenhuma organização é dona dela."""

    __tablename__ = "perda_referencia"
    __table_args__ = (
        CheckConstraint("tipo IN ('processo', 'coccao', 'comercial')", name="ck_perda_referencia_tipo"),
        CheckConstraint(
            "formato IN ('qualquer', 'forma', 'forma_enriquecida', 'livre', 'assadeira', 'pequeno')",
            name="ck_perda_referencia_formato",
        ),
        CheckConstraint("sugerido >= 0 AND sugerido < 100", name="ck_perda_referencia_sugerido"),
    )

    id: Mapped[UUID] = _pk()
    tipo: Mapped[str] = mapped_column(String(12), nullable=False)
    formato: Mapped[str] = mapped_column(String(20), nullable=False)
    peso_min_g: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    peso_max_g: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    faixa_min: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    faixa_max: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    sugerido: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    confianca: Mapped[str | None] = mapped_column(String(12))
    fonte_id: Mapped[str] = mapped_column(String(40), nullable=False)
    fonte_titulo: Mapped[str] = mapped_column(String(200), nullable=False)
    fonte_url: Mapped[str | None] = mapped_column(String(300))
    nota: Mapped[str | None] = mapped_column(Text)


class PerdaPadrao(OrgScoped, Base):
    """O que a casa informou. Família e formato vazios valem para todos."""

    __tablename__ = "perda_padrao"
    __table_args__ = (
        CheckConstraint("tipo IN ('processo', 'coccao', 'comercial')", name="ck_perda_padrao_tipo"),
        CheckConstraint(
            "formato IS NULL OR formato IN ('forma', 'forma_enriquecida', 'livre', 'assadeira', 'pequeno')",
            name="ck_perda_padrao_formato",
        ),
        CheckConstraint("percentual >= 0 AND percentual < 100", name="ck_perda_padrao_percentual"),
    )

    id: Mapped[UUID] = _pk()
    familia_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("familias.id"))
    formato: Mapped[str | None] = mapped_column(String(20))
    peso_min_g: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    peso_max_g: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    tipo: Mapped[str] = mapped_column(String(12), nullable=False)
    percentual: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    observacao: Mapped[str | None] = mapped_column(Text)
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    criado_em: Mapped[datetime] = _agora()


class PerdaMedicao(OrgScoped, Base):
    """Uma produção registrada. A etapa 5 grava; o cálculo já lê."""

    __tablename__ = "perda_medicao"
    __table_args__ = (
        CheckConstraint("massa_total_g > 0", name="ck_perda_medicao_massa"),
        CheckConstraint("pecas > 0", name="ck_perda_medicao_pecas"),
        CheckConstraint("peso_cru_medio_g > 0", name="ck_perda_medicao_cru"),
        CheckConstraint("peso_final_medio_g > 0", name="ck_perda_medicao_final"),
    )

    id: Mapped[UUID] = _pk()
    receita_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("receitas.id"), nullable=False, index=True
    )
    data: Mapped[date] = mapped_column(Date, nullable=False, server_default=func.current_date())
    massa_total_g: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    pecas: Mapped[int] = mapped_column(Integer, nullable=False)
    peso_cru_medio_g: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    peso_final_medio_g: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

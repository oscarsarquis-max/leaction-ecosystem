"""Custos fixos mensais e a regra de preço (margem ou markup)."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.escopo import OrgScoped


def _pk() -> Mapped[UUID]:
    return mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)


def _agora() -> Mapped[datetime]:
    return mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class CustoFixo(OrgScoped, Base):
    __tablename__ = "custos_fixos"
    __table_args__ = (CheckConstraint("valor_mensal >= 0", name="ck_custos_fixos_valor"),)

    id: Mapped[UUID] = _pk()
    nome: Mapped[str] = mapped_column(String(80), nullable=False)
    valor_mensal: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    criado_em: Mapped[datetime] = _agora()


class ParametrosCusto(Base):
    """Um registro por organização: massa do mês e a regra geral de preço."""

    __tablename__ = "parametros_custo"
    __table_args__ = (
        CheckConstraint(
            "massa_mensal_kg IS NULL OR massa_mensal_kg > 0",
            name="ck_parametros_custo_massa",
        ),
        CheckConstraint(
            "regra_tipo IS NULL OR regra_tipo IN ('margem', 'markup')",
            name="ck_parametros_custo_tipo",
        ),
    )

    organizacao_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizacoes.id"), primary_key=True
    )
    massa_mensal_kg: Mapped[Decimal | None] = mapped_column(Numeric(12, 3))
    regra_tipo: Mapped[str | None] = mapped_column(String(12))
    regra_valor: Mapped[Decimal | None] = mapped_column(Numeric(12, 4))

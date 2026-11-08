"""Ordens de produção, fornadas e programação. Tudo na organização."""

from datetime import date, datetime, time
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    Time,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.escopo import OrgScoped

ORIGENS = ("programada", "loja", "avulsa")
SITUACOES = ("planejada", "impressa", "em_producao", "concluida", "cancelada")


def _pk() -> Mapped[UUID]:
    return mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)


class Fornada(OrgScoped, Base):
    __tablename__ = "fornadas"
    __table_args__ = (
        UniqueConstraint("organizacao_id", "nome", name="uq_fornadas_org_nome"),
        CheckConstraint("ordem > 0", name="ck_fornadas_ordem"),
    )

    id: Mapped[UUID] = _pk()
    nome: Mapped[str] = mapped_column(String(80), nullable=False)
    horario: Mapped[time] = mapped_column(Time(), nullable=False)
    ordem: Mapped[int] = mapped_column(Integer, nullable=False)
    ativa: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class Programacao(OrgScoped, Base):
    __tablename__ = "programacoes"
    __table_args__ = (
        CheckConstraint("quantidade_por_fornada > 0", name="ck_programacoes_quantidade"),
    )

    id: Mapped[UUID] = _pk()
    produto_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("produtos.id"), nullable=False)
    quantidade_por_fornada: Mapped[int] = mapped_column(Integer, nullable=False)
    fornada_ids: Mapped[list] = mapped_column(JSON, nullable=False)
    dias_semana: Mapped[list] = mapped_column(JSON, nullable=False)
    inicio: Mapped[date | None] = mapped_column(Date)
    fim: Mapped[date | None] = mapped_column(Date)
    ativa: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class OrdemProducao(OrgScoped, Base):
    __tablename__ = "ordens_producao"
    __table_args__ = (
        UniqueConstraint(
            "organizacao_id",
            "data",
            "fornada_id",
            "produto_id",
            "origem",
            name="uq_ordens_org_data_fornada_produto_origem",
        ),
        CheckConstraint("unidades > 0", name="ck_ordens_unidades"),
        CheckConstraint("origem IN ('programada','loja','avulsa')", name="ck_ordens_origem"),
        CheckConstraint(
            "situacao IN ('planejada','impressa','em_producao','concluida','cancelada')",
            name="ck_ordens_situacao",
        ),
    )

    id: Mapped[UUID] = _pk()
    data: Mapped[date] = mapped_column(Date, nullable=False)
    fornada_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("fornadas.id"), nullable=False)
    produto_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("produtos.id"), nullable=False)
    unidades: Mapped[int] = mapped_column(Integer, nullable=False)
    origem: Mapped[str] = mapped_column(String(12), nullable=False)
    programacao_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("programacoes.id"))
    loja_pedido_ids: Mapped[list | None] = mapped_column(JSON)
    situacao: Mapped[str] = mapped_column(String(16), nullable=False, default="planejada")
    foto: Mapped[dict | None] = mapped_column(JSON)
    observacao: Mapped[str | None] = mapped_column(Text)
    demanda_diferenca: Mapped[int | None] = mapped_column(Integer)
    via: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    comanda_numero: Mapped[int | None] = mapped_column(Integer)
    impressa_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    impressa_por: Mapped[str | None] = mapped_column(String(120))
    criada_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

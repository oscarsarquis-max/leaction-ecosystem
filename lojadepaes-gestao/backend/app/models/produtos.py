"""Produto nasce na Gestão. A Loja de Pães só recebe o que o Oscar mandar, num ciclo futuro.

Produto produzido tem uma receita técnica (ainda sem linhas). Produto comprado aponta um item de
estoque. Componente vira um ingrediente de "Preparos da casa", para entrar na receita de outro.
"""

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
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.escopo import OrgScoped

MODALIDADES = ("produzido", "comprado")
UNIDADES_VENDA = ("un", "kg")
SITUACOES_RECEITA = ("rascunho",)


def _pk() -> Mapped[UUID]:
    return mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)


def _agora() -> Mapped[datetime]:
    return mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class Familia(OrgScoped, Base):
    __tablename__ = "familias"
    __table_args__ = (
        UniqueConstraint("organizacao_id", "nome_normalizado", name="uq_familias_org_nome"),
    )

    id: Mapped[UUID] = _pk()
    nome: Mapped[str] = mapped_column(String(80), nullable=False)
    nome_normalizado: Mapped[str] = mapped_column(String(80), nullable=False)
    criado_em: Mapped[datetime] = _agora()


class Produto(OrgScoped, Base):
    __tablename__ = "produtos"
    __table_args__ = (
        UniqueConstraint("organizacao_id", "nome_normalizado", name="uq_produtos_org_nome"),
        CheckConstraint("modalidade IN ('produzido','comprado')", name="ck_produtos_modalidade"),
        CheckConstraint("unidade_venda IN ('un','kg')", name="ck_produtos_unidade_venda"),
        CheckConstraint("uso_venda OR uso_componente", name="ck_produtos_uso"),
        CheckConstraint(
            "peso_unidade_g IS NULL OR peso_unidade_g > 0", name="ck_produtos_peso"
        ),
    )

    id: Mapped[UUID] = _pk()
    nome: Mapped[str] = mapped_column(String(120), nullable=False)
    nome_normalizado: Mapped[str] = mapped_column(String(120), nullable=False)
    codigo: Mapped[str | None] = mapped_column(String(40))
    modalidade: Mapped[str] = mapped_column(String(12), nullable=False)
    uso_venda: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    uso_componente: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    familia_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("familias.id"))
    unidade_venda: Mapped[str] = mapped_column(String(2), nullable=False)
    peso_unidade_g: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    observacao: Mapped[str | None] = mapped_column(Text)
    item_estoque_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("itens_estoque.id")
    )
    criado_em: Mapped[datetime] = _agora()
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class Receita(OrgScoped, Base):
    """O lugar da receita técnica. As linhas ficam para o GESTAO-010."""

    __tablename__ = "receitas"
    __table_args__ = (
        UniqueConstraint("produto_id", name="uq_receitas_produto"),
        CheckConstraint("situacao IN ('rascunho')", name="ck_receitas_situacao"),
    )

    id: Mapped[UUID] = _pk()
    produto_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("produtos.id"), nullable=False
    )
    situacao: Mapped[str] = mapped_column(String(12), nullable=False, default="rascunho")
    criado_em: Mapped[datetime] = _agora()

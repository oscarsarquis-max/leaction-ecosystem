"""Padrão da casa e o registro de cada sugestão do Gigio. Nada de custo, preço ou dado pessoal."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
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


def _pk() -> Mapped[UUID]:
    return mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)


class PadraoPadaria(OrgScoped, Base):
    """Regra da casa: um ingrediente, ou um termo, e a % do padeiro que o Gigio respeita."""

    __tablename__ = "padrao_padaria"
    __table_args__ = (
        CheckConstraint("percentual >= 0", name="ck_padrao_padaria_percentual"),
    )

    id: Mapped[UUID] = _pk()
    nome: Mapped[str] = mapped_column(String(80), nullable=False)
    ingrediente_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("ingredientes.id"))
    termo: Mapped[str] = mapped_column(String(80), nullable=False)
    percentual: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    observacao: Mapped[str | None] = mapped_column(Text)
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    ordem: Mapped[int] = mapped_column(Integer, nullable=False, default=1)


class GigioSugestao(OrgScoped, Base):
    """Quem pediu, quando, o modelo, os tokens e o texto. Sem custo, preço ou dado pessoal."""

    __tablename__ = "gigio_sugestao"

    id: Mapped[UUID] = _pk()
    receita_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("receitas.id"), nullable=False)
    usuario_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("usuarios.id"))
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    modelo: Mapped[str] = mapped_column(String(120), nullable=False)
    tokens_entrada: Mapped[int | None] = mapped_column(Integer)
    tokens_saida: Mapped[int | None] = mapped_column(Integer)
    entrada: Mapped[dict] = mapped_column(JSON, nullable=False)
    saida: Mapped[dict] = mapped_column(JSON, nullable=False)

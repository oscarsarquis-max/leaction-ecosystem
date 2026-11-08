from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    String,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

PAPEIS = ("dono", "operador", "somente_leitura")


class Organizacao(Base):
    """O cliente. Os dados operacionais pertencem a ela, não ao dono do sistema."""

    __tablename__ = "organizacoes"
    __table_args__ = (
        CheckConstraint("cnpj ~ '^[0-9A-Z]{12}[0-9]{2}$'", name="ck_organizacoes_cnpj"),
        CheckConstraint("nome_curto = lower(nome_curto)", name="ck_organizacoes_nome_curto"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    nome: Mapped[str] = mapped_column(String(160), nullable=False)
    nome_curto: Mapped[str] = mapped_column(String(40), nullable=False, unique=True)
    cnpj: Mapped[str] = mapped_column(String(14), nullable=False, unique=True)
    fonte_loja: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # A 1ª visita a Produtos oferece famílias. Apagar as sugestões não as cria de novo.
    familias_sugestoes_dispensadas: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    email_contato: Mapped[str | None] = mapped_column(String(200))
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class Membro(Base):
    """Liga usuário, organização e papel (dono, operador ou somente leitura)."""

    __tablename__ = "membros"
    __table_args__ = (
        UniqueConstraint("usuario_id", "organizacao_id", name="uq_membros_usuario_org"),
        CheckConstraint("papel IN ('dono','operador','somente_leitura')", name="ck_membros_papel"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    usuario_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False
    )
    organizacao_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizacoes.id"), nullable=False, index=True
    )
    papel: Mapped[str] = mapped_column(String(20), nullable=False)
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

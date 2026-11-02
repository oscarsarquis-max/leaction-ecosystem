from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

PAPEIS = ("dono", "operador", "somente_leitura")


class Usuario(Base):
    __tablename__ = "usuarios"
    __table_args__ = (
        CheckConstraint("papel IN ('dono','operador','somente_leitura')", name="ck_usuarios_papel"),
        CheckConstraint("usuario = lower(usuario)", name="ck_usuarios_usuario_minusculo"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    usuario: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    nome: Mapped[str] = mapped_column(String(120), nullable=False)
    senha_hash: Mapped[str] = mapped_column(Text, nullable=False)
    papel: Mapped[str] = mapped_column(String(20), nullable=False)
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    ultimo_acesso_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Sessao(Base):
    __tablename__ = "sessoes"
    __table_args__ = (Index("ix_sessoes_expira_em", "expira_em"),)

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    csrf_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    usuario_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False
    )
    criada_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    expira_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ultimo_uso_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revogada_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cliente: Mapped[str | None] = mapped_column(String(80))


class TentativaLogin(Base):
    __tablename__ = "tentativas_login"
    __table_args__ = (Index("ix_tentativas_login_usuario_em", "usuario", "criada_em"),)

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    usuario: Mapped[str] = mapped_column(String(80), nullable=False)
    cliente: Mapped[str] = mapped_column(String(80), nullable=False)
    sucesso: Mapped[bool] = mapped_column(Boolean, nullable=False)
    criada_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

"""Quais organizações uma pessoa opera (vínculos ativos, em organizações ativas)."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.organizacao import Membro, Organizacao


def acessos(db: Session, usuario_id: UUID) -> list[tuple[Membro, Organizacao]]:
    consulta = (
        select(Membro, Organizacao)
        .join(Organizacao, Organizacao.id == Membro.organizacao_id)
        .where(
            Membro.usuario_id == usuario_id,
            Membro.ativo.is_(True),
            Organizacao.ativo.is_(True),
        )
        .order_by(Organizacao.nome)
    )
    return [(membro, organizacao) for membro, organizacao in db.execute(consulta).all()]

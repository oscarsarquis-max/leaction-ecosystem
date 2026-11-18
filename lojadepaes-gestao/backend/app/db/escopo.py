"""Isolamento por organização, garantido por construção.

Toda tabela operacional herda de `OrgScoped` (tem `organizacao_id NOT NULL`). Quando a sessão do
banco recebe a organização atual (`ativar_escopo`), duas travas passam a valer para ela:

  * toda consulta ORM sobre um modelo `OrgScoped` ganha `WHERE organizacao_id = <atual>`
    (inclusive em joins, agregações e carregamento de relacionamentos);
  * toda gravação de um modelo `OrgScoped` recebe a organização atual quando está vazia e é
    recusada se apontar para outra.

A dependência `contexto` da API é a única que entrega a sessão das telas operacionais, sempre já
com o escopo ligado. Consultas em SQL puro (`text`) não passam por aqui: use sempre `:org`.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import ForeignKey, Uuid, event
from sqlalchemy.orm import Mapped, Session, declared_attr, mapped_column, with_loader_criteria

CHAVE = "org_id"


class OrgScoped:
    """Mixin: a linha pertence a uma organização (o cliente), nunca ao dono do sistema."""

    @declared_attr
    def organizacao_id(cls) -> Mapped[UUID]:  # noqa: N805
        return mapped_column(
            Uuid(as_uuid=True), ForeignKey("organizacoes.id"), nullable=False, index=True
        )


class EscopoViolado(RuntimeError):
    """Tentativa de gravar numa organização que não é a da sessão."""


def ativar_escopo(sessao: Session, organizacao_id: UUID) -> None:
    sessao.info[CHAVE] = organizacao_id


def escopo_ativo(sessao: Session) -> UUID | None:
    return sessao.info.get(CHAVE)


@event.listens_for(Session, "do_orm_execute")
def _filtrar_consultas(estado) -> None:
    org = estado.session.info.get(CHAVE)
    if org is None or not estado.is_select:
        return
    estado.statement = estado.statement.options(
        with_loader_criteria(
            OrgScoped,
            lambda cls: cls.organizacao_id == org,
            include_aliases=True,
        )
    )


@event.listens_for(Session, "before_flush")
def _conferir_gravacoes(sessao: Session, _contexto, _instancias) -> None:
    org = sessao.info.get(CHAVE)
    if org is None:
        return
    for objeto in list(sessao.new) + list(sessao.dirty):
        if isinstance(objeto, OrgScoped):
            atual = objeto.organizacao_id
            if atual is None:
                objeto.organizacao_id = org
            elif atual != org:
                raise EscopoViolado("gravação em outra organização recusada")

"""Contexto de uma requisição operacional: quem é, em qual organização, com qual papel.

É a única porta de entrada das telas que mexem em dados da organização. Ao resolver o contexto, a
sessão do banco já sai com o escopo ligado (ver `app.db.escopo`): nenhuma consulta ou gravação
operacional existe sem o filtro da organização atual.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.db.escopo import ativar_escopo
from app.domain.acessos import acessos
from app.domain.auth import Principal
from app.models.organizacao import Organizacao


class SemOrganizacao(Exception):
    """A conta não é membro de nenhuma organização (é o caso do admin_plataforma)."""


class OrganizacaoNaoEscolhida(Exception):
    """Membro de várias organizações que ainda não escolheu uma nesta sessão."""


@dataclass(frozen=True)
class Contexto:
    principal: Principal
    organizacao: Organizacao
    papel: str
    db: Session

    @property
    def org_id(self):
        return self.organizacao.id


def resolver_contexto(db: Session, principal: Principal) -> Contexto:
    vinculos = acessos(db, principal.usuario_id)  # type: ignore[arg-type]
    if not vinculos:
        raise SemOrganizacao()
    escolhido = None
    if principal.organizacao_id is not None:
        escolhido = next((v for v in vinculos if v[1].id == principal.organizacao_id), None)
    if escolhido is None and len(vinculos) == 1:
        escolhido = vinculos[0]
    if escolhido is None:
        raise OrganizacaoNaoEscolhida()
    membro, organizacao = escolhido
    ativar_escopo(db, organizacao.id)
    return Contexto(principal=principal, organizacao=organizacao, papel=membro.papel, db=db)

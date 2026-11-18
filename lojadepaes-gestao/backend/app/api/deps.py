from typing import Annotated
from urllib.parse import urlsplit

from fastapi import Cookie, Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.db.session import get_db, get_loja_db
from app.domain.auth import (
    CABECALHO_CSRF,
    COOKIE_SESSAO,
    Principal,
    carregar_sessao,
    csrf_valido,
)
from app.domain.contexto import Contexto, OrganizacaoNaoEscolhida, SemOrganizacao, resolver_contexto
from app.domain.papeis import pode

DbSession = Annotated[Session, Depends(get_db)]
LojaSession = Annotated[Session, Depends(get_loja_db)]
AppSettings = Annotated[Settings, Depends(get_settings)]


def cliente_do_pedido(request: Request) -> str:
    if request.client is None:
        return "desconhecido"
    return request.client.host[:80]


ClientHost = Annotated[str, Depends(cliente_do_pedido)]


def _origem_permitida(request: Request, settings: Settings, origem: str) -> bool:
    if origem in settings.allowed_origin_list:
        return True
    host = request.headers.get("host", "")
    return bool(host) and urlsplit(origem).netloc == host


def obter_principal(
    request: Request,
    db: DbSession,
    settings: AppSettings,
    token: Annotated[str | None, Cookie(alias=COOKIE_SESSAO)] = None,
    csrf: Annotated[str | None, Header(alias=CABECALHO_CSRF)] = None,
) -> Principal:
    carregado = carregar_sessao(db, settings, token, rotacionar_csrf=False)
    if carregado is None:
        raise HTTPException(status_code=401, detail="não autenticado")
    principal, sessao = carregado
    if request.method.upper() not in {"GET", "HEAD", "OPTIONS"}:
        origem = request.headers.get("origin")
        if origem and not _origem_permitida(request, settings, origem):
            raise HTTPException(status_code=403, detail="origem não permitida")
        if not csrf_valido(settings, sessao, csrf):
            raise HTTPException(status_code=403, detail="requisição recusada")
    return principal


UsuarioLogado = Annotated[Principal, Depends(obter_principal)]


def erro(status: int, codigo: str, mensagem: str, **extra: object) -> HTTPException:
    """Erro com código estável (para a tela decidir) e mensagem em português."""
    return HTTPException(
        status_code=status, detail={"codigo": codigo, "mensagem": mensagem, **extra}
    )


def obter_contexto(db: DbSession, principal: UsuarioLogado) -> Contexto:
    """Organização atual da sessão, com o escopo do banco ligado. Sem organização: 403."""
    try:
        return resolver_contexto(db, principal)
    except SemOrganizacao:
        raise erro(
            403,
            "sem_organizacao",
            "Sua conta não opera nenhuma organização. "
            "Peça a quem administra para vincular você a uma.",
        ) from None
    except OrganizacaoNaoEscolhida:
        raise erro(
            403, "organizacao_nao_escolhida", "Escolha a organização em que você vai trabalhar."
        ) from None


ContextoOrg = Annotated[Contexto, Depends(obter_contexto)]


def exigir(acao: str):
    """Dependência: exige membro de uma organização cujo papel possa realizar `acao`."""

    def verificar(ctx: ContextoOrg) -> Contexto:
        if not pode(ctx.papel, acao):
            raise erro(403, "papel_insuficiente", "Seu papel não permite esta ação.")
        return ctx

    return verificar

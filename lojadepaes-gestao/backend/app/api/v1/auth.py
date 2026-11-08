from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Cookie, HTTPException, Query, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import AppSettings, ClientHost, DbSession, UsuarioLogado, erro
from app.core.config import Settings
from app.domain import cnpj as cnpj_dom
from app.domain.acessos import acessos
from app.domain.auth import COOKIE_SESSAO, Principal, carregar_sessao, entrar, revogar
from app.domain.errors import AuthDisabledError, AuthError, RateLimitError
from app.domain.papeis import permissoes_do_papel

router = APIRouter(prefix="/auth", tags=["auth"])


class EntrarIn(BaseModel):
    usuario: str = Field(min_length=1, max_length=80)
    senha: str = Field(min_length=1, max_length=200)


class OrganizacaoOut(BaseModel):
    id: UUID
    nome: str
    nome_curto: str
    cnpj: str  # sem máscara (como é guardado)
    cnpj_formatado: str
    fonte_loja: bool
    papel: str


class SessaoOut(BaseModel):
    usuario: str
    nome: str
    admin_plataforma: bool
    # Papel na organização atual (None quando não há organização atual).
    papel: str | None
    permissoes: list[str]
    csrf: str
    fuso: str
    organizacao: OrganizacaoOut | None
    # Todas as organizações que a pessoa opera (para escolher ao entrar e trocar no menu).
    organizacoes: list[OrganizacaoOut]
    precisa_escolher_organizacao: bool


class EscolherOrganizacaoIn(BaseModel):
    organizacao_id: UUID


def _gravar_cookie(response: Response, settings: Settings, token: str) -> None:
    response.set_cookie(
        key=COOKIE_SESSAO,
        value=token,
        httponly=True,
        samesite="strict",
        secure=settings.cookie_secure,
        max_age=settings.session_ttl_hours * 3600,
        path="/",
    )


def _limpar_cookie(response: Response, settings: Settings) -> None:
    response.delete_cookie(
        key=COOKIE_SESSAO,
        path="/",
        httponly=True,
        samesite="strict",
        secure=settings.cookie_secure,
    )


def _sem_cache(response: Response) -> None:
    response.headers["Cache-Control"] = "no-store"


def montar_sessao(
    db: Session,
    settings: Settings,
    usuario_id: UUID,
    *,
    nome: str,
    login: str,
    admin: bool,
    organizacao_id: UUID | None,
    csrf: str,
) -> SessaoOut:
    vinculos = acessos(db, usuario_id)
    organizacoes = [
        OrganizacaoOut(
            id=o.id,
            nome=o.nome,
            nome_curto=o.nome_curto,
            cnpj=o.cnpj,
            cnpj_formatado=cnpj_dom.formatar(o.cnpj),
            fonte_loja=o.fonte_loja,
            papel=m.papel,
        )
        for m, o in vinculos
    ]
    atual = next((o for o in organizacoes if o.id == organizacao_id), None)
    if atual is None and len(organizacoes) == 1:
        atual = organizacoes[0]
    return SessaoOut(
        usuario=login,
        nome=nome,
        admin_plataforma=admin,
        papel=atual.papel if atual else None,
        permissoes=permissoes_do_papel(atual.papel if atual else None),
        csrf=csrf,
        fuso=settings.bakery_timezone,
        organizacao=atual,
        organizacoes=organizacoes,
        precisa_escolher_organizacao=atual is None and len(organizacoes) > 1,
    )


def _de_principal(db: Session, settings: Settings, principal: Principal) -> SessaoOut:
    return montar_sessao(
        db,
        settings,
        principal.usuario_id,  # type: ignore[arg-type]
        nome=principal.nome,
        login=principal.usuario,
        admin=principal.admin_plataforma,
        organizacao_id=principal.organizacao_id,  # type: ignore[arg-type]
        csrf=principal.csrf,
    )


@router.post("/entrar", response_model=SessaoOut)
def post_entrar(
    dados: EntrarIn,
    response: Response,
    db: DbSession,
    settings: AppSettings,
    cliente: ClientHost,
) -> SessaoOut:
    _sem_cache(response)
    try:
        token, csrf, usuario, sessao = entrar(
            db, settings, usuario=dados.usuario, senha=dados.senha, cliente=cliente
        )
    except AuthDisabledError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from None
    except RateLimitError as exc:
        db.commit()
        raise HTTPException(status_code=429, detail=str(exc)) from None
    except AuthError as exc:
        db.commit()  # a falha precisa ficar registrada para o limite de tentativas
        raise HTTPException(status_code=401, detail=str(exc)) from None
    _gravar_cookie(response, settings, token)
    return montar_sessao(
        db,
        settings,
        usuario.id,
        nome=usuario.nome,
        login=usuario.usuario,
        admin=usuario.admin_plataforma,
        organizacao_id=sessao.organizacao_id,
        csrf=csrf,
    )


@router.get("/sessao", response_model=SessaoOut)
def get_sessao(
    response: Response,
    db: DbSession,
    settings: AppSettings,
    token: Annotated[str | None, Cookie(alias=COOKIE_SESSAO)] = None,
    rotacionar: Annotated[bool, Query()] = True,
) -> SessaoOut:
    _sem_cache(response)
    carregado = carregar_sessao(db, settings, token, rotacionar_csrf=rotacionar)
    if carregado is None:
        _limpar_cookie(response, settings)
        raise HTTPException(status_code=401, detail="não autenticado")
    principal, _sessao = carregado
    return _de_principal(db, settings, principal)


@router.post("/organizacao", response_model=SessaoOut)
def post_organizacao(
    dados: EscolherOrganizacaoIn,
    response: Response,
    db: DbSession,
    settings: AppSettings,
    principal: UsuarioLogado,
    token: Annotated[str | None, Cookie(alias=COOKIE_SESSAO)] = None,
) -> SessaoOut:
    """Escolhe (ou troca) a organização desta sessão. Só vale para organizações em que a pessoa é membro."""
    _sem_cache(response)
    permitido = {o.id for _m, o in acessos(db, principal.usuario_id)}  # type: ignore[arg-type]
    if dados.organizacao_id not in permitido:
        raise erro(403, "organizacao_nao_permitida", "Você não opera essa organização.")
    carregado = carregar_sessao(db, settings, token, rotacionar_csrf=False)
    assert carregado is not None
    _principal, sessao = carregado
    sessao.organizacao_id = dados.organizacao_id
    db.flush()
    return montar_sessao(
        db,
        settings,
        principal.usuario_id,  # type: ignore[arg-type]
        nome=principal.nome,
        login=principal.usuario,
        admin=principal.admin_plataforma,
        organizacao_id=dados.organizacao_id,
        csrf=principal.csrf,
    )


@router.post("/sair")
def post_sair(
    response: Response,
    db: DbSession,
    settings: AppSettings,
    principal: UsuarioLogado,
    token: Annotated[str | None, Cookie(alias=COOKIE_SESSAO)] = None,
) -> dict[str, str]:
    del principal
    _sem_cache(response)
    carregado = carregar_sessao(db, settings, token, rotacionar_csrf=False)
    if carregado is not None:
        revogar(db, carregado[1])
    _limpar_cookie(response, settings)
    return {"status": "ok"}

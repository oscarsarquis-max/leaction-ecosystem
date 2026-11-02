from typing import Annotated

from fastapi import APIRouter, Cookie, HTTPException, Query, Response
from pydantic import BaseModel, Field

from app.api.deps import AppSettings, ClientHost, DbSession, UsuarioLogado
from app.core.config import Settings
from app.domain.auth import COOKIE_SESSAO, carregar_sessao, entrar, revogar
from app.domain.errors import AuthDisabledError, AuthError, RateLimitError
from app.domain.papeis import permissoes_do_papel

router = APIRouter(prefix="/auth", tags=["auth"])


class EntrarIn(BaseModel):
    usuario: str = Field(min_length=1, max_length=80)
    senha: str = Field(min_length=1, max_length=200)


class SessaoOut(BaseModel):
    usuario: str
    nome: str
    papel: str
    permissoes: list[str]
    csrf: str
    fuso: str


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
        token, csrf, usuario = entrar(
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
    return SessaoOut(
        usuario=usuario.usuario,
        nome=usuario.nome,
        papel=usuario.papel,
        permissoes=permissoes_do_papel(usuario.papel),
        csrf=csrf,
        fuso=settings.bakery_timezone,
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
    return SessaoOut(
        usuario=principal.usuario,
        nome=principal.nome,
        papel=principal.papel,
        permissoes=permissoes_do_papel(principal.papel),
        csrf=principal.csrf,
        fuso=settings.bakery_timezone,
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

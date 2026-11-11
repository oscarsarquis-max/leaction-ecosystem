"""Calendário de produção, programação e comanda. Tudo na organização da sessão."""

from datetime import date, timedelta
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from app.api.deps import AppSettings, LojaSession, exigir
from app.domain import producao as prod
from app.domain.contexto import Contexto
from app.domain.errors import ErroDeDominio
from app.domain.estoque import hoje_em

router = APIRouter(prefix="/producao", tags=["producao"])

Ver = Annotated[Contexto, Depends(exigir("ver_estoque"))]
Lancar = Annotated[Contexto, Depends(exigir("lancar"))]


class FornadaIn(BaseModel):
    nome: str = Field(max_length=80)
    horario: str
    ordem: int
    ativa: bool = True


class ProgramacaoIn(BaseModel):
    produto_id: UUID
    quantidade_por_fornada: int
    fornada_ids: list[UUID]
    dias_semana: list[int]
    inicio: date | None = None
    fim: date | None = None
    ativa: bool = True


class OrdemIn(BaseModel):
    data: date
    fornada_id: UUID
    produto_id: UUID
    unidades: int
    observacao: str | None = Field(default=None, max_length=500)


class OrdemPatch(BaseModel):
    unidades: int | None = None
    fornada_id: UUID | None = None
    observacao: str | None = Field(default=None, max_length=500)


class IntervaloIn(BaseModel):
    de: date
    ate: date


class ImprimirIn(BaseModel):
    data: date
    fornada_id: UUID


def _hoje(settings: AppSettings) -> date:
    return hoje_em(settings.bakery_timezone)


def _semana(dia: date) -> tuple[date, date]:
    inicio = dia - timedelta(days=dia.weekday())
    return inicio, inicio + timedelta(days=6)


@router.get("")
def get_producao(
    ctx: Ver,
    settings: AppSettings,
    data: date | None = None,
    de: date | None = None,
    ate: date | None = None,
) -> dict:
    hoje = _hoje(settings)
    if de is None or ate is None:
        de, ate = _semana(data or hoje)
    if ate < de:
        raise ErroDeDominio("intervalo_invalido", "O fim do período é depois do início.")
    return prod.calendario(ctx.db, ctx.organizacao.id, hoje=hoje, de=de, ate=ate)


@router.get("/fornadas")
def get_fornadas(ctx: Ver) -> dict:
    prod.semear_fornadas(ctx.db, ctx.organizacao.id)
    return {"fornadas": prod.listar_fornadas(ctx.db)}


@router.post("/fornadas", status_code=201)
def post_fornada(dados: FornadaIn, ctx: Lancar) -> dict:
    return prod.salvar_fornada(ctx.db, ctx.organizacao.id, dados.model_dump())


@router.patch("/fornadas/{fornada_id}")
def patch_fornada(fornada_id: UUID, dados: FornadaIn, ctx: Lancar) -> dict:
    return prod.salvar_fornada(ctx.db, ctx.organizacao.id, dados.model_dump(), fornada_id)


@router.get("/programacoes")
def get_programacoes(ctx: Ver) -> dict:
    return {"programacoes": prod.listar_programacoes(ctx.db)}


@router.post("/programacoes", status_code=201)
def post_programacao(dados: ProgramacaoIn, ctx: Lancar, settings: AppSettings) -> dict:
    return prod.salvar_programacao(ctx.db, ctx.organizacao.id, dados.model_dump(mode="json"), hoje=_hoje(settings))


@router.patch("/programacoes/{programacao_id}")
def patch_programacao(programacao_id: UUID, dados: ProgramacaoIn, ctx: Lancar, settings: AppSettings) -> dict:
    return prod.salvar_programacao(
        ctx.db,
        ctx.organizacao.id,
        dados.model_dump(mode="json"),
        hoje=_hoje(settings),
        programacao_id=programacao_id,
    )


@router.post("/ordens", status_code=201)
def post_ordem(dados: OrdemIn, ctx: Lancar) -> dict:
    return prod.criar_avulsa(ctx.db, ctx.organizacao.id, dados.model_dump(mode="json"))


@router.patch("/ordens/{ordem_id}")
def patch_ordem(ordem_id: UUID, dados: OrdemPatch, ctx: Lancar) -> dict:
    return prod.alterar_ordem(ctx.db, ordem_id, dados.model_dump(exclude_unset=True, mode="json"))


@router.post("/ordens/{ordem_id}/cancelar")
def post_cancelar(ordem_id: UUID, ctx: Lancar) -> dict:
    return prod.cancelar_ordem(ctx.db, ordem_id)


@router.post("/trazer-loja")
def post_trazer(dados: IntervaloIn, ctx: Lancar, loja: LojaSession, settings: AppSettings) -> dict:
    if not ctx.organizacao.fonte_loja:
        raise ErroDeDominio("sem_fonte_loja", "Esta organização não lê a Loja.", status=403)
    if dados.ate < dados.de:
        raise ErroDeDominio("intervalo_invalido", "O fim do período é depois do início.")
    return prod.trazer_loja(
        ctx.db,
        loja,
        ctx.organizacao.id,
        de=dados.de,
        ate=dados.ate,
        fuso=settings.bakery_timezone,
    )


@router.get("/comanda")
def get_comanda(
    ctx: Ver,
    loja: LojaSession,
    settings: AppSettings,
    data: date = Query(...),
    fornada: UUID = Query(...),
) -> dict:
    return prod.montar_comanda(
        ctx.db,
        dia=data,
        fornada_id=fornada,
        por=ctx.principal.nome,
        fuso=settings.bakery_timezone,
        loja=loja,
    )


@router.post("/comanda/imprimir")
def post_imprimir(dados: ImprimirIn, ctx: Lancar, loja: LojaSession, settings: AppSettings) -> dict:
    return prod.imprimir_comanda(
        ctx.db,
        ctx.organizacao.id,
        dia=dados.data,
        fornada_id=dados.fornada_id,
        por=ctx.principal.nome,
        fuso=settings.bakery_timezone,
        loja=loja,
    )

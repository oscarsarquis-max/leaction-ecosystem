"""Custos fixos e regra de preço. O preço da Loja só é lido."""

from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.api.deps import LojaSession, exigir
from app.domain import custos_preco as custos
from app.domain.contexto import Contexto

router = APIRouter(prefix="/custos", tags=["custos"])

Ver = Annotated[Contexto, Depends(exigir("ver_estoque"))]
Lancar = Annotated[Contexto, Depends(exigir("lancar"))]


class RegraIn(BaseModel):
    tipo: Literal["margem", "markup"]
    valor: Decimal


class ParametrosIn(BaseModel):
    massa_mensal_kg: Decimal | None = None
    regra: RegraIn | None = None


class PrecoCorpo(BaseModel):
    preco: Decimal | None = None


class FixoIn(BaseModel):
    nome: str = Field(max_length=80)
    valor_mensal: Decimal


class RegraCorpo(BaseModel):
    regra: RegraIn | None = None


def _fonte(ctx: Contexto) -> bool:
    return bool(ctx.organizacao.fonte_loja)


@router.get("")
def get_custos(ctx: Ver, loja: LojaSession) -> dict:
    return custos.visao(ctx.db, ctx.organizacao.id, loja, fonte_loja=_fonte(ctx))


@router.put("/parametros")
def put_parametros(dados: ParametrosIn, ctx: Lancar, loja: LojaSession) -> dict:
    return custos.salvar_parametros(
        ctx.db, ctx.organizacao.id, dados.model_dump(), loja, fonte_loja=_fonte(ctx)
    )


@router.post("/fixos")
def post_fixo(dados: FixoIn, ctx: Lancar, loja: LojaSession) -> dict:
    return custos.criar_fixo(
        ctx.db, ctx.organizacao.id, dados.model_dump(), loja, fonte_loja=_fonte(ctx)
    )


@router.put("/fixos/{fixo_id}")
def put_fixo(fixo_id: UUID, dados: FixoIn, ctx: Lancar, loja: LojaSession) -> dict:
    return custos.editar_fixo(ctx.db, fixo_id, dados.model_dump(), loja, fonte_loja=_fonte(ctx))


@router.delete("/fixos/{fixo_id}")
def delete_fixo(fixo_id: UUID, ctx: Lancar, loja: LojaSession) -> dict:
    return custos.apagar_fixo(ctx.db, fixo_id, loja, fonte_loja=_fonte(ctx))


@router.put("/familias/{familia_id}/regra")
def put_familia(familia_id: UUID, dados: RegraCorpo, ctx: Lancar, loja: LojaSession) -> dict:
    regra = None if dados.regra is None else dados.regra.model_dump()
    return custos.regra_familia(ctx.db, familia_id, regra, loja, fonte_loja=_fonte(ctx))


@router.put("/produtos/{produto_id}/regra")
def put_produto(produto_id: UUID, dados: RegraCorpo, ctx: Lancar, loja: LojaSession) -> dict:
    regra = None if dados.regra is None else dados.regra.model_dump()
    return custos.regra_produto(ctx.db, produto_id, regra, loja, fonte_loja=_fonte(ctx))


@router.put("/produtos/{produto_id}/preco")
def put_preco(produto_id: UUID, dados: PrecoCorpo, ctx: Lancar, loja: LojaSession) -> dict:
    return custos.preco_produto(ctx.db, produto_id, dados.preco, loja, fonte_loja=_fonte(ctx))

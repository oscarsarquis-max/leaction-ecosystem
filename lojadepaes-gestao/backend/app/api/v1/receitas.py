"""Receitas técnicas. Tudo na organização da sessão."""

from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.api.deps import exigir
from app.domain import receitas as rec
from app.domain.contexto import Contexto

router = APIRouter(tags=["receitas"])

Ver = Annotated[Contexto, Depends(exigir("ver_estoque"))]
Lancar = Annotated[Contexto, Depends(exigir("lancar"))]


class LinhaIn(BaseModel):
    ingrediente_id: UUID | None = None
    texto: str | None = Field(default=None, max_length=120)
    quantidade: Decimal
    unidade: Literal["g", "kg", "ml", "l", "un"]
    observacao: str | None = Field(default=None, max_length=300)


class ReceitaIn(BaseModel):
    linhas: list[LinhaIn] = Field(default_factory=list, max_length=80)
    rendimento_quantidade: Decimal | None = None
    rendimento_unidade: Literal["g", "kg", "ml", "l", "un"] | None = None
    peso_unidade_g: Decimal | None = None
    perda_percentual: Decimal = Decimal(0)
    modo_fazer: list[str] = Field(default_factory=list, max_length=40)


@router.get("/receitas")
def get_receitas(
    ctx: Ver,
    filtro: Literal["todas", "rascunhos", "publicadas", "custo_parcial"] = "todas",
) -> dict:
    return rec.listar(ctx.db, filtro)


@router.get("/receitas/{produto_id}")
def get_receita(produto_id: UUID, ctx: Ver) -> dict:
    return rec.detalhe(ctx.db, produto_id)


@router.put("/receitas/{produto_id}")
def put_receita(produto_id: UUID, dados: ReceitaIn, ctx: Lancar) -> dict:
    return rec.salvar(
        ctx,
        produto_id,
        linhas=[linha.model_dump() for linha in dados.linhas],
        rendimento_quantidade=dados.rendimento_quantidade,
        rendimento_unidade=dados.rendimento_unidade,
        peso_unidade_g=dados.peso_unidade_g,
        perda_percentual=dados.perda_percentual,
        modo_fazer=dados.modo_fazer,
    )


@router.post("/receitas/{produto_id}/publicar")
def post_publicar(produto_id: UUID, ctx: Lancar) -> dict:
    return rec.publicar(ctx, produto_id)

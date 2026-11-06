"""Sugestão do Gigio e os padrões da casa. A receita só muda quando o padeiro aplica."""

from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.api.deps import exigir
from app.domain.contexto import Contexto
from app.domain.gigio import padroes, servico

router = APIRouter(tags=["gigio"])

Ver = Annotated[Contexto, Depends(exigir("ver_estoque"))]
Lancar = Annotated[Contexto, Depends(exigir("lancar"))]


class FixaIn(BaseModel):
    ingrediente_id: UUID | None = None
    texto: str | None = Field(default=None, max_length=120)
    quantidade: Decimal
    unidade: Literal["g", "kg", "ml", "l", "un"] = "g"


class SugestaoIn(BaseModel):
    descricao: str = Field(max_length=4500)
    massa_base_id: UUID | None = None
    linhas_fixas: list[FixaIn] = Field(default_factory=list, max_length=40)
    rendimento_quantidade: Decimal | None = None
    rendimento_unidade: Literal["g", "kg", "ml", "l", "un"] | None = None


class LinhaAplicar(BaseModel):
    ingrediente_id: UUID | None = None
    texto: str | None = None
    quantidade: Decimal
    unidade: Literal["g", "kg", "ml", "l", "un"] = "g"
    observacao: str | None = None
    origem: Literal["manual", "estimado", "conferido"] = "estimado"
    faixa_min: Decimal | None = None
    faixa_max: Decimal | None = None
    fixa: bool = False


class AplicarIn(BaseModel):
    linhas: list[LinhaAplicar] = Field(default_factory=list, max_length=80)
    rendimento_quantidade: Decimal | None = None
    rendimento_unidade: Literal["g", "kg", "ml", "l", "un"] | None = None
    rendimento_g: Decimal | None = None
    perda_pct: Decimal | None = None
    perda_percentual: Decimal | None = None
    modo_de_fazer: list[str] | None = None


class PadraoIn(BaseModel):
    nome: str = Field(max_length=80)
    termo: str = Field(default="", max_length=80)
    ingrediente_id: UUID | None = None
    percentual: Decimal
    observacao: str | None = Field(default=None, max_length=300)
    ativo: bool | None = None


@router.get("/gigio/situacao")
def get_situacao(ctx: Ver) -> dict:
    return servico.situacao(ctx.db)


@router.post("/receitas/{produto_id}/sugestao-gigio")
def post_sugestao(produto_id: UUID, dados: SugestaoIn, ctx: Lancar) -> dict:
    return servico.sugerir_receita(ctx, produto_id, dados.model_dump())


@router.post("/receitas/{produto_id}/aplicar-sugestao")
def post_aplicar(produto_id: UUID, dados: AplicarIn, ctx: Lancar) -> dict:
    return servico.aplicar(ctx, produto_id, dados.model_dump())


@router.get("/padroes")
def get_padroes(ctx: Ver) -> dict:
    return {"padroes": padroes.listar(ctx.db, ctx.organizacao.id)}


@router.post("/padroes", status_code=201)
def post_padrao(dados: PadraoIn, ctx: Lancar) -> dict:
    return padroes.criar(ctx.db, ctx.organizacao.id, dados.model_dump())


@router.patch("/padroes/{padrao_id}")
def patch_padrao(padrao_id: UUID, dados: PadraoIn, ctx: Lancar) -> dict:
    return padroes.alterar(ctx.db, padrao_id, dados.model_dump())

"""Padrão da casa para perdas e a referência global, só leitura."""

from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.api.deps import exigir
from app.domain import perdas
from app.domain.contexto import Contexto

router = APIRouter(prefix="/perdas", tags=["perdas"])

Ver = Annotated[Contexto, Depends(exigir("ver_estoque"))]
Lancar = Annotated[Contexto, Depends(exigir("lancar"))]


class PadraoPerdaIn(BaseModel):
    tipo: Literal["processo", "coccao", "comercial"]
    formato: Literal["forma", "forma_enriquecida", "livre", "assadeira", "pequeno"] | None = None
    peso_min_g: Decimal | None = None
    peso_max_g: Decimal | None = None
    percentual: Decimal
    observacao: str | None = Field(default=None, max_length=300)
    ativo: bool = True


@router.get("")
def get_perdas(ctx: Ver) -> dict:
    return {
        "padroes": perdas.listar_padroes(ctx.db, ctx.organizacao.id),
        "referencias": perdas.listar_referencia(ctx.db),
    }


@router.get("/padroes")
def get_padroes(ctx: Ver) -> dict:
    return {"padroes": perdas.listar_padroes(ctx.db, ctx.organizacao.id)}


@router.post("/padroes", status_code=201)
def post_padrao(dados: PadraoPerdaIn, ctx: Lancar) -> dict:
    return perdas.criar_padrao(ctx.db, ctx.organizacao.id, dados.model_dump())


@router.patch("/padroes/{padrao_id}")
def patch_padrao(padrao_id: UUID, dados: PadraoPerdaIn, ctx: Lancar) -> dict:
    return perdas.alterar_padrao(ctx.db, padrao_id, dados.model_dump())

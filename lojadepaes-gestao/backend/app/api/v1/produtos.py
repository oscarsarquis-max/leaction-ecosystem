"""Produtos e famílias. Tudo na organização da sessão. Não lê a Loja."""

from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, File, Query, Request, Response, UploadFile
from pydantic import BaseModel, Field

from app.api.deps import exigir
from app.domain import fotos as foto_dom
from app.domain import produtos as prod
from app.domain.contexto import Contexto

router = APIRouter(tags=["produtos"])

Ver = Annotated[Contexto, Depends(exigir("ver_estoque"))]
Lancar = Annotated[Contexto, Depends(exigir("lancar"))]


class FamiliaIn(BaseModel):
    nome: str = Field(min_length=1, max_length=80)


class ProdutoIn(BaseModel):
    nome: str = Field(min_length=1, max_length=120)
    modalidade: Literal["produzido", "comprado"]
    uso_venda: bool = True
    uso_componente: bool = False
    familia_id: UUID | None = None
    unidade_venda: Literal["un", "kg"]
    item_estoque_id: UUID | None = None
    codigo: str | None = Field(default=None, max_length=40)
    peso_unidade_g: Decimal | None = None
    observacao: str | None = Field(default=None, max_length=500)
    confirmado_inexistente: bool = False
    unidade_base: Literal["g", "ml", "un"] | None = None


class ProdutoPatch(BaseModel):
    nome: str | None = Field(default=None, min_length=1, max_length=120)
    uso_venda: bool | None = None
    uso_componente: bool | None = None
    familia_id: UUID | None = None
    unidade_venda: Literal["un", "kg"] | None = None
    item_estoque_id: UUID | None = None
    codigo: str | None = Field(default=None, max_length=40)
    peso_unidade_g: Decimal | None = None
    observacao: str | None = Field(default=None, max_length=500)
    confirmado_inexistente: bool = False
    unidade_base: Literal["g", "ml", "un"] | None = None


def _informado(dados: BaseModel, campo: str) -> bool:
    return campo in dados.model_fields_set


@router.get("/familias")
def get_familias(ctx: Ver) -> dict:
    return prod.listar_familias(ctx.db)


@router.post("/familias", status_code=201)
def post_familia(dados: FamiliaIn, ctx: Lancar) -> dict:
    return prod.saida_familia(prod.criar_familia(ctx, dados.nome))


@router.post("/familias/dispensar-sugestoes", status_code=204)
def post_dispensar(ctx: Lancar) -> Response:
    prod.dispensar_sugestoes(ctx)
    return Response(status_code=204)


@router.delete("/familias/{familia_id}", status_code=204)
def delete_familia(familia_id: UUID, ctx: Lancar) -> Response:
    prod.apagar_familia(ctx, familia_id)
    return Response(status_code=204)


@router.get("/produtos/itens")
def get_itens(ctx: Ver, q: Annotated[str, Query(max_length=120)] = "") -> dict:
    return {"itens": prod.buscar_itens(ctx.db, q)}


@router.get("/produtos")
def get_produtos(
    ctx: Ver,
    filtro: Literal["todos", "produzidos", "comprados", "componentes", "pendentes"] = "todos",
    familia_id: Annotated[UUID | None, Query()] = None,
) -> dict:
    return prod.listar_produtos(ctx.db, filtro, familia_id)


@router.post("/produtos", status_code=201)
def post_produto(dados: ProdutoIn, ctx: Lancar) -> dict:
    criado = prod.criar_produto(
        ctx,
        nome=dados.nome,
        modalidade=dados.modalidade,
        uso_venda=dados.uso_venda,
        uso_componente=dados.uso_componente,
        familia_id=dados.familia_id,
        unidade_venda=dados.unidade_venda,
        item_estoque_id=dados.item_estoque_id,
        codigo=dados.codigo,
        peso_unidade_g=dados.peso_unidade_g,
        observacao=dados.observacao,
        confirmado_inexistente=dados.confirmado_inexistente,
        unidade_base=dados.unidade_base,
    )
    return prod.detalhe_produto(ctx.db, criado.id)


@router.get("/produtos/{produto_id}")
def get_produto(produto_id: UUID, ctx: Ver) -> dict:
    return prod.detalhe_produto(ctx.db, produto_id)


@router.patch("/produtos/{produto_id}")
def patch_produto(produto_id: UUID, dados: ProdutoPatch, ctx: Lancar) -> dict:
    prod.editar_produto(
        ctx,
        produto_id,
        nome=dados.nome,
        uso_venda=dados.uso_venda,
        uso_componente=dados.uso_componente,
        familia_id=dados.familia_id,
        familia_informada=_informado(dados, "familia_id"),
        unidade_venda=dados.unidade_venda,
        item_estoque_id=dados.item_estoque_id,
        item_informado=_informado(dados, "item_estoque_id"),
        codigo=dados.codigo,
        codigo_informado=_informado(dados, "codigo"),
        peso_unidade_g=dados.peso_unidade_g,
        peso_informado=_informado(dados, "peso_unidade_g"),
        observacao=dados.observacao,
        observacao_informada=_informado(dados, "observacao"),
        confirmado_inexistente=dados.confirmado_inexistente,
        unidade_base=dados.unidade_base,
        unidade_base_informada=_informado(dados, "unidade_base"),
    )
    return prod.detalhe_produto(ctx.db, produto_id)


@router.post("/produtos/{produto_id}/inativar")
def post_inativar(produto_id: UUID, ctx: Lancar) -> dict:
    prod.inativar_produto(ctx, produto_id)
    return {"id": str(produto_id), "ativo": False}


def _foto(produto_id: UUID, ctx: Ver, request: Request, *, mini: bool) -> Response:
    conteudo, marca = foto_dom.ler(ctx.db, produto_id, mini=mini)
    cabecalhos = {"ETag": marca, "Cache-Control": "private, max-age=86400"}
    if request.headers.get("if-none-match") == marca:
        return Response(status_code=304, headers=cabecalhos)
    return Response(content=conteudo, media_type="image/webp", headers=cabecalhos)


@router.get("/produtos/{produto_id}/foto")
def get_foto(produto_id: UUID, ctx: Ver, request: Request) -> Response:
    return _foto(produto_id, ctx, request, mini=False)


@router.get("/produtos/{produto_id}/foto/mini")
def get_foto_mini(produto_id: UUID, ctx: Ver, request: Request) -> Response:
    return _foto(produto_id, ctx, request, mini=True)


@router.post("/produtos/{produto_id}/foto")
async def post_foto(produto_id: UUID, ctx: Lancar, arquivo: UploadFile = File(...)) -> dict:
    return foto_dom.gravar(ctx, produto_id, await arquivo.read())


@router.delete("/produtos/{produto_id}/foto")
def delete_foto(produto_id: UUID, ctx: Lancar) -> dict:
    return foto_dom.apagar(ctx, produto_id)

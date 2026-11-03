"""Fluxo da padaria: Entradas, Ingredientes e Locais. Tudo dentro da organização da sessão."""

from datetime import date
from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.api.deps import AppSettings, erro, exigir
from app.domain import entradas as ent
from app.domain import estoque as est
from app.domain import ingredientes as ing
from app.domain.contexto import Contexto
from app.domain.errors import ErroDeDominio
from app.models.estoque import Entrada, EntradaLinha, Local, Lote
from app.models.usuarios import Usuario

router = APIRouter(tags=["estoque"])

Ver = Annotated[Contexto, Depends(exigir("ver_estoque"))]
Lancar = Annotated[Contexto, Depends(exigir("lancar"))]
Ajustar = Annotated[Contexto, Depends(exigir("ajustar"))]
Juntar = Annotated[Contexto, Depends(exigir("juntar"))]


def _hoje(settings: AppSettings) -> date:
    return est.hoje_em(settings.bakery_timezone)


def fluxo_para_dict(fluxo: est.Fluxo) -> dict:
    return {
        "etapas": [
            {
                "id": e.id,
                "nome": e.nome,
                "pergunta": e.pergunta,
                "estado": e.estado,
                "frase": e.frase,
                "href": e.href,
            }
            for e in fluxo.etapas
        ],
        "proximo_passo": fluxo.proximo_passo,
        "entradas_total": fluxo.entradas_total,
        "entradas_pendentes": fluxo.entradas_pendentes,
    }


def fluxo_dict(ctx: Contexto, hoje: date) -> dict:
    return fluxo_para_dict(est.calcular_fluxo(ctx.db, hoje))


@router.get("/fluxo")
def get_fluxo(ctx: Ver, settings: AppSettings) -> dict:
    return fluxo_dict(ctx, _hoje(settings))


# ---------------------------------------------------------------- catálogo para os formulários


@router.get("/catalogo")
def get_catalogo(ctx: Ver) -> dict:
    visao = est.carregar_visao(ctx.db)
    ativos = [i for i in visao.ingredientes.values() if i.ativo]
    return {
        "ingredientes": [
            {"id": i.id, "nome": i.nome, "unidade_base": i.unidade_base}
            for i in sorted(ativos, key=lambda x: x.nome.lower())
        ],
        "itens": [
            {
                "id": i.id,
                "nome": i.nome,
                "marca": i.marca,
                "unidade_controle": i.unidade_controle,
                "conteudo_embalagem": float(i.conteudo_embalagem)
                if i.conteudo_embalagem is not None
                else None,
                "ingrediente_id": i.ingrediente_id,
                "ingrediente": visao.ingredientes[i.ingrediente_id].nome,
                "unidade_base": visao.ingredientes[i.ingrediente_id].unidade_base,
            }
            for i in sorted(
                (x for x in visao.itens.values() if x.ativo), key=lambda x: x.nome.lower()
            )
        ],
        "locais": [
            {"id": lc.id, "nome": lc.nome, "padrao": lc.padrao} for lc in est.locais_ativos(ctx.db)
        ],
    }


# ---------------------------------------------------------------- entradas


@router.get("/entradas")
def get_entradas(
    ctx: Ver,
    filtro: Annotated[Literal["todas", "com_nota", "sem_nota", "pendentes"], Query()] = "todas",
) -> dict:
    return {"filtro": filtro, "entradas": ent.listar_entradas(ctx.db, filtro)}


def _detalhe_entrada(ctx: Contexto, entrada: Entrada) -> dict:
    db = ctx.db
    local = db.scalar(select(Local).where(Local.id == entrada.local_id))
    por = db.scalar(select(Usuario.nome).where(Usuario.id == entrada.lancada_por))
    visao = est.carregar_visao(db)
    linhas = []
    total = Decimal(0)
    com_valor = 0
    for linha in db.scalars(
        select(EntradaLinha)
        .where(EntradaLinha.entrada_id == entrada.id)
        .order_by(EntradaLinha.posicao)
    ):
        item = visao.itens[linha.item_id]
        lote = next(lv.lote for lv in visao.lotes if lv.lote.id == linha.lote_id)
        ingrediente = visao.ingredientes[item.ingrediente_id]
        if linha.valor_total is not None:
            total += linha.valor_total
            com_valor += 1
        linhas.append(
            {
                "posicao": linha.posicao,
                "item": item.nome,
                "marca": item.marca,
                "ingrediente_id": ingrediente.id,
                "ingrediente": ingrediente.nome,
                "quantidade": float(linha.quantidade),
                "unidade": linha.unidade,
                "quantidade_base": float(linha.quantidade_base),
                "unidade_base": ingrediente.unidade_base,
                "lote_id": lote.id,
                "lote": lote.codigo,
                "validade": lote.validade,
                "sem_validade": lote.sem_validade,
                "validade_pendente": lote.validade is None and not lote.sem_validade,
                "custo": float(linha.custo_informado)
                if linha.custo_informado is not None
                else None,
                "custo_por": linha.custo_por,
                "valor_total": float(linha.valor_total) if linha.valor_total is not None else None,
            }
        )
    return {
        "id": entrada.id,
        "data": entrada.data,
        "tipo": entrada.tipo,
        "motivo": entrada.motivo,
        "motivo_detalhe": entrada.motivo_detalhe,
        "fornecedor": entrada.fornecedor,
        "observacao": entrada.observacao,
        "local": local.nome if local else None,
        "lancada_por": por,
        "linhas": linhas,
        "valor": float(total) if com_valor else None,
        "valor_parcial": 0 < com_valor < len(linhas),
        "situacao": "pendente" if any(lc["validade_pendente"] for lc in linhas) else "completa",
    }


@router.get("/entradas/{entrada_id}")
def get_entrada(entrada_id: UUID, ctx: Ver) -> dict:
    entrada = ctx.db.scalar(select(Entrada).where(Entrada.id == entrada_id))
    if entrada is None:
        raise erro(404, "entrada_inexistente", "Essa entrada não existe.")
    return _detalhe_entrada(ctx, entrada)


@router.post("/entradas/verificar")
def post_verificar(dados: ent.VerificarIn, ctx: Lancar, settings: AppSettings) -> dict:
    """Pré-visualização: parecidos, pendências e totais de cada linha. Não grava nada."""
    visao = est.carregar_visao(ctx.db)
    analises = ent.analisar_linhas(ctx.db, visao, dados.linhas, hoje=_hoje(settings))
    return {"linhas": [a for a, _r in analises]}


@router.post("/entradas", status_code=201)
def post_entrada(
    dados: ent.EntradaIn, response: Response, ctx: Lancar, settings: AppSettings
) -> dict:
    try:
        entrada, criada = ent.lancar_entrada(ctx, dados, hoje=_hoje(settings))
    except ErroDeDominio:
        ctx.db.rollback()
        raise
    if not criada:
        response.status_code = 200  # mesma chave: devolve a entrada que já existe
    return _detalhe_entrada(ctx, entrada)


class LoteIn(BaseModel):
    validade: date | None = None
    sem_validade: bool = False


@router.patch("/lotes/{lote_id}")
def patch_lote(lote_id: UUID, dados: LoteIn, ctx: Lancar) -> dict:
    """Informa a validade de um lote que ficou pendente (ou corrige: data ou "sem validade")."""
    if dados.validade is not None and dados.sem_validade:
        raise ErroDeDominio(
            "validade_conflito", "Escolha uma data de validade ou “sem validade”, não os dois."
        )
    if dados.validade is None and not dados.sem_validade:
        raise ErroDeDominio("validade_vazia", "Informe a data ou marque “sem validade”.")
    lote = ctx.db.scalar(select(Lote).where(Lote.id == lote_id))
    if lote is None:
        raise erro(404, "lote_inexistente", "Esse lote não existe.")
    lote.validade, lote.sem_validade = dados.validade, dados.sem_validade
    ctx.db.flush()
    return {"id": lote.id, "validade": lote.validade, "sem_validade": lote.sem_validade}


# ---------------------------------------------------------------- ingredientes


class IngredienteIn(BaseModel):
    nome: str = Field(min_length=1, max_length=120)
    unidade_base: Literal["g", "ml", "un"]
    confirmar_novo: bool = False


class IngredientePatch(BaseModel):
    nome: str | None = Field(default=None, min_length=1, max_length=120)
    unidade_base: Literal["g", "ml", "un"] | None = None


class AjusteIn(BaseModel):
    lote_id: UUID
    # Saldo contado, na unidade base do ingrediente (g, ml ou un).
    saldo_contado_base: Decimal = Field(ge=0)
    motivo: str = Field(min_length=3, max_length=300)


class JuntarIn(BaseModel):
    mantem_id: UUID
    remove_id: UUID


class DistintosIn(BaseModel):
    a_id: UUID
    b_id: UUID


@router.get("/ingredientes")
def get_ingredientes(
    ctx: Ver,
    settings: AppSettings,
    filtro: Annotated[Literal["todos", "com_saldo", "sem_saldo", "vence7"], Query()] = "todos",
) -> dict:
    return ing.listar_ingredientes(ctx.db, _hoje(settings), filtro)


@router.post("/ingredientes", status_code=201)
def post_ingrediente(dados: IngredienteIn, ctx: Lancar, settings: AppSettings) -> dict:
    criado = ing.criar_ingrediente(
        ctx, dados.nome, dados.unidade_base, confirmar_novo=dados.confirmar_novo
    )
    return ing.detalhe_ingrediente(ctx.db, criado.id, _hoje(settings))


@router.post("/ingredientes/juntar")
def post_juntar(dados: JuntarIn, ctx: Juntar, settings: AppSettings) -> dict:
    mantido = ing.juntar(ctx, dados.mantem_id, dados.remove_id)
    return ing.detalhe_ingrediente(ctx.db, mantido.id, _hoje(settings))


@router.post("/ingredientes/distintos", status_code=204)
def post_distintos(dados: DistintosIn, ctx: Juntar) -> Response:
    """ "São diferentes": o par deixa de aparecer como parecido."""
    ing.marcar_distintos(ctx, dados.a_id, dados.b_id)
    return Response(status_code=204)


@router.get("/ingredientes/{ingrediente_id}")
def get_ingrediente(ingrediente_id: UUID, ctx: Ver, settings: AppSettings) -> dict:
    return ing.detalhe_ingrediente(ctx.db, ingrediente_id, _hoje(settings))


@router.patch("/ingredientes/{ingrediente_id}")
def patch_ingrediente(
    ingrediente_id: UUID, dados: IngredientePatch, ctx: Lancar, settings: AppSettings
) -> dict:
    ing.editar_ingrediente(ctx, ingrediente_id, dados.nome, dados.unidade_base)
    return ing.detalhe_ingrediente(ctx.db, ingrediente_id, _hoje(settings))


@router.post("/ingredientes/{ingrediente_id}/ajustes", status_code=201)
def post_ajuste(ingrediente_id: UUID, dados: AjusteIn, ctx: Ajustar, settings: AppSettings) -> dict:
    ing.ajustar_saldo(ctx, ingrediente_id, dados.lote_id, dados.saldo_contado_base, dados.motivo)
    return ing.detalhe_ingrediente(ctx.db, ingrediente_id, _hoje(settings))


# ---------------------------------------------------------------- locais


class LocalIn(BaseModel):
    nome: str = Field(min_length=1, max_length=80)
    padrao: bool = False


class LocalPatch(BaseModel):
    nome: str | None = Field(default=None, min_length=1, max_length=80)
    ativo: bool | None = None
    padrao: bool | None = None


def _local_out(lc: Local) -> dict:
    return {"id": lc.id, "nome": lc.nome, "padrao": lc.padrao, "ativo": lc.ativo}


@router.get("/locais")
def get_locais(ctx: Ver) -> list[dict]:
    return [
        _local_out(lc)
        for lc in ctx.db.scalars(select(Local).order_by(Local.padrao.desc(), Local.nome))
    ]


@router.post("/locais", status_code=201)
def post_local(dados: LocalIn, ctx: Lancar) -> dict:
    return _local_out(ing.criar_local(ctx, dados.nome, padrao=dados.padrao))


@router.patch("/locais/{local_id}")
def patch_local(local_id: UUID, dados: LocalPatch, ctx: Lancar) -> dict:
    local = ing.editar_local(ctx, local_id, dados.nome, dados.ativo)
    if dados.padrao:
        local = ing.definir_padrao(ctx, local_id)
    return _local_out(local)

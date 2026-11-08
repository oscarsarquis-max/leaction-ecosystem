import logging
from datetime import date, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.exc import SQLAlchemyError

from app.api.deps import AppSettings, LojaSession, exigir
from app.api.v1.estoque import fluxo_para_dict
from app.domain import estoque as est
from app.domain.contexto import Contexto
from app.domain.producao import resumo_hoje
from app.loja_reader.demanda import consultar_demanda, versao_loja

router = APIRouter(tags=["hoje"])
log = logging.getLogger("gestao.hoje")


class ItemDemanda(BaseModel):
    origem: str
    produto_ou_massa: str | None
    variante_ou_forma: str | None
    receita_base: str | None
    quantidade: int
    paes_fisicos: int
    linhas_unidades_pendentes: int


class Fornada(BaseModel):
    data: date
    paes_fisicos: int
    quantidade: int
    unidades_pendentes: int
    itens: list[ItemDemanda]


class Compatibilidade(BaseModel):
    ok: bool
    versao_loja: str | None = None
    versao_conhecida: bool | None = None
    mensagem: str | None = None


class VenceEm7Dias(BaseModel):
    lote_id: str
    ingrediente_id: str
    ingrediente: str
    item: str
    codigo: str
    validade: date
    dias: int
    saldo: float
    unidade_base: str


class SemSaldo(BaseModel):
    id: str
    nome: str


class ProducaoHoje(BaseModel):
    fornada_id: str
    fornada: str
    horario: str
    unidades: int
    ordens: int
    pedido_mudou: bool


class HojeOut(BaseModel):
    hoje: date
    ate: date
    dias: int
    # Só a organização marcada como fonte da Loja lê a demanda dela.
    fonte_loja: bool
    compatibilidade: Compatibilidade
    fornadas: list[Fornada]
    total_paes_fisicos: int
    fluxo: dict
    vence_em_7_dias: list[VenceEm7Dias]
    sem_saldo: list[SemSaldo]
    producao_hoje: list[ProducaoHoje] = []


def _blocos_do_estoque(
    ctx: Contexto, hoje: date
) -> tuple[dict, list[VenceEm7Dias], list[SemSaldo]]:
    visao = est.carregar_visao(ctx.db)
    fluxo = est.calcular_fluxo(ctx.db, hoje, visao)
    vencem = [
        VenceEm7Dias(
            lote_id=str(lv.lote.id),
            ingrediente_id=str(lv.item.ingrediente_id),
            ingrediente=visao.ingredientes[lv.item.ingrediente_id].nome,
            item=lv.item.nome,
            codigo=lv.lote.codigo,
            validade=lv.lote.validade,  # type: ignore[arg-type]
            dias=(lv.lote.validade - hoje).days,  # type: ignore[operator]
            saldo=float(lv.saldo),
            unidade_base=visao.ingredientes[lv.item.ingrediente_id].unidade_base,
        )
        for lv in sorted(fluxo.alertas.vencem, key=lambda x: x.lote.validade)  # type: ignore[arg-type,return-value]
    ]
    sem_saldo = [SemSaldo(id=str(i.id), nome=i.nome) for i in fluxo.alertas.sem_saldo]
    return fluxo_para_dict(fluxo), vencem, sem_saldo


@router.get("/hoje", response_model=HojeOut)
def get_hoje(
    loja: LojaSession,
    settings: AppSettings,
    ctx: Annotated[Contexto, Depends(exigir("ver_hoje"))],
    dias: Annotated[int | None, Query(ge=1)] = None,
) -> HojeOut:
    horizonte = min(dias or settings.horizonte_dias_padrao, settings.horizonte_dias_maximo)
    hoje = est.hoje_em(settings.bakery_timezone)
    ate = hoje + timedelta(days=horizonte - 1)
    fluxo, vencem, sem_saldo = _blocos_do_estoque(ctx, hoje)
    base = dict(
        producao_hoje=resumo_hoje(ctx.db, hoje),
        hoje=hoje,
        ate=ate,
        dias=horizonte,
        fonte_loja=ctx.organizacao.fonte_loja,
        fluxo=fluxo,
        vence_em_7_dias=vencem,
        sem_saldo=sem_saldo,
    )

    if not ctx.organizacao.fonte_loja:
        return HojeOut(
            **base, compatibilidade=Compatibilidade(ok=True), fornadas=[], total_paes_fisicos=0
        )

    try:
        linhas = consultar_demanda(loja, de=hoje, ate=ate, fuso=settings.bakery_timezone)
        versao = versao_loja(loja)
    except SQLAlchemyError:
        log.exception("leitura da demanda da Loja falhou")
        loja.rollback()
        return HojeOut(
            **base,
            compatibilidade=Compatibilidade(
                ok=False,
                mensagem=(
                    "Não consegui ler os dados da Loja agora. Nenhum número foi calculado "
                    "para não mostrar demanda errada."
                ),
            ),
            fornadas=[],
            total_paes_fisicos=0,
        )

    por_data: dict[date, list[ItemDemanda]] = {}
    for linha in linhas:
        por_data.setdefault(linha.fornada_data, []).append(
            ItemDemanda(
                origem=linha.origem,
                produto_ou_massa=linha.produto_ou_massa,
                variante_ou_forma=linha.variante_ou_forma,
                receita_base=linha.receita_base,
                quantidade=linha.quantidade,
                paes_fisicos=linha.paes_fisicos,
                linhas_unidades_pendentes=linha.linhas_unidades_pendentes,
            )
        )
    fornadas = [
        Fornada(
            data=dia,
            paes_fisicos=sum(i.paes_fisicos for i in itens),
            quantidade=sum(i.quantidade for i in itens),
            unidades_pendentes=sum(i.linhas_unidades_pendentes for i in itens),
            itens=itens,
        )
        for dia, itens in sorted(por_data.items())
    ]
    conhecida = versao in settings.loja_head_list if versao else None
    mensagem = None
    if conhecida is False:
        mensagem = (
            "A Loja mudou de versão desde a última conferência do Gestão. "
            "A leitura continua funcionando, mas vale revisar."
        )
    return HojeOut(
        **base,
        compatibilidade=Compatibilidade(
            ok=True, versao_loja=versao, versao_conhecida=conhecida, mensagem=mensagem
        ),
        fornadas=fornadas,
        total_paes_fisicos=sum(f.paes_fisicos for f in fornadas),
    )

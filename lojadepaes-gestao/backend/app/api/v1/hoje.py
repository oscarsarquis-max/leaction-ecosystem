import logging
from datetime import date, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.exc import SQLAlchemyError

from app.api.deps import AppSettings, LojaSession, exigir
from app.api.v1.estoque import fluxo_para_dict
from app.domain import estoque as est
from app.domain import hoje_painel as painel
from app.domain.contexto import Contexto
from app.domain.producao import resumo_hoje
from app.loja_reader.demanda import consultar_demanda, versao_loja

router = APIRouter(tags=["hoje"])
log = logging.getLogger("gestao.hoje")


class Vinculo(BaseModel):
    produto_id: str
    produto: str
    receita: str  # publicada | rascunho | sem_receita


class ItemDemanda(BaseModel):
    origem: str
    produto_ou_massa: str | None
    variante_ou_forma: str | None
    receita_base: str | None
    quantidade: int
    paes_fisicos: int
    linhas_unidades_pendentes: int
    # O produto do Gestão ligado a este item da Loja (None: sem vínculo ou pedido do criador).
    vinculo: Vinculo | None = None


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


class Pendencia(BaseModel):
    codigo: str
    texto: str
    acao: str
    href: str
    estado: str  # falta | atencao


class ItemNecessidade(BaseModel):
    ingrediente_id: str
    ingrediente: str
    unidade_base: str
    precisa: float
    tem: float
    falta: float


class ForaDaConta(BaseModel):
    nome: str
    paes_fisicos: int
    motivo: str  # sem_vinculo | rascunho | sem_receita


class Necessidade(BaseModel):
    itens: list[ItemNecessidade]
    # Pães confirmados que não entram na conta. ora_da_conta_itens diz quais e por quê.
    fora_da_conta: int
    fora_da_conta_itens: list[ForaDaConta] = []


class Indicadores(BaseModel):
    receitas_publicadas: int
    produtos_produzidos: int
    entradas_mes_qtd: int
    entradas_mes_valor: float


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
    # Legado: espelha cabaram, para quem já lia este campo.
    sem_saldo: list[SemSaldo]
    # Controla estoque, já teve entrada e zerou. Água e preparo da casa nunca entram.
    acabaram: list[SemSaldo] = []
    pendencias: list[Pendencia] = []
    necessidade: Necessidade | None = None
    indicadores: Indicadores | None = None
    producao_hoje: list[ProducaoHoje] = []


def _blocos_do_estoque(
    ctx: Contexto, hoje: date
) -> tuple[dict, list[VenceEm7Dias], list[SemSaldo], est.Visao]:
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
    zeraram = [SemSaldo(id=str(i.id), nome=i.nome) for i in painel.acabaram(ctx.db, visao)]
    return fluxo_para_dict(fluxo), vencem, zeraram, visao


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
    fluxo, vencem, zeraram, visao = _blocos_do_estoque(ctx, hoje)
    fonte = bool(ctx.organizacao.fonte_loja)
    base = dict(
        producao_hoje=resumo_hoje(ctx.db, hoje),
        hoje=hoje,
        ate=ate,
        dias=horizonte,
        fonte_loja=ctx.organizacao.fonte_loja,
        fluxo=fluxo,
        vence_em_7_dias=vencem,
        sem_saldo=zeraram,
        acabaram=zeraram,
        indicadores=painel.indicadores(ctx.db, hoje),
    )

    if not fonte:
        return HojeOut(
            **base,
            pendencias=painel.pendencias(ctx.db, visao, fonte_loja=False, linhas=None, vinculos=None),
            necessidade=painel.necessidade_vazia(),
            compatibilidade=Compatibilidade(ok=True),
            fornadas=[],
            total_paes_fisicos=0,
        )

    try:
        linhas = consultar_demanda(loja, de=hoje, ate=ate, fuso=settings.bakery_timezone)
        versao = versao_loja(loja)
    except SQLAlchemyError:
        log.exception("leitura da demanda da Loja falhou")
        loja.rollback()
        return HojeOut(
            **base,
            pendencias=painel.pendencias(ctx.db, visao, fonte_loja=True, linhas=None, vinculos=None),
            necessidade=None,
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

    vinculos = painel.vincular(ctx.db, linhas)
    por_data: dict[date, list[ItemDemanda]] = {}
    for linha, vinculo in zip(linhas, vinculos, strict=True):
        por_data.setdefault(linha.fornada_data, []).append(
            ItemDemanda(
                origem=linha.origem,
                produto_ou_massa=linha.produto_ou_massa,
                variante_ou_forma=linha.variante_ou_forma,
                receita_base=linha.receita_base,
                quantidade=linha.quantidade,
                paes_fisicos=linha.paes_fisicos,
                linhas_unidades_pendentes=linha.linhas_unidades_pendentes,
                vinculo=Vinculo(**vinculo) if vinculo else None,
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
        pendencias=painel.pendencias(
            ctx.db, visao, fonte_loja=True, linhas=linhas, vinculos=vinculos
        ),
        necessidade=painel.necessidade(ctx.db, visao, linhas, vinculos),
        compatibilidade=Compatibilidade(
            ok=True, versao_loja=versao, versao_conhecida=conhecida, mensagem=mensagem
        ),
        fornadas=fornadas,
        total_paes_fisicos=sum(f.paes_fisicos for f in fornadas),
    )

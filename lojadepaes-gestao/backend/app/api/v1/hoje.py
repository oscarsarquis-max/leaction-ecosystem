import logging
from datetime import date, datetime, timedelta
from typing import Annotated
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.exc import SQLAlchemyError

from app.api.deps import AppSettings, LojaSession, exigir
from app.domain.auth import Principal
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


class HojeOut(BaseModel):
    hoje: date
    ate: date
    dias: int
    compatibilidade: Compatibilidade
    fornadas: list[Fornada]
    total_paes_fisicos: int


@router.get("/hoje", response_model=HojeOut)
def get_hoje(
    loja: LojaSession,
    settings: AppSettings,
    _principal: Annotated[Principal, Depends(exigir("ver_hoje"))],
    dias: Annotated[int | None, Query(ge=1)] = None,
) -> HojeOut:
    horizonte = min(dias or settings.horizonte_dias_padrao, settings.horizonte_dias_maximo)
    hoje = datetime.now(ZoneInfo(settings.bakery_timezone)).date()
    ate = hoje + timedelta(days=horizonte - 1)
    try:
        linhas = consultar_demanda(loja, de=hoje, ate=ate, fuso=settings.bakery_timezone)
        versao = versao_loja(loja)
    except SQLAlchemyError:
        log.exception("leitura da demanda da Loja falhou")
        loja.rollback()
        return HojeOut(
            hoje=hoje,
            ate=ate,
            dias=horizonte,
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
        hoje=hoje,
        ate=ate,
        dias=horizonte,
        compatibilidade=Compatibilidade(
            ok=True, versao_loja=versao, versao_conhecida=conhecida, mensagem=mensagem
        ),
        fornadas=fornadas,
        total_paes_fisicos=sum(f.paes_fisicos for f in fornadas),
    )

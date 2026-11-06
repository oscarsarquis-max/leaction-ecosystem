"""Unidades, saldo derivado do ledger e o estado de cada etapa do fluxo.

Regras que valem em todo o módulo:
  * o saldo nunca é gravado: é a soma dos movimentos (por lote, por item, por ingrediente);
  * embalagem conta pelo conteúdo (3 embalagens de 1000 g = 3000 g);
  * nunca converte massa em volume, nem volume em massa;
  * custo desconhecido é "sem custo" e nunca entra como zero.
Toda consulta passa pela sessão com o escopo da organização ligado (ver `app.db.escopo`).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domain.normalizacao import sao_parecidos
from app.models.estoque import (
    Entrada,
    EntradaLinha,
    Ingrediente,
    ItemEstoque,
    Local,
    Lote,
    Movimento,
    ParecidoDistinto,
)

ZERO = Decimal(0)
JANELA_VALIDADE_DIAS = 7

# Unidades que a pessoa pode digitar, por unidade de controle do item.
UNIDADES_POR_CONTROLE: dict[str, tuple[str, ...]] = {
    "massa": ("g", "kg"),
    "volume": ("ml", "l"),
    "embalagem": ("emb",),
}
FATOR_PARA_BASE = {"g": Decimal(1), "kg": Decimal(1000), "ml": Decimal(1), "l": Decimal(1000)}
BASE_DO_CONTROLE = {"massa": "g", "volume": "ml"}
CUSTO_POR_CONTROLE = {"massa": "kg", "volume": "l", "embalagem": "emb"}


def quantidade_em_base(
    controle: str, unidade: str, quantidade: Decimal, conteudo: Decimal | None
) -> Decimal:
    if controle == "embalagem":
        return quantidade * (conteudo or ZERO)
    return quantidade * FATOR_PARA_BASE[unidade]


def custo_para_base(controle: str, custo: Decimal, conteudo: Decimal | None) -> Decimal:
    """R$ por kg/L/embalagem -> R$ por g/ml/un (a unidade base do ingrediente)."""
    if controle == "embalagem":
        return custo / (conteudo or Decimal(1))
    return custo / Decimal(1000)


# Como o custo de uma linha foi informado.
MODO_VALOR_PAGO = "valor_pago"
MODO_PRECO_UNIDADE = "preco_unidade"


def custo_de_valor_pago(valor_pago: Decimal, quantidade_base: Decimal) -> Decimal:
    """O que se sabe é quanto foi pago: R$ por g, ml ou un = valor pago ÷ quantidade na unidade base.

    Sem arredondar (quem mostra arredonda): 22,99 pagos por 500 g são R$ 0,04598 por g, R$ 45,98 por kg.
    """
    return valor_pago / quantidade_base


def arredondar_centavos(valor: Decimal) -> Decimal:
    return valor.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


# ---------------------------------------------------------------- visão do estoque


@dataclass
class LoteVisao:
    lote: Lote
    item: ItemEstoque
    saldo: Decimal

    @property
    def vence_em(self) -> date | None:
        return self.lote.validade


@dataclass
class Visao:
    ingredientes: dict[UUID, Ingrediente]
    itens: dict[UUID, ItemEstoque]
    lotes: list[LoteVisao]
    distintos: set[tuple[str, UUID, UUID]] = field(default_factory=set)

    def lotes_do_ingrediente(self, ingrediente_id: UUID) -> list[LoteVisao]:
        return [lv for lv in self.lotes if lv.item.ingrediente_id == ingrediente_id]

    def saldo_do_ingrediente(self, ingrediente_id: UUID) -> Decimal:
        return sum((lv.saldo for lv in self.lotes_do_ingrediente(ingrediente_id)), ZERO)

    def itens_do_ingrediente(self, ingrediente_id: UUID) -> list[ItemEstoque]:
        return [i for i in self.itens.values() if i.ingrediente_id == ingrediente_id]


def par_ordenado(a: UUID, b: UUID) -> tuple[UUID, UUID]:
    return (a, b) if str(a) < str(b) else (b, a)


def carregar_visao(db: Session) -> Visao:
    ingredientes = {i.id: i for i in db.scalars(select(Ingrediente))}
    itens = {i.id: i for i in db.scalars(select(ItemEstoque))}
    somas = {
        lote_id: total
        for lote_id, total in db.execute(
            select(Movimento.lote_id, func.sum(Movimento.quantidade_base))
            .where(Movimento.lote_id.is_not(None))
            .group_by(Movimento.lote_id)
        )
    }
    lotes = [
        LoteVisao(lote=lc, item=itens[lc.item_id], saldo=Decimal(somas.get(lc.id) or 0))
        for lc in db.scalars(
            select(Lote).order_by(Lote.validade.asc().nulls_last(), Lote.criado_em)
        )
    ]
    distintos = {(p.tipo, p.id_menor, p.id_maior) for p in db.scalars(select(ParecidoDistinto))}
    return Visao(ingredientes=ingredientes, itens=itens, lotes=lotes, distintos=distintos)


def pares_parecidos(visao: Visao) -> list[tuple[Ingrediente, Ingrediente]]:
    """Pares de ingredientes ativos que parecem o mesmo e ainda não foram decididos."""
    ativos = sorted(
        (i for i in visao.ingredientes.values() if i.ativo), key=lambda i: i.nome_normalizado
    )
    pares: list[tuple[Ingrediente, Ingrediente]] = []
    for indice, a in enumerate(ativos):
        for b in ativos[indice + 1 :]:
            if not sao_parecidos(a.nome_normalizado, b.nome_normalizado):
                continue
            # Import tardio: busca importa este módulo no carregamento.
            from app.domain.busca import se_contradizem

            if se_contradizem(a, b):
                continue
            menor, maior = par_ordenado(a.id, b.id)
            if ("ingrediente", menor, maior) in visao.distintos:
                continue
            pares.append((a, b))
    return pares


def vence_primeiro(lotes: list[LoteVisao]) -> date | None:
    datas = [lv.vence_em for lv in lotes if lv.saldo > 0 and lv.vence_em is not None]
    return min(datas) if datas else None


def custo_medio_base(lotes: list[LoteVisao]) -> tuple[Decimal | None, int, int]:
    """Custo médio por unidade base, ponderado pelo saldo dos lotes com custo conhecido.

    Devolve (custo, lotes_com_custo, lotes_com_saldo). Lote sem custo não entra como zero.
    """
    com_saldo = [lv for lv in lotes if lv.saldo > 0]
    com_custo = [lv for lv in com_saldo if lv.lote.custo_unidade_base is not None]
    peso = sum((lv.saldo for lv in com_custo), ZERO)
    if not com_custo or peso <= 0:
        return None, 0, len(com_saldo)
    total = sum((lv.saldo * lv.lote.custo_unidade_base for lv in com_custo), ZERO)  # type: ignore[operator]
    return total / peso, len(com_custo), len(com_saldo)


# ---------------------------------------------------------------- estado das etapas


EM_DIA, ATENCAO, FALTA = "em_dia", "atencao", "falta"
_GRAVIDADE = {EM_DIA: 0, ATENCAO: 1, FALTA: 2}


@dataclass
class Etapa:
    id: str
    nome: str
    pergunta: str
    estado: str | None  # None = etapa que ainda não existe ("em breve")
    frase: str
    href: str | None = None


@dataclass
class Alertas:
    vencem: list[LoteVisao]
    sem_saldo: list[Ingrediente]
    pares: list[tuple[Ingrediente, Ingrediente]]


@dataclass
class Fluxo:
    etapas: list[Etapa]
    alertas: Alertas
    entradas_total: int
    entradas_pendentes: int
    proximo_passo: dict | None


def _plural(n: int, singular: str, plural: str) -> str:
    return f"{n} {singular if n == 1 else plural}"


def pendentes_ids(db: Session) -> set[UUID]:
    """Entradas com ao menos um lote sem validade informada (nem data, nem 'sem validade')."""
    consulta = (
        select(EntradaLinha.entrada_id)
        .join(Lote, Lote.id == EntradaLinha.lote_id)
        .where(Lote.validade.is_(None), Lote.sem_validade.is_(False))
        .distinct()
    )
    return set(db.scalars(consulta))


def calcular_fluxo(db: Session, hoje: date, visao: Visao | None = None) -> Fluxo:
    visao = visao or carregar_visao(db)
    entradas_total = int(db.scalar(select(func.count()).select_from(Entrada)) or 0)
    entradas_pendentes = len(pendentes_ids(db))

    # Entradas
    if entradas_total == 0:
        entradas = Etapa(
            "entradas", "Entradas", "O que chegou?", FALTA, "nenhuma entrada ainda", "/entradas"
        )
    elif entradas_pendentes > 0:
        entradas = Etapa(
            "entradas",
            "Entradas",
            "O que chegou?",
            ATENCAO,
            _plural(entradas_pendentes, "pendente", "pendentes"),
            "/entradas?filtro=pendentes",
        )
    else:
        entradas = Etapa(
            "entradas",
            "Entradas",
            "O que chegou?",
            EM_DIA,
            _plural(entradas_total, "entrada", "entradas"),
            "/entradas",
        )

    # Ingredientes
    ativos = [i for i in visao.ingredientes.values() if i.ativo]
    com_saldo = [i for i in ativos if visao.saldo_do_ingrediente(i.id) > 0]
    sem_saldo = sorted((i for i in ativos if i not in com_saldo), key=lambda i: i.nome_normalizado)
    limite = hoje + timedelta(days=JANELA_VALIDADE_DIAS)
    vencem = [
        lv
        for lv in visao.lotes
        if lv.saldo > 0 and lv.vence_em is not None and lv.vence_em <= limite
    ]
    pares = pares_parecidos(visao)
    ingredientes_vencem = {lv.item.ingrediente_id for lv in vencem}

    if not com_saldo:
        ingredientes = Etapa(
            "ingredientes",
            "Ingredientes",
            "O que eu tenho?",
            FALTA,
            "nenhum com saldo",
            "/ingredientes",
        )
    elif ingredientes_vencem:
        ingredientes = Etapa(
            "ingredientes",
            "Ingredientes",
            "O que eu tenho?",
            ATENCAO,
            f"{len(ingredientes_vencem)} {'vence' if len(ingredientes_vencem) == 1 else 'vencem'} em {JANELA_VALIDADE_DIAS} dias",
            "/ingredientes?filtro=vence7",
        )
    elif sem_saldo:
        ingredientes = Etapa(
            "ingredientes",
            "Ingredientes",
            "O que eu tenho?",
            ATENCAO,
            _plural(len(sem_saldo), "sem saldo", "sem saldo"),
            "/ingredientes?filtro=sem_saldo",
        )
    elif pares:
        ingredientes = Etapa(
            "ingredientes",
            "Ingredientes",
            "O que eu tenho?",
            ATENCAO,
            _plural(len(pares), "par parecido", "pares parecidos"),
            "/ingredientes",
        )
    else:
        ingredientes = Etapa(
            "ingredientes",
            "Ingredientes",
            "O que eu tenho?",
            EM_DIA,
            f"{len(com_saldo)} com saldo",
            "/ingredientes",
        )
    # Uma etapa não fica em dia se a anterior está em falta.
    if entradas.estado == FALTA and ingredientes.estado == EM_DIA:
        ingredientes.estado = ATENCAO

    from app.domain.produtos import etapa_produtos
    from app.domain.receitas import etapa_receitas

    produtos = etapa_produtos(db)
    if ingredientes.estado == FALTA and produtos.estado == EM_DIA:
        produtos.estado = ATENCAO
    receitas = etapa_receitas(db)
    if receitas.estado == EM_DIA and any(e.estado == FALTA for e in (entradas, ingredientes, produtos)):
        receitas.estado = ATENCAO
    etapas = [
        entradas,
        ingredientes,
        produtos,
        receitas,
        Etapa("producao", "Produção", "O que faço hoje?", None, "em breve"),
    ]

    proximo = None
    for alvo in (FALTA, ATENCAO):
        etapa = next((e for e in etapas if e.estado == alvo), None)
        if etapa is not None:
            proximo = _proximo_passo(etapa, entradas_pendentes, vencem, sem_saldo, pares)
            break

    return Fluxo(
        etapas=etapas,
        alertas=Alertas(vencem=vencem, sem_saldo=sem_saldo, pares=pares),
        entradas_total=entradas_total,
        entradas_pendentes=entradas_pendentes,
        proximo_passo=proximo,
    )


def _proximo_passo(etapa: Etapa, pendentes: int, vencem, sem_saldo, pares) -> dict:
    if etapa.id == "entradas" and etapa.estado == FALTA:
        return {
            "etapa": "entradas",
            "estado": FALTA,
            "titulo": "Lance a primeira entrada",
            "texto": "Ainda não chegou nada no sistema. Registre o que você tem em casa ou o que acabou de chegar.",
            "acao": "Nova entrada",
            "href": "/entradas?nova=1",
        }
    if etapa.id == "entradas":
        return {
            "etapa": "entradas",
            "estado": ATENCAO,
            "titulo": _plural(pendentes, "entrada pendente", "entradas pendentes"),
            "texto": "Falta informar a validade de lotes. Sem ela o sistema não avisa quando algo vence.",
            "acao": "Ver pendentes",
            "href": "/entradas?filtro=pendentes",
        }
    if etapa.id == "produtos" and etapa.estado == FALTA:
        return {
            "etapa": "produtos",
            "estado": FALTA,
            "titulo": "Cadastre o primeiro produto",
            "texto": "O produto nasce aqui. Ele só vai para a Loja quando você decidir.",
            "acao": "Novo produto",
            "href": "/produtos?novo=1",
        }
    if etapa.id == "produtos":
        return {
            "etapa": "produtos",
            "estado": ATENCAO,
            "titulo": etapa.frase,
            "texto": "Há produto produzido sem receita, ou comprado sem o item de estoque.",
            "acao": "Ver pendentes",
            "href": "/produtos?filtro=pendentes",
        }
    if etapa.id == "receitas" and etapa.estado == FALTA:
        return {
            "etapa": "receitas",
            "estado": FALTA,
            "titulo": "Monte a primeira receita",
            "texto": "Há produto produzido sem receita. O modo de fazer fica na receita técnica.",
            "acao": "Ver receitas",
            "href": "/receitas",
        }
    if etapa.id == "receitas":
        return {
            "etapa": "receitas",
            "estado": ATENCAO,
            "titulo": etapa.frase,
            "texto": "Há receita em rascunho ou com custo parcial.",
            "acao": "Ver receitas",
            "href": "/receitas",
        }
    if etapa.estado == FALTA:
        return {
            "etapa": "ingredientes",
            "estado": FALTA,
            "titulo": "Nenhum ingrediente com saldo",
            "texto": "Lance uma entrada para saber o que você tem.",
            "acao": "Nova entrada",
            "href": "/entradas?nova=1",
        }
    if vencem:
        return {
            "etapa": "ingredientes",
            "estado": ATENCAO,
            "titulo": f"{_plural(len({lv.item.ingrediente_id for lv in vencem}), 'ingrediente', 'ingredientes')} perto do vencimento",
            "texto": f"Há lotes que vencem em até {JANELA_VALIDADE_DIAS} dias.",
            "acao": "Ver ingredientes",
            "href": "/ingredientes?filtro=vence7",
        }
    if sem_saldo:
        return {
            "etapa": "ingredientes",
            "estado": ATENCAO,
            "titulo": f"{len(sem_saldo)} sem saldo",
            "texto": "Ingredientes cadastrados que não têm nada em estoque.",
            "acao": "Ver ingredientes",
            "href": "/ingredientes?filtro=sem_saldo",
        }
    return {
        "etapa": "ingredientes",
        "estado": ATENCAO,
        "titulo": _plural(
            len(pares), "par parece o mesmo ingrediente", "pares parecem o mesmo ingrediente"
        ),
        "texto": "Junte os repetidos para o saldo não ficar dividido.",
        "acao": "Ver ingredientes",
        "href": "/ingredientes",
    }


def hoje_em(fuso: str) -> date:
    from datetime import datetime
    from zoneinfo import ZoneInfo

    return datetime.now(ZoneInfo(fuso)).date()


def locais_ativos(db: Session) -> list[Local]:
    return list(
        db.scalars(
            select(Local).where(Local.ativo.is_(True)).order_by(Local.padrao.desc(), Local.nome)
        )
    )

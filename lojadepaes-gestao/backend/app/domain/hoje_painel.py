"""O que o painel da Hoje precisa além do fluxo: o que acabou, pendências, necessidade e números.

Só lê. Nada daqui grava no Gestão nem na Loja. A demanda da Loja chega pronta (`LinhaDemanda`);
este módulo liga cada item ao produto do Gestão e faz as contas no lado do Gestão.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domain import estoque as est
from app.domain.estoque import Visao, _plural, controla_estoque, ingredientes_com_entrada
from app.domain.producao import _produto_da_loja, calcular_foto
from app.domain.receitas import _calcular, _ids_publicados, _linhas_de
from app.loja_reader.demanda import LinhaDemanda
from app.models.estoque import Entrada, EntradaLinha
from app.models.produtos import Produto, Receita, ReceitaLinha, ReceitaVersao

FALTA, ATENCAO = est.FALTA, est.ATENCAO


# ---------------------------------------------------------------- estoque


def acabaram(db: Session, visao: Visao) -> list:
    """Ingredientes que controlam estoque, já tiveram entrada e hoje estão sem saldo."""
    com_entrada = ingredientes_com_entrada(db)
    return sorted(
        (
            i
            for i in visao.ingredientes.values()
            if i.ativo
            and controla_estoque(i)
            and i.id in com_entrada
            and visao.saldo_do_ingrediente(i.id) <= 0
        ),
        key=lambda i: i.nome_normalizado,
    )


def sem_entrada(db: Session, visao: Visao) -> list:
    """Ingredientes que controlam estoque e nunca receberam uma entrada."""
    com_entrada = ingredientes_com_entrada(db)
    return sorted(
        (
            i
            for i in visao.ingredientes.values()
            if i.ativo and controla_estoque(i) and i.id not in com_entrada
        ),
        key=lambda i: i.nome_normalizado,
    )


# ---------------------------------------------------------------- vínculo da demanda


def _situacao_da_receita(db: Session, produto_id: UUID) -> str:
    receita = db.scalar(select(Receita).where(Receita.produto_id == produto_id))
    if receita is None:
        return "sem_receita"
    if db.scalar(select(ReceitaVersao.id).where(ReceitaVersao.receita_id == receita.id).limit(1)):
        return "publicada"
    if db.scalar(select(ReceitaLinha.id).where(ReceitaLinha.receita_id == receita.id).limit(1)):
        return "rascunho"
    return "sem_receita"


def vincular(db: Session, linhas: list[LinhaDemanda]) -> list[dict | None]:
    """Para cada item da demanda, o produto do Gestão e a situação da receita (None: sem vínculo)."""
    cache: dict[tuple[str | None, str | None], dict | None] = {}
    saida: list[dict | None] = []
    for linha in linhas:
        if linha.origem == "criador" or not linha.product_id:
            saida.append(None)
            continue
        chave = (linha.product_id, linha.product_variant_id)
        if chave not in cache:
            produto = _produto_da_loja(db, linha.product_id, linha.product_variant_id)
            cache[chave] = (
                None
                if produto is None
                else {
                    "produto_id": str(produto.id),
                    "produto": produto.nome,
                    "receita": _situacao_da_receita(db, produto.id),
                }
            )
        saida.append(cache[chave])
    return saida


def _rotulo(linha: LinhaDemanda) -> str:
    nome = linha.produto_ou_massa or "Item sem nome"
    return f"{nome} · {linha.variante_ou_forma}" if linha.variante_ou_forma else nome


# ---------------------------------------------------------------- necessidade


def _folhas_da_foto(linhas: list[dict]) -> list[tuple[str, Decimal]]:
    """(nome, gramas) de cada ingrediente real. Preparo da casa abre nos filhos; inóculo não conta."""
    saida: list[tuple[str, Decimal]] = []
    for linha in linhas or []:
        if linha.get("funcao") == "inoculo":
            continue
        if linha.get("componente"):
            saida.extend(_folhas_da_foto(linha.get("filhos") or []))
            continue
        saida.append((str(linha.get("nome") or ""), Decimal(str(linha.get("quantidade_g") or 0))))
    return saida


def necessidade(
    db: Session, visao: Visao, linhas: list[LinhaDemanda], vinculos: list[dict | None]
) -> dict:
    """O que as fornadas confirmadas consomem (receitas publicadas) contra o saldo do estoque."""
    unidades_por_produto: dict[str, int] = {}
    fora: list[dict] = []
    for linha, vinculo in zip(linhas, vinculos, strict=True):
        if linha.paes_fisicos <= 0:
            continue
        if vinculo is None:
            fora.append({"nome": _rotulo(linha), "paes_fisicos": linha.paes_fisicos, "motivo": "sem_vinculo"})
        elif vinculo["receita"] != "publicada":
            fora.append(
                {"nome": _rotulo(linha), "paes_fisicos": linha.paes_fisicos, "motivo": vinculo["receita"]}
            )
        else:
            unidades_por_produto[vinculo["produto_id"]] = (
                unidades_por_produto.get(vinculo["produto_id"], 0) + linha.paes_fisicos
            )

    por_nome = {
        i.nome: i
        for i in visao.ingredientes.values()
        if i.ativo and controla_estoque(i) and i.unidade_base == "g"
    }
    precisa: dict[UUID, Decimal] = {}
    for produto_id, unidades in unidades_por_produto.items():
        foto = calcular_foto(db, UUID(produto_id), unidades)
        if foto.get("sem_receita"):
            continue
        for nome, gramas in _folhas_da_foto(foto.get("linhas") or []):
            ing = por_nome.get(nome)
            if ing is None:
                continue
            precisa[ing.id] = precisa.get(ing.id, Decimal(0)) + gramas

    itens = []
    for ing_id, total in precisa.items():
        ing = visao.ingredientes[ing_id]
        tem = visao.saldo_do_ingrediente(ing_id)
        falta = max(Decimal(0), total - tem)
        itens.append(
            {
                "ingrediente_id": str(ing_id),
                "ingrediente": ing.nome,
                "unidade_base": ing.unidade_base,
                "precisa": float(total),
                "tem": float(tem),
                "falta": float(falta),
            }
        )
    itens.sort(key=lambda x: (x["falta"] <= 0, x["ingrediente"].lower()))
    return {
        "itens": itens,
        # Quantos pães ficaram fora da conta; `fora_da_conta_itens` diz quais e por quê.
        "fora_da_conta": sum(x["paes_fisicos"] for x in fora),
        "fora_da_conta_itens": fora,
    }


def necessidade_vazia() -> dict:
    return {"itens": [], "fora_da_conta": 0, "fora_da_conta_itens": []}


# ---------------------------------------------------------------- pendências


def _pendencia(codigo: str, texto: str, acao: str, href: str, estado: str) -> dict:
    return {"codigo": codigo, "texto": texto, "acao": acao, "href": href, "estado": estado}


def pendencias(
    db: Session,
    visao: Visao,
    *,
    fonte_loja: bool,
    linhas: list[LinhaDemanda] | None,
    vinculos: list[dict | None] | None,
) -> list[dict]:
    """Só o que tem quantidade maior que zero. O que falta vem antes do que pede atenção."""
    achadas: list[dict] = []

    produzidos = list(
        db.scalars(
            select(Produto).where(Produto.ativo.is_(True), Produto.modalidade == "produzido")
        )
    )
    publicados = _ids_publicados(db)
    sem_receita = [p for p in produzidos if p.id not in publicados]
    if sem_receita:
        achadas.append(
            _pendencia(
                "produtos_sem_receita",
                _plural(len(sem_receita), "produto sem receita publicada", "produtos sem receita publicada"),
                "Ver produtos",
                "/produtos?filtro=pendentes",
                FALTA,
            )
        )

    if fonte_loja and linhas is not None and vinculos is not None:
        sem_vinculo = {
            (linha.product_id, linha.product_variant_id)
            for linha, vinculo in zip(linhas, vinculos, strict=True)
            if linha.origem == "catalogo" and vinculo is None
        }
        if sem_vinculo:
            achadas.append(
                _pendencia(
                    "demanda_sem_vinculo",
                    _plural(
                        len(sem_vinculo),
                        "item da Loja sem produto no Gestão",
                        "itens da Loja sem produto no Gestão",
                    ),
                    "Ver produção",
                    "/producao",
                    FALTA,
                )
            )

    comprados = db.scalar(
        select(func.count())
        .select_from(Produto)
        .where(
            Produto.ativo.is_(True),
            Produto.modalidade == "comprado",
            Produto.item_estoque_id.is_(None),
        )
    )
    if comprados:
        achadas.append(
            _pendencia(
                "comprado_sem_item",
                _plural(
                    int(comprados),
                    "produto comprado sem item de estoque",
                    "produtos comprados sem item de estoque",
                ),
                "Ver produtos",
                "/produtos?filtro=pendentes",
                ATENCAO,
            )
        )

    entradas_pendentes = len(est.pendentes_ids(db))
    if entradas_pendentes:
        achadas.append(
            _pendencia(
                "entradas_pendentes",
                _plural(entradas_pendentes, "entrada sem validade", "entradas sem validade"),
                "Ver entradas",
                "/entradas?filtro=pendentes",
                ATENCAO,
            )
        )

    nunca = sem_entrada(db, visao)
    if nunca:
        texto = (
            f"{nunca[0].nome} ainda sem entrada"
            if len(nunca) == 1
            else f"{nunca[0].nome} e mais {len(nunca) - 1} sem entrada"
        )
        achadas.append(
            _pendencia(
                "sem_entrada",
                texto,
                "Ver ingredientes",
                "/ingredientes?filtro=sem_saldo",
                ATENCAO,
            )
        )

    parciais = 0
    for produto in produzidos:
        if produto.id not in publicados:
            continue
        receita = db.scalar(select(Receita).where(Receita.produto_id == produto.id))
        if receita is None:
            continue
        if _calcular(db, visao, receita, _linhas_de(db, receita.id))["custo_parcial"]:
            parciais += 1
    if parciais:
        achadas.append(
            _pendencia(
                "custo_parcial",
                _plural(parciais, "receita com custo parcial", "receitas com custo parcial"),
                "Ver receitas",
                "/receitas",
                ATENCAO,
            )
        )

    return [p for p in achadas if p["estado"] == FALTA] + [p for p in achadas if p["estado"] == ATENCAO]


# ---------------------------------------------------------------- indicadores


def indicadores(db: Session, hoje: date) -> dict:
    produzidos = set(
        db.scalars(
            select(Produto.id).where(Produto.ativo.is_(True), Produto.modalidade == "produzido")
        )
    )
    inicio = hoje.replace(day=1)
    proximo = (inicio + timedelta(days=32)).replace(day=1)
    do_mes = Entrada.data >= inicio, Entrada.data < proximo
    qtd = int(db.scalar(select(func.count()).select_from(Entrada).where(*do_mes)) or 0)
    valor = db.scalar(
        select(func.sum(EntradaLinha.valor_total))
        .join(Entrada, Entrada.id == EntradaLinha.entrada_id)
        .where(*do_mes)
    )
    return {
        "receitas_publicadas": len(_ids_publicados(db) & produzidos),
        "produtos_produzidos": len(produzidos),
        "entradas_mes_qtd": qtd,
        "entradas_mes_valor": float(valor) if valor is not None else 0.0,
    }

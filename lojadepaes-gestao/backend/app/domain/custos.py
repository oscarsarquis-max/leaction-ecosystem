"""Custo de um lote: leitura e "Corrigir custo".

O lote guarda o custo na unidade base (R$ por g, ml ou un) = valor pago ÷ quantidade comprada. Corrigir o
custo NÃO é movimento de saldo: grava um histórico (quem, quando, antes, depois, motivo) e nunca mexe na
quantidade. O valor pago de uma correção vale para a quantidade COMPRADA do lote (a soma das linhas de
entrada), não para o saldo de hoje.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator
from sqlalchemy import func, select

from app.domain import estoque as est
from app.domain.contexto import Contexto
from app.domain.errors import ErroDeDominio
from app.models.estoque import CorrecaoCusto, EntradaLinha, Lote
from app.models.usuarios import Usuario


class CorrecaoIn(BaseModel):
    """Informe o valor pago (total, R$) OU o preço por unidade (R$ por kg, L ou embalagem)."""

    valor_pago: Decimal | None = None
    preco_unidade: Decimal | None = None
    motivo: str = Field(min_length=3, max_length=300)

    @model_validator(mode="after")
    def _um_so(self) -> CorrecaoIn:
        if (self.valor_pago is None) == (self.preco_unidade is None):
            raise ValueError("informe o valor pago ou o preço por unidade, não os dois")
        return self


Modo = Literal["valor_pago", "preco_unidade"]


def quantidade_comprada(db, lote_id: UUID) -> Decimal:
    """Tudo o que entrou neste lote por entrada (na unidade base). Ajustes de saldo não contam."""
    total = db.scalar(
        select(func.sum(EntradaLinha.quantidade_base)).where(EntradaLinha.lote_id == lote_id)
    )
    return Decimal(total or 0)


def _lote(db, lote_id: UUID, *, travar: bool = False) -> Lote:
    consulta = select(Lote).where(Lote.id == lote_id)
    if travar:
        consulta = consulta.with_for_update()
    lote = db.scalar(consulta)
    if lote is None:
        raise ErroDeDominio("lote_inexistente", "Esse lote não existe.", status=404)
    return lote


def valor_do_lote(custo_base: Decimal | None, comprada: Decimal) -> Decimal | None:
    """Quanto custou o que foi comprado, com o custo gravado (arredondado a centavos)."""
    if custo_base is None or comprada <= 0:
        return None
    return est.arredondar_centavos(custo_base * comprada)


def historico_do_lote(db, lote_id: UUID) -> list[dict]:
    nomes = {i: n for i, n in db.execute(select(Usuario.id, Usuario.nome))}
    saida = []
    for c in db.scalars(
        select(CorrecaoCusto)
        .where(CorrecaoCusto.lote_id == lote_id)
        .order_by(CorrecaoCusto.criado_em.desc())
    ):
        saida.append(
            {
                "id": c.id,
                "quando": c.criado_em,
                "quem": nomes.get(c.usuario_id),
                "modo": c.modo,
                "valor_pago": float(c.valor_pago) if c.valor_pago is not None else None,
                "preco_informado": float(c.preco_informado) if c.preco_informado is not None else None,
                "custo_antes": float(c.custo_antes) if c.custo_antes is not None else None,
                "custo_depois": float(c.custo_depois),
                "quantidade_base": float(c.quantidade_base),
                "motivo": c.motivo,
            }
        )
    return saida


def correcoes_recentes(db, lote_ids) -> dict[UUID, CorrecaoCusto]:
    """A correção mais nova de cada lote, para o selo "custo corrigido"."""
    ids = list({i for i in lote_ids if i is not None})
    if not ids:
        return {}
    achados: dict[UUID, CorrecaoCusto] = {}
    for correcao in db.scalars(
        select(CorrecaoCusto)
        .where(CorrecaoCusto.lote_id.in_(ids))
        .order_by(CorrecaoCusto.criado_em.desc())
    ):
        achados.setdefault(correcao.lote_id, correcao)
    return achados


def resumo_correcao(correcao: CorrecaoCusto | None) -> dict:
    if correcao is None:
        return {"custo_corrigido": False, "custo_antes": None, "custo_depois": None}
    return {
        "custo_corrigido": True,
        "custo_antes": float(correcao.custo_antes) if correcao.custo_antes is not None else None,
        "custo_depois": float(correcao.custo_depois),
    }


def dados_do_lote(db, lote_id: UUID) -> dict:
    """O que o diálogo "Corrigir custo" precisa: o lote, o que foi comprado e o custo de hoje."""
    lote = _lote(db, lote_id)
    visao = est.carregar_visao(db)
    item = visao.itens[lote.item_id]
    ing = visao.ingredientes[item.ingrediente_id]
    comprada = quantidade_comprada(db, lote.id)
    return {
        "id": lote.id,
        "codigo": lote.codigo,
        "item": item.nome,
        "marca": item.marca,
        "ingrediente_id": ing.id,
        "ingrediente": ing.nome,
        "unidade_base": ing.unidade_base,
        "unidade_controle": item.unidade_controle,
        "conteudo_embalagem": float(item.conteudo_embalagem)
        if item.conteudo_embalagem is not None
        else None,
        "quantidade_comprada_base": float(comprada),
        "custo_unidade_base": float(lote.custo_unidade_base)
        if lote.custo_unidade_base is not None
        else None,
        "valor_pago_atual": (
            float(v) if (v := valor_do_lote(lote.custo_unidade_base, comprada)) is not None else None
        ),
        "historico": historico_do_lote(db, lote.id),
    }


def corrigir_custo(ctx: Contexto, lote_id: UUID, dados: CorrecaoIn) -> dict:
    """Troca o custo do lote e guarda o histórico. A quantidade (o saldo) não muda."""
    db = ctx.db
    lote = _lote(db, lote_id, travar=True)
    visao = est.carregar_visao(db)
    item = visao.itens[lote.item_id]
    comprada = quantidade_comprada(db, lote.id)
    if comprada <= 0:
        raise ErroDeDominio(
            "lote_sem_compra", "Este lote não veio de uma entrada: não há o que corrigir."
        )
    motivo = dados.motivo.strip()
    if len(motivo) < 3:
        raise ErroDeDominio("motivo_obrigatorio", "Diga o motivo da correção.")

    if dados.valor_pago is not None:
        if dados.valor_pago < 0:
            raise ErroDeDominio("custo_invalido", "O valor pago não pode ser negativo.")
        modo: Modo = "valor_pago"
        novo = est.custo_de_valor_pago(dados.valor_pago, comprada)
    else:
        assert dados.preco_unidade is not None
        if dados.preco_unidade < 0:
            raise ErroDeDominio("custo_invalido", "O preço não pode ser negativo.")
        modo = "preco_unidade"
        novo = est.custo_para_base(item.unidade_controle, dados.preco_unidade, item.conteudo_embalagem)

    antes = lote.custo_unidade_base
    if antes is not None and Decimal(antes) == novo.quantize(Decimal("0.00000001")):
        raise ErroDeDominio("sem_diferenca", "O custo informado é igual ao atual. Nada a corrigir.")

    lote.custo_unidade_base = novo
    db.add(
        CorrecaoCusto(
            lote_id=lote.id,
            usuario_id=ctx.principal.usuario_id,  # type: ignore[arg-type]
            quantidade_base=comprada,
            modo=modo,
            valor_pago=dados.valor_pago,
            preco_informado=dados.preco_unidade,
            custo_antes=antes,
            custo_depois=novo,
            motivo=motivo,
        )
    )
    db.flush()
    db.refresh(lote)  # a partir daqui vale o custo como o banco o guardou (8 casas)
    # O valor de cada linha de entrada deste lote acompanha o custo vigente (o que foi digitado fica em
    # `valor_pago`/`custo_informado`; o histórico guarda o antes e o depois).
    for linha in db.scalars(select(EntradaLinha).where(EntradaLinha.lote_id == lote.id)):
        linha.valor_total = est.arredondar_centavos(linha.quantidade_base * lote.custo_unidade_base)
    db.flush()
    return dados_do_lote(db, lote.id)

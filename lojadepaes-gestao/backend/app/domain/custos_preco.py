"""Custos fixos rateados por kg e regra de preço (margem ou markup).

O preço da Loja só é lido. Nada daqui grava na Loja.
Não confundir com app.domain.custos (corrigir custo de lote).
"""

from __future__ import annotations

import logging
from decimal import ROUND_HALF_UP, Decimal
from types import SimpleNamespace
from uuid import UUID, uuid4

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.domain.errors import ErroDeDominio
from app.domain.estoque import carregar_visao
from app.domain.perdas import resolver_receita
from app.domain.producao import calcular_foto
from app.domain.receitas import _calcular, _versao_publicada
from app.models.custos import CustoFixo, ParametrosCusto
from app.models.produtos import Familia, Produto, Receita

log = logging.getLogger("gestao.custos")

_CENTAVO = Decimal("0.01")
_CEM = Decimal(100)
_MIL = Decimal(1000)

_SQL_VARIANTES = text(
    """
    SELECT pv.id::text AS id,
           COALESCE(pv.display_name, p.name) AS variante,
           pv.price_cents AS price_cents,
           pv.physical_units AS physical_units,
           pv.units_per_pack AS units_per_pack
    FROM product_variants pv
    JOIN products p ON p.id = pv.product_id
    WHERE pv.is_active
      AND (pv.id = CAST(:origem AS uuid) OR pv.product_id = CAST(:origem AS uuid))
    ORDER BY pv.sort_order, pv.display_name
    """
)


def _num(valor: Decimal | None) -> float | None:
    if valor is None:
        return None
    return float(valor)


def _dinheiro(valor: Decimal) -> Decimal:
    return valor.quantize(_CENTAVO, rounding=ROUND_HALF_UP)


def _regra_de(tipo: str | None, valor: Decimal | None) -> dict | None:
    if tipo is None or valor is None:
        return None
    return {"tipo": tipo, "valor": float(valor)}


def _validar_regra(regra: dict | None) -> tuple[str | None, Decimal | None]:
    if regra is None:
        return None, None
    tipo = regra.get("tipo")
    if tipo not in ("margem", "markup"):
        raise ErroDeDominio("regra_tipo", "A regra precisa ser margem ou markup.")
    try:
        valor = Decimal(str(regra["valor"]))
    except Exception as erro:
        raise ErroDeDominio("regra_valor", "Informe um valor numérico para a regra.") from erro
    if tipo == "margem":
        if valor <= 0 or valor >= 100:
            raise ErroDeDominio(
                "margem_invalida",
                "A margem precisa ficar entre 0 e 100, sem incluir os extremos.",
            )
    elif valor <= 0:
        raise ErroDeDominio("markup_invalido", "O markup precisa ser maior que zero.")
    return tipo, valor


def _validar_massa(massa) -> Decimal | None:
    if massa is None:
        return None
    valor = Decimal(str(massa))
    if valor <= 0:
        raise ErroDeDominio("massa_invalida", "A massa do mês precisa ser maior que zero.")
    return valor


def _parametros(db: Session, org_id: UUID) -> ParametrosCusto:
    atual = db.get(ParametrosCusto, org_id)
    if atual is not None:
        return atual
    atual = ParametrosCusto(organizacao_id=org_id)
    db.add(atual)
    db.flush()
    return atual


def _resolver_regra(
    produto: Produto, familia: Familia | None, geral: ParametrosCusto
) -> tuple[dict | None, str | None]:
    propria = _regra_de(produto.regra_tipo, produto.regra_valor)
    if propria is not None:
        return propria, "produto"
    if familia is not None:
        da_familia = _regra_de(familia.regra_tipo, familia.regra_valor)
        if da_familia is not None:
            return da_familia, "familia"
    geral_r = _regra_de(geral.regra_tipo, geral.regra_valor)
    if geral_r is not None:
        return geral_r, "geral"
    return None, None


def _sugerido(regra: dict | None, custo_variavel: Decimal | None, custo_total: Decimal | None) -> Decimal | None:
    if regra is None:
        return None
    tipo = regra["tipo"]
    valor = Decimal(str(regra["valor"]))
    if tipo == "margem":
        if custo_variavel is None:
            return None
        denom = Decimal(1) - (valor / _CEM)
        if denom <= 0:
            return None
        return _dinheiro(custo_variavel / denom)
    if custo_total is None:
        return None
    return _dinheiro(custo_total * valor)


def _custo_publicado(
    db: Session, produto: Produto
) -> tuple[Decimal | None, bool, bool]:
    """Custo variável por unidade e se é parcial; e se há versão publicada."""
    receita = db.scalar(select(Receita).where(Receita.produto_id == produto.id))
    if receita is None:
        return None, False, False
    versao = _versao_publicada(db, receita.id)
    if versao is None or not versao.linhas:
        return None, False, False
    linhas = []
    for ordem, bruta in enumerate(versao.linhas, start=1):
        ing_id = bruta.get("ingrediente_id")
        linhas.append(
            SimpleNamespace(
                id=uuid4(),
                ingrediente_id=UUID(str(ing_id)) if ing_id else None,
                texto=bruta.get("texto"),
                quantidade=Decimal(str(bruta["quantidade"])),
                unidade=str(bruta.get("unidade") or "g"),
                ordem=ordem,
                observacao=bruta.get("observacao"),
                origem=bruta.get("origem") or "manual",
                faixa_min=None,
                faixa_max=None,
                funcao=bruta.get("funcao") or "massa",
            )
        )
    receita_calc = SimpleNamespace(
        id=receita.id,
        produto_id=receita.produto_id,
        rendimento_quantidade=versao.rendimento_quantidade
        if versao.rendimento_quantidade is not None
        else receita.rendimento_quantidade,
        rendimento_unidade=versao.rendimento_unidade or receita.rendimento_unidade,
        perda_percentual=versao.perda_percentual
        if versao.perda_percentual is not None
        else receita.perda_percentual,
        peso_unidade_g=versao.peso_unidade_g
        if versao.peso_unidade_g is not None
        else receita.peso_unidade_g,
    )
    visao = carregar_visao(db)
    conta = _calcular(db, visao, receita_calc, linhas)  # type: ignore[arg-type]
    perdas = resolver_receita(
        db, receita, familia_id=produto.familia_id, massa_total_g=conta["total_massa_g"]
    )
    custo = None
    if conta["custo_total"] is not None and perdas.get("unidades"):
        custo = Decimal(str(conta["custo_total"])) / Decimal(perdas["unidades"])
    elif conta.get("custo_por_unidade") is not None:
        custo = Decimal(str(conta["custo_por_unidade"]))
    return custo, bool(conta["custo_parcial"]), True


def _unidades_variante(physical_units, units_per_pack) -> tuple[int, str]:
    """Retorna (unidades, campo usado). Preferência: physical_units → units_per_pack → 1."""
    if physical_units is not None and Decimal(str(physical_units)) > 0:
        return int(Decimal(str(physical_units))), "physical_units"
    if units_per_pack is not None and Decimal(str(units_per_pack)) > 0:
        return int(Decimal(str(units_per_pack))), "units_per_pack"
    return 1, "default_1"


def _precos_loja(
    loja: Session | None,
    produto: Produto,
    custo_variavel: Decimal | None,
    custo_total: Decimal | None,
) -> list[dict]:
    if loja is None or produto.origem_loja_id is None:
        return []
    try:
        linhas = loja.execute(_SQL_VARIANTES, {"origem": str(produto.origem_loja_id)}).mappings().all()
    except Exception:
        log.exception("leitura da Loja falhou para o produto %s", produto.id)
        try:
            loja.rollback()
        except Exception:
            pass
        return []
    saida = []
    for linha in linhas:
        cents = linha["price_cents"]
        if cents is None:
            continue
        preco = _dinheiro(Decimal(cents) / _CEM)
        unidades, campo_unidades = _unidades_variante(linha["physical_units"], linha["units_per_pack"])
        por_un = _dinheiro(preco / Decimal(unidades))
        mc = None
        mc_pct = None
        markup = None
        resultado = None
        if custo_variavel is not None:
            mc = _dinheiro(por_un - custo_variavel)
            if por_un > 0:
                mc_pct = (mc / por_un * _CEM).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
        if custo_total is not None and custo_total > 0:
            markup = (por_un / custo_total).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            resultado = _dinheiro(por_un - custo_total)
        saida.append(
            {
                "variante": linha["variante"] or "",
                "unidades": unidades,
                "campo_unidades": campo_unidades,
                "preco": float(preco),
                "preco_por_unidade": float(por_un),
                "mc": _num(mc),
                "mc_pct": _num(mc_pct),
                "markup": _num(markup),
                "resultado": _num(resultado),
            }
        )
    return saida


def visao(
    db: Session,
    org_id: UUID,
    loja: Session | None = None,
    *,
    fonte_loja: bool = False,
) -> dict:
    """Custos e regras da organização da sessão. Loja só quando fonte_loja=True."""
    loja_leitura = loja if fonte_loja else None
    params = _parametros(db, org_id)
    fixos = list(
        db.scalars(
            select(CustoFixo)
            .where(CustoFixo.ativo.is_(True))
            .order_by(CustoFixo.nome, CustoFixo.criado_em)
        )
    )
    total = sum((f.valor_mensal for f in fixos), Decimal(0))
    por_kg = None
    if params.massa_mensal_kg is not None and params.massa_mensal_kg > 0:
        por_kg = total / params.massa_mensal_kg

    familias = {
        f.id: f for f in db.scalars(select(Familia).order_by(Familia.nome))
    }
    produtos = list(
        db.scalars(
            select(Produto)
            .where(
                Produto.ativo.is_(True),
                Produto.modalidade == "produzido",
                Produto.uso_venda.is_(True),
            )
            .order_by(Produto.nome)
        )
    )

    linhas_produtos = []
    for produto in produtos:
        familia = familias.get(produto.familia_id) if produto.familia_id else None
        custo_var, parcial, publicada = _custo_publicado(db, produto)
        massa_g = None
        if publicada:
            foto = calcular_foto(db, produto.id, 1)
            massa_bruta = foto.get("massa_necessaria_g")
            if massa_bruta is not None:
                massa_g = Decimal(str(massa_bruta))
        rateio = None
        if massa_g is not None and por_kg is not None:
            rateio = massa_g / _MIL * por_kg
        custo_total = None
        if custo_var is not None:
            custo_total = custo_var + (rateio or Decimal(0))
        regra_propria = _regra_de(produto.regra_tipo, produto.regra_valor)
        regra, origem = _resolver_regra(produto, familia, params)
        sugerido = _sugerido(regra, custo_var, custo_total)
        linhas_produtos.append(
            {
                "produto_id": str(produto.id),
                "nome": produto.nome,
                "familia_id": str(familia.id) if familia else None,
                "familia": familia.nome if familia else None,
                "receita_publicada": publicada,
                "massa_g": _num(massa_g),
                "custo_variavel": _num(_dinheiro(custo_var) if custo_var is not None else None),
                "custo_parcial": parcial,
                "rateio": _num(_dinheiro(rateio) if rateio is not None else None),
                "custo_total": _num(_dinheiro(custo_total) if custo_total is not None else None),
                "regra_propria": regra_propria,
                "regra": regra,
                "regra_origem": origem,
                "preco_sugerido": _num(sugerido),
                "loja": _precos_loja(loja_leitura, produto, custo_var, custo_total),
            }
        )

    return {
        "parametros": {
            "massa_mensal_kg": _num(params.massa_mensal_kg),
            "regra": _regra_de(params.regra_tipo, params.regra_valor),
            "custo_fixo_total": float(_dinheiro(total)),
            "custo_fixo_por_kg": _num(_dinheiro(por_kg) if por_kg is not None else None),
        },
        "custos_fixos": [
            {"id": str(f.id), "nome": f.nome, "valor_mensal": float(_dinheiro(f.valor_mensal))}
            for f in fixos
        ],
        "familias": [
            {
                "id": str(f.id),
                "nome": f.nome,
                "regra": _regra_de(f.regra_tipo, f.regra_valor),
            }
            for f in sorted(familias.values(), key=lambda x: x.nome.lower())
        ],
        "produtos": linhas_produtos,
    }


def _devolver(db: Session, org_id: UUID, loja: Session | None, fonte_loja: bool) -> dict:
    return visao(db, org_id, loja, fonte_loja=fonte_loja)


def salvar_parametros(
    db: Session, org_id: UUID, dados: dict, loja: Session | None = None, *, fonte_loja: bool = False
) -> dict:
    params = _parametros(db, org_id)
    params.massa_mensal_kg = _validar_massa(dados.get("massa_mensal_kg"))
    tipo, valor = _validar_regra(dados.get("regra"))
    params.regra_tipo = tipo
    params.regra_valor = valor
    db.flush()
    return _devolver(db, org_id, loja, fonte_loja)


def criar_fixo(
    db: Session, org_id: UUID, dados: dict, loja: Session | None = None, *, fonte_loja: bool = False
) -> dict:
    nome = " ".join((dados.get("nome") or "").split())
    if not nome:
        raise ErroDeDominio("nome_vazio", "Informe o nome do custo fixo.")
    valor = Decimal(str(dados["valor_mensal"]))
    if valor < 0:
        raise ErroDeDominio("valor_negativo", "O valor mensal não pode ser negativo.")
    db.add(CustoFixo(organizacao_id=org_id, nome=nome, valor_mensal=valor, ativo=True))
    db.flush()
    return _devolver(db, org_id, loja, fonte_loja)


def editar_fixo(
    db: Session, fixo_id: UUID, dados: dict, loja: Session | None = None, *, fonte_loja: bool = False
) -> dict:
    fixo = db.get(CustoFixo, fixo_id)
    if fixo is None or not fixo.ativo:
        raise ErroDeDominio("custo_inexistente", "Esse custo fixo não existe.", status=404)
    nome = " ".join((dados.get("nome") or "").split())
    if not nome:
        raise ErroDeDominio("nome_vazio", "Informe o nome do custo fixo.")
    valor = Decimal(str(dados["valor_mensal"]))
    if valor < 0:
        raise ErroDeDominio("valor_negativo", "O valor mensal não pode ser negativo.")
    fixo.nome = nome
    fixo.valor_mensal = valor
    db.flush()
    return _devolver(db, fixo.organizacao_id, loja, fonte_loja)


def apagar_fixo(
    db: Session, fixo_id: UUID, loja: Session | None = None, *, fonte_loja: bool = False
) -> dict:
    fixo = db.get(CustoFixo, fixo_id)
    if fixo is None or not fixo.ativo:
        raise ErroDeDominio("custo_inexistente", "Esse custo fixo não existe.", status=404)
    fixo.ativo = False
    db.flush()
    return _devolver(db, fixo.organizacao_id, loja, fonte_loja)


def regra_familia(
    db: Session, familia_id: UUID, regra: dict | None, loja: Session | None = None, *, fonte_loja: bool = False
) -> dict:
    familia = db.get(Familia, familia_id)
    if familia is None:
        raise ErroDeDominio("familia_inexistente", "Essa família não existe.", status=404)
    tipo, valor = _validar_regra(regra)
    familia.regra_tipo = tipo
    familia.regra_valor = valor
    db.flush()
    return _devolver(db, familia.organizacao_id, loja, fonte_loja)


def regra_produto(
    db: Session, produto_id: UUID, regra: dict | None, loja: Session | None = None, *, fonte_loja: bool = False
) -> dict:
    produto = db.get(Produto, produto_id)
    if produto is None or not produto.ativo:
        raise ErroDeDominio("produto_inexistente", "Esse produto não existe.", status=404)
    tipo, valor = _validar_regra(regra)
    produto.regra_tipo = tipo
    produto.regra_valor = valor
    db.flush()
    return _devolver(db, produto.organizacao_id, loja, fonte_loja)

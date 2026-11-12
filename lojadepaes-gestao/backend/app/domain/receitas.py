"""Receita técnica: linhas, % do padeiro, custo calculado e versão publicada.

Conversões: só kg↔g e l↔ml. Unidade só quando o ingrediente é em unidade.
Massa e volume não se convertem. Custo desconhecido fica desconhecido, nunca zero.
O custo de um preparo da casa é o da versão publicada, por unidade base.
"""

from __future__ import annotations

from decimal import ROUND_FLOOR, ROUND_HALF_UP, Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.contexto import Contexto
from app.domain.errors import ErroDeDominio
from app.domain.estoque import Visao, carregar_visao
from app.domain.perdas import resolver_receita
from app.domain.verificacoes import e_agua, e_farinha, verificar
from app.models.estoque import Ingrediente
from app.models.produtos import Familia, Produto, Receita, ReceitaLinha, ReceitaVersao

UNIDADES = ("g", "kg", "ml", "l", "un")
_GRUPO = {"g": "massa", "kg": "massa", "ml": "volume", "l": "volume", "un": "un"}
_FATOR = {"g": Decimal(1), "kg": Decimal(1000), "ml": Decimal(1), "l": Decimal(1000), "un": Decimal(1)}
_ZERO = Decimal(0)
_CEM = Decimal(100)
_NOMES = {"g": "grama", "kg": "quilo", "ml": "mililitro", "l": "litro", "un": "unidade"}


def _num(valor: Decimal | None) -> float | None:
    if valor is None:
        return None
    return float(valor)


def _qtd(valor: Decimal) -> str:
    texto = f"{valor:f}"
    if "." in texto:
        texto = texto.rstrip("0").rstrip(".")
    return texto


def compativel(unidade: str, base: str) -> bool:
    return _GRUPO.get(unidade) == _GRUPO.get(base) and unidade in _GRUPO and base in _GRUPO


def para_base(quantidade: Decimal, unidade: str, base: str) -> Decimal:
    if not compativel(unidade, base):
        raise ErroDeDominio(
            "unidade_incompativel",
            f"Não dá para converter {_NOMES.get(unidade, unidade)} em {_NOMES.get(base, base)}.",
        )
    return quantidade * _FATOR[unidade] / _FATOR[base]


def _rendimento_na_base(
    quantidade: Decimal | None,
    unidade: str | None,
    base: str,
    peso_unidade_g: Decimal | None,
) -> Decimal | None:
    if quantidade is None or not unidade or quantidade <= 0:
        return None
    if compativel(unidade, base):
        return para_base(quantidade, unidade, base)
    if unidade == "un" and base == "g" and peso_unidade_g is not None and peso_unidade_g > 0:
        return quantidade * peso_unidade_g
    return None


def _linhas_de(db: Session, receita_id: UUID) -> list[ReceitaLinha]:
    return list(
        db.scalars(
            select(ReceitaLinha).where(ReceitaLinha.receita_id == receita_id).order_by(ReceitaLinha.ordem)
        )
    )


def _ingrediente_do_produto(db: Session, produto_id: UUID) -> str | None:
    ing = db.scalar(select(Ingrediente).where(Ingrediente.produto_id == produto_id))
    return str(ing.id) if ing else None


def _receita_do_produto(db: Session, produto_id: UUID) -> tuple[Produto, Receita]:
    produto = db.get(Produto, produto_id)
    if produto is None or not produto.ativo or produto.modalidade != "produzido":
        raise ErroDeDominio("receita_inexistente", "Esse produto produzido não existe.", status=404)
    receita = db.scalar(select(Receita).where(Receita.produto_id == produto.id))
    if receita is None:
        raise ErroDeDominio("receita_inexistente", "Esse produto ainda não tem receita.", status=404)
    return produto, receita


def _versao_publicada(db: Session, receita_id: UUID) -> ReceitaVersao | None:
    return db.scalar(
        select(ReceitaVersao)
        .where(ReceitaVersao.receita_id == receita_id)
        .order_by(ReceitaVersao.versao.desc())
    )


def _ids_publicados(db: Session) -> set[UUID]:
    return set(
        db.scalars(select(Receita.produto_id).join(ReceitaVersao, ReceitaVersao.receita_id == Receita.id))
    )


def _componentes(db: Session, receita_id: UUID) -> set[UUID]:
    saida: set[UUID] = set()
    for linha in _linhas_de(db, receita_id):
        if linha.ingrediente_id is None:
            continue
        ing = db.get(Ingrediente, linha.ingrediente_id)
        if ing is not None and ing.produto_id is not None:
            saida.add(ing.produto_id)
    return saida


def _nome_produto(db: Session, produto_id: UUID) -> str:
    produto = db.get(Produto, produto_id)
    return produto.nome if produto else "um preparo"


def _frase_caminho(db: Session, caminho: list[UUID]) -> str:
    nomes = [_nome_produto(db, pid) for pid in caminho]
    if len(nomes) < 2:
        return "Esta receita usa um preparo que, direta ou indiretamente, usa ela mesma."
    texto = f"{nomes[0]} usa {nomes[1]}"
    for extra in nomes[2:]:
        texto += f", que usa {extra}"
    return texto + "."


def _conferir_ciclo(db: Session, origem: UUID, usados: dict[UUID, int]) -> None:
    """usados mapeia o preparo citado para a linha (1-based) desta receita."""
    fila: list[tuple[UUID, list[UUID], int]] = [
        (alvo, [origem, alvo], linha) for alvo, linha in usados.items()
    ]
    vistos: set[UUID] = set()
    while fila:
        alvo, caminho, linha = fila.pop(0)
        if alvo == origem:
            raise ErroDeDominio("ciclo_receita", _frase_caminho(db, caminho), linha=linha)
        if alvo in vistos:
            continue
        vistos.add(alvo)
        receita = db.scalar(select(Receita).where(Receita.produto_id == alvo))
        if receita is None:
            continue
        for proximo in _componentes(db, receita.id):
            if proximo == alvo:
                continue
            fila.append((proximo, caminho + [proximo], linha))


def custo_de_lotes(visao: Visao, ingrediente_id: UUID) -> Decimal | None:
    """Média ponderada dos lotes com saldo. Sem saldo, o custo do último lote. Sem custo, desconhecido."""
    lotes = [lv for lv in visao.lotes if lv.item.ingrediente_id == ingrediente_id]
    com_saldo = [lv for lv in lotes if lv.saldo > 0 and lv.lote.custo_unidade_base is not None]
    peso = sum((lv.saldo for lv in com_saldo), _ZERO)
    if peso > 0:
        total = sum((lv.saldo * lv.lote.custo_unidade_base for lv in com_saldo), _ZERO)
        return total / peso
    com_custo = [lv for lv in lotes if lv.lote.custo_unidade_base is not None]
    if not com_custo:
        return None
    ultimo = max(com_custo, key=lambda lv: (lv.lote.criado_em, str(lv.lote.id)))
    return ultimo.lote.custo_unidade_base


def custo_por_base(
    db: Session,
    visao: Visao,
    ingrediente: Ingrediente,
    visitando: set[UUID] | None = None,
) -> Decimal | None:
    """R$ por unidade base. Preparos da casa usam a receita publicada, de forma recursiva."""
    if ingrediente.produto_id is None:
        return custo_de_lotes(visao, ingrediente.id)
    visitando = set() if visitando is None else visitando
    if ingrediente.produto_id in visitando:
        return None
    receita = db.scalar(select(Receita).where(Receita.produto_id == ingrediente.produto_id))
    if receita is None:
        return None
    versao = _versao_publicada(db, receita.id)
    if versao is None or not versao.linhas:
        return None
    visitando.add(ingrediente.produto_id)
    total = _ZERO
    massa = _ZERO
    inoculo_g = _ZERO
    tem_inoculo = False
    desconhecido = False
    for bruta in versao.linhas:
        ing = db.get(Ingrediente, UUID(str(bruta["ingrediente_id"])))
        if ing is None:
            visitando.discard(ingrediente.produto_id)
            return None
        gramas = _ZERO
        if compativel(str(bruta.get("unidade") or "g"), "g"):
            try:
                gramas = para_base(Decimal(str(bruta["quantidade"])), str(bruta["unidade"]), "g")
            except ErroDeDominio:
                gramas = _ZERO
        if bruta.get("funcao") == "inoculo" and ing.produto_id == ingrediente.produto_id:
            tem_inoculo = True
            massa += gramas
            inoculo_g += gramas
            continue
        massa += gramas
        custo = custo_por_base(db, visao, ing, visitando)
        if custo is None:
            desconhecido = True
            continue
        try:
            na_base = para_base(Decimal(str(bruta["quantidade"])), str(bruta["unidade"]), ing.unidade_base)
        except ErroDeDominio:
            visitando.discard(ingrediente.produto_id)
            return None
        total += na_base * custo
    visitando.discard(ingrediente.produto_id)
    if tem_inoculo:
        perda = Decimal(versao.perda_percentual or 0)
        rende = (massa * (Decimal(1) - perda / _CEM)).to_integral_value(ROUND_FLOOR)
        disponivel = rende - inoculo_g
        if disponivel <= 0:
            return None
        if desconhecido and total == 0:
            return None
        return total / disponivel
    # Preparo da casa grava o rendimento já líquido da perda de processo.
    if (
        versao.rendimento_unidade == "g"
        and versao.peso_unidade_g is None
        and versao.rendimento_quantidade is not None
    ):
        if desconhecido:
            return None
        base = Decimal(str(versao.rendimento_quantidade))
        if base <= 0:
            return None
        return total / base
    if desconhecido:
        return None
    perda = Decimal(versao.perda_percentual or 0)
    fator = Decimal(1) - (perda / _CEM)
    base_rend = _rendimento_na_base(
        Decimal(str(versao.rendimento_quantidade)) if versao.rendimento_quantidade is not None else None,
        versao.rendimento_unidade,
        ingrediente.unidade_base,
        Decimal(str(versao.peso_unidade_g)) if versao.peso_unidade_g is not None else None,
    )
    if fator <= 0 or base_rend is None or base_rend <= 0:
        return None
    return total / (base_rend * fator)


def composicao_publicada(
    db: Session, produto_id: UUID, visitando: set[UUID] | None = None
) -> tuple[Decimal, Decimal]:
    """Farinha e massa, em gramas, de uma fornada da receita publicada."""
    visitando = set() if visitando is None else visitando
    if produto_id in visitando:
        return _ZERO, _ZERO
    receita = db.scalar(select(Receita).where(Receita.produto_id == produto_id))
    if receita is None:
        return _ZERO, _ZERO
    versao = _versao_publicada(db, receita.id)
    if versao is None or not versao.linhas:
        return _ZERO, _ZERO
    visitando.add(produto_id)
    farinha = _ZERO
    massa = _ZERO
    for bruta in versao.linhas:
        ing = db.get(Ingrediente, UUID(str(bruta["ingrediente_id"]))) if bruta.get("ingrediente_id") else None
        unidade = str(bruta.get("unidade") or "g")
        if not compativel(unidade, "g"):
            continue
        gramas = para_base(Decimal(str(bruta["quantidade"])), unidade, "g")
        massa += gramas
        if ing is not None and ing.produto_id is not None:
            interna, massa_interna = composicao_publicada(db, ing.produto_id, visitando)
            if massa_interna > 0:
                farinha += gramas * interna / massa_interna
        elif ing is not None and ing.categoria == "Farinhas":
            farinha += gramas
    visitando.discard(produto_id)
    return farinha, massa


def farinha_contida(db: Session, produto_id: UUID, peso_g: Decimal) -> Decimal:
    """Farinha que existe dentro de `peso_g` do preparo publicado."""
    farinha, massa = composicao_publicada(db, produto_id)
    if massa <= 0 or peso_g <= 0:
        return _ZERO
    return peso_g * farinha / massa


def folhas_publicadas(
    db: Session, produto_id: UUID, peso_g: Decimal, visitando: set[UUID] | None = None
) -> list[dict]:
    """Ingredientes da receita publicada, na proporção de `peso_g` do preparo."""
    visitando = set() if visitando is None else visitando
    if produto_id in visitando or peso_g <= 0:
        return []
    receita = db.scalar(select(Receita).where(Receita.produto_id == produto_id))
    if receita is None:
        return []
    versao = _versao_publicada(db, receita.id)
    if versao is None or not versao.linhas:
        return []
    visitando.add(produto_id)
    massa = _ZERO
    preparadas = []
    for bruta in versao.linhas:
        unidade = str(bruta.get("unidade") or "g")
        if not compativel(unidade, "g"):
            continue
        gramas = para_base(Decimal(str(bruta["quantidade"])), unidade, "g")
        massa += gramas
        preparadas.append((bruta, gramas))
    saida: list[dict] = []
    if massa <= 0:
        visitando.discard(produto_id)
        return saida
    fator = peso_g / massa
    for bruta, gramas in preparadas:
        ing = db.get(Ingrediente, UUID(str(bruta["ingrediente_id"]))) if bruta.get("ingrediente_id") else None
        na_porcao = gramas * fator
        if ing is not None and ing.produto_id is not None:
            saida.extend(folhas_publicadas(db, ing.produto_id, na_porcao, visitando))
            continue
        saida.append(
            {
                "ingrediente_id": str(ing.id) if ing else None,
                "nome": ing.nome if ing else str(bruta.get("nome") or ""),
                "quantidade_g": na_porcao,
                "categoria": ing.categoria if ing else None,
            }
        )
    visitando.discard(produto_id)
    return saida


def _farinha_da_linha(db: Session, ing: Ingrediente | None, quantidade: Decimal, unidade: str) -> Decimal:
    if ing is None or not compativel(unidade, "g"):
        return _ZERO
    gramas = para_base(quantidade, unidade, "g")
    if ing.produto_id is not None:
        return farinha_contida(db, ing.produto_id, gramas)
    if ing.categoria == "Farinhas":
        return gramas
    return _ZERO


def _calcular(
    db: Session, visao: Visao, receita: Receita, linhas: list[ReceitaLinha]
) -> dict:
    ingredientes = {
        i.id: i
        for i in (
            db.get(Ingrediente, linha.ingrediente_id) for linha in linhas if linha.ingrediente_id
        )
        if i is not None
    }
    farinha = _ZERO
    for linha in linhas:
        if linha.funcao == "inoculo":
            continue
        ing = ingredientes.get(linha.ingrediente_id) if linha.ingrediente_id else None
        farinha += _farinha_da_linha(db, ing, linha.quantidade, linha.unidade)
    saida_linhas = []
    conhecidos: list[Decimal] = []
    faltam = 0
    massa = _ZERO
    inoculo_g = _ZERO
    tem_inoculo = False
    for linha in linhas:
        ing = ingredientes.get(linha.ingrediente_id) if linha.ingrediente_id else None
        custo = None
        percentual = None
        componente = bool(ing and ing.produto_id)
        inoculo = linha.funcao == "inoculo" and bool(ing and ing.produto_id == receita.produto_id)
        em_gramas = None
        if ing is not None and compativel(linha.unidade, "g"):
            em_gramas = para_base(linha.quantidade, linha.unidade, "g")
            massa += em_gramas
            if farinha > 0 and (not componente or inoculo):
                percentual = em_gramas / farinha * _CEM
        if inoculo:
            tem_inoculo = True
            if em_gramas is not None:
                inoculo_g += em_gramas
        elif ing is not None:
            unitario = custo_por_base(db, visao, ing)
            if unitario is None or not compativel(linha.unidade, ing.unidade_base):
                faltam += 1
            else:
                custo = para_base(linha.quantidade, linha.unidade, ing.unidade_base) * unitario
                conhecidos.append(custo)
        saida_linhas.append(
            {
                "id": str(linha.id),
                "ingrediente_id": str(ing.id) if ing else None,
                "nome": ing.nome if ing else (linha.texto or ""),
                "categoria": ing.categoria if ing else None,
                "componente": bool(ing and ing.produto_id),
                "unidade_base": ing.unidade_base if ing else None,
                "texto": linha.texto,
                "a_decidir": ing is None,
                "quantidade": _num(linha.quantidade),
                "unidade": linha.unidade,
                "ordem": linha.ordem,
                "observacao": linha.observacao,
                "percentual_padeiro": _num(percentual),
                "custo": _num(custo),
                "origem": linha.origem or "manual",
                "faixa_min": _num(linha.faixa_min),
                "faixa_max": _num(linha.faixa_max),
                "funcao": linha.funcao or "massa",
            }
        )
    parcial = faltam > 0
    total = sum(conhecidos, _ZERO) if conhecidos else None
    por_unidade = None
    if total is not None and receita.rendimento_quantidade and receita.rendimento_unidade:
        fator = Decimal(1) - (Decimal(receita.perda_percentual or 0) / _CEM)
        divisor = Decimal(receita.rendimento_quantidade) * fator
        if fator > 0 and divisor > 0:
            por_unidade = total / divisor
    custo_por_grama = None
    if tem_inoculo and massa > inoculo_g:
        custo_por_grama = sum(conhecidos, _ZERO) / (massa - inoculo_g)
    return {
        "linhas": saida_linhas,
        "total_massa_g": _num(massa) if massa > 0 else None,
        "custo_total": _num(total),
        "custo_parcial": parcial,
        "linhas_sem_custo": faltam,
        "custo_por_unidade": _num(por_unidade),
        "custo_por_grama": _num(custo_por_grama),
    }


def _selos(situacao: str, tem_linhas: bool, parcial: bool) -> list[str]:
    selos = []
    if not tem_linhas:
        selos.append("sem_linhas")
    if situacao == "rascunho":
        selos.append("rascunho")
    if parcial:
        selos.append("custo_parcial")
    return selos


def _rotulo_rendimento(quantidade: Decimal | None, unidade: str | None) -> str | None:
    if quantidade is None or not unidade:
        return None
    return f"{_qtd(Decimal(quantidade))} {unidade}"


def _modo_massa(produto: Produto) -> bool:
    return bool(produto.uso_componente) and not bool(produto.uso_venda)


def _gramas_linha(quantidade, unidade) -> Decimal:
    if quantidade is None or not compativel(str(unidade or "g"), "g"):
        return _ZERO
    try:
        return para_base(Decimal(str(quantidade)), str(unidade), "g")
    except ErroDeDominio:
        return _ZERO


def _par_de_linhas(
    db: Session, produto_id: UUID, linhas: list, visitando: set[UUID]
) -> tuple[Decimal, Decimal, Decimal]:
    """Farinha, água e massa destas linhas. O inóculo entra no equilíbrio do resto."""
    if produto_id in visitando:
        return _ZERO, _ZERO, _ZERO
    visitando.add(produto_id)
    try:
        farinha_resto = _ZERO
        agua_resto = _ZERO
        massa_resto = _ZERO
        q_inoculo = _ZERO
        massa = _ZERO
        for linha in linhas:
            gramas = _gramas_linha(linha.get("quantidade"), linha.get("unidade"))
            massa += gramas
            ing = None
            if linha.get("ingrediente_id"):
                ing = db.get(Ingrediente, UUID(str(linha["ingrediente_id"])))
            proprio = linha.get("funcao") == "inoculo" and ing is not None and ing.produto_id == produto_id
            if proprio:
                q_inoculo += gramas
                continue
            massa_resto += gramas
            if ing is not None and ing.produto_id is not None:
                farinha_parte, agua_parte = _par_publicado(db, ing.produto_id, gramas, visitando)
                farinha_resto += farinha_parte
                agua_resto += agua_parte
                continue
            nome = ing.nome if ing is not None else linha.get("nome")
            categoria = ing.categoria if ing is not None else linha.get("categoria")
            if e_farinha(nome, categoria):
                farinha_resto += gramas
            if e_agua(nome, categoria):
                agua_resto += gramas
        farinha = farinha_resto
        agua = agua_resto
        if massa_resto > 0 and q_inoculo > 0:
            farinha += q_inoculo * farinha_resto / massa_resto
            agua += q_inoculo * agua_resto / massa_resto
        return farinha, agua, massa
    finally:
        visitando.discard(produto_id)


def _par_publicado(
    db: Session, produto_id: UUID, peso_g: Decimal, visitando: set[UUID]
) -> tuple[Decimal, Decimal]:
    if peso_g <= 0 or produto_id in visitando:
        return _ZERO, _ZERO
    receita = db.scalar(select(Receita).where(Receita.produto_id == produto_id))
    if receita is None:
        return _ZERO, _ZERO
    versao = _versao_publicada(db, receita.id)
    if versao is None or not versao.linhas:
        return _ZERO, _ZERO
    farinha, agua, massa = _par_de_linhas(db, produto_id, versao.linhas, visitando)
    if massa <= 0:
        return _ZERO, _ZERO
    fator = peso_g / massa
    return farinha * fator, agua * fator


def _hidratacao(db: Session, produto: Produto, linhas: list) -> dict | None:
    farinha, agua, _massa = _par_de_linhas(db, produto.id, linhas, set())
    if farinha <= 0:
        return None
    percentual = (agua / farinha * _CEM).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
    return {"farinha_g": float(farinha), "agua_g": float(agua), "percentual": float(percentual)}


def _rendimento_massa(
    produto: Produto, linhas: list, total_massa_g, processo_pct, custo_total
) -> tuple[dict | None, Decimal | None]:
    if not _modo_massa(produto):
        return None, None
    massa = Decimal(str(total_massa_g or 0))
    reserva = _ZERO
    for linha in linhas:
        if linha.get("funcao") == "inoculo":
            reserva += _gramas_linha(linha.get("quantidade"), linha.get("unidade"))
    pct = Decimal(str(processo_pct)) if processo_pct is not None else _ZERO
    rende = (massa * (Decimal(1) - pct / _CEM)).to_integral_value(ROUND_FLOOR)
    disponivel = rende - reserva
    custo_kg = None
    if custo_total is not None and disponivel > 0:
        custo_kg = (Decimal(str(custo_total)) / disponivel * Decimal(1000)).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
    return {
        "massa_g": float(massa),
        "processo_pct": None if processo_pct is None else float(pct),
        "rende_g": int(rende),
        "reserva_g": float(reserva),
        "disponivel_g": float(disponivel),
        "custo_por_kg": None if custo_kg is None else float(custo_kg),
    }, custo_kg


def _ficha(db: Session, visao: Visao, produto: Produto, receita: Receita) -> dict:
    linhas = _linhas_de(db, receita.id)
    conta = _calcular(db, visao, receita, linhas)
    perdas = resolver_receita(
        db, receita, familia_id=produto.familia_id, massa_total_g=conta["total_massa_g"]
    )
    if conta["custo_total"] is not None and perdas["unidades"]:
        conta["custo_por_unidade"] = float(Decimal(str(conta["custo_total"])) / Decimal(perdas["unidades"]))
    publicada = _versao_publicada(db, receita.id)
    tem_ingrediente = any(not item["a_decidir"] for item in conta["linhas"]) or bool(conta["linhas"])
    verificacoes = _verificacoes_da_ficha(db, produto, conta["linhas"])
    if perdas["processo"]["origem"] == "referencia" or perdas["coccao"]["origem"] == "referencia":
        verificacoes["avisos"].append(
            {"codigo": "perda_referencia", "mensagem": "Ainda sem padrão da casa nem medição"}
        )
    modo = "massa" if _modo_massa(produto) else "unidades"
    processo_pct = perdas["processo"]["percentual"]
    rendimento_massa, custo_kg = _rendimento_massa(
        produto, conta["linhas"], conta["total_massa_g"], processo_pct, conta["custo_total"]
    )
    if modo == "massa":
        conta["custo_por_grama"] = None if custo_kg is None else float(custo_kg / Decimal(1000))
    if modo != "unidades" or produto.cultura_viva:
        verificacoes["pendencias"] = [
            item for item in verificacoes["pendencias"] if item["codigo"] != "sem_fermento"
        ]
    if rendimento_massa is not None and rendimento_massa["disponivel_g"] < 0:
        verificacoes["pendencias"].append(
            {
                "codigo": "reserva_maior",
                "mensagem": "A reserva do inóculo é maior do que a receita rende.",
            }
        )
    hidratacao = _hidratacao(db, produto, conta["linhas"])
    return {
        "id": str(receita.id),
        "produto_id": str(produto.id),
        "produto": produto.nome,
        "cultura_viva": bool(produto.cultura_viva),
        "ingrediente_id": _ingrediente_do_produto(db, produto.id),
        "situacao": receita.situacao,
        "versao": receita.versao,
        "rendimento_quantidade": _num(receita.rendimento_quantidade),
        "rendimento_unidade": receita.rendimento_unidade,
        "rendimento": _rotulo_rendimento(receita.rendimento_quantidade, receita.rendimento_unidade),
        "peso_unidade_g": _num(receita.peso_unidade_g),
        "perda_percentual": _num(receita.perda_percentual),
        "formato": receita.formato,
        "unidades_desejadas": receita.unidades_desejadas,
        "modo_fazer": list(receita.modo_fazer or []),
        "selos": _selos(receita.situacao, bool(linhas), conta["custo_parcial"]),
        "publicada": None
        if publicada is None
        else {
            "versao": publicada.versao,
            "linhas": publicada.linhas,
            "rendimento_quantidade": _num(publicada.rendimento_quantidade),
            "rendimento_unidade": publicada.rendimento_unidade,
        },
        **conta,
        "tem_linhas": tem_ingrediente,
        "verificacoes": verificacoes,
        "perdas": perdas,
        "modo_rendimento": modo,
        "rendimento_massa": rendimento_massa,
        "hidratacao": hidratacao,
    }


def _verificacoes_da_ficha(db: Session, produto: Produto, linhas: list[dict]) -> dict:
    familia = db.get(Familia, produto.familia_id) if produto.familia_id else None
    farinha = _ZERO
    componentes = []
    diretas = []
    for item in linhas:
        ing = db.get(Ingrediente, UUID(str(item["ingrediente_id"]))) if item.get("ingrediente_id") else None
        gramas = _ZERO
        if compativel(item.get("unidade") or "g", "g") and item.get("quantidade"):
            gramas = para_base(Decimal(str(item["quantidade"])), item["unidade"], "g")
        if ing is not None and ing.produto_id is not None and gramas > 0:
            componentes.append({"nome": ing.nome, "folhas": folhas_publicadas(db, ing.produto_id, gramas)})
            farinha += farinha_contida(db, ing.produto_id, gramas)
            continue
        if ing is not None and ing.categoria == "Farinhas":
            farinha += gramas
        diretas.append(
            {
                "nome": item.get("nome"),
                "categoria": item.get("categoria"),
                "quantidade_g": gramas,
                "componente": False,
                "funcao": item.get("funcao") or "massa",
            }
        )
    bruto = verificar(
        diretas,
        farinha=farinha,
        familia=familia.nome if familia else None,
        componentes=componentes,
    )
    return {"pendencias": bruto["pendencias"], "avisos": bruto["avisos"]}


def listar(db: Session, filtro: str) -> dict:
    visao = carregar_visao(db)
    produtos = list(
        db.scalars(
            select(Produto)
            .where(Produto.ativo.is_(True), Produto.modalidade == "produzido")
            .order_by(Produto.nome)
        )
    )
    saida = []
    for produto in produtos:
        receita = db.scalar(select(Receita).where(Receita.produto_id == produto.id))
        if receita is None:
            continue
        ficha = _ficha(db, visao, produto, receita)
        item = {
            "id": ficha["id"],
            "produto_id": ficha["produto_id"],
            "nome": produto.nome,
            "rendimento": ficha["rendimento"],
            "custo_por_unidade": ficha["custo_por_unidade"],
            "custo_parcial": ficha["custo_parcial"],
            "situacao": ficha["situacao"],
            "selos": ficha["selos"],
            "versao": ficha["versao"],
        }
        if filtro == "rascunhos" and item["situacao"] != "rascunho":
            continue
        if filtro == "publicadas" and item["situacao"] != "publicada":
            continue
        if filtro == "custo_parcial" and not item["custo_parcial"]:
            continue
        saida.append(item)
    return {"filtro": filtro, "receitas": saida}


def detalhe(db: Session, produto_id: UUID) -> dict:
    produto, receita = _receita_do_produto(db, produto_id)
    return _ficha(db, carregar_visao(db), produto, receita)


def resumo_no_produto(db: Session, receita: Receita) -> dict:
    """O que o painel do produto mostra: linhas reais e o custo por unidade."""
    produto = db.get(Produto, receita.produto_id)
    ficha = _ficha(db, carregar_visao(db), produto, receita)  # type: ignore[arg-type]
    return {
        "id": ficha["id"],
        "situacao": ficha["situacao"],
        "versao": ficha["versao"],
        "publicada": ficha["publicada"] is not None,
        "linhas": [
            {
                "id": linha["id"],
                "nome": linha["nome"],
                "componente": linha["componente"],
                "quantidade": linha["quantidade"],
                "unidade": linha["unidade"],
            }
            for linha in ficha["linhas"]
        ],
        "custo_por_unidade": ficha["custo_por_unidade"],
        "custo_parcial": ficha["custo_parcial"],
        "linhas_sem_custo": ficha["linhas_sem_custo"],
    }


def usados_em(db: Session, produto: Produto) -> list[dict]:
    ing = db.scalar(select(Ingrediente).where(Ingrediente.produto_id == produto.id))
    if ing is None:
        return []
    vistos: dict[UUID, str] = {}
    linhas = db.scalars(select(ReceitaLinha).where(ReceitaLinha.ingrediente_id == ing.id))
    for linha in linhas:
        receita = db.get(Receita, linha.receita_id)
        if receita is None or receita.produto_id == produto.id:
            continue
        outro = db.get(Produto, receita.produto_id)
        if outro is not None and outro.ativo:
            vistos[outro.id] = outro.nome
    return [{"id": str(i), "nome": nome} for i, nome in sorted(vistos.items(), key=lambda par: par[1].lower())]


def _abrir_rascunho(receita: Receita) -> None:
    if receita.situacao == "publicada":
        receita.situacao = "rascunho"
        receita.versao = int(receita.versao) + 1


def _gravar_manual(receita: Receita, lado: str, dados: dict | None) -> None:
    if dados is None:
        return
    origem = dados.get("origem")
    pct = dados.get("percentual")
    motivo = (dados.get("motivo") or "").strip()
    if origem != "manual":
        setattr(receita, f"perda_{lado}_pct", None)
        setattr(receita, f"perda_{lado}_origem", None)
        setattr(receita, f"perda_{lado}_motivo", None)
        setattr(receita, f"perda_{lado}_referencia_id", None)
        if lado == "processo":
            receita.perda_percentual = Decimal(0)
        return
    if pct is None:
        raise ErroDeDominio("perda_invalida", "Informe o percentual do ajuste manual.")
    valor = Decimal(str(pct))
    if valor <= 0 or valor >= 100:
        raise ErroDeDominio("perda_invalida", "A perda fica entre 0 e menos de 100%.")
    if not motivo:
        raise ErroDeDominio("motivo_obrigatorio", "O ajuste manual da perda precisa de um motivo.")
    setattr(receita, f"perda_{lado}_pct", valor)
    setattr(receita, f"perda_{lado}_origem", "manual")
    setattr(receita, f"perda_{lado}_motivo", motivo)
    setattr(receita, f"perda_{lado}_referencia_id", None)
    if lado == "processo":
        receita.perda_percentual = valor


def salvar(
    ctx: Contexto,
    produto_id: UUID,
    *,
    linhas: list[dict],
    rendimento_quantidade: Decimal | None,
    rendimento_unidade: str | None,
    peso_unidade_g: Decimal | None,
    perda_percentual: Decimal,
    modo_fazer: list[str],
    formato: str | None = None,
    unidades_desejadas: int | None = None,
    atualizar_formato: bool = False,
    atualizar_unidades: bool = False,
    atualizar_rendimento: bool = True,
    processo: dict | None = None,
    coccao: dict | None = None,
) -> dict:
    db = ctx.db
    produto, receita = _receita_do_produto(db, produto_id)
    modo_massa = _modo_massa(produto)
    if modo_massa:
        peso_unidade_g = None
        formato = None
        unidades_desejadas = None
        atualizar_formato = True
        atualizar_unidades = True
        coccao = {"origem": None}
    if perda_percentual < 0 or perda_percentual >= 100:
        raise ErroDeDominio("perda_invalida", "A perda fica entre 0 e menos de 100%.")
    if atualizar_rendimento:
        if (rendimento_quantidade is None) != (rendimento_unidade is None):
            raise ErroDeDominio("rendimento_incompleto", "Informe a quantidade e a unidade do rendimento.")
        if rendimento_quantidade is not None and rendimento_quantidade <= 0:
            raise ErroDeDominio("rendimento_invalido", "O rendimento precisa ser maior que zero.")
        if rendimento_unidade is not None and rendimento_unidade not in UNIDADES:
            raise ErroDeDominio("unidade_invalida", "A unidade do rendimento é g, kg, ml, l ou un.")
    if peso_unidade_g is not None and peso_unidade_g <= 0:
        raise ErroDeDominio("peso_invalido", "O peso da unidade precisa ser maior que zero.")

    anteriores = {
        (str(linha.ingrediente_id) if linha.ingrediente_id else (linha.texto or "").strip().lower()): linha
        for linha in _linhas_de(db, receita.id)
    }
    preparadas: list[tuple] = []
    usados: dict[UUID, int] = {}
    inoculo_proprio = 0
    for indice, bruta in enumerate(linhas, start=1):
        quantidade = Decimal(bruta["quantidade"])
        unidade = bruta["unidade"]
        if quantidade <= 0:
            raise ErroDeDominio("quantidade_invalida", f"A quantidade da linha {indice} precisa ser maior que zero.", linha=indice)
        if unidade not in UNIDADES:
            raise ErroDeDominio("unidade_invalida", f"A unidade da linha {indice} é g, kg, ml, l ou un.", linha=indice)
        ing = None
        texto = (bruta.get("texto") or "").strip() or None
        if bruta.get("ingrediente_id"):
            ing = db.get(Ingrediente, bruta["ingrediente_id"])
            if ing is None or not ing.ativo:
                raise ErroDeDominio(
                    "ingrediente_inexistente",
                    f"O ingrediente da linha {indice} não existe.",
                    linha=indice,
                )
            if not compativel(unidade, ing.unidade_base):
                raise ErroDeDominio(
                    "unidade_incompativel",
                    f"A linha {indice} mistura {_NOMES.get(unidade, unidade)} com um ingrediente em {_NOMES.get(ing.unidade_base, ing.unidade_base)}. Massa e volume não se convertem.",
                    linha=indice,
                )
            if ing.produto_id is not None and ing.produto_id != produto_id:
                usados.setdefault(ing.produto_id, indice)
        elif not texto:
            continue
        obs = (bruta.get("observacao") or "").strip() or None
        origem = bruta.get("origem") or "manual"
        if origem not in {"manual", "estimado", "conferido"}:
            origem = "manual"
        chave_anterior = str(ing.id) if ing else (texto or "").strip().lower()
        anterior = anteriores.get(chave_anterior)
        if origem == "estimado" and anterior is not None and anterior.origem == "estimado":
            if Decimal(anterior.quantidade) != quantidade or anterior.unidade != unidade:
                origem = "conferido"
        faixa_min = bruta.get("faixa_min")
        faixa_max = bruta.get("faixa_max")
        if origem == "conferido" and anterior is not None and faixa_min is None:
            faixa_min = anterior.faixa_min
            faixa_max = anterior.faixa_max
        funcao = bruta.get("funcao") or "massa"
        if funcao not in {"massa", "recheio", "cobertura", "finalizacao", "inoculo"}:
            funcao = "massa"
        proprio = bool(ing is not None and ing.produto_id == produto_id)
        if funcao == "inoculo" and not proprio:
            funcao = "massa"
        if proprio:
            if produto.cultura_viva and funcao == "inoculo" and inoculo_proprio == 0:
                inoculo_proprio = indice
            else:
                raise ErroDeDominio(
                    "ciclo_receita",
                    _frase_caminho(db, [produto_id, produto_id]),
                    linha=indice,
                )
        preparadas.append((ing, texto, quantidade, unidade, obs, origem, faixa_min, faixa_max, funcao))

    massa_lote = _ZERO
    massa_inoculo = _ZERO
    for _ing, _texto, quantidade, unidade, _obs, _origem, _faixa_min, _faixa_max, funcao in preparadas:
        if not compativel(unidade, "g"):
            continue
        gramas = para_base(quantidade, unidade, "g")
        massa_lote += gramas
        if funcao == "inoculo":
            massa_inoculo += gramas
    if inoculo_proprio and massa_inoculo >= massa_lote:
        raise ErroDeDominio(
            "inoculo_maior",
            "O inóculo não pode ser maior que a massa.",
            linha=inoculo_proprio,
        )

    _conferir_ciclo(db, produto_id, usados)
    _abrir_rascunho(receita)
    for antiga in _linhas_de(db, receita.id):
        db.delete(antiga)
    db.flush()
    for ordem, (ing, texto, quantidade, unidade, obs, origem, faixa_min, faixa_max, funcao) in enumerate(preparadas, start=1):
        db.add(
            ReceitaLinha(
                receita_id=receita.id,
                ingrediente_id=ing.id if ing else None,
                texto=None if ing else texto,
                quantidade=quantidade,
                unidade=unidade,
                ordem=ordem,
                observacao=obs,
                origem=origem,
                faixa_min=Decimal(str(faixa_min)) if faixa_min is not None else None,
                faixa_max=Decimal(str(faixa_max)) if faixa_max is not None else None,
                funcao=funcao,
            )
        )
    if atualizar_rendimento:
        receita.rendimento_quantidade = rendimento_quantidade
        receita.rendimento_unidade = rendimento_unidade
    receita.peso_unidade_g = peso_unidade_g
    if processo is None and coccao is None:
        receita.perda_percentual = perda_percentual
        if perda_percentual > 0 and receita.perda_processo_origem != "manual":
            receita.perda_processo_pct = perda_percentual
            receita.perda_processo_origem = "manual"
            receita.perda_processo_motivo = receita.perda_processo_motivo or "Valor informado antes do modelo de perdas."
    if atualizar_formato:
        if formato is not None and formato not in {"forma", "forma_enriquecida", "livre", "assadeira", "pequeno"}:
            raise ErroDeDominio("formato_invalido", "O formato não é um dos formatos da casa.")
        receita.formato = formato
    if atualizar_unidades:
        if unidades_desejadas is not None and int(unidades_desejadas) <= 0:
            raise ErroDeDominio("unidades_invalidas", "As unidades desejadas precisam ser maiores que zero.")
        receita.unidades_desejadas = int(unidades_desejadas) if unidades_desejadas else None
    _gravar_manual(receita, "processo", processo)
    _gravar_manual(receita, "coccao", coccao)
    receita.modo_fazer = [passo.strip() for passo in modo_fazer if passo and passo.strip()]
    db.flush()
    ficha = detalhe(db, produto_id)
    if modo_massa:
        rende = int((ficha.get("rendimento_massa") or {}).get("rende_g") or 0)
        if rende > 0:
            receita.rendimento_quantidade = Decimal(rende)
            receita.rendimento_unidade = "g"
            db.flush()
            return detalhe(db, produto_id)
        return ficha
    unidades = (ficha.get("perdas") or {}).get("unidades")
    if unidades and int(unidades) > 0:
        receita.rendimento_quantidade = Decimal(int(unidades))
        receita.rendimento_unidade = "un"
        db.flush()
        return detalhe(db, produto_id)
    return ficha


def publicar(ctx: Contexto, produto_id: UUID, *, confirmar_sem_fermento: bool = False) -> dict:
    db = ctx.db
    produto, receita = _receita_do_produto(db, produto_id)
    linhas = _linhas_de(db, receita.id)
    if not linhas:
        raise ErroDeDominio("sem_linhas", "A receita não tem linhas.")
    for indice, linha in enumerate(linhas, start=1):
        if linha.ingrediente_id is None:
            raise ErroDeDominio(
                "a_decidir",
                f"A linha {indice} ainda está a decidir. Escolha o ingrediente antes de publicar.",
                linha=indice,
            )
        ing = db.get(Ingrediente, linha.ingrediente_id)
        if ing is None or not compativel(linha.unidade, ing.unidade_base):
            raise ErroDeDominio(
                "unidade_incompativel",
                f"A linha {indice} tem uma unidade que não combina com o ingrediente.",
                linha=indice,
            )
    ficha = detalhe(db, produto_id)
    if _modo_massa(produto):
        if any(item["codigo"] == "reserva_maior" for item in ficha["verificacoes"]["pendencias"]):
            raise ErroDeDominio(
                "reserva_maior",
                "A reserva do inóculo é maior do que a receita rende.",
            )
        rende = int((ficha.get("rendimento_massa") or {}).get("rende_g") or 0)
        if rende > 0:
            receita.rendimento_quantidade = Decimal(rende)
            receita.rendimento_unidade = "g"
            db.flush()
    if receita.rendimento_quantidade is None or not receita.rendimento_unidade:
        raise ErroDeDominio(
            "rendimento_vazio",
            "O rendimento sai da massa e do peso final. Falta dado para calcular as unidades.",
        )
    sem_fermento = any(item["codigo"] == "sem_fermento" for item in ficha["verificacoes"]["pendencias"])
    if sem_fermento and not confirmar_sem_fermento:
        raise ErroDeDominio("sem_fermento", "Falta o fermento. Confirme para publicar mesmo assim.")
    if db.scalar(
        select(ReceitaVersao).where(
            ReceitaVersao.receita_id == receita.id, ReceitaVersao.versao == receita.versao
        )
    ):
        raise ErroDeDominio("versao_ja_publicada", "Esta versão já foi publicada.")
    copia = []
    for linha in linhas:
        ing = db.get(Ingrediente, linha.ingrediente_id)
        copia.append(
            {
                "ingrediente_id": str(linha.ingrediente_id),
                "nome": ing.nome if ing else "",
                "quantidade": _num(linha.quantidade),
                "unidade": linha.unidade,
                "ordem": linha.ordem,
                "observacao": linha.observacao,
                "origem": linha.origem or "manual",
                "funcao": linha.funcao or "massa",
            }
        )
    db.add(
        ReceitaVersao(
            receita_id=receita.id,
            versao=receita.versao,
            rendimento_quantidade=receita.rendimento_quantidade,
            rendimento_unidade=receita.rendimento_unidade,
            peso_unidade_g=receita.peso_unidade_g,
            perda_percentual=receita.perda_percentual,
            modo_fazer=list(receita.modo_fazer or []),
            linhas=copia,
        )
    )
    receita.situacao = "publicada"
    db.flush()
    return detalhe(db, produto.id)


def etapa_receitas(db: Session):
    from app.domain.estoque import ATENCAO, EM_DIA, FALTA, Etapa

    produtos = list(
        db.scalars(select(Produto).where(Produto.ativo.is_(True), Produto.modalidade == "produzido"))
    )
    if not produtos:
        return Etapa("receitas", "Receitas", "Como eu faço?", EM_DIA, "nenhum produzido", "/receitas")
    visao = carregar_visao(db)
    publicados = _ids_publicados(db)
    faltam = 0
    atencao = 0
    for produto in produtos:
        receita = db.scalar(select(Receita).where(Receita.produto_id == produto.id))
        if receita is None or (produto.id not in publicados and not _linhas_de(db, receita.id)):
            faltam += 1
            continue
        conta = _calcular(db, visao, receita, _linhas_de(db, receita.id))
        if receita.situacao == "rascunho" or conta["custo_parcial"]:
            atencao += 1
    if faltam:
        texto = "1 sem receita" if faltam == 1 else f"{faltam} sem receita"
        return Etapa("receitas", "Receitas", "Como eu faço?", FALTA, texto, "/receitas")
    if atencao:
        texto = "1 em atenção" if atencao == 1 else f"{atencao} em atenção"
        return Etapa("receitas", "Receitas", "Como eu faço?", ATENCAO, texto, "/receitas")
    texto = "1 receita" if len(produtos) == 1 else f"{len(produtos)} receitas"
    return Etapa("receitas", "Receitas", "Como eu faço?", EM_DIA, texto, "/receitas")

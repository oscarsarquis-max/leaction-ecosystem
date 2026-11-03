"""Entrada sem nota: análise das linhas (parecidos, pendências) e lançamento atômico e idempotente.

A MESMA análise roda na pré-visualização (a tela mostra "Parecido com X" e as pendências) e na
gravação (a API recusa o que a tela deixaria passar). Ninguém grava duplicado por acidente.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.domain import estoque as est
from app.domain.contexto import Contexto
from app.domain.errors import ErroDeDominio
from app.domain.normalizacao import normalizar, rotulo_padrao_lote, sao_parecidos
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

MAX_LINHAS = 300
MOTIVOS = ("contagem", "compra_sem_nota", "bonificacao", "outro")


# ---------------------------------------------------------------- entrada de dados


class LinhaIn(BaseModel):
    # Item que já existe (a tela trava ingrediente, unidade e conteúdo) ...
    item_id: UUID | None = None
    # ... ou item novo (nome como comprado + marca + como é controlado).
    item_nome: str = Field(default="", max_length=160)
    marca: str = Field(default="", max_length=80)
    unidade_controle: Literal["massa", "volume", "embalagem"] | None = None
    # Conteúdo de UMA embalagem, na unidade base do ingrediente.
    conteudo_embalagem: Decimal | None = None
    ingrediente_id: UUID | None = None
    ingrediente_nome: str = Field(default="", max_length=120)
    ingrediente_unidade_base: Literal["g", "ml", "un"] | None = None
    # "novo" = "Criar novo" mesmo havendo parecido (decisão de uma pessoa).
    decisao_item: Literal["novo"] | None = None
    decisao_ingrediente: Literal["novo"] | None = None
    quantidade: Decimal | None = None
    unidade: str = Field(default="", max_length=12)
    lote_codigo: str = Field(default="", max_length=40)
    validade: date | None = None
    sem_validade: bool = False
    # R$ por kg, L ou embalagem (segue a unidade de controle). Vazio = custo desconhecido.
    custo: Decimal | None = None


class VerificarIn(BaseModel):
    linhas: list[LinhaIn] = Field(default_factory=list, max_length=MAX_LINHAS)


class EntradaIn(BaseModel):
    chave: str = Field(min_length=8, max_length=64)
    data: date
    local_id: UUID
    tipo: Literal["sem_nota", "com_nota"] = "sem_nota"
    motivo: Literal["contagem", "compra_sem_nota", "bonificacao", "outro"]
    motivo_detalhe: str = Field(default="", max_length=200)
    fornecedor: str = Field(default="", max_length=160)
    observacao: str = Field(default="", max_length=2000)
    linhas: list[LinhaIn] = Field(min_length=1, max_length=MAX_LINHAS)


# ---------------------------------------------------------------- resultado da análise


class IngredienteRef(BaseModel):
    id: UUID
    nome: str
    unidade_base: str


class Candidato(BaseModel):
    id: UUID
    nome: str
    marca: str = ""
    unidade_controle: str | None = None
    conteudo_embalagem: float | None = None
    ingrediente: IngredienteRef | None = None
    unidade_base: str | None = None


class Pendencia(BaseModel):
    codigo: str
    mensagem: str
    bloqueia: bool = True


class AnaliseLinha(BaseModel):
    posicao: int
    item_existente: Candidato | None = None
    item_igual: Candidato | None = None
    item_parecidos: list[Candidato] = Field(default_factory=list)
    ingrediente_existente: IngredienteRef | None = None
    ingrediente_igual: IngredienteRef | None = None
    ingrediente_parecidos: list[IngredienteRef] = Field(default_factory=list)
    unidade_controle: str | None = None
    conteudo_embalagem: float | None = None
    unidade_base: str | None = None
    unidades_validas: list[str] = Field(default_factory=list)
    custo_por: str | None = None
    pendencias: list[Pendencia] = Field(default_factory=list)
    a_decidir: bool = False
    incompleta: bool = False
    quantidade_base: float | None = None
    valor_total: float | None = None


@dataclass
class Resolvido:
    item: ItemEstoque | None = None
    novo_item: dict | None = None
    ingrediente: Ingrediente | None = None
    novo_ingrediente: dict | None = None
    controle: str | None = None
    conteudo: Decimal | None = None
    base: str | None = None
    quantidade_base: Decimal | None = None
    custo_base: Decimal | None = None
    valor: Decimal | None = None
    lote_existente: Lote | None = None
    parecidos_item: list[ItemEstoque] = field(default_factory=list)
    parecidos_ingrediente: list[Ingrediente] = field(default_factory=list)


def _ing_ref(i: Ingrediente) -> IngredienteRef:
    return IngredienteRef(id=i.id, nome=i.nome, unidade_base=i.unidade_base)


def _candidato(item: ItemEstoque, visao: est.Visao) -> Candidato:
    ing = visao.ingredientes.get(item.ingrediente_id)
    return Candidato(
        id=item.id,
        nome=item.nome,
        marca=item.marca,
        unidade_controle=item.unidade_controle,
        conteudo_embalagem=float(item.conteudo_embalagem)
        if item.conteudo_embalagem is not None
        else None,
        ingrediente=_ing_ref(ing) if ing else None,
        unidade_base=ing.unidade_base if ing else None,
    )


def _itens_parecidos(visao: est.Visao, nome_n: str, marca_n: str) -> list[ItemEstoque]:
    achados = []
    for item in visao.itens.values():
        if not item.ativo or not sao_parecidos(nome_n, item.nome_normalizado):
            continue
        # marcas diferentes e ambas preenchidas = produtos diferentes de verdade
        if marca_n and item.marca_normalizada and marca_n != item.marca_normalizada:
            continue
        achados.append(item)
    return achados


# ---------------------------------------------------------------- análise


def analisar_linhas(
    db, visao: est.Visao, linhas: list[LinhaIn], *, hoje: date | None = None
) -> list[tuple[AnaliseLinha, Resolvido]]:
    novos_ing: dict[str, dict] = {}
    novos_itens: dict[tuple[str, str], dict] = {}
    saida = []
    for posicao, linha in enumerate(linhas, start=1):
        saida.append(_analisar(db, visao, linha, posicao, novos_ing, novos_itens, hoje))
    return saida


def _analisar(
    db, visao, linha: LinhaIn, posicao: int, novos_ing, novos_itens, hoje
) -> tuple[AnaliseLinha, Resolvido]:
    r = Resolvido()
    a = AnaliseLinha(posicao=posicao)
    pend: list[Pendencia] = []

    def bloqueia(codigo: str, mensagem: str) -> None:
        pend.append(Pendencia(codigo=codigo, mensagem=mensagem, bloqueia=True))

    def aviso(codigo: str, mensagem: str) -> None:
        pend.append(Pendencia(codigo=codigo, mensagem=mensagem, bloqueia=False))

    # ----- item
    if linha.item_id is not None:
        item = visao.itens.get(linha.item_id)
        if item is None or not item.ativo:
            bloqueia("item_inexistente", "Esse item não existe mais. Escolha outro.")
        else:
            r.item = item
            r.controle, r.conteudo = item.unidade_controle, item.conteudo_embalagem
            r.ingrediente = visao.ingredientes[item.ingrediente_id]
            r.base = r.ingrediente.unidade_base
            a.item_existente = _candidato(item, visao)
    elif not linha.item_nome.strip():
        bloqueia("sem_item", "Informe o item como foi comprado.")
    else:
        nome_n, marca_n = normalizar(linha.item_nome), normalizar(linha.marca)
        existente = next(
            (
                i
                for i in visao.itens.values()
                if i.nome_normalizado == nome_n and i.marca_normalizada == marca_n
            ),
            None,
        )
        anterior = novos_itens.get((nome_n, marca_n))
        if existente is not None:
            a.item_igual = _candidato(existente, visao)
            bloqueia("item_ja_existe", f"Já existe o item “{existente.nome}”. Use este.")
            r.controle, r.conteudo = existente.unidade_controle, existente.conteudo_embalagem
            r.base = visao.ingredientes[existente.ingrediente_id].unidade_base
        elif anterior is not None:
            # a mesma coisa digitada em outra linha desta entrada: vale como o mesmo item
            if (anterior["controle"], anterior["conteudo"]) != (
                linha.unidade_controle,
                linha.conteudo_embalagem,
            ):
                bloqueia(
                    "item_conflito",
                    "Este item já aparece em outra linha com outra unidade ou conteúdo.",
                )
            r.controle, r.conteudo = anterior["controle"], anterior["conteudo"]
            r.novo_item = anterior
        else:
            r.controle, r.conteudo = linha.unidade_controle, linha.conteudo_embalagem
            r.novo_item = {
                "nome": linha.item_nome.strip(),
                "marca": linha.marca.strip(),
                "nome_n": nome_n,
                "marca_n": marca_n,
                "controle": linha.unidade_controle,
                "conteudo": linha.conteudo_embalagem,
            }
            parecidos = _itens_parecidos(visao, nome_n, marca_n)
            r.parecidos_item = parecidos
            if parecidos:
                a.item_parecidos = [_candidato(i, visao) for i in parecidos]
                if linha.decisao_item != "novo":
                    bloqueia(
                        "item_parecido",
                        "Parecido com um item que já existe. Decida: usar este ou criar novo.",
                    )
            novos_itens[(nome_n, marca_n)] = r.novo_item
        if existente is None and anterior is None:
            if r.controle is None:
                bloqueia("sem_controle", "Escolha como é controlado: massa, volume ou embalagem.")
            if r.controle == "embalagem" and (r.conteudo is None or r.conteudo <= 0):
                bloqueia(
                    "embalagem_sem_conteudo",
                    "Embalagem sem conteúdo: informe quanto vem em cada uma.",
                )
            if r.controle != "embalagem" and r.conteudo is not None:
                r.conteudo = None

        # ----- ingrediente (só item novo escolhe o ingrediente)
        if existente is not None or anterior is not None:
            pass  # item igual (bloqueado) ou repetido nesta entrada: o ingrediente já foi decidido
        elif linha.ingrediente_id is not None:
            ing = visao.ingredientes.get(linha.ingrediente_id)
            if ing is None or not ing.ativo:
                bloqueia(
                    "ingrediente_inexistente", "Esse ingrediente não existe mais. Escolha outro."
                )
            else:
                r.ingrediente, r.base = ing, ing.unidade_base
                a.ingrediente_existente = _ing_ref(ing)
        elif linha.ingrediente_nome.strip():
            ing_n = normalizar(linha.ingrediente_nome)
            igual = next(
                (i for i in visao.ingredientes.values() if i.nome_normalizado == ing_n), None
            )
            if igual is not None and not igual.ativo:
                bloqueia(
                    "ingrediente_inativo",
                    f"“{igual.nome}” foi juntado a outro ingrediente. Escolha o que ficou.",
                )
            elif igual is not None:
                a.ingrediente_igual = _ing_ref(igual)
                bloqueia(
                    "ingrediente_ja_existe", f"Já existe o ingrediente “{igual.nome}”. Use este."
                )
            else:
                anterior_ing = novos_ing.get(ing_n)
                base = linha.ingrediente_unidade_base or BASE_INFERIDA.get(r.controle or "")
                if anterior_ing is not None:
                    r.novo_ingrediente = anterior_ing
                    r.base = anterior_ing["base"]
                    if base and base != anterior_ing["base"]:
                        bloqueia(
                            "unidade_base_conflito",
                            "Este ingrediente aparece em outra linha com outra unidade base.",
                        )
                else:
                    if base is None:
                        bloqueia("sem_unidade_base", "Diga a unidade do ingrediente: g, ml ou un.")
                    r.novo_ingrediente = {
                        "nome": linha.ingrediente_nome.strip(),
                        "nome_n": ing_n,
                        "base": base,
                    }
                    r.base = base
                    parecidos = [
                        i
                        for i in visao.ingredientes.values()
                        if i.ativo and sao_parecidos(ing_n, i.nome_normalizado)
                    ]
                    r.parecidos_ingrediente = parecidos
                    if parecidos:
                        a.ingrediente_parecidos = [_ing_ref(i) for i in parecidos]
                        if linha.decisao_ingrediente != "novo":
                            bloqueia(
                                "ingrediente_parecido",
                                "Parecido com um ingrediente que já existe. Decida: usar este ou criar novo.",
                            )
                    if base is not None:
                        novos_ing[ing_n] = r.novo_ingrediente
        else:
            bloqueia("sem_ingrediente", "Escolha o ingrediente ou crie um novo.")

    # ----- compatibilidade de unidade: nunca converte massa em volume
    if (
        r.controle in BASE_INFERIDA_OBRIGATORIA
        and r.base is not None
        and r.base != BASE_INFERIDA_OBRIGATORIA[r.controle]
    ):
        quem = "massa (g)" if r.controle == "massa" else "volume (ml)"
        bloqueia(
            "unidade_incompativel",
            f"Este item é controlado por {quem}, mas o ingrediente é em {r.base}. Massa não vira volume.",
        )

    a.unidade_controle = r.controle
    a.conteudo_embalagem = float(r.conteudo) if r.conteudo is not None else None
    a.unidade_base = r.base
    a.custo_por = est.CUSTO_POR_CONTROLE.get(r.controle or "")
    a.unidades_validas = list(est.UNIDADES_POR_CONTROLE.get(r.controle or "", ()))

    # ----- quantidade
    if linha.quantidade is None or linha.quantidade <= 0:
        bloqueia("quantidade_invalida", "Informe uma quantidade maior que zero.")
    elif r.controle is not None:
        validas = est.UNIDADES_POR_CONTROLE[r.controle]
        unidade = linha.unidade or validas[0]
        if unidade not in validas:
            bloqueia("unidade_invalida", f"Use {' ou '.join(validas)} para este item.")
        elif r.controle != "embalagem" or (r.conteudo and r.conteudo > 0):
            r.quantidade_base = est.quantidade_em_base(
                r.controle, unidade, linha.quantidade, r.conteudo
            )
            a.quantidade_base = float(r.quantidade_base)

    # ----- validade
    if linha.validade is not None and linha.sem_validade:
        bloqueia(
            "validade_conflito", "Escolha uma data de validade ou “sem validade”, não os dois."
        )
    elif linha.validade is None and not linha.sem_validade:
        aviso(
            "validade_nao_informada", "Falta a validade. A entrada fica pendente até você informar."
        )
    elif linha.validade is not None and hoje is not None and linha.validade < hoje:
        aviso("validade_passada", "Esta validade já passou.")

    # ----- custo
    if linha.custo is not None:
        if linha.custo < 0:
            bloqueia("custo_invalido", "O custo não pode ser negativo.")
        elif r.controle is not None and (
            r.controle != "embalagem" or (r.conteudo and r.conteudo > 0)
        ):
            r.custo_base = est.custo_para_base(r.controle, linha.custo, r.conteudo)
            if r.quantidade_base is not None:
                r.valor = (r.quantidade_base * r.custo_base).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                )
                a.valor_total = float(r.valor)

    # ----- lote que já existe (mesmo item e código)
    if r.item is not None and linha.lote_codigo.strip():
        existente = db.scalar(
            select(Lote).where(Lote.item_id == r.item.id, Lote.codigo == linha.lote_codigo.strip())
        )
        if existente is not None:
            r.lote_existente = existente
            if existente.validade and linha.validade and existente.validade != linha.validade:
                bloqueia(
                    "lote_conflito", f"O lote {existente.codigo} já existe com outra validade."
                )

    a.pendencias = pend
    a.a_decidir = any(p.codigo in ("item_parecido", "ingrediente_parecido") for p in pend)
    a.incompleta = any(
        p.bloqueia and p.codigo not in ("item_parecido", "ingrediente_parecido") for p in pend
    )
    return a, r


BASE_INFERIDA = {"massa": "g", "volume": "ml"}
BASE_INFERIDA_OBRIGATORIA = {"massa": "g", "volume": "ml"}


# ---------------------------------------------------------------- lançamento


def _proxima_sequencia(db, prefixo: str) -> int:
    codigos = db.scalars(select(Lote.codigo).where(Lote.codigo.like(f"{prefixo}%")))
    usados = [int(c[len(prefixo) :]) for c in codigos if c[len(prefixo) :].isdigit()]
    return (max(usados) if usados else 0) + 1


def _decidir_distintos(db, ctx: Contexto, tipo: str, novo_id: UUID, outros) -> None:
    for outro in outros:
        menor, maior = est.par_ordenado(novo_id, outro.id)
        db.add(
            ParecidoDistinto(
                tipo=tipo, id_menor=menor, id_maior=maior, usuario_id=ctx.principal.usuario_id
            )
        )


def lancar_entrada(ctx: Contexto, dados: EntradaIn, *, hoje: date) -> tuple[Entrada, bool]:
    """Grava a entrada inteira ou nada. Devolve (entrada, criada). A mesma chave devolve a mesma entrada."""
    db = ctx.db
    existente = db.scalar(select(Entrada).where(Entrada.chave_idempotencia == dados.chave))
    if existente is not None:
        return existente, False

    if dados.tipo != "sem_nota":
        raise ErroDeDominio("tipo_indisponivel", "Entrada com nota ainda não está disponível.")
    if dados.data > hoje:
        raise ErroDeDominio("data_futura", "A data da entrada não pode ser no futuro.")
    if dados.motivo == "outro" and not dados.motivo_detalhe.strip():
        raise ErroDeDominio("motivo_sem_detalhe", "Em “Outro”, diga o motivo.")
    local = db.scalar(select(Local).where(Local.id == dados.local_id, Local.ativo.is_(True)))
    if local is None:
        raise ErroDeDominio("local_inexistente", "Esse local não existe ou está inativo.")

    visao = est.carregar_visao(db)
    analises = analisar_linhas(db, visao, dados.linhas, hoje=hoje)
    com_problema = [
        {"posicao": a.posicao, "pendencias": [p.model_dump() for p in a.pendencias if p.bloqueia]}
        for a, _r in analises
        if any(p.bloqueia for p in a.pendencias)
    ]
    if com_problema:
        decidir = any(a.a_decidir for a, _r in analises)
        raise ErroDeDominio(
            "parecido_nao_decidido"
            if decidir
            and all(
                all(
                    p["codigo"] in ("item_parecido", "ingrediente_parecido")
                    for p in x["pendencias"]
                )
                for x in com_problema
            )
            else "linhas_com_pendencia",
            "Há linhas que ainda precisam de uma decisão ou de dados.",
            linhas=com_problema,
        )

    entrada = Entrada(
        data=dados.data,
        local_id=local.id,
        tipo="sem_nota",
        motivo=dados.motivo,
        motivo_detalhe=dados.motivo_detalhe.strip() or None,
        fornecedor=dados.fornecedor.strip() or None,
        observacao=dados.observacao.strip() or None,
        lancada_por=ctx.principal.usuario_id,  # type: ignore[arg-type]
        chave_idempotencia=dados.chave,
    )
    db.add(entrada)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise ErroDeDominio(
            "entrada_repetida", "Esta entrada já foi enviada.", status=409
        ) from None

    prefixo = rotulo_padrao_lote(dados.data.isoformat(), 0)[:-2]  # "E20261102-"
    sequencia = _proxima_sequencia(db, prefixo)
    ing_criados: dict[str, Ingrediente] = {}
    itens_criados: dict[tuple[str, str], ItemEstoque] = {}

    for (analise, r), linha in zip(analises, dados.linhas, strict=True):
        item = r.item
        if item is None:
            assert r.novo_item is not None
            chave_item = (r.novo_item["nome_n"], r.novo_item["marca_n"])
            item = itens_criados.get(chave_item)
        if item is None:
            ing = r.ingrediente
            if ing is None:
                assert r.novo_ingrediente is not None
                ing = ing_criados.get(r.novo_ingrediente["nome_n"])
                if ing is None:
                    ing = Ingrediente(
                        nome=r.novo_ingrediente["nome"],
                        nome_normalizado=r.novo_ingrediente["nome_n"],
                        unidade_base=r.novo_ingrediente["base"],
                    )
                    db.add(ing)
                    db.flush()
                    ing_criados[r.novo_ingrediente["nome_n"]] = ing
                    # "Criar novo" cria o ingrediente; não afirma que são diferentes. O par continua apontado
                    # na tela Ingredientes até alguém juntar ou marcar "São diferentes" (marcar_distintos).
            item = ItemEstoque(
                ingrediente_id=ing.id,
                nome=r.novo_item["nome"],
                nome_normalizado=r.novo_item["nome_n"],
                marca=r.novo_item["marca"],
                marca_normalizada=r.novo_item["marca_n"],
                unidade_controle=r.novo_item["controle"],
                conteudo_embalagem=r.novo_item["conteudo"]
                if r.novo_item["controle"] == "embalagem"
                else None,
            )
            db.add(item)
            db.flush()
            itens_criados[chave_item] = item
            _decidir_distintos(db, ctx, "item", item.id, r.parecidos_item)

        codigo = linha.lote_codigo.strip()
        lote = r.lote_existente
        if lote is None and codigo:
            lote = db.scalar(select(Lote).where(Lote.item_id == item.id, Lote.codigo == codigo))
        if lote is None:
            if not codigo:
                codigo = rotulo_padrao_lote(dados.data.isoformat(), sequencia)
                sequencia += 1
            lote = Lote(
                item_id=item.id,
                local_id=local.id,
                codigo=codigo,
                validade=linha.validade,
                sem_validade=linha.sem_validade,
                custo_unidade_base=r.custo_base,
            )
            db.add(lote)
            db.flush()
        else:
            if lote.validade is None and not lote.sem_validade:
                lote.validade, lote.sem_validade = linha.validade, linha.sem_validade
            if lote.custo_unidade_base is None and r.custo_base is not None:
                lote.custo_unidade_base = r.custo_base

        assert r.quantidade_base is not None
        movimento = Movimento(
            tipo="entrada",
            item_id=item.id,
            lote_id=lote.id,
            quantidade_base=r.quantidade_base,
            motivo=dados.motivo,
            entrada_id=entrada.id,
            usuario_id=ctx.principal.usuario_id,  # type: ignore[arg-type]
        )
        db.add(movimento)
        db.flush()
        unidade = linha.unidade or est.UNIDADES_POR_CONTROLE[item.unidade_controle][0]
        db.add(
            EntradaLinha(
                entrada_id=entrada.id,
                posicao=analise.posicao,
                item_id=item.id,
                lote_id=lote.id,
                movimento_id=movimento.id,
                quantidade=linha.quantidade,
                unidade=unidade,  # type: ignore[arg-type]
                quantidade_base=r.quantidade_base,
                custo_informado=linha.custo,
                custo_por=est.CUSTO_POR_CONTROLE[item.unidade_controle]
                if linha.custo is not None
                else None,
                valor_total=r.valor,
            )
        )
    db.flush()
    return entrada, True


# ---------------------------------------------------------------- leitura


def listar_entradas(db, filtro: str) -> list[dict]:
    pendentes = est.pendentes_ids(db)
    agregados = {
        entrada_id: (n, soma, com_valor)
        for entrada_id, n, soma, com_valor in db.execute(
            select(
                EntradaLinha.entrada_id,
                func.count(),
                func.sum(EntradaLinha.valor_total),
                func.count(EntradaLinha.valor_total),
            ).group_by(EntradaLinha.entrada_id)
        )
    }
    saida = []
    for e in db.scalars(select(Entrada).order_by(Entrada.data.desc(), Entrada.criada_em.desc())):
        pendente = e.id in pendentes
        if filtro == "com_nota" and e.tipo != "com_nota":
            continue
        if filtro == "sem_nota" and e.tipo != "sem_nota":
            continue
        if filtro == "pendentes" and not pendente:
            continue
        n, soma, com_valor = agregados.get(e.id, (0, None, 0))
        saida.append(
            {
                "id": e.id,
                "data": e.data,
                "tipo": e.tipo,
                "motivo": e.motivo,
                "motivo_detalhe": e.motivo_detalhe,
                "fornecedor": e.fornecedor,
                "itens": int(n),
                "valor": float(soma) if soma is not None else None,
                "valor_parcial": bool(com_valor) and com_valor < n,
                "situacao": "pendente" if pendente else "completa",
            }
        )
    return saida

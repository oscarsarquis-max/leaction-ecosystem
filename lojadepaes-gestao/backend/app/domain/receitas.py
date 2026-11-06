"""Receita técnica: linhas, % do padeiro, custo calculado e versão publicada.

Conversões: só kg↔g e l↔ml. Unidade só quando o ingrediente é em unidade.
Massa e volume não se convertem. Custo desconhecido fica desconhecido, nunca zero.
O custo de um preparo da casa é o da versão publicada, por unidade base.
"""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.contexto import Contexto
from app.domain.errors import ErroDeDominio
from app.domain.estoque import Visao, carregar_visao
from app.models.estoque import Ingrediente
from app.models.produtos import Produto, Receita, ReceitaLinha, ReceitaVersao

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


def _conferir_ciclo(db: Session, origem: UUID, usados: set[UUID]) -> None:
    vistos: set[UUID] = set()
    pilha = list(usados)
    while pilha:
        alvo = pilha.pop()
        if alvo == origem:
            raise ErroDeDominio(
                "ciclo_receita",
                "Esta receita usa um preparo que, direta ou indiretamente, usa ela mesma.",
            )
        if alvo in vistos:
            continue
        vistos.add(alvo)
        receita = db.scalar(select(Receita).where(Receita.produto_id == alvo))
        if receita is None:
            continue
        pilha.extend(_componentes(db, receita.id))


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
    for bruta in versao.linhas:
        ing = db.get(Ingrediente, UUID(str(bruta["ingrediente_id"])))
        if ing is None:
            visitando.discard(ingrediente.produto_id)
            return None
        custo = custo_por_base(db, visao, ing, visitando)
        if custo is None:
            visitando.discard(ingrediente.produto_id)
            return None
        try:
            na_base = para_base(Decimal(str(bruta["quantidade"])), str(bruta["unidade"]), ing.unidade_base)
        except ErroDeDominio:
            visitando.discard(ingrediente.produto_id)
            return None
        total += na_base * custo
    visitando.discard(ingrediente.produto_id)
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
        ing = ingredientes.get(linha.ingrediente_id) if linha.ingrediente_id else None
        if ing is None or ing.categoria != "Farinhas":
            continue
        if not compativel(linha.unidade, "g"):
            continue
        farinha += para_base(linha.quantidade, linha.unidade, "g")
    saida_linhas = []
    conhecidos: list[Decimal] = []
    faltam = 0
    massa = _ZERO
    for linha in linhas:
        ing = ingredientes.get(linha.ingrediente_id) if linha.ingrediente_id else None
        custo = None
        percentual = None
        if ing is not None and compativel(linha.unidade, "g"):
            em_gramas = para_base(linha.quantidade, linha.unidade, "g")
            massa += em_gramas
            if farinha > 0:
                percentual = em_gramas / farinha * _CEM
        if ing is not None:
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
    return {
        "linhas": saida_linhas,
        "total_massa_g": _num(massa) if massa > 0 else None,
        "custo_total": _num(total),
        "custo_parcial": parcial,
        "linhas_sem_custo": faltam,
        "custo_por_unidade": _num(por_unidade),
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


def _ficha(db: Session, visao: Visao, produto: Produto, receita: Receita) -> dict:
    linhas = _linhas_de(db, receita.id)
    conta = _calcular(db, visao, receita, linhas)
    publicada = _versao_publicada(db, receita.id)
    tem_ingrediente = any(not item["a_decidir"] for item in conta["linhas"]) or bool(conta["linhas"])
    return {
        "id": str(receita.id),
        "produto_id": str(produto.id),
        "produto": produto.nome,
        "situacao": receita.situacao,
        "versao": receita.versao,
        "rendimento_quantidade": _num(receita.rendimento_quantidade),
        "rendimento_unidade": receita.rendimento_unidade,
        "rendimento": _rotulo_rendimento(receita.rendimento_quantidade, receita.rendimento_unidade),
        "peso_unidade_g": _num(receita.peso_unidade_g),
        "perda_percentual": _num(receita.perda_percentual),
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
    }


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
) -> dict:
    db = ctx.db
    _produto, receita = _receita_do_produto(db, produto_id)
    if perda_percentual < 0 or perda_percentual >= 100:
        raise ErroDeDominio("perda_invalida", "A perda fica entre 0 e menos de 100%.")
    if (rendimento_quantidade is None) != (rendimento_unidade is None):
        raise ErroDeDominio("rendimento_incompleto", "Informe a quantidade e a unidade do rendimento.")
    if rendimento_quantidade is not None and rendimento_quantidade <= 0:
        raise ErroDeDominio("rendimento_invalido", "O rendimento precisa ser maior que zero.")
    if peso_unidade_g is not None and peso_unidade_g <= 0:
        raise ErroDeDominio("peso_invalido", "O peso da unidade precisa ser maior que zero.")
    if rendimento_unidade is not None and rendimento_unidade not in UNIDADES:
        raise ErroDeDominio("unidade_invalida", "A unidade do rendimento é g, kg, ml, l ou un.")

    anteriores = {
        (str(linha.ingrediente_id) if linha.ingrediente_id else (linha.texto or "").strip().lower()): linha
        for linha in _linhas_de(db, receita.id)
    }
    preparadas: list[tuple] = []
    usados: set[UUID] = set()
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
            if ing.produto_id is not None:
                usados.add(ing.produto_id)
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
        preparadas.append((ing, texto, quantidade, unidade, obs, origem, faixa_min, faixa_max))

    _conferir_ciclo(db, produto_id, usados)
    _abrir_rascunho(receita)
    for antiga in _linhas_de(db, receita.id):
        db.delete(antiga)
    db.flush()
    for ordem, (ing, texto, quantidade, unidade, obs, origem, faixa_min, faixa_max) in enumerate(preparadas, start=1):
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
            )
        )
    receita.rendimento_quantidade = rendimento_quantidade
    receita.rendimento_unidade = rendimento_unidade
    receita.peso_unidade_g = peso_unidade_g
    receita.perda_percentual = perda_percentual
    receita.modo_fazer = [passo.strip() for passo in modo_fazer if passo and passo.strip()]
    db.flush()
    return detalhe(db, produto_id)


def publicar(ctx: Contexto, produto_id: UUID) -> dict:
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
    if receita.rendimento_quantidade is None or not receita.rendimento_unidade:
        raise ErroDeDominio("rendimento_vazio", "Informe o rendimento antes de publicar.")
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

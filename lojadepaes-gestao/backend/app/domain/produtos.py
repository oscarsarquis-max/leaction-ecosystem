"""Produtos da padaria: produzido (com receita) ou comprado (com item). O componente vira ingrediente.

Nada daqui lê ou grava a Loja. O produto só sai da Gestão quando o Oscar mandar, num ciclo futuro.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domain.busca import LIMIAR_PARECIDO, _semelhanca_de_nomes
from app.domain.contexto import Contexto
from app.domain.errors import ErroDeDominio
from app.domain.estoque import ATENCAO, EM_DIA, FALTA, Etapa, Visao, carregar_visao
from app.domain.normalizacao import normalizar
from app.models.estoque import CATEGORIAS_INGREDIENTE, Ingrediente, ItemEstoque
from app.models.organizacao import Organizacao
from app.models.produtos import Familia, Produto, Receita, ReceitaVersao

CATEGORIA_PREPARO = "Preparos da casa"
_FUSO_PADARIA = ZoneInfo("America/Sao_Paulo")
SUGESTOES_FAMILIA = (
    "Pães",
    "Bolos",
    "Doces",
    "Coberturas e recheios",
    "Massas",
    "Revenda",
)


def _limpar(nome: str, vazio: str) -> tuple[str, str]:
    nome = " ".join((nome or "").split())
    nome_n = normalizar(nome)
    if not nome_n:
        raise ErroDeDominio("nome_vazio", vazio)
    return nome, nome_n


def _org(db: Session) -> Organizacao:
    org = db.scalar(select(Organizacao))
    if org is None:
        raise ErroDeDominio("sem_organizacao", "Escolha a organização.", status=403)
    return org


def listar_familias(db: Session) -> dict:
    familias = list(db.scalars(select(Familia).order_by(Familia.nome)))
    org = _org(db)
    existentes = {f.nome_normalizado for f in familias}
    sugestoes: list[str] = []
    if not org.familias_sugestoes_dispensadas:
        sugestoes = [n for n in SUGESTOES_FAMILIA if normalizar(n) not in existentes]
    return {
        "familias": [saida_familia(f) for f in familias],
        "sugestoes": sugestoes,
    }


def criar_familia(ctx: Contexto, nome: str) -> Familia:
    db = ctx.db
    nome, nome_n = _limpar(nome, "Dê um nome à família.")
    if len(nome) > 80:
        raise ErroDeDominio("nome_longo", "O nome da família tem no máximo 80 letras.")
    igual = db.scalar(select(Familia).where(Familia.nome_normalizado == nome_n))
    if igual is not None:
        return igual
    familia = Familia(nome=nome, nome_normalizado=nome_n)
    db.add(familia)
    db.flush()
    return familia


def dispensar_sugestoes(ctx: Contexto) -> None:
    _org(ctx.db).familias_sugestoes_dispensadas = True
    ctx.db.flush()


def apagar_familia(ctx: Contexto, familia_id: UUID) -> None:
    db = ctx.db
    familia = db.get(Familia, familia_id)
    if familia is None:
        raise ErroDeDominio("familia_inexistente", "Essa família não existe.", status=404)
    em_uso = db.scalar(select(func.count()).select_from(Produto).where(Produto.familia_id == familia.id))
    if em_uso:
        raise ErroDeDominio(
            "familia_em_uso",
            f"“{familia.nome}” tem produtos. Mude a família deles antes de apagar.",
        )
    db.delete(familia)
    db.flush()


def saida_familia(f: Familia) -> dict:
    return {"id": str(f.id), "nome": f.nome}


def _unidade_componente(valor: str | None) -> str:
    """A unidade base do preparo é escolhida. O padrão é grama, não a unidade de venda."""
    if valor is None:
        return "g"
    if valor not in ("g", "ml", "un"):
        raise ErroDeDominio(
            "unidade_invalida",
            "A unidade base do preparo é grama, mililitro ou unidade.",
        )
    return valor


def _parecidos(db: Session, nome: str, ignorar: UUID | None = None) -> list[Produto]:
    achados = []
    for produto in db.scalars(select(Produto).where(Produto.ativo.is_(True))):
        if produto.id == ignorar or produto.nome_normalizado == normalizar(nome):
            continue
        if _semelhanca_de_nomes(nome, produto.nome) >= LIMIAR_PARECIDO:
            achados.append(produto)
    achados.sort(key=lambda p: p.nome.lower())
    return achados


def _resumo(p: Produto) -> dict:
    return {"id": str(p.id), "nome": p.nome}


def _conferir_usos(venda: bool, componente: bool) -> None:
    if not venda and not componente:
        raise ErroDeDominio("uso_vazio", "Marque Venda, Componente, ou os dois.")


def _conferir_familia(db: Session, familia_id: UUID | None) -> None:
    if familia_id is not None and db.get(Familia, familia_id) is None:
        raise ErroDeDominio("familia_inexistente", "Essa família não existe.", status=404)


def _conferir_item(db: Session, item_id: UUID | None) -> ItemEstoque | None:
    if item_id is None:
        return None
    item = db.get(ItemEstoque, item_id)
    if item is None or not item.ativo:
        raise ErroDeDominio("item_inexistente", "Esse item de estoque não existe.", status=404)
    return item


def _garantir_receita(db: Session, produto: Produto) -> Receita | None:
    if produto.modalidade != "produzido":
        return None
    receita = db.scalar(select(Receita).where(Receita.produto_id == produto.id))
    if receita is None:
        receita = Receita(produto_id=produto.id, situacao="rascunho")
        db.add(receita)
        db.flush()
    return receita


def _sincronizar_componente(
    ctx: Contexto,
    produto: Produto,
    unidade_base: str | None = None,
    *,
    aplicar_unidade: bool = False,
) -> Ingrediente | None:
    """Ligado: cria ou religa o ingrediente. Desligado: nunca apaga; inativa se não houver saldo."""
    db = ctx.db
    ing = db.scalar(select(Ingrediente).where(Ingrediente.produto_id == produto.id))
    if not produto.uso_componente or not produto.ativo:
        if ing is not None and carregar_visao(db).saldo_do_ingrediente(ing.id) == 0:
            ing.ativo = False
            db.flush()
        return ing
    base = _unidade_componente(unidade_base) if aplicar_unidade else None
    if CATEGORIA_PREPARO not in CATEGORIAS_INGREDIENTE:
        raise ErroDeDominio("categoria_invalida", "A categoria do preparo não está disponível.")
    if ing is None:
        choque = db.scalar(select(Ingrediente).where(Ingrediente.nome_normalizado == produto.nome_normalizado))
        if choque is not None:
            raise ErroDeDominio(
                "ingrediente_ja_existe",
                f"Já existe o ingrediente “{choque.nome}”. Escolha outro nome para o componente.",
                status=409,
                existente={"id": str(choque.id), "nome": choque.nome},
            )
        ing = Ingrediente(
            nome=produto.nome,
            nome_normalizado=produto.nome_normalizado,
            unidade_base=base or "g",
            categoria=CATEGORIA_PREPARO,
            apelidos=[],
            produto_id=produto.id,
            ativo=True,
        )
        db.add(ing)
    else:
        outro = db.scalar(
            select(Ingrediente).where(
                Ingrediente.nome_normalizado == produto.nome_normalizado,
                Ingrediente.id != ing.id,
            )
        )
        if outro is not None:
            raise ErroDeDominio(
                "ingrediente_ja_existe",
                f"Já existe o ingrediente “{outro.nome}”. O componente não pode usar esse nome.",
                status=409,
            )
        ing.nome = produto.nome
        ing.nome_normalizado = produto.nome_normalizado
        ing.categoria = CATEGORIA_PREPARO
        ing.ativo = True
        if base is not None and base != ing.unidade_base:
            if carregar_visao(db).saldo_do_ingrediente(ing.id) > 0:
                raise ErroDeDominio(
                    "unidade_com_saldo",
                    "Este preparo já tem saldo. A unidade base não muda.",
                )
            ing.unidade_base = base
    db.flush()
    return ing


def criar_produto(
    ctx: Contexto,
    *,
    nome: str,
    modalidade: str,
    uso_venda: bool,
    uso_componente: bool,
    familia_id: UUID | None,
    unidade_venda: str,
    item_estoque_id: UUID | None = None,
    codigo: str | None = None,
    peso_unidade_g: Decimal | None = None,
    observacao: str | None = None,
    confirmado_inexistente: bool = False,
    unidade_base: str | None = None,
) -> Produto:
    db = ctx.db
    nome, nome_n = _limpar(nome, "Dê um nome ao produto.")
    if modalidade not in ("produzido", "comprado"):
        raise ErroDeDominio("modalidade_invalida", "Escolha Produzido ou Comprado.")
    if unidade_venda not in ("un", "kg"):
        raise ErroDeDominio("unidade_invalida", "A unidade de venda é unidade ou quilo.")
    _conferir_usos(uso_venda, uso_componente)
    _conferir_familia(db, familia_id)
    if modalidade == "produzido":
        item_estoque_id = None
    _conferir_item(db, item_estoque_id)
    if peso_unidade_g is not None and peso_unidade_g <= 0:
        raise ErroDeDominio("peso_invalido", "O peso da unidade precisa ser maior que zero.")
    igual = db.scalar(select(Produto).where(Produto.nome_normalizado == nome_n))
    if igual is not None:
        raise ErroDeDominio(
            "ja_existe",
            f"Já existe o produto “{igual.nome}”.",
            status=409,
            existente=_resumo(igual),
        )
    parecidos = _parecidos(db, nome)
    if parecidos and not confirmado_inexistente:
        raise ErroDeDominio(
            "produto_parecido",
            "Já existe algo parecido com isso. Use o existente ou confirme que não existe.",
            status=409,
            parecidos=[_resumo(p) for p in parecidos[:3]],
        )
    produto = Produto(
        nome=nome,
        nome_normalizado=nome_n,
        codigo=(codigo or "").strip() or None,
        modalidade=modalidade,
        uso_venda=uso_venda,
        uso_componente=uso_componente,
        familia_id=familia_id,
        unidade_venda=unidade_venda,
        peso_unidade_g=peso_unidade_g,
        observacao=(observacao or "").strip() or None,
        item_estoque_id=item_estoque_id,
        ativo=True,
    )
    if confirmado_inexistente:
        produto.atualizado_em = datetime.now(UTC)
    db.add(produto)
    db.flush()
    _garantir_receita(db, produto)
    _sincronizar_componente(ctx, produto, unidade_base, aplicar_unidade=True)
    return produto


def editar_produto(
    ctx: Contexto,
    produto_id: UUID,
    *,
    nome: str | None = None,
    uso_venda: bool | None = None,
    uso_componente: bool | None = None,
    familia_id: UUID | None = None,
    familia_informada: bool = False,
    unidade_venda: str | None = None,
    item_estoque_id: UUID | None = None,
    item_informado: bool = False,
    codigo: str | None = None,
    codigo_informado: bool = False,
    peso_unidade_g: Decimal | None = None,
    peso_informado: bool = False,
    observacao: str | None = None,
    observacao_informada: bool = False,
    confirmado_inexistente: bool = False,
    unidade_base: str | None = None,
    unidade_base_informada: bool = False,
) -> Produto:
    db = ctx.db
    produto = db.get(Produto, produto_id)
    if produto is None or not produto.ativo:
        raise ErroDeDominio("produto_inexistente", "Esse produto não existe.", status=404)
    if nome is not None:
        nome, nome_n = _limpar(nome, "Dê um nome ao produto.")
        igual = db.scalar(
            select(Produto).where(Produto.nome_normalizado == nome_n, Produto.id != produto.id)
        )
        if igual is not None:
            raise ErroDeDominio(
                "ja_existe", f"Já existe o produto “{igual.nome}”.", status=409, existente=_resumo(igual)
            )
        if nome_n != produto.nome_normalizado:
            parecidos = _parecidos(db, nome, ignorar=produto.id)
            if parecidos and not confirmado_inexistente:
                raise ErroDeDominio(
                    "produto_parecido",
                    "Já existe algo parecido com isso. Use o existente ou confirme que não existe.",
                    status=409,
                    parecidos=[_resumo(p) for p in parecidos[:3]],
                )
        produto.nome = nome
        produto.nome_normalizado = nome_n
    venda = produto.uso_venda if uso_venda is None else uso_venda
    componente = produto.uso_componente if uso_componente is None else uso_componente
    _conferir_usos(venda, componente)
    produto.uso_venda = venda
    produto.uso_componente = componente
    if familia_informada:
        _conferir_familia(db, familia_id)
        produto.familia_id = familia_id
    if unidade_venda is not None:
        if unidade_venda not in ("un", "kg"):
            raise ErroDeDominio("unidade_invalida", "A unidade de venda é unidade ou quilo.")
        produto.unidade_venda = unidade_venda
    if produto.modalidade == "comprado" and item_informado:
        _conferir_item(db, item_estoque_id)
        produto.item_estoque_id = item_estoque_id
    if codigo_informado:
        produto.codigo = (codigo or "").strip() or None
    if peso_informado:
        if peso_unidade_g is not None and peso_unidade_g <= 0:
            raise ErroDeDominio("peso_invalido", "O peso da unidade precisa ser maior que zero.")
        produto.peso_unidade_g = peso_unidade_g
    if observacao_informada:
        produto.observacao = (observacao or "").strip() or None
    produto.atualizado_em = datetime.now(UTC)
    db.flush()
    _garantir_receita(db, produto)
    _sincronizar_componente(ctx, produto, unidade_base, aplicar_unidade=unidade_base_informada)
    return produto


def inativar_produto(ctx: Contexto, produto_id: UUID) -> Produto:
    produto = ctx.db.get(Produto, produto_id)
    if produto is None or not produto.ativo:
        raise ErroDeDominio("produto_inexistente", "Esse produto não existe.", status=404)
    produto.ativo = False
    produto.atualizado_em = datetime.now(UTC)
    ctx.db.flush()
    _sincronizar_componente(ctx, produto)
    return produto


def _publicados(db: Session) -> set[UUID]:
    return set(
        db.scalars(select(Receita.produto_id).join(ReceitaVersao, ReceitaVersao.receita_id == Receita.id))
    )


def _selos(produto: Produto, publicados: set[UUID]) -> list[str]:
    selos = []
    if produto.modalidade == "produzido" and produto.id not in publicados:
        selos.append("sem_receita")
    if produto.modalidade == "comprado" and produto.item_estoque_id is None:
        selos.append("sem_item")
    return selos


def _linha(produto: Produto, familias: dict[UUID, Familia], publicados: set[UUID]) -> dict:
    familia = familias.get(produto.familia_id) if produto.familia_id else None
    selos = _selos(produto, publicados)
    return {
        "id": str(produto.id),
        "nome": produto.nome,
        "codigo": produto.codigo,
        "modalidade": produto.modalidade,
        "uso_venda": produto.uso_venda,
        "uso_componente": produto.uso_componente,
        "familia_id": str(familia.id) if familia else None,
        "familia": familia.nome if familia else None,
        "unidade_venda": produto.unidade_venda,
        "ativo": produto.ativo,
        "selos": selos,
        "pendente": bool(selos),
        "foto_url": produto.foto_url,
    }


def listar_produtos(db: Session, filtro: str, familia_id: UUID | None) -> dict:
    produtos = list(db.scalars(select(Produto).where(Produto.ativo.is_(True)).order_by(Produto.nome)))
    familias = {f.id: f for f in db.scalars(select(Familia))}
    publicados = _publicados(db)
    linhas = [_linha(p, familias, publicados) for p in produtos]
    if familia_id is not None:
        linhas = [x for x in linhas if x["familia_id"] == str(familia_id)]
    if filtro == "produzidos":
        linhas = [x for x in linhas if x["modalidade"] == "produzido"]
    elif filtro == "comprados":
        linhas = [x for x in linhas if x["modalidade"] == "comprado"]
    elif filtro == "componentes":
        linhas = [x for x in linhas if x["uso_componente"]]
    elif filtro == "pendentes":
        linhas = [x for x in linhas if x["pendente"]]
    contagem: dict[str, int] = {}
    for f in familias.values():
        contagem[str(f.id)] = sum(1 for p in produtos if p.familia_id == f.id)
    return {
        "filtro": filtro,
        "produtos": linhas,
        "familias": [
            {"id": str(f.id), "nome": f.nome, "total": contagem.get(str(f.id), 0)}
            for f in sorted(familias.values(), key=lambda f: f.nome.lower())
        ],
    }


def _item_do_produto(visao: Visao, produto: Produto) -> dict | None:
    if produto.item_estoque_id is None:
        return None
    item = visao.itens.get(produto.item_estoque_id)
    if item is None:
        return None
    lotes = [lv for lv in visao.lotes if lv.item.id == item.id and lv.saldo > 0]
    saldo = sum((lv.saldo for lv in lotes), Decimal(0))
    com_custo = [lv for lv in lotes if lv.lote.custo_unidade_base is not None and lv.saldo > 0]
    custo = None
    if com_custo and saldo > 0:
        total = sum((lv.saldo * (lv.lote.custo_unidade_base or 0) for lv in com_custo), Decimal(0))
        base = sum((lv.saldo for lv in com_custo), Decimal(0))
        custo = float(total / base) if base else None
    ing = visao.ingredientes.get(item.ingrediente_id)
    return {
        "id": str(item.id),
        "nome": item.nome,
        "marca": item.marca,
        "saldo": float(saldo),
        "unidade_base": ing.unidade_base if ing else "g",
        "custo_medio_base": custo,
        "ingrediente_id": str(item.ingrediente_id),
        "ingrediente": ing.nome if ing else "",
    }


def detalhe_produto(db: Session, produto_id: UUID) -> dict:
    produto = db.get(Produto, produto_id)
    if produto is None or not produto.ativo:
        raise ErroDeDominio("produto_inexistente", "Esse produto não existe.", status=404)
    familias = {f.id: f for f in db.scalars(select(Familia))}
    receita = db.scalar(select(Receita).where(Receita.produto_id == produto.id))
    ing = db.scalar(select(Ingrediente).where(Ingrediente.produto_id == produto.id))
    visao = carregar_visao(db)
    corpo = _linha(produto, familias, _publicados(db))
    from app.domain.receitas import resumo_no_produto, usados_em

    corpo.update(
        {
            "observacao": produto.observacao,
            "peso_unidade_g": float(produto.peso_unidade_g) if produto.peso_unidade_g is not None else None,
            "unidade_base": ing.unidade_base if ing else None,
            "receita": None if receita is None else resumo_no_produto(db, receita),
            "ingrediente_id": str(ing.id) if ing else None,
            "ingrediente": ing.nome if ing else None,
            "item": _item_do_produto(visao, produto) if produto.modalidade == "comprado" else None,
            "usado_em": usados_em(db, produto),
            "importado_em": _dia_importado(produto),
        }
    )
    return corpo


def _dia_importado(produto: Produto) -> str | None:
    if produto.origem_loja_id is None or produto.criado_em is None:
        return None
    instante = produto.criado_em
    if instante.tzinfo is None:
        instante = instante.replace(tzinfo=UTC)
    return instante.astimezone(_FUSO_PADARIA).date().isoformat()


def buscar_itens(db: Session, q: str) -> list[dict]:
    visao = carregar_visao(db)
    termo = normalizar(q)
    saida = []
    for item in visao.itens.values():
        if not item.ativo:
            continue
        if termo and termo not in normalizar(item.nome) and termo not in normalizar(item.marca):
            continue
        ing = visao.ingredientes.get(item.ingrediente_id)
        saldo = sum((lv.saldo for lv in visao.lotes if lv.item.id == item.id), Decimal(0))
        saida.append(
            {
                "id": str(item.id),
                "nome": item.nome,
                "marca": item.marca,
                "ingrediente_id": str(item.ingrediente_id),
                "ingrediente": ing.nome if ing else "",
                "saldo": float(saldo),
                "unidade_base": ing.unidade_base if ing else "g",
            }
        )
    saida.sort(key=lambda x: x["nome"].lower())
    return saida[:30]


def etapa_produtos(db: Session) -> Etapa:
    produtos = list(db.scalars(select(Produto).where(Produto.ativo.is_(True))))
    if not produtos:
        return Etapa("produtos", "Produtos", "O que eu vendo?", FALTA, "nenhum produto", "/produtos")
    publicados = _publicados(db)
    pendentes = sum(1 for p in produtos if _selos(p, publicados))
    if pendentes:
        texto = "1 pendente" if pendentes == 1 else f"{pendentes} pendentes"
        return Etapa(
            "produtos",
            "Produtos",
            "O que eu vendo?",
            ATENCAO,
            texto,
            "/produtos?filtro=pendentes",
        )
    texto = "1 produto" if len(produtos) == 1 else f"{len(produtos)} produtos"
    return Etapa("produtos", "Produtos", "O que eu vendo?", EM_DIA, texto, "/produtos")

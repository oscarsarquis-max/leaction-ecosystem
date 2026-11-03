"""Ingredientes: lista, detalhe, criação, edição, ajuste de saldo e junção; e os locais."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select

from app.domain import estoque as est
from app.domain.busca import ingredientes_parecidos
from app.domain.contexto import Contexto
from app.domain.errors import ErroDeDominio
from app.domain.normalizacao import normalizar
from app.models.estoque import (
    CATEGORIA_PADRAO,
    CATEGORIAS_INGREDIENTE,
    Ingrediente,
    Local,
    Lote,
    Movimento,
    ParecidoDistinto,
)

MAX_APELIDOS = 20
MAX_PARECIDOS = 3


def _ingrediente(db, ingrediente_id: UUID) -> Ingrediente:
    ing = db.scalar(select(Ingrediente).where(Ingrediente.id == ingrediente_id))
    if ing is None:
        raise ErroDeDominio("ingrediente_inexistente", "Esse ingrediente não existe.", status=404)
    return ing


# ---------------------------------------------------------------- leitura


def linha_do_ingrediente(visao: est.Visao, ing: Ingrediente, hoje: date) -> dict:
    lotes = visao.lotes_do_ingrediente(ing.id)
    saldo = visao.saldo_do_ingrediente(ing.id)
    primeiro = est.vence_primeiro(lotes)
    limite = hoje + timedelta(days=est.JANELA_VALIDADE_DIAS)
    return {
        "id": ing.id,
        "nome": ing.nome,
        "unidade_base": ing.unidade_base,
        "categoria": ing.categoria,
        "apelidos": list(ing.apelidos or []),
        "ativo": ing.ativo,
        "saldo": float(saldo),
        "itens": len(visao.itens_do_ingrediente(ing.id)),
        "lotes": sum(1 for lv in lotes if lv.saldo > 0),
        "vence_primeiro": primeiro,
        "vence_em_7_dias": primeiro is not None and primeiro <= limite,
    }


def listar_ingredientes(db, hoje: date, filtro: str, categoria: str | None = None) -> dict:
    visao = est.carregar_visao(db)
    linhas = [linha_do_ingrediente(visao, i, hoje) for i in visao.ingredientes.values() if i.ativo]
    linhas.sort(key=lambda x: x["nome"].lower())
    por_categoria: dict[str, int] = {}
    for x in linhas:
        por_categoria[x["categoria"]] = por_categoria.get(x["categoria"], 0) + 1
    categorias = [
        {"nome": c, "total": por_categoria[c]} for c in CATEGORIAS_INGREDIENTE if c in por_categoria
    ]
    if categoria:
        linhas = [x for x in linhas if x["categoria"] == categoria]
    if filtro == "com_saldo":
        linhas = [x for x in linhas if x["saldo"] > 0]
    elif filtro == "sem_saldo":
        linhas = [x for x in linhas if x["saldo"] <= 0]
    elif filtro == "vence7":
        linhas = [x for x in linhas if x["vence_em_7_dias"]]
    pares = [
        {
            "a": {"id": a.id, "nome": a.nome},
            "b": {"id": b.id, "nome": b.nome},
            "unidade_base": a.unidade_base,
        }
        for a, b in est.pares_parecidos(visao)
    ]
    return {"ingredientes": linhas, "pares_parecidos": pares, "categorias": categorias}


def detalhe_ingrediente(db, ingrediente_id: UUID, hoje: date) -> dict:
    visao = est.carregar_visao(db)
    ing = visao.ingredientes.get(ingrediente_id)
    if ing is None:
        raise ErroDeDominio("ingrediente_inexistente", "Esse ingrediente não existe.", status=404)
    lotes = visao.lotes_do_ingrediente(ing.id)
    custo, com_custo, com_saldo = est.custo_medio_base(lotes)
    locais = {lc.id: lc.nome for lc in db.scalars(select(Local))}
    itens = visao.itens_do_ingrediente(ing.id)
    saldo_por_item = {
        i.id: sum((lv.saldo for lv in lotes if lv.item.id == i.id), est.ZERO) for i in itens
    }

    consulta = (
        select(Movimento)
        .where(
            (Movimento.item_id.in_([i.id for i in itens]))
            | (Movimento.ingrediente_destino_id == ing.id)
            | (Movimento.ingrediente_origem_id == ing.id)
        )
        .order_by(Movimento.criado_em.desc())
        .limit(60)
    )
    codigos = {lv.lote.id: lv.lote.codigo for lv in visao.lotes}
    movimentos = [
        {
            "id": m.id,
            "tipo": m.tipo,
            "quando": m.criado_em,
            "quantidade_base": float(m.quantidade_base),
            "motivo": m.motivo,
            "lote": codigos.get(m.lote_id) if m.lote_id else None,
            "item": visao.itens[m.item_id].nome if m.item_id in visao.itens else None,
            "de": visao.ingredientes[m.ingrediente_origem_id].nome
            if m.ingrediente_origem_id in visao.ingredientes
            else None,
            "para": visao.ingredientes[m.ingrediente_destino_id].nome
            if m.ingrediente_destino_id in visao.ingredientes
            else None,
        }
        for m in db.scalars(consulta)
    ]
    vence7 = hoje + timedelta(days=est.JANELA_VALIDADE_DIAS)
    return {
        **linha_do_ingrediente(visao, ing, hoje),
        "custo_medio_base": float(custo) if custo is not None else None,
        "lotes_com_custo": com_custo,
        "lotes_com_saldo": com_saldo,
        "itens_detalhe": [
            {
                "id": i.id,
                "nome": i.nome,
                "marca": i.marca,
                "unidade_controle": i.unidade_controle,
                "conteudo_embalagem": float(i.conteudo_embalagem)
                if i.conteudo_embalagem is not None
                else None,
                "saldo": float(saldo_por_item[i.id]),
            }
            for i in sorted(itens, key=lambda x: x.nome.lower())
        ],
        "lotes_detalhe": [
            {
                "id": lv.lote.id,
                "codigo": lv.lote.codigo,
                "item": lv.item.nome,
                "marca": lv.item.marca,
                "local": locais.get(lv.lote.local_id, "—"),
                "validade": lv.lote.validade,
                "sem_validade": lv.lote.sem_validade,
                "saldo": float(lv.saldo),
                "custo_unidade_base": float(lv.lote.custo_unidade_base)
                if lv.lote.custo_unidade_base is not None
                else None,
                "vence_em_7_dias": lv.saldo > 0
                and lv.lote.validade is not None
                and lv.lote.validade <= vence7,
            }
            for lv in sorted(
                lotes,
                key=lambda x: (x.saldo <= 0, x.lote.validade is None, x.lote.validade or date.max),
            )
        ],
        "movimentos": movimentos,
        "juntado_em_id": ing.juntado_em_id,
    }


# ---------------------------------------------------------------- escrita


def _limpar_apelidos(apelidos: list[str] | None, nome: str) -> list[str]:
    """Apelidos sem vazios, sem repetição e sem o próprio nome (comparados sem acento/caixa)."""
    vistos = {normalizar(nome)}
    saida: list[str] = []
    for bruto in apelidos or []:
        texto = " ".join((bruto or "").split())
        chave = normalizar(texto)
        if not chave or chave in vistos:
            continue
        if len(texto) > 120:
            raise ErroDeDominio("apelido_longo", "Cada apelido tem no máximo 120 letras.")
        vistos.add(chave)
        saida.append(texto)
    if len(saida) > MAX_APELIDOS:
        raise ErroDeDominio("apelidos_demais", f"Use no máximo {MAX_APELIDOS} apelidos.")
    return saida


def _conferir_categoria(categoria: str) -> str:
    if categoria not in CATEGORIAS_INGREDIENTE:
        raise ErroDeDominio("categoria_invalida", "Escolha uma categoria da lista.")
    return categoria


def _resumo(i: Ingrediente) -> dict:
    return {
        "id": str(i.id),
        "nome": i.nome,
        "categoria": i.categoria,
        "unidade_base": i.unidade_base,
    }


def criar_ingrediente(
    ctx: Contexto,
    nome: str,
    unidade_base: str,
    *,
    categoria: str = CATEGORIA_PADRAO,
    apelidos: list[str] | None = None,
    confirmado_inexistente: bool = False,
) -> Ingrediente:
    """Cadastra um ingrediente SÓ depois de ter certeza de que ele não existe.

    - mesmo nome (normalizado): 409 `ja_existe`, devolvendo o existente;
    - algum parecido: 409 `ingrediente_parecido` até vir `confirmado_inexistente`, que grava quem
      confirmou e quando.
    """
    db = ctx.db
    nome = " ".join(nome.split())
    nome_n = normalizar(nome)
    if not nome_n:
        raise ErroDeDominio("nome_vazio", "Dê um nome ao ingrediente.")
    categoria = _conferir_categoria(categoria)
    apelidos = _limpar_apelidos(apelidos, nome)
    igual = db.scalar(select(Ingrediente).where(Ingrediente.nome_normalizado == nome_n))
    if igual is not None:
        raise ErroDeDominio(
            "ja_existe",
            f"Já existe o ingrediente “{igual.nome}”."
            + ("" if igual.ativo else " Ele foi juntado a outro; use o que ficou."),
            status=409,
            existente=_resumo(igual),
        )
    visao = est.carregar_visao(db)
    parecidos = ingredientes_parecidos(visao.ingredientes.values(), nome, apelidos)
    if parecidos and not confirmado_inexistente:
        raise ErroDeDominio(
            "ingrediente_parecido",
            "Já existe algo parecido com isso. Use o existente ou confirme que não existe.",
            status=409,
            parecidos=[_resumo(p) for p, _pontos in parecidos[:MAX_PARECIDOS]],
        )
    ing = Ingrediente(
        nome=nome,
        nome_normalizado=nome_n,
        unidade_base=unidade_base,
        categoria=categoria,
        apelidos=apelidos,
    )
    if confirmado_inexistente:
        ing.confirmado_inexistente_por = ctx.principal.usuario_id
        ing.confirmado_inexistente_em = datetime.now(UTC)
    db.add(ing)
    db.flush()
    # Confirmar "não existe" cria o ingrediente; não afirma que são diferentes. O par continua apontado
    # na tela Ingredientes até alguém juntar ou marcar "São diferentes" (marcar_distintos).
    return ing


def editar_ingrediente(
    ctx: Contexto,
    ingrediente_id: UUID,
    nome: str | None,
    unidade_base: str | None,
    categoria: str | None = None,
    apelidos: list[str] | None = None,
) -> Ingrediente:
    db = ctx.db
    ing = _ingrediente(db, ingrediente_id)
    if nome is not None:
        nome = " ".join(nome.split())
        nome_n = normalizar(nome)
        if not nome_n:
            raise ErroDeDominio("nome_vazio", "Dê um nome ao ingrediente.")
        outro = db.scalar(
            select(Ingrediente).where(
                Ingrediente.nome_normalizado == nome_n, Ingrediente.id != ing.id
            )
        )
        if outro is not None:
            raise ErroDeDominio(
                "ja_existe",
                f"Já existe o ingrediente “{outro.nome}”.",
                status=409,
                existente=_resumo(outro),
            )
        ing.nome, ing.nome_normalizado = nome, nome_n
    if categoria is not None:
        ing.categoria = _conferir_categoria(categoria)
    if apelidos is not None:
        ing.apelidos = _limpar_apelidos(apelidos, ing.nome)
    elif nome is not None:
        ing.apelidos = _limpar_apelidos(ing.apelidos, ing.nome)
    if unidade_base is not None and unidade_base != ing.unidade_base:
        visao = est.carregar_visao(db)
        if visao.itens_do_ingrediente(ing.id):
            raise ErroDeDominio(
                "unidade_base_travada",
                "Este ingrediente já tem itens. A unidade base não pode mudar (massa não vira volume).",
            )
        ing.unidade_base = unidade_base
    ing.atualizado_em = datetime.now(UTC)
    db.flush()
    return ing


def marcar_distintos(ctx: Contexto, a_id: UUID, b_id: UUID) -> None:
    db = ctx.db
    a, b = _ingrediente(db, a_id), _ingrediente(db, b_id)
    menor, maior = est.par_ordenado(a.id, b.id)
    ja = db.scalar(
        select(ParecidoDistinto).where(
            ParecidoDistinto.tipo == "ingrediente",
            ParecidoDistinto.id_menor == menor,
            ParecidoDistinto.id_maior == maior,
        )
    )
    if ja is None:
        db.add(
            ParecidoDistinto(
                tipo="ingrediente",
                id_menor=menor,
                id_maior=maior,
                usuario_id=ctx.principal.usuario_id,
            )
        )  # type: ignore[arg-type]
        db.flush()


def ajustar_saldo(
    ctx: Contexto, ingrediente_id: UUID, lote_id: UUID, saldo_contado_base: Decimal, motivo: str
) -> Movimento:
    """Leva o saldo do lote ao valor contado, por um movimento de ajuste (nunca editando o passado)."""
    db = ctx.db
    ing = _ingrediente(db, ingrediente_id)
    motivo = motivo.strip()
    if len(motivo) < 3:
        raise ErroDeDominio("motivo_obrigatorio", "Diga o motivo do ajuste.")
    if saldo_contado_base < 0:
        raise ErroDeDominio("saldo_negativo", "O saldo contado não pode ser negativo.")
    lote = db.scalar(select(Lote).where(Lote.id == lote_id).with_for_update())
    if lote is None:
        raise ErroDeDominio("lote_inexistente", "Esse lote não existe.", status=404)
    visao = est.carregar_visao(db)
    item = visao.itens[lote.item_id]
    if item.ingrediente_id != ing.id:
        raise ErroDeDominio("lote_de_outro_ingrediente", "Esse lote não é deste ingrediente.")
    atual = next(lv.saldo for lv in visao.lotes if lv.lote.id == lote.id)
    delta = saldo_contado_base - atual
    if delta == 0:
        raise ErroDeDominio("sem_diferenca", "O saldo contado é igual ao atual. Nada a ajustar.")
    movimento = Movimento(
        tipo="ajuste",
        item_id=item.id,
        lote_id=lote.id,
        quantidade_base=delta,
        motivo=motivo,
        usuario_id=ctx.principal.usuario_id,  # type: ignore[arg-type]
    )
    db.add(movimento)
    db.flush()
    return movimento


def juntar(ctx: Contexto, mantem_id: UUID, remove_id: UUID, *, motivo: str = "") -> Ingrediente:
    """Move os itens do ingrediente `remove` para o `mantem` e inativa o vazio. Nada é apagado."""
    db = ctx.db
    if mantem_id == remove_id:
        raise ErroDeDominio("mesmo_ingrediente", "Escolha dois ingredientes diferentes.")
    mantem, remove = _ingrediente(db, mantem_id), _ingrediente(db, remove_id)
    if not mantem.ativo or not remove.ativo:
        raise ErroDeDominio("ingrediente_inativo", "Só dá para juntar ingredientes ativos.")
    if mantem.unidade_base != remove.unidade_base:
        raise ErroDeDominio(
            "unidade_incompativel",
            f"“{mantem.nome}” é em {mantem.unidade_base} e “{remove.nome}” é em {remove.unidade_base}. Não dá para juntar: massa não vira volume.",
        )
    visao = est.carregar_visao(db)
    nota = motivo.strip() or f"Junção: “{remove.nome}” passou para “{mantem.nome}”"
    itens = visao.itens_do_ingrediente(remove.id)
    for item in itens:
        item.ingrediente_id = mantem.id
        db.add(
            Movimento(
                tipo="juncao",
                item_id=item.id,
                lote_id=None,
                quantidade_base=Decimal(0),
                motivo=nota,
                ingrediente_origem_id=remove.id,
                ingrediente_destino_id=mantem.id,
                usuario_id=ctx.principal.usuario_id,  # type: ignore[arg-type]
            )
        )
    if not itens:
        db.add(
            Movimento(
                tipo="juncao",
                item_id=None,
                lote_id=None,
                quantidade_base=Decimal(0),
                motivo=nota,
                ingrediente_origem_id=remove.id,
                ingrediente_destino_id=mantem.id,
                usuario_id=ctx.principal.usuario_id,  # type: ignore[arg-type]
            )
        )
    remove.ativo = False
    remove.juntado_em_id = mantem.id
    db.flush()
    return mantem


# ---------------------------------------------------------------- locais


def criar_local(ctx: Contexto, nome: str, *, padrao: bool = False) -> Local:
    db = ctx.db
    nome = " ".join(nome.split())
    nome_n = normalizar(nome)
    if not nome_n:
        raise ErroDeDominio("nome_vazio", "Dê um nome ao local.")
    if db.scalar(select(Local).where(Local.nome_normalizado == nome_n)) is not None:
        raise ErroDeDominio("local_ja_existe", "Já existe um local com esse nome.", status=409)
    primeiro = db.scalar(select(Local).where(Local.padrao.is_(True))) is None
    local = Local(nome=nome, nome_normalizado=nome_n, padrao=False)
    db.add(local)
    db.flush()
    if padrao or primeiro:
        definir_padrao(ctx, local.id)
    return local


def definir_padrao(ctx: Contexto, local_id: UUID) -> Local:
    db = ctx.db
    local = db.scalar(select(Local).where(Local.id == local_id))
    if local is None or not local.ativo:
        raise ErroDeDominio(
            "local_inexistente", "Esse local não existe ou está inativo.", status=404
        )
    for outro in db.scalars(select(Local).where(Local.padrao.is_(True), Local.id != local.id)):
        outro.padrao = False
    db.flush()  # solta o índice único antes de marcar o novo
    local.padrao = True
    db.flush()
    return local


def editar_local(ctx: Contexto, local_id: UUID, nome: str | None, ativo: bool | None) -> Local:
    db = ctx.db
    local = db.scalar(select(Local).where(Local.id == local_id))
    if local is None:
        raise ErroDeDominio("local_inexistente", "Esse local não existe.", status=404)
    if nome is not None:
        nome = " ".join(nome.split())
        nome_n = normalizar(nome)
        if not nome_n:
            raise ErroDeDominio("nome_vazio", "Dê um nome ao local.")
        outro = db.scalar(
            select(Local).where(Local.nome_normalizado == nome_n, Local.id != local.id)
        )
        if outro is not None:
            raise ErroDeDominio("local_ja_existe", "Já existe um local com esse nome.", status=409)
        local.nome, local.nome_normalizado = nome, nome_n
    if ativo is not None and ativo != local.ativo:
        if not ativo and local.padrao:
            raise ErroDeDominio(
                "local_padrao", "Escolha outro local como padrão antes de inativar este."
            )
        local.ativo = ativo
    db.flush()
    return local

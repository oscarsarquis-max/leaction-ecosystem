"""Ordens de produção: programação, demanda da Loja, escala da receita e comanda.

A quantidade impressa sai do rendimento do GESTAO-013. A foto gravada na impressão
não é recalculada numa reimpressão.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta
from decimal import ROUND_HALF_UP, Decimal
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domain.errors import ErroDeDominio
from app.domain.perdas import massa_necessaria, peso_cru_g, resolver_receita
from app.domain.receitas import compativel, folhas_publicadas, para_base
from app.loja_reader.demanda import LinhaVinculo, consultar_demanda_vinculo
from app.models.estoque import Ingrediente
from app.models.producao import Fornada, OrdemProducao, Programacao
from app.models.produtos import Produto, Receita, ReceitaLinha, ReceitaVersao

HORIZONTE_DIAS = 14
_GRAMA = Decimal("1")
_DECIMO = Decimal("0.1")
_MIL = Decimal(1000)
_FUNCOES = ("massa", "recheio", "cobertura", "finalizacao")
_ROTULO_FUNCAO = {
    "massa": "Massa",
    "recheio": "Recheio",
    "cobertura": "Cobertura",
    "finalizacao": "Finalização",
}
_ROTULO_ORIGEM = {"programada": "Programada", "loja": "Loja", "avulsa": "Avulsa"}
_ROTULO_SITUACAO = {
    "planejada": "Planejada",
    "impressa": "Impressa",
    "em_producao": "Em produção",
    "concluida": "Concluída",
    "cancelada": "Cancelada",
}
SEMENTES = (
    ("Manhã 05:00", time(5, 0), 1),
    ("Tarde 13:00", time(13, 0), 2),
)


def texto_quantidade(gramas: Decimal) -> str:
    """Abaixo de 20 g, uma casa. De 20 g para cima, gramas inteiros. Acima de 1 kg, também em kg."""
    if gramas < 20:
        valor = gramas.quantize(_DECIMO, rounding=ROUND_HALF_UP)
        texto = f"{valor:.1f}".replace(".", ",") + " g"
    else:
        valor = gramas.quantize(_GRAMA, rounding=ROUND_HALF_UP)
        texto = f"{int(valor):,}".replace(",", ".") + " g"
    if valor > _MIL:
        kg = (valor / _MIL).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)
        kg_txt = f"{kg:.3f}".replace(".", ",")
        texto = f"{texto} ({kg_txt} kg)"
    return texto


def texto_diferenca(valor: int) -> str:
    if valor > 0:
        return f"+{valor}"
    return f"−{abs(valor)}"


def semear_fornadas(db: Session, organizacao_id: UUID) -> None:
    existe = db.scalar(select(Fornada.id).where(Fornada.organizacao_id == organizacao_id))
    if existe is not None:
        return
    for nome, horario, ordem in SEMENTES:
        db.add(
            Fornada(
                organizacao_id=organizacao_id,
                nome=nome,
                horario=horario,
                ordem=ordem,
                ativa=True,
            )
        )
    db.flush()


def _fornadas(db: Session, *, so_ativas: bool = False) -> list[Fornada]:
    consulta = select(Fornada).order_by(Fornada.ordem, Fornada.nome)
    if so_ativas:
        consulta = consulta.where(Fornada.ativa.is_(True))
    return list(db.scalars(consulta))


def _fornada_ou_404(db: Session, fornada_id: UUID) -> Fornada:
    fornada = db.get(Fornada, fornada_id)
    if fornada is None:
        raise ErroDeDominio("fornada_inexistente", "Essa fornada não existe.", status=404)
    return fornada


def _produto_ou_404(db: Session, produto_id: UUID) -> Produto:
    produto = db.get(Produto, produto_id)
    if produto is None or not produto.ativo:
        raise ErroDeDominio("produto_inexistente", "Esse produto não existe.", status=404)
    return produto


def _hora(valor: time) -> str:
    return valor.strftime("%H:%M")


def _parse_hora(texto: str) -> time:
    try:
        partes = (texto or "").strip().split(":")
        valor = time(int(partes[0]), int(partes[1]))
    except (ValueError, AttributeError, IndexError):
        raise ErroDeDominio("horario_invalido", "O horário é no formato 05:00.") from None
    return valor


def fornada_dict(fornada: Fornada) -> dict:
    return {
        "id": str(fornada.id),
        "nome": fornada.nome,
        "horario": _hora(fornada.horario),
        "ordem": fornada.ordem,
        "ativa": fornada.ativa,
    }


def listar_fornadas(db: Session) -> list[dict]:
    return [fornada_dict(item) for item in _fornadas(db)]


def salvar_fornada(db: Session, organizacao_id: UUID, dados: dict, fornada_id: UUID | None = None) -> dict:
    nome = (dados.get("nome") or "").strip()
    if not nome:
        raise ErroDeDominio("nome_vazio", "Dê um nome à fornada.")
    horario = _parse_hora(dados.get("horario") or "")
    ordem = int(dados.get("ordem") or 0)
    if ordem <= 0:
        raise ErroDeDominio("ordem_invalida", "A ordem da fornada começa em 1.")
    if fornada_id is None:
        fornada = Fornada(organizacao_id=organizacao_id, nome=nome, horario=horario, ordem=ordem, ativa=bool(dados.get("ativa", True)))
        db.add(fornada)
    else:
        fornada = _fornada_ou_404(db, fornada_id)
        fornada.nome = nome
        fornada.horario = horario
        fornada.ordem = ordem
        fornada.ativa = bool(dados.get("ativa", True))
    db.flush()
    return fornada_dict(fornada)


def _dias(brutos) -> list[int]:
    if not isinstance(brutos, list) or not brutos:
        raise ErroDeDominio("dias_vazios", "Escolha ao menos um dia da semana.")
    dias = []
    for item in brutos:
        try:
            dia = int(item)
        except (TypeError, ValueError):
            raise ErroDeDominio("dia_invalido", "O dia da semana não foi reconhecido.") from None
        if dia < 0 or dia > 6 or dia in dias:
            raise ErroDeDominio("dia_invalido", "O dia da semana vai de segunda a domingo, sem repetir.")
        dias.append(dia)
    return dias


def _ids_fornada(db: Session, brutos) -> list[str]:
    if not isinstance(brutos, list) or not brutos:
        raise ErroDeDominio("fornadas_vazias", "Escolha ao menos uma fornada.")
    ids = []
    for item in brutos:
        try:
            chave = UUID(str(item))
        except (TypeError, ValueError):
            raise ErroDeDominio("fornada_invalida", "A fornada escolhida não existe.") from None
        if _fornada_ou_404(db, chave).id and str(chave) not in ids:
            ids.append(str(chave))
    return ids


def _programacao_dict(db: Session, item: Programacao) -> dict:
    produto = db.get(Produto, item.produto_id)
    return {
        "id": str(item.id),
        "produto_id": str(item.produto_id),
        "produto": produto.nome if produto else "",
        "quantidade_por_fornada": item.quantidade_por_fornada,
        "fornada_ids": [str(x) for x in item.fornada_ids or []],
        "dias_semana": [int(x) for x in item.dias_semana or []],
        "inicio": item.inicio.isoformat() if item.inicio else None,
        "fim": item.fim.isoformat() if item.fim else None,
        "ativa": item.ativa,
    }


def listar_programacoes(db: Session) -> list[dict]:
    itens = db.scalars(select(Programacao).order_by(Programacao.ativa.desc(), Programacao.id)).all()
    return [_programacao_dict(db, item) for item in itens]


def _data_ou_none(valor) -> date | None:
    if not valor:
        return None
    if isinstance(valor, date):
        return valor
    try:
        return date.fromisoformat(str(valor))
    except ValueError:
        raise ErroDeDominio("data_invalida", "A data de vigência não foi reconhecida.") from None


def salvar_programacao(
    db: Session, organizacao_id: UUID, dados: dict, *, hoje: date, programacao_id: UUID | None = None
) -> dict:
    produto = _produto_ou_404(db, UUID(str(dados["produto_id"])))
    if produto.modalidade != "produzido":
        raise ErroDeDominio("produto_comprado", "A programação é de um produto produzido.")
    quantidade = int(dados.get("quantidade_por_fornada") or 0)
    if quantidade <= 0:
        raise ErroDeDominio("quantidade_invalida", "A quantidade por fornada precisa ser maior que zero.")
    inicio = _data_ou_none(dados.get("inicio"))
    fim = _data_ou_none(dados.get("fim"))
    if inicio and fim and fim < inicio:
        raise ErroDeDominio("vigencia_invalida", "O fim da vigência é depois do início.")
    campos = dict(
        produto_id=produto.id,
        quantidade_por_fornada=quantidade,
        fornada_ids=_ids_fornada(db, dados.get("fornada_ids")),
        dias_semana=_dias(dados.get("dias_semana")),
        inicio=inicio,
        fim=fim,
        ativa=bool(dados.get("ativa", True)),
    )
    if programacao_id is None:
        item = Programacao(organizacao_id=organizacao_id, **campos)
        db.add(item)
    else:
        item = db.get(Programacao, programacao_id)
        if item is None:
            raise ErroDeDominio("programacao_inexistente", "Essa programação não existe.", status=404)
        for chave, valor in campos.items():
            setattr(item, chave, valor)
    db.flush()
    garantir_ordens(db, organizacao_id, hoje=hoje)
    return _programacao_dict(db, item)


def _desejadas(db: Session, hoje: date, ate: date) -> dict[tuple, tuple[int, UUID]]:
    ativas = {item.id for item in _fornadas(db, so_ativas=True)}
    desejadas: dict[tuple, tuple[int, UUID]] = {}
    programacoes = db.scalars(select(Programacao).where(Programacao.ativa.is_(True))).all()
    for item in programacoes:
        inicio = item.inicio or hoje
        fim = item.fim or ate
        dia = max(hoje, inicio)
        limite = min(ate, fim)
        dias = {int(d) for d in item.dias_semana or []}
        while dia <= limite:
            if dia.weekday() in dias:
                for bruto in item.fornada_ids or []:
                    fornada_id = UUID(str(bruto))
                    if fornada_id not in ativas:
                        continue
                    desejadas[(dia, fornada_id, item.produto_id)] = (item.quantidade_por_fornada, item.id)
            dia += timedelta(days=1)
    return desejadas


def garantir_ordens(db: Session, organizacao_id: UUID, *, hoje: date, ate: date | None = None) -> int:
    """Cria e atualiza ordens programadas de hoje até `ate`. Idempotente. Não mexe em impressa."""
    semear_fornadas(db, organizacao_id)
    ate = ate or (hoje + timedelta(days=HORIZONTE_DIAS))
    desejadas = _desejadas(db, hoje, ate)
    existentes = list(
        db.scalars(
            select(OrdemProducao).where(
                OrdemProducao.origem == "programada",
                OrdemProducao.data >= hoje,
                OrdemProducao.data <= ate,
            )
        )
    )
    vistas = set()
    for ordem in existentes:
        chave = (ordem.data, ordem.fornada_id, ordem.produto_id)
        vistas.add(chave)
        if ordem.situacao != "planejada":
            continue
        if chave not in desejadas:
            db.delete(ordem)
            continue
        unidades, programacao_id = desejadas[chave]
        ordem.unidades = unidades
        ordem.programacao_id = programacao_id
    for (dia, fornada_id, produto_id), (unidades, programacao_id) in desejadas.items():
        if (dia, fornada_id, produto_id) in vistas:
            continue
        db.add(
            OrdemProducao(
                organizacao_id=organizacao_id,
                data=dia,
                fornada_id=fornada_id,
                produto_id=produto_id,
                unidades=unidades,
                origem="programada",
                programacao_id=programacao_id,
                situacao="planejada",
            )
        )
    db.flush()
    return len(desejadas)


def _versao(db: Session, receita_id: UUID) -> ReceitaVersao | None:
    return db.scalar(
        select(ReceitaVersao).where(ReceitaVersao.receita_id == receita_id).order_by(ReceitaVersao.versao.desc())
    )


def _sem_receita(db: Session, produto_id: UUID) -> bool:
    receita = db.scalar(select(Receita).where(Receita.produto_id == produto_id))
    if receita is None:
        return True
    return _versao(db, receita.id) is None


def _gramas(bruta: dict) -> Decimal | None:
    unidade = str(bruta.get("unidade") or "g")
    if not compativel(unidade, "g"):
        return None
    return para_base(Decimal(str(bruta["quantidade"])), unidade, "g")


def _linha_folha(nome: str, quantidade: Decimal, *, funcao: str = "massa", componente: bool = False, filhos=None) -> dict:
    return {
        "nome": nome,
        "funcao": funcao,
        "funcao_rotulo": _ROTULO_FUNCAO.get(funcao, "Massa"),
        "quantidade_g": format(quantidade, "f"),
        "texto": texto_quantidade(quantidade),
        "componente": componente,
        "filhos": filhos or [],
    }


def calcular_foto(db: Session, produto_id: UUID, unidades: int) -> dict:
    produto = db.get(Produto, produto_id)
    nome = produto.nome if produto else ""
    base = {
        "produto_id": str(produto_id),
        "produto": nome,
        "unidades": unidades,
        "sem_receita": False,
        "aviso": None,
        "peso_cru_g": None,
        "pecas": None,
        "massa_necessaria_g": None,
        "massa_receita_g": None,
        "fator": None,
        "processo_pct": None,
        "coccao_pct": None,
        "linhas": [],
        "modo_fazer": [],
    }
    receita = db.scalar(select(Receita).where(Receita.produto_id == produto_id))
    versao = _versao(db, receita.id) if receita else None
    if receita is None or versao is None:
        base["sem_receita"] = True
        base["aviso"] = "Sem receita publicada. A comanda sai sem os ingredientes."
        return base
    perdas = resolver_receita(db, receita, familia_id=produto.familia_id if produto else None, massa_total_g=None)
    proc = perdas["processo"]["percentual"]
    coc = perdas["coccao"]["percentual"]
    final = versao.peso_unidade_g if versao.peso_unidade_g is not None else receita.peso_unidade_g
    base["modo_fazer"] = list(versao.modo_fazer or [])
    base["processo_pct"] = proc
    base["coccao_pct"] = coc
    if final is None or proc is None or coc is None:
        base["aviso"] = "Falta o peso final."
        return base
    final_d = Decimal(str(final))
    proc_d = Decimal(str(proc))
    coc_d = Decimal(str(coc))
    massa = massa_necessaria(unidades, final_d, coc_d, proc_d)
    cru = peso_cru_g(final_d, coc_d)
    preparadas = []
    massa_receita = Decimal(0)
    for bruta in versao.linhas or []:
        gramas = _gramas(bruta)
        if gramas is None:
            continue
        massa_receita += gramas
        preparadas.append((bruta, gramas))
    if massa_receita <= 0:
        base["aviso"] = "A receita publicada não tem quantidade em gramas."
        base["massa_necessaria_g"] = int(massa)
        base["peso_cru_g"] = int(cru)
        base["pecas"] = f"Peças de {int(cru)} g"
        return base
    fator = massa / massa_receita
    vivas = {
        str(linha.ingrediente_id): (linha.funcao or "massa")
        for linha in db.scalars(select(ReceitaLinha).where(ReceitaLinha.receita_id == receita.id))
        if linha.ingrediente_id
    }
    linhas = []
    for bruta, gramas in preparadas:
        escalada = gramas * fator
        ing = db.get(Ingrediente, UUID(str(bruta["ingrediente_id"]))) if bruta.get("ingrediente_id") else None
        funcao = bruta.get("funcao") or (vivas.get(str(ing.id)) if ing else None) or "massa"
        if funcao not in _FUNCOES:
            funcao = "massa"
        if ing is not None and ing.produto_id is not None:
            filhos = [
                _linha_folha(folha["nome"], Decimal(str(folha["quantidade_g"])))
                for folha in folhas_publicadas(db, ing.produto_id, escalada)
            ]
            linhas.append(_linha_folha(ing.nome, escalada, funcao=funcao, componente=True, filhos=filhos))
        else:
            linhas.append(_linha_folha(ing.nome if ing else str(bruta.get("nome") or ""), escalada, funcao=funcao))
    base.update(
        {
            "peso_cru_g": int(cru),
            "pecas": f"Peças de {int(cru)} g",
            "massa_necessaria_g": int(massa),
            "massa_receita_g": format(massa_receita, "f"),
            "fator": format(fator, "f"),
            "linhas": linhas,
        }
    )
    return base


def somar_pesagem(fotos: list[dict]) -> list[dict]:
    """Soma a folha de cada ingrediente. O cabeçalho da massa-base não entra de novo."""
    totais: dict[str, Decimal] = {}
    ordem: list[str] = []
    for foto in fotos:
        if foto.get("sem_receita") or foto.get("aviso") == "Falta o peso final.":
            continue
        for linha in foto.get("linhas") or []:
            folhas = linha.get("filhos") if linha.get("componente") else [linha]
            for folha in folhas or []:
                nome = folha.get("nome") or ""
                if not nome:
                    continue
                if nome not in totais:
                    ordem.append(nome)
                    totais[nome] = Decimal(0)
                totais[nome] += Decimal(str(folha.get("quantidade_g") or 0))
    return [
        {"nome": nome, "quantidade_g": format(totais[nome], "f"), "texto": texto_quantidade(totais[nome])}
        for nome in ordem
    ]


def _ordem(db: Session, ordem_id: UUID) -> OrdemProducao:
    ordem = db.get(OrdemProducao, ordem_id)
    if ordem is None:
        raise ErroDeDominio("ordem_inexistente", "Essa ordem não existe.", status=404)
    return ordem


def criar_avulsa(db: Session, organizacao_id: UUID, dados: dict) -> dict:
    semear_fornadas(db, organizacao_id)
    produto = _produto_ou_404(db, UUID(str(dados["produto_id"])))
    fornada = _fornada_ou_404(db, UUID(str(dados["fornada_id"])))
    unidades = int(dados.get("unidades") or 0)
    if unidades <= 0:
        raise ErroDeDominio("quantidade_invalida", "As unidades precisam ser maiores que zero.")
    dia = _data_ou_none(dados.get("data"))
    if dia is None:
        raise ErroDeDominio("data_invalida", "Informe o dia da ordem.")
    existe = db.scalar(
        select(OrdemProducao.id).where(
            OrdemProducao.data == dia,
            OrdemProducao.fornada_id == fornada.id,
            OrdemProducao.produto_id == produto.id,
            OrdemProducao.origem == "avulsa",
        )
    )
    if existe is not None:
        raise ErroDeDominio("ordem_existente", "Já existe uma ordem avulsa deste produto nesta fornada.")
    ordem = OrdemProducao(
        organizacao_id=organizacao_id,
        data=dia,
        fornada_id=fornada.id,
        produto_id=produto.id,
        unidades=unidades,
        origem="avulsa",
        situacao="planejada",
        observacao=(dados.get("observacao") or "").strip() or None,
    )
    db.add(ordem)
    db.flush()
    return _ordem_dict(db, ordem)


def alterar_ordem(db: Session, ordem_id: UUID, dados: dict) -> dict:
    ordem = _ordem(db, ordem_id)
    if ordem.situacao != "planejada":
        raise ErroDeDominio("ordem_impressa", "Esta ordem já foi impressa. A comanda guardou as quantidades.")
    if "unidades" in dados and dados["unidades"] is not None:
        unidades = int(dados["unidades"])
        if unidades <= 0:
            raise ErroDeDominio("quantidade_invalida", "As unidades precisam ser maiores que zero.")
        ordem.unidades = unidades
    if dados.get("fornada_id"):
        ordem.fornada_id = _fornada_ou_404(db, UUID(str(dados["fornada_id"]))).id
    if "observacao" in dados:
        ordem.observacao = (dados.get("observacao") or "").strip() or None
    db.flush()
    return _ordem_dict(db, ordem)


def cancelar_ordem(db: Session, ordem_id: UUID) -> dict:
    ordem = _ordem(db, ordem_id)
    if ordem.situacao == "cancelada":
        return _ordem_dict(db, ordem)
    ordem.situacao = "cancelada"
    db.flush()
    return _ordem_dict(db, ordem)


def _ordem_dict(db: Session, ordem: OrdemProducao) -> dict:
    produto = db.get(Produto, ordem.produto_id)
    foto = ordem.foto if ordem.situacao != "planejada" and ordem.foto else None
    conta = foto or calcular_foto(db, ordem.produto_id, ordem.unidades)
    diferenca = ordem.demanda_diferenca
    return {
        "id": str(ordem.id),
        "data": ordem.data.isoformat(),
        "fornada_id": str(ordem.fornada_id),
        "produto_id": str(ordem.produto_id),
        "produto": produto.nome if produto else conta.get("produto") or "",
        "unidades": ordem.unidades,
        "origem": ordem.origem,
        "origem_rotulo": _ROTULO_ORIGEM.get(ordem.origem, ordem.origem),
        "situacao": ordem.situacao,
        "situacao_rotulo": _ROTULO_SITUACAO.get(ordem.situacao, ordem.situacao),
        "pecas": conta.get("pecas"),
        "massa_necessaria_g": conta.get("massa_necessaria_g"),
        "massa": texto_quantidade(Decimal(conta["massa_necessaria_g"])) if conta.get("massa_necessaria_g") else None,
        "sem_receita": bool(conta.get("sem_receita")),
        "aviso": conta.get("aviso"),
        "demanda_diferenca": diferenca,
        "diferenca_texto": texto_diferenca(diferenca) if diferenca else None,
        "observacao": ordem.observacao,
        "via": ordem.via,
        "comanda_numero": ordem.comanda_numero,
    }


def calendario(db: Session, organizacao_id: UUID, *, hoje: date, de: date, ate: date) -> dict:
    garantir_ordens(db, organizacao_id, hoje=hoje)
    ordens = list(
        db.scalars(
            select(OrdemProducao).where(
                OrdemProducao.data >= de,
                OrdemProducao.data <= ate,
                OrdemProducao.situacao != "cancelada",
            )
        )
    )
    return {
        "hoje": hoje.isoformat(),
        "de": de.isoformat(),
        "ate": ate.isoformat(),
        "fornadas": listar_fornadas(db),
        "ordens": [_ordem_dict(db, ordem) for ordem in ordens],
    }


def _produto_da_loja(db: Session, product_id: str | None, variant_id: str | None) -> Produto | None:
    if variant_id:
        achado = db.scalar(
            select(Produto).where(Produto.origem_loja_id == UUID(variant_id), Produto.ativo.is_(True))
        )
        if achado is not None:
            return achado
    if product_id:
        return db.scalar(
            select(Produto).where(Produto.origem_loja_id == UUID(product_id), Produto.ativo.is_(True))
        )
    return None


def _nome_loja(linha: LinhaVinculo) -> str:
    nome = linha.produto_ou_massa or "Item sem nome"
    if linha.variante_ou_forma:
        return f"{nome} · {linha.variante_ou_forma}"
    return nome


def trazer_loja(
    db: Session,
    loja: Session,
    organizacao_id: UUID,
    *,
    de: date,
    ate: date,
    fuso: str,
) -> dict:
    semear_fornadas(db, organizacao_id)
    ativas = _fornadas(db, so_ativas=True)
    if not ativas:
        raise ErroDeDominio("sem_fornada", "Cadastre uma fornada ativa antes de trazer os pedidos.")
    primeira = ativas[0]
    linhas = consultar_demanda_vinculo(loja, de=de, ate=ate, fuso=fuso)
    demandas: dict[tuple[date, UUID], dict] = {}
    sem_vinculo = []
    for linha in linhas:
        if linha.paes_fisicos <= 0:
            continue
        produto = _produto_da_loja(db, linha.product_id, linha.product_variant_id)
        if produto is None:
            sem_vinculo.append(
                {
                    "data": linha.fornada_data.isoformat(),
                    "nome": _nome_loja(linha),
                    "unidades": linha.paes_fisicos,
                    "pedidos": linha.pedido_ids,
                }
            )
            continue
        chave = (linha.fornada_data, produto.id)
        atual = demandas.setdefault(
            chave, {"unidades": 0, "pedidos": [], "produto_id": produto.id}
        )
        atual["unidades"] += linha.paes_fisicos
        for pedido in linha.pedido_ids:
            if pedido not in atual["pedidos"]:
                atual["pedidos"].append(pedido)
    existentes = list(
        db.scalars(
            select(OrdemProducao).where(
                OrdemProducao.origem == "loja",
                OrdemProducao.data >= de,
                OrdemProducao.data <= ate,
            )
        )
    )
    por_chave = {(ordem.data, ordem.produto_id): ordem for ordem in existentes}
    for chave, demanda in demandas.items():
        ordem = por_chave.get(chave)
        if ordem is None:
            db.add(
                OrdemProducao(
                    organizacao_id=organizacao_id,
                    data=chave[0],
                    fornada_id=primeira.id,
                    produto_id=demanda["produto_id"],
                    unidades=demanda["unidades"],
                    origem="loja",
                    situacao="planejada",
                    loja_pedido_ids=demanda["pedidos"],
                )
            )
            continue
        if ordem.situacao == "planejada":
            ordem.unidades = demanda["unidades"]
            ordem.loja_pedido_ids = demanda["pedidos"]
            ordem.demanda_diferenca = None
        elif ordem.situacao != "cancelada":
            diferenca = demanda["unidades"] - ordem.unidades
            ordem.demanda_diferenca = diferenca or None
            ordem.loja_pedido_ids = demanda["pedidos"]
    for chave, ordem in por_chave.items():
        if chave in demandas or ordem.situacao == "cancelada":
            continue
        if ordem.situacao == "planejada":
            db.delete(ordem)
        else:
            ordem.demanda_diferenca = -ordem.unidades
    db.flush()
    return {"sem_vinculo": sem_vinculo, "fornada_id": str(primeira.id)}


def _folha_da_ordem(db: Session, ordem: OrdemProducao, *, por: str, fuso: str, numero: int | None) -> dict:
    foto = ordem.foto or calcular_foto(db, ordem.produto_id, ordem.unidades)
    quando = None
    if ordem.impressa_em is not None:
        quando = ordem.impressa_em.astimezone(ZoneInfo(fuso)).strftime("%d/%m/%Y %H:%M")
    via = ordem.via or 0
    return {
        "ordem_id": str(ordem.id),
        "produto": foto.get("produto") or "",
        "unidades": ordem.unidades,
        "pecas": foto.get("pecas"),
        "massa": texto_quantidade(Decimal(foto["massa_necessaria_g"])) if foto.get("massa_necessaria_g") else None,
        "sem_receita": bool(foto.get("sem_receita")),
        "aviso": foto.get("aviso"),
        "linhas": foto.get("linhas") or [],
        "modo_fazer": foto.get("modo_fazer") or [],
        "observacao": ordem.observacao,
        "situacao": ordem.situacao,
        "via": via,
        "via_rotulo": f"{via}ª via" if via > 1 else None,
        "comanda_numero": ordem.comanda_numero or numero,
        "impressa_em": quando,
        "impressa_por": ordem.impressa_por or (por if via else None),
    }


def _ordens_da_fornada(db: Session, dia: date, fornada_id: UUID) -> list[OrdemProducao]:
    return list(
        db.scalars(
            select(OrdemProducao).where(
                OrdemProducao.data == dia,
                OrdemProducao.fornada_id == fornada_id,
                OrdemProducao.situacao != "cancelada",
            )
        )
    )


def montar_comanda(
    db: Session, *, dia: date, fornada_id: UUID, por: str, fuso: str
) -> dict:
    fornada = _fornada_ou_404(db, fornada_id)
    ordens = _ordens_da_fornada(db, dia, fornada_id)
    if not ordens:
        raise ErroDeDominio("comanda_vazia", "Não há ordem nesta fornada.")
    numero = next((ordem.comanda_numero for ordem in ordens if ordem.comanda_numero), None)
    blocos = [_folha_da_ordem(db, ordem, por=por, fuso=fuso, numero=numero) for ordem in ordens]
    fotos = [ordem.foto or calcular_foto(db, ordem.produto_id, ordem.unidades) for ordem in ordens]
    vias = [bloco["via"] for bloco in blocos]
    via = min(vias) if vias else 0
    return {
        "data": dia.isoformat(),
        "fornada": fornada_dict(fornada),
        "numero": numero,
        "via": via,
        "via_rotulo": f"{via}ª via" if via > 1 else None,
        "impressa_em": next((bloco["impressa_em"] for bloco in blocos if bloco["impressa_em"]), None),
        "impressa_por": next((bloco["impressa_por"] for bloco in blocos if bloco["impressa_por"]), None),
        "produtos": blocos,
        "pesagem": somar_pesagem(fotos),
    }


def imprimir_comanda(
    db: Session, organizacao_id: UUID, *, dia: date, fornada_id: UUID, por: str, fuso: str
) -> dict:
    _fornada_ou_404(db, fornada_id)
    ordens = _ordens_da_fornada(db, dia, fornada_id)
    if not ordens:
        raise ErroDeDominio("comanda_vazia", "Não há ordem nesta fornada.")
    agora = datetime.now(UTC)
    novas = [ordem for ordem in ordens if not ordem.via]
    numero = next((ordem.comanda_numero for ordem in ordens if ordem.comanda_numero), None)
    if novas and numero is None:
        ultimo = db.scalar(select(func.max(OrdemProducao.comanda_numero))) or 0
        numero = int(ultimo) + 1
    for ordem in ordens:
        if not ordem.via:
            ordem.foto = calcular_foto(db, ordem.produto_id, ordem.unidades)
            ordem.via = 1
            ordem.situacao = "impressa"
            ordem.impressa_em = agora
            ordem.impressa_por = por
            ordem.comanda_numero = numero
        else:
            ordem.via += 1
    db.flush()
    return montar_comanda(db, dia=dia, fornada_id=fornada_id, por=por, fuso=fuso)


def resumo_hoje(db: Session, hoje: date) -> list[dict]:
    ordens = list(
        db.scalars(
            select(OrdemProducao).where(OrdemProducao.data == hoje, OrdemProducao.situacao != "cancelada")
        )
    )
    saida = []
    for fornada in _fornadas(db, so_ativas=True):
        delas = [ordem for ordem in ordens if ordem.fornada_id == fornada.id]
        saida.append(
            {
                "fornada_id": str(fornada.id),
                "fornada": fornada.nome,
                "horario": _hora(fornada.horario),
                "unidades": sum(ordem.unidades for ordem in delas),
                "ordens": len(delas),
                "pedido_mudou": any(ordem.demanda_diferenca for ordem in delas),
            }
        )
    return saida


def etapa_producao(db: Session, hoje: date):
    from app.domain.estoque import ATENCAO, EM_DIA, FALTA, Etapa

    ordens = list(
        db.scalars(
            select(OrdemProducao).where(OrdemProducao.data == hoje, OrdemProducao.situacao != "cancelada")
        )
    )
    if not ordens:
        return Etapa("producao", "Produção", "O que faço hoje?", FALTA, "nada planejado hoje", "/producao")
    if any(ordem.demanda_diferenca for ordem in ordens):
        return Etapa("producao", "Produção", "O que faço hoje?", ATENCAO, "pedido mudou", "/producao")
    if any(_sem_receita(db, ordem.produto_id) for ordem in ordens):
        return Etapa("producao", "Produção", "O que faço hoje?", ATENCAO, "sem receita", "/producao")
    return Etapa(
        "producao",
        "Produção",
        "O que faço hoje?",
        EM_DIA,
        f"{len(ordens)} {'ordem' if len(ordens) == 1 else 'ordens'}",
        "/producao",
    )

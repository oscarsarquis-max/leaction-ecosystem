"""Sugestão de receita. O padeiro decide; o Gigio não publica e não cria ingrediente."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domain.busca import sugerir
from app.domain.contexto import Contexto
from app.domain.errors import ErroDeDominio
from app.domain.estoque import carregar_visao
from app.domain.gigio.bedrock import BedrockGateway
from app.domain.gigio.fake import FakeGateway
from app.domain.gigio.gateway import ChatRequest, ChatTurn, GatewayError, GigioGateway
from app.domain.gigio.padroes import ativos as padroes_ativos
from app.domain.gigio.policy import MAX_DESCRICAO, limpar_descricao, parece_injecao
from app.domain.gigio.settings import disponivel, load_gigio_model_settings
from app.domain.normalizacao import normalizar
from app.domain.perdas import resolver_receita, texto_fixo
from app.domain.receitas import (
    UNIDADES,
    compativel,
    farinha_contida,
    folhas_publicadas,
    para_base,
    salvar,
)
from app.domain.verificacoes import (
    apertar_faixa,
    aplicar_substituicao,
    calibrar_confianca,
    casa_com_padrao,
    e_farinha,
    e_fermento,
    essencial,
    faixa_da_familia,
    gramas_do_percentual,
    na_descricao,
    pede_fermento_natural,
    percentual_dos_gramas,
    sal_classico,
    verificar,
)
from app.models.estoque import CatalogoIngrediente, Ingrediente
from app.models.gigio import GigioSugestao
from app.models.produtos import Familia, Produto, Receita

LIMITE_DIA = 30
FUSO = ZoneInfo("America/Sao_Paulo")
_GATEWAY: GigioGateway | None = None

FERRAMENTA = {
    "name": "sugerir_receita",
    "description": "Entrega a sugestão em porcentagem do padeiro, com faixa quando a medida é incerta.",
    "input_schema": {
        "type": "object",
        "properties": {
            "linhas": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "ingrediente": {"type": "string"},
                        "quantidade_g": {"type": "number"},
                        "percentual": {"type": "number"},
                        "faixa_min": {"type": "number"},
                        "faixa_max": {"type": "number"},
                        "confianca": {"type": "string"},
                        "motivo": {"type": "string"},
                        "funcao": {"type": "string"},
                    },
                    "required": ["ingrediente", "quantidade_g", "percentual", "confianca", "motivo"],
                },
            },
            "substituicoes": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "ingrediente": {"type": "string"},
                        "percentual": {"type": "number"},
                        "motivo": {"type": "string"},
                        "confianca": {"type": "string"},
                    },
                    "required": ["ingrediente", "percentual", "motivo"],
                },
            },
            "rendimento_g": {"type": "number"},
            "perda_pct": {"type": "number"},
            "modo_de_fazer": {"type": "array", "items": {"type": "string"}},
            "observacoes": {"type": "string"},
        },
        "required": ["linhas"],
    },
}

PERSONA = """
Você é o Gigio, assistente da padaria dentro da Gestão. Você sugere. O padeiro decide.
Fale em português brasileiro, curto e prático. Sem exagero técnico.
Com massa-base, trabalhe em porcentagem do padeiro sobre a farinha contida. O servidor calcula os gramas. Não mande gramas.
Sem massa-base, mande cada linha em gramas. As farinhas, em gramas, somam 100 %. O servidor recalcula o % a partir desses gramas.
Com massa-base, o % é sobre a farinha já contida nela. Não repita ingrediente da base: sugira só inclusão, recheio ou acabamento.
Se a descrição mudar a farinha da base (meio integral, por exemplo), não acrescente essa farinha. Devolva em substituicoes: o % da farinha da base que ela substitui.
As linhas fixas não mudam: nem o ingrediente, nem a quantidade.
Quando um padrão da casa servir e não houver linha fixa nem ingrediente da base, use a porcentagem do padrão e escreva "padrão da casa" no motivo.
"Longa maturação" ou "fermentação natural" pede o levain ou o PFF no % do padrão da casa, com "padrão da casa" no motivo.
Confiança alta só na linha fixa ou no padrão da casa. O que a descrição pede fica média. O que a descrição não cita fica baixa.
Cada linha diz a função: massa, recheio, cobertura ou finalizacao. Sem função, é massa.
Não estime perda de processo nem de cocção. Esses números já vêm resolvidos. Se vier perda_pct, ela é ignorada.
Inclusão que o padeiro não mediu (castanha, embutido, erva, canela) sai como faixa típica: mínimo, máximo e um valor no meio. Nunca invente precisão.
Se faltar fermento ou sal no estoque, use o nome do catálogo.
Não crie ingrediente. Não cite preço, custo, cliente, pedido ou dado pessoal.
Não prometa saúde, ausência de glúten ou resultado de forno.
Responda somente pela ferramenta sugerir_receita.
""".strip()


def definir_gateway(gateway: GigioGateway | None) -> None:
    global _GATEWAY
    _GATEWAY = gateway


def situacao(db: Session) -> dict:
    ok, motivo = disponivel()
    usadas = _usadas_hoje(db)
    if ok and usadas >= LIMITE_DIA:
        ok = False
        motivo = "O limite de 30 sugestões de hoje já foi usado."
    return {"disponivel": ok, "motivo": motivo, "usadas": usadas, "limite": LIMITE_DIA}


def sugerir_receita(ctx: Contexto, produto_id: UUID, dados: dict, *, gravar: bool = True) -> dict:
    ok, motivo = disponivel()
    if not ok:
        raise ErroDeDominio("gigio_indisponivel", motivo or "O Gigio ainda não está configurado nesta padaria.", status=503)
    if _usadas_hoje(ctx.db) >= LIMITE_DIA:
        raise ErroDeDominio("limite_gigio", "O limite de 30 sugestões de hoje já foi usado.", status=429)
    try:
        descricao = limpar_descricao(dados.get("descricao"))
    except ValueError as exc:
        if str(exc) == "longa":
            raise ErroDeDominio("descricao_longa", f"A descrição passa de {MAX_DESCRICAO} caracteres.") from None
        raise ErroDeDominio("descricao_vazia", "Conte ao Gigio sobre este pão.") from None
    if parece_injecao(descricao):
        raise ErroDeDominio("descricao_recusada", "Esse texto não entra na sugestão.")

    produto, receita = _receita(ctx.db, produto_id)
    familia = ctx.db.get(Familia, produto.familia_id) if produto.familia_id else None
    fixas = _fixas(ctx.db, dados.get("linhas_fixas") or [])
    componente, da_base, farinha = _massa_base(ctx.db, dados.get("massa_base_id"), dados.get("massa_base_quantidade"))
    padroes = padroes_ativos(ctx.db, ctx.organizacao.id)
    perdas = resolver_receita(ctx.db, receita, familia_id=produto.familia_id, massa_total_g=None)
    entrada = _entrada(
        produto, familia.nome if familia else None, descricao, fixas, da_base, farinha, dados, padroes, ctx.db
    )
    pedido = ChatRequest(
        system_prompt=_instrucao(
            padroes, fixas, da_base, farinha, familia.nome if familia else None, texto_fixo(perdas)
        ),
        messages=[ChatTurn("user", _mensagem(entrada))],
        tools=[FERRAMENTA],
        max_tokens=2048,
    )
    try:
        resposta = _gateway().complete(pedido)
    except GatewayError as exc:
        raise ErroDeDominio("gigio_falhou", "O Gigio não conseguiu montar a sugestão agora.", status=502) from exc
    bruto = _da_ferramenta(resposta.tool_use)
    fechado = _fechar(
        ctx.db,
        bruto,
        fixas,
        da_base,
        componente,
        farinha,
        descricao,
        padroes,
        familia.nome if familia else None,
        _instrucao(padroes, fixas, da_base, farinha, familia.nome if familia else None),
    )
    tokens_entrada = (resposta.input_tokens or 0) + fechado["tokens_entrada"]
    tokens_saida = (resposta.output_tokens or 0) + fechado["tokens_saida"]
    saida = {
        "linhas": fechado["linhas"],
        "substituicoes": fechado["substituicoes"],
        "avisos": fechado["avisos"],
        "verificacoes": fechado["verificacoes"],
        "rendimento_g": _num(bruto.get("rendimento_g")),
        "perda_pct": None,
        "modo_de_fazer": [str(p).strip() for p in (bruto.get("modo_de_fazer") or []) if str(p).strip()][:20],
        "observacoes": _observacao(bruto.get("observacoes")),
    }
    registro_id = None
    if gravar:
        registro = GigioSugestao(
            organizacao_id=ctx.organizacao.id,
            receita_id=receita.id,
            usuario_id=ctx.principal.usuario_id,
            modelo=(resposta.model_id or "fake")[:120],
            tokens_entrada=tokens_entrada,
            tokens_saida=tokens_saida,
            entrada=entrada,
            saida=saida,
        )
        ctx.db.add(registro)
        ctx.db.flush()
        registro_id = str(registro.id)
    return {
        "id": registro_id,
        "modelo": resposta.model_id,
        "tokens_entrada": tokens_entrada,
        "tokens_saida": tokens_saida,
        **saida,
    }


def aplicar(ctx: Contexto, produto_id: UUID, dados: dict) -> dict:
    """Grava as linhas escolhidas no rascunho. Não publica. Substituição não soma farinha."""
    _produto, receita = _receita(ctx.db, produto_id)
    linhas = []
    for bruta in dados.get("linhas") or []:
        origem = bruta.get("origem") or ("manual" if bruta.get("fixa") else "estimado")
        if origem not in {"manual", "estimado", "conferido"}:
            origem = "estimado"
        linhas.append(
            {
                "ingrediente_id": bruta.get("ingrediente_id"),
                "texto": bruta.get("texto"),
                "quantidade": bruta.get("quantidade"),
                "unidade": bruta.get("unidade") or "g",
                "observacao": bruta.get("observacao"),
                "origem": origem,
                "faixa_min": bruta.get("faixa_min"),
                "faixa_max": bruta.get("faixa_max"),
                "funcao": bruta.get("funcao") or "massa",
            }
        )
    if dados.get("substituicoes"):
        linhas = _variar_base(ctx.db, linhas, dados["substituicoes"])
    if not dados.get("confirmar_sem_fermento") and not _linhas_tem_fermento(ctx.db, linhas):
        raise ErroDeDominio(
            "sem_fermento",
            "Falta o fermento. Confirme para aplicar mesmo assim.",
        )
    rendimento = dados.get("rendimento_quantidade")
    unidade = dados.get("rendimento_unidade")
    if rendimento is None and dados.get("rendimento_g"):
        rendimento = dados["rendimento_g"]
        unidade = "g"
    if rendimento is None:
        rendimento = receita.rendimento_quantidade
        unidade = receita.rendimento_unidade
    perda = receita.perda_percentual
    modo = dados.get("modo_de_fazer")
    if modo is None:
        modo = list(receita.modo_fazer or [])
    return salvar(
        ctx,
        produto_id,
        linhas=linhas,
        rendimento_quantidade=Decimal(str(rendimento)) if rendimento is not None else None,
        rendimento_unidade=unidade,
        peso_unidade_g=receita.peso_unidade_g if dados.get("peso_unidade_g") is None else Decimal(str(dados["peso_unidade_g"])),
        perda_percentual=Decimal(str(perda or 0)),
        modo_fazer=list(modo),
    )


def _gateway() -> GigioGateway:
    if _GATEWAY is not None:
        return _GATEWAY
    from app.domain.gigio.settings import gateway_falso

    if gateway_falso():
        return FakeGateway()
    return BedrockGateway(settings=load_gigio_model_settings())


def _usadas_hoje(db: Session) -> int:
    inicio = datetime.now(FUSO).replace(hour=0, minute=0, second=0, microsecond=0)
    return int(
        db.scalar(select(func.count()).select_from(GigioSugestao).where(GigioSugestao.criado_em >= inicio)) or 0
    )


def _receita(db: Session, produto_id: UUID) -> tuple[Produto, Receita]:
    produto = db.get(Produto, produto_id)
    if produto is None or not produto.ativo:
        raise ErroDeDominio("produto_inexistente", "Esse produto não existe.", status=404)
    receita = db.scalar(select(Receita).where(Receita.produto_id == produto.id))
    if receita is None:
        raise ErroDeDominio("sem_receita", "Esse produto não tem receita.", status=404)
    return produto, receita


def _fixas(db: Session, linhas: list[dict]) -> list[dict]:
    saida = []
    for bruta in linhas:
        quantidade = Decimal(str(bruta.get("quantidade") or 0))
        unidade = bruta.get("unidade") or "g"
        if quantidade <= 0 or unidade not in UNIDADES:
            continue
        ing = None
        if bruta.get("ingrediente_id"):
            ing = db.get(Ingrediente, bruta["ingrediente_id"])
        nome = ing.nome if ing else (bruta.get("texto") or bruta.get("nome") or "").strip()
        if not nome:
            continue
        gramas = float(para_base(quantidade, unidade, "g")) if unidade in {"g", "kg"} else None
        saida.append(
            {
                "ingrediente_id": str(ing.id) if ing else None,
                "nome": nome,
                "quantidade": float(quantidade),
                "quantidade_g": gramas,
                "unidade": unidade,
                "fixa": True,
            }
        )
    return saida


def _massa_base(db: Session, produto_id, peso) -> tuple[dict | None, list[dict], Decimal]:
    """Componente, ingredientes já incluídos e a farinha contida nesse peso."""
    if not produto_id:
        return None, [], Decimal(0)
    peso_g = Decimal(str(peso or 0))
    if peso_g <= 0:
        raise ErroDeDominio("massa_base_invalida", "Informe o peso da massa-base.")
    produto = db.get(Produto, produto_id)
    if produto is None or not produto.ativo or not produto.uso_componente:
        raise ErroDeDominio("massa_base_invalida", "A massa-base precisa ser um preparo da casa.")
    ing = db.scalar(select(Ingrediente).where(Ingrediente.produto_id == produto.id))
    if ing is None:
        raise ErroDeDominio("massa_base_invalida", "A massa-base ainda não é um ingrediente.")
    folhas = folhas_publicadas(db, produto.id, peso_g)
    if not folhas:
        raise ErroDeDominio(
            "massa_sem_receita",
            f"Monte primeiro a receita da {produto.nome}.",
        )
    farinha = farinha_contida(db, produto.id, peso_g)
    componente = {
        "ingrediente_id": str(ing.id),
        "nome": ing.nome,
        "quantidade": float(peso_g),
        "quantidade_g": float(peso_g),
        "unidade": "g",
        "fixa": True,
        "componente": True,
    }
    da_base = [
        {
            "ingrediente_id": folha["ingrediente_id"],
            "nome": folha["nome"],
            "quantidade_g": float(folha["quantidade_g"]),
            "categoria": folha["categoria"],
        }
        for folha in folhas
    ]
    return componente, da_base, farinha


def _entrada(produto, familia, descricao, fixas, da_base, farinha, dados, padroes, db: Session) -> dict:
    ingredientes = [
        {"nome": i.nome, "categoria": i.categoria}
        for i in db.scalars(select(Ingrediente).where(Ingrediente.ativo.is_(True)).order_by(Ingrediente.nome))
    ]
    catalogo = [
        {"nome": c.nome, "categoria": c.categoria}
        for c in db.scalars(select(CatalogoIngrediente).order_by(CatalogoIngrediente.nome))
    ]
    return {
        "produto": produto.nome,
        "familia": familia,
        "descricao": descricao,
        "massa_base_id": str(dados["massa_base_id"]) if dados.get("massa_base_id") else None,
        "massa_base_quantidade": _num(dados.get("massa_base_quantidade")),
        "farinha_contida_g": float(farinha) if farinha else None,
        "linhas_fixas": [
            {"nome": f["nome"], "quantidade": f["quantidade"], "unidade": f["unidade"]} for f in fixas
        ],
        "massa_base": [
            {"nome": f["nome"], "quantidade_g": f["quantidade_g"]} for f in da_base
        ],
        "rendimento_quantidade": _num(dados.get("rendimento_quantidade")),
        "rendimento_unidade": dados.get("rendimento_unidade"),
        "padroes": [
            {"nome": p.nome, "termo": p.termo, "percentual": float(p.percentual)} for p in padroes
        ],
        "ingredientes": ingredientes,
        "catalogo": catalogo,
    }


def _qtd_txt(valor: Decimal | float) -> str:
    numero = Decimal(str(valor))
    if numero == numero.to_integral_value():
        return str(int(numero))
    return _gramas(numero)


def _gramas(valor: Decimal | float) -> str:
    texto = f"{Decimal(str(valor)).quantize(Decimal('0.1')):f}"
    return texto.rstrip("0").rstrip(".")


def _instrucao(padroes, fixas, da_base, farinha: Decimal, familia: str | None = None, perdas_txt: str | None = None) -> str:
    casa = "\n".join(
        f"- {p.nome}: {p.percentual} % ({p.termo}). {p.observacao or ''}".strip() for p in padroes
    ) or "- Nenhum padrão ativo."
    travadas = "\n".join(
        f"- {f['nome']}: {_qtd_txt(f['quantidade'])} {f['unidade']} (não mude)" for f in fixas
    ) or "- Nenhuma linha fixa."
    if da_base:
        incluidas = "\n".join(
            f"- {f['nome']}: {_gramas(f['quantidade_g'])} g (já incluída na massa-base)" for f in da_base
        )
        base = (
            f"Massa-base já incluída. Farinha contida: {_gramas(farinha)} g. "
            "O % das sugestões é sobre essa farinha. Não repita estes ingredientes:\n"
            f"{incluidas}"
        )
    else:
        base = (
            "Nenhuma massa-base. Informe cada linha em gramas, e o % que você calculou. "
            "A soma das farinhas, em gramas, é 100 %. O servidor recalcula o % (gramas ÷ essa farinha) "
            "e ignora um % que não feche com os gramas. Não deixe quantidade_g em zero."
        )
    faixa = faixa_da_familia(familia)
    faixa_txt = ""
    if faixa:
        faixa_txt = (
            f"\nHidratação da família {faixa['nome']}: "
            f"{faixa['hidratacao_min']}–{faixa['hidratacao_max']} %."
        )
    perdas = perdas_txt or texto_fixo(None)
    return (
        f"{PERSONA}\n\nPadrões da casa:\n{casa}\n\n"
        f"Linhas fixas, que valem mais que o padrão:\n{travadas}\n\n{base}{faixa_txt}\n\n{perdas}"
    )


def _mensagem(entrada: dict) -> str:
    return (
        f"Produto: {entrada['produto']}\n"
        f"Família: {entrada['familia'] or 'sem família'}\n"
        f"Descrição do padeiro:\n{entrada['descricao']}\n"
        f"Rendimento desejado: {entrada['rendimento_quantidade'] or 'não informado'} {entrada['rendimento_unidade'] or ''}"
    )


def _da_ferramenta(tools: list[dict]) -> dict:
    for ferramenta in tools:
        if ferramenta.get("name") == "sugerir_receita" and isinstance(ferramenta.get("input"), dict):
            return ferramenta["input"]
    raise ErroDeDominio("saida_invalida", "O Gigio não devolveu uma sugestão utilizável.")


def _faixa(bruta: dict) -> tuple[float | None, float | None]:
    minima = _num(bruta.get("faixa_min"))
    maxima = _num(bruta.get("faixa_max"))
    if minima is not None and maxima is not None and abs(minima - maxima) < 1e-9:
        return None, None
    return minima, maxima


def _percentual(quantidade, farinha: Decimal, componente: bool) -> float | None:
    if componente or farinha <= 0 or not quantidade:
        return None
    return float(Decimal(str(quantidade)) / farinha * Decimal(100))


def _ligar(
    db: Session,
    linhas: list,
    fixas: list[dict],
    da_base: list[dict],
    componente: dict | None,
    farinha: Decimal,
) -> tuple[list[dict], list[str]]:
    visao = carregar_visao(db)
    catalogo = list(db.scalars(select(CatalogoIngrediente)))
    por_id = {f["ingrediente_id"]: f for f in fixas if f["ingrediente_id"]}
    por_nome = {normalizar(f["nome"]): f for f in fixas}
    ids_base = {f["ingrediente_id"] for f in da_base if f.get("ingrediente_id")}
    nomes_base = {normalizar(f["nome"]) for f in da_base if f.get("nome")}
    if componente and componente.get("ingrediente_id"):
        ids_base.add(componente["ingrediente_id"])
    usadas: set[str] = set()
    saida = []
    avisos: list[str] = []
    for bruta in linhas:
        nome = str(bruta.get("ingrediente") or "").strip()
        if not nome:
            continue
        fixa = por_nome.get(normalizar(nome))
        ing, texto = (None, nome)
        if fixa and fixa["ingrediente_id"]:
            ing = db.get(Ingrediente, fixa["ingrediente_id"])
            texto = None
        else:
            ing, texto = _buscar(db, visao, catalogo, nome)
        fora_estoque = False
        if ing is None and essencial(nome):
            do_catalogo = _nome_catalogo(catalogo, nome)
            if do_catalogo:
                texto = do_catalogo
                fora_estoque = True
        if fixa is None and ing is not None:
            fixa = por_id.get(str(ing.id))
        nome_ligado = ing.nome if ing else (texto or nome)
        repetida = normalizar(nome) in nomes_base or normalizar(nome_ligado) in nomes_base
        if ing is not None and str(ing.id) in ids_base:
            repetida = True
        funcao = str(bruta.get("funcao") or "massa").strip().lower()
        if funcao not in {"massa", "recheio", "cobertura", "finalizacao"}:
            funcao = "massa"
        if fixa is None and repetida and funcao == "massa":
            avisos.append(f"{nome_ligado} já está na massa-base e foi descartada.")
            continue
        quantidade = _num(bruta.get("quantidade_g")) or 0
        unidade = "g"
        motivo = str(bruta.get("motivo") or "")[:180]
        if fixa is not None:
            quantidade = fixa["quantidade_g"] if fixa["quantidade_g"] is not None else fixa["quantidade"]
            unidade = fixa["unidade"] if fixa["quantidade_g"] is None else "g"
            if fixa["quantidade_g"] is not None:
                quantidade = fixa["quantidade_g"]
                unidade = "g"
            motivo = "Linha fixa da receita. Vale mais que o padrão da casa."
            usadas.add(fixa["ingrediente_id"] or normalizar(fixa["nome"]))
        confianca = bruta.get("confianca")
        if confianca not in {"alta", "media", "baixa"}:
            confianca = "media"
        minima, maxima = _faixa(bruta)
        saida.append(
            {
                "ingrediente_id": str(ing.id) if ing else None,
                "nome": nome_ligado,
                "texto": None if ing else (texto or nome),
                "a_decidir": ing is None,
                "fora_estoque": fora_estoque,
                "categoria": ing.categoria if ing else None,
                "componente": False,
                "percentual_pedido": _num(bruta.get("percentual")),
                "quantidade": quantidade,
                "unidade": unidade,
                "percentual": _percentual(quantidade, farinha, False) if da_base else _num(bruta.get("percentual")),
                "faixa_min": minima,
                "faixa_max": maxima,
                "confianca": confianca,
                "motivo": motivo,
                "fixa": fixa is not None,
                "origem": "manual" if fixa is not None else "estimado",
                "funcao": funcao,
            }
        )
    for fixa in fixas:
        chave = fixa["ingrediente_id"] or normalizar(fixa["nome"])
        if chave in usadas:
            continue
        ing = db.get(Ingrediente, fixa["ingrediente_id"]) if fixa["ingrediente_id"] else None
        quantidade = fixa["quantidade_g"] if fixa["quantidade_g"] is not None else fixa["quantidade"]
        saida.insert(
            0,
            {
                "ingrediente_id": fixa["ingrediente_id"],
                "nome": ing.nome if ing else fixa["nome"],
                "texto": None if ing else fixa["nome"],
                "a_decidir": ing is None,
                "fora_estoque": False,
                "categoria": ing.categoria if ing else None,
                "componente": False,
                "percentual_pedido": None,
                "quantidade": quantidade,
                "unidade": "g" if fixa["quantidade_g"] is not None else fixa["unidade"],
                "percentual": _percentual(quantidade, farinha, False) if da_base else None,
                "faixa_min": None,
                "faixa_max": None,
                "confianca": "alta",
                "motivo": "Linha fixa da receita. Vale mais que o padrão da casa.",
                "fixa": True,
                "origem": "manual",
                "funcao": "massa",
            },
        )
    if componente is not None and componente.get("ingrediente_id"):
        saida.insert(
            0,
            {
                "ingrediente_id": componente["ingrediente_id"],
                "nome": componente["nome"],
                "texto": None,
                "a_decidir": False,
                "fora_estoque": False,
                "categoria": None,
                "componente": True,
                "percentual_pedido": None,
                "quantidade": componente["quantidade"],
                "unidade": "g",
                "percentual": None,
                "faixa_min": None,
                "faixa_max": None,
                "confianca": "alta",
                "motivo": "Massa-base. Os ingredientes dela já estão incluídos.",
                "fixa": True,
                "origem": "manual",
                "funcao": "massa",
            },
        )
    return saida, avisos


def _buscar(db: Session, visao, catalogo, nome: str):
    opcoes = sugerir(visao, catalogo, nome)
    if not opcoes:
        return None, nome
    primeira = opcoes[0]
    ing = primeira.get("ingrediente")
    if primeira.get("destaque") and ing:
        entidade = db.get(Ingrediente, ing["id"])
        if entidade is not None and entidade.ativo:
            return entidade, None
    return None, nome


def _nome_catalogo(catalogo, nome: str) -> str | None:
    alvo = normalizar(nome)
    candidatos = [item.nome for item in catalogo if alvo and (normalizar(item.nome) == alvo or alvo in normalizar(item.nome))]
    if not candidatos:
        return None
    return sorted(candidatos, key=lambda item: (normalizar(item) != alvo, len(item)))[0]


def _observacao(texto) -> str:
    limpo = str(texto or "").strip()
    if limpo.lower().startswith("produto:"):
        return ""
    return limpo[:500]


def _padrao_fermento(padroes):
    for padrao in padroes:
        if e_fermento(padrao.termo) or e_fermento(padrao.nome):
            return padrao
    return None


def _tem_nas_linhas(linhas, da_base) -> bool:
    if any(e_fermento(linha.get("nome"), linha.get("categoria")) for linha in linhas):
        return True
    return any(e_fermento(folha.get("nome"), folha.get("categoria")) for folha in da_base)


def _acertar(linhas, farinha: Decimal, descricao, padroes, substituicoes_brutas):
    conhecida = farinha > 0
    if not conhecida:
        farinha = sum(
            (
                Decimal(str(linha.get("quantidade") or 0))
                for linha in linhas
                if e_farinha(linha.get("nome"), linha.get("categoria")) and not linha.get("componente")
            ),
            Decimal(0),
        )
    avisos: list[str] = []
    escala_percentual = False
    soma_farinha = Decimal(0)
    if not conhecida and farinha <= 0:
        soma_farinha = sum(
            (
                Decimal(str(linha.get("percentual_pedido") or 0))
                for linha in linhas
                if e_farinha(linha.get("nome"), linha.get("categoria")) and not linha.get("componente")
            ),
            Decimal(0),
        )
        if soma_farinha > 0:
            farinha = Decimal(1000)
            escala_percentual = True
            avisos.append("Sem gramas de farinha, a conta usa 1 kg de farinha.")
    substituicoes = []
    nomes_troca: set[str] = set()
    for bruta in substituicoes_brutas or []:
        nome = str(bruta.get("ingrediente") or "").strip()
        percentual = Decimal(str(bruta.get("percentual") or 0))
        if not nome or percentual <= 0 or farinha <= 0:
            continue
        gramas = gramas_do_percentual(percentual, farinha)
        substituicoes.append(
            {
                "nome": nome,
                "percentual": float(percentual_dos_gramas(gramas, farinha) or percentual),
                "quantidade_g": float(gramas),
                "motivo": str(bruta.get("motivo") or "Substitui parte da farinha da base.")[:180],
                "confianca": calibrar_confianca(
                    bruta.get("confianca"), fixa=False, padrao=False, descrita=na_descricao(nome, descricao)
                ),
            }
        )
        nomes_troca.add(normalizar(nome))
    saida = []
    for linha in linhas:
        if linha.get("componente"):
            saida.append(linha)
            continue
        if (
            conhecida
            and not linha.get("fixa")
            and e_farinha(linha.get("nome"), linha.get("categoria"))
        ):
            percentual = Decimal(str(linha.get("percentual_pedido") or linha.get("percentual") or 0))
            if percentual > 0 and normalizar(linha["nome"]) not in nomes_troca:
                gramas = gramas_do_percentual(percentual, farinha)
                substituicoes.append(
                    {
                        "nome": linha["nome"],
                        "percentual": float(percentual_dos_gramas(gramas, farinha) or percentual),
                        "quantidade_g": float(gramas),
                        "motivo": linha.get("motivo") or "Substitui parte da farinha da base.",
                        "confianca": calibrar_confianca(
                            "media", fixa=False, padrao=False, descrita=na_descricao(linha["nome"], descricao)
                        ),
                    }
                )
                nomes_troca.add(normalizar(linha["nome"]))
            avisos.append(f"{linha['nome']} entrou como substituição da farinha da base, não como acréscimo.")
            continue
        quantidade = Decimal(str(linha.get("quantidade") or 0))
        aviso = None
        if not linha.get("fixa") and conhecida and farinha > 0 and linha.get("percentual_pedido") is not None:
            percentual = Decimal(str(linha["percentual_pedido"]))
            percentual, aviso = apertar_faixa(percentual, linha.get("faixa_min"), linha.get("faixa_max"))
            quantidade = gramas_do_percentual(percentual, farinha)
        elif escala_percentual and not linha.get("fixa") and farinha > 0:
            percentual = Decimal(str(linha.get("percentual_pedido") or 0))
            if e_farinha(linha.get("nome"), linha.get("categoria")) and soma_farinha > 0:
                percentual = percentual / soma_farinha * Decimal(100)
            percentual, aviso = apertar_faixa(percentual, linha.get("faixa_min"), linha.get("faixa_max"))
            quantidade = gramas_do_percentual(percentual, farinha)
        percentual = None
        if farinha > 0:
            percentual = percentual_dos_gramas(quantidade, farinha)
        padrao = casa_com_padrao(linha.get("nome"), linha.get("motivo"), percentual, padroes)
        linha = {
            **linha,
            "quantidade": float(quantidade),
            "percentual": float(percentual) if percentual is not None else None,
            "confianca": calibrar_confianca(
                linha.get("confianca"),
                fixa=bool(linha.get("fixa")),
                padrao=padrao,
                descrita=na_descricao(linha.get("nome"), descricao),
                classico=sal_classico(linha.get("nome"), percentual),
            ),
        }
        linha.pop("percentual_pedido", None)
        if aviso:
            avisos.append(f"{linha['nome']}: {aviso}")
        saida.append(linha)
    for linha in saida:
        linha.pop("percentual_pedido", None)
    return saida, substituicoes, avisos, farinha


def _fechar(db, bruto, fixas, da_base, componente, farinha, descricao, padroes, familia, instrucao):
    linhas, avisos = _ligar(db, bruto.get("linhas") or [], fixas, da_base, componente, farinha)
    if bruto.get("perda_pct") is not None:
        avisos.append("O Gigio informou uma perda e ela foi ignorada.")
    linhas, substituicoes, extras, farinha_final = _acertar(
        linhas, farinha, descricao, padroes, bruto.get("substituicoes")
    )
    avisos.extend(extras)
    tokens_entrada = 0
    tokens_saida = 0
    if not _tem_nas_linhas(linhas, da_base):
        pedido = ChatRequest(
            system_prompt=instrucao,
            messages=[
                ChatTurn(
                    "user",
                    "Falta o agente de fermentação. Sugira só o fermento, o levain ou o PFF, "
                    f"em % da farinha contida ({_gramas(farinha_final) if farinha_final else 'a soma das farinhas'} g). "
                    "Se a descrição pedir longa maturação ou fermentação natural, use o padrão da casa.",
                )
            ],
            tools=[FERRAMENTA],
            max_tokens=800,
        )
        try:
            resposta = _gateway().complete(pedido)
        except GatewayError:
            resposta = None
        if resposta is not None:
            tokens_entrada += resposta.input_tokens or 0
            tokens_saida += resposta.output_tokens or 0
            try:
                extra = _da_ferramenta(resposta.tool_use)
            except ErroDeDominio:
                extra = {}
            novas, _avisos_ligar = _ligar(db, extra.get("linhas") or [], [], da_base, None, farinha_final or farinha)
            novas = [linha for linha in novas if e_fermento(linha.get("nome"), linha.get("categoria"))]
            if novas:
                novas, _, _, farinha_final = _acertar(novas, farinha_final or farinha, descricao, padroes, [])
                linhas.extend(novas)
    if not _tem_nas_linhas(linhas, da_base) and pede_fermento_natural(descricao) and farinha_final > 0:
        padrao = _padrao_fermento(padroes)
        if padrao is not None:
            gramas = gramas_do_percentual(padrao.percentual, farinha_final)
            linhas.append(
                {
                    "ingrediente_id": None,
                    "nome": padrao.nome,
                    "texto": padrao.termo,
                    "a_decidir": True,
                    "fora_estoque": True,
                    "categoria": None,
                    "componente": False,
                    "quantidade": float(gramas),
                    "unidade": "g",
                    "percentual": float(padrao.percentual),
                    "faixa_min": None,
                    "faixa_max": None,
                    "confianca": "alta",
                    "motivo": "Padrão da casa. A descrição pede longa maturação ou fermentação natural.",
                    "fixa": False,
                    "origem": "estimado",
                }
            )
    componentes = []
    if da_base:
        nome = componente["nome"] if componente else "massa-base"
        componentes.append({"nome": nome, "folhas": da_base})
    ver = verificar(linhas, farinha=farinha_final, familia=familia, componentes=componentes)
    for aviso in ver["avisos"]:
        if aviso["mensagem"] not in avisos:
            avisos.append(aviso["mensagem"])
    for pendencia in ver["pendencias"]:
        if pendencia["mensagem"] not in avisos:
            avisos.append(pendencia["mensagem"])
    return {
        "linhas": linhas,
        "substituicoes": substituicoes,
        "avisos": avisos,
        "verificacoes": {"pendencias": ver["pendencias"], "avisos": ver["avisos"]},
        "tokens_entrada": tokens_entrada,
        "tokens_saida": tokens_saida,
        "farinha": farinha_final,
    }


def _variar_base(db: Session, linhas: list[dict], substituicoes: list[dict]) -> list[dict]:
    saida = []
    for linha in linhas:
        ing = db.get(Ingrediente, linha["ingrediente_id"]) if linha.get("ingrediente_id") else None
        if ing is None or ing.produto_id is None or not compativel(linha.get("unidade") or "g", "g"):
            saida.append(linha)
            continue
        peso = para_base(Decimal(str(linha["quantidade"])), linha["unidade"], "g")
        folhas = folhas_publicadas(db, ing.produto_id, peso)
        for troca in substituicoes:
            folhas = aplicar_substituicao(folhas, troca.get("nome") or troca.get("ingrediente") or "", troca.get("percentual"))
        for folha in folhas:
            quantidade = Decimal(str(folha["quantidade_g"]))
            if quantidade <= 0:
                continue
            saida.append(
                {
                    "ingrediente_id": folha.get("ingrediente_id"),
                    "texto": None if folha.get("ingrediente_id") else folha["nome"],
                    "quantidade": float(quantidade),
                    "unidade": "g",
                    "observacao": None,
                    "origem": "estimado",
                    "faixa_min": None,
                    "faixa_max": None,
                }
            )
    return saida


def _linhas_tem_fermento(db: Session, linhas: list[dict]) -> bool:
    for linha in linhas:
        ing = db.get(Ingrediente, linha["ingrediente_id"]) if linha.get("ingrediente_id") else None
        nome = ing.nome if ing else (linha.get("texto") or "")
        categoria = ing.categoria if ing else None
        if e_fermento(nome, categoria):
            return True
        if ing is not None and ing.produto_id is not None and compativel(linha.get("unidade") or "g", "g"):
            peso = para_base(Decimal(str(linha["quantidade"])), linha["unidade"], "g")
            for folha in folhas_publicadas(db, ing.produto_id, peso):
                if e_fermento(folha.get("nome"), folha.get("categoria")):
                    return True
    return False


def ensaiar(
    db: Session,
    organizacao_id: UUID,
    *,
    titulo: str,
    familia: str | None,
    descricao: str,
    base: list[dict],
) -> dict:
    """Uma sugestão de leitura. Não grava receita, produto nem auditoria."""
    from app.db.escopo import ativar_escopo

    ativar_escopo(db, organizacao_id)
    da_base = [
        {"ingrediente_id": None, "nome": item["nome"], "quantidade_g": float(item["quantidade_g"]), "categoria": None}
        for item in base
    ]
    farinha = sum(
        (Decimal(str(item["quantidade_g"])) for item in da_base if "farinha" in normalizar(item["nome"])),
        Decimal(0),
    )
    visao = carregar_visao(db)
    catalogo = list(db.scalars(select(CatalogoIngrediente)))
    for item in da_base:
        # A linha que o padeiro já informou não troca de nome. Só liga o
        # ingrediente da casa quando o nome é o mesmo; um parecido (sarraceno
        # no lugar de trigo) não entra na massa-base.
        ing, _texto = _buscar(db, visao, catalogo, item["nome"])
        if ing is not None and normalizar(ing.nome) == normalizar(item["nome"]):
            item["ingrediente_id"] = str(ing.id)
            item["nome"] = ing.nome
    padroes = padroes_ativos(db, organizacao_id)
    nomes = "\n".join(f"- {i.nome} ({i.categoria})" for i in visao.ingredientes.values() if i.ativo)
    entrada = {
        "produto": titulo,
        "familia": familia,
        "descricao": descricao,
        "rendimento_quantidade": None,
        "rendimento_unidade": None,
    }
    instrucao = _instrucao(padroes, [], da_base, farinha, familia)
    pedido = ChatRequest(
        system_prompt=instrucao,
        messages=[ChatTurn("user", _mensagem(entrada) + f"\nIngredientes da padaria, só nome e categoria:\n{nomes}")],
        tools=[FERRAMENTA],
        max_tokens=2048,
    )
    resposta = _gateway().complete(pedido)
    bruto = _da_ferramenta(resposta.tool_use)
    componente = {"nome": "massa-base"} if da_base else None
    fechado = _fechar(db, bruto, [], da_base, componente, farinha, descricao, padroes, familia, instrucao)
    incluidas = []
    for item in da_base:
        quantidade = item["quantidade_g"]
        incluidas.append(
            {
                "nome": item["nome"],
                "quantidade": quantidade,
                "unidade": "g",
                "percentual": float(Decimal(str(quantidade)) / farinha * 100) if farinha else None,
                "faixa_min": None,
                "faixa_max": None,
                "confianca": "alta",
                "motivo": "Já incluída na massa-base.",
                "fixa": True,
            }
        )
    return {
        "titulo": titulo,
        "descricao": descricao,
        "modelo": resposta.model_id,
        "tokens_entrada": (resposta.input_tokens or 0) + fechado["tokens_entrada"],
        "tokens_saida": (resposta.output_tokens or 0) + fechado["tokens_saida"],
        "farinha_contida_g": float(fechado["farinha"]) if fechado["farinha"] else None,
        "linhas": incluidas + fechado["linhas"],
        "substituicoes": fechado["substituicoes"],
        "avisos": fechado["avisos"],
        "verificacoes": fechado["verificacoes"],
        "rendimento_g": _num(bruto.get("rendimento_g")),
        "perda_pct": None,
        "modo_de_fazer": [str(p).strip() for p in (bruto.get("modo_de_fazer") or []) if str(p).strip()][:20],
        "observacoes": _observacao(bruto.get("observacoes")),
    }


def _num(valor) -> float | None:
    if valor is None or valor == "":
        return None
    try:
        return float(valor)
    except (TypeError, ValueError):
        return None

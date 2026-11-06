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
from app.domain.receitas import UNIDADES, farinha_contida, folhas_publicadas, para_base, salvar
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
                    },
                    "required": ["ingrediente", "quantidade_g", "percentual", "confianca", "motivo"],
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
Trabalhe em porcentagem do padeiro. Sem massa-base, a farinha da massa vale 100 %.
Com massa-base, o % é sobre a farinha já contida nela. Não repita ingrediente da base: sugira só inclusão, recheio ou acabamento.
As linhas fixas não mudam: nem o ingrediente, nem a quantidade.
Quando um padrão da casa servir e não houver linha fixa nem ingrediente da base, use a porcentagem do padrão e escreva "padrão da casa" no motivo.
Inclusão que o padeiro não mediu (castanha, embutido, erva, canela) sai como faixa típica: mínimo, máximo e um valor no meio. Nunca invente precisão.
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
    entrada = _entrada(
        produto, familia.nome if familia else None, descricao, fixas, da_base, farinha, dados, padroes, ctx.db
    )
    pedido = ChatRequest(
        system_prompt=_instrucao(padroes, fixas, da_base, farinha),
        messages=[ChatTurn("user", _mensagem(entrada))],
        tools=[FERRAMENTA],
        max_tokens=2048,
    )
    try:
        resposta = _gateway().complete(pedido)
    except GatewayError as exc:
        raise ErroDeDominio("gigio_falhou", "O Gigio não conseguiu montar a sugestão agora.", status=502) from exc
    bruto = _da_ferramenta(resposta.tool_use)
    linhas, avisos = _ligar(ctx.db, bruto.get("linhas") or [], fixas, da_base, componente, farinha)
    saida = {
        "linhas": linhas,
        "avisos": avisos,
        "rendimento_g": _num(bruto.get("rendimento_g")),
        "perda_pct": _num(bruto.get("perda_pct")),
        "modo_de_fazer": [str(p).strip() for p in (bruto.get("modo_de_fazer") or []) if str(p).strip()][:20],
        "observacoes": str(bruto.get("observacoes") or "")[:500],
    }
    registro_id = None
    if gravar:
        registro = GigioSugestao(
            organizacao_id=ctx.organizacao.id,
            receita_id=receita.id,
            usuario_id=ctx.principal.usuario_id,
            modelo=(resposta.model_id or "fake")[:120],
            tokens_entrada=resposta.input_tokens,
            tokens_saida=resposta.output_tokens,
            entrada=entrada,
            saida=saida,
        )
        ctx.db.add(registro)
        ctx.db.flush()
        registro_id = str(registro.id)
    return {
        "id": registro_id,
        "modelo": resposta.model_id,
        "tokens_entrada": resposta.input_tokens,
        "tokens_saida": resposta.output_tokens,
        **saida,
    }


def aplicar(ctx: Contexto, produto_id: UUID, dados: dict) -> dict:
    """Grava as linhas escolhidas no rascunho. Não publica."""
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
            }
        )
    rendimento = dados.get("rendimento_quantidade")
    unidade = dados.get("rendimento_unidade")
    if rendimento is None and dados.get("rendimento_g"):
        rendimento = dados["rendimento_g"]
        unidade = "g"
    if rendimento is None:
        rendimento = receita.rendimento_quantidade
        unidade = receita.rendimento_unidade
    perda = dados.get("perda_percentual")
    if perda is None:
        perda = dados.get("perda_pct")
    if perda is None:
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


def _instrucao(padroes, fixas, da_base, farinha: Decimal) -> str:
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
        base = "Nenhuma massa-base. A farinha desta receita vale 100 %."
    return (
        f"{PERSONA}\n\nPadrões da casa:\n{casa}\n\n"
        f"Linhas fixas, que valem mais que o padrão:\n{travadas}\n\n{base}"
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
        if fixa is None and ing is not None:
            fixa = por_id.get(str(ing.id))
        nome_ligado = ing.nome if ing else nome
        repetida = normalizar(nome) in nomes_base or normalizar(nome_ligado) in nomes_base
        if ing is not None and str(ing.id) in ids_base:
            repetida = True
        if fixa is None and repetida:
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
                "quantidade": quantidade,
                "unidade": unidade,
                "percentual": _percentual(quantidade, farinha, False) if da_base else _num(bruta.get("percentual")),
                "faixa_min": minima,
                "faixa_max": maxima,
                "confianca": confianca,
                "motivo": motivo,
                "fixa": fixa is not None,
                "origem": "manual" if fixa is not None else "estimado",
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
                "quantidade": quantidade,
                "unidade": "g" if fixa["quantidade_g"] is not None else fixa["unidade"],
                "percentual": _percentual(quantidade, farinha, False) if da_base else None,
                "faixa_min": None,
                "faixa_max": None,
                "confianca": "alta",
                "motivo": "Linha fixa da receita. Vale mais que o padrão da casa.",
                "fixa": True,
                "origem": "manual",
            },
        )
    if componente is not None:
        saida.insert(
            0,
            {
                "ingrediente_id": componente["ingrediente_id"],
                "nome": componente["nome"],
                "texto": None,
                "a_decidir": False,
                "quantidade": componente["quantidade"],
                "unidade": "g",
                "percentual": None,
                "faixa_min": None,
                "faixa_max": None,
                "confianca": "alta",
                "motivo": "Massa-base. Os ingredientes dela já estão incluídos.",
                "fixa": True,
                "origem": "manual",
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
    pedido = ChatRequest(
        system_prompt=_instrucao(padroes, [], da_base, farinha),
        messages=[ChatTurn("user", _mensagem(entrada) + f"\nIngredientes da padaria, só nome e categoria:\n{nomes}")],
        tools=[FERRAMENTA],
        max_tokens=2048,
    )
    resposta = _gateway().complete(pedido)
    bruto = _da_ferramenta(resposta.tool_use)
    linhas, avisos = _ligar(db, bruto.get("linhas") or [], [], da_base, None, farinha)
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
        "tokens_entrada": resposta.input_tokens,
        "tokens_saida": resposta.output_tokens,
        "farinha_contida_g": float(farinha) if farinha else None,
        "linhas": incluidas + linhas,
        "avisos": avisos,
        "rendimento_g": _num(bruto.get("rendimento_g")),
        "perda_pct": _num(bruto.get("perda_pct")),
        "modo_de_fazer": [str(p).strip() for p in (bruto.get("modo_de_fazer") or []) if str(p).strip()][:20],
        "observacoes": str(bruto.get("observacoes") or "")[:500],
    }


def _num(valor) -> float | None:
    if valor is None or valor == "":
        return None
    try:
        return float(valor)
    except (TypeError, ValueError):
        return None

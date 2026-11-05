"""Achar o ingrediente certo antes de cadastrar outro: comparação de nomes, busca e sugestão.

A comparação é feita em Python (rapidfuzz), sem extensão no Postgres. Para comparar, NÃO contam:
acento, maiúsculas, plural, ordem das palavras, palavras vazias (de, da, tipo...) e o peso/volume
escrito no nome ("1 kg", "500 g", "1,5 L"). Números que identificam o produto (o "00" de
"farinha 00") contam: "tipo 00" nunca vira "tipo 0".
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable

from rapidfuzz import fuzz

from app.domain import estoque as est
from app.domain.normalizacao import PALAVRAS_VAZIAS, _singular, normalizar, sao_parecidos
from app.models.estoque import CatalogoIngrediente, Ingrediente

# Acima disto um nome é "parecido" com outro (o cadastro exige confirmação).
LIMIAR_PARECIDO = 85.0
# Abaixo disto a busca/sugestão nem mostra o resultado.
LIMIAR_BUSCA = 70.0
MAX_SUGESTOES = 3
MAX_CATALOGO_NA_BUSCA = 8

_PESO = re.compile(
    r"(?<![a-z0-9])\d+(?:[.,]\d+)?\s*"
    r"(?:kgs?|quilos?|gramas?|grs?|g|mg|litros?|lts?|l|ml|unidades?|unids?|und|un)"
    r"(?![a-z0-9])"
)


def _sem_acento(texto: str) -> str:
    decomposto = unicodedata.normalize("NFKD", texto or "")
    return "".join(c for c in decomposto if not unicodedata.combining(c)).lower()


def sem_peso(texto: str) -> str:
    """Tira "1 kg", "500 g", "1,5 L" do nome (devolve sem acento e em minúsculas)."""
    return _PESO.sub(" ", _sem_acento(texto))


def _singular_nome(palavra: str) -> str:
    if len(palavra) > 4 and palavra.endswith("zes"):  # nozes -> noz
        return palavra[:-2]
    return _singular(palavra)


def palavras(texto: str) -> frozenset[str]:
    """O que sobra do nome para comparar: sem peso, sem palavra vazia, no singular."""
    normal = normalizar(sem_peso(texto))
    return frozenset(_singular_nome(p) for p in normal.split() if p not in PALAVRAS_VAZIAS)


def chave_de_comparacao(texto: str) -> str:
    return " ".join(sorted(palavras(texto)))


def _numeros(conjunto: frozenset[str]) -> frozenset[str]:
    return frozenset(p for p in conjunto if p.isdigit())


def pontuar_palavras(q: frozenset[str], a: frozenset[str]) -> float:
    """0 a 100: quanto `q` (o que a pessoa escreveu) combina com `a` (um nome conhecido)."""
    if not q or not a:
        return 0.0
    nq, na = _numeros(q), _numeros(a)
    if nq and na and nq != na:
        return 0.0  # "tipo 00" não é "tipo 0"
    if q == a:
        return 100.0
    if a <= q or q <= a:
        menor, maior = (a, q) if a <= q else (q, a)
        r = len(menor) / len(maior)
        return 80 + 20 * r if len(menor) >= 2 else 70 + 15 * r
    f = fuzz.ratio(" ".join(sorted(q)), " ".join(sorted(a)))
    return f * 0.92 if f >= LIMIAR_PARECIDO else 0.0


def pontuar(consulta: str, alvo: str) -> float:
    return pontuar_palavras(palavras(consulta), palavras(alvo))


def pontuar_digitando(consulta: str, alvo: str) -> float:
    """Como `pontuar`, mas as palavras ainda incompletas valem ("farinha de tri" acha "trigo")."""
    q, a = palavras(consulta), palavras(alvo)
    base = pontuar_palavras(q, a)
    if q and a and all(any(p.startswith(qp) for p in a) for qp in q):
        base = max(base, min(100.0, 85 + 15 * len(q) / len(a)))
    return base


def _melhor(consulta: str, nomes: Iterable[str], *, digitando: bool = False) -> tuple[float, str]:
    funcao = pontuar_digitando if digitando else pontuar
    melhor, quem = 0.0, ""
    for nome in nomes:
        pontos = funcao(consulta, nome)
        if pontos > melhor:
            melhor, quem = pontos, nome
    return melhor, quem


# ---------------------------------------------------------------- parecidos (cadastro)


def _semelhanca_de_nomes(a: str, b: str) -> float:
    """Nomes diferentes que provavelmente são o mesmo produto (para o cadastro)."""
    pa, pb = palavras(a), palavras(b)
    if not pa or not pb:
        return 0.0
    if pa == pb:
        return 100.0
    na, nb = _numeros(pa), _numeros(pb)
    if na and nb and na != nb:
        return 0.0
    f = fuzz.ratio(" ".join(sorted(pa)), " ".join(sorted(pb)))
    if f >= LIMIAR_PARECIDO:
        return float(f)
    if sao_parecidos(normalizar(a), normalizar(b)):
        return LIMIAR_PARECIDO
    return 0.0


def ingredientes_parecidos(
    ingredientes: Iterable[Ingrediente], nome: str, apelidos: Iterable[str] = ()
) -> list[tuple[Ingrediente, float]]:
    """Ingredientes ativos da organização que parecem o que se quer cadastrar, mais próximos antes.

    Compara o nome (e os apelidos) novos com o nome e os apelidos de cada um. Nome idêntico
    (normalizado) não entra: esse caso é recusado antes (`ja_existe`).
    """
    meus = [nome, *apelidos]
    nome_n = normalizar(nome)
    achados = []
    for i in ingredientes:
        if not i.ativo or i.nome_normalizado == nome_n:
            continue
        deles = [i.nome, *(i.apelidos or [])]
        pontos = max(_semelhanca_de_nomes(x, y) for x in meus for y in deles)
        if pontos >= LIMIAR_PARECIDO:
            achados.append((i, pontos))
    achados.sort(key=lambda par: (-par[1], par[0].nome.lower()))
    return achados


# ---------------------------------------------------------------- busca e sugestão


def _ingrediente_dict(visao: est.Visao, i: Ingrediente) -> dict:
    return {
        "id": i.id,
        "nome": i.nome,
        "categoria": i.categoria,
        "unidade_base": i.unidade_base,
        "apelidos": list(i.apelidos or []),
        "saldo": float(visao.saldo_do_ingrediente(i.id)),
        "itens": len(visao.itens_do_ingrediente(i.id)),
    }


def _catalogo_dict(c: CatalogoIngrediente) -> dict:
    return {
        "id": c.id,
        "nome": c.nome,
        "categoria": c.categoria,
        "unidade_base": c.unidade_base,
        "apelidos": list(c.apelidos or []),
    }


def _catalogo_ja_existe(c: CatalogoIngrediente, ativos: list[Ingrediente]) -> bool:
    """O catálogo só mostra o que a padaria ainda não tem (mesmo nome ou mesmas palavras)."""
    chave = chave_de_comparacao(c.nome)
    return any(
        i.nome_normalizado == c.nome_normalizado or chave_de_comparacao(i.nome) == chave
        for i in ativos
    )


def buscar(visao: est.Visao, catalogo: list[CatalogoIngrediente], q: str) -> dict:
    """`GET /ingredientes/busca`: o que a padaria já tem (por nome ou apelido) e, depois, o catálogo."""
    q = (q or "").strip()
    ativos = [i for i in visao.ingredientes.values() if i.ativo]
    if not q:
        da_padaria = sorted(ativos, key=lambda i: (i.categoria, i.nome.lower()))
        return {
            "q": q,
            "da_padaria": [_ingrediente_dict(visao, i) for i in da_padaria],
            "do_catalogo": [],
        }

    achados = []
    for i in ativos:
        pontos, nome = _melhor(q, [i.nome, *(i.apelidos or [])], digitando=True)
        if pontos >= LIMIAR_BUSCA:
            achados.append((pontos, i, nome))
    achados.sort(key=lambda t: (-t[0], t[1].nome.lower()))

    sugestoes = []
    for c in catalogo:
        if _catalogo_ja_existe(c, ativos):
            continue
        pontos, _nome = _melhor(q, [c.nome, *(c.apelidos or [])], digitando=True)
        if pontos >= LIMIAR_BUSCA:
            sugestoes.append((pontos, c))
    sugestoes.sort(key=lambda t: (-t[0], t[1].nome.lower()))

    da_padaria = []
    for pontos, i, nome in achados:
        d = _ingrediente_dict(visao, i)
        d["pontuacao"] = round(pontos, 1)
        d["achado_por"] = nome if normalizar(nome) != i.nome_normalizado else None
        da_padaria.append(d)
    do_catalogo = [
        {**_catalogo_dict(c), "pontuacao": round(p, 1)}
        for p, c in sugestoes[:MAX_CATALOGO_NA_BUSCA]
    ]
    return {"q": q, "da_padaria": da_padaria, "do_catalogo": do_catalogo}


# ---------------------------------------------------------------- qualificadores

# Termos que DIFERENCIAM ingredientes. Dentro de um mesmo grupo eles se excluem: "seco" não é "fresco",
# "com sal" não é "sem sal", "tipo 00" não é "tipo 1". Item sem qualificador não exclui ninguém.
_NUMERO_DE_FARINHA = r"(?<![\d,.])%s(?![\d,.])"
_QUALIFICADORES: tuple[tuple[str, str, str, bool], ...] = (
    # (grupo, termo, expressão sobre o texto sem acento e sem peso, só vale em texto de farinha)
    ("frescor", "seco", r"\bsec[oa]s?\b", False),
    ("frescor", "fresco", r"\bfresc[oa]s?\b", False),
    ("tipo", "00", _NUMERO_DE_FARINHA % "00", True),
    ("tipo", "0", _NUMERO_DE_FARINHA % "0", True),
    ("tipo", "1", _NUMERO_DE_FARINHA % "1", True),
    ("tipo", "integral", r"\bintegra(?:l|is)\b", False),
    ("tipo", "especial", r"\bespecia(?:l|is)\b", False),
    ("sal", "com sal", r"\bcom sal\b", False),
    ("sal", "sem sal", r"\bsem sal\b", False),
    ("cor", "branco", r"\bbranc[oa]s?\b", False),
    ("cor", "preto", r"\bpret[oa]s?\b", False),
    ("cor", "ao leite", r"\bao leite\b", False),
    ("cor", "meio amargo", r"\bmeio amargo\b", False),
    ("cor", "amargo", r"(?<!meio )\bamargo\b", False),
    ("forma", "em po", r"\bem po\b", False),
    ("forma", "em flocos", r"\bem flocos?\b", False),
    ("forma", "em grao", r"\bem graos?\b", False),
    ("acucar", "refinado", r"\brefinad[oa]s?\b", False),
    ("acucar", "cristal", r"\bcristal\b", False),
    ("acucar", "mascavo", r"\bmascav[oa]s?\b", False),
    ("acucar", "demerara", r"\bdemerara\b", False),
    # "Trigo sarraceno" (mourisco) NÃO é trigo: o termo é exclusivo, veja _EXCLUSIVOS.
    ("grao", "sarraceno", r"\b(?:sarracen[oa]|mourisc[oa]|buckwheat)s?\b", False),
)
# Qualificadores EXCLUSIVOS: se o item traz o termo, só serve quem também o traz (mesmo sem outro termo no
# mesmo grupo). "Farinha de trigo sarraceno" nunca sugere "Farinha de trigo ..." sem esse termo.
_EXCLUSIVOS: frozenset[tuple[str, str]] = frozenset({("grao", "sarraceno")})
_TEXTO_DE_FARINHA = re.compile(r"\b(?:tipo|farinha|trigo)\b")

Qualificadores = dict[str, frozenset[str]]


def qualificadores(texto: str) -> Qualificadores:
    """Os termos que diferenciam o ingrediente, por grupo: "Fermento biológico seco" -> {frescor: {seco}}."""
    limpo = sem_peso(texto)
    de_farinha = bool(_TEXTO_DE_FARINHA.search(limpo))
    achados: dict[str, set[str]] = {}
    for grupo, termo, expressao, so_farinha in _QUALIFICADORES:
        if so_farinha and not de_farinha:
            continue
        if re.search(expressao, limpo):
            achados.setdefault(grupo, set()).add(termo)
    return {g: frozenset(v) for g, v in achados.items()}


def exclusivo_quebrado(do_item: Qualificadores, do_candidato: Qualificadores) -> bool:
    """O item traz um termo exclusivo (sarraceno) que o candidato não traz."""
    return any(termo in do_item.get(g, ()) and termo not in do_candidato.get(g, ()) for g, termo in _EXCLUSIVOS)


def contradiz(do_item: Qualificadores, do_candidato: Qualificadores) -> bool:
    """O item e o candidato trazem termos diferentes no mesmo grupo (seco x fresco, com sal x sem sal...),
    ou o item traz um termo exclusivo (sarraceno) que o candidato não traz."""
    return exclusivo_quebrado(do_item, do_candidato) or any(
        g in do_candidato and do_item[g].isdisjoint(do_candidato[g]) for g in do_item
    )


def _unir(*varios: Qualificadores) -> Qualificadores:
    saida: dict[str, frozenset[str]] = {}
    for q in varios:
        for g, termos in q.items():
            saida[g] = saida.get(g, frozenset()) | termos
    return saida


# ---------------------------------------------------------------- sugestão

# Ordem de confiança (o motivo mostrado segue esta ordem).
NIVEL_ITEM_EXISTE = 1
NIVEL_NOME_NO_ITEM = 2
NIVEL_ITEM_PARECIDO = 3
NIVEL_SEMELHANCA = 4


def sugerir(
    visao: est.Visao,
    catalogo: list[CatalogoIngrediente],
    item: str,
    marca: str = "",
    *,
    so_catalogo: bool = False,
) -> list[dict]:
    """`GET /ingredientes/sugestao`: até 3 ingredientes prováveis para o item, cada um com o motivo.

    Ordem de confiança: 1) o item já existe (ingrediente travado); 2) o nome ou um apelido do
    ingrediente (da padaria ou do catálogo) está no nome do item, com os mesmos qualificadores;
    3) item parecido da padaria; 4) semelhança geral. Quem CONTRADIZ um qualificador do item
    (seco x fresco, com sal x sem sal, tipo 00 x tipo 1...) sai das sugestões.

    Só a 1ª sugestão pode vir com `destaque` (pré-preenchida para o clique ou o Enter), e só se for do
    nível 1 ou 2 e estiver claramente à frente da 2ª. Sem essa certeza nada fica em destaque.
    """
    item = (item or "").strip()
    if not normalizar(item):
        return []
    nome_n, marca_n = normalizar(item), normalizar(marca)
    texto_item = f"{item} {marca}".strip()
    palavras_item = palavras(texto_item)
    q_item = qualificadores(item)
    ativos = [i for i in visao.ingredientes.values() if i.ativo]
    ativos_por_id = {i.id: i for i in ativos}
    itens = [x for x in visao.itens.values() if x.ativo and x.ingrediente_id in ativos_por_id]

    # candidato = {"chave", "nivel", "espec", "pontos", "motivo", "ing", "cat", "travado"}
    candidatos: dict[tuple[str, object], dict] = {}
    # nomes de tudo o que pode ser sugerido (padaria e catálogo ainda não adotado), para saber se um termo
    # é genérico: "farinha de trigo" está dentro de "farinha de trigo tipo 00", "... tipo 1"...
    todos_os_nomes = [(("ing", i.id), palavras(i.nome)) for i in ativos] + [
        (("cat", c.id), palavras(c.nome)) for c in catalogo if not _catalogo_ja_existe(c, ativos)
    ]

    def generico(termo_palavras: frozenset[str], chave) -> bool:
        return any(
            outra != chave and termo_palavras < nome_palavras for outra, nome_palavras in todos_os_nomes
        )

    def propor(chave, nivel, pontos, motivo, ing=None, cat=None, espec=0, travado=False, generico=False):
        atual = candidatos.get(chave)
        if atual is not None and (
            atual["nivel"],
            atual["generico"],
            -atual["espec"],
            -atual["pontos"],
        ) <= (nivel, generico, -espec, -pontos):
            return
        origem = {
            NIVEL_ITEM_EXISTE: "item_existente",
            NIVEL_NOME_NO_ITEM: "ingrediente" if ing is not None else "catalogo",
            NIVEL_ITEM_PARECIDO: "item_parecido",
        }.get(nivel, "ingrediente" if ing is not None else "catalogo")
        candidatos[chave] = {
            "nivel": nivel,
            "espec": espec,
            "pontos": pontos,
            "generico": generico,
            "motivo": motivo,
            "ing": ing,
            "cat": cat,
            "travado": travado,
            "origem": origem,
        }

    def nomes_de(entidade) -> list[str]:
        return [entidade.nome, *(entidade.apelidos or [])]

    def avaliar(entidade, chave, *, eh_catalogo: bool, qualificadores_extra: Qualificadores | None = None):
        """Níveis 2 e 4 de um ingrediente da padaria ou do catálogo (se não contradiz o item)."""
        q_cand = _unir(qualificadores(entidade.nome), qualificadores_extra or {})
        if contradiz(q_item, q_cand):
            return
        melhor_termo = None
        for termo in nomes_de(entidade):
            pt = palavras(termo)
            if not pt or not pt <= palavras_item:
                continue
            if qualificadores(termo) != q_item:
                continue  # qualificadores diferentes (ou só de um lado): não é certeza
            if melhor_termo is None or len(pt) > melhor_termo[1]:
                melhor_termo = (termo, len(pt))
        ing = None if eh_catalogo else entidade
        cat = entidade if eh_catalogo else None
        sufixo = " (do catálogo)" if eh_catalogo else ""
        if melhor_termo is not None:
            termo, tamanho = melhor_termo
            if normalizar(termo) == entidade.nome_normalizado:
                motivo = f"O nome do item traz “{entidade.nome}”{sufixo}"
            else:
                motivo = f"O nome do item traz “{termo}”, outro nome deste{sufixo}"
            termo_palavras = palavras(termo)
            propor(
                chave,
                NIVEL_NOME_NO_ITEM,
                100.0,
                motivo,
                ing,
                cat,
                espec=tamanho,
                # só um APELIDO pode ser genérico (o nome inteiro de um ingrediente nunca é)
                generico=normalizar(termo) != entidade.nome_normalizado
                and generico(termo_palavras, chave),
            )
            return
        pontos, nome = _melhor(texto_item, nomes_de(entidade))
        if pontos >= LIMIAR_BUSCA:
            if eh_catalogo:
                motivo = (
                    "Sugerido pelo catálogo"
                    if normalizar(nome) == entidade.nome_normalizado
                    else f"Sugerido pelo catálogo: também chamado de “{nome}”"
                )
            else:
                motivo = (
                    "Parecido com o nome do item"
                    if normalizar(nome) == entidade.nome_normalizado
                    else f"Também chamado de “{nome}”"
                )
            propor(chave, NIVEL_SEMELHANCA, pontos, motivo, ing, cat)

    # 1) o item já existe
    for x in itens:
        if x.nome_normalizado == nome_n and x.marca_normalizada == marca_n:
            ing = ativos_por_id[x.ingrediente_id]
            propor(
                ("ing", ing.id),
                NIVEL_ITEM_EXISTE,
                100.0,
                "Este item já existe e usa este ingrediente",
                ing,
                travado=True,
            )
            break

    # 3) itens parecidos da padaria (sem contradizer o item nem o ingrediente que eles usam)
    parecidos = []
    for x in itens:
        pontos = _pontos_de_item(texto_item, f"{x.nome} {x.marca}".strip())
        if pontos >= LIMIAR_BUSCA:
            parecidos.append((pontos, x))
    parecidos.sort(key=lambda t: (-t[0], t[1].nome.lower()))
    for pontos, x in parecidos:
        ing = ativos_por_id[x.ingrediente_id]
        if contradiz(q_item, _unir(qualificadores(ing.nome), qualificadores(x.nome))):
            continue
        if exclusivo_quebrado(q_item, qualificadores(ing.nome)):
            continue  # um item ligado ao ingrediente errado não prova nada sobre o ingrediente
        rotulo = f"{x.nome} — {x.marca}" if x.marca else x.nome
        propor(("ing", ing.id), NIVEL_ITEM_PARECIDO, pontos, f"“{rotulo}” usa este", ing)

    # 2 e 4) ingredientes da padaria e do catálogo (o catálogo só mostra o que a padaria ainda não tem)
    for i in ativos:
        avaliar(i, ("ing", i.id), eh_catalogo=False)
    for c in catalogo:
        if not _catalogo_ja_existe(c, ativos):
            avaliar(c, ("cat", c.id), eh_catalogo=True)

    ordenados = sorted(
        candidatos.values(),
        key=lambda c: (
            c["nivel"],
            c["generico"] if c["nivel"] == NIVEL_NOME_NO_ITEM else 0,
            -c["espec"] if c["nivel"] == NIVEL_NOME_NO_ITEM else 0,
            0 if c["ing"] is not None else 1,
            -c["pontos"],
            (c["ing"].nome if c["ing"] is not None else c["cat"].nome).lower(),
        ),
    )

    destaque = False
    if ordenados and ordenados[0]["nivel"] <= NIVEL_NOME_NO_ITEM:
        primeiro = ordenados[0]
        segundo = ordenados[1] if len(ordenados) > 1 else None
        destaque = (
            primeiro["nivel"] == NIVEL_ITEM_EXISTE
            or segundo is None
            or segundo["nivel"] > NIVEL_NOME_NO_ITEM
            or (segundo["generico"] and not primeiro["generico"])
            or (
                primeiro["generico"] == segundo["generico"]
                and primeiro["espec"] > segundo["espec"]
            )
            or (
                primeiro["generico"] == segundo["generico"]
                and primeiro["espec"] == segundo["espec"]
                and primeiro["ing"] is not None
                and segundo["ing"] is None
            )
        )

    saida = []
    for posicao, c in enumerate(ordenados):
        if so_catalogo and c["cat"] is None:
            continue
        saida.append(
            {
                "origem": c["origem"],
                "nivel": c["nivel"],
                "motivo": c["motivo"],
                "travado": c["travado"],
                "destaque": bool(destaque and posicao == 0),
                "ingrediente": _ingrediente_dict(visao, c["ing"]) if c["ing"] is not None else None,
                "catalogo": _catalogo_dict(c["cat"]) if c["cat"] is not None else None,
            }
        )
    return saida[:MAX_SUGESTOES]


def _pontos_de_item(a: str, b: str) -> float:
    """Itens da padaria que se parecem: mesmas palavras em comum (marca à parte), não só o nome todo."""
    pa, pb = palavras(a), palavras(b)
    if not pa or not pb:
        return 0.0
    comuns = pa & pb
    menor = min(len(pa), len(pb))
    # mesmas palavras de produto + mesmo número (tipo 00 com tipo 00), marca à parte
    if len(comuns) >= 2 and len(comuns) / menor >= 2 / 3 and _numeros(pa) == _numeros(pb):
        return 70 + 30 * len(comuns) / max(len(pa), len(pb))
    return pontuar_palavras(pa, pb)

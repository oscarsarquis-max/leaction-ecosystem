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


def sugerir(
    visao: est.Visao,
    catalogo: list[CatalogoIngrediente],
    item: str,
    marca: str = "",
) -> list[dict]:
    """`GET /ingredientes/sugestao`: até 3 ingredientes prováveis para o item, cada um com o motivo.

    Ordem dos motivos: 1) o item já existe (ingrediente travado); 2) item parecido da padaria;
    3) ingrediente da padaria que combina por nome ou apelido; 4) entrada do catálogo.
    """
    item = (item or "").strip()
    if not normalizar(item):
        return []
    nome_n, marca_n = normalizar(item), normalizar(marca)
    ativos = [i for i in visao.ingredientes.values() if i.ativo]
    ativos_por_id = {i.id: i for i in ativos}
    saida: list[dict] = []
    usados: set = set()

    def adicionar(
        origem: str,
        motivo: str,
        ing: Ingrediente | None,
        cat: CatalogoIngrediente | None,
        travado=False,
    ):
        if ing is not None:
            if ing.id in usados:
                return
            usados.add(ing.id)
        saida.append(
            {
                "origem": origem,
                "motivo": motivo,
                "travado": travado,
                "ingrediente": _ingrediente_dict(visao, ing) if ing is not None else None,
                "catalogo": _catalogo_dict(cat) if cat is not None else None,
            }
        )

    # 1) o item já existe
    itens = [x for x in visao.itens.values() if x.ativo and x.ingrediente_id in ativos_por_id]
    for x in itens:
        if x.nome_normalizado == nome_n and x.marca_normalizada == marca_n:
            adicionar(
                "item_existente",
                "Este item já existe e usa este ingrediente",
                ativos_por_id[x.ingrediente_id],
                None,
                travado=True,
            )
            break

    # 2) itens parecidos da padaria
    texto_item = f"{item} {marca}".strip()
    parecidos = []
    for x in itens:
        pontos = _pontos_de_item(texto_item, f"{x.nome} {x.marca}".strip())
        if pontos >= LIMIAR_BUSCA:
            parecidos.append((pontos, x))
    parecidos.sort(key=lambda t: (-t[0], t[1].nome.lower()))
    for _pontos, x in parecidos:
        rotulo = f"{x.nome} — {x.marca}" if x.marca else x.nome
        adicionar("item_parecido", f"“{rotulo}” usa este", ativos_por_id[x.ingrediente_id], None)

    # 3) ingrediente da padaria que combina com o nome do item
    combinam = []
    for i in ativos:
        pontos, nome = _melhor(texto_item, [i.nome, *(i.apelidos or [])])
        if pontos >= LIMIAR_BUSCA:
            combinam.append((pontos, i, nome))
    combinam.sort(key=lambda t: (-t[0], t[1].nome.lower()))
    for _pontos, i, nome in combinam:
        motivo = (
            "Combina com o nome do item"
            if normalizar(nome) == i.nome_normalizado
            else f"Também chamado de “{nome}”"
        )
        adicionar("ingrediente", motivo, i, None)

    # 4) catálogo (só o que a padaria ainda não tem)
    do_catalogo = []
    for c in catalogo:
        if _catalogo_ja_existe(c, ativos):
            continue
        pontos, nome = _melhor(texto_item, [c.nome, *(c.apelidos or [])])
        if pontos >= LIMIAR_BUSCA:
            do_catalogo.append((pontos, c, nome))
    do_catalogo.sort(key=lambda t: (-t[0], t[1].nome.lower()))
    for _pontos, c, nome in do_catalogo:
        motivo = (
            "Sugerido pelo catálogo"
            if normalizar(nome) == c.nome_normalizado
            else f"Sugerido pelo catálogo: também chamado de “{nome}”"
        )
        adicionar("catalogo", motivo, None, c)

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

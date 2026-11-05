"""Catálogo de referência de ingredientes: leitura do YAML versionado, validação e carga no banco.

O catálogo é GLOBAL (nenhuma organização é dona dele) e só SUGERE. Quem o altera é o arquivo
`app/catalogo/catalogo-ingredientes.yaml` (nova versão), nunca a tela. A carga é idempotente, nunca
apaga e registra a versão. Qualquer erro no arquivo falha a carga inteira, com a linha do erro.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.busca import chave_de_comparacao
from app.domain.normalizacao import normalizar
from app.models.estoque import CATEGORIAS_INGREDIENTE, UNIDADES_BASE, CatalogoIngrediente

CAMINHO_PADRAO = Path(__file__).resolve().parent.parent / "catalogo" / "catalogo-ingredientes.yaml"
_CAMPOS = {"nome", "categoria", "unidade", "apelidos"}


class CatalogoInvalido(Exception):
    """O YAML não passou na validação. `erros` traz uma frase por problema, com a linha."""

    def __init__(self, erros: list[str]) -> None:
        self.erros = erros
        super().__init__("; ".join(erros))


@dataclass(frozen=True)
class EntradaCatalogo:
    linha: int
    nome: str
    categoria: str
    unidade: str
    apelidos: tuple[str, ...]


@dataclass(frozen=True)
class Catalogo:
    versao: int
    entradas: tuple[EntradaCatalogo, ...]


@dataclass
class ResultadoCarga:
    versao: int
    inseridos: int = 0
    alterados: int = 0
    iguais: int = 0
    fora_do_arquivo: int = 0


def ler_catalogo(caminho: Path | str = CAMINHO_PADRAO) -> Catalogo:
    caminho = Path(caminho)
    try:
        texto = caminho.read_text(encoding="utf-8")
    except OSError as exc:
        raise CatalogoInvalido([f"não consegui ler {caminho}: {exc}"]) from None
    return interpretar(texto)


def interpretar(texto: str) -> Catalogo:
    try:
        raiz = yaml.compose(texto)
        dados = yaml.safe_load(texto)
    except yaml.YAMLError as exc:
        marca = getattr(exc, "problem_mark", None)
        onde = f"linha {marca.line + 1}: " if marca is not None else ""
        raise CatalogoInvalido([f"{onde}YAML inválido ({getattr(exc, 'problem', exc)})"]) from None

    erros: list[str] = []
    if not isinstance(dados, dict):
        raise CatalogoInvalido(
            ["linha 1: o arquivo precisa ser um mapa com `versao` e `ingredientes`"]
        )

    versao = dados.get("versao")
    if not isinstance(versao, int) or isinstance(versao, bool) or versao < 1:
        erros.append("linha 1: `versao` precisa ser um número inteiro maior que zero")
        versao = 0
    lista = dados.get("ingredientes")
    if not isinstance(lista, list) or not lista:
        erros.append("linha 1: `ingredientes` precisa ser uma lista com pelo menos um ingrediente")
        raise CatalogoInvalido(erros)

    linhas = _linhas_da_lista(raiz, len(lista))
    entradas: list[EntradaCatalogo] = []
    for indice, bruto in enumerate(lista):
        linha = linhas[indice]
        if not isinstance(bruto, dict):
            erros.append(
                f"linha {linha}: cada ingrediente precisa ser um mapa (nome, categoria, unidade, apelidos)"
            )
            continue
        extras = set(bruto) - _CAMPOS
        if extras:
            erros.append(
                f"linha {linha}: campo desconhecido: {', '.join(sorted(map(str, extras)))}"
            )
        nome = bruto.get("nome")
        if not isinstance(nome, str) or not normalizar(nome) or len(nome.strip()) > 120:
            erros.append(f"linha {linha}: `nome` precisa ser um texto de 1 a 120 caracteres")
            continue
        categoria = bruto.get("categoria")
        if categoria not in CATEGORIAS_INGREDIENTE:
            erros.append(f"linha {linha}: categoria fora da lista: {categoria!r} (em “{nome}”)")
        unidade = bruto.get("unidade")
        if unidade not in UNIDADES_BASE:
            erros.append(f"linha {linha}: unidade fora de g, ml ou un: {unidade!r} (em “{nome}”)")
        apelidos = bruto.get("apelidos", [])
        if not isinstance(apelidos, list) or not all(
            isinstance(a, str) and normalizar(a) for a in apelidos
        ):
            erros.append(f"linha {linha}: `apelidos` precisa ser uma lista de textos (em “{nome}”)")
            apelidos = []
        entradas.append(
            EntradaCatalogo(
                linha=linha,
                nome=" ".join(nome.split()),
                categoria=str(categoria),
                unidade=str(unidade),
                apelidos=tuple(" ".join(a.split()) for a in apelidos),
            )
        )

    erros.extend(_conferir_nomes_e_apelidos(entradas))
    if erros:
        raise CatalogoInvalido(erros)
    return Catalogo(versao=versao, entradas=tuple(entradas))


def _linhas_da_lista(raiz, total: int) -> list[int]:
    """Linha (1-based) onde começa cada ingrediente da lista."""
    if isinstance(raiz, yaml.MappingNode):
        for chave, valor in raiz.value:
            if getattr(chave, "value", None) == "ingredientes" and isinstance(
                valor, yaml.SequenceNode
            ):
                return [no.start_mark.line + 1 for no in valor.value]
    return [1] * total


def _conferir_nomes_e_apelidos(entradas: list[EntradaCatalogo]) -> list[str]:
    erros: list[str] = []
    por_nome: dict[str, EntradaCatalogo] = {}
    for e in entradas:
        chave = normalizar(e.nome)
        anterior = por_nome.get(chave)
        if anterior is not None:
            erros.append(
                f"linha {e.linha}: nome repetido “{e.nome}” (já na linha {anterior.linha})"
            )
        else:
            por_nome[chave] = e

    # um termo (nome ou apelido) só pode levar a UM ingrediente
    donos: dict[str, EntradaCatalogo] = {}
    for e in entradas:
        for termo in (e.nome, *e.apelidos):
            chave = chave_de_comparacao(termo)
            if not chave:
                continue
            dono = donos.setdefault(chave, e)
            if dono is not e:
                erros.append(
                    f"linha {e.linha}: o termo “{termo}” aponta para dois nomes: "
                    f"“{dono.nome}” (linha {dono.linha}) e “{e.nome}”"
                )
    return erros


def carregar_catalogo(db: Session, caminho: Path | str = CAMINHO_PADRAO) -> ResultadoCarga:
    """Upsert pelo nome normalizado. Nunca apaga; o que já está igual não é tocado."""
    catalogo = ler_catalogo(caminho)
    existentes = {c.nome_normalizado: c for c in db.scalars(select(CatalogoIngrediente))}
    resultado = ResultadoCarga(versao=catalogo.versao)
    vistos: set[str] = set()
    for e in catalogo.entradas:
        chave = normalizar(e.nome)
        vistos.add(chave)
        atual = existentes.get(chave)
        if atual is None:
            db.add(
                CatalogoIngrediente(
                    nome=e.nome,
                    nome_normalizado=chave,
                    categoria=e.categoria,
                    unidade_base=e.unidade,
                    apelidos=list(e.apelidos),
                    versao=catalogo.versao,
                )
            )
            resultado.inseridos += 1
        elif (atual.nome, atual.categoria, atual.unidade_base, list(atual.apelidos or [])) != (
            e.nome,
            e.categoria,
            e.unidade,
            list(e.apelidos),
        ):
            atual.nome, atual.categoria, atual.unidade_base = e.nome, e.categoria, e.unidade
            atual.apelidos = list(e.apelidos)
            atual.versao = catalogo.versao
            resultado.alterados += 1
        else:
            resultado.iguais += 1
    resultado.fora_do_arquivo = sum(1 for chave in existentes if chave not in vistos)
    db.flush()
    return resultado

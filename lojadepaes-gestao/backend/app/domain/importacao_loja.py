"""Importação única dos produtos publicados da Loja para a Gestão.

Lê só nome, base da receita, id e a foto (`featured_image_id`) em `products`.
Não lê `showcase_slots`, `media_assets`, preço, pedido nem cliente.
Não escreve na Loja. Depois de gravado, o produto é da Gestão.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from uuid import UUID

import yaml
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.db.escopo import ativar_escopo
from app.domain.busca import LIMIAR_PARECIDO, _semelhanca_de_nomes
from app.domain.contexto import Contexto
from app.domain.normalizacao import normalizar
from app.domain.produtos import criar_familia, criar_produto
from app.models.produtos import Familia, Produto, Receita

CAMINHO_FAMILIAS = Path(__file__).resolve().parent.parent / "importacao" / "familias-vitrine.yaml"
URL_FOTO = "https://lojadepaes.com.br/api/v1/catalog/media/{id}"

# Só colunas que o gestao_reader já lê. Sem preço, sem vitrine, sem o arquivo da foto.
_SQL_PUBLICADOS = text(
    """
    SELECT p.id::text AS id,
           p.name AS nome,
           p.featured_image_id::text AS foto_id,
           rb.name AS base
    FROM products p
    LEFT JOIN recipe_bases rb ON rb.id = p.recipe_base_id
    WHERE p.editorial_status = 'published'
    ORDER BY p.sort_order, p.name
    """
)


@dataclass
class ItemLoja:
    id: UUID
    nome: str
    foto_id: UUID | None
    base: str | None


@dataclass
class LinhaPlano:
    nome: str
    familia: str
    tem_foto: bool
    ja_existe: bool
    motivo: str = ""


@dataclass
class ResultadoImportacao:
    linhas: list[LinhaPlano] = field(default_factory=list)
    familias_criadas: int = 0
    produtos_criados: int = 0
    ja_existiam: int = 0
    nao_criados: list[LinhaPlano] = field(default_factory=list)


def carregar_mapa(caminho: Path | None = None) -> dict[str, str]:
    arquivo = caminho or CAMINHO_FAMILIAS
    bruto = yaml.safe_load(arquivo.read_text(encoding="utf-8")) or {}
    mapa: dict[str, str] = {}
    for item in bruto.get("produtos") or []:
        nome = " ".join(str(item.get("produto") or "").split())
        familia = " ".join(str(item.get("familia") or "").split())
        if nome and familia:
            mapa[nome] = familia
    return mapa


def propor_familia(nome: str, base: str | None, mapa: dict[str, str]) -> str:
    if nome in mapa:
        return mapa[nome]
    texto = normalizar(f"{nome} {base or ''}")
    if "focaccia" in texto:
        return "Focaccia"
    if "rustico" in texto:
        return "Pão Rústico"
    if "sovado" in texto:
        return "Pão Sovado"
    return "a decidir"


def ler_publicados(loja: Session) -> list[ItemLoja]:
    itens = []
    for linha in loja.execute(_SQL_PUBLICADOS).mappings():
        foto = linha["foto_id"]
        itens.append(
            ItemLoja(
                id=UUID(str(linha["id"])),
                nome=" ".join(str(linha["nome"]).split()),
                foto_id=UUID(str(foto)) if foto else None,
                base=(linha["base"] or None),
            )
        )
    return itens


def _url_foto(foto_id: UUID | None) -> str | None:
    if foto_id is None:
        return None
    return URL_FOTO.format(id=foto_id)


def _ja_por_origem(db: Session, origem: UUID) -> Produto | None:
    return db.scalar(select(Produto).where(Produto.origem_loja_id == origem))


def _conflito_nome(db: Session, nome: str) -> str:
    nome_n = normalizar(nome)
    igual = db.scalar(select(Produto).where(Produto.nome_normalizado == nome_n, Produto.ativo.is_(True)))
    if igual is not None:
        return f"já existe “{igual.nome}”"
    for produto in db.scalars(select(Produto).where(Produto.ativo.is_(True))):
        if produto.origem_loja_id is not None:
            continue
        if _semelhanca_de_nomes(nome, produto.nome) >= LIMIAR_PARECIDO:
            return f"parecido com “{produto.nome}”"
    return ""


def importar_vitrine(
    ctx: Contexto,
    loja: Session,
    *,
    executar: bool,
    caminho: Path | None = None,
) -> ResultadoImportacao:
    """Dry-run quando executar é falso. Nunca altera um produto que o Oscar já editou."""
    ativar_escopo(ctx.db, ctx.organizacao.id)
    mapa = carregar_mapa(caminho)
    resultado = ResultadoImportacao()
    for item in ler_publicados(loja):
        familia = propor_familia(item.nome, item.base, mapa)
        existente = _ja_por_origem(ctx.db, item.id)
        if existente is not None:
            linha = LinhaPlano(item.nome, familia, item.foto_id is not None, True, "origem")
            resultado.linhas.append(linha)
            resultado.ja_existiam += 1
            continue
        if familia == "a decidir":
            linha = LinhaPlano(item.nome, familia, item.foto_id is not None, False, "família a decidir")
            resultado.linhas.append(linha)
            resultado.nao_criados.append(linha)
            continue
        motivo = _conflito_nome(ctx.db, item.nome)
        if motivo:
            linha = LinhaPlano(item.nome, familia, item.foto_id is not None, True, motivo)
            resultado.linhas.append(linha)
            resultado.nao_criados.append(linha)
            continue
        linha = LinhaPlano(item.nome, familia, item.foto_id is not None, False)
        resultado.linhas.append(linha)
        if not executar:
            continue
        nome_n = normalizar(familia)
        ja_familia = ctx.db.scalar(select(Familia).where(Familia.nome_normalizado == nome_n))
        familia_row = criar_familia(ctx, familia)
        if ja_familia is None:
            resultado.familias_criadas += 1
        produto = criar_produto(
            ctx,
            nome=item.nome,
            modalidade="produzido",
            uso_venda=True,
            uso_componente=False,
            familia_id=familia_row.id,
            unidade_venda="un",
        )
        produto.foto_url = _url_foto(item.foto_id)
        produto.origem_loja_id = item.id
        ctx.db.flush()
        receita = ctx.db.scalar(select(Receita).where(Receita.produto_id == produto.id))
        if receita is None or receita.situacao != "rascunho":
            raise RuntimeError("o produto produzido precisa nascer com receita em rascunho")
        resultado.produtos_criados += 1
    return resultado

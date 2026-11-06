"""Higiene do texto que o padeiro cola. Não executa instrução vinda desse texto."""

from __future__ import annotations

import re

MAX_DESCRICAO = 4000

INJECTION_MARKERS = (
    "ignore as regras",
    "ignore previous",
    "ignore all rules",
    "system prompt",
    "revelar segredo",
    "aws_secret",
    "mostre a chave",
)


def limpar_descricao(valor: object) -> str:
    texto = str(valor or "").replace("\r\n", "\n")
    texto = re.sub(r"(?is)<(?:script|style|iframe)[^>]*>.*?</(?:script|style|iframe)>", " ", texto)
    texto = re.sub(r"(?i)ignore (?:all |as |the )?previous.+", " ", texto)
    texto = "\n".join(linha.strip() for linha in texto.split("\n"))
    texto = texto.strip()
    if not texto:
        raise ValueError("vazia")
    if len(texto) > MAX_DESCRICAO:
        raise ValueError("longa")
    return texto


def parece_injecao(texto: str) -> bool:
    baixo = texto.casefold()
    return any(marca in baixo for marca in INJECTION_MARKERS)

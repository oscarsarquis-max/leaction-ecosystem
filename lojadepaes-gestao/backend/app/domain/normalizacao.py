"""Nomes: normalização (para unicidade) e "parecido" (para não duplicar sem querer).

`normalizar` tira acento, caixa, pontuação e espaços repetidos. Duas grafias com a mesma forma
normalizada são o MESMO nome (a API recusa a repetição). `parecidos` é outra coisa: nomes diferentes
que provavelmente são a mesma coisa ("Farinha Trigo" e "Farinha de trigo"). Esses precisam de uma
decisão de uma pessoa: usar o existente ou criar novo.
"""

from __future__ import annotations

import re
import unicodedata
from difflib import SequenceMatcher

_NAO_ALFANUM = re.compile(r"[^a-z0-9]+")
PALAVRAS_VAZIAS = frozenset(
    {"de", "da", "do", "das", "dos", "e", "com", "em", "para", "tipo", "a", "o"}
)
LIMITE_SEMELHANCA = 0.85


def normalizar(texto: str) -> str:
    decomposto = unicodedata.normalize("NFKD", texto or "")
    sem_acento = "".join(c for c in decomposto if not unicodedata.combining(c))
    return _NAO_ALFANUM.sub(" ", sem_acento.lower()).strip()


def _singular(palavra: str) -> str:
    if len(palavra) > 3 and palavra.endswith("oes"):
        return palavra[:-3] + "ao"
    if len(palavra) > 3 and palavra.endswith("s") and not palavra.endswith("ss"):
        return palavra[:-1]
    return palavra


def _chave(normalizado: str) -> str:
    palavras = [_singular(p) for p in normalizado.split() if p not in PALAVRAS_VAZIAS]
    return " ".join(sorted(palavras))


def sao_parecidos(a_normalizado: str, b_normalizado: str) -> bool:
    """Nomes diferentes (já normalizados) que provavelmente são o mesmo."""
    if not a_normalizado or not b_normalizado or a_normalizado == b_normalizado:
        return False
    chave_a, chave_b = _chave(a_normalizado), _chave(b_normalizado)
    if chave_a and chave_a == chave_b:
        return True
    return SequenceMatcher(None, a_normalizado, b_normalizado).ratio() >= LIMITE_SEMELHANCA


def rotulo_padrao_lote(data_iso: str, sequencia: int) -> str:
    """`E20261102-01`: E + data da entrada + número do lote do dia."""
    return f"E{data_iso.replace('-', '')}-{sequencia:02d}"

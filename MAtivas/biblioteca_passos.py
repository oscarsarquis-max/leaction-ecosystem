"""
Biblioteca de passos canônicos das Metodologias Inov-ativas (Andrea Filatro).

Fonte: database/biblioteca_passos.json (gerada a partir do texto Faça Fácil).
Quando a metodologia tem cadastro, título e descrição saem LITERAIS —
sem adaptação, resumo ou reescrita pela IA.
"""

from __future__ import annotations

import json
import re
import unicodedata
from functools import lru_cache
from pathlib import Path

_JSON_PATH = Path(__file__).resolve().parent / "database" / "biblioteca_passos.json"


def _chave(metodologia: str) -> str:
    texto = metodologia or ""
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return texto.strip().lower()


def _chave_normalizada(metodologia: str) -> str:
    """Remove acentos, sufixos entre parênteses e espaços extras."""
    chave = _chave(metodologia)
    chave = re.sub(r"\s*\([^)]*\)\s*", " ", chave)
    chave = re.sub(r"\s+", " ", chave).strip()
    return chave


@lru_cache(maxsize=1)
def _carregar_biblioteca() -> dict[str, list[dict]]:
    if not _JSON_PATH.is_file():
        return {}
    data = json.loads(_JSON_PATH.read_text(encoding="utf-8"))
    # Normaliza chaves do JSON
    return {_chave(k): v for k, v in data.items() if isinstance(v, list)}


# Compat: testes / imports antigos
BIBLIOTECA_PASSOS: dict[str, list[dict]] = {}  # preenchido lazy via property-like load


def _bib() -> dict[str, list[dict]]:
    global BIBLIOTECA_PASSOS
    BIBLIOTECA_PASSOS = _carregar_biblioteca()
    return BIBLIOTECA_PASSOS


def obter_passos_biblioteca(metodologia: str) -> list[dict] | None:
    """Retorna passos canônicos da metodologia ou None se não cadastrada."""
    if not metodologia:
        return None

    bib = _bib()
    chave = _chave(metodologia)
    chave_limpa = _chave_normalizada(metodologia)

    for candidata in (chave, chave_limpa):
        if candidata and candidata in bib:
            return bib[candidata]

    for k, passos in bib.items():
        if chave_limpa.startswith(k) or k.startswith(chave_limpa):
            return passos
        if len(chave_limpa) >= 8 and (k in chave_limpa or chave_limpa in k):
            return passos

    return None


def formatar_passos_para_prompt(passos: list[dict]) -> str:
    """Serializa passos canônicos para injeção no prompt da IA."""
    payload = [
        {
            "ordem": i + 1,
            "imperativo": p["imperativo"],
            "descricao_base": p.get("descricao_base", ""),
        }
        for i, p in enumerate(passos)
    ]
    return json.dumps(payload, ensure_ascii=False, indent=2)


def passos_canonicos_para_roteiro(
    canonicos: list[dict], gerados: list[dict] | None = None
) -> list[dict]:
    """Monta passos do roteiro com texto LITERAL da biblioteca.

    A IA pode contribuir apenas com estimativa de tempo; título e descrição
    vêm sempre de imperativo + descricao_base.
    """
    gerados = gerados or []
    resultado = []
    for i, canon in enumerate(canonicos):
        gen = gerados[i] if i < len(gerados) else {}
        resultado.append(
            {
                "titulo": canon["imperativo"],
                "descricao": canon.get("descricao_base", ""),
                "tempo": (gen.get("tempo") or "").strip(),
            }
        )
    return resultado


def mesclar_passos_gerados(canonicos: list[dict], gerados: list[dict]) -> list[dict]:
    """Alias: garante texto canônico literal (não usa descrição da IA)."""
    return passos_canonicos_para_roteiro(canonicos, gerados)

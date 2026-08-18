"""Lookup exato Mativas — SOMENTE Crystal Ball (experimental).

Não registra em services/context7/. Não é alcançável pelo state_engine.
"""

from __future__ import annotations

import json
import re
import unicodedata
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

_CORPUS_PATH = (
    Path(__file__).resolve().parents[2]
    / "context7"
    / "corpus"
    / "mativas_base_conhecimento.json"
)


def _norm(s: str) -> str:
    texto = unicodedata.normalize("NFKD", s or "")
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    texto = texto.strip().lower()
    texto = re.sub(r"\s*\([^)]*\)\s*", " ", texto)
    return re.sub(r"\s+", " ", texto).strip()


@lru_cache(maxsize=1)
def _load_corpus() -> list[dict[str, Any]]:
    if not _CORPUS_PATH.is_file():
        return []
    data = json.loads(_CORPUS_PATH.read_text(encoding="utf-8"))
    items = data.get("metodologias") if isinstance(data, dict) else data
    if not isinstance(items, list):
        return []
    return [m for m in items if isinstance(m, dict)]


def list_metodologias() -> list[str]:
    return [
        str(m.get("metodologia") or "")
        for m in _load_corpus()
        if m.get("metodologia")
    ]


def lookup_metodologia_exata(nome: str) -> Optional[dict[str, Any]]:
    """Match exato (case/acento-insensitive) pelo campo metodologia.

    Sem embeddings / sem fuzzy além de normalização de acentos e
    remoção de sufixo entre parênteses.
    """
    alvo = _norm(nome)
    if not alvo:
        return None
    for item in _load_corpus():
        cand = _norm(str(item.get("metodologia") or ""))
        if cand == alvo:
            return {k: v for k, v in item.items() if not str(k).startswith("_")}
    return None


def build_context7_shadow_artifact(
    *,
    metodologia: str,
    user_prompt: str,
) -> dict[str, Any]:
    """Artefato no formato consumível por synthesize/L4 via context7_hits."""
    registro = lookup_metodologia_exata(metodologia)
    if registro is None:
        raise LookupError(
            f"Metodologia não encontrada no corpus Mativas (lookup exato): {metodologia!r}. "
            f"Disponíveis: {', '.join(list_metodologias()[:8])}…"
        )

    passos = registro.get("passos") if isinstance(registro.get("passos"), list) else []
    passos_txt: list[str] = []
    for p in passos:
        if not isinstance(p, dict):
            continue
        ordem = p.get("ordem")
        imp = p.get("imperativo") or ""
        desc = p.get("descricao_base") or ""
        passos_txt.append(f"{ordem}. {imp}\n{desc}")

    resumo = (
        f"Metodologia: {registro.get('metodologia')}\n"
        f"Grupo: {registro.get('grupo')}\n"
        f"Público preferencial: {registro.get('publico_preferencial')}\n"
        f"Modalidade preferencial: {registro.get('modalidade_preferencial')}\n"
        f"Problemas combinados: {registro.get('problemas_combinados')}\n"
        f"Observação automação: {registro.get('observacao_automatizacao')}\n"
        f"Biblioteca de Passos (LITERAL — copiar imperativo/descricao_base sem parafrasear):\n"
        + "\n\n".join(passos_txt)
    )

    hit = {
        "titulo": registro.get("metodologia"),
        "tipo": "MATIVAS_METODOLOGIA",
        "resumo": resumo,
        "score": 1.0,
        "mativas_registro": registro,
        "passos": passos,
    }

    inner = {
        "search_keywords": [metodologia, "mativas", "biblioteca_passos"],
        "context7_hits": [hit],
        "mativas_registro": registro,
        "passos": passos,
        "metodologia_fixada": registro.get("metodologia"),
        "user_prompt": user_prompt,
        "provider": "crystal_ball.experimental_providers.mativas_lookup",
    }

    return {
        "status": "success",
        "phase": "context7_mativas",
        "capability": "context7_search",
        "artifact_data": inner,
        "inputs_used": [],
        "meta": {
            "experimental": True,
            "is_simulation": True,
            "provider": "crystal_ball.mativas_lookup",
            "n_passos": len(passos),
            "corpus_path": str(_CORPUS_PATH).replace("\\", "/"),
        },
        "is_simulation": True,
    }

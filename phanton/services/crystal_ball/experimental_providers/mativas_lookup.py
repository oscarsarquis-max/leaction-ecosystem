"""Lookup exato Mativas — SOMENTE Crystal Ball (experimental).

Wrapper fino sobre generic_corpus_lookup. API pública preservada.
Não registra em services/context7/. Não é alcançável pelo state_engine.
"""

from __future__ import annotations

from typing import Any, Optional

from services.crystal_ball.experimental_providers.generic_corpus_lookup import (
    MATIVAS_SCHEMA_CONFIG,
    build_context7_shadow_artifact_from_registro,
    list_chave_values,
    lookup_by_chave,
)

_PROVIDER = "crystal_ball.experimental_providers.mativas_lookup"


def list_metodologias() -> list[str]:
    return list_chave_values(MATIVAS_SCHEMA_CONFIG)


def lookup_metodologia_exata(nome: str) -> Optional[dict[str, Any]]:
    """Match exato (case/acento-insensitive) pelo campo metodologia.

    Sem embeddings / sem fuzzy além de normalização de acentos e
    remoção de sufixo entre parênteses.
    """
    return lookup_by_chave(MATIVAS_SCHEMA_CONFIG, nome)


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
    art = build_context7_shadow_artifact_from_registro(
        registro=registro,
        schema_config=MATIVAS_SCHEMA_CONFIG,
        user_prompt=user_prompt,
        provider=_PROVIDER,
        phase="context7_mativas",
    )
    # Preserva meta.provider histórico esperado pelos testes/UI
    meta = art.get("meta") if isinstance(art.get("meta"), dict) else {}
    meta = {**meta, "provider": "crystal_ball.mativas_lookup"}
    art["meta"] = meta
    inner = art.get("artifact_data") if isinstance(art.get("artifact_data"), dict) else {}
    if isinstance(inner, dict):
        inner["provider"] = _PROVIDER
        art["artifact_data"] = inner
    return art

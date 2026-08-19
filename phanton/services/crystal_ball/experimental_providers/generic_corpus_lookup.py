"""Lookup genérico de corpus — Crystal Ball experimental.

Parametrizado por schema_config. Sem escrita em sistemas externos.
"""

from __future__ import annotations

import json
import re
import unicodedata
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

_SERVICES_ROOT = Path(__file__).resolve().parents[2]


def norm_chave(s: str) -> str:
    texto = unicodedata.normalize("NFKD", s or "")
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    texto = texto.strip().lower()
    texto = re.sub(r"\s*\([^)]*\)\s*", " ", texto)
    return re.sub(r"\s+", " ", texto).strip()


def resolve_fonte_path(schema_config: dict[str, Any]) -> Path:
    rel = str(schema_config.get("fonte_path") or "").strip().replace("\\", "/")
    if not rel:
        raise ValueError("schema_config.fonte_path obrigatório para upload_json")
    path = Path(rel)
    if not path.is_absolute():
        path = _SERVICES_ROOT / rel
    return path


@lru_cache(maxsize=8)
def _load_json_records(path_str: str, lista_raiz: str) -> tuple[dict[str, Any], ...]:
    path = Path(path_str)
    if not path.is_file():
        return tuple()
    data = json.loads(path.read_text(encoding="utf-8"))
    if lista_raiz and isinstance(data, dict):
        items = data.get(lista_raiz)
    else:
        items = data
    if not isinstance(items, list):
        return tuple()
    return tuple(m for m in items if isinstance(m, dict))


def load_corpus_records(schema_config: dict[str, Any]) -> list[dict[str, Any]]:
    tipo = str(schema_config.get("tipo_fonte_efetivo") or "upload_json")
    if tipo == "conexao_db_readonly":
        # Reservado — nesta Sprint só JSON file/path.
        raise NotImplementedError(
            "conexao_db_readonly ainda não implementada no lookup genérico"
        )
    path = resolve_fonte_path(schema_config)
    lista_raiz = str(schema_config.get("lista_raiz") or "")
    return list(_load_json_records(str(path), lista_raiz))


def list_chave_values(schema_config: dict[str, Any]) -> list[str]:
    chave = str(schema_config.get("campo_chave") or "").strip()
    if not chave:
        return []
    return [
        str(item.get(chave) or "")
        for item in load_corpus_records(schema_config)
        if item.get(chave)
    ]


def lookup_by_chave(
    schema_config: dict[str, Any],
    valor: str,
) -> Optional[dict[str, Any]]:
    """Match exato (case/acento-insensitive) pelo campo_chave do schema."""
    chave = str(schema_config.get("campo_chave") or "").strip()
    if not chave:
        return None
    alvo = norm_chave(valor)
    if not alvo:
        return None
    for item in load_corpus_records(schema_config):
        cand = norm_chave(str(item.get(chave) or ""))
        if cand == alvo:
            return {k: v for k, v in item.items() if not str(k).startswith("_")}
    return None


def build_context7_shadow_artifact_from_registro(
    *,
    registro: dict[str, Any],
    schema_config: dict[str, Any],
    user_prompt: str,
    provider: str,
    phase: str = "context7_corpus",
) -> dict[str, Any]:
    """Artefato no formato consumível por synthesize/L4 via context7_hits."""
    chave = str(schema_config.get("campo_chave") or "chave")
    titulo = registro.get(chave) or registro.get("titulo") or "registro"
    passos = registro.get("passos") if isinstance(registro.get("passos"), list) else []

    linhas: list[str] = [f"{chave}: {titulo}"]
    for campo in schema_config.get("campos_sinteticos") or []:
        if campo in registro and registro.get(campo) not in (None, ""):
            linhas.append(f"{campo}: {registro.get(campo)}")

    # Campos de cópia literal — destacar no resumo
    for spec in schema_config.get("campos_copia_literal") or []:
        if not isinstance(spec, dict):
            continue
        campo = str(spec.get("campo") or "")
        if campo == "passos" and passos:
            passos_txt: list[str] = []
            for p in passos:
                if not isinstance(p, dict):
                    continue
                ordem = p.get("ordem")
                imp = p.get("imperativo") or p.get("titulo") or ""
                desc = p.get("descricao_base") or p.get("descricao") or ""
                passos_txt.append(f"{ordem}. {imp}\n{desc}")
            linhas.append(
                "Biblioteca de Passos (LITERAL — copiar imperativo/descricao_base "
                "sem parafrasear):\n" + "\n\n".join(passos_txt)
            )
        elif campo and campo in registro:
            linhas.append(f"{campo} (LITERAL): {registro.get(campo)}")

    resumo = "\n".join(linhas)
    hit = {
        "titulo": titulo,
        "tipo": "CORPUS_REGISTRO",
        "resumo": resumo,
        "score": 1.0,
        "corpus_registro": registro,
        "passos": passos,
    }
    inner = {
        "search_keywords": [str(titulo), "corpus", provider],
        "context7_hits": [hit],
        "corpus_registro": registro,
        "mativas_registro": registro,  # compat consumidores Mativas existentes
        "passos": passos,
        "metodologia_encontrada": registro.get("metodologia") or titulo,
        "user_prompt": user_prompt,
        "provider": provider,
        "schema_campo_chave": chave,
    }
    fonte = str(schema_config.get("fonte_path") or "")
    return {
        "status": "success",
        "phase": phase,
        "capability": "context7_search",
        "artifact_data": inner,
        "inputs_used": [],
        "meta": {
            "experimental": True,
            "is_simulation": True,
            "provider": provider,
            "n_passos": len(passos),
            "corpus_path": fonte.replace("\\", "/"),
            "campo_chave": chave,
            "chave_valor": titulo,
        },
        "is_simulation": True,
    }


# --- Config canônico Mativas (primeira entrada do registro genérico) ---

MATIVAS_SCHEMA_CONFIG: dict[str, Any] = {
    "campo_chave": "metodologia",
    "lista_raiz": "metodologias",
    "fonte_path": "context7/corpus/mativas_base_conhecimento.json",
    "campos_copia_literal": [
        {
            "campo": "passos",
            "tipo": "lista_passos",
            "titulo_keys": ["imperativo", "titulo", "titulo_do_card"],
            "descricao_keys": [
                "descricao_base",
                "descricao",
                "como_executar_detalhado",
            ],
        }
    ],
    "campos_sinteticos": [
        "grupo",
        "problemas_combinados",
        "observacao_automatizacao",
        "publico_preferencial",
        "publico_complementar",
        "modalidade_preferencial",
        "modalidades_alternativas",
    ],
}

MATIVAS_SLUG = "mativas"

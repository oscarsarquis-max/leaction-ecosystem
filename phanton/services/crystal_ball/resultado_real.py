"""Ingestão de resultado real colado manualmente — comparação campo-a-campo."""

from __future__ import annotations

import json
import re
import uuid
from typing import Any, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from services.crystal_ball.campo_compare import compare_literal_fields
from services.crystal_ball.corpora import (
    compute_corpus_content_hash,
    get_corpus,
    lookup_corpus_record,
)
from services.crystal_ball.models import CrystalCicloMelhoria, CrystalResultadoReal
from services.crystal_ball.passos_compare import extract_passos_from_artifact


class ResultadoRealError(Exception):
    pass


def _parse_payload(raw: Any) -> dict[str, Any]:
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        text = raw.strip()
        if not text:
            raise ResultadoRealError("payload vazio")
        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                return parsed
            if isinstance(parsed, list):
                return {"passos": parsed}
        except json.JSONDecodeError:
            return {"delivery": text}
    raise ResultadoRealError("payload deve ser JSON objeto, lista de passos ou texto")


def _inconsistencia_ciclo_prompt(
    versao_prompt_origem: str, numero_ciclo: Optional[int]
) -> Optional[str]:
    """Aviso se o texto do prompt sugerir 'antes de ciclo' mas for associado a ciclo > 0."""
    if numero_ciclo is None:
        return None
    txt = (versao_prompt_origem or "").strip().lower()
    if not txt:
        return None
    before = (
        "antes de qualquer ciclo" in txt
        or "antes do ciclo" in txt
        or "sem ciclo" in txt
        or "pre-ciclo" in txt
        or "pré-ciclo" in txt
    )
    if before and int(numero_ciclo) >= 1:
        return (
            f"versao_prompt_origem sugere estado anterior a ciclos, "
            f"mas numero_ciclo={numero_ciclo}"
        )
    # "após ciclo N" vs numero_ciclo M
    m = re.search(r"ciclo\s*(\d+)", txt)
    if m:
        declared = int(m.group(1))
        if declared != int(numero_ciclo):
            return (
                f"versao_prompt_origem menciona ciclo {declared}, "
                f"mas numero_ciclo={numero_ciclo}"
            )
    return None


def registrar_resultado_real(
    db: Session,
    *,
    corpus_id: UUID | str,
    chave_valor: str,
    payload: Any,
    versao_prompt_origem: str,
    desafio_texto: Optional[str] = None,
    numero_ciclo: Optional[int] = None,
    versao_corpus_simulacao: Optional[str] = None,
) -> dict[str, Any]:
    corpus = get_corpus(db, corpus_id)
    chave = (chave_valor or "").strip()
    if not chave:
        raise ResultadoRealError("chave_valor obrigatória (ex.: metodologia)")

    prompt_v = (versao_prompt_origem or "").strip()
    if not prompt_v:
        raise ResultadoRealError(
            "versao_prompt_origem obrigatória "
            "(ex.: 'prompt mestre v3, aplicado após ciclo 2')"
        )

    registro = lookup_corpus_record(corpus, chave)
    if registro is None:
        raise ResultadoRealError(
            f"valor não encontrado no corpus para "
            f"{corpus.schema_config.get('campo_chave')}: {chave!r}"
        )

    # Garante hash atualizado
    versao_corpus = (corpus.versao_atual or "").strip() or compute_corpus_content_hash(
        dict(corpus.schema_config or {})
    )
    if not (corpus.versao_atual or "").strip():
        corpus.versao_atual = versao_corpus
        db.add(corpus)

    data = _parse_payload(payload)
    if extract_passos_from_artifact(data):
        gen_art: Any = data
    else:
        gen_art = {"artifact_data": data, **data}

    comparison = compare_literal_fields(
        generated_artifact=gen_art,
        reference_record=registro,
        schema_config=dict(corpus.schema_config or {}),
    )
    comparison["fonte"] = "resultado_real_colado"
    comparison["chave_valor"] = registro.get(
        corpus.schema_config.get("campo_chave") or "metodologia"
    )
    comparison["versao_corpus"] = versao_corpus
    comparison["aplicacao_origem"] = corpus.aplicacao_origem or "Mativas"

    avisos: list[str] = []
    inconsistencia = _inconsistencia_ciclo_prompt(prompt_v, numero_ciclo)
    if inconsistencia:
        avisos.append(inconsistencia)

    confiavel = True
    if versao_corpus_simulacao and versao_corpus_simulacao != versao_corpus:
        confiavel = False
        avisos.append(
            "Atenção: comparando versões diferentes do corpus "
            f"(simulação={versao_corpus_simulacao[:16]}… vs "
            f"atual={versao_corpus[:16]}…)."
        )
        comparison["comparavel_com_confianca"] = False
        comparison["motivo_nao_confiavel"] = "versao_corpus divergente"
    else:
        comparison["comparavel_com_confianca"] = True

    if avisos:
        comparison["avisos_integridade"] = avisos

    row = CrystalResultadoReal(
        id=uuid.uuid4(),
        corpus_id=corpus.id,
        chave_valor=str(
            registro.get(corpus.schema_config.get("campo_chave") or "metodologia")
            or chave
        ),
        desafio_texto=(desafio_texto or "").strip() or None,
        payload=data,
        comparison=comparison,
        numero_ciclo=numero_ciclo,
        versao_corpus=versao_corpus,
        versao_prompt_origem=prompt_v,
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    return {
        "id": str(row.id),
        "corpus_id": str(corpus.id),
        "aplicacao_origem": corpus.aplicacao_origem or "Mativas",
        "chave_valor": row.chave_valor,
        "desafio_texto": row.desafio_texto,
        "numero_ciclo": row.numero_ciclo,
        "versao_corpus": row.versao_corpus,
        "versao_prompt_origem": row.versao_prompt_origem,
        "comparison": row.comparison,
        "avisos_integridade": avisos,
        "comparavel_com_confianca": confiavel,
        "disclaimer": (
            "Resultado colado manualmente. Sem conexão automática ao sistema "
            "de origem do corpus nem a qualquer sistema externo."
        ),
    }

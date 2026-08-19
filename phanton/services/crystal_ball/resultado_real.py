"""Ingestão de resultado real colado manualmente — comparação campo-a-campo."""

from __future__ import annotations

import json
import uuid
from typing import Any, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from services.crystal_ball.campo_compare import compare_literal_fields
from services.crystal_ball.corpora import get_corpus, lookup_corpus_record
from services.crystal_ball.models import CrystalResultadoReal
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
            # Tratar como markdown/texto de entrega
            return {"delivery": text}
    raise ResultadoRealError("payload deve ser JSON objeto, lista de passos ou texto")


def registrar_resultado_real(
    db: Session,
    *,
    corpus_id: UUID | str,
    chave_valor: str,
    payload: Any,
    desafio_texto: Optional[str] = None,
    numero_ciclo: Optional[int] = None,
) -> dict[str, Any]:
    corpus = get_corpus(db, corpus_id)
    chave = (chave_valor or "").strip()
    if not chave:
        raise ResultadoRealError("chave_valor obrigatória (ex.: metodologia)")

    registro = lookup_corpus_record(corpus, chave)
    if registro is None:
        raise ResultadoRealError(
            f"valor não encontrado no corpus para "
            f"{corpus.schema_config.get('campo_chave')}: {chave!r}"
        )

    data = _parse_payload(payload)
    # Normaliza para o comparador (mesma forma da simulação)
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
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    return {
        "id": str(row.id),
        "corpus_id": str(corpus.id),
        "chave_valor": row.chave_valor,
        "desafio_texto": row.desafio_texto,
        "numero_ciclo": row.numero_ciclo,
        "comparison": row.comparison,
        "disclaimer": (
            "Resultado colado manualmente. Sem conexão automática ao Mativas "
            "ou qualquer sistema externo."
        ),
    }

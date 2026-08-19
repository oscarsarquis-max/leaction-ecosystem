"""Registro de corpora Crystal Ball + seed Mativas."""

from __future__ import annotations

import uuid
from typing import Any, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from services.crystal_ball.experimental_providers.generic_corpus_lookup import (
    MATIVAS_SCHEMA_CONFIG,
    MATIVAS_SLUG,
    lookup_by_chave,
)
from services.crystal_ball.models import CrystalCorpus


def ensure_mativas_corpus(db: Session) -> CrystalCorpus:
    row = db.query(CrystalCorpus).filter(CrystalCorpus.slug == MATIVAS_SLUG).first()
    if row:
        return row
    row = CrystalCorpus(
        id=uuid.uuid4(),
        slug=MATIVAS_SLUG,
        nome="Mativas — Biblioteca de Passos",
        tipo_fonte="upload_json",
        schema_config=dict(MATIVAS_SCHEMA_CONFIG),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_corpus(db: Session, corpus_id: UUID | str) -> CrystalCorpus:
    ensure_mativas_corpus(db)
    if isinstance(corpus_id, str):
        try:
            cid = UUID(corpus_id)
            row = db.get(CrystalCorpus, cid)
            if row:
                return row
        except ValueError:
            pass
        row = db.query(CrystalCorpus).filter(CrystalCorpus.slug == corpus_id).first()
        if row:
            return row
        raise LookupError(f"corpus não encontrado: {corpus_id}")
    row = db.get(CrystalCorpus, corpus_id)
    if not row:
        raise LookupError(f"corpus não encontrado: {corpus_id}")
    return row


def list_corpora(db: Session) -> list[dict[str, Any]]:
    ensure_mativas_corpus(db)
    rows = db.query(CrystalCorpus).order_by(CrystalCorpus.nome).all()
    return [
        {
            "id": str(r.id),
            "slug": r.slug,
            "nome": r.nome,
            "tipo_fonte": r.tipo_fonte,
            "schema_config": r.schema_config,
        }
        for r in rows
    ]


def register_corpus(
    db: Session,
    *,
    slug: str,
    nome: str,
    tipo_fonte: str,
    schema_config: dict[str, Any],
) -> CrystalCorpus:
    existing = db.query(CrystalCorpus).filter(CrystalCorpus.slug == slug).first()
    if existing:
        raise ValueError(f"slug já existe: {slug}")
    if tipo_fonte not in ("upload_json", "conexao_db_readonly"):
        raise ValueError("tipo_fonte inválido")
    if not schema_config.get("campo_chave"):
        raise ValueError("schema_config.campo_chave obrigatório")
    row = CrystalCorpus(
        id=uuid.uuid4(),
        slug=slug.strip(),
        nome=nome.strip(),
        tipo_fonte=tipo_fonte,
        schema_config=schema_config,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def lookup_corpus_record(
    corpus: CrystalCorpus, chave_valor: str
) -> Optional[dict[str, Any]]:
    cfg = dict(corpus.schema_config or {})
    return lookup_by_chave(cfg, chave_valor)

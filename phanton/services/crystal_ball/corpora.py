"""Registro de corpora Crystal Ball + seed Mativas + hash de versão."""

from __future__ import annotations

import hashlib
import uuid
from typing import Any, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from services.crystal_ball.experimental_providers.generic_corpus_lookup import (
    MATIVAS_SCHEMA_CONFIG,
    MATIVAS_SLUG,
    lookup_by_chave,
    resolve_fonte_path,
)
from services.crystal_ball.models import CrystalCorpus


def compute_corpus_content_hash(schema_config: dict[str, Any]) -> str:
    """sha256 do conteúdo em fonte_path (ou do schema serializado se sem arquivo)."""
    try:
        path = resolve_fonte_path(schema_config)
        if path.is_file():
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            return f"sha256:{digest}"
    except Exception:
        pass
    # Fallback estável: hash do schema_config canônico
    blob = repr(sorted((schema_config or {}).items())).encode("utf-8")
    return f"sha256:{hashlib.sha256(blob).hexdigest()}"


def refresh_corpus_versao(db: Session, corpus: CrystalCorpus) -> str:
    versao = compute_corpus_content_hash(dict(corpus.schema_config or {}))
    corpus.versao_atual = versao
    db.add(corpus)
    db.commit()
    db.refresh(corpus)
    return versao


def ensure_mativas_corpus(db: Session) -> CrystalCorpus:
    row = db.query(CrystalCorpus).filter(CrystalCorpus.slug == MATIVAS_SLUG).first()
    if row:
        dirty = False
        if not (row.aplicacao_origem or "").strip():
            row.aplicacao_origem = "Mativas"
            dirty = True
        if not (row.versao_atual or "").strip():
            row.versao_atual = compute_corpus_content_hash(
                dict(row.schema_config or MATIVAS_SCHEMA_CONFIG)
            )
            dirty = True
        if dirty:
            db.add(row)
            db.commit()
            db.refresh(row)
        return row
    schema = dict(MATIVAS_SCHEMA_CONFIG)
    row = CrystalCorpus(
        id=uuid.uuid4(),
        slug=MATIVAS_SLUG,
        nome="Mativas — Biblioteca de Passos",
        tipo_fonte="upload_json",
        schema_config=schema,
        aplicacao_origem="Mativas",
        versao_atual=compute_corpus_content_hash(schema),
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


def _corpus_public(r: CrystalCorpus) -> dict[str, Any]:
    return {
        "id": str(r.id),
        "slug": r.slug,
        "nome": r.nome,
        "tipo_fonte": r.tipo_fonte,
        "schema_config": r.schema_config,
        "aplicacao_origem": r.aplicacao_origem or "Mativas",
        "versao_atual": r.versao_atual,
    }


def list_corpora(db: Session) -> list[dict[str, Any]]:
    ensure_mativas_corpus(db)
    rows = db.query(CrystalCorpus).order_by(CrystalCorpus.nome).all()
    return [_corpus_public(r) for r in rows]


def register_corpus(
    db: Session,
    *,
    slug: str,
    nome: str,
    tipo_fonte: str,
    schema_config: dict[str, Any],
    aplicacao_origem: str,
) -> CrystalCorpus:
    existing = db.query(CrystalCorpus).filter(CrystalCorpus.slug == slug).first()
    if existing:
        raise ValueError(f"slug já existe: {slug}")
    if tipo_fonte not in ("upload_json", "conexao_db_readonly"):
        raise ValueError("tipo_fonte inválido")
    if not schema_config.get("campo_chave"):
        raise ValueError("schema_config.campo_chave obrigatório")
    app = (aplicacao_origem or "").strip()
    if not app:
        raise ValueError("aplicacao_origem obrigatória")
    schema = dict(schema_config)
    row = CrystalCorpus(
        id=uuid.uuid4(),
        slug=slug.strip(),
        nome=nome.strip(),
        tipo_fonte=tipo_fonte,
        schema_config=schema,
        aplicacao_origem=app,
        versao_atual=compute_corpus_content_hash(schema),
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

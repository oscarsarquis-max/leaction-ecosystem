"""Porta local de ingestão. Sem crawler, HTTP público ou LLM."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import date, datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.knowledge_grounding.models import (
    KnowledgeFragment,
    KnowledgeSource,
    KnowledgeSourceVersion,
)
from app.modules.knowledge_grounding.rules import (
    CONTENT_USAGE_KINDS,
    KnowledgeError,
    assert_source_identity,
)

MAX_CONTENT_BYTES = 262_144
MAX_TITLE = 500
MAX_FRAGMENT_CHARS = 2_000
ALLOWED_MIME = frozenset({"text/plain", "text/markdown"})
HASH_EMPTY = hashlib.sha256(b"").hexdigest()


class IngestError(KnowledgeError):
    """Conteúdo ou metadado recusado na ingestão local."""


@dataclass(frozen=True)
class IngestRequest:
    source_kind: str
    authority_level: str
    title: str
    content: str
    organization_id: UUID | None = None
    issuer_or_author: str | None = None
    jurisdiction: str | None = None
    canonical_url: str | None = None
    language: str = "pt-BR"
    license_or_usage_notes: str | None = None
    mime_type: str = "text/plain"
    version_label: str = "v1"
    publication_date: date | None = None
    effective_from: date | None = None
    effective_until: date | None = None
    regulatory_status: str = "not_applicable"
    content_usage_kind: str = "not_applicable"
    created_by_user_id: UUID | None = None
    heading: str | None = None


@dataclass
class IngestResult:
    source: KnowledgeSource
    version: KnowledgeSourceVersion
    fragments: list[KnowledgeFragment]
    created_source: bool
    created_version: bool
    content_hash: str


def content_sha256(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def sanitize_metadata(value: str | None, *, max_len: int, label: str) -> str | None:
    if value is None:
        return None
    cleaned = value.replace("\x00", "")
    cleaned = re.sub(r"[\r\n\t]+", " ", cleaned).strip()
    if not cleaned:
        return None
    if len(cleaned) > max_len:
        raise IngestError(f"{label} excede o limite")
    return cleaned


def sanitize_content(value: str) -> str:
    cleaned = value.replace("\x00", "").replace("\r\n", "\n").replace("\r", "\n")
    if not cleaned.strip():
        raise IngestError("conteúdo vazio")
    encoded = cleaned.encode("utf-8")
    if len(encoded) > MAX_CONTENT_BYTES:
        raise IngestError("conteúdo excede o limite")
    return cleaned


def segment_text(content: str) -> list[tuple[int, str, str]]:
    blocks = [part.strip() for part in re.split(r"\n\s*\n", content) if part.strip()]
    if not blocks:
        blocks = [content.strip()]
    fragments: list[tuple[int, str, str]] = []
    sequence = 1
    for block in blocks:
        start = 0
        while start < len(block):
            chunk = block[start : start + MAX_FRAGMENT_CHARS].strip()
            if chunk:
                fragments.append((sequence, f"paragrafo-{sequence}", chunk))
                sequence += 1
            start += MAX_FRAGMENT_CHARS
    return fragments


def _find_source(session: Session, request: IngestRequest) -> KnowledgeSource | None:
    stmt = select(KnowledgeSource).where(
        KnowledgeSource.source_kind == request.source_kind,
        KnowledgeSource.title == request.title,
    )
    if request.organization_id is None:
        stmt = stmt.where(KnowledgeSource.organization_id.is_(None))
    else:
        stmt = stmt.where(KnowledgeSource.organization_id == request.organization_id)
    if request.canonical_url:
        stmt = stmt.where(KnowledgeSource.canonical_url == request.canonical_url)
    return session.scalars(stmt).first()


def _find_version_by_hash(
    session: Session, source_id: UUID, content_hash: str
) -> KnowledgeSourceVersion | None:
    return session.scalars(
        select(KnowledgeSourceVersion).where(
            KnowledgeSourceVersion.knowledge_source_id == source_id,
            KnowledgeSourceVersion.content_hash == content_hash,
        )
    ).first()


def ingest(session: Session, request: IngestRequest) -> IngestResult:
    if request.mime_type not in ALLOWED_MIME:
        raise IngestError("tipo de conteúdo não permitido")
    title = sanitize_metadata(request.title, max_len=MAX_TITLE, label="título")
    if not title:
        raise IngestError("título obrigatório")
    content = sanitize_content(request.content)
    digest = content_sha256(content)
    issuer = sanitize_metadata(request.issuer_or_author, max_len=300, label="emissor")
    jurisdiction = sanitize_metadata(request.jurisdiction, max_len=120, label="jurisdição")
    url = sanitize_metadata(request.canonical_url, max_len=1_000, label="url")
    notes = sanitize_metadata(
        request.license_or_usage_notes, max_len=2_000, label="condição de uso"
    )
    heading = sanitize_metadata(request.heading, max_len=300, label="título do trecho")
    usage = request.content_usage_kind
    if usage not in CONTENT_USAGE_KINDS:
        raise IngestError("uso de conteúdo inválido")
    if request.source_kind == "recipe" and usage == "not_applicable":
        raise IngestError("receita exige citação, resumo ou estrutura extraída")
    if request.source_kind == "normative":
        usage = "citation"
    review_status = "pending"

    source = _find_source(session, request)
    created_source = False
    if source is None:
        source = KnowledgeSource(
            organization_id=request.organization_id,
            source_kind=request.source_kind,
            authority_level=request.authority_level,
            title=title,
            issuer_or_author=issuer,
            jurisdiction=jurisdiction,
            canonical_url=url,
            language=request.language,
            license_or_usage_notes=notes,
            status="active",
            release_state="private" if request.organization_id else "restricted",
            created_by_user_id=request.created_by_user_id,
        )
        assert_source_identity(source)
        session.add(source)
        session.flush()
        created_source = True
    else:
        assert_source_identity(source)

    existing = _find_version_by_hash(session, source.id, digest)
    if existing is not None:
        fragments = list(
            session.scalars(
                select(KnowledgeFragment)
                .where(KnowledgeFragment.knowledge_source_version_id == existing.id)
                .order_by(KnowledgeFragment.sequence)
            )
        )
        return IngestResult(
            source=source,
            version=existing,
            fragments=fragments,
            created_source=created_source,
            created_version=False,
            content_hash=digest,
        )

    version = KnowledgeSourceVersion(
        knowledge_source_id=source.id,
        organization_id=source.organization_id,
        version_label=request.version_label,
        publication_date=request.publication_date,
        effective_from=request.effective_from,
        effective_until=request.effective_until,
        regulatory_status=request.regulatory_status,
        content_hash=digest,
        mime_type=request.mime_type,
        language=request.language,
        content_usage_kind=usage,
        review_status=review_status,
    )
    session.add(version)
    session.flush()

    fragments: list[KnowledgeFragment] = []
    for sequence, locator_value, chunk in segment_text(content):
        fragment = KnowledgeFragment(
            knowledge_source_version_id=version.id,
            organization_id=source.organization_id,
            sequence=sequence,
            locator_type="paragraph",
            locator_value=locator_value,
            heading=heading,
            content=chunk,
            content_hash=content_sha256(chunk),
        )
        session.add(fragment)
        fragments.append(fragment)
    session.flush()
    return IngestResult(
        source=source,
        version=version,
        fragments=fragments,
        created_source=created_source,
        created_version=True,
        content_hash=digest,
    )


def release_global_source(source: KnowledgeSource) -> None:
    if source.organization_id is not None:
        raise KnowledgeError("somente fonte global pode ser liberada")
    source.release_state = "released"


def review_source_version(
    version: KnowledgeSourceVersion,
    *,
    decision: str,
    reviewed_by_user_id: UUID | None,
) -> None:
    if decision not in {"reviewed", "rejected"}:
        raise KnowledgeError("decisão de revisão inválida")
    if version.review_status != "pending":
        raise KnowledgeError("versão já revisada")
    version.review_status = decision
    version.reviewed_by_user_id = reviewed_by_user_id
    version.reviewed_at = datetime.now(timezone.utc)


def revoke_source_version(version: KnowledgeSourceVersion, *, superseded: bool = False) -> None:
    version.regulatory_status = "superseded" if superseded else "revoked"

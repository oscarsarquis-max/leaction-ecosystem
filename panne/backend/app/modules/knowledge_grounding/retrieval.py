"""Recuperação determinística em PostgreSQL. Sem LLM e sem embeddings."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy import cast, func, literal, or_, select
from sqlalchemy.dialects.postgresql import REGCONFIG
from sqlalchemy.orm import Session

from app.modules.knowledge_grounding.models import (
    GroundingCitation,
    GroundingQuery,
    GroundingResult,
    KnowledgeFragment,
    KnowledgeSource,
    KnowledgeSourceTag,
    KnowledgeSourceVersion,
    KnowledgeTag,
)
from app.modules.knowledge_grounding.rules import (
    AUTHORITY_RANK,
    DEFAULT_NORMATIVE_AUTHORITY,
    DEFAULT_NORMATIVE_REGULATORY,
    DEFAULT_NORMATIVE_REVIEW,
    REGULATORY_RANK,
    REVIEW_RANK,
    KnowledgeError,
    source_visible_to,
    version_is_effective_on,
)

RETRIEVAL_ALGORITHM = "deterministic_pg_fts_pt"
RETRIEVAL_VERSION = "1"
SECRET_PATTERN = (
    r"(?i)(password|passwd|secret|api[_-]?key|token|authorization)\s*[:=]"
)


class RetrievalError(KnowledgeError):
    """Consulta de grounding recusada."""


@dataclass(frozen=True)
class RetrievalRequest:
    query_text: str | None = None
    organization_id: UUID | None = None
    source_kinds: tuple[str, ...] | None = None
    authority_levels: tuple[str, ...] | None = None
    jurisdiction: str | None = None
    applicability_date: date | None = None
    regulatory_statuses: tuple[str, ...] | None = None
    review_statuses: tuple[str, ...] | None = None
    tag_codes: tuple[str, ...] | None = None
    include_historical: bool = False
    include_consultation: bool = False
    normative_defaults: bool = True
    limit: int = 20
    created_by_user_id: UUID | None = None


@dataclass(frozen=True)
class RankedFragment:
    fragment: KnowledgeFragment
    source: KnowledgeSource
    version: KnowledgeSourceVersion
    rank: int
    score: Decimal
    selection_reason: dict


@dataclass
class RetrievalBundle:
    query: GroundingQuery
    results: list[GroundingResult] = field(default_factory=list)
    citations: list[GroundingCitation] = field(default_factory=list)


def _reject_secrets(query_text: str | None) -> str | None:
    if query_text is None:
        return None
    cleaned = query_text.replace("\x00", "").strip()
    if not cleaned:
        return None
    if len(cleaned) > 4_000:
        raise RetrievalError("consulta textual excede o limite")
    import re

    if re.search(SECRET_PATTERN, cleaned):
        raise RetrievalError("consulta não pode registrar segredo")
    return cleaned


def _normative_statuses(request: RetrievalRequest) -> tuple[str, ...]:
    if request.regulatory_statuses:
        return request.regulatory_statuses
    statuses = list(DEFAULT_NORMATIVE_REGULATORY)
    if request.include_historical:
        statuses.extend(["superseded", "revoked"])
    if request.include_consultation:
        statuses.append("public_consultation")
    return tuple(statuses)


def _tsquery(query_text: str):
    return func.plainto_tsquery(
        cast(literal("portuguese"), REGCONFIG),
        func.panne_unaccent_immutable(query_text),
    )


def _text_score(session: Session, fragment_id: UUID, query_text: str) -> Decimal:
    rank = session.scalar(
        select(func.ts_rank_cd(KnowledgeFragment.search_vector, _tsquery(query_text))).where(
            KnowledgeFragment.id == fragment_id
        )
    )
    return Decimal(str(rank or 0))


def retrieve(session: Session, request: RetrievalRequest) -> list[RankedFragment]:
    query_text = _reject_secrets(request.query_text)
    when = request.applicability_date or date.today()
    stmt = (
        select(KnowledgeFragment, KnowledgeSource, KnowledgeSourceVersion)
        .join(
            KnowledgeSourceVersion,
            KnowledgeFragment.knowledge_source_version_id == KnowledgeSourceVersion.id,
        )
        .join(
            KnowledgeSource,
            KnowledgeSourceVersion.knowledge_source_id == KnowledgeSource.id,
        )
        .where(KnowledgeSource.status == "active")
    )
    released_global = (KnowledgeSource.organization_id.is_(None)) & (
        KnowledgeSource.release_state == "released"
    )
    if request.organization_id is None:
        stmt = stmt.where(released_global)
    else:
        stmt = stmt.where(
            or_(
                KnowledgeSource.organization_id == request.organization_id,
                released_global,
            )
        )

    if request.source_kinds:
        stmt = stmt.where(KnowledgeSource.source_kind.in_(request.source_kinds))
    if request.tag_codes:
        stmt = (
            stmt.join(
                KnowledgeSourceTag,
                KnowledgeSourceTag.knowledge_source_id == KnowledgeSource.id,
            )
            .join(KnowledgeTag, KnowledgeSourceTag.knowledge_tag_id == KnowledgeTag.id)
            .where(KnowledgeTag.code.in_(request.tag_codes), KnowledgeTag.status == "active")
        )
    if query_text:
        stmt = stmt.where(KnowledgeFragment.search_vector.op("@@")(_tsquery(query_text)))

    rows = list(session.execute(stmt).all())
    ranked: list[tuple[Decimal, int, int, int, str, RankedFragment]] = []
    for fragment, source, version in rows:
        if not source_visible_to(source, request.organization_id):
            continue
        if source.organization_id is not None and source.organization_id != request.organization_id:
            continue
        is_normative = source.source_kind == "normative"
        if is_normative and request.normative_defaults:
            authority = request.authority_levels or DEFAULT_NORMATIVE_AUTHORITY
            review = request.review_statuses or DEFAULT_NORMATIVE_REVIEW
            regulatory = _normative_statuses(request)
            if source.authority_level not in authority:
                continue
            if version.review_status not in review:
                continue
            if version.regulatory_status not in regulatory:
                continue
            if request.jurisdiction and source.jurisdiction != request.jurisdiction:
                continue
            if not version_is_effective_on(version, when):
                continue
            if (
                version.regulatory_status == "public_consultation"
                and not request.include_consultation
            ):
                continue
        else:
            if request.authority_levels and source.authority_level not in request.authority_levels:
                continue
            if request.review_statuses and version.review_status not in request.review_statuses:
                continue
            if (
                request.regulatory_statuses
                and version.regulatory_status not in request.regulatory_statuses
            ):
                continue
            if request.jurisdiction and source.jurisdiction not in {request.jurisdiction, None}:
                continue
        text_score = _text_score(session, fragment.id, query_text) if query_text else Decimal("0")
        authority = AUTHORITY_RANK[source.authority_level]
        review = REVIEW_RANK[version.review_status]
        regulatory = REGULATORY_RANK[version.regulatory_status]
        score = (text_score * Decimal("100")) + Decimal(authority)
        reason = {
            "algorithm": RETRIEVAL_ALGORITHM,
            "version": RETRIEVAL_VERSION,
            "text_matched": bool(query_text),
            "authority_level": source.authority_level,
            "regulatory_status": version.regulatory_status,
            "review_status": version.review_status,
            "jurisdiction": source.jurisdiction,
            "effective_from": version.effective_from.isoformat()
            if version.effective_from
            else None,
            "effective_until": version.effective_until.isoformat()
            if version.effective_until
            else None,
            "score_is_not_probability": True,
        }
        ranked.append(
            (
                text_score,
                authority,
                regulatory,
                review,
                str(fragment.id),
                RankedFragment(
                    fragment=fragment,
                    source=source,
                    version=version,
                    rank=0,
                    score=score,
                    selection_reason=reason,
                ),
            )
        )
    ranked.sort(key=lambda item: (-item[0], -item[1], -item[2], -item[3], item[4]))
    selected: list[RankedFragment] = []
    for index, item in enumerate(ranked[: request.limit], start=1):
        row = item[5]
        selected.append(
            RankedFragment(
                fragment=row.fragment,
                source=row.source,
                version=row.version,
                rank=index,
                score=row.score,
                selection_reason=row.selection_reason,
            )
        )
    return selected


def persist_grounding(
    session: Session,
    request: RetrievalRequest,
    ranked: list[RankedFragment],
) -> RetrievalBundle:
    query_text = _reject_secrets(request.query_text)
    when = request.applicability_date or date.today()
    if request.normative_defaults and request.source_kinds == ("normative",):
        if not request.jurisdiction:
            raise RetrievalError("consulta normativa exige jurisdição")
        if request.applicability_date is None:
            raise RetrievalError("consulta normativa exige data de aplicabilidade")
    filters = {
        "source_kinds": list(request.source_kinds) if request.source_kinds else None,
        "authority_levels": list(request.authority_levels) if request.authority_levels else None,
        "jurisdiction": request.jurisdiction,
        "regulatory_statuses": list(request.regulatory_statuses)
        if request.regulatory_statuses
        else None,
        "review_statuses": list(request.review_statuses) if request.review_statuses else None,
        "tag_codes": list(request.tag_codes) if request.tag_codes else None,
        "include_historical": request.include_historical,
        "include_consultation": request.include_consultation,
        "normative_defaults": request.normative_defaults,
    }
    query = GroundingQuery(
        organization_id=request.organization_id,
        query_text=query_text,
        filters=filters,
        retrieval_algorithm=RETRIEVAL_ALGORITHM,
        retrieval_version=RETRIEVAL_VERSION,
        applicability_date=when if request.source_kinds == ("normative",) else request.applicability_date,
        created_by_user_id=request.created_by_user_id,
    )
    session.add(query)
    session.flush()
    bundle = RetrievalBundle(query=query)
    accessed_at = datetime.now(timezone.utc)
    for row in ranked:
        if not source_visible_to(row.source, request.organization_id):
            raise RetrievalError("fragmento de outra organização rejeitado")
        if (
            row.source.organization_id is not None
            and row.source.organization_id != request.organization_id
        ):
            raise RetrievalError("fragmento de outra organização rejeitado")
        result = GroundingResult(
            grounding_query_id=query.id,
            knowledge_fragment_id=row.fragment.id,
            rank=row.rank,
            score=row.score,
            selection_reason=row.selection_reason,
        )
        session.add(result)
        session.flush()
        citation = GroundingCitation(
            grounding_result_id=result.id,
            source_title=row.source.title,
            version_label=row.version.version_label,
            issuer_or_author=row.source.issuer_or_author,
            canonical_url=row.source.canonical_url,
            locator_type=row.fragment.locator_type,
            locator_value=row.fragment.locator_value,
            version_content_hash=row.version.content_hash,
            fragment_content_hash=row.fragment.content_hash,
            accessed_at=accessed_at,
        )
        session.add(citation)
        bundle.results.append(result)
        bundle.citations.append(citation)
    session.flush()
    return bundle


def retrieve_and_persist(session: Session, request: RetrievalRequest) -> RetrievalBundle:
    return persist_grounding(session, request, retrieve(session, request))

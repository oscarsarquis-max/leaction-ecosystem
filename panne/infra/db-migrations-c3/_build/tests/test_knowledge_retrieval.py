from datetime import date
from decimal import Decimal

import pytest
from app.modules.knowledge_grounding.ingest import (
    IngestRequest,
    ingest,
    release_global_source,
    review_source_version,
)
from app.modules.knowledge_grounding.models import KnowledgeSourceTag
from app.modules.knowledge_grounding.retrieval import (
    RETRIEVAL_ALGORITHM,
    RankedFragment,
    RetrievalError,
    RetrievalRequest,
    persist_grounding,
    retrieve,
    retrieve_and_persist,
)
from sqlalchemy.orm import Session
from tests import helpers


def _reviewed_norm(
    session: Session,
    *,
    title: str,
    content: str,
    version_label: str,
    regulatory_status: str = "in_force",
    effective_from=date(2020, 10, 8),
    reviewer_email: str,
):
    result = ingest(
        session,
        IngestRequest(
            source_kind="normative",
            authority_level="official",
            title=title,
            issuer_or_author="Anvisa",
            jurisdiction="BR",
            content=content,
            regulatory_status=regulatory_status,
            effective_from=effective_from,
            version_label=version_label,
        ),
    )
    release_global_source(result.source)
    actor = helpers.user(session, reviewer_email)
    review_source_version(result.version, decision="reviewed", reviewed_by_user_id=actor.id)
    session.flush()
    return result


def test_recipe_retrieval_is_not_normative(db_session: Session) -> None:
    org = helpers.org(db_session, "org-kr-rec")
    recipe = ingest(
        db_session,
        IngestRequest(
            source_kind="recipe",
            authority_level="curated",
            title="Pão caseiro citado",
            content="Misture farinha, água e fermento.",
            content_usage_kind="summary",
            canonical_url="https://example.test/pao",
            issuer_or_author="Padaria exemplo",
            license_or_usage_notes="resumo autorizado; sem republicação integral",
            organization_id=org.id,
        ),
    )
    found = retrieve(
        db_session,
        RetrievalRequest(
            organization_id=org.id,
            source_kinds=("recipe",),
            query_text="farinha",
        ),
    )
    assert [row.fragment.id for row in found] == [recipe.fragments[0].id]
    assert found[0].source.source_kind == "recipe"


def test_in_force_norm_and_filters_and_stable_rank(db_session: Session) -> None:
    first = _reviewed_norm(
        db_session,
        title="RDC 429/2020",
        content="A rotulagem nutricional declara energia e nutrientes.",
        version_label="429",
        reviewer_email="rev-429@panne.test",
    )
    second = _reviewed_norm(
        db_session,
        title="IN 75/2020",
        content="A rotulagem nutricional complementar detalha porções técnicas.",
        version_label="75",
        reviewer_email="rev-75@panne.test",
    )
    tag = helpers.knowledge_tag(db_session, "rotulagem", category="norm", display_name="Rotulagem")
    db_session.add(
        KnowledgeSourceTag(knowledge_source_id=first.source.id, knowledge_tag_id=tag.id)
    )
    db_session.flush()
    found = retrieve(
        db_session,
        RetrievalRequest(
            source_kinds=("normative",),
            jurisdiction="BR",
            applicability_date=date(2026, 8, 22),
            query_text="rotulagem nutricional",
            tag_codes=("rotulagem",),
        ),
    )
    assert [row.source.id for row in found] == [first.source.id]
    both = retrieve(
        db_session,
        RetrievalRequest(
            source_kinds=("normative",),
            jurisdiction="BR",
            applicability_date=date(2026, 8, 22),
            query_text="rotulagem nutricional",
        ),
    )
    ranks = [row.rank for row in both]
    assert ranks == list(range(1, len(both) + 1))
    assert {row.source.id for row in both} == {first.source.id, second.source.id}
    assert both[0].selection_reason["score_is_not_probability"] is True
    again = retrieve(
        db_session,
        RetrievalRequest(
            source_kinds=("normative",),
            jurisdiction="BR",
            applicability_date=date(2026, 8, 22),
            query_text="rotulagem nutricional",
        ),
    )
    assert [row.fragment.id for row in again] == [row.fragment.id for row in both]


def test_citation_is_reconstructible_and_empty_has_no_evidence(db_session: Session) -> None:
    result = _reviewed_norm(
        db_session,
        title="RDC 727/2022",
        content="Rotulagem geral de alimentos embalados.",
        version_label="727",
        reviewer_email="rev-727@panne.test",
    )
    request = RetrievalRequest(
        source_kinds=("normative",),
        jurisdiction="BR",
        applicability_date=date(2026, 8, 22),
        query_text="alimentos embalados",
    )
    bundle = retrieve_and_persist(db_session, request)
    assert bundle.query.retrieval_algorithm == RETRIEVAL_ALGORITHM
    assert bundle.query.filters["jurisdiction"] == "BR"
    assert bundle.citations[0].source_title == "RDC 727/2022"
    assert bundle.citations[0].version_content_hash == result.version.content_hash
    assert bundle.citations[0].fragment_content_hash == result.fragments[0].content_hash
    assert bundle.citations[0].locator_value == result.fragments[0].locator_value
    empty = persist_grounding(
        db_session,
        RetrievalRequest(
            source_kinds=("normative",),
            jurisdiction="BR",
            applicability_date=date(2026, 8, 22),
            query_text="inexistente-xyz",
        ),
        [],
    )
    assert empty.results == []
    assert empty.citations == []
    assert empty.query.id is not None


def test_foreign_fragment_rejected_on_persist(db_session: Session) -> None:
    org_a = helpers.org(db_session, "org-kr-a")
    org_b = helpers.org(db_session, "org-kr-b")
    private = ingest(
        db_session,
        IngestRequest(
            source_kind="internal_document",
            authority_level="user_provided",
            title="Segredo da casa",
            content="Procedimento interno confidencial.",
            organization_id=org_a.id,
        ),
    )
    hidden = retrieve(
        db_session,
        RetrievalRequest(organization_id=org_b.id, query_text="confidencial"),
    )
    assert hidden == []
    forged = RankedFragment(
        fragment=private.fragments[0],
        source=private.source,
        version=private.version,
        rank=1,
        score=Decimal("1"),
        selection_reason={"forged": True, "score_is_not_probability": True},
    )
    with pytest.raises(RetrievalError, match="outra organização"):
        persist_grounding(
            db_session,
            RetrievalRequest(organization_id=org_b.id, query_text="confidencial"),
            [forged],
        )


def test_normative_query_requires_jurisdiction_and_date(db_session: Session) -> None:
    with pytest.raises(RetrievalError, match="jurisdição"):
        persist_grounding(
            db_session,
            RetrievalRequest(source_kinds=("normative",), query_text="rotulagem"),
            [],
        )
    with pytest.raises(RetrievalError, match="data"):
        persist_grounding(
            db_session,
            RetrievalRequest(
                source_kinds=("normative",),
                jurisdiction="BR",
                query_text="rotulagem",
            ),
            [],
        )

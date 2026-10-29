from datetime import date
from inspect import getsource
from pathlib import Path

import pytest
from app.modules.knowledge_grounding import ingest as ingest_mod
from app.modules.knowledge_grounding import retrieval as retrieval_mod
from app.modules.knowledge_grounding.ingest import (
    IngestError,
    IngestRequest,
    content_sha256,
    ingest,
    release_global_source,
    review_source_version,
    revoke_source_version,
)
from app.modules.knowledge_grounding.retrieval import RetrievalRequest, retrieve
from app.modules.knowledge_grounding.rules import KnowledgeError
from sqlalchemy.orm import Session
from tests import helpers


def test_global_and_private_sources_are_isolated(db_session: Session) -> None:
    org_a = helpers.org(db_session, "org-ks-a")
    org_b = helpers.org(db_session, "org-ks-b")
    global_result = ingest(
        db_session,
        IngestRequest(
            source_kind="technical",
            authority_level="curated",
            title="Manual técnico de fermentação",
            content="A fermentação lenta desenvolve aroma.",
        ),
    )
    release_global_source(global_result.source)
    private_a = ingest(
        db_session,
        IngestRequest(
            source_kind="internal_document",
            authority_level="user_provided",
            title="Caderno interno de padaria",
            content="Anotação privada da organização A.",
            organization_id=org_a.id,
        ),
    )
    found_b = retrieve(
        db_session,
        RetrievalRequest(organization_id=org_b.id, query_text="fermentação"),
    )
    assert [row.source.id for row in found_b] == [global_result.source.id]
    found_a = retrieve(
        db_session,
        RetrievalRequest(organization_id=org_a.id, query_text="anotação privada"),
    )
    assert private_a.source.id in {row.source.id for row in found_a}
    hidden = retrieve(
        db_session,
        RetrievalRequest(organization_id=org_b.id, query_text="anotação privada"),
    )
    assert hidden == []


def test_restricted_global_source_is_not_visible(db_session: Session) -> None:
    org = helpers.org(db_session, "org-ks-restr")
    ingest(
        db_session,
        IngestRequest(
            source_kind="technical",
            authority_level="curated",
            title="Texto ainda restrito",
            content="Conteúdo global ainda não liberado.",
        ),
    )
    assert retrieve(db_session, RetrievalRequest(organization_id=org.id, query_text="restrito")) == []


def test_official_norm_requires_issuer_and_jurisdiction(db_session: Session) -> None:
    with pytest.raises(KnowledgeError, match="jurisdição"):
        ingest(
            db_session,
            IngestRequest(
                source_kind="normative",
                authority_level="official",
                title="RDC sem jurisdição",
                issuer_or_author="Anvisa",
                content="Texto normativo de teste.",
                regulatory_status="draft",
            ),
        )


def test_recipe_cannot_be_official_norm(db_session: Session) -> None:
    with pytest.raises(KnowledgeError, match="receita"):
        ingest(
            db_session,
            IngestRequest(
                source_kind="recipe",
                authority_level="official",
                title="Receita oficial indevida",
                content="Misture a farinha e a água.",
                content_usage_kind="citation",
            ),
        )


def test_versions_are_immutable_and_hash_creates_new_version(db_session: Session) -> None:
    first = ingest(
        db_session,
        IngestRequest(
            source_kind="technical",
            authority_level="curated",
            title="Manual de escala",
            content="Primeira captura do manual.",
            version_label="v1",
        ),
    )
    same = ingest(
        db_session,
        IngestRequest(
            source_kind="technical",
            authority_level="curated",
            title="Manual de escala",
            content="Primeira captura do manual.",
            version_label="v1-again",
        ),
    )
    assert same.created_version is False
    assert same.version.id == first.version.id
    second = ingest(
        db_session,
        IngestRequest(
            source_kind="technical",
            authority_level="curated",
            title="Manual de escala",
            content="Segunda captura com texto diferente.",
            version_label="v2",
        ),
    )
    assert second.created_version is True
    assert second.version.id != first.version.id
    assert second.content_hash != first.content_hash
    first.version.version_label = "alterado"
    with pytest.raises(Exception, match="append_only"):
        db_session.flush()


def test_retrieved_at_is_not_validity(db_session: Session) -> None:
    result = ingest(
        db_session,
        IngestRequest(
            source_kind="normative",
            authority_level="official",
            title="Norma futura",
            issuer_or_author="Anvisa",
            jurisdiction="BR",
            content="Texto de norma ainda não vigente.",
            regulatory_status="in_force",
            effective_from=date(2099, 1, 1),
            version_label="futuro",
        ),
    )
    release_global_source(result.source)
    actor = helpers.user(db_session, "revisor-futuro@panne.test")
    review_source_version(result.version, decision="reviewed", reviewed_by_user_id=actor.id)
    db_session.flush()
    found = retrieve(
        db_session,
        RetrievalRequest(
            source_kinds=("normative",),
            jurisdiction="BR",
            applicability_date=date(2026, 8, 22),
            query_text="norma",
        ),
    )
    assert found == []
    assert result.version.retrieved_at is not None


def test_revocation_keeps_historical_version(db_session: Session) -> None:
    result = ingest(
        db_session,
        IngestRequest(
            source_kind="normative",
            authority_level="official",
            title="Norma revogada",
            issuer_or_author="Anvisa",
            jurisdiction="BR",
            content="Artigo sobre rotulagem nutricional.",
            regulatory_status="in_force",
            effective_from=date(2020, 10, 8),
            version_label="2020",
        ),
    )
    release_global_source(result.source)
    actor = helpers.user(db_session, "revisor-rev@panne.test")
    review_source_version(result.version, decision="reviewed", reviewed_by_user_id=actor.id)
    db_session.flush()
    revoke_source_version(result.version)
    db_session.flush()
    current = retrieve(
        db_session,
        RetrievalRequest(
            source_kinds=("normative",),
            jurisdiction="BR",
            applicability_date=date(2026, 8, 22),
            query_text="rotulagem",
        ),
    )
    historical = retrieve(
        db_session,
        RetrievalRequest(
            source_kinds=("normative",),
            jurisdiction="BR",
            applicability_date=date(2026, 8, 22),
            query_text="rotulagem",
            include_historical=True,
        ),
    )
    assert current == []
    assert [row.version.id for row in historical] == [result.version.id]


def test_public_consultation_excluded_by_default(db_session: Session) -> None:
    result = ingest(
        db_session,
        IngestRequest(
            source_kind="normative",
            authority_level="official",
            title="Consulta pública",
            issuer_or_author="Anvisa",
            jurisdiction="BR",
            content="Proposta em consulta pública sobre rotulagem.",
            regulatory_status="public_consultation",
            version_label="cp",
        ),
    )
    release_global_source(result.source)
    actor = helpers.user(db_session, "revisor-cp@panne.test")
    review_source_version(result.version, decision="reviewed", reviewed_by_user_id=actor.id)
    db_session.flush()
    default = retrieve(
        db_session,
        RetrievalRequest(
            source_kinds=("normative",),
            jurisdiction="BR",
            applicability_date=date(2026, 8, 22),
            query_text="consulta",
        ),
    )
    optional = retrieve(
        db_session,
        RetrievalRequest(
            source_kinds=("normative",),
            jurisdiction="BR",
            applicability_date=date(2026, 8, 22),
            query_text="consulta",
            include_consultation=True,
        ),
    )
    assert default == []
    assert [row.version.id for row in optional] == [result.version.id]


def test_normative_review_is_required(db_session: Session) -> None:
    result = ingest(
        db_session,
        IngestRequest(
            source_kind="normative",
            authority_level="official",
            title="Norma pendente",
            issuer_or_author="Anvisa",
            jurisdiction="BR",
            content="Texto oficial ainda pendente de revisão.",
            regulatory_status="in_force",
            effective_from=date(2020, 1, 1),
            version_label="pendente",
        ),
    )
    release_global_source(result.source)
    pending = retrieve(
        db_session,
        RetrievalRequest(
            source_kinds=("normative",),
            jurisdiction="BR",
            applicability_date=date(2026, 8, 22),
            query_text="pendente",
        ),
    )
    assert pending == []
    actor = helpers.user(db_session, "revisor-ok@panne.test")
    review_source_version(result.version, decision="reviewed", reviewed_by_user_id=actor.id)
    db_session.flush()
    reviewed = retrieve(
        db_session,
        RetrievalRequest(
            source_kinds=("normative",),
            jurisdiction="BR",
            applicability_date=date(2026, 8, 22),
            query_text="pendente",
        ),
    )
    assert [row.version.id for row in reviewed] == [result.version.id]


def test_fragment_sequence_locator_hash_and_portuguese_search(db_session: Session) -> None:
    org = helpers.org(db_session, "org-ks-fts")
    result = ingest(
        db_session,
        IngestRequest(
            source_kind="technical",
            authority_level="curated",
            title="Guia de nutrição",
            content="Primeiro bloco.\n\nA nutrição do pão depende da farinha.",
            organization_id=org.id,
        ),
    )
    assert [row.sequence for row in result.fragments] == [1, 2]
    assert result.fragments[1].locator_type == "paragraph"
    assert result.fragments[1].locator_value == "paragrafo-2"
    assert result.fragments[1].content_hash == content_sha256(result.fragments[1].content)
    found = retrieve(
        db_session,
        RetrievalRequest(organization_id=org.id, query_text="nutricao"),
    )
    assert result.fragments[1].id in {row.fragment.id for row in found}


def test_ingest_rejects_excess_and_keeps_recipe_as_citation(db_session: Session) -> None:
    with pytest.raises(IngestError, match="excede"):
        ingest(
            db_session,
            IngestRequest(
                source_kind="recipe",
                authority_level="curated",
                title="Página inteira",
                content="x" * (ingest_mod.MAX_CONTENT_BYTES + 1),
                content_usage_kind="citation",
                canonical_url="https://example.test/receita",
                issuer_or_author="Autor exemplo",
                license_or_usage_notes="somente citação do trecho necessário",
            ),
        )
    result = ingest(
        db_session,
        IngestRequest(
            source_kind="recipe",
            authority_level="curated",
            title="Receita citada",
            content="Misture 100 g de farinha.",
            content_usage_kind="citation",
            canonical_url="https://example.test/receita",
            issuer_or_author="Autor exemplo",
            license_or_usage_notes="citação do trecho necessário; sem republicação",
        ),
    )
    assert result.version.content_usage_kind == "citation"
    assert result.source.canonical_url == "https://example.test/receita"


def test_physical_delete_blocked_and_no_llm(db_session: Session) -> None:
    result = ingest(
        db_session,
        IngestRequest(
            source_kind="technical",
            authority_level="curated",
            title="Texto protegido",
            content="Documento é dado, não comando.",
        ),
    )
    db_session.delete(result.source)
    with pytest.raises(Exception):
        db_session.flush()


def test_knowledge_module_has_no_llm() -> None:
    blob = (
        getsource(ingest_mod)
        + getsource(retrieval_mod)
        + Path("app/modules/knowledge_grounding/models.py").read_text(encoding="utf-8")
    )
    for token in ("import openai", "import anthropic", "boto3", "sentence_transformers"):
        assert token not in blob.lower()

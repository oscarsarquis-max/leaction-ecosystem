from app.core.config import get_settings
from app.domain.errors import ConfirmationError
from app.domain.gigio.pairing import (
    PAIRING_SEEDS,
    ensure_pairing_seeds,
    is_allowed_source_url,
    list_references,
    lookup_pairing_references,
    reference_admin_view,
    save_reference,
    sources_for_conversation,
)
from app.domain.gigio.pairing_match import compatible_offer_ids, match_offer_to_reference
from app.domain.gigio.service import chat
from app.domain.gigio.tools import execute_tool
from app.models.gigio import GigioPairingReference
from sqlalchemy import select
from sqlalchemy.orm import Session
from tests.test_prompt77 import _TextOnlyGateway, _catalog, _enable


def _enable_pairing(monkeypatch, enabled=True) -> None:
    monkeypatch.setenv("LOJADEPAES_GIGIO_PAIRING_REFS_ENABLED", "true" if enabled else "false")
    monkeypatch.setenv("LOJADEPAES_GIGIO_ENABLED", "true")
    get_settings.cache_clear()


def _publish(db: Session, profile_key: str, **overrides) -> GigioPairingReference:
    ensure_pairing_seeds(db)
    row = db.scalar(select(GigioPairingReference).where(GigioPairingReference.profile_key == profile_key))
    assert row is not None
    payload = reference_admin_view(row)
    payload.update(
        {
            "editorial_status": "published",
            "reviewed_by": "Oscar",
            "reviewed_at": "2026-10-07",
        }
    )
    payload.update(overrides)
    return save_reference(db, row.id, payload)


def test_seeds_start_draft_with_provenance(db: Session) -> None:
    rows = list_references(db)
    assert {row.profile_key for row in rows} == {seed["profile_key"] for seed in PAIRING_SEEDS}
    assert all(row.editorial_status == "draft" for row in rows)
    assert all(row.loja_choice is False for row in rows)
    assert all(is_allowed_source_url(row.source_url) for row in rows)
    dao = next(row for row in rows if row.profile_key == "wine-dao-leitao")
    assert dao.source_kind == "commercial_editorial"
    assert dao.verification_status == "inaccessible"
    assert dao.retrieval_role == "excluded"
    assert "leitão" not in dao.synthesis.casefold() or "não se afirma" in dao.synthesis.casefold()
    assert not dao.reviewed_by
    canastra = next(row for row in rows if row.profile_key == "cheese-canastra-ig")
    assert canastra.source_kind == "official_register"
    assert canastra.retrieval_role == "informational"
    assert "concessão" in canastra.synthesis.casefold() or "concessao" in canastra.synthesis.casefold() or "2012-03-13" in canastra.source_date


def test_flag_off_does_not_ground_even_if_published(db: Session, monkeypatch) -> None:
    _publish(db, "wine-dao-leitao")
    _enable_pairing(monkeypatch, False)
    lookup = lookup_pairing_references(db, enabled=False, categories=["vinhos"], dishes=["leitao"])
    assert lookup["enabled"] is False
    assert lookup["references"] == []
    result = chat(
        db,
        get_settings(),
        messages=[{"role": "user", "content": "Qual vinho combina com o leitão?"}],
        page={"path": "/"},
        order_token=None,
        is_admin=False,
        gateway=_TextOnlyGateway("Um tinto de acidez presente costuma ir bem com o leitão."),
    )
    assert result["sources"] == []
    assert "cta" in result


def test_published_ref_grounds_chat_without_claiming_partnership(db: Session, monkeypatch) -> None:
    _publish(db, "wine-churrasco-porco")
    _enable_pairing(monkeypatch)
    _catalog(db, monkeypatch)
    _enable(monkeypatch)
    result = chat(
        db,
        get_settings(),
        messages=[{"role": "user", "content": "Qual vinho para linguiça no churrasco?"}],
        page={"path": "/"},
        order_token=None,
        is_admin=False,
        gateway=_TextOnlyGateway(
            "No churrasco, a Evino aponta Lambrusco ou Cabernet Franc para porco e linguiça. "
            "Sugestão do Gigio a partir dessa orientação, sem endosso de rótulo."
        ),
    )
    assert result["sources"]
    hrefs = [item["href"] for item in result["sources"]]
    assert hrefs == ["https://www.evino.com.br/blog/vinhos-e-churrasco/"]
    assert result["sources"][0]["kind"] == "source"
    assert "não avaliação independente" in result["sources"][0]["kind_note"]
    href = (result.get("cta") or {}).get("href") or ""
    assert href != "/acompanhar"
    if href:
        assert href.startswith("/acompanhar")
    assert all(item.get("kind") != "source" for item in result["links"])


def test_no_wine_exclusion_skips_wine_sources(db: Session, monkeypatch) -> None:
    _publish(db, "wine-dao-leitao")
    _publish(db, "cheese-canastra-ig")
    _enable_pairing(monkeypatch)
    sources = sources_for_conversation(
        db,
        enabled=True,
        user_text="Sem vinho. Que queijo vai com o leitão?",
        reply="Para completar a mesa, um queijo de tábua.",
    )
    assert sources == []


def test_archived_ref_does_not_ground(db: Session) -> None:
    row = _publish(db, "wine-dao-leitao")
    save_reference(
        db,
        row.id,
        {**reference_admin_view(row), "editorial_status": "archived", "reviewed_by": "Oscar"},
    )
    lookup = lookup_pairing_references(db, enabled=True, categories=["vinhos"], dishes=["leitao"])
    assert lookup["available"] is False
    assert lookup["references"] == []


def test_insufficient_reference_stays_general(db: Session, monkeypatch) -> None:
    _enable_pairing(monkeypatch)
    result = chat(
        db,
        get_settings(),
        messages=[{"role": "user", "content": "Qual vinho para o leitão?"}],
        page={"path": "/"},
        order_token=None,
        is_admin=False,
        gateway=_TextOnlyGateway("Um tinto de acidez presente costuma acompanhar o porco assado."),
    )
    assert result["sources"] == []
    assert "evino" not in result["reply"].casefold()


def test_hub_down_keeps_published_knowledge(db: Session, monkeypatch) -> None:
    _publish(db, "oil-azeite-brasileiro-embrapa")
    _enable_pairing(monkeypatch)
    _enable(monkeypatch)
    from tests.test_prompt73 import _mock_hub

    _mock_hub(monkeypatch, [], ok=False)
    result = chat(
        db,
        get_settings(),
        messages=[{"role": "user", "content": "Que azeite uso na salada com o pão?"}],
        page={"path": "/"},
        order_token=None,
        is_admin=False,
        gateway=_TextOnlyGateway("Um azeite extra virgem no pão ou na salada. Sugestão do Gigio, sem consulta especializada."),
    )
    assert result["sources"] == []
    assert result["cta"] is None


def test_loja_choice_requires_review() -> None:
    from app.domain.gigio.pairing import _validated_payload

    try:
        _validated_payload(
            {
                "title": "Teste",
                "synthesis": "Síntese fiel.",
                "category": "vinhos",
                "scope": "style",
                "source_kind": "commercial",
                "source_url": "https://www.evino.com.br/blog/vinhos-do-dao/",
                "source_title": "Vinhos do Dão",
                "editorial_status": "published",
                "reviewed_by": "",
                "loja_choice": True,
            },
            creating=False,
        )
        raise AssertionError("deveria exigir revisão")
    except ConfirmationError as exc:
        assert "revisão" in str(exc)


def test_source_url_rejects_token_and_unknown_host() -> None:
    assert is_allowed_source_url("https://www.evino.com.br/blog/vinhos-do-dao/")
    assert not is_allowed_source_url("https://www.evino.com.br/blog?token=abc")
    assert not is_allowed_source_url("https://example.com/ficha")
    assert not is_allowed_source_url("http://www.gov.br/inpi")


def test_style_does_not_certify_generic_bottle() -> None:
    ref = {
        "category": "vinhos",
        "scope": "style",
        "match_hints": ["dao", "dão"],
        "editorial_status": "published",
        "loja_choice": False,
    }
    generic = {"title": "Vinho Tinto 750ml", "category": "vinhos"}
    dao = {"title": "Vinho Tinto do Dão Reserva 750ml", "category": "vinhos"}
    generic_match = match_offer_to_reference(generic, ref)
    dao_match = match_offer_to_reference(dao, ref)
    assert generic_match["nature"] is True
    assert generic_match["correspondence"] == "none"
    assert generic_match["excellence"] is None
    assert dao_match["correspondence"] == "none"
    assert "região" in dao_match["caution"] or "geográfic" in dao_match["caution"]


def test_divergent_vintage_does_not_inherit() -> None:
    ref = {
        "category": "vinhos",
        "scope": "product",
        "match_hints": ["touriga"],
        "identity": {"brand": "quinta da pedra", "variety": "touriga", "vintage": "2020", "volume": "750ml"},
        "editorial_status": "published",
        "loja_choice": False,
    }
    other = {
        "title": "Quinta da Pedra Touriga Nacional 2021 750ml",
        "category": "vinhos",
        "brand": "Quinta da Pedra",
        "variety": "touriga",
        "vintage": "2021",
        "volume": "750ml",
    }
    same = {**other, "title": "Quinta da Pedra Touriga Nacional 2020 750ml", "vintage": "2020"}
    assert match_offer_to_reference(other, ref)["correspondence"] == "none"
    assert "safra" in match_offer_to_reference(other, ref)["identity_reason"]
    assert match_offer_to_reference(same, ref)["correspondence"] == "specific"


def test_salame_is_not_cheese_correspondence() -> None:
    ref = {
        "category": "queijos",
        "scope": "style",
        "match_hints": ["canastra"],
        "editorial_status": "published",
    }
    salame = {"title": "Salame com queijo Canastra 300g", "category": "queijos"}
    cheese = {"title": "Queijo Canastra 500g", "category": "queijos"}
    assert match_offer_to_reference(salame, ref)["nature"] is False
    assert match_offer_to_reference(cheese, ref)["correspondence"] == "none"


def test_missing_data_does_not_fill_grid() -> None:
    refs = [
        {
            "category": "vinhos",
            "scope": "style",
            "match_hints": ["dao"],
            "editorial_status": "published",
        }
    ]
    offers = [
        {"hub_offer_id": "A", "title": "Vinho Tinto 750ml", "category": "vinhos"},
        {"hub_offer_id": "B", "title": "Tinto do Dão 750ml", "category": "vinhos"},
    ]
    assert compatible_offer_ids(offers, refs) == []


def test_commission_is_not_used_as_quality() -> None:
    result = match_offer_to_reference(
        {"title": "Tinto do Dão 750ml", "category": "vinhos", "bestseller": True, "commission": 0.12},
        {"category": "vinhos", "scope": "style", "match_hints": ["dao"], "editorial_status": "published"},
    )
    assert result["commission_used"] is False
    assert result["excellence"] is None


def test_tool_does_not_leak_when_flag_off(db: Session, monkeypatch) -> None:
    _publish(db, "wine-dao-leitao")
    _enable_pairing(monkeypatch, False)
    payload = execute_tool(
        "lookup_pairing_references",
        {"categories": ["vinhos"], "dishes": ["leitao"]},
        session=db,
        settings=get_settings(),
        order_reference=None,
        order_token=None,
        is_admin=False,
    )
    assert payload["enabled"] is False
    assert payload["references"] == []


def test_prompt80_meal_cta_still_attaches(db: Session, monkeypatch) -> None:
    _catalog(db, monkeypatch)
    _enable(monkeypatch)
    _enable_pairing(monkeypatch, False)
    result = chat(
        db,
        get_settings(),
        messages=[
            {
                "role": "user",
                "content": "Vou servir leitão com saladas. Que pão e acompanhamentos você sugere?",
            }
        ],
        page={"path": "/"},
        order_token=None,
        is_admin=False,
        gateway=_TextOnlyGateway(
            "Para o leitão, um pão de crosta firme. Para completar a mesa, vinho, queijo e azeite."
        ),
    )
    assert result["cta"]["label"] == "Ver acompanhamentos sugeridos"
    assert "mesa=leitao,salada" in result["cta"]["href"]
    assert result["sources"] == []

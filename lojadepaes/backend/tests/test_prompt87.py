from app.core.config import get_settings
from app.domain.builder_proposal import (
    BUILDER_CTA_LABEL,
    propose_from_slugs,
    resolve_proposal,
    verify_proposal,
)
from app.domain.builder_tip import builder_tip
from app.domain.custom_loaf import public_builder_catalog
from app.domain.errors import ConfirmationError
from app.domain.gigio.fake import FakeGigioGateway
from app.domain.gigio.rules import PROCESS_RULES, PROCESS_RULES_VERSION
from app.domain.gigio.service import chat
from app.domain.gigio.tools import execute_tool
from sqlalchemy.orm import Session
from tests.test_prompt73 import _mock_hub, _offer
from tests.test_prompt77 import _enable
from tests.test_prompt81 import _enable_pairing

SANDWICH_Q = (
    "Quero um sanduíche para receber amigos, com pão de farinha branca "
    "e fermentação natural, talvez com queijo na massa e em pão de forma."
)


def _enable_gigio(monkeypatch) -> None:
    monkeypatch.setenv("LOJADEPAES_GIGIO_ENABLED", "true")
    monkeypatch.setenv("LOJADEPAES_GIGIO_GATEWAY", "fake")
    get_settings.cache_clear()


def _slugs(catalog: dict) -> dict[str, set[str]]:
    return {
        "flours": {row["slug"] for row in catalog["flours"]},
        "doughs": {row["slug"] for row in catalog["doughs"]},
        "inclusions": {row["slug"] for row in catalog["ingredients"]},
        "shapes": {row["slug"] for row in catalog["shapes"]},
    }


def test_rules_version_is_87() -> None:
    assert int(PROCESS_RULES_VERSION) >= 87
    assert "propose_builder" in PROCESS_RULES
    assert "Montar esse pão" in PROCESS_RULES
    assert "Ausência na vitrine não é impossibilidade" in PROCESS_RULES
    assert "hambúrguer" in PROCESS_RULES.casefold() or "hamburguer" in PROCESS_RULES.casefold()


def test_builder_capabilities_are_canonical(db: Session) -> None:
    catalog = public_builder_catalog(db)
    slugs = _slugs(catalog)
    assert "farinha-branca-strong-white" in slugs["flours"]
    assert "farinha-branca-italiana" not in slugs["flours"]
    assert "fermentacao-natural-curta" in slugs["doughs"]
    assert "queijo-parmesao" in slugs["inclusions"]
    assert "granola" in slugs["inclusions"]
    assert "graos" not in slugs["inclusions"] and "grãos" not in slugs["inclusions"]
    assert "pao-de-forma" in slugs["shapes"]
    lookup = execute_tool(
        "lookup_builder",
        {},
        session=db,
        settings=get_settings(),
        order_reference=None,
        order_token=None,
        is_admin=False,
    )
    assert {row["slug"] for row in lookup["flours"]} == slugs["flours"]
    assert {row["slug"] for row in lookup["preparations"]} == slugs["doughs"]
    assert lookup["structured"] == ["flour", "preparation", "inclusions", "shape"]


def test_sandwich_chat_proposes_validated_builder(db: Session, monkeypatch) -> None:
    _enable_gigio(monkeypatch)
    result = chat(
        db,
        get_settings(),
        messages=[{"role": "user", "content": SANDWICH_Q}],
        page={"path": "/"},
        order_token=None,
        is_admin=False,
        gateway=FakeGigioGateway(),
    )
    assert result["unavailable"] is False
    cta = result["builder_cta"]
    assert cta["label"] == BUILDER_CTA_LABEL
    assert cta["href"].startswith("/?proposta=")
    assert cta["href"].endswith("#criacao")
    token = cta["href"].split("proposta=")[1].split("#")[0]
    resolved = resolve_proposal(db, get_settings(), token)
    assert resolved["flour_slug"] == "farinha-branca-strong-white"
    assert resolved["dough_slug"] == "fermentacao-natural-curta"
    assert resolved["shape_slug"] == "pao-de-forma"
    assert "queijo-parmesao" in resolved["ingredient_slugs"]
    assert resolved["flour_id"]
    assert resolved["dough_id"]
    assert resolved["shape_id"]


def test_unknown_slug_is_rejected_without_fabrication(db: Session) -> None:
    rejected = propose_from_slugs(
        db,
        get_settings(),
        flour="farinha-de-unicornio",
        preparation="fermentacao-natural-curta",
        inclusions=["graos-inventados"],
        shape="pao-de-forma",
    )
    assert rejected["accepted"] is True
    assert "flour" in rejected["needs_choice"]
    assert "graos-inventados" in rejected["unknown"]
    token = rejected["proposal_token"]
    resolved = resolve_proposal(db, get_settings(), token)
    assert resolved["flour_id"] == ""
    assert resolved["dough_slug"] == "fermentacao-natural-curta"
    assert resolved["ingredient_ids"] == []
    italian = propose_from_slugs(
        db,
        get_settings(),
        flour="farinha-branca-italiana",
        preparation="fermentacao-natural-curta",
        shape="pao-de-forma",
    )
    assert italian["accepted"] is True
    assert "flour" in italian["needs_choice"]
    empty = propose_from_slugs(db, get_settings(), flour="nao-existe", inclusions=["tampouco"])
    assert empty["accepted"] is False
    assert empty.get("cta") is None


def test_tampered_proposal_is_rejected(db: Session) -> None:
    ok = propose_from_slugs(
        db,
        get_settings(),
        flour="farinha-branca-strong-white",
        preparation="fermentacao-natural-curta",
        shape="pao-de-forma",
    )
    bad = ok["proposal_token"][:-4] + "abcd"
    try:
        resolve_proposal(db, get_settings(), bad)
        raise AssertionError("token adulterado deveria falhar")
    except ConfirmationError:
        pass
    payload = verify_proposal(get_settings(), ok["proposal_token"])
    assert "conversation" not in payload
    assert "email" not in payload


def test_tip_uses_current_composition_and_apply_patch(db: Session, monkeypatch) -> None:
    _enable_gigio(monkeypatch)
    catalog = public_builder_catalog(db)
    flour = next(row for row in catalog["flours"] if row["slug"] == "farinha-branca-strong-white")
    dough = next(row for row in catalog["doughs"] if row["slug"] == "fermentacao-natural-curta")
    shape = next(row for row in catalog["shapes"] if row["slug"] == "pao-de-forma")
    cheese = next(row for row in catalog["ingredients"] if row["slug"] == "queijo-parmesao")
    first = builder_tip(
        db,
        get_settings(),
        {
            "flour_id": flour["id"],
            "dough_id": dough["id"],
            "ingredient_ids": [],
            "shape_id": shape["id"],
            "free_text": "",
        },
        FakeGigioGateway(),
    )
    assert flour["name"].split()[0] in first["observation"] or "branca" in first["observation"].casefold()
    assert first["composition"]["flour"] == flour["name"]
    assert first["suggestion"]
    assert first["suggestion"]["patch"]["ingredient_ids"] == [cheese["id"]]
    with_cheese = builder_tip(
        db,
        get_settings(),
        {
            "flour_id": flour["id"],
            "dough_id": dough["id"],
            "ingredient_ids": [cheese["id"]],
            "shape_id": shape["id"],
            "free_text": "",
        },
        FakeGigioGateway(),
    )
    assert "parmes" in with_cheese["observation"].casefold()
    assert with_cheese["composition"]["inclusions"] == [cheese["name"]]


def test_tip_respects_no_cheese_and_no_alcohol(db: Session, monkeypatch) -> None:
    _enable(monkeypatch)
    _enable_pairing(monkeypatch)
    _enable_gigio(monkeypatch)
    _mock_hub(
        monkeypatch,
        [
            _offer(id="MLBVINHO1", title="Vinho tinto da mesa", category="vinhos", link="https://www.mercadolivre.com.br/p/MLBVINHO1"),
            _offer(id="MLBQUEIJO1", title="Queijo Canastra", category="queijos", link="https://www.mercadolivre.com.br/p/MLBQUEIJO1"),
        ],
    )
    catalog = public_builder_catalog(db)
    flour = next(row for row in catalog["flours"] if row["slug"] == "farinha-branca-strong-white")
    dough = next(row for row in catalog["doughs"] if row["slug"] == "fermentacao-natural-curta")
    shape = next(row for row in catalog["shapes"] if row["slug"] == "pao-de-forma")
    tip = builder_tip(
        db,
        get_settings(),
        {
            "flour_id": flour["id"],
            "dough_id": dough["id"],
            "ingredient_ids": [],
            "shape_id": shape["id"],
            "occasion": "sanduíche sem queijo e sem álcool",
            "context_text": "sem queijo sem álcool",
        },
        FakeGigioGateway(),
    )
    if tip["suggestion"]:
        names = " ".join(tip["suggestion"]["patch"].get("ingredient_names") or []).casefold()
        assert "queijo" not in names
    href = ((tip.get("cta") or {}) or {}).get("href") or ""
    assert "vinhos" not in href
    assert "MLBVINHO1" not in href


def test_tip_failure_does_not_invent_composition(db: Session, monkeypatch) -> None:
    _enable_gigio(monkeypatch)

    class DeadGateway:
        def complete(self, request):
            raise RuntimeError("modelo fora")

    catalog = public_builder_catalog(db)
    flour = next(row for row in catalog["flours"] if row["slug"] == "farinha-branca-strong-white")
    dough = next(row for row in catalog["doughs"] if row["slug"] == "fermentacao-natural-curta")
    try:
        builder_tip(
            db,
            get_settings(),
            {"flour_id": flour["id"], "dough_id": dough["id"], "ingredient_ids": [], "shape_id": ""},
            DeadGateway(),
        )
        raise AssertionError("falha do modelo deveria aparecer")
    except ConfirmationError as exc:
        assert "dica" in str(exc)


def test_chat_with_builder_context_does_not_create_order(db: Session, monkeypatch) -> None:
    _enable_gigio(monkeypatch)
    catalog = public_builder_catalog(db)
    flour = next(row for row in catalog["flours"] if row["slug"] == "farinha-branca-strong-white")
    result = chat(
        db,
        get_settings(),
        messages=[{"role": "user", "content": "Essa massa serve para sanduíche?"}],
        page={
            "path": "/",
            "builder": {
                "flour": flour["name"],
                "preparation": "Fermentação natural curta (Classic sourdough)",
                "inclusions": ["Queijo parmesão"],
                "shape": "Pão de forma",
                "note": "",
            },
        },
        order_token=None,
        is_admin=False,
        gateway=FakeGigioGateway(),
    )
    assert result["unavailable"] is False
    assert "pedido" not in (result.get("builder_cta") or {})

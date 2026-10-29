from app.core.config import get_settings
from app.domain.gigio.pairing import (
    ALL_AUTHORIZED_KEYS,
    EVALUATION_PROFILE_KEYS,
    GUIDE_CATALOG_KEYS,
    PUBLISHABLE_PROFILE_KEYS,
    lookup_pairing_references,
    publish_authorized_pilot,
    reference_admin_view,
    sources_for_conversation,
)
from app.domain.gigio.pairing_match import (
    compatible_offer_ids,
    match_offer_to_evaluation,
    match_offer_to_reference,
)
from app.domain.gigio.rules import PROCESS_RULES_VERSION
from app.domain.gigio.service import chat
from app.models.gigio import GigioPairingReference
from sqlalchemy import select
from sqlalchemy.orm import Session
from tests.test_prompt77 import _TextOnlyGateway
from tests.test_prompt81 import _enable_pairing


def _eval_ref(db: Session, key: str) -> dict:
    publish_authorized_pilot(db)
    row = db.scalar(select(GigioPairingReference).where(GigioPairingReference.profile_key == key))
    assert row is not None
    return reference_admin_view(row)


def test_evaluation_rules_remain_after_later_prompts() -> None:
    from app.domain.gigio.rules import PROCESS_RULES

    assert "Avaliação de guia" in PROCESS_RULES
    assert PROCESS_RULES_VERSION


def test_publish_keeps_pairing_and_adds_verified_evaluations(db: Session) -> None:
    report = publish_authorized_pilot(db)
    keys = {item["profile_key"] for item in report if item["action"] == "published"}
    assert PUBLISHABLE_PROFILE_KEYS <= keys
    assert EVALUATION_PROFILE_KEYS <= keys
    assert GUIDE_CATALOG_KEYS <= keys
    assert "wine-dao-leitao" not in keys
    rows = list(db.scalars(select(GigioPairingReference)))
    published = {row.profile_key: row for row in rows if row.editorial_status == "published"}
    assert set(published) == set(ALL_AUTHORIZED_KEYS)
    sacramentos = published["eval-descorchados-sacramentos-ses-sb-2025"]
    assert sacramentos.retrieval_role == "evaluation"
    assert sacramentos.evidence_type == "guide_evaluation"
    assert sacramentos.verification_status == "verified"
    assert sacramentos.characteristics["nota"] == "95"
    assert sacramentos.characteristics["escala"] == "100"
    assert sacramentos.identity["vintage"] == "2025"
    adega = published["guide-adega-brasil-2026"]
    assert adega.retrieval_role == "informational"
    assert adega.verification_status == "pending"
    assert adega.evidence_type != "guide_evaluation"


def test_pairing_question_does_not_attach_guide_score(db: Session) -> None:
    publish_authorized_pilot(db)
    fish = lookup_pairing_references(db, enabled=True, categories=["vinhos"], query="peixe grelhado")
    shrimp = sources_for_conversation(db, enabled=True, user_text="Camarão com molho de limão e ervas", reply="")
    assert [item["profile_key"] for item in fish["references"]] == ["wine-peixe-grelhado"]
    assert fish.get("evaluations") == []
    assert all(item.get("retrieval_role") != "evaluation" for item in fish["sources"])
    assert all("95" not in (item.get("title") or "") for item in shrimp)
    assert all(item.get("retrieval_role") != "evaluation" for item in shrimp)


def test_named_label_returns_verified_evaluation_only(db: Session) -> None:
    publish_authorized_pilot(db)
    named = lookup_pairing_references(
        db, enabled=True, categories=["vinhos"], query="Sacramentos Sabina Entre Serras 2025"
    )
    assert named["references"] == []
    keys = [item["profile_key"] for item in named["evaluations"]]
    assert keys == ["eval-descorchados-sacramentos-ses-sb-2025"]
    assert named["evaluations"][0]["characteristics"]["nota"] == "95"
    sources = sources_for_conversation(
        db, enabled=True, user_text="O Sacramentos Sabina Entre Serras Sauvignon Blanc 2025 tem nota?", reply=""
    )
    assert len(sources) == 1
    assert sources[0]["retrieval_role"] == "evaluation"
    assert "95" in sources[0]["score_line"]
    assert "Descorchados" in sources[0]["score_line"]
    assert "safra 2025" in sources[0]["score_line"]


def test_style_name_does_not_inherit_score(db: Session) -> None:
    publish_authorized_pilot(db)
    style = lookup_pairing_references(
        db, enabled=True, categories=["vinhos"], query="um sauvignon blanc para peixe grelhado"
    )
    assert style.get("evaluations") == []
    assert [item["profile_key"] for item in style["references"]] == ["wine-peixe-grelhado"]
    sources = sources_for_conversation(
        db, enabled=True, user_text="Qual sauvignon blanc combina com peixe grelhado?", reply=""
    )
    assert all(item.get("retrieval_role") != "evaluation" for item in sources)


def test_adega_catalog_is_locator_not_score(db: Session) -> None:
    publish_authorized_pilot(db)
    lookup = lookup_pairing_references(db, enabled=True, query="vocês usam o guia ADEGA Brasil 2026?")
    assert lookup["evaluations"] == []
    assert [item["profile_key"] for item in lookup["catalogs"]] == ["guide-adega-brasil-2026"]
    sources = sources_for_conversation(db, enabled=True, user_text="O que diz o guia ADEGA sobre vinhos?", reply="")
    assert sources[0]["retrieval_role"] == "informational"
    assert "fichas" in sources[0]["synthesis"].casefold() or "pendente" in sources[0]["title"].casefold()


def test_descorchados_catalog_without_label_has_no_score(db: Session) -> None:
    publish_authorized_pilot(db)
    lookup = lookup_pairing_references(db, enabled=True, query="o que é o guia Descorchados?")
    assert lookup["evaluations"] == []
    assert [item["profile_key"] for item in lookup["catalogs"]] == ["guide-descorchados-informe-brasil-2026"]


def test_exact_offer_inherits_evaluation_divergent_does_not(db: Session) -> None:
    ref = _eval_ref(db, "eval-descorchados-sacramentos-ses-sb-2025")
    exact = {
        "hub_offer_id": "EXACT",
        "title": "Sacramentos Vinifer Sabina Entre Serras Sauvignon Blanc 2025 750ml",
        "category": "vinhos",
    }
    other_vintage = {
        "hub_offer_id": "VINTAGE",
        "title": "Sacramentos Vinifer Sabina Entre Serras Sauvignon Blanc 2024 750ml",
        "category": "vinhos",
    }
    other_line = {
        "hub_offer_id": "LINE",
        "title": "Sacramentos Vinifer Reserva Sauvignon Blanc 2025 750ml",
        "category": "vinhos",
    }
    generic = {"hub_offer_id": "GEN", "title": "Sauvignon Blanc 750ml", "category": "vinhos"}
    no_year = {
        "hub_offer_id": "NV",
        "title": "Sacramentos Vinifer Sabina Entre Serras Sauvignon Blanc 750ml",
        "category": "vinhos",
    }
    assert match_offer_to_evaluation(exact, ref)["correspondence"] == "specific"
    assert match_offer_to_evaluation(other_vintage, ref)["correspondence"] == "none"
    assert "safra" in match_offer_to_evaluation(other_vintage, ref)["caution"]
    assert match_offer_to_evaluation(other_line, ref)["correspondence"] == "none"
    assert match_offer_to_evaluation(generic, ref)["correspondence"] == "none"
    assert match_offer_to_evaluation(no_year, ref)["correspondence"] == "none"
    assert match_offer_to_reference(exact, ref)["correspondence"] == "none"
    assert compatible_offer_ids([exact, generic], [ref]) == []


def test_almeida_line_does_not_transfer(db: Session) -> None:
    ref = _eval_ref(db, "eval-descorchados-almeida-paralelas-cf-2024")
    exact = {
        "title": "Casa Almeida Barreto Paralelas Cabernet Franc 2024",
        "category": "vinhos",
    }
    cinsault = {
        "title": "Casa Almeida Barreto Paralelas Cinsault 2024",
        "category": "vinhos",
    }
    assert match_offer_to_evaluation(exact, ref)["correspondence"] == "specific"
    assert match_offer_to_evaluation(cinsault, ref)["correspondence"] == "none"


def test_previous_pilot_refs_still_work(db: Session) -> None:
    publish_authorized_pilot(db)
    pork = lookup_pairing_references(db, enabled=True, categories=["vinhos"], query="churrasco de porco e linguica")
    cheese = lookup_pairing_references(db, enabled=True, categories=["vinhos"], query="tabua de queijos")
    frios = sources_for_conversation(db, enabled=True, user_text="Como monto uma mesa de frios?", reply="")
    assert [item["profile_key"] for item in pork["references"]] == ["wine-churrasco-porco"]
    assert [item["profile_key"] for item in cheese["references"]] == ["wine-queijo-tabua"]
    assert pork.get("evaluations") == []
    assert any("winefolly.com" in item["href"] for item in frios)


def test_named_wine_chat_shows_evaluation_not_as_pairing(db: Session, monkeypatch) -> None:
    _enable_pairing(monkeypatch)
    publish_authorized_pilot(db)
    result = chat(
        db,
        get_settings(),
        messages=[{"role": "user", "content": "O Sacramentos Sabina Entre Serras 2025 tem avaliação?"}],
        page={"path": "/"},
        order_token=None,
        is_admin=False,
        gateway=_TextOnlyGateway(
            "O Descorchados Informe Brasil 2026 atribui 95 pontos a este rótulo e safra. "
            "Isso não prova combinação com um prato."
        ),
    )
    assert result["sources"]
    assert result["sources"][0]["retrieval_role"] == "evaluation"
    assert "95" in result["sources"][0]["score_line"]
    assert "não prova harmonização" in result["sources"][0]["kind_note"].casefold()


def test_pairing_chat_does_not_surface_guide_evaluation(db: Session, monkeypatch) -> None:
    _enable_pairing(monkeypatch)
    publish_authorized_pilot(db)
    result = chat(
        db,
        get_settings(),
        messages=[{"role": "user", "content": "Qual vinho com peixe grelhado?"}],
        page={"path": "/"},
        order_token=None,
        is_admin=False,
        gateway=_TextOnlyGateway("O tipo e o preparo mudam a escolha, segundo a Wine Folly."),
    )
    assert result["sources"]
    assert all(item.get("retrieval_role") != "evaluation" for item in result["sources"])
    assert all("95" not in (item.get("score_line") or "") for item in result["sources"])


def test_flag_off_hides_evaluations(db: Session, monkeypatch) -> None:
    publish_authorized_pilot(db)
    _enable_pairing(monkeypatch, False)
    result = chat(
        db,
        get_settings(),
        messages=[{"role": "user", "content": "O Sacramentos Sabina tem nota no Descorchados?"}],
        page={"path": "/"},
        order_token=None,
        is_admin=False,
        gateway=_TextOnlyGateway("Posso orientar de forma geral, sem consultar guia."),
    )
    assert result["sources"] == []

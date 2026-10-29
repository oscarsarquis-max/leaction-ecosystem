import re

from app.core.config import get_settings
from app.domain.baker_library.access import (
    AUTHORIZED_COMPLEMENTARY_BRL,
    AUTHORIZED_INITIAL_BRL,
    COMPLEMENTARY_HINT_SKU,
    PLAN_HINT_SKU,
    public_plan,
)
from app.domain.cpf import mask_email
from app.domain.customer_identity import start_resume_by_cpf, start_signup, verify_code
from app.domain.gigio.rules import PROCESS_RULES, PROCESS_RULES_VERSION
from app.domain.storefront_orders import apply_subscriber_discount
from app.models.email_outbox import EmailOutbox
from sqlalchemy.orm import Session
from tests.admin_client import TEST_SESSION_SECRET


def test_rules_keep_three_domains_and_one_shot_pack() -> None:
    assert int(PROCESS_RULES_VERSION) >= 91
    assert "R$ 19,00" in PROCESS_RULES
    assert "R$ 10,00 avulso" in PROCESS_RULES
    assert "R$ 10,00 / mês" not in PROCESS_RULES
    assert "10% de desconto" in PROCESS_RULES
    assert "fidelidade/créditos de pão" in PROCESS_RULES
    assert "página de planos do ActionHub" in PROCESS_RULES


def test_public_plan_points_to_hub_loja_and_pack_is_one_shot(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.domain.baker_library.access._fetch_catalog",
        lambda _settings: {"plans": []},
    )
    plan = public_plan(get_settings())
    assert plan["authorized_initial_brl"] == AUTHORIZED_INITIAL_BRL
    assert plan["authorized_complementary_brl"] == AUTHORIZED_COMPLEMENTARY_BRL
    assert plan["pack"]["period"] == "avulso"
    assert plan["pack"]["sku"] == COMPLEMENTARY_HINT_SKU
    assert plan["principal"]["sku"] == PLAN_HINT_SKU or plan["suggested_sku"] == PLAN_HINT_SKU
    assert "/loja" in plan["plans_href"]
    assert "return_origin" in plan["plans_href"]
    notes = " ".join(plan["cycle_rules"]["notes"])
    assert "avulsa" in notes
    assert "/ mês" not in notes or "19,00 por mês" in notes
    assert "R$ 10,00 / mês" not in notes


def test_subscriber_discount_is_ten_percent_and_skips_freight(monkeypatch, db: Session) -> None:
    account = type("A", (), {"id": 1, "email": "ana@example.com", "name": "Ana"})()
    monkeypatch.setattr(
        "app.domain.baker_library.access.access_for_account",
        lambda *_a, **_k: {"authorized": True, "identified": True, "subscription_status": "active"},
    )
    quote = {
        "subtotal_cents": 7000,
        "discount_cents": 0,
        "total_cents": 7000,
        "credit_applied": False,
    }
    result = apply_subscriber_discount(db, get_settings(), {"_fidelity_account": account}, quote)
    assert result["subscriber_discount_cents"] == 700
    assert result["discount_cents"] == 700
    assert result["total_cents"] == 6300
    assert result["promo_conflict"] is None

    ninety = apply_subscriber_discount(
        db,
        get_settings(),
        {"_fidelity_account": account},
        {"subtotal_cents": 9000, "discount_cents": 0, "total_cents": 9000, "credit_applied": False},
    )
    assert ninety["subscriber_discount_cents"] == 900
    assert ninety["total_cents"] == 8100


def test_pack_only_account_does_not_get_subscriber_discount(monkeypatch, db: Session) -> None:
    account = type("A", (), {"id": 2, "email": "pacote@example.com", "name": "Pacote"})()
    monkeypatch.setattr(
        "app.domain.baker_library.access.access_for_account",
        lambda *_a, **_k: {
            "authorized": False,
            "identified": True,
            "subscription_status": "none",
            "ai_credits": 10,
            "pack_credits": 10,
        },
    )
    result = apply_subscriber_discount(
        db,
        get_settings(),
        {"_fidelity_account": account},
        {"subtotal_cents": 7000, "discount_cents": 0, "total_cents": 7000, "credit_applied": False},
    )
    assert result["subscriber_discount_cents"] == 0
    assert result["total_cents"] == 7000


def test_fidelity_and_subscriber_keep_separate_lines(monkeypatch, db: Session) -> None:
    account = type("A", (), {"id": 3, "email": "ambas@example.com", "name": "Ambas"})()
    monkeypatch.setattr(
        "app.domain.baker_library.access.access_for_account",
        lambda *_a, **_k: {"authorized": True, "identified": True, "subscription_status": "active"},
    )
    result = apply_subscriber_discount(
        db,
        get_settings(),
        {"_fidelity_account": account},
        {
            "subtotal_cents": 14000,
            "discount_cents": 7000,
            "total_cents": 7000,
            "credit_applied": True,
        },
    )
    assert result["promo_conflict"] is None
    assert result["subscriber_discount_cents"] == 1400
    assert result["fidelity_discount_cents"] == 7000
    assert result["discount_cents"] == 8400
    assert result["total_cents"] == 5600
    assert result["subscriber_discount_base"] == "subtotal"


def test_cpf_resume_sends_to_registered_email(db: Session, monkeypatch) -> None:
    monkeypatch.setenv("LOJADEPAES_CUSTOMER_IDENTITY_SECRET", TEST_SESSION_SECRET)
    monkeypatch.setenv("LOJADEPAES_ADMIN_SESSION_SECRET", TEST_SESSION_SECRET)
    get_settings.cache_clear()
    settings = get_settings()
    start_signup(db, settings, "Ana", "ana.cadastrada@example.com", "390.533.447-05")
    account, _token = verify_code(
        db, settings, "ana.cadastrada@example.com", _latest_code(db), enroll_fidelity=False
    )
    assert account.email == "ana.cadastrada@example.com"
    result = start_resume_by_cpf(db, settings, "39053344705")
    assert result["email_masked"] == mask_email("ana.cadastrada@example.com")
    assert result["email_masked"] == "a***@example.com"
    mail = db.query(EmailOutbox).order_by(EmailOutbox.id.desc()).first()
    assert mail is not None
    assert mail.to_address == "ana.cadastrada@example.com"
    get_settings.cache_clear()


def _latest_code(db: Session) -> str:
    mail = db.query(EmailOutbox).order_by(EmailOutbox.id.desc()).first()
    assert mail is not None
    match = re.search(r"é (\d{6})", mail.body)
    assert match
    return match.group(1)

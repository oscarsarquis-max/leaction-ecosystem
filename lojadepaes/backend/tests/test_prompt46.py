from datetime import timedelta
from uuid import uuid4

from app.core.config import get_settings
from app.domain.bakery_time import bakery_today
from app.domain.house_fidelity import FOCACCIA_SLUG, lines_qualify_for_stamp, reward_gaps
from app.domain.house_fidelity_redeem import eligible_500g_variants
from app.domain.recipe_bases import create_recipe_base
from app.domain.schedule import evaluate_day, save_date_override
from app.domain.showcase import ensure_slots
from app.models.enums import EditorialStatus
from app.models.products import Product, ProductVariant
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from tests.test_date_requests import product_client


def _today():
    return bakery_today(get_settings())


def _product(db: Session, *, slug: str, eligible: bool = True, slot: int = 0) -> ProductVariant:
    base = create_recipe_base(db, code=f"rb-{uuid4().hex[:6]}", name="Massa 46")
    product = Product(
        name="Pão 46",
        slug=slug,
        short_description="teste",
        recipe_base_id=base.id,
        featured_image_alt="pão",
        editorial_status=EditorialStatus.PUBLISHED.value,
        is_available=True,
        fidelity_eligible=eligible,
    )
    db.add(product)
    db.flush()
    variant = ProductVariant(
        product_id=product.id,
        display_name="500 g",
        presentation_type="weight",
        net_weight_grams=500,
        physical_units=1,
        price_cents=7000,
        currency="BRL",
        is_active=True,
    )
    db.add(variant)
    db.flush()
    slots = ensure_slots(db)
    slots[slot].product_id = product.id
    db.flush()
    return variant


def test_today_is_not_selectable_for_normal_order(db: Session) -> None:
    settings = get_settings()
    today = _today()
    day = evaluate_day(db, settings, today, [])
    assert day.eligible_for_selection is False
    assert day.status in {"same_day", "closed"}
    if day.status == "same_day":
        assert "próximos dias" in day.accessible_label


def test_accepting_today_still_allowed_with_ignore_advance(db: Session) -> None:
    settings = get_settings()
    today = _today()
    save_date_override(
        db,
        settings,
        today,
        open_state="open",
        daily_physical_limit=15,
        daily_base_limit=5,
        eligibility_mode="inherit",
        eligible_base_ids=None,
    )
    blocked = evaluate_day(db, settings, today, [])
    assert blocked.eligible_for_selection is False
    accepted = evaluate_day(db, settings, today, [], ignore_advance=True)
    assert accepted.eligible_for_selection is True


def test_date_request_allows_today_and_rejects_past(product_client: TestClient) -> None:
    today = _today().isoformat()
    past = (_today() - timedelta(days=1)).isoformat()
    ok = product_client.post(
        "/api/v1/schedule/date-requests",
        json={
            "desired_date": today,
            "customer_name": "Ana",
            "customer_email": "ana46@example.com",
            "intended_quantity": 2,
            "idempotency_key": "req-today-46",
        },
    )
    assert ok.status_code == 200, ok.text
    assert ok.json()["status"] == "pending"
    denied = product_client.post(
        "/api/v1/schedule/date-requests",
        json={
            "desired_date": past,
            "customer_name": "Ana",
            "customer_email": "ana46@example.com",
            "intended_quantity": 2,
            "idempotency_key": "req-past-46",
        },
    )
    assert denied.status_code == 422
    replay = product_client.post(
        "/api/v1/schedule/date-requests",
        json={
            "desired_date": today,
            "customer_name": "Ana",
            "customer_email": "ana46@example.com",
            "intended_quantity": 2,
            "idempotency_key": "req-today-46",
        },
    )
    assert replay.status_code == 200
    assert replay.json()["id"] == ok.json()["id"]


def test_focaccia_and_custom_do_not_qualify(db: Session) -> None:
    focaccia = _product(db, slug=FOCACCIA_SLUG, eligible=False, slot=0)
    bread = _product(db, slug=f"pao-vitrine-{uuid4().hex[:8]}", eligible=True, slot=1)
    assert all(item["slug"] != FOCACCIA_SLUG for item in eligible_500g_variants(db))
    assert reward_gaps(db) == []
    only_focaccia = [
        {
            "origin": "product",
            "product_id": str(focaccia.product_id),
            "variant_id": str(focaccia.id),
            "line_cents": 9000,
        }
    ]
    only_custom = [{"origin": "custom", "dough_type_id": str(uuid4()), "line_cents": 7000}]
    mixed = only_focaccia + [
        {
            "origin": "product",
            "product_id": str(bread.product_id),
            "variant_id": str(bread.id),
            "line_cents": 7000,
        }
    ]
    assert lines_qualify_for_stamp(db, only_focaccia) is False
    assert lines_qualify_for_stamp(db, only_custom) is False
    assert lines_qualify_for_stamp(db, mixed) is True

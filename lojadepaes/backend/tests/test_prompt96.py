"""Fechamento de período na Agenda: datas 10–20 bloqueadas, 21+ abertas."""

from datetime import date, datetime
from uuid import uuid4
from zoneinfo import ZoneInfo

from app.core.config import get_settings
from app.domain.bakery_time import bakery_today
from app.domain.errors import ConfirmationError
from app.domain.schedule import evaluate_day, preview_calendar, save_date_override
from app.domain.schedule_closures import (
    cancel_closure,
    list_closures,
    upsert_closure,
)
from app.domain.storefront_orders import quote_lines
from app.models.catalog import DoughType
from app.models.enums import EditorialStatus
from app.models.products import Product, ProductVariant
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from tests.admin_client import admin_client, login

assert admin_client

TRIP_START = date(2026, 10, 10)
TRIP_END = date(2026, 10, 18)
FIRST = date(2026, 10, 21)
BLOCKED = (date(2026, 10, 10), date(2026, 10, 18), date(2026, 10, 19), date(2026, 10, 20))


def _freeze(monkeypatch, day: date) -> None:
    zone = ZoneInfo("America/Sao_Paulo")
    now = datetime(day.year, day.month, day.day, 10, 0, tzinfo=zone)

    def today(_settings=None):
        return day

    def current(_settings=None):
        return now

    for target in (
        "app.domain.bakery_time.bakery_today",
        "app.domain.bakery_time.bakery_now",
        "app.domain.schedule.bakery_today",
        "app.domain.schedule.bakery_now",
        "app.domain.schedule_closures.bakery_today",
        "app.domain.date_requests.bakery_today",
        "app.domain.date_request_accept.bakery_today",
    ):
        if target.endswith("bakery_now"):
            monkeypatch.setattr(target, current)
        else:
            monkeypatch.setattr(target, today)


def _program(db: Session, *, pause: bool = False, actor: str = "admin:padaria"):
    return upsert_closure(
        db,
        get_settings(),
        start_date=TRIP_START,
        end_date=TRIP_END,
        first_eligible_date=FIRST,
        pause_intake=pause,
        internal_reason="Viagem",
        public_notice=None,
        actor_ref=actor,
    )


def _variant(db: Session) -> ProductVariant:
    from app.domain.recipe_bases import create_recipe_base

    base = create_recipe_base(db, code=f"rb-{uuid4().hex[:6]}", name="Massa 96")
    product = Product(
        name="Pão 96",
        slug=f"pao-96-{uuid4().hex[:8]}",
        short_description="teste",
        recipe_base_id=base.id,
        featured_image_alt="pão",
        editorial_status=EditorialStatus.PUBLISHED.value,
        is_available=True,
    )
    db.add(product)
    db.flush()
    variant = ProductVariant(
        product_id=product.id,
        display_name="500 g",
        presentation_type="weight",
        net_weight_grams=500,
        physical_units=1,
        price_cents=2490,
        currency="BRL",
        is_active=True,
    )
    db.add(variant)
    db.flush()
    return variant


def test_period_blocks_dates_even_if_override_opens_them(db: Session, monkeypatch) -> None:
    _freeze(monkeypatch, date(2026, 10, 9))
    settings = get_settings()
    save_date_override(
        db,
        settings,
        date(2026, 10, 10),
        open_state="open",
        daily_physical_limit=None,
        daily_base_limit=None,
        eligibility_mode="inherit",
        eligible_base_ids=None,
    )
    save_date_override(
        db,
        settings,
        date(2026, 10, 18),
        open_state="open",
        daily_physical_limit=None,
        daily_base_limit=None,
        eligibility_mode="inherit",
        eligible_base_ids=None,
    )
    _program(db)
    for day in BLOCKED:
        result = evaluate_day(db, settings, day, [])
        assert result.eligible_for_selection is False
        assert result.reason == "period_closed"
        assert "21 de outubro" in result.accessible_label
        assert "viagem" not in result.accessible_label.lower()
    opened = evaluate_day(db, settings, FIRST, [])
    assert opened.eligible_for_selection is True
    later = evaluate_day(db, settings, date(2026, 10, 24), [])
    assert later.eligible_for_selection is True
    preview = preview_calendar(db, settings, start=date(2026, 10, 10), end=date(2026, 10, 24))
    assert preview.closure_notice and "21 de outubro" in preview.closure_notice


def test_order_during_trip_for_eligible_date(db: Session, monkeypatch) -> None:
    _freeze(monkeypatch, date(2026, 10, 15))
    settings = get_settings()
    _program(db)
    variant = _variant(db)
    quote = quote_lines(
        db,
        settings,
        {"requested_date": FIRST.isoformat(), "items": [{"variant_id": str(variant.id), "quantity": 1}]},
    )
    assert quote["requested_date"] == FIRST.isoformat()
    try:
        quote_lines(
            db,
            settings,
            {
                "requested_date": date(2026, 10, 18).isoformat(),
                "items": [{"variant_id": str(variant.id), "quantity": 1}],
            },
        )
        raise AssertionError("18/10 deveria ser recusado")
    except Exception as exc:
        assert "não está disponível" in str(exc)


def test_intake_pause_blocks_new_entries_not_date_alone(db: Session, monkeypatch) -> None:
    _freeze(monkeypatch, date(2026, 10, 15))
    settings = get_settings()
    _program(db, pause=True)
    paused = evaluate_day(db, settings, FIRST, [])
    assert paused.eligible_for_selection is False
    assert paused.reason == "intake_paused"


def test_cancel_does_not_open_other_overlap(db: Session, monkeypatch) -> None:
    _freeze(monkeypatch, date(2026, 10, 9))
    settings = get_settings()
    first = _program(db)
    second = upsert_closure(
        db,
        settings,
        start_date=date(2026, 10, 19),
        end_date=date(2026, 10, 19),
        first_eligible_date=date(2026, 10, 21),
        pause_intake=False,
        internal_reason="Folga",
        public_notice=None,
        actor_ref="admin:padaria",
    )
    cancel_closure(db, first.id, actor_ref="admin:padaria")
    assert evaluate_day(db, settings, date(2026, 10, 10), []).reason != "period_closed"
    still = evaluate_day(db, settings, date(2026, 10, 19), [])
    assert still.reason == "period_closed"
    assert second.cancelled_at is None


def test_double_click_does_not_duplicate(db: Session, monkeypatch) -> None:
    _freeze(monkeypatch, date(2026, 10, 9))
    first = _program(db)
    second = _program(db)
    assert first.id == second.id
    listed = list_closures(db, get_settings())
    assert len(listed["items"]) == 1


def test_update_keeps_history(db: Session, monkeypatch) -> None:
    _freeze(monkeypatch, date(2026, 10, 9))
    settings = get_settings()
    row = _program(db, pause=True)
    updated = upsert_closure(
        db,
        settings,
        start_date=TRIP_START,
        end_date=TRIP_END,
        first_eligible_date=FIRST,
        pause_intake=False,
        internal_reason="Viagem",
        public_notice=None,
        actor_ref="admin:assistido",
    )
    assert updated.id == row.id
    assert updated.pause_intake is False
    from app.domain.schedule_closures import list_closure_events

    events = list_closure_events(db, row.id)
    assert {item["action"] for item in events} >= {"created", "updated"}
    assert any(item["actor_ref"] == "admin:assistido" for item in events)


def test_date_request_rejects_blocked_keeps_exceptional(client: TestClient, db: Session, monkeypatch) -> None:
    _freeze(monkeypatch, date(2026, 10, 9))
    _program(db)
    variant = _variant(db)
    db.commit()
    blocked = client.post(
        "/api/v1/schedule/date-requests",
        json={
            "desired_date": "2026-10-18",
            "customer_name": "Cliente 96",
            "customer_email": "cliente96@example.test",
            "intended_quantity": 1,
            "idempotency_key": f"96-block-{uuid4().hex}",
            "lines": [{"variant_id": str(variant.id), "quantity": 1}],
        },
    )
    assert blocked.status_code == 422
    assert "não está disponível" in blocked.text
    exceptional = client.post(
        "/api/v1/schedule/date-requests",
        json={
            "desired_date": bakery_today(get_settings()).isoformat(),
            "customer_name": "Cliente 96",
            "customer_email": "ok96@example.test",
            "intended_quantity": 1,
            "message": "fora da rotina, fora do fechamento",
            "idempotency_key": f"96-ok-{uuid4().hex}",
            "lines": [{"variant_id": str(variant.id), "quantity": 1}],
        },
    )
    assert exceptional.status_code == 200, exceptional.text


def test_admin_upsert_and_cancel(admin_client: TestClient, db: Session, monkeypatch) -> None:
    _freeze(monkeypatch, date(2026, 10, 9))
    csrf = login(admin_client)
    created = admin_client.post(
        "/api/v1/admin/schedule/closures",
        headers={"X-CSRF-Token": csrf},
        json={
            "start_date": "2026-10-10",
            "end_date": "2026-10-18",
            "first_eligible_date": "2026-10-21",
            "pause_intake": False,
            "internal_reason": "Viagem",
        },
    )
    assert created.status_code == 200, created.text
    body = created.json()
    assert body["blocked_until"] == "2026-10-20"
    assert body["pause_intake"] is False
    assert body["created_by"].startswith("admin:")
    replay = admin_client.post(
        "/api/v1/admin/schedule/closures",
        headers={"X-CSRF-Token": csrf},
        json={
            "start_date": "2026-10-10",
            "end_date": "2026-10-18",
            "first_eligible_date": "2026-10-21",
            "pause_intake": False,
            "internal_reason": "Viagem",
        },
    )
    assert replay.json()["id"] == body["id"]
    listed = admin_client.get("/api/v1/admin/schedule/closures").json()
    assert len(listed["items"]) == 1
    cancelled = admin_client.post(
        f"/api/v1/admin/schedule/closures/{body['id']}/cancel",
        headers={"X-CSRF-Token": csrf},
    )
    assert cancelled.json()["status"] == "cancelled"
    calendar = admin_client.post(
        "/api/v1/schedule/preview",
        json={"start": "2026-10-10", "end": "2026-10-21"},
    )
    assert calendar.status_code == 200
    day = next(item for item in calendar.json()["days"] if item["date"] == "2026-10-10")
    assert day["reason"] != "period_closed"

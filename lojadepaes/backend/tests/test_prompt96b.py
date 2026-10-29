"""Adendo 96B: quantidade pretendida sem default e orientação derivada da Agenda."""

from datetime import date, timedelta
from uuid import uuid4

from app.core.config import get_settings
from app.domain.attendance import date_request_reference
from app.domain.bakery_time import bakery_today
from app.domain.operations import operations_payload
from app.models.date_requests import DateRequest
from app.schemas.suggestions import QUANTITY_REQUIRED_MESSAGE
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from tests.admin_client import admin_client, login
from tests.test_prompt96 import FIRST, _freeze, _program, _variant

assert admin_client

QTY_MSG = QUANTITY_REQUIRED_MESSAGE


def _payload(**overrides):
    today = bakery_today(get_settings())
    body = {
        "desired_date": (today + timedelta(days=20)).isoformat(),
        "customer_name": "Cliente 96B",
        "customer_email": f"{uuid4().hex[:8]}@example.test",
        "idempotency_key": f"96b-{uuid4().hex}",
    }
    body.update(overrides)
    return body


def test_quantity_one_persists_and_shows_in_attendance(admin_client: TestClient, db: Session) -> None:
    created = admin_client.post("/api/v1/schedule/date-requests", json=_payload(intended_quantity=1))
    assert created.status_code == 200, created.text
    request_id = created.json()["id"]
    row = db.get(DateRequest, request_id)
    assert row is not None
    assert row.intended_quantity == 1
    replay = admin_client.post(
        "/api/v1/schedule/date-requests",
        json=_payload(intended_quantity=1, idempotency_key=row.idempotency_key),
    )
    assert replay.status_code == 200
    assert replay.json()["id"] == request_id
    assert db.query(DateRequest).filter_by(idempotency_key=row.idempotency_key).count() == 1
    login(admin_client)
    listed = admin_client.get("/api/v1/admin/orders").json()
    item = next(entry for entry in listed["items"] if entry["id"] == request_id)
    assert item["bread_units"] == 1
    assert item["public_reference"] == date_request_reference(request_id)


def test_empty_zero_negative_fractional_rejected(client: TestClient) -> None:
    missing = client.post("/api/v1/schedule/date-requests", json=_payload())
    assert missing.status_code == 422
    assert QTY_MSG in missing.text
    for value in (0, -1, 1.5, "0", ""):
        denied = client.post("/api/v1/schedule/date-requests", json=_payload(intended_quantity=value))
        assert denied.status_code == 422, denied.text
        assert QTY_MSG in denied.text


def test_operations_notice_follows_agenda_not_hardcoded_trip(
    client: TestClient, db: Session, monkeypatch
) -> None:
    _freeze(monkeypatch, date(2026, 10, 9))
    settings = get_settings()
    empty = operations_payload(settings, db)
    assert empty["closure_notice"] is None

    _program(db)
    db.commit()
    active = client.get("/api/v1/operations").json()
    assert active["closure_notice"]
    assert "21 de outubro" in active["closure_notice"]
    assert "viagem" not in active["closure_notice"].lower()

    from app.domain.schedule_closures import cancel_closure, load_active_closures, upsert_closure

    for row in load_active_closures(db):
        cancel_closure(db, row.id, actor_ref="admin:teste96b")
    db.commit()
    future = upsert_closure(
        db,
        settings,
        start_date=date(2026, 12, 10),
        end_date=date(2026, 12, 18),
        first_eligible_date=date(2026, 12, 21),
        pause_intake=False,
        internal_reason="Período futuro",
        public_notice=None,
        actor_ref="admin:teste96b",
    )
    db.commit()
    scheduled = operations_payload(settings, db)
    assert scheduled["closure_notice"]
    assert "21 de dezembro" in scheduled["closure_notice"]
    october = client.post(
        "/api/v1/schedule/date-requests",
        json=_payload(desired_date="2026-10-15", intended_quantity=1),
    )
    assert october.status_code == 200, october.text
    blocked_future = client.post(
        "/api/v1/schedule/date-requests",
        json=_payload(desired_date="2026-12-15", intended_quantity=1),
    )
    assert blocked_future.status_code == 422
    assert "não está disponível" in blocked_future.text
    assert future.id is not None


def test_blocked_date_still_rejected_quantity_does_not_open_it(
    client: TestClient, db: Session, monkeypatch
) -> None:
    _freeze(monkeypatch, date(2026, 10, 9))
    _program(db)
    variant = _variant(db)
    db.commit()
    blocked = client.post(
        "/api/v1/schedule/date-requests",
        json=_payload(
            desired_date="2026-10-18",
            intended_quantity=1,
            lines=[{"variant_id": str(variant.id), "quantity": 1}],
        ),
    )
    assert blocked.status_code == 422
    assert "não está disponível" in blocked.text
    eligible = client.post(
        "/api/v1/schedule/date-requests",
        json=_payload(
            desired_date=FIRST.isoformat(),
            intended_quantity=1,
            lines=[{"variant_id": str(variant.id), "quantity": 1}],
        ),
    )
    assert eligible.status_code == 200, eligible.text

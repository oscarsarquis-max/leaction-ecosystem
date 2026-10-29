"""Propor outra data de produção não muda status, reserva nem avisos."""

from datetime import timedelta

import pytest
from app.models.email_outbox import EmailOutbox
from app.models.managerial import OpsPushDelivery
from app.models.orders import Order
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from tests.admin_client import admin_client, login
from tests.contract.support import send_submitted

assert admin_client
pytestmark = pytest.mark.contract


def _counts(db: Session, order: Order) -> tuple[int, int]:
    emails = db.query(EmailOutbox).filter_by(order_id=order.id).count()
    pushes = db.query(OpsPushDelivery).filter(OpsPushDelivery.path == f"/admin/pedidos/{order.id}").count()
    return emails, pushes


def test_propose_date_keeps_status_reservation_and_notices(admin_client: TestClient, db: Session) -> None:
    # propose_production_date: só grava proposed_production_date. Hoje não enfileira e-mail nem push.
    order = send_submitted(db, "propose-date")
    original = order.production_local_date
    assert original is not None
    assert order.holds_capacity is False
    orders_before = db.query(Order).count()
    notices_before = _counts(db, order)
    db.commit()
    other = (original + timedelta(days=7)).isoformat()
    headers = {"X-CSRF-Token": login(admin_client)}
    same = admin_client.post(
        f"/api/v1/admin/orders/{order.id}/propose-date",
        headers=headers,
        json={"date": original.isoformat()},
    )
    assert same.status_code == 422, same.text
    assert same.json()["detail"] == "a data proposta é a mesma já pedida"
    changed = admin_client.post(
        f"/api/v1/admin/orders/{order.id}/propose-date",
        headers=headers,
        json={"date": other},
    )
    assert changed.status_code == 200, changed.text
    body = changed.json()
    assert body["status"] == "submitted"
    assert body["production_local_date"] == original.isoformat()
    assert body["proposed_production_date"] == other
    assert body["holds_capacity"] is False
    again = admin_client.post(
        f"/api/v1/admin/orders/{order.id}/propose-date",
        headers=headers,
        json={"date": other},
    )
    assert again.status_code == 200, again.text
    assert again.json()["proposed_production_date"] == other
    db.expire_all()
    stored = db.get(Order, order.id)
    assert stored is not None
    assert stored.status == "submitted"
    assert stored.holds_capacity is False
    assert stored.production_local_date == original
    assert db.query(Order).count() == orders_before
    assert _counts(db, stored) == notices_before

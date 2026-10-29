"""Push com VAPID fictício. O gateway de envio permanece falso."""

from datetime import timedelta

import pytest
from app.core.config import get_settings
from app.domain.web_push import save_subscription
from app.models.managerial import OpsPushDelivery
from cryptography.hazmat.primitives import serialization
from fastapi.testclient import TestClient
from py_vapid import Vapid
from py_vapid.utils import b64urlencode
from sqlalchemy.orm import Session
from tests.admin_client import TEST_ADMIN_USER, admin_client, login
from tests.contract.support import send_confirmed, variant
from tests.test_schedule import _next_iso

assert admin_client
pytestmark = pytest.mark.contract

_P256 = "B" * 80
_AUTH = "C" * 24


def _vapid_pair() -> tuple[str, str]:
    vapid = Vapid()
    vapid.generate_keys()
    private = b64urlencode(vapid.private_key.private_numbers().private_value.to_bytes(32, "big"))
    public = b64urlencode(
        vapid.public_key.public_bytes(
            serialization.Encoding.X962,
            serialization.PublicFormat.UncompressedPoint,
        )
    )
    return private, public


def _forbid_send(*_args, **_kwargs):
    raise AssertionError("gateway de envio deve permanecer falso")


def test_accept_and_auto_accept_enqueue_push_without_sending(
    admin_client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    private, public = _vapid_pair()
    monkeypatch.setenv("LOJADEPAES_VAPID_PRIVATE_KEY", private)
    monkeypatch.setenv("LOJADEPAES_VAPID_PUBLIC_KEY", public)
    monkeypatch.setenv("LOJADEPAES_MAIL_OPS_TO", "ops-107a@example.test")
    get_settings.cache_clear()
    monkeypatch.setattr("app.domain.web_push._network_sender", _forbid_send)
    bread = variant(db, "Pão push")
    db.commit()
    save_subscription(
        db,
        get_settings(),
        actor_ref=f"admin:{TEST_ADMIN_USER}",
        endpoint="https://updates.push.services.mozilla.com/wpush/v2/fake-107a",
        p256dh=_P256,
        auth_secret=_AUTH,
        label="ensaio 107A",
    )
    order = send_confirmed(db, "push-auto", bread)
    db.commit()
    auto = db.query(OpsPushDelivery).filter_by(kind="order_auto_accepted_admin").all()
    assert len(auto) == 1
    assert auto[0].status == "awaiting"
    assert auto[0].path == f"/admin/pedidos/{order.id}"

    desired = (_next_iso(3) + timedelta(days=21)).isoformat()
    created = admin_client.post(
        "/api/v1/schedule/date-requests",
        json={
            "desired_date": desired,
            "customer_name": "Cliente Exemplo Push",
            "customer_email": "push-107a@example.test",
            "intended_quantity": 1,
            "idempotency_key": "push-accept-107a",
        },
    )
    assert created.status_code == 200, created.text
    headers = {"X-CSRF-Token": login(admin_client)}
    accepted = admin_client.post(
        f"/api/v1/admin/date-requests/{created.json()['id']}",
        headers=headers,
        json={"action": "accept", "lines": [{"variant_id": str(bread.id), "quantity": 1}]},
    )
    assert accepted.status_code == 200, accepted.text
    db.expire_all()
    notice = db.query(OpsPushDelivery).filter_by(kind="acceptance_update").one()
    assert notice.status == "awaiting"
    assert notice.path == f"/admin/pedidos/{accepted.json()['converted_order_id']}"

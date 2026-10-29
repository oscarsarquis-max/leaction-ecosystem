"""Envio do pedido diante de falhas do Hub. Hub só por HTTP falso."""

import json
from uuid import uuid4

import httpx
import pytest
from app.core.config import get_settings
from app.domain import actionhub_client
from app.domain.storefront_orders import request_amount_checkout, lookup_amount_checkout
from app.models.email_outbox import EmailOutbox
from app.models.orders import Order
from app.models.payments import PaymentRecord
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from tests.contract.support import variant
from tests.db_fixtures import NEW_ORDER_ADDRESS
from tests.test_storefront import _next_wednesday

pytestmark = pytest.mark.contract


def _pix_body(amount: int, *, order_id: str = "hub-107b", amount_cents: object | None = None) -> dict:
    return {
        "order_id": order_id,
        "status": "PENDING",
        "amount_cents": amount if amount_cents is None else amount_cents,
        "method": "pix",
        "reused": False,
        "pix": {"qr_code": "00020126580014br.gov.bcb.pix"},
    }


def _install_http(monkeypatch: pytest.MonkeyPatch, post, get=None) -> None:
    monkeypatch.setattr("app.domain.storefront_orders.request_amount_checkout", request_amount_checkout)
    monkeypatch.setattr("app.domain.storefront_orders.lookup_amount_checkout", lookup_amount_checkout)
    monkeypatch.setattr(actionhub_client.httpx, "post", post)
    if get is not None:
        monkeypatch.setattr(actionhub_client.httpx, "get", get)


def _payments_on(monkeypatch: pytest.MonkeyPatch, base_url: str = "http://127.0.0.1:9") -> None:
    monkeypatch.setenv("LOJADEPAES_PUBLIC_PAYMENTS_ENABLED", "true")
    monkeypatch.setenv("LOJADEPAES_ACTIONHUB_APP_SECRET", "hub-107b-not-a-real-secret")
    monkeypatch.setenv("LOJADEPAES_ACTIONHUB_BASE_URL", base_url)
    get_settings.cache_clear()


def _payload(db: Session, key: str) -> dict:
    row = variant(db, f"Pão {key}", price=2490)
    db.commit()
    return {
        "requested_date": _next_wednesday(),
        "items": [{"variant_id": str(row.id), "quantity": 1}],
        "quoted_cents": row.price_cents,
        "customer_name": "Cliente Exemplo 107B",
        "customer_email": "cliente-107b@example.test",
        "idempotency_key": key,
        **NEW_ORDER_ADDRESS,
    }


def _not_found(_url, **_kwargs):
    return httpx.Response(404, json={"error": "missing"})


def _observe(db: Session, response_status: int, commits: int, exc: str | None) -> dict:
    order = db.query(Order).filter_by(customer_email="cliente-107b@example.test").one_or_none()
    db.expire_all()
    order = db.query(Order).filter_by(customer_email="cliente-107b@example.test").one_or_none()
    kinds: list[str] = []
    payment = None
    if order is not None:
        kinds = sorted(
            row.kind for row in db.query(EmailOutbox).filter_by(order_id=order.id).all()
        )
        payment = db.query(PaymentRecord).filter_by(order_id=order.id).one_or_none()
    return {
        "http": response_status,
        "exc": exc,
        "commits": commits,
        "status": None if order is None else order.status,
        "holds": None if order is None else order.holds_capacity,
        "kinds": kinds,
        "pay_status": None if payment is None else payment.financial_status,
        "external_reference": None if payment is None else payment.external_reference,
        "sanitized_error": None if payment is None else payment.sanitized_error,
    }


@pytest.mark.parametrize(
    "case",
    ["H1", "H2", "H3", "H4", "H5", "H6", "H7", "H8"],
)
def test_submit_hub_scenario_current(
    client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch, case: str
) -> None:
    """Caracteriza o envio. As asserções do comportamento esperado entram depois da correção."""
    _payments_on(monkeypatch)
    payload = _payload(db, f"hub-107b-{case}-{uuid4().hex[:8]}")
    commits = {"n": 0}
    real_commit = Session.commit

    def _count(self, *args, **kwargs):
        commits["n"] += 1
        return real_commit(self, *args, **kwargs)

    monkeypatch.setattr(Session, "commit", _count)

    def post(url, **kwargs):
        body = json.loads(kwargs.get("content") or b"{}") if kwargs.get("content") else kwargs.get("json") or {}
        amount = body.get("amount_cents", 2490)
        if case == "H1":
            return httpx.Response(201, json=_pix_body(amount))
        if case == "H2":
            raise httpx.TimeoutException("timeout")
        if case == "H3":
            return httpx.Response(503, json={"error": "down"})
        if case == "H4":
            return httpx.Response(409, json={"error": "conflict"})
        if case == "H5":
            return httpx.Response(201, json={"status": "PENDING", "amount_cents": amount, "method": "pix"})
        if case == "H6":
            return httpx.Response(201, json=_pix_body(amount, amount_cents="nao-numerico"))
        if case == "H8":
            return httpx.Response(201, json=_pix_body(amount))
        raise AssertionError(case)

    if case == "H8":
        def _boom(*_args, **_kwargs):
            raise RuntimeError("falha inesperada ao gravar a cobranca")

        monkeypatch.setattr("app.domain.storefront_orders.attach_hub_checkout", _boom)
        _install_http(monkeypatch, post, _not_found)
    elif case == "H7":
        settings = get_settings()
        monkeypatch.setattr(settings, "actionhub_base_url", "http://\x00hub", raising=False)
        monkeypatch.setattr("app.domain.storefront_orders.request_amount_checkout", request_amount_checkout)
        monkeypatch.setattr("app.domain.storefront_orders.lookup_amount_checkout", lookup_amount_checkout)
    else:
        _install_http(monkeypatch, post, _not_found)

    before = commits["n"]
    status = 0
    exc_name = None
    try:
        response = client.post("/api/v1/storefront/orders", json=payload)
        status = response.status_code
        body = response.json()
    except Exception as exc:
        exc_name = type(exc).__name__
        status = 500
        body = {}
    seen = _observe(db, status, commits["n"] - before, exc_name)
    assert exc_name is None
    assert status == 200
    assert body["public_reference"]
    assert body["access_token"]
    assert seen["commits"] == 1
    assert seen["status"] == "confirmed"
    assert seen["holds"] is True
    assert seen["kinds"] == ["order_accepted", "order_auto_accepted_admin"]
    assert seen["pay_status"] == "pending"
    if case == "H1":
        assert seen["external_reference"] == "hub-107b"
        assert seen["sanitized_error"] is None
        record = db.query(PaymentRecord).filter_by(external_reference="hub-107b").one()
        assert record.pix_qr_code
    else:
        assert seen["external_reference"] is None
        assert seen["sanitized_error"] is None


def test_public_checkout_keeps_sanitized_error_when_the_hub_fails(
    client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A página do pedido continua a gravar a falha. O envio automático é que não grava no meio."""
    monkeypatch.setenv("LOJADEPAES_PUBLIC_PAYMENTS_ENABLED", "false")
    monkeypatch.setenv("LOJADEPAES_ACTIONHUB_APP_SECRET", "hub-107b-not-a-real-secret")
    monkeypatch.setenv("LOJADEPAES_ACTIONHUB_BASE_URL", "http://127.0.0.1:9")
    get_settings.cache_clear()
    payload = _payload(db, f"hub-107b-public-{uuid4().hex[:8]}")
    created = client.post("/api/v1/storefront/orders", json=payload)
    assert created.status_code == 200, created.text
    token = created.json()["access_token"]
    reference = created.json()["public_reference"]

    monkeypatch.setenv("LOJADEPAES_PUBLIC_PAYMENTS_ENABLED", "true")
    get_settings.cache_clear()

    def post(_url, **_kwargs):
        return httpx.Response(503, json={"error": "down"})

    _install_http(monkeypatch, post, _not_found)
    failed = client.post(
        f"/api/v1/storefront/orders/{reference}/checkout",
        json={"method": "pix"},
        headers={"X-Order-Token": token},
    )
    assert failed.status_code == 422
    db.expire_all()
    order = db.query(Order).filter_by(public_reference=reference).one()
    record = db.query(PaymentRecord).filter_by(order_id=order.id).one()
    assert order.status == "confirmed"
    assert record.external_reference is None
    assert record.sanitized_error == "ActionHub indisponível"

"""E1: quem recebeu a entrega. Dados fictícios. Sem os campos, a confirmação segue igual."""

from uuid import uuid4

from app.core.config import get_settings
from app.domain.storefront_orders import email_access_token, hash_access_token
from app.models.email_outbox import EmailOutbox
from app.models.orders import Order, OrderStatusHistory
from app.models.payments import PaymentRecord
from app.schemas.storefront import StorefrontOrderOut
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from tests.admin_client import admin_client, login
from tests.db_fixtures import draft_order, priced_catalog

assert admin_client


def _headers(csrf: str) -> dict[str, str]:
    return {"X-CSRF-Token": csrf}


def _mail(db: Session) -> int:
    db.expire_all()
    return int(db.scalar(select(func.count()).select_from(EmailOutbox)) or 0)


def _history(db: Session, order_id) -> list[OrderStatusHistory]:
    db.expire_all()
    return list(
        db.scalars(
            select(OrderStatusHistory)
            .where(OrderStatusHistory.order_id == order_id)
            .order_by(OrderStatusHistory.created_at.asc())
        )
    )


def _ready_for_delivery(db: Session, client: TestClient, csrf: str, name: str) -> Order:
    catalog = priced_catalog(db)
    order = draft_order(db, catalog)
    order.customer_name = name
    order.customer_email = "conferencia@exemplo.test"
    db.commit()
    client.post(f"/api/v1/admin/orders/{order.id}/confirm", headers=_headers(csrf))
    db.expire_all()
    current = db.get(Order, order.id)
    assert current is not None
    db.add(
        PaymentRecord(
            order_id=current.id,
            provider="actionhub",
            idempotency_key=f"e1-{uuid4().hex}",
            expected_cents=current.total_cents or 0,
            currency="BRL",
            financial_status="paid",
            amount_paid_cents=current.total_cents,
        )
    )
    db.commit()
    started = client.post(
        f"/api/v1/admin/orders/{current.id}/start-production", headers=_headers(csrf)
    )
    assert started.status_code == 200, started.text
    db.expire_all()
    stored = db.get(Order, current.id)
    assert stored is not None
    return stored


def _public(client: TestClient, db: Session, order: Order) -> dict:
    db.expire_all()
    current = db.get(Order, order.id)
    assert current is not None
    token = email_access_token(get_settings(), current)
    current.access_token_hash = hash_access_token(token)
    db.commit()
    denied = client.get(f"/api/v1/storefront/orders/{current.public_reference}")
    assert denied.status_code == 401
    view = client.get(
        f"/api/v1/storefront/orders/{current.public_reference}",
        headers={"X-Order-Token": token},
    )
    assert view.status_code == 200, view.text
    body = view.json()
    StorefrontOrderOut(**body)
    return body


def test_confirm_without_new_fields_matches_today(admin_client: TestClient, db: Session) -> None:
    csrf = login(admin_client)
    order = _ready_for_delivery(db, admin_client, csrf, "Entrega Sem Dados Ficticia")
    mail_before = _mail(db)
    fidelity_before = order.fidelity_opt_in
    first = admin_client.post(
        f"/api/v1/admin/orders/{order.id}/confirm-delivery", headers=_headers(csrf)
    )
    assert first.status_code == 200, first.text
    body = first.json()
    assert body["status"] == "completed"
    assert body["visible_stage"] == "delivered"
    assert body["visible_label"] == "Entregue"
    assert body["delivery_confirmed_at"]
    assert body["delivery_received_by"] is None
    assert body["delivery_note"] is None
    stamp = body["delivery_confirmed_at"]
    proofs = [row for row in _history(db, order.id) if row.reason == "entrega confirmada pelo gestor"]
    assert len(proofs) == 1
    assert proofs[0].to_status == "completed"
    assert _mail(db) == mail_before
    db.expire_all()
    stored = db.get(Order, order.id)
    assert stored is not None
    assert stored.fidelity_opt_in is fidelity_before
    second = admin_client.post(
        f"/api/v1/admin/orders/{order.id}/confirm-delivery",
        headers=_headers(csrf),
        json={"received_by": "Nao Deve Gravar", "note": "Nao deve gravar"},
    )
    assert second.status_code == 200, second.text
    assert second.json()["delivery_confirmed_at"] == stamp
    assert second.json()["delivery_received_by"] is None
    assert second.json()["delivery_note"] is None
    assert second.json()["status"] == "completed"
    proofs_after = [
        row for row in _history(db, order.id) if row.reason == "entrega confirmada pelo gestor"
    ]
    assert len(proofs_after) == 1


def test_confirm_stores_and_cleans_the_receipt(admin_client: TestClient, db: Session) -> None:
    csrf = login(admin_client)
    order = _ready_for_delivery(db, admin_client, csrf, "Entrega Com Dados Ficticia")
    saved = admin_client.post(
        f"/api/v1/admin/orders/{order.id}/confirm-delivery",
        headers=_headers(csrf),
        json={"received_by": "  Maria   (portaria) ", "note": "  Deixado   na   portaria  "},
    )
    assert saved.status_code == 200, saved.text
    body = saved.json()
    assert body["delivery_received_by"] == "Maria (portaria)"
    assert body["delivery_note"] == "Deixado na portaria"
    assert body["status"] == "completed"
    blank = _ready_for_delivery(db, admin_client, csrf, "Entrega Campos Vazios Ficticia")
    cleared = admin_client.post(
        f"/api/v1/admin/orders/{blank.id}/confirm-delivery",
        headers=_headers(csrf),
        json={"received_by": "   ", "note": ""},
    )
    assert cleared.status_code == 200, cleared.text
    assert cleared.json()["delivery_received_by"] is None
    assert cleared.json()["delivery_note"] is None


def test_patch_only_after_delivery_and_keeps_status(admin_client: TestClient, db: Session) -> None:
    csrf = login(admin_client)
    order = _ready_for_delivery(db, admin_client, csrf, "Edicao Da Entrega Ficticia")
    early = admin_client.patch(
        f"/api/v1/admin/orders/{order.id}/delivery-info",
        headers=_headers(csrf),
        json={"received_by": "Cedo demais", "note": "nao"},
    )
    assert early.status_code == 409, early.text
    db.expire_all()
    untouched = db.get(Order, order.id)
    assert untouched is not None
    assert untouched.status == "in_production"
    assert untouched.delivery_confirmed_at is None
    assert not any(row.reason == "Dados da entrega atualizados" for row in _history(db, order.id))
    confirmed = admin_client.post(
        f"/api/v1/admin/orders/{order.id}/confirm-delivery",
        headers=_headers(csrf),
        json={"received_by": "Maria", "note": "Portaria"},
    )
    assert confirmed.status_code == 200, confirmed.text
    stamp = confirmed.json()["delivery_confirmed_at"]
    mail_before = _mail(db)
    edited = admin_client.patch(
        f"/api/v1/admin/orders/{order.id}/delivery-info",
        headers=_headers(csrf),
        json={"received_by": "  Maria   Souza ", "note": "   "},
    )
    assert edited.status_code == 200, edited.text
    body = edited.json()
    assert body["status"] == "completed"
    assert body["delivery_confirmed_at"] == stamp
    assert body["delivery_received_by"] == "Maria Souza"
    assert body["delivery_note"] is None
    assert _mail(db) == mail_before
    updates = [row for row in _history(db, order.id) if row.reason == "Dados da entrega atualizados"]
    assert len(updates) == 1
    assert updates[0].from_status == "completed"
    assert updates[0].to_status == "completed"


def test_public_view_hides_delivery_until_it_is_confirmed(
    admin_client: TestClient, db: Session
) -> None:
    csrf = login(admin_client)
    order = _ready_for_delivery(db, admin_client, csrf, "Pagina Publica Ficticia")
    before = _public(admin_client, db, order)
    assert before["delivery"] is None
    assert before["visitor_state"] == "accepted"
    saved = admin_client.post(
        f"/api/v1/admin/orders/{order.id}/confirm-delivery",
        headers=_headers(csrf),
        json={"received_by": "Joao da portaria", "note": "Deixado as 10h"},
    )
    assert saved.status_code == 200, saved.text
    after = _public(admin_client, db, order)
    assert after["visitor_state"] == before["visitor_state"]
    assert after["public_reference"] == before["public_reference"]
    assert after["customer_name"] == before["customer_name"]
    assert after["fidelity_opt_in"] == before["fidelity_opt_in"]
    assert after["order_kind"] == before["order_kind"]
    assert set(after) == set(before)
    assert after["delivery"]["received_by"] == "Joao da portaria"
    assert after["delivery"]["note"] == "Deixado as 10h"
    assert after["delivery"]["confirmed_at"]
    assert after["status"] == "completed"

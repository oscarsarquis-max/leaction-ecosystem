"""Matriz status × comando. Cada caso cita o comando do grafo."""

import pytest
from app.domain.errors import ConfirmationError, TransitionError, UnpaidProductionError
from app.domain.order_board import classify_payment, visible_stage_for_order
from app.domain.orders import (
    cancel_order,
    confirm_delivery,
    confirm_order,
    correct_ready_to_in_production,
    start_production,
    transition_order,
)
from app.models.enums import OrderStatus
from app.models.orders import OrderStatusHistory
from app.models.payments import PaymentRecord
from sqlalchemy.orm import Session
from tests.contract.support import send_confirmed, send_submitted

pytestmark = pytest.mark.contract


def _stage(db: Session, order) -> str:
    records = list(db.query(PaymentRecord).filter_by(order_id=order.id))
    return visible_stage_for_order(order, classify_payment(order, records))


def _authors(db: Session, order) -> list[str | None]:
    rows = (
        db.query(OrderStatusHistory)
        .filter_by(order_id=order.id)
        .order_by(OrderStatusHistory.created_at)
        .all()
    )
    return [row.actor_ref for row in rows]


def test_plain_submit_auto_accepts(db: Session) -> None:
    # grafo: submitted → confirmed por system:auto-accept
    order = send_confirmed(db)
    assert order.status == "confirmed"
    assert order.holds_capacity is True
    assert "system:auto-accept" in _authors(db, order)
    assert _stage(db, order) == "accepted"


def test_adaptation_stays_submitted(db: Session) -> None:
    # grafo: Finalizar compra com adaptação permanece submitted / Aberto
    order = send_submitted(db)
    assert order.status == "submitted"
    assert order.holds_capacity is False
    assert _stage(db, order) == "open"


def test_confirm_submitted_is_idempotent_after(db: Session) -> None:
    # comando confirm_order; segunda chamada não duplica histórico
    order = send_submitted(db)
    confirm_order(db, order.id, actor_ref="admin:contrato")
    db.flush()
    before = db.query(OrderStatusHistory).filter_by(order_id=order.id).count()
    again = confirm_order(db, order.id, actor_ref="admin:contrato")
    assert again.status == "confirmed"
    assert db.query(OrderStatusHistory).filter_by(order_id=order.id).count() == before


def test_cancel_requires_reason_and_releases_capacity_before_production(db: Session) -> None:
    # comando cancel_order a partir de confirmed
    order = send_confirmed(db, "contract-cancel")
    with pytest.raises(ConfirmationError, match="motivo"):
        cancel_order(db, order.id, None, actor_ref="admin:contrato")
    cancel_order(db, order.id, "cliente desistiu", actor_ref="admin:contrato")
    db.flush()
    assert order.status == "cancelled"
    assert order.holds_capacity is False
    assert _stage(db, order) == "cancelled"
    again = cancel_order(db, order.id, "de novo", actor_ref="admin:contrato")
    assert again.status == "cancelled"


def test_start_production_refuses_without_explicit_exception(db: Session) -> None:
    # comando start_production; pagamento pendente não é quitação
    order = send_confirmed(db, "contract-unpaid")
    with pytest.raises(UnpaidProductionError):
        start_production(db, order.id, actor_ref="admin:contrato", unpaid_exception=False)
    assert order.status == "confirmed"


def test_unpaid_exception_records_reason_and_does_not_notify(db: Session) -> None:
    # comando start_production com unpaid_exception
    from app.models.email_outbox import EmailOutbox

    order = send_confirmed(db, "contract-exception")
    before = db.query(EmailOutbox).filter_by(order_id=order.id).count()
    start_production(db, order.id, actor_ref="admin:contrato", unpaid_exception=True)
    db.flush()
    assert order.status == "in_production"
    assert order.production_started_at is not None
    assert order.holds_capacity is True
    assert _stage(db, order) == "in_production"
    assert db.query(EmailOutbox).filter_by(order_id=order.id).count() == before
    history = (
        db.query(OrderStatusHistory)
        .filter_by(order_id=order.id, to_status="in_production")
        .one()
    )
    assert history.actor_ref == "admin:contrato"
    assert "sem quitação" in (history.reason or "")


def test_second_start_production_is_idempotent(db: Session) -> None:
    order = send_confirmed(db, "contract-start-twice")
    start_production(db, order.id, actor_ref="admin:contrato", unpaid_exception=True)
    before = db.query(OrderStatusHistory).filter_by(order_id=order.id).count()
    start_production(db, order.id, actor_ref="admin:contrato", unpaid_exception=True)
    assert order.status == "in_production"
    assert db.query(OrderStatusHistory).filter_by(order_id=order.id).count() == before


def test_mark_ready_then_complete_without_delivery_stamp(db: Session) -> None:
    # transition_order READY e COMPLETED; concluir não carimba entrega
    order = send_confirmed(db, "contract-ready")
    start_production(db, order.id, actor_ref="admin:contrato", unpaid_exception=True)
    transition_order(
        db, order.id, OrderStatus.READY.value, "marcado pronto pelo gestor", actor_ref="admin:contrato"
    )
    assert order.status == "ready"
    assert _stage(db, order) == "ready_legacy"
    transition_order(db, order.id, OrderStatus.COMPLETED.value, "entregue ou retirado", actor_ref="admin:contrato")
    assert order.status == "completed"
    assert order.delivery_confirmed_at is None
    assert _stage(db, order) == "finalized"


def test_complete_from_in_production_is_refused_by_the_generic_transition(db: Session) -> None:
    # ALLOWED_TRANSITIONS não inclui in_production → completed
    order = send_confirmed(db, "contract-no-skip")
    start_production(db, order.id, actor_ref="admin:contrato", unpaid_exception=True)
    with pytest.raises(TransitionError):
        transition_order(db, order.id, OrderStatus.COMPLETED.value, "atalho", actor_ref="admin:contrato")
    assert order.status == "in_production"


def test_confirm_delivery_from_in_production_stamps_delivery(db: Session) -> None:
    # confirm_delivery sai de in_production para completed com carimbo
    order = send_confirmed(db, "contract-deliver")
    start_production(db, order.id, actor_ref="admin:contrato", unpaid_exception=True)
    confirm_delivery(db, order.id, actor_ref="admin:contrato")
    assert order.status == "completed"
    assert order.delivery_confirmed_at is not None
    assert _stage(db, order) == "delivered"
    before = db.query(OrderStatusHistory).filter_by(order_id=order.id).count()
    confirm_delivery(db, order.id, actor_ref="admin:contrato")
    assert db.query(OrderStatusHistory).filter_by(order_id=order.id).count() == before


def test_completed_cannot_be_cancelled(db: Session) -> None:
    order = send_confirmed(db, "contract-done")
    start_production(db, order.id, actor_ref="admin:contrato", unpaid_exception=True)
    confirm_delivery(db, order.id, actor_ref="admin:contrato")
    with pytest.raises(TransitionError, match="concluído"):
        cancel_order(db, order.id, "tarde", actor_ref="admin:contrato")


def test_ready_repair_returns_to_production_without_new_notice(db: Session) -> None:
    # correct_ready_to_in_production; sem rota HTTP
    from app.models.email_outbox import EmailOutbox

    order = send_confirmed(db, "contract-repair")
    start_production(db, order.id, actor_ref="admin:contrato", unpaid_exception=True)
    transition_order(db, order.id, OrderStatus.READY.value, "marcado pronto pelo gestor", actor_ref="admin:contrato")
    before = db.query(EmailOutbox).filter_by(order_id=order.id).count()
    correct_ready_to_in_production(db, order.id, actor_ref="assisted:107")
    assert order.status == "in_production"
    assert order.delivery_confirmed_at is None
    assert db.query(EmailOutbox).filter_by(order_id=order.id).count() == before
    with pytest.raises(TransitionError):
        correct_ready_to_in_production(db, order.id, actor_ref="assisted:107")


def test_cancel_after_production_keeps_capacity(db: Session) -> None:
    order = send_confirmed(db, "contract-hold")
    start_production(db, order.id, actor_ref="admin:contrato", unpaid_exception=True)
    cancel_order(db, order.id, "forno interrompido", actor_ref="admin:contrato")
    assert order.status == "cancelled"
    assert order.holds_capacity is True

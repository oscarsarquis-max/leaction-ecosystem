import pytest
from app.domain.errors import CapacityError, ConfirmationError, TransitionError
from app.domain.orders import cancel_order, confirm_order, transition_order
from app.models.enums import OrderStatus
from app.models.orders import OrderItem, OrderStatusHistory
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from tests.db_fixtures import draft_order, priced_catalog


def test_confirm_requires_price(db: Session) -> None:
    catalog = priced_catalog(db)
    catalog["dough"].base_price_cents = None
    order = draft_order(db, catalog)
    with pytest.raises(ConfirmationError, match="preço"):
        confirm_order(db, order.id)


def test_confirm_snapshots_and_blocks_catalog_delete(db: Session) -> None:
    catalog = priced_catalog(db)
    order = draft_order(db, catalog)
    confirm_order(db, order.id)
    db.flush()
    assert order.status == OrderStatus.CONFIRMED.value
    item = db.query(OrderItem).filter_by(order_id=order.id).one()
    assert item.dough_name_snapshot == catalog["dough"].name
    assert item.unit_price_cents == 1400
    assert item.line_total_cents == 1400
    catalog["dough"].name = "Nome novo no catálogo"
    db.flush()
    db.refresh(item)
    assert item.dough_name_snapshot == "Sourdough clássico"
    db.delete(catalog["dough"])
    with pytest.raises(IntegrityError):
        db.flush()


def test_confirm_is_idempotent(db: Session) -> None:
    catalog = priced_catalog(db)
    order = draft_order(db, catalog)
    first = confirm_order(db, order.id)
    second = confirm_order(db, order.id)
    assert first.status == second.status == OrderStatus.CONFIRMED.value
    history = db.query(OrderStatusHistory).filter_by(order_id=order.id).all()
    assert len(history) == 1


def test_cancel_releases_capacity_once(db: Session) -> None:
    catalog = priced_catalog(db)
    catalog["batch"].capacity_units = 1
    catalog["slot"].capacity_units = 1
    first = draft_order(db, catalog)
    confirm_order(db, first.id)
    second = draft_order(db, catalog)
    with pytest.raises(CapacityError):
        confirm_order(db, second.id)
    cancel_order(db, first.id, reason="cliente desistiu")
    cancel_order(db, first.id, reason="repetido")
    confirm_order(db, second.id)
    assert second.status == OrderStatus.CONFIRMED.value
    assert first.status == OrderStatus.CANCELLED.value


def test_cannot_reconfirm_cancelled(db: Session) -> None:
    catalog = priced_catalog(db)
    order = draft_order(db, catalog)
    confirm_order(db, order.id)
    cancel_order(db, order.id, reason="desistência de teste")
    with pytest.raises(TransitionError):
        confirm_order(db, order.id)


def test_incompatible_shape_blocked(db: Session) -> None:
    catalog = priced_catalog(db)
    order = draft_order(db, catalog, extras=False)
    from app.models.catalog import DoughShapeCompatibility

    db.query(DoughShapeCompatibility).delete()
    db.flush()
    with pytest.raises(ConfirmationError, match="formato"):
        confirm_order(db, order.id)


def test_transition_table(db: Session) -> None:
    catalog = priced_catalog(db)
    order = draft_order(db, catalog)
    confirm_order(db, order.id)
    transition_order(db, order.id, OrderStatus.IN_PRODUCTION.value)
    transition_order(db, order.id, OrderStatus.READY.value)
    transition_order(db, order.id, OrderStatus.COMPLETED.value)
    with pytest.raises(TransitionError):
        transition_order(db, order.id, OrderStatus.CANCELLED.value)


def test_complete_keeps_batch_capacity(db: Session) -> None:
    from app.domain.capacity import occupied_batch_units, occupied_slot_units

    catalog = priced_catalog(db)
    catalog["batch"].capacity_units = 1
    catalog["slot"].capacity_units = 1
    first = draft_order(db, catalog)
    confirm_order(db, first.id)
    transition_order(db, first.id, OrderStatus.IN_PRODUCTION.value)
    transition_order(db, first.id, OrderStatus.READY.value)
    transition_order(db, first.id, OrderStatus.COMPLETED.value)
    assert first.holds_capacity is True
    assert occupied_batch_units(db, catalog["batch"].id) == 1
    assert occupied_slot_units(db, catalog["slot"].id) == 1
    second = draft_order(db, catalog)
    with pytest.raises(CapacityError):
        confirm_order(db, second.id)


def test_cancel_after_production_keeps_capacity(db: Session) -> None:
    from app.domain.capacity import occupied_batch_units

    catalog = priced_catalog(db)
    catalog["batch"].capacity_units = 1
    first = draft_order(db, catalog)
    confirm_order(db, first.id)
    transition_order(db, first.id, OrderStatus.IN_PRODUCTION.value)
    cancel_order(db, first.id, reason="queimou na fornada")
    assert first.holds_capacity is True
    assert occupied_batch_units(db, catalog["batch"].id) == 1
    second = draft_order(db, catalog)
    with pytest.raises(CapacityError):
        confirm_order(db, second.id)


def test_cancel_without_reason_rejected(db: Session) -> None:
    catalog = priced_catalog(db)
    order = draft_order(db, catalog)
    confirm_order(db, order.id)
    with pytest.raises(ConfirmationError, match="motivo"):
        cancel_order(db, order.id, reason="  ")

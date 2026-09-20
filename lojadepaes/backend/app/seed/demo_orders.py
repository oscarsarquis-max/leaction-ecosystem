from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_engine, reset_engine
from app.models.catalog import BreadShape, DoughType
from app.models.enums import BatchStatus, FulfillmentModality, OrderStatus
from app.models.orders import Order, OrderInternalNote, OrderItem, OrderStatusHistory
from app.models.production import FulfillmentSlot, ProductionBatch
from app.seed import seed_demo_catalog, seed_id

ALLOWED = frozenset({"local", "development", "test", "demo"})


def seed_demo_orders(session: Session) -> None:
    """Pedidos claramente marcados como demonstração. Não altera preços do catálogo."""
    seed_demo_catalog(session)
    dough = session.get(DoughType, seed_id("dough", "sourdough-classico"))
    shape = session.get(BreadShape, seed_id("shape", "rustico-de-cesto"))
    if dough is None or shape is None:
        raise RuntimeError("catálogo demonstrativo ausente")

    batch_id = seed_id("demo-batch", "nao-comercial")
    batch = session.get(ProductionBatch, batch_id)
    if batch is None:
        start = datetime.now(UTC) + timedelta(days=30)
        available = start + timedelta(hours=12)
        batch = ProductionBatch(
            id=batch_id,
            code="DEMO-NAO-COMERCIAL",
            planned_start_at=start,
            breads_available_at=available,
            order_deadline_at=available,
            capacity_units=20,
            status=BatchStatus.CLOSED.value,
        )
        session.add(batch)
        session.flush()
    slot_id = seed_id("demo-slot", "retirada")
    slot = session.get(FulfillmentSlot, slot_id)
    if slot is None:
        slot = FulfillmentSlot(
            id=slot_id,
            production_batch_id=batch.id,
            starts_at=batch.breads_available_at + timedelta(minutes=30),
            ends_at=batch.breads_available_at + timedelta(hours=3),
            capacity_units=20,
            is_active=False,
            modality=FulfillmentModality.PICKUP.value,
        )
        session.add(slot)
        session.flush()

    specs = [
        ("DEMO-DRAFT-01", OrderStatus.DRAFT.value, False, False),
        ("DEMO-CONF-01", OrderStatus.CONFIRMED.value, True, False),
        ("DEMO-PROD-01", OrderStatus.IN_PRODUCTION.value, True, True),
        ("DEMO-READY-01", OrderStatus.READY.value, True, True),
        ("DEMO-DONE-01", OrderStatus.COMPLETED.value, True, True),
        ("DEMO-CANC-01", OrderStatus.CANCELLED.value, True, True),
    ]
    for reference, status, hold, started in specs:
        existing = session.scalar(select(Order).where(Order.public_reference == reference))
        if existing is not None:
            continue
        now = datetime.now(UTC)
        cancelled = status == OrderStatus.CANCELLED.value
        order = Order(
            public_reference=reference,
            status=status,
            fulfillment_modality=FulfillmentModality.PICKUP.value,
            fulfillment_slot_id=slot.id,
            production_batch_id=batch.id,
            customer_name="Cliente demonstração",
            customer_email="demo@example.test",
            customer_note="Pedido de demonstração — não é cliente real.",
            currency="BRL",
            holds_capacity=hold,
            confirmed_at=now if status != OrderStatus.DRAFT.value else None,
            production_started_at=now if started else None,
            ready_at=now if status in {OrderStatus.READY.value, OrderStatus.COMPLETED.value} else None,
            completed_at=now if status == OrderStatus.COMPLETED.value else None,
            cancelled_at=now if cancelled else None,
            cancellation_reason="cancelamento demonstrativo" if cancelled else None,
        )
        session.add(order)
        session.flush()
        session.add(
            OrderItem(
                order_id=order.id,
                dough_type_id=dough.id,
                bread_shape_id=shape.id,
                quantity=1,
                dough_name_snapshot=dough.name if hold else None,
                shape_name_snapshot=shape.name if hold else None,
                unit_price_cents=None,
                line_total_cents=None,
            )
        )
        session.add(
            OrderStatusHistory(
                order_id=order.id,
                from_status=None if status == OrderStatus.DRAFT.value else OrderStatus.DRAFT.value,
                to_status=status,
                reason="registro demonstrativo",
            )
        )
        session.add(
            OrderInternalNote(
                order_id=order.id,
                body="Nota interna de demonstração. Não usar como operação real.",
            )
        )
        session.flush()


def main() -> None:
    settings = get_settings()
    if settings.env not in ALLOWED:
        raise SystemExit(f"seed de pedidos demonstrativos recusado: LOJADEPAES_ENV={settings.env}")
    reset_engine()
    with Session(get_engine()) as session:
        seed_demo_orders(session)
        session.commit()
    print("pedidos demonstrativos aplicados (insert-if-missing por referência DEMO-*)")


if __name__ == "__main__":
    main()

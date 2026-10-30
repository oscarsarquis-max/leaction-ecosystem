"""Acrescenta no lojadepaes_capture os estados de trilha que o seed 107A não cobre.

Não apaga o banco e não mexe em pedido já semeado. Recusa qualquer URL que não
seja 127.0.0.1/localhost com o banco lojadepaes_capture. Nomes só de exemplo.
"""

from __future__ import annotations

import os
import sys
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
CAPTURE_URL = "postgresql+psycopg://lojadepaes:lojadepaes_dev@127.0.0.1:5438/lojadepaes_capture"


def assert_capture_target(url: str) -> None:
    from sqlalchemy.engine.url import make_url

    parsed = make_url(url)
    host = (parsed.host or "").lower()
    name = parsed.database or ""
    if host not in {"127.0.0.1", "localhost"} or name != "lojadepaes_capture":
        raise SystemExit(f"recusando seed: {host}/{name}")
    if any(token in url.lower() for token in ("amazonaws.com", "production", "mercadopago")):
        raise SystemExit("recusando seed: a URL parece produção")


def main() -> None:
    assert_capture_target(CAPTURE_URL)
    os.environ["LOJADEPAES_DATABASE_URL"] = CAPTURE_URL
    os.environ["LOJADEPAES_PUBLIC_PAYMENTS_ENABLED"] = "false"
    os.environ["LOJADEPAES_MAIL_IDENTITY_READY"] = "false"
    sys.path.insert(0, str(BACKEND))

    from sqlalchemy import create_engine, select
    from sqlalchemy.orm import sessionmaker

    from app.models.date_requests import DateRequest
    from app.models.orders import Order, OrderItem
    from app.models.payments import PaymentRecord

    engine = create_engine(CAPTURE_URL, pool_pre_ping=True)
    session = sessionmaker(bind=engine)()
    try:
        source = session.scalar(select(Order).where(Order.customer_email.like("%@example.test")).limit(1))
        if source is None:
            raise SystemExit("capture sem pedido de exemplo; rode scripts/p107a-seed-capture.py antes")
        item = session.scalar(select(OrderItem).where(OrderItem.order_id == source.id).limit(1))
        if item is None:
            raise SystemExit("pedido de exemplo sem item")
        past = date(2026, 10, 20)
        specs = [
            ("LPCAPESTORNO", {"status": "confirmed", "customer_name": "Cliente Exemplo Estorno"}, "refunded"),
            ("LPCAPPARCIAL", {"status": "confirmed", "customer_name": "Cliente Exemplo Parcial"}, "partial"),
            ("LPCAPFALHOU", {"status": "confirmed", "customer_name": "Cliente Exemplo Falhou"}, "failed"),
            ("LPCAPVERIF", {"status": "confirmed", "customer_name": "Cliente Exemplo Verificando"}, "unknown"),
            ("LPCAPSEMVAL", {"status": "confirmed", "customer_name": "Cliente Exemplo Sem valor", "total_cents": 0, "subtotal_cents": 0}, None),
            ("LPCAPRETIRA", {"status": "confirmed", "customer_name": "Cliente Exemplo Retirada", "fulfillment_modality": "pickup"}, "paid"),
            ("LPCAPINTER", {"status": "cancelled", "customer_name": "Cliente Exemplo Interrompido", "production_started_at": datetime.now(UTC), "cancellation_reason": "cliente de exemplo desistiu depois da produção"}, None),
            ("LPCAPPASSOU", {"status": "confirmed", "customer_name": "Cliente Exemplo Data passada", "production_local_date": past}, "paid"),
            ("LPCAPCOBRAN", {"status": "confirmed", "customer_name": "Cliente Exemplo Cobrança cancelada"}, "charge_cancelled"),
            ("LPCAPABERTO", {"status": "submitted", "customer_name": "Cliente Exemplo Sem cobrança"}, None),
        ]
        for reference, overrides, pay in specs:
            if session.scalar(select(Order.id).where(Order.public_reference == reference)):
                continue
            data = {
                column.name: getattr(source, column.name)
                for column in Order.__table__.columns
                if column.name not in {"id", "created_at", "updated_at"}
            }
            data.update(
                public_reference=reference,
                submit_idempotency_key=f"p109-{reference}",
                access_token_hash=None,
                fidelity_account_id=None,
                fidelity_campaign_id=None,
                fidelity_credit_id=None,
                source_date_request_id=None,
                holds_capacity=False,
                customer_email=f"{reference.lower()}@example.test",
                cancellation_reason=None,
                production_started_at=None,
                delivery_confirmed_at=None,
                cancelled_at=None,
            )
            data.update(overrides)
            order = Order(**data)
            session.add(order)
            session.flush()
            session.add(
                OrderItem(
                    order_id=order.id,
                    product_id=item.product_id,
                    product_variant_id=item.product_variant_id,
                    recipe_base_id=item.recipe_base_id,
                    quantity=1,
                    physical_units=item.physical_units or 1,
                    dough_name_snapshot=item.dough_name_snapshot or "Fermentação natural de trigo",
                    shape_name_snapshot=item.shape_name_snapshot,
                    unit_price_cents=0 if overrides.get("total_cents") == 0 else item.unit_price_cents,
                    line_total_cents=0 if overrides.get("total_cents") == 0 else item.line_total_cents,
                    net_weight_grams=item.net_weight_grams or 500,
                )
            )
            if pay:
                session.add(_payment(order, pay))
        if not session.scalar(select(DateRequest.id).where(DateRequest.idempotency_key == "p109-data-passada")):
            session.add(
                DateRequest(
                    desired_date=past,
                    customer_name="Cliente Exemplo Data vencida",
                    customer_email="data-vencida@example.test",
                    intended_quantity=2,
                    message="Solicitação de exemplo com data já passada.",
                    status="pending",
                    idempotency_key="p109-data-passada",
                    client_host="127.0.0.1",
                )
            )
        session.commit()
        print("capture 109 atualizado")
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
        engine.dispose()


def _payment(order, kind: str):
    from app.models.payments import PaymentRecord

    status = {
        "refunded": "refunded",
        "partial": "partially_refunded",
        "failed": "failed",
        "unknown": "unknown",
        "paid": "paid",
        "charge_cancelled": "cancelled",
    }[kind]
    paid = order.total_cents if status in {"refunded", "partially_refunded", "paid"} else None
    refunded = order.total_cents if status == "refunded" else (order.total_cents // 2 if status == "partially_refunded" else None)
    return PaymentRecord(
        order_id=order.id,
        provider="actionhub",
        external_reference=f"capture-{order.public_reference}",
        idempotency_key=f"p109-{order.public_reference}",
        expected_cents=order.total_cents or 0,
        currency="BRL",
        financial_status=status,
        amount_paid_cents=paid,
        amount_refunded_cents=refunded,
        method="pix",
    )


if __name__ == "__main__":
    main()

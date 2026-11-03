"""Acrescenta no lojadepaes_capture os casos visuais do 109F. Dados só de exemplo.

Não apaga nada. Recusa qualquer URL que não seja 127.0.0.1/localhost com o banco lojadepaes_capture.
Escreve readme/evidence/prompt-109f/capture-ids.json.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
CAPTURE_URL = "postgresql+psycopg://lojadepaes:lojadepaes_dev@127.0.0.1:5438/lojadepaes_capture"
OUT = ROOT / "readme" / "evidence" / "prompt-109f" / "capture-ids.json"


def assert_capture_target(url: str) -> None:
    from sqlalchemy.engine.url import make_url

    parsed = make_url(url)
    if (parsed.host or "").lower() not in {"127.0.0.1", "localhost"} or parsed.database != "lojadepaes_capture":
        raise SystemExit("recusando seed: não é o banco de captura local")


def next_weekday(start: date, weekday: int) -> date:
    return start + timedelta(days=(weekday - start.weekday()) % 7)


def main() -> None:
    assert_capture_target(CAPTURE_URL)
    os.environ["LOJADEPAES_DATABASE_URL"] = CAPTURE_URL
    os.environ["LOJADEPAES_PUBLIC_PAYMENTS_ENABLED"] = "false"
    os.environ["LOJADEPAES_MAIL_IDENTITY_READY"] = "false"
    sys.path.insert(0, str(BACKEND))

    from sqlalchemy import create_engine, select
    from sqlalchemy.orm import sessionmaker

    from app.core.config import get_settings
    from app.domain.bakery_time import bakery_today
    from app.models.date_requests import DateRequest
    from app.models.orders import Order, OrderItem
    from app.models.payments import PaymentRecord

    get_settings.cache_clear()
    settings = get_settings()
    engine = create_engine(CAPTURE_URL, pool_pre_ping=True)
    session = sessionmaker(bind=engine)()
    ids: dict[str, str] = {}
    try:
        source = session.scalar(select(Order).where(Order.customer_email.like("%@example.test")).limit(1))
        if source is None:
            raise SystemExit("capture sem pedido de exemplo")
        item = session.scalar(select(OrderItem).where(OrderItem.order_id == source.id).limit(1))
        today = bakery_today(settings)
        wednesday = next_weekday(today + timedelta(days=2), 2)
        saturday = wednesday + timedelta(days=3)

        def make(reference: str, *, email: str, name: str, produced: date) -> Order:
            found = session.scalar(select(Order).where(Order.public_reference == reference))
            if found is not None:
                ids[reference] = str(found.id)
                return found
            data = {
                c.name: getattr(source, c.name)
                for c in Order.__table__.columns
                if c.name not in {"id", "created_at", "updated_at"}
            }
            data.update(
                public_reference=reference,
                submit_idempotency_key=f"p109f-{reference}",
                access_token_hash=None,
                fidelity_account_id=None,
                fidelity_campaign_id=None,
                fidelity_credit_id=None,
                source_date_request_id=None,
                customer_email=email,
                customer_name=name,
                status="confirmed",
                holds_capacity=True,
                production_local_date=produced,
                requested_date=produced,
                date_change_origin=None,
                date_change_reason=None,
                date_change_actor=None,
                proposed_production_date=None,
                cancellation_reason=None,
                cancelled_at=None,
                production_started_at=None,
                delivery_confirmed_at=None,
                created_at=datetime.now(UTC) - timedelta(hours=1),
            )
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
                    physical_units=1,
                    dough_name_snapshot=item.dough_name_snapshot or "Pão de Café 500 g",
                    shape_name_snapshot=item.shape_name_snapshot,
                    unit_price_cents=item.unit_price_cents,
                    line_total_cents=item.line_total_cents,
                    net_weight_grams=item.net_weight_grams or 500,
                )
            )
            session.add(
                PaymentRecord(
                    order_id=order.id,
                    provider="actionhub",
                    external_reference=f"capture-{reference}",
                    idempotency_key=f"p109f-{reference}",
                    expected_cents=order.total_cents or 0,
                    currency="BRL",
                    financial_status="paid",
                    amount_paid_cents=order.total_cents,
                    method="pix",
                )
            )
            session.flush()
            ids[reference] = str(order.id)
            return order

        def request(key: str, desired: date, *, email: str, name: str) -> DateRequest:
            found = session.scalar(select(DateRequest).where(DateRequest.idempotency_key == key))
            if found is None:
                found = DateRequest(
                    desired_date=desired,
                    customer_name=name,
                    customer_email=email,
                    intended_quantity=1,
                    status="pending",
                    cart_context=[
                        {
                            "product_id": str(item.product_id),
                            "variant_id": str(item.product_variant_id),
                            "product_name": item.dough_name_snapshot or "Pão de Café 500 g",
                            "variant_name": item.shape_name_snapshot or "500 g",
                            "quantity": 1,
                        }
                    ],
                    idempotency_key=key,
                    client_host="127.0.0.1",
                )
                session.add(found)
                session.commit()
            return found

        make("LPF109ATEND", email="atendida@example.test", name="Cliente Exemplo Atendida", produced=wednesday)
        make("LPF109OUTRA", email="outra-data@example.test", name="Cliente Exemplo Outra Data", produced=saturday)
        session.commit()
        ids["date_request_mesma"] = str(
            request("p109f-mesma-data", wednesday, email="atendida@example.test", name="Cliente Exemplo Atendida").id
        )
        ids["date_request_outra"] = str(
            request(
                "p109f-outra-data",
                saturday + timedelta(days=7),
                email="outra-data@example.test",
                name="Cliente Exemplo Outra Data",
            ).id
        )
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(ids, ensure_ascii=False, indent=2), encoding="utf-8")
        print("capture 109f atualizado")
    finally:
        session.close()
        engine.dispose()


if __name__ == "__main__":
    main()

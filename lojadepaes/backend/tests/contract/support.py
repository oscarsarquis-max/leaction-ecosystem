"""Pedidos pelos caminhos de domínio usados na vitrine. Sem INSERT de pedido."""

from uuid import uuid4

from app.core.config import get_settings
from app.domain.recipe_bases import create_recipe_base
from app.domain.storefront_orders import submit_order
from app.models.enums import EditorialStatus
from app.models.orders import Order
from app.models.products import Product, ProductVariant
from sqlalchemy.orm import Session
from tests.db_fixtures import NEW_ORDER_ADDRESS
from tests.test_storefront import _next_wednesday


def variant(db: Session, name: str, price: int = 2490) -> ProductVariant:
    base = create_recipe_base(db, code=f"rb-{uuid4().hex[:6]}", name=f"Massa {name}")
    product = Product(
        name=name,
        slug=f"pao-{uuid4().hex[:8]}",
        short_description="crosta firme",
        recipe_base_id=base.id,
        featured_image_alt="pão",
        editorial_status=EditorialStatus.PUBLISHED.value,
        is_available=True,
    )
    db.add(product)
    db.flush()
    row = ProductVariant(
        product_id=product.id,
        display_name="500 g",
        presentation_type="weight",
        net_weight_grams=500,
        physical_units=1,
        price_cents=price,
        currency="BRL",
        is_active=True,
    )
    db.add(row)
    db.flush()
    return row


def send(db: Session, items: list[dict], quoted: int, key: str) -> Order:
    payload = {
        "requested_date": _next_wednesday(),
        "items": items,
        "quoted_cents": quoted,
        "customer_name": "Cliente Contrato",
        "customer_email": "contrato@example.com",
        "idempotency_key": key,
        **NEW_ORDER_ADDRESS,
    }
    order, _token = submit_order(db, get_settings(), payload)
    db.flush()
    return order


def send_confirmed(db: Session, key: str = "contract-plain", row: ProductVariant | None = None) -> Order:
    chosen = row or variant(db, "Pão contrato")
    return send(db, [{"variant_id": str(chosen.id), "quantity": 1}], chosen.price_cents, key)


def send_submitted(db: Session, key: str = "contract-review") -> Order:
    row = variant(db, "Pão com nota")
    return send(
        db,
        [
            {
                "variant_id": str(row.id),
                "quantity": 1,
                "adaptation": {"text": "sem sementes", "reason": "preference"},
            }
        ],
        2490,
        key,
    )

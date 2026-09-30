from __future__ import annotations

import secrets
from datetime import date
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.domain.email_outbox import enqueue_order_email
from app.domain.errors import ConfirmationError
from app.domain.house_fidelity import (
    BENEFIT_COPY,
    campaign_is_publicly_active,
    current_campaign,
    is_500g_unit,
    product_is_fidelity_eligible,
    reward_gaps,
    vitrine_products,
)
from app.domain.house_fidelity_ledger import reserve_credit
from app.domain.orders import new_public_reference
from app.domain.schedule import ProposedLine, evaluate_day, resolve_proposed_lines
from app.domain.storefront_orders import (
    hash_access_token,
    parse_delivery_address,
    parse_preferred_time,
)
from app.models.customers import CustomerAccount
from app.models.enums import EditorialStatus, OrderStatus
from app.models.orders import Order, OrderItem
from app.models.products import Product, ProductVariant


def eligible_500g_variants(session: Session) -> list[dict]:
    rows = list(
        session.scalars(
            select(ProductVariant)
            .join(Product, Product.id == ProductVariant.product_id)
            .where(
                Product.editorial_status == EditorialStatus.PUBLISHED.value,
                Product.is_available.is_(True),
                ProductVariant.is_active.is_(True),
                ProductVariant.net_weight_grams == 500,
            )
        )
    )
    showcase_ids = {item.id for item in vitrine_products(session)}
    items = []
    for variant in rows:
        if not is_500g_unit(variant):
            continue
        product = session.get(Product, variant.product_id)
        if product is None or not product_is_fidelity_eligible(product):
            continue
        if product.id not in showcase_ids:
            continue
        items.append(
            {
                "product_id": str(product.id),
                "variant_id": str(variant.id),
                "name": product.name,
                "slug": product.slug,
                "presentation": variant.display_name,
                "original_cents": variant.price_cents,
                "benefit_cents": variant.price_cents,
                "due_cents": 0,
            }
        )
    return items


def redeem_loaf(
    session: Session,
    settings: Settings,
    account: CustomerAccount,
    payload: dict,
) -> tuple[Order, str]:
    campaign = current_campaign(session)
    if campaign is None or not campaign_is_publicly_active(settings, campaign):
        raise ConfirmationError("a fidelidade da casa ainda não está em vigor")
    gaps = reward_gaps(session)
    if gaps:
        names = ", ".join(item["name"] for item in gaps)
        raise ConfirmationError(
            f"nem todos os pães da vitrine têm apresentação de 500 g ({names}). "
            "A Loja precisa completar o cadastro antes do resgate."
        )
    variant = session.get(ProductVariant, UUID(str(payload.get("variant_id"))))
    product = session.get(Product, variant.product_id) if variant is not None else None
    if (
        variant is None
        or product is None
        or not variant.is_active
        or product.editorial_status != EditorialStatus.PUBLISHED.value
        or not is_500g_unit(variant)
        or not product_is_fidelity_eligible(product)
        or product.id not in {item.id for item in vitrine_products(session)}
    ):
        raise ConfirmationError("escolha um pão de 500 g da vitrine")
    requested = date.fromisoformat(str(payload["requested_date"]))
    proposed = [ProposedLine(kind="product", variant_id=variant.id, quantity=1)]
    resolved = resolve_proposed_lines(session, proposed)
    day = evaluate_day(session, settings, requested, resolved)
    if day.status != "available" or not day.eligible_for_selection:
        raise ConfirmationError(day.accessible_label or "esta data não comporta o resgate")
    freight = 0
    original = variant.price_cents or 0
    token = secrets.token_urlsafe(32)
    address = parse_delivery_address(payload) if payload.get("delivery_street") else None
    order = Order(
        public_reference=new_public_reference(),
        status=OrderStatus.SUBMITTED.value,
        fulfillment_modality="delivery" if address else "pickup",
        preferred_time=parse_preferred_time(payload.get("preferred_time")),
        production_local_date=requested,
        customer_name=account.name,
        customer_email=account.email,
        customer_note=str(payload.get("customer_note") or "")[:2000],
        currency="BRL",
        subtotal_cents=original,
        delivery_fee_cents=freight,
        discount_cents=original,
        total_cents=freight,
        holds_capacity=False,
        access_token_hash=hash_access_token(token),
        submit_idempotency_key=str(payload.get("idempotency_key") or secrets.token_urlsafe(16)),
        order_kind="redemption",
        fidelity_opt_in=False,
        fidelity_account_id=account.id,
        fidelity_campaign_id=campaign.id,
        fidelity_rules_version=campaign.rules_version,
    )
    if address:
        order.delivery_street = address["delivery_street"]
        order.delivery_number = address["delivery_number"]
        order.delivery_complement = address["delivery_complement"]
        order.delivery_district = address["delivery_district"]
        order.delivery_city = address["delivery_city"]
        order.delivery_state = address["delivery_state"]
        order.delivery_postal_code = address["delivery_postal_code"]
    session.add(order)
    session.flush()
    reserve_credit(session, settings, account.id, order)
    session.add(
        OrderItem(
            order_id=order.id,
            product_id=product.id,
            product_variant_id=variant.id,
            recipe_base_id=product.recipe_base_id,
            physical_units=1,
            quantity=1,
            dough_name_snapshot=product.name,
            shape_name_snapshot=variant.display_name,
            unit_price_cents=original,
            line_total_cents=0,
            net_weight_grams=500,
        )
    )
    enqueue_order_email(session, settings, order, "order_submitted")
    session.flush()
    return order, token


def redeem_review(session: Session, variant_id: str) -> dict:
    variant = session.get(ProductVariant, UUID(variant_id))
    product = session.get(Product, variant.product_id) if variant is not None else None
    if variant is None or product is None:
        raise ConfirmationError("pão não encontrado")
    original = variant.price_cents or 0
    return {
        "name": product.name,
        "presentation": variant.display_name,
        "original_cents": original,
        "benefit_cents": original,
        "freight_cents": 0,
        "due_cents": 0,
        "notice": "Sem valor a pagar — benefício de fidelidade",
        "benefit": BENEFIT_COPY,
    }

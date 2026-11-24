"""Ponte da combo (M8) entre a Loja e o marketplace.

Único arquivo fora de `app/marketplace` que importa o módulo, além do registro das rotas
(`app/api/v1/__init__.py`). Com `marketplace_enabled` desligado, todas as rotas respondem 404.
"""

import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import AppSettings, DbSession, PreviewGate
from app.core.config import Settings
from app.domain.combo_house_order import (
    accept_deadline_for_date,
    address_line_of,
    bread_variants,
    combo_house_order_by_ref,
    combo_status_label,
    create_combo_house_order,
    find_combo_order,
    require_full_delivery_address,
)
from app.domain.email_outbox import enqueue_combo_order_customer_notice, enqueue_combo_order_partner_notice
from app.domain.operations import assert_orders_enabled
from app.domain.storefront_orders import (
    email_access_token,
    protected_order_url,
    require_order_token,
)
from app.marketplace import service
from app.marketplace.rules import MarketplaceError
from app.schemas.combo import ComboOrderCreatedOut, ComboOrderIn

logger = logging.getLogger("lojadepaes.combo")

router = APIRouter(prefix="/combos", tags=["combos"])


def _marketplace_on(settings: AppSettings) -> None:
    if not settings.marketplace_enabled:
        raise HTTPException(status_code=404, detail="não encontrado")


MarketplaceOn = Annotated[None, Depends(_marketplace_on)]


def _call(fn):
    try:
        return fn()
    except MarketplaceError as exc:
        raise HTTPException(status_code=exc.status, detail=exc.detail) from None


def _uuid_or_404(value: str) -> UUID:
    try:
        return UUID(value)
    except ValueError:
        raise HTTPException(status_code=404, detail="não encontrado") from None


def _enqueue_notices(
    db: Session,
    settings: Settings,
    sale: service.ComboSale,
    created,
    partner_order,
) -> None:
    """Avisos por e-mail: nunca derrubam o pedido já gravado (savepoint por aviso)."""
    order = created.order
    try:
        with db.begin_nested():
            enqueue_combo_order_customer_notice(
                db,
                settings,
                order,
                combo_ref=str(created.combo_ref),
                token=email_access_token(settings, order),
                parts=[{"brand_name": sale.partner.brand_name}],
            )
    except Exception as exc:
        logger.warning("aviso da combo ao cliente falhou: %s", type(exc).__name__)
    try:
        with db.begin_nested():
            to_address = service.partner_email(db, sale.partner.id)
            if to_address:
                enqueue_combo_order_partner_notice(
                    db,
                    settings,
                    order,
                    to_address=to_address,
                    partner_order_id=str(partner_order.id),
                    partner_reference=partner_order.public_reference,
                    product_name=partner_order.product_name,
                    quantity=partner_order.item_quantity,
                    accept_deadline=partner_order.accept_deadline,
                )
    except Exception as exc:
        logger.warning("aviso da combo ao parceiro falhou: %s", type(exc).__name__)


@router.get("/pedido/{ref}")
def combo_order_view(
    ref: str,
    db: DbSession,
    settings: AppSettings,
    _on: MarketplaceOn,
    _gate: PreviewGate,
    t: Annotated[str | None, Query()] = None,
) -> dict:
    combo_ref = _uuid_or_404(ref)
    order = combo_house_order_by_ref(db, combo_ref)
    require_order_token(db, settings, order.public_reference, t)
    parts = service.combo_partner_parts(db, combo_ref)
    house_cents = int(order.total_cents or 0)
    return {
        "combo_ref": str(combo_ref),
        "requested_date": order.production_local_date.isoformat() if order.production_local_date else None,
        "total_cents": house_cents + sum(int(part["amount_cents"]) for part in parts),
        "house": {
            "public_reference": order.public_reference,
            "status": order.status,
            "status_label": combo_status_label(order.status),
            "amount_cents": house_cents,
            "order_url": protected_order_url(settings, order),
        },
        "partners": parts,
    }


@router.get("/{combo_id}")
def combo_summary(
    combo_id: str,
    db: DbSession,
    _on: MarketplaceOn,
    _gate: PreviewGate,
) -> dict:
    sale = _call(lambda: service.combo_for_sale(db, _uuid_or_404(combo_id)))
    sellable = bread_variants(db, sale.combo.house_product_slug)
    if sellable is None or not sellable[1]:
        raise HTTPException(status_code=404, detail="não encontrado")
    body = service.combo_summary(db, sale)
    body["bread"]["variants"] = [
        {"id": str(variant.id), "name": variant.display_name, "price_cents": variant.price_cents}
        for variant in sellable[1]
    ]
    return body


@router.post("/{combo_id}/orders", response_model=ComboOrderCreatedOut)
def combo_submit_order(
    combo_id: str,
    payload: ComboOrderIn,
    db: DbSession,
    settings: AppSettings,
    _on: MarketplaceOn,
    _gate: PreviewGate,
) -> ComboOrderCreatedOut:
    assert_orders_enabled(settings)
    data = payload.model_dump(mode="json")
    replay = find_combo_order(db, settings, payload.idempotency_key)
    if replay is not None:
        return ComboOrderCreatedOut(combo_ref=str(replay.combo_ref), token=replay.token)

    sale = _call(lambda: service.combo_for_sale(db, _uuid_or_404(combo_id)))
    address = require_full_delivery_address(data)
    _call(
        lambda: service.assert_partner_delivery(
            sale.product,
            city=address["delivery_city"],
            district=address["delivery_district"],
            requested_date=payload.requested_date,
        )
    )
    product = sale.product
    partner_face_cents = payload.item_quantity * product.price_cents + (product.freight_cents or 0)
    created = create_combo_house_order(
        db,
        settings,
        data,
        bread_slug=sale.combo.house_product_slug,
        house_unit_price_cents=sale.combo.house_unit_price_cents,
        partner_fee_cents=sale.partner.fee_cents,
        partner_face_cents=partner_face_cents,
    )
    if not created.created:
        return ComboOrderCreatedOut(combo_ref=str(created.combo_ref), token=created.token)
    order = created.order
    partner_order = _call(
        lambda: service.create_partner_order(
            db,
            sale,
            combo_ref=created.combo_ref,
            house_order_id=order.id,
            requested_date=payload.requested_date,
            customer_name=order.customer_name or "",
            address_line=address_line_of(address),
            item_quantity=payload.item_quantity,
            accept_deadline=accept_deadline_for_date(db, settings, payload.requested_date),
            idempotency_key=payload.idempotency_key,
        )
    )
    _enqueue_notices(db, settings, sale, created, partner_order)
    return ComboOrderCreatedOut(combo_ref=str(created.combo_ref), token=created.token)

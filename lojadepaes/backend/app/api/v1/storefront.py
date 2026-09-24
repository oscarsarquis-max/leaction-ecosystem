from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy.orm import Session

from app.api.deps import AppSettings, DbSession, PreviewGate
from app.domain.adaptations import client_respond_adaptation
from app.domain.operations import assert_orders_enabled, assert_payments_enabled
from app.domain.payment_webhooks import apply_actionhub_webhook
from app.domain.storefront_orders import (
    accept_proposed_date,
    public_order_view,
    quote_lines,
    reconcile_checkout,
    require_order_token,
    set_delivery_address,
    start_checkout,
    submit_order,
)
from app.schemas.storefront import (
    AdaptationRespondIn,
    DeliveryAddressIn,
    StorefrontCheckoutIn,
    StorefrontCheckoutOut,
    StorefrontOrderOut,
    StorefrontQuoteIn,
    StorefrontSubmitIn,
    WebhookIn,
)

router = APIRouter(tags=["storefront"])


def _order_token(
    x_order_token: Annotated[str | None, Header()] = None,
) -> str | None:
    return x_order_token


def _view(session: Session, order, access_token: str | None = None) -> StorefrontOrderOut:
    payload = public_order_view(session, order)
    return StorefrontOrderOut(**payload, access_token=access_token)


@router.post("/storefront/quote")
def storefront_quote(
    payload: StorefrontQuoteIn, db: DbSession, settings: AppSettings, _: PreviewGate
) -> dict:
    assert_orders_enabled(settings)
    quote = quote_lines(db, settings, payload.model_dump(mode="json"))
    items = [{key: value for key, value in item.items() if key != "adaptation"} for item in quote["items"]]
    return {**quote, "items": items}


@router.post("/storefront/orders", response_model=StorefrontOrderOut)
def storefront_submit(
    payload: StorefrontSubmitIn, db: DbSession, settings: AppSettings, _: PreviewGate
) -> StorefrontOrderOut:
    assert_orders_enabled(settings)
    order, token = submit_order(db, settings, payload.model_dump(mode="json"))
    return _view(db, order, access_token=token)


@router.get("/storefront/orders/{public_reference}", response_model=StorefrontOrderOut)
def storefront_get_order(
    public_reference: str,
    db: DbSession,
    settings: AppSettings,
    _: PreviewGate,
    token: Annotated[str | None, Depends(_order_token)] = None,
) -> StorefrontOrderOut:
    order = require_order_token(db, settings, public_reference, token)
    return _view(db, order)


@router.post("/storefront/orders/{public_reference}/checkout", response_model=StorefrontCheckoutOut)
def storefront_checkout(
    public_reference: str,
    payload: StorefrontCheckoutIn,
    db: DbSession,
    settings: AppSettings,
    _: PreviewGate,
    token: Annotated[str | None, Depends(_order_token)] = None,
) -> StorefrontCheckoutOut:
    assert_payments_enabled(settings)
    order = require_order_token(db, settings, public_reference, token)
    result = start_checkout(db, settings, order, payload.method, replace=payload.replace)
    return StorefrontCheckoutOut(**result)


@router.post("/storefront/orders/{public_reference}/delivery-address", response_model=StorefrontOrderOut)
def storefront_delivery_address(
    public_reference: str,
    payload: DeliveryAddressIn,
    db: DbSession,
    settings: AppSettings,
    _: PreviewGate,
    token: Annotated[str | None, Depends(_order_token)] = None,
) -> StorefrontOrderOut:
    order = require_order_token(db, settings, public_reference, token)
    set_delivery_address(db, settings, order, payload.model_dump())
    return _view(db, order)


@router.post("/storefront/orders/{public_reference}/reconcile", response_model=StorefrontOrderOut)
def storefront_reconcile(
    public_reference: str,
    db: DbSession,
    settings: AppSettings,
    _: PreviewGate,
    token: Annotated[str | None, Depends(_order_token)] = None,
) -> StorefrontOrderOut:
    order = require_order_token(db, settings, public_reference, token)
    view = reconcile_checkout(db, settings, order)
    return StorefrontOrderOut(**view)


@router.post("/storefront/orders/{public_reference}/accept-date", response_model=StorefrontOrderOut)
def storefront_accept_date(
    public_reference: str,
    db: DbSession,
    settings: AppSettings,
    _: PreviewGate,
    token: Annotated[str | None, Depends(_order_token)] = None,
) -> StorefrontOrderOut:
    order = require_order_token(db, settings, public_reference, token)
    accept_proposed_date(db, settings, order)
    return _view(db, order)


@router.post("/storefront/orders/{public_reference}/items/{item_id}/adaptation", response_model=StorefrontOrderOut)
def storefront_respond_adaptation(
    public_reference: str,
    item_id: UUID,
    payload: AdaptationRespondIn,
    db: DbSession,
    settings: AppSettings,
    _: PreviewGate,
    token: Annotated[str | None, Depends(_order_token)] = None,
) -> StorefrontOrderOut:
    order = require_order_token(db, settings, public_reference, token)
    client_respond_adaptation(db, order, item_id, payload.decision)
    return _view(db, order)


@router.post("/webhooks/actionhub")
def actionhub_webhook(
    payload: WebhookIn,
    request: Request,
    db: DbSession,
    settings: AppSettings,
) -> dict:
    token = (payload.token or "").strip()
    authorization = request.headers.get("authorization") or ""
    if not token and authorization.lower().startswith("bearer "):
        token = authorization[7:].strip()
    result = apply_actionhub_webhook(db, settings, token)
    return result

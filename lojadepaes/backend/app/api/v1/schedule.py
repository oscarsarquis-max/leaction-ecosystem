from datetime import date
from uuid import UUID

from fastapi import APIRouter, Query, Response

from app.api.deps import AppSettings, ClientHost, DbSession, PreviewGate
from app.domain.bakery_time import bakery_today
from app.domain.date_request_accept import (
    accept_preview,
    complete_date_request,
    verify_date_request_token,
)
from app.domain.date_requests import create_date_request, get_date_request
from app.domain.errors import AuthError
from app.domain.operations import assert_date_requests_enabled
from app.domain.orders import order_delivery_pending
from app.domain.storefront_orders import protected_order_url
from app.models.orders import Order
from app.domain.schedule import ProposedLine, preview_calendar
from app.domain.suggestions import suggest_fornada
from app.schemas.schedule import CalendarQuery
from app.schemas.suggestions import (
    DateRequestCompleteIn,
    DateRequestCreateIn,
    DateRequestPublicDetailOut,
    DateRequestPublicOut,
    SuggestionsOut,
    SuggestionsQuery,
)

router = APIRouter(prefix="/schedule", tags=["schedule"])


def _preview(db, settings, payload: CalendarQuery) -> dict:
    result = preview_calendar(
        db,
        settings,
        start=payload.start,
        end=payload.end,
        selected=payload.selected,
        lines=[
            ProposedLine(
                kind=line.kind,
                quantity=line.quantity,
                variant_id=line.variant_id,
                dough_type_id=line.dough_type_id,
            )
            for line in payload.lines
        ],
    )
    return {
        "occupancy_enabled": result.occupancy_enabled,
        "reservation_policy": result.reservation_policy,
        "timezone": result.timezone,
        "business_date": bakery_today(settings).isoformat(),
        "selected_date": result.selected_date.isoformat() if result.selected_date else None,
        "selected_status": result.selected_status,
        "full_message": result.full_message,
        "alternatives": result.alternatives,
        "notice": result.notice,
        "review_message": result.review_message,
        "closure_notice": result.closure_notice,
        "days": [
            {
                "date": item.local_date.isoformat(),
                "status": item.status,
                "origin": item.origin,
                "daily_physical_limit": item.daily_physical_limit,
                "daily_base_limit": item.daily_base_limit,
                "committed_physical": item.committed_physical,
                "remaining_physical": item.remaining_physical,
                "committed_base_ids": item.committed_base_ids,
                "remaining_new_bases": item.remaining_new_bases,
                "reason": item.reason,
                "accessible_label": item.accessible_label,
                "weekday_name": item.weekday_name,
                "eligible": item.eligible_for_selection,
                "awaiting_review": item.awaiting_review,
                "at_capacity": item.at_capacity,
                "windows": item.windows,
            }
            for item in result.days
        ],
    }


@router.get("/calendar")
def get_calendar(
    db: DbSession,
    settings: AppSettings,
    response: Response,
    _: PreviewGate,
    start: date | None = Query(default=None),
    end: date | None = Query(default=None),
    selected: date | None = Query(default=None),
) -> dict:
    response.headers["Cache-Control"] = "no-store"
    return _preview(db, settings, CalendarQuery(start=start, end=end, selected=selected))


@router.post("/preview")
def post_preview(
    payload: CalendarQuery, db: DbSession, settings: AppSettings, response: Response, _: PreviewGate
) -> dict:
    response.headers["Cache-Control"] = "no-store"
    return _preview(db, settings, payload)


@router.post("/suggestions", response_model=SuggestionsOut)
def post_suggestions(
    payload: SuggestionsQuery,
    db: DbSession,
    settings: AppSettings,
    response: Response,
    _: PreviewGate,
) -> SuggestionsOut:
    response.headers["Cache-Control"] = "no-store"
    return suggest_fornada(db, settings, payload)


@router.post("/date-requests", response_model=DateRequestPublicOut)
def post_date_request(
    payload: DateRequestCreateIn,
    db: DbSession,
    settings: AppSettings,
    host: ClientHost,
    response: Response,
    _: PreviewGate,
) -> DateRequestPublicOut:
    assert_date_requests_enabled(settings)
    response.headers["Cache-Control"] = "no-store"
    row = create_date_request(db, settings, payload, client_host=host)
    return DateRequestPublicOut(
        id=row.id,
        status=row.status,
        desired_date=row.desired_date,
        message=(
            "Registramos sua solicitação de data. A Loja vai avaliar e responder por e-mail. "
            "Isso ainda não confirma a fornada."
        ),
    )


def _require_token(settings, row, token: str | None):
    if not verify_date_request_token(settings, row, token):
        raise AuthError("acesso à solicitação recusado")


def _public_date_request_detail(db, settings, row) -> DateRequestPublicDetailOut:
    preview = accept_preview(db, settings, row)
    converted = row.converted_order_id is not None
    order = db.get(Order, row.converted_order_id) if converted else None
    href = protected_order_url(settings, order) if order else None
    pending = order_delivery_pending(order) if order else not preview["has_address"]
    if converted:
        message = (
            "Pedido já formalizado. Pague e complete os dados de entrega no endereço protegido do pedido."
            if pending
            else "Pedido já formalizado. Use o endereço protegido do pedido para pagar."
        )
    else:
        message = (
            "Complete o endereço se quiser. Isso ainda não reserva a fornada. "
            "Depois do aceite você também pode pagar e completar a entrega no mesmo acesso."
        )
    return DateRequestPublicDetailOut(
        id=row.id,
        status=row.status,
        desired_date=row.desired_date,
        gaps=[] if converted else preview["gaps"],
        converted=converted,
        message=message,
        order_href=href,
        delivery_pending=pending,
    )


@router.get("/date-requests/{request_id}", response_model=DateRequestPublicDetailOut)
def get_date_request_public(
    request_id: UUID,
    db: DbSession,
    settings: AppSettings,
    response: Response,
    _: PreviewGate,
    token: str | None = Query(default=None),
) -> DateRequestPublicDetailOut:
    assert_date_requests_enabled(settings)
    response.headers["Cache-Control"] = "no-store"
    row = get_date_request(db, request_id)
    _require_token(settings, row, token)
    return _public_date_request_detail(db, settings, row)


@router.post("/date-requests/{request_id}/complete", response_model=DateRequestPublicDetailOut)
def complete_date_request_public(
    request_id: UUID,
    payload: DateRequestCompleteIn,
    db: DbSession,
    settings: AppSettings,
    response: Response,
    _: PreviewGate,
) -> DateRequestPublicDetailOut:
    assert_date_requests_enabled(settings)
    response.headers["Cache-Control"] = "no-store"
    row = get_date_request(db, request_id)
    _require_token(settings, row, payload.token)
    updated = complete_date_request(db, settings, row, payload.model_dump(exclude={"token"}))
    return _public_date_request_detail(db, settings, updated)

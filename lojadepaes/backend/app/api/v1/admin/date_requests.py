from uuid import UUID

from fastapi import APIRouter, Response
from sqlalchemy import select

from app.api.deps import AdminUser, AppSettings, DbSession
from app.domain.attendance import date_request_reference
from app.domain.date_request_accept import accept_preview, converted_order_href
from app.domain.date_requests import (
    apply_date_request_action,
    date_request_allowed_actions,
    date_request_reply_preview,
    get_date_request,
    list_date_requests,
)
from app.models.date_requests import DateRequest
from app.models.email_outbox import EmailOutbox
from app.schemas.suggestions import (
    DateRequestActionIn,
    DateRequestAdminList,
    DateRequestAdminOut,
    DateRequestCommercialPreviewIn,
    DateRequestEventOut,
    DateRequestNotificationOut,
)

router = APIRouter(prefix="/admin/date-requests", tags=["admin-date-requests"])


def _notifications(db, request_id: UUID) -> list[DateRequestNotificationOut]:
    rows = db.scalars(
        select(EmailOutbox)
        .where(EmailOutbox.date_request_id == request_id)
        .order_by(EmailOutbox.created_at.asc())
    )
    return [
        DateRequestNotificationOut(
            id=row.id, kind=row.kind, status=row.status, last_error=row.last_error
        )
        for row in rows
    ]


def _out(row: DateRequest, db, settings) -> DateRequestAdminOut:
    return DateRequestAdminOut(
        id=row.id,
        public_reference=date_request_reference(row.id),
        status=row.status,
        desired_date=row.desired_date,
        proposed_date=row.proposed_date,
        customer_name=row.customer_name,
        customer_email=row.customer_email,
        intended_quantity=row.intended_quantity,
        message=row.message,
        admin_note=row.admin_note,
        cart_context=row.cart_context,
        created_at=row.created_at.isoformat(),
        events=[
            DateRequestEventOut(
                action=event.action,
                actor_ref=event.actor_ref,
                detail=event.detail,
                created_at=event.created_at.isoformat(),
            )
            for event in row.events
        ],
        notifications=_notifications(db, row.id),
        allowed_actions=date_request_allowed_actions(row),
        reply_preview=date_request_reply_preview(settings),
        converted_order_id=row.converted_order_id,
        converted_order_href=converted_order_href(row),
        accept_preview=accept_preview(db, settings, row),
    )


@router.get("", response_model=DateRequestAdminList)
def admin_list_date_requests(
    db: DbSession, settings: AppSettings, principal: AdminUser, response: Response
) -> DateRequestAdminList:
    del principal
    response.headers["Cache-Control"] = "no-store"
    items = [_out(row, db, settings) for row in list_date_requests(db)]
    pending_count = sum(
        1 for row in items if row.status in {"pending", "alternative_proposed", "awaiting_details"}
    )
    return DateRequestAdminList(items=items, pending_count=pending_count)


@router.get("/{request_id}", response_model=DateRequestAdminOut)
def admin_get_date_request(
    request_id: UUID,
    db: DbSession,
    settings: AppSettings,
    principal: AdminUser,
    response: Response,
) -> DateRequestAdminOut:
    del principal
    response.headers["Cache-Control"] = "no-store"
    return _out(get_date_request(db, request_id), db, settings)


@router.post("/{request_id}/commercial-preview")
def admin_commercial_preview(
    request_id: UUID,
    payload: DateRequestCommercialPreviewIn,
    db: DbSession,
    settings: AppSettings,
    principal: AdminUser,
    response: Response,
) -> dict:
    """Cota produto e total sem gravar aceite, pedido, reserva ou aviso."""
    del principal
    response.headers["Cache-Control"] = "no-store"
    request = get_date_request(db, request_id)
    return accept_preview(
        db,
        settings,
        request,
        [line.model_dump() for line in payload.lines],
    )


@router.post("/{request_id}", response_model=DateRequestAdminOut)
def admin_act_date_request(
    request_id: UUID,
    payload: DateRequestActionIn,
    db: DbSession,
    settings: AppSettings,
    principal: AdminUser,
) -> DateRequestAdminOut:
    return _out(
        apply_date_request_action(
            db, settings, request_id, payload, actor_ref=principal.actor_ref
        ),
        db,
        settings,
    )

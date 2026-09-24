from uuid import UUID

from fastapi import APIRouter, Response

from app.api.deps import AdminUser, AppSettings, DbSession
from app.domain.date_requests import apply_date_request_action, list_date_requests
from app.models.date_requests import DateRequest
from app.schemas.suggestions import (
    DateRequestActionIn,
    DateRequestAdminList,
    DateRequestAdminOut,
    DateRequestEventOut,
)

router = APIRouter(prefix="/admin/date-requests", tags=["admin-date-requests"])


def _out(row: DateRequest) -> DateRequestAdminOut:
    return DateRequestAdminOut(
        id=row.id,
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
    )


@router.get("", response_model=DateRequestAdminList)
def admin_list_date_requests(
    db: DbSession, principal: AdminUser, response: Response
) -> DateRequestAdminList:
    del principal
    response.headers["Cache-Control"] = "no-store"
    return DateRequestAdminList(items=[_out(row) for row in list_date_requests(db)])


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
        )
    )

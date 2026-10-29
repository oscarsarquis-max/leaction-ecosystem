from uuid import UUID

from fastapi import APIRouter, Response
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.api.deps import AdminUser, AppSettings, DbSession
from app.domain.admin_orders import attendance_health
from app.domain.attendance import (
    OPS_SUMMARY_DEDUPE,
    attendance_summary,
    enqueue_authorized_ops_summary,
)
from app.domain.email_outbox import retry_and_deliver
from app.domain.errors import ConfirmationError, NotFoundError
from app.domain.owner_alerts import retry_owner_alert, save_whatsapp_destination
from app.domain.production_agenda import production_agenda
from app.domain.web_push import (
    enqueue_test_push,
    list_devices,
    process_due_pushes,
    push_status,
    revoke_device,
    save_subscription,
)
from app.models.email_outbox import EmailOutbox

router = APIRouter(prefix="/admin/ops", tags=["admin-ops"])


class WhatsAppDestinationIn(BaseModel):
    number: str = Field(min_length=8, max_length=20)


@router.get("/production-agenda")
def admin_production_agenda(
    db: DbSession,
    settings: AppSettings,
    principal: AdminUser,
    response: Response,
    year: int | None = None,
    month: int | None = None,
) -> dict:
    del principal
    response.headers["Cache-Control"] = "no-store"
    from app.domain.bakery_time import bakery_today

    today = bakery_today(settings)
    try:
        return production_agenda(db, settings, year or today.year, month or today.month)
    except ValueError as exc:
        raise NotFoundError(str(exc)) from exc


@router.post("/alert-channels/whatsapp")
def admin_save_whatsapp(
    payload: WhatsAppDestinationIn,
    db: DbSession,
    principal: AdminUser,
) -> dict:
    try:
        return save_whatsapp_destination(db, payload.number, author_ref=principal.actor_ref)
    except ValueError as exc:
        raise ConfirmationError(str(exc)) from exc


@router.post("/owner-alerts/{alert_id}/retry")
def admin_retry_owner_alert(
    alert_id: UUID,
    db: DbSession,
    settings: AppSettings,
    principal: AdminUser,
) -> dict:
    del principal
    try:
        row = retry_owner_alert(db, settings, alert_id)
    except LookupError as exc:
        raise NotFoundError(str(exc)) from exc
    return {
        "id": str(row.id),
        "channel": row.channel,
        "status": row.status,
        "last_error": row.last_error,
        "attempts": row.attempts,
    }


@router.get("/attendance-health")
def admin_attendance_health(db: DbSession, principal: AdminUser, response: Response) -> dict:
    del principal
    response.headers["Cache-Control"] = "no-store"
    return attendance_health(db)


@router.get("/attendance-summary")
def admin_attendance_summary(
    db: DbSession, settings: AppSettings, principal: AdminUser, response: Response
) -> dict:
    del principal
    response.headers["Cache-Control"] = "no-store"
    payload = attendance_summary(db, settings)
    existing = db.scalar(select(EmailOutbox).where(EmailOutbox.dedupe_key == OPS_SUMMARY_DEDUPE))
    payload["dispatch"] = None
    if existing is not None:
        payload["dispatch"] = {
            "id": str(existing.id),
            "status": existing.status,
            "last_error": existing.last_error,
            "provider_message_id": existing.provider_message_id,
            "sent_at": existing.sent_at.isoformat() if existing.sent_at else None,
        }
    return payload


@router.post("/attendance-summary/dispatch")
def admin_dispatch_attendance_summary(
    db: DbSession, settings: AppSettings, principal: AdminUser
) -> dict:
    del principal
    row = enqueue_authorized_ops_summary(db, settings)
    return {
        "id": str(row.id),
        "status": row.status,
        "dedupe_key": row.dedupe_key,
        "to_address": row.to_address,
        "last_error": row.last_error,
        "provider_message_id": row.provider_message_id,
    }


@router.post("/outbox/{outbox_id}/retry")
def admin_retry_outbox(
    outbox_id: UUID,
    db: DbSession,
    settings: AppSettings,
    principal: AdminUser,
) -> dict:
    del principal
    row = db.get(EmailOutbox, outbox_id)
    if row is None:
        raise NotFoundError("aviso não encontrado")
    retry_and_deliver(db, settings, row)
    return {
        "id": str(row.id),
        "status": row.status,
        "kind": row.kind,
        "last_error": row.last_error,
        "provider_message_id": row.provider_message_id,
    }


class PushSubscriptionIn(BaseModel):
    endpoint: str = Field(min_length=20, max_length=2000)
    p256dh: str = Field(min_length=16, max_length=200)
    auth: str = Field(min_length=16, max_length=200)
    label: str = Field(default="Este aparelho", max_length=40)


@router.get("/push")
def admin_push_status(settings: AppSettings, principal: AdminUser, response: Response) -> dict:
    del principal
    response.headers["Cache-Control"] = "no-store"
    return push_status(settings)


@router.get("/push/devices")
def admin_push_devices(db: DbSession, principal: AdminUser, response: Response) -> dict:
    response.headers["Cache-Control"] = "no-store"
    return {"devices": list_devices(db, principal.actor_ref), "receipt_confirmed": False}


@router.post("/push/subscriptions")
def admin_push_subscribe(
    payload: PushSubscriptionIn,
    db: DbSession,
    settings: AppSettings,
    principal: AdminUser,
) -> dict:
    try:
        row = save_subscription(
            db,
            settings,
            actor_ref=principal.actor_ref,
            endpoint=payload.endpoint,
            p256dh=payload.p256dh,
            auth_secret=payload.auth,
            label=payload.label,
        )
    except ValueError as exc:
        raise ConfirmationError(str(exc)) from exc
    return {"id": str(row.id), "active": row.active, "receipt_confirmed": False}


@router.post("/push/devices/{device_id}/revoke")
def admin_push_revoke(device_id: UUID, db: DbSession, principal: AdminUser) -> dict:
    try:
        row = revoke_device(
            db, principal.actor_ref, device_id, reason="desativado pelo administrador"
        )
    except LookupError as exc:
        raise NotFoundError(str(exc)) from exc
    return {"id": str(row.id), "active": row.active}


@router.post("/push/devices/{device_id}/test")
def admin_push_test(
    device_id: UUID,
    db: DbSession,
    settings: AppSettings,
    principal: AdminUser,
) -> dict:
    try:
        row = enqueue_test_push(db, settings, actor_ref=principal.actor_ref, device_id=device_id)
        process_due_pushes(db, settings)
    except LookupError as exc:
        raise NotFoundError(str(exc)) from exc
    except ValueError as exc:
        raise ConfirmationError(str(exc)) from exc
    db.refresh(row)
    return {
        "id": str(row.id),
        "status": row.status,
        "last_error": row.last_error,
        "receipt_confirmed": False,
    }

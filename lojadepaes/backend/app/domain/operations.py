from __future__ import annotations

from fastapi import HTTPException, Request
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.domain.admin_auth import SESSION_COOKIE, load_session
from app.domain.errors import ConfirmationError


def operations_payload(settings: Settings) -> dict:
    preview = settings.preview_protection
    orders = settings.public_orders_enabled
    payments = settings.public_payments_enabled
    dates = settings.public_date_requests_enabled
    message = None
    if preview or not orders:
        message = "A loja está em preparação. Pedidos estão desativados."
    return {
        "preview_protection": preview,
        "orders_enabled": orders,
        "payments_enabled": payments,
        "date_requests_enabled": dates,
        "message": message,
    }


def assert_orders_enabled(settings: Settings) -> None:
    if not settings.public_orders_enabled:
        raise ConfirmationError("pedidos estão desativados neste momento")


def assert_payments_enabled(settings: Settings) -> None:
    if not settings.public_payments_enabled:
        raise ConfirmationError("pagamentos estão desativados neste momento")


def assert_date_requests_enabled(settings: Settings) -> None:
    if not settings.public_date_requests_enabled:
        raise ConfirmationError("solicitações de data estão desativadas neste momento")


def require_preview_access(request: Request, db: Session, settings: Settings) -> None:
    if not settings.preview_protection:
        return
    token = request.cookies.get(SESSION_COOKIE)
    loaded = load_session(db, settings, token, rotate_csrf=False)
    if loaded is None:
        raise HTTPException(
            status_code=401,
            detail="prévia protegida: entre com a conta da padaria",
        )

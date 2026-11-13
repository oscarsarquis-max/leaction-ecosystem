"""Rotas do marketplace. Com a chave desligada, todas respondem 404."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Cookie, Depends, Header, HTTPException, Request, Response

from app.api.deps import AppSettings, DbSession, get_principal
from app.marketplace.auth import PARTNER_COOKIE, csrf_matches, open_session
from app.marketplace.rules import MarketplaceError
from app.marketplace.schemas import (
    BrandPatch,
    InviteAccept,
    LinkCreate,
    LinkEnd,
    PartnerCreate,
    PartnerLogin,
    PartnerPatch,
    ProductCreate,
    ProductPatch,
    ReviewIn,
)
from app.marketplace import service

ADMIN_COOKIE = "lojadepaes_admin_session"
CSRF_HEADER_NAME = "X-CSRF-Token"

admin_router = APIRouter(prefix="/admin/marketplace")
partner_router = APIRouter(prefix="/partner")


def _call(fn):
    try:
        return fn()
    except MarketplaceError as exc:
        raise HTTPException(status_code=exc.status, detail=exc.detail) from None


def _enabled(settings: AppSettings) -> None:
    if not settings.marketplace_enabled:
        raise HTTPException(status_code=404, detail="não encontrado")


def require_admin(
    request: Request,
    db: DbSession,
    settings: AppSettings,
    session_token: Annotated[str | None, Cookie(alias=ADMIN_COOKIE)] = None,
    csrf_header: Annotated[str | None, Header(alias=CSRF_HEADER_NAME)] = None,
):
    _enabled(settings)
    return get_principal(request, db, settings, session_token, csrf_header)


def require_partner(
    request: Request,
    db: DbSession,
    settings: AppSettings,
    session_token: Annotated[str | None, Cookie(alias=PARTNER_COOKIE)] = None,
    csrf_header: Annotated[str | None, Header(alias=CSRF_HEADER_NAME)] = None,
):
    _enabled(settings)
    opened = open_session(db, session_token)
    if opened is None:
        raise HTTPException(status_code=401, detail="não autenticado")
    user, partner, row = opened
    if request.method.upper() not in {"GET", "HEAD", "OPTIONS"} and not csrf_matches(row, csrf_header):
        raise HTTPException(status_code=403, detail="requisição recusada")
    return user, partner, row


def _set_partner_cookie(response: Response, settings, raw: str) -> None:
    response.set_cookie(
        PARTNER_COOKIE,
        raw,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
        max_age=60 * 60 * 12,
    )


@admin_router.get("/partners")
def admin_list_partners(db: DbSession, _admin=Depends(require_admin)):
    return _call(lambda: service.list_partners(db))


@admin_router.post("/partners", status_code=201)
def admin_create_partner(payload: PartnerCreate, db: DbSession, _admin=Depends(require_admin)):
    return _call(lambda: service.create_partner(db, payload.model_dump()))


@admin_router.get("/partners/{partner_id}")
def admin_get_partner(partner_id: UUID, db: DbSession, _admin=Depends(require_admin)):
    return _call(lambda: service.get_partner(db, partner_id))


@admin_router.patch("/partners/{partner_id}")
def admin_update_partner(partner_id: UUID, payload: PartnerPatch, db: DbSession, _admin=Depends(require_admin)):
    return _call(lambda: service.update_partner(db, partner_id, payload.model_dump(exclude_unset=True)))


@admin_router.post("/partners/{partner_id}/pause")
def admin_pause_partner(partner_id: UUID, db: DbSession, _admin=Depends(require_admin)):
    return _call(lambda: service.pause_partner(db, partner_id))


@admin_router.post("/partners/{partner_id}/links", status_code=201)
def admin_create_link(partner_id: UUID, payload: LinkCreate, db: DbSession, _admin=Depends(require_admin)):
    return _call(lambda: service.create_link(db, partner_id, payload.model_dump()))


@admin_router.post("/partners/{partner_id}/links/{link_id}/end")
def admin_end_link(
    partner_id: UUID, link_id: UUID, payload: LinkEnd, db: DbSession, _admin=Depends(require_admin)
):
    return _call(lambda: service.end_link(db, partner_id, link_id, payload.model_dump()))


@admin_router.get("/products")
def admin_products(db: DbSession, status: str | None = None, _admin=Depends(require_admin)):
    return _call(lambda: service.list_products_admin(db, status))


@admin_router.get("/products/{product_id}/reviews")
def admin_product_reviews(product_id: UUID, db: DbSession, _admin=Depends(require_admin)):
    return _call(lambda: service.list_product_reviews(db, product_id))


@admin_router.post("/products/{product_id}/review")
def admin_review(
    product_id: UUID, payload: ReviewIn, db: DbSession, admin=Depends(require_admin)
):
    return _call(lambda: service.review_product(db, product_id, payload.model_dump(), admin.actor_ref))


@admin_router.post("/products/{product_id}/pause")
def admin_pause_product(product_id: UUID, db: DbSession, _admin=Depends(require_admin)):
    return _call(lambda: service.pause_product(db, product_id))


@partner_router.post("/invite/accept")
def partner_accept(payload: InviteAccept, response: Response, db: DbSession, settings: AppSettings):
    _enabled(settings)

    def _accept():
        body, raw, _csrf = service.accept_invite(db, payload.token, payload.password)
        _set_partner_cookie(response, settings, raw)
        return body

    return _call(_accept)


@partner_router.post("/login")
def partner_login(payload: PartnerLogin, response: Response, db: DbSession, settings: AppSettings):
    _enabled(settings)

    def _login():
        body, raw, _csrf = service.login(db, payload.email, payload.password)
        _set_partner_cookie(response, settings, raw)
        return body

    return _call(_login)


@partner_router.post("/logout", status_code=204)
def partner_logout(db: DbSession, principal=Depends(require_partner)):
    _user, _partner, row = principal
    db.delete(row)
    outgoing = Response(status_code=204)
    outgoing.delete_cookie(PARTNER_COOKIE, path="/")
    return outgoing


@partner_router.get("/me")
def partner_me(principal=Depends(require_partner)):
    user, partner, row = principal
    return service.me(partner, user, row.csrf_token)


@partner_router.patch("/profile")
def partner_profile(payload: BrandPatch, db: DbSession, principal=Depends(require_partner)):
    user, partner, _row = principal
    return _call(lambda: service.update_profile(db, partner, user, payload.model_dump(exclude_unset=True)))


@partner_router.get("/products")
def partner_products(db: DbSession, principal=Depends(require_partner)):
    _user, partner, _row = principal
    return service.list_my_products(db, partner)


@partner_router.post("/products", status_code=201)
def partner_create_product(payload: ProductCreate, db: DbSession, principal=Depends(require_partner)):
    _user, partner, _row = principal
    return _call(lambda: service.create_product(db, partner, payload.model_dump()))


@partner_router.patch("/products/{product_id}")
def partner_update_product(
    product_id: UUID, payload: ProductPatch, db: DbSession, principal=Depends(require_partner)
):
    _user, partner, _row = principal
    return _call(
        lambda: service.update_product(db, partner, product_id, payload.model_dump(exclude_unset=True))
    )


@partner_router.post("/products/{product_id}/submit")
def partner_submit(product_id: UUID, db: DbSession, principal=Depends(require_partner)):
    _user, partner, _row = principal
    return _call(lambda: service.submit_product(db, partner, product_id))


@partner_router.get("/products/{product_id}/reviews")
def partner_reviews(product_id: UUID, db: DbSession, principal=Depends(require_partner)):
    _user, partner, _row = principal
    return _call(lambda: service.list_reviews(db, partner, product_id))

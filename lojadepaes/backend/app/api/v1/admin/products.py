from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Response, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.exc import IntegrityError

from app.api.deps import AdminUser, AppSettings, DbSession
from app.domain.errors import ProductError
from app.domain.media import media_file
from app.domain.products import (
    admin_media,
    archive_product,
    attach_image,
    catch_slug_conflict,
    create_product,
    get_product,
    list_admin_products,
    product_detail,
    publish_product,
    set_availability,
    unpublish_product,
    update_product,
)
from app.schemas.products import (
    AdminProductDetail,
    AdminProductList,
    AvailabilityIn,
    ProductListQuery,
    ProductSaveIn,
)

router = APIRouter(prefix="/admin/products", tags=["admin-products"])
media_router = APIRouter(prefix="/admin/media", tags=["admin-media"])


def _save(db, actor_ref: str, payload: ProductSaveIn, product_id: UUID | None) -> AdminProductDetail:
    try:
        if product_id is None:
            product = create_product(db, actor_ref, payload)
        else:
            product = update_product(db, product_id, actor_ref, payload)
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        catch_slug_conflict(exc)
    return product_detail(db, product)


@router.get("", response_model=AdminProductList)
def admin_list_products(
    db: DbSession,
    principal: AdminUser,
    query: Annotated[ProductListQuery, Depends()],
) -> AdminProductList:
    del principal
    return list_admin_products(
        db,
        query=query.query,
        status=query.status,
        available=query.available,
        page=query.page,
        page_size=query.page_size,
    )


@router.post("", response_model=AdminProductDetail)
def admin_create_product(
    payload: ProductSaveIn, db: DbSession, principal: AdminUser
) -> AdminProductDetail:
    return _save(db, principal.actor_ref, payload, None)


@router.get("/{product_id}", response_model=AdminProductDetail)
def admin_get_product(product_id: UUID, db: DbSession, principal: AdminUser) -> AdminProductDetail:
    del principal
    return product_detail(db, get_product(db, product_id))


@router.put("/{product_id}", response_model=AdminProductDetail)
def admin_update_product(
    product_id: UUID, payload: ProductSaveIn, db: DbSession, principal: AdminUser
) -> AdminProductDetail:
    return _save(db, principal.actor_ref, payload, product_id)


@router.post("/{product_id}/image", response_model=AdminProductDetail)
async def admin_upload_image(
    product_id: UUID,
    db: DbSession,
    settings: AppSettings,
    principal: AdminUser,
    file: UploadFile = File(...),
    alt: Annotated[str | None, Form()] = None,
) -> AdminProductDetail:
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await file.read(1024 * 1024)
        if not chunk:
            break
        total += len(chunk)
        if total > settings.media_max_bytes:
            raise ProductError("a imagem excede o limite de 8 MB")
        chunks.append(chunk)
    product = attach_image(db, settings, product_id, principal.actor_ref, b"".join(chunks), alt)
    db.flush()
    return product_detail(db, product)


@router.post("/{product_id}/publish", response_model=AdminProductDetail)
def admin_publish_product(
    product_id: UUID, db: DbSession, principal: AdminUser
) -> AdminProductDetail:
    product = publish_product(db, product_id, principal.actor_ref)
    db.flush()
    return product_detail(db, product)


@router.post("/{product_id}/unpublish", response_model=AdminProductDetail)
def admin_unpublish_product(
    product_id: UUID, db: DbSession, principal: AdminUser
) -> AdminProductDetail:
    product = unpublish_product(db, product_id, principal.actor_ref)
    db.flush()
    return product_detail(db, product)


@router.post("/{product_id}/archive", response_model=AdminProductDetail)
def admin_archive_product(
    product_id: UUID, db: DbSession, principal: AdminUser
) -> AdminProductDetail:
    product = archive_product(db, product_id, principal.actor_ref)
    db.flush()
    return product_detail(db, product)


@router.post("/{product_id}/availability", response_model=AdminProductDetail)
def admin_set_availability(
    product_id: UUID, payload: AvailabilityIn, db: DbSession, principal: AdminUser
) -> AdminProductDetail:
    product = set_availability(db, product_id, principal.actor_ref, payload.is_available)
    db.flush()
    return product_detail(db, product)


@media_router.get("/{media_id}")
def admin_get_media(media_id: UUID, db: DbSession, settings: AppSettings, principal: AdminUser) -> Response:
    del principal
    asset = admin_media(db, media_id)
    path = media_file(settings, asset.stored_name)
    return FileResponse(
        path,
        media_type=asset.content_type,
        headers={"X-Content-Type-Options": "nosniff", "Cache-Control": "private, max-age=300"},
    )

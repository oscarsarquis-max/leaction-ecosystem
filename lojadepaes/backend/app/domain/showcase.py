from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.domain.errors import NotFoundError, ProductError
from app.domain.products import from_price_cents, public_list_item
from app.models.enums import EditorialStatus
from app.models.products import Product, ShowcaseSlot
from app.schemas.admin import MoneyOut
from app.schemas.catalog_public import PublicProductList
from app.schemas.showcase import (
    ShowcaseAdminOut,
    ShowcaseProductOut,
    ShowcaseSlotIn,
    ShowcaseSlotOut,
)

SLOT_COUNT = 10


def ensure_slots(session: Session) -> list[ShowcaseSlot]:
    rows = list(session.scalars(select(ShowcaseSlot).order_by(ShowcaseSlot.position)))
    by_position = {row.position: row for row in rows}
    created = False
    for position in range(1, SLOT_COUNT + 1):
        if position not in by_position:
            row = ShowcaseSlot(position=position, product_id=None)
            session.add(row)
            by_position[position] = row
            created = True
    if created:
        session.flush()
        rows = list(session.scalars(select(ShowcaseSlot).order_by(ShowcaseSlot.position)))
    return rows


def _slot_query(session: Session):
    return (
        select(ShowcaseSlot)
        .options(
            selectinload(ShowcaseSlot.product).selectinload(Product.variants),
            selectinload(ShowcaseSlot.product).selectinload(Product.featured_image),
            selectinload(ShowcaseSlot.product).selectinload(Product.composition),
        )
        .order_by(ShowcaseSlot.position)
    )


def _product_summary(product: Product) -> ShowcaseProductOut:
    media_url = None
    if product.featured_image_id is not None:
        media_url = f"/api/v1/catalog/media/{product.featured_image_id}"
        if product.editorial_status != EditorialStatus.PUBLISHED.value:
            media_url = f"/api/v1/admin/media/{product.featured_image_id}"
    return ShowcaseProductOut(
        id=product.id,
        name=product.name,
        slug=product.slug,
        editorial_status=product.editorial_status,
        is_available=product.is_available,
        thumbnail_url=media_url,
        from_price=MoneyOut(cents=from_price_cents(list(product.variants))),
    )


def clear_product_from_showcase(session: Session, product_id: UUID) -> None:
    rows = list(session.scalars(select(ShowcaseSlot).where(ShowcaseSlot.product_id == product_id)))
    if not rows:
        return
    for row in rows:
        row.product_id = None
    session.flush()


def fill_empty_showcase_slots(session: Session) -> None:
    ensure_slots(session)
    occupied_rows = list(session.scalars(_slot_query(session)))
    released = False
    for row in occupied_rows:
        product = row.product
        if product is None:
            continue
        if product.editorial_status != EditorialStatus.PUBLISHED.value:
            row.product_id = None
            released = True
    if released:
        session.flush()
    occupied = {
        product_id
        for product_id in session.scalars(
            select(ShowcaseSlot.product_id).where(ShowcaseSlot.product_id.is_not(None))
        )
        if product_id is not None
    }
    empties = list(
        session.scalars(
            select(ShowcaseSlot)
            .where(ShowcaseSlot.product_id.is_(None))
            .order_by(ShowcaseSlot.position.asc())
        )
    )
    if not empties:
        return
    pending = [
        product
        for product in session.scalars(
            select(Product)
            .where(Product.editorial_status == EditorialStatus.PUBLISHED.value)
            .order_by(
                Product.sort_order.asc(),
                Product.published_at.asc(),
                Product.name.asc(),
                Product.id.asc(),
            )
        )
        if product.id not in occupied
    ]
    changed = False
    for slot, product in zip(empties, pending, strict=False):
        slot.product_id = product.id
        changed = True
    if changed:
        session.flush()


def place_published_on_showcase(session: Session, product_id: UUID) -> int | None:
    product = session.get(Product, product_id)
    if product is None or product.editorial_status != EditorialStatus.PUBLISHED.value:
        return None
    ensure_slots(session)
    existing = session.scalar(select(ShowcaseSlot).where(ShowcaseSlot.product_id == product_id))
    if existing is not None:
        return existing.position
    empty = session.scalar(
        select(ShowcaseSlot)
        .where(ShowcaseSlot.product_id.is_(None))
        .order_by(ShowcaseSlot.position.asc())
    )
    if empty is None:
        return None
    empty.product_id = product_id
    session.flush()
    return empty.position


def list_admin_slots(session: Session) -> ShowcaseAdminOut:
    ensure_slots(session)
    fill_empty_showcase_slots(session)
    rows = list(session.scalars(_slot_query(session)))
    slots = []
    for row in rows:
        product = row.product
        slots.append(
            ShowcaseSlotOut(
                position=row.position,
                product_id=row.product_id,
                product=_product_summary(product) if product is not None else None,
            )
        )
    return ShowcaseAdminOut(slots=slots)


def public_showcase(session: Session) -> PublicProductList:
    ensure_slots(session)
    fill_empty_showcase_slots(session)
    rows = list(session.scalars(_slot_query(session)))
    items = []
    for row in rows:
        product = row.product
        if product is None:
            continue
        if product.editorial_status != EditorialStatus.PUBLISHED.value:
            continue
        items.append(public_list_item(product))
    return PublicProductList(items=items, page=1, page_size=SLOT_COUNT, total=len(items))


def _require_product(session: Session, product_id: UUID) -> Product:
    product = session.get(Product, product_id)
    if product is None:
        raise NotFoundError("produto não encontrado")
    if product.editorial_status == EditorialStatus.ARCHIVED.value:
        raise ProductError("produto arquivado não entra na vitrine")
    return product


def save_slots(session: Session, payload: list[ShowcaseSlotIn]) -> ShowcaseAdminOut:
    ensure_slots(session)
    by_position = {item.position: item.product_id for item in payload}
    if set(by_position) != set(range(1, SLOT_COUNT + 1)):
        raise ProductError("informe as dez posições da vitrine")
    assigned: dict[UUID, int] = {}
    for position, product_id in by_position.items():
        if product_id is None:
            continue
        if product_id in assigned:
            raise ProductError("o mesmo produto não pode ocupar duas posições da vitrine")
        assigned[product_id] = position
        _require_product(session, product_id)
    rows = list(session.scalars(select(ShowcaseSlot).order_by(ShowcaseSlot.position)))
    for row in rows:
        row.product_id = None
    session.flush()
    for row in rows:
        row.product_id = by_position[row.position]
    session.flush()
    return list_admin_slots(session)


def assign_slot(session: Session, position: int, product_id: UUID | None) -> ShowcaseAdminOut:
    if position < 1 or position > SLOT_COUNT:
        raise ProductError("posição da vitrine inválida")
    ensure_slots(session)
    row = session.get(ShowcaseSlot, position)
    if row is None:
        raise ProductError("posição da vitrine inválida")
    if product_id is not None:
        _require_product(session, product_id)
        taken = session.scalar(
            select(ShowcaseSlot).where(
                ShowcaseSlot.product_id == product_id,
                ShowcaseSlot.position != position,
            )
        )
        if taken is not None:
            raise ProductError("o mesmo produto não pode ocupar duas posições da vitrine")
    row.product_id = product_id
    session.flush()
    return list_admin_slots(session)


def move_slot(session: Session, position: int, direction: str) -> ShowcaseAdminOut:
    if direction not in {"up", "down"}:
        raise ProductError("movimento da vitrine inválido")
    delta = -1 if direction == "up" else 1
    other_position = position + delta
    if position < 1 or position > SLOT_COUNT or other_position < 1 or other_position > SLOT_COUNT:
        raise ProductError("não há posição vizinha nessa direção")
    ensure_slots(session)
    current = session.get(ShowcaseSlot, position)
    neighbor = session.get(ShowcaseSlot, other_position)
    if current is None or neighbor is None:
        raise ProductError("posição da vitrine inválida")
    current_product = current.product_id
    neighbor_product = neighbor.product_id
    current.product_id = None
    neighbor.product_id = None
    session.flush()
    current.product_id = neighbor_product
    neighbor.product_id = current_product
    session.flush()
    return list_admin_slots(session)

from __future__ import annotations

from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.core.config import Settings
from app.domain.capacity import utc_now
from app.domain.errors import ConflictError, NotFoundError, ProductError
from app.domain.media import store_image
from app.domain.money import slugify
from app.models.catalog import Ingredient
from app.models.enums import EditorialStatus, PresentationType, ProductEventAction
from app.models.products import MediaAsset, Product, ProductEvent, ProductIngredient, ProductVariant
from app.schemas.catalog_public import (
    PublicIngredientOut,
    PublicProductDetail,
    PublicProductList,
    PublicProductListItem,
    PublicVariantOut,
)
from app.schemas.products import (
    AdminProductDetail,
    AdminProductList,
    AdminProductListItem,
    IngredientIn,
    IngredientOut,
    MediaOut,
    MoneyOut,
    ProductEventOut,
    ProductSaveIn,
    VariantIn,
    VariantOut,
)


def _lock_product(session: Session, product_id: UUID) -> Product:
    product = session.execute(
        select(Product).where(Product.id == product_id).with_for_update()
    ).scalar_one_or_none()
    if product is None:
        raise NotFoundError("produto não encontrado")
    return product


def _append_event(session: Session, product: Product, action: str, actor_ref: str | None, detail: str | None = None) -> None:
    session.add(
        ProductEvent(product_id=product.id, action=action, actor_ref=actor_ref, detail=detail)
    )


def _variants(session: Session, product_id: UUID) -> list[ProductVariant]:
    return list(
        session.scalars(
            select(ProductVariant)
            .where(ProductVariant.product_id == product_id)
            .order_by(ProductVariant.sort_order, ProductVariant.created_at)
        )
    )


def _ingredients(session: Session, product_id: UUID) -> list[ProductIngredient]:
    return list(
        session.scalars(
            select(ProductIngredient)
            .where(ProductIngredient.product_id == product_id)
            .order_by(ProductIngredient.sort_order)
        )
    )


def sellable_variants(variants: list[ProductVariant]) -> list[ProductVariant]:
    return [
        row
        for row in variants
        if row.is_active and row.price_cents is not None and row.price_cents > 0
    ]


def from_price_cents(variants: list[ProductVariant]) -> int | None:
    prices = [row.price_cents for row in sellable_variants(variants) if row.price_cents is not None]
    return min(prices) if prices else None


def _validate_variant(item: VariantIn) -> None:
    if item.presentation_type == PresentationType.WEIGHT.value:
        if item.net_weight_grams is None or item.net_weight_grams <= 0:
            raise ProductError("informe o peso em gramas da variação")
        if item.units_per_pack is not None:
            raise ProductError("variação por peso não usa unidades por embalagem")
    else:
        if item.units_per_pack is None or item.units_per_pack <= 0:
            raise ProductError("informe quantas unidades vão na embalagem")
        if item.net_weight_grams is not None:
            raise ProductError("variação por unidade não usa peso em gramas")
    if item.price_cents is not None and item.price_cents <= 0:
        raise ProductError("preço da variação deve ser maior que zero")


def _assert_unique_variants(items: list[VariantIn]) -> None:
    names: set[str] = set()
    weights: set[int] = set()
    packs: set[int] = set()
    for item in items:
        _validate_variant(item)
        key = item.display_name.strip().lower()
        if key in names:
            raise ProductError("há variações com o mesmo nome")
        names.add(key)
        if item.presentation_type == PresentationType.WEIGHT.value and item.net_weight_grams:
            if item.net_weight_grams in weights:
                raise ProductError("já existe uma variação com esse peso")
            weights.add(item.net_weight_grams)
        if item.presentation_type == PresentationType.PACK.value and item.units_per_pack:
            if item.units_per_pack in packs:
                raise ProductError("já existe uma variação com essa quantidade por embalagem")
            packs.add(item.units_per_pack)


def publication_ready(product: Product, ingredients: list[ProductIngredient], variants: list[ProductVariant]) -> list[str]:
    missing: list[str] = []
    if not product.name.strip():
        missing.append("nome")
    if not product.slug.strip():
        missing.append("identificação pública")
    if not product.short_description.strip():
        missing.append("descrição curta")
    if product.featured_image_id is None:
        missing.append("foto destacada")
    if not product.featured_image_alt.strip():
        missing.append("texto da foto")
    if not ingredients:
        missing.append("ingredientes básicos")
    if not sellable_variants(variants):
        missing.append("uma variação à venda com preço")
    return missing


def _replace_composition(session: Session, product: Product, items: list[IngredientIn]) -> None:
    session.execute(delete(ProductIngredient).where(ProductIngredient.product_id == product.id))
    seen: set[str] = set()
    for index, item in enumerate(items):
        name = item.name.strip()
        if not name:
            raise ProductError("ingrediente básico sem nome")
        key = name.casefold()
        if key in seen:
            raise ProductError("ingrediente básico repetido")
        seen.add(key)
        catalog_id = item.catalog_ingredient_id
        if catalog_id is not None and session.get(Ingredient, catalog_id) is None:
            raise ProductError("ingrediente do assistente não encontrado")
        session.add(
            ProductIngredient(
                product_id=product.id,
                name=name,
                sort_order=index,
                catalog_ingredient_id=catalog_id,
            )
        )


def _replace_variants(session: Session, product: Product, items: list[VariantIn]) -> None:
    _assert_unique_variants(items)
    existing = {row.id: row for row in _variants(session, product.id)}
    keep: set[UUID] = set()
    for index, item in enumerate(items):
        row = existing.get(item.id) if item.id else None
        if row is None:
            row = ProductVariant(id=item.id or uuid4(), product_id=product.id)
            session.add(row)
        row.display_name = item.display_name.strip()
        row.presentation_type = item.presentation_type
        row.net_weight_grams = item.net_weight_grams
        row.units_per_pack = item.units_per_pack
        row.price_cents = item.price_cents
        row.currency = "BRL"
        row.is_active = item.is_active
        row.sort_order = index
        keep.add(row.id)
    removed = [row_id for row_id in existing if row_id not in keep]
    if removed:
        session.execute(delete(ProductVariant).where(ProductVariant.id.in_(removed)))
        session.flush()


def _unique_slug(session: Session, slug: str, exclude_id: UUID | None = None) -> str:
    base = slugify(slug) or "pao"
    candidate = base
    suffix = 2
    while True:
        stmt = select(Product.id).where(Product.slug == candidate)
        if exclude_id is not None:
            stmt = stmt.where(Product.id != exclude_id)
        if session.scalar(stmt) is None:
            return candidate
        candidate = f"{base}-{suffix}"[:80]
        suffix += 1


def create_product(session: Session, actor_ref: str, payload: ProductSaveIn) -> Product:
    slug = _unique_slug(session, payload.slug or payload.name)
    product = Product(
        name=payload.name.strip(),
        slug=slug,
        short_description=payload.short_description.strip(),
        long_description=(payload.long_description or "").strip() or None,
        featured_image_alt=payload.featured_image_alt.strip(),
        is_available=payload.is_available,
        sort_order=payload.sort_order,
        editorial_status=EditorialStatus.DRAFT.value,
        updated_by_ref=actor_ref,
    )
    session.add(product)
    session.flush()
    _replace_composition(session, product, payload.ingredients)
    _replace_variants(session, product, payload.variants)
    _append_event(session, product, ProductEventAction.CREATED.value, actor_ref)
    session.flush()
    return product


def update_product(session: Session, product_id: UUID, actor_ref: str, payload: ProductSaveIn) -> Product:
    product = _lock_product(session, product_id)
    if payload.expected_updated_at is not None:
        current = product.updated_at
        expected = payload.expected_updated_at
        if current.tzinfo is None:
            current = current.replace(tzinfo=ZoneInfo("UTC"))
        if abs((current - expected).total_seconds()) > 0.5:
            raise ConflictError("este produto foi alterado em outro lugar; recarregue e tente de novo")
    if product.editorial_status == EditorialStatus.ARCHIVED.value:
        raise ProductError("produto arquivado não pode ser editado; reabra o cadastro se precisar")
    product.name = payload.name.strip()
    product.slug = _unique_slug(session, payload.slug or payload.name, product.id)
    product.short_description = payload.short_description.strip()
    product.long_description = (payload.long_description or "").strip() or None
    product.featured_image_alt = payload.featured_image_alt.strip()
    product.is_available = payload.is_available
    product.sort_order = payload.sort_order
    product.updated_by_ref = actor_ref
    _replace_composition(session, product, payload.ingredients)
    _replace_variants(session, product, payload.variants)
    session.flush()
    if product.editorial_status == EditorialStatus.PUBLISHED.value:
        gaps = publication_ready(product, _ingredients(session, product.id), _variants(session, product.id))
        if gaps:
            raise ProductError(
                "um produto publicado precisa de " + ", ".join(gaps) + "; corrija ou retire de publicação"
            )
    _append_event(session, product, ProductEventAction.UPDATED.value, actor_ref)
    session.flush()
    return product


def attach_image(
    session: Session, settings: Settings, product_id: UUID, actor_ref: str, payload: bytes, alt: str | None
) -> Product:
    product = _lock_product(session, product_id)
    stored_name, content_type, size, width, height = store_image(settings, payload)
    asset = MediaAsset(
        stored_name=stored_name,
        content_type=content_type,
        byte_size=size,
        width=width,
        height=height,
        created_by_ref=actor_ref,
    )
    session.add(asset)
    session.flush()
    product.featured_image_id = asset.id
    if alt and alt.strip():
        product.featured_image_alt = alt.strip()
    product.updated_by_ref = actor_ref
    _append_event(session, product, ProductEventAction.IMAGE.value, actor_ref)
    session.flush()
    return product


def publish_product(session: Session, product_id: UUID, actor_ref: str) -> Product:
    product = _lock_product(session, product_id)
    if product.editorial_status == EditorialStatus.ARCHIVED.value:
        raise ProductError("produto arquivado não pode ser publicado")
    gaps = publication_ready(product, _ingredients(session, product.id), _variants(session, product.id))
    if gaps:
        raise ProductError("para publicar, complete: " + ", ".join(gaps))
    product.editorial_status = EditorialStatus.PUBLISHED.value
    product.published_at = product.published_at or utc_now()
    product.updated_by_ref = actor_ref
    _append_event(session, product, ProductEventAction.PUBLISHED.value, actor_ref)
    session.flush()
    return product


def unpublish_product(session: Session, product_id: UUID, actor_ref: str) -> Product:
    product = _lock_product(session, product_id)
    if product.editorial_status != EditorialStatus.PUBLISHED.value:
        raise ProductError("só um produto publicado pode voltar a rascunho")
    product.editorial_status = EditorialStatus.DRAFT.value
    product.updated_by_ref = actor_ref
    _append_event(session, product, ProductEventAction.UNPUBLISHED.value, actor_ref)
    session.flush()
    return product


def archive_product(session: Session, product_id: UUID, actor_ref: str) -> Product:
    product = _lock_product(session, product_id)
    product.editorial_status = EditorialStatus.ARCHIVED.value
    product.archived_at = utc_now()
    product.updated_by_ref = actor_ref
    _append_event(session, product, ProductEventAction.ARCHIVED.value, actor_ref)
    session.flush()
    return product


def set_availability(session: Session, product_id: UUID, actor_ref: str, is_available: bool) -> Product:
    product = _lock_product(session, product_id)
    product.is_available = is_available
    product.updated_by_ref = actor_ref
    _append_event(
        session,
        product,
        ProductEventAction.AVAILABILITY.value,
        actor_ref,
        "disponível" if is_available else "indisponível",
    )
    session.flush()
    return product


def _media_out(session: Session, media_id: UUID | None) -> MediaOut | None:
    if media_id is None:
        return None
    asset = session.get(MediaAsset, media_id)
    if asset is None:
        return None
    return MediaOut(
        id=asset.id,
        content_type=asset.content_type,
        width=asset.width,
        height=asset.height,
        url=f"/api/v1/admin/media/{asset.id}",
        public_url=f"/api/v1/catalog/media/{asset.id}",
    )


def product_detail(session: Session, product: Product) -> AdminProductDetail:
    variants = _variants(session, product.id)
    ingredients = _ingredients(session, product.id)
    events = session.scalars(
        select(ProductEvent)
        .where(ProductEvent.product_id == product.id)
        .order_by(ProductEvent.created_at.asc())
    ).all()
    return AdminProductDetail(
        id=product.id,
        name=product.name,
        slug=product.slug,
        short_description=product.short_description,
        long_description=product.long_description,
        featured_image=_media_out(session, product.featured_image_id),
        featured_image_alt=product.featured_image_alt,
        editorial_status=product.editorial_status,
        is_available=product.is_available,
        sort_order=product.sort_order,
        created_at=product.created_at,
        updated_at=product.updated_at,
        published_at=product.published_at,
        ingredients=[
            IngredientOut(
                id=row.id,
                name=row.name,
                sort_order=row.sort_order,
                catalog_ingredient_id=row.catalog_ingredient_id,
            )
            for row in ingredients
        ],
        variants=[
            VariantOut(
                id=row.id,
                display_name=row.display_name,
                presentation_type=row.presentation_type,
                net_weight_grams=row.net_weight_grams,
                units_per_pack=row.units_per_pack,
                price=MoneyOut(cents=row.price_cents),
                is_active=row.is_active,
                sort_order=row.sort_order,
            )
            for row in variants
        ],
        events=[
            ProductEventOut(
                id=row.id, action=row.action, actor_ref=row.actor_ref, detail=row.detail, created_at=row.created_at
            )
            for row in events
        ],
        publication_gaps=publication_ready(product, ingredients, variants),
        from_price=MoneyOut(cents=from_price_cents(variants)),
    )


def list_admin_products(
    session: Session,
    *,
    query: str | None,
    status: str | None,
    available: bool | None,
    page: int,
    page_size: int,
) -> AdminProductList:
    filters = select(Product)
    if query:
        filters = filters.where(Product.name.ilike(f"%{query.strip()}%"))
    if status:
        filters = filters.where(Product.editorial_status == status)
    if available is not None:
        filters = filters.where(Product.is_available.is_(available))
    total = int(session.scalar(select(func.count()).select_from(filters.subquery())) or 0)
    rows = session.scalars(
        filters.options(selectinload(Product.variants), selectinload(Product.featured_image))
        .order_by(Product.sort_order, Product.name, Product.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    items = []
    for product in rows:
        variants = list(product.variants)
        media = _media_out(session, product.featured_image_id)
        items.append(
            AdminProductListItem(
                id=product.id,
                name=product.name,
                slug=product.slug,
                editorial_status=product.editorial_status,
                is_available=product.is_available,
                updated_at=product.updated_at,
                thumbnail_url=media.url if media else None,
                from_price=MoneyOut(cents=from_price_cents(variants)),
            )
        )
    return AdminProductList(items=items, page=page, page_size=page_size, total=total)


def public_list(session: Session, page: int, page_size: int) -> PublicProductList:
    published = select(Product).where(Product.editorial_status == EditorialStatus.PUBLISHED.value)
    total = int(session.scalar(select(func.count()).select_from(published.subquery())) or 0)
    rows = session.scalars(
        published.options(selectinload(Product.variants), selectinload(Product.featured_image))
        .order_by(Product.sort_order, Product.published_at.desc(), Product.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    items = []
    for product in rows:
        variants = sellable_variants(list(product.variants))
        prices = [row.price_cents for row in variants if row.price_cents is not None]
        lowest = min(prices) if prices else None
        same = len(set(prices)) == 1 if prices else False
        items.append(
            PublicProductListItem(
                name=product.name,
                slug=product.slug,
                short_description=product.short_description,
                image_url=f"/api/v1/catalog/media/{product.featured_image_id}" if product.featured_image_id else None,
                image_alt=product.featured_image_alt,
                is_available=product.is_available and bool(variants),
                from_price=MoneyOut(cents=lowest),
                price_is_from=bool(prices) and not same,
                variants=[_public_variant(row) for row in variants],
            )
        )
    return PublicProductList(items=items, page=page, page_size=page_size, total=total)


def public_detail(session: Session, slug: str) -> PublicProductDetail:
    product = session.scalar(
        select(Product).where(
            Product.slug == slug, Product.editorial_status == EditorialStatus.PUBLISHED.value
        )
    )
    if product is None:
        raise NotFoundError("produto não encontrado")
    variants = sellable_variants(_variants(session, product.id))
    ingredients = _ingredients(session, product.id)
    prices = [row.price_cents for row in variants if row.price_cents is not None]
    lowest = min(prices) if prices else None
    same = len(set(prices)) == 1 if prices else False
    return PublicProductDetail(
        name=product.name,
        slug=product.slug,
        short_description=product.short_description,
        long_description=product.long_description,
        image_url=f"/api/v1/catalog/media/{product.featured_image_id}" if product.featured_image_id else None,
        image_alt=product.featured_image_alt,
        is_available=product.is_available and bool(variants),
        from_price=MoneyOut(cents=lowest),
        price_is_from=bool(prices) and not same,
        ingredients=[PublicIngredientOut(name=row.name) for row in ingredients],
        variants=[_public_variant(row) for row in variants],
        allergen_note="Informações sobre alergênicos ainda não foram revisadas para este produto.",
    )


def _public_variant(row: ProductVariant) -> PublicVariantOut:
    pack_label = None
    if row.presentation_type == PresentationType.PACK.value and row.units_per_pack:
        pack_label = (
            "1 unidade" if row.units_per_pack == 1 else f"pacote com {row.units_per_pack} unidades"
        )
    return PublicVariantOut(
        id=row.id,
        display_name=row.display_name,
        presentation_type=row.presentation_type,
        net_weight_grams=row.net_weight_grams,
        units_per_pack=row.units_per_pack,
        pack_label=pack_label,
        price=MoneyOut(cents=row.price_cents),
    )


def published_media(session: Session, media_id: UUID) -> MediaAsset:
    asset = session.get(MediaAsset, media_id)
    if asset is None:
        raise NotFoundError("imagem não encontrada")
    used = session.scalar(
        select(Product.id).where(
            Product.featured_image_id == media_id,
            Product.editorial_status == EditorialStatus.PUBLISHED.value,
        )
    )
    if used is None:
        raise NotFoundError("imagem não encontrada")
    return asset


def get_product(session: Session, product_id: UUID) -> Product:
    product = session.get(Product, product_id)
    if product is None:
        raise NotFoundError("produto não encontrado")
    return product


def admin_media(session: Session, media_id: UUID) -> MediaAsset:
    asset = session.get(MediaAsset, media_id)
    if asset is None:
        raise NotFoundError("imagem não encontrada")
    return asset


def catch_slug_conflict(exc: IntegrityError) -> None:
    message = str(exc.orig) if exc.orig is not None else str(exc)
    if "slug" in message or "uq_product_variant" in message:
        raise ConflictError("já existe um produto ou variação com esses dados") from exc
    raise ConflictError("não foi possível gravar o produto") from exc

"""Importa só o catálogo editorial público. Sem pedidos, usuários ou credenciais."""

from __future__ import annotations

from datetime import UTC, datetime

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_engine
from app.domain.media import store_image
from app.domain.recipe_bases import create_recipe_base
from app.domain.showcase import fill_empty_showcase_slots
from app.models.accompaniments import AccompanimentItem
from app.models.enums import EditorialStatus
from app.models.products import MediaAsset, Product, ProductIngredient, ProductVariant
from app.models.schedule import RecipeBase
from app.models.week_recipes import WeekRecipe, WeekRecipeBread, WeekRecipeIngredient, WeekRecipeStep

PUBLIC_ORIGIN = "https://lojadepaes.com.br"
STORY_HUB_ID = "local-demo-azeite"


def run(*, origin: str = PUBLIC_ORIGIN) -> dict:
    settings = get_settings()
    if settings.env.strip().lower() not in {"local", "development", "dev"}:
        raise RuntimeError("import público só no ambiente local")
    base = origin.rstrip("/")
    with httpx.Client(timeout=20.0, follow_redirects=True) as client:
        listing = client.get(f"{base}/api/v1/catalog/products", params={"page_size": 50})
        listing.raise_for_status()
        items = listing.json().get("items") or []
        details = []
        for item in items:
            slug = item.get("slug")
            if not slug:
                continue
            detail = client.get(f"{base}/api/v1/catalog/products/{slug}")
            detail.raise_for_status()
            details.append(detail.json())
        recipe_payload = client.get(f"{base}/api/v1/catalog/week-recipe")
        recipe_payload.raise_for_status()
        featured = (recipe_payload.json() or {}).get("recipe")
        session = Session(bind=get_engine())
        try:
            created = 0
            updated = 0
            for detail in details:
                was_new = _upsert_product(session, settings, client, base, detail)
                created += int(was_new)
                updated += int(not was_new)
            if featured:
                _upsert_recipe(session, settings, client, base, featured)
            _ensure_preview_overlay(session)
            fill_empty_showcase_slots(session)
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    return {"products": len(details), "created": created, "updated": updated, "recipe": bool(featured)}


def _upsert_product(session: Session, settings, client: httpx.Client, base: str, detail: dict) -> bool:
    slug = str(detail["slug"])
    existing = session.scalar(select(Product).where(Product.slug == slug))
    created = existing is None
    if existing is None:
        existing = Product(
            name=detail["name"][:120],
            slug=slug[:80],
            short_description=(detail.get("short_description") or "")[:280],
            recipe_base_id=_import_base(session).id,
            featured_image_alt=(detail.get("image_alt") or detail["name"])[:160],
            featured_image_caption=(detail.get("image_caption") or "")[:200],
            editorial_status=EditorialStatus.PUBLISHED.value,
            is_available=bool(detail.get("is_available", True)),
            published_at=datetime.now(UTC),
        )
        session.add(existing)
        session.flush()
    if not existing.featured_image_id:
        media = _import_media(session, settings, client, base, detail.get("image_url"))
        if media is not None:
            existing.featured_image_id = media.id
            existing.featured_image_alt = (detail.get("image_alt") or existing.name)[:160]
    if not existing.variants:
        for index, variant in enumerate(detail.get("variants") or []):
            price = (variant.get("price") or {}).get("cents")
            session.add(
                ProductVariant(
                    product_id=existing.id,
                    display_name=str(variant.get("display_name") or "500 g")[:80],
                    presentation_type=variant.get("presentation_type") or "weight",
                    net_weight_grams=variant.get("net_weight_grams"),
                    units_per_pack=variant.get("units_per_pack"),
                    physical_units=1,
                    price_cents=price,
                    currency="BRL",
                    is_active=True,
                    sort_order=index,
                )
            )
    if not existing.composition:
        for index, ingredient in enumerate(detail.get("ingredients") or []):
            name = str(ingredient.get("name") or "").strip()
            if not name:
                continue
            session.add(ProductIngredient(product_id=existing.id, name=name[:120], sort_order=index))
    session.flush()
    return created


def _upsert_recipe(session: Session, settings, client: httpx.Client, base: str, payload: dict) -> None:
    slug = str(payload.get("slug") or "")[:80]
    if not slug:
        return
    existing = session.scalar(select(WeekRecipe).where(WeekRecipe.slug == slug))
    if existing is None:
        for featured_row in session.scalars(select(WeekRecipe).where(WeekRecipe.is_featured.is_(True))):
            featured_row.is_featured = False
        existing = WeekRecipe(
            title=str(payload.get("title") or "")[:160],
            slug=slug,
            summary=str(payload.get("summary") or "")[:280],
            featured_image_alt=str(payload.get("image_alt") or payload.get("title") or "")[:160],
            featured_image_caption=str(payload.get("image_caption") or "")[:200],
            prep_time_text=str(payload.get("prep_time") or "")[:80],
            yield_text=str(payload.get("yield_text") or "")[:80],
            method_text=payload.get("method_text"),
            editorial_status=EditorialStatus.PUBLISHED.value,
            is_featured=True,
            published_at=datetime.now(UTC),
        )
        session.add(existing)
        session.flush()
        for index, body in enumerate(payload.get("ingredients") or []):
            session.add(WeekRecipeIngredient(recipe_id=existing.id, sort_order=index, body=str(body)[:280]))
        for index, body in enumerate(payload.get("steps") or []):
            session.add(WeekRecipeStep(recipe_id=existing.id, sort_order=index, body=str(body)))
        for index, bread in enumerate(payload.get("breads") or []):
            product = session.scalar(select(Product).where(Product.slug == bread.get("slug")))
            session.add(
                WeekRecipeBread(
                    recipe_id=existing.id,
                    product_id=product.id if product is not None else None,
                    sort_order=index,
                    name_snapshot=str(bread.get("name") or "")[:120],
                )
            )
    if not existing.featured_image_id:
        media = _import_media(session, settings, client, base, payload.get("image_url"))
        if media is not None:
            existing.featured_image_id = media.id
    session.flush()


def _ensure_preview_overlay(session: Session) -> None:
    row = session.scalar(select(AccompanimentItem).where(AccompanimentItem.hub_offer_id == STORY_HUB_ID))
    if row is None:
        row = AccompanimentItem(hub_offer_id=STORY_HUB_ID)
        session.add(row)
    row.occasion = "Café da manhã"
    row.story_title = "Café com fatias mornas"
    row.story_lead = (
        "Toste algumas fatias do pão, leve-as à mesa ainda mornas e acrescente o azeite na hora de servir."
    )
    row.why_pairs = "A gordura do azeite equilibra a crosta crocante e o miolo alveolado."
    row.serving_tip = "Sirva ainda morno. Não é um kit nem uma entrega conjunta."
    row.related_product_slugs = [
        "pao-fermentacao-natural-de-trigo",
        "focaccia-alta-italian-focaccia",
    ]
    row.related_recipe_slugs = ["sardinhas-e-homus-de-grao-de-bico-fresco-tartine-bread"]
    row.published = True
    row.sort_order = 1
    session.flush()


def _import_base(session: Session) -> RecipeBase:
    existing = session.scalar(select(RecipeBase).where(RecipeBase.code == "PUBLIC-IMPORT"))
    if existing is not None:
        return existing
    return create_recipe_base(session, code="public-import", name="Importação editorial pública")


def _import_media(session: Session, settings, client: httpx.Client, base: str, image_url: object) -> MediaAsset | None:
    raw = str(image_url or "").strip()
    if not raw:
        return None
    url = raw if raw.startswith("http") else f"{base}{raw}"
    try:
        response = client.get(url)
        if response.status_code != 200 or not response.content:
            return None
        stored_name, backend, content_type, size, width, height = store_image(settings, response.content)
    except Exception:
        return None
    media = MediaAsset(
        stored_name=stored_name,
        object_key=stored_name,
        storage_backend=backend,
        content_type=content_type,
        byte_size=size,
        width=width,
        height=height,
        created_by_ref="public-import",
    )
    session.add(media)
    session.flush()
    return media


if __name__ == "__main__":
    print(run())

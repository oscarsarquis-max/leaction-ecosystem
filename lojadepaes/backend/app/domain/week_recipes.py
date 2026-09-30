from __future__ import annotations

import re
from uuid import UUID

from sqlalchemy import delete, exists, func, or_, select, update
from sqlalchemy.orm import Session, selectinload

from app.core.config import Settings
from app.domain.capacity import utc_now
from app.domain.errors import NotFoundError, ProductError
from app.domain.media import store_image
from app.domain.money import slugify
from app.models.enums import EditorialStatus
from app.models.products import MediaAsset, Product
from app.models.week_recipes import (
    WeekRecipe,
    WeekRecipeBread,
    WeekRecipeIngredient,
    WeekRecipeStep,
)

_TAG_RE = re.compile(r"<[^>]*>")
_CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")
_METHOD_MAX = 20000
_STEP_MAX = 20000


def steps_to_method_text(steps: list[object]) -> str:
    parts: list[str] = []
    for raw in steps:
        body = raw.get("body") if isinstance(raw, dict) else raw
        text = str(body or "").replace("\r\n", "\n").strip()
        if text:
            parts.append(text)
    return "\n\n".join(parts)


def method_text_to_steps(value: str) -> list[str]:
    cleaned = str(value or "").replace("\r\n", "\n").strip()
    if not cleaned:
        return []
    return [chunk.strip() for chunk in re.split(r"\n\s*\n", cleaned) if chunk.strip()]


def ingredients_from_lines(raw_items: list[object] | str) -> list[str]:
    if isinstance(raw_items, str):
        lines = raw_items.replace("\r\n", "\n").split("\n")
    else:
        lines = []
        for raw in raw_items or []:
            body = raw.get("body") if isinstance(raw, dict) else raw
            lines.extend(str(body or "").replace("\r\n", "\n").split("\n"))
    result: list[str] = []
    for line in lines:
        item = line.strip()
        if item:
            result.append(item)
    return result


def method_text_for_recipe(recipe: WeekRecipe) -> str:
    stored = (recipe.method_text or "").strip()
    if stored:
        return stored
    return steps_to_method_text([row.body for row in sorted(recipe.steps, key=lambda item: item.sort_order)])


def _plain(value: object, *, max_len: int, allow_newlines: bool = False) -> str:
    cleaned = _TAG_RE.sub(" ", str(value or ""))
    cleaned = _CONTROL_RE.sub("", cleaned)
    if allow_newlines:
        cleaned = "\n".join(line.strip() for line in cleaned.replace("\r\n", "\n").split("\n"))
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()
    else:
        cleaned = " ".join(cleaned.split())
    if len(cleaned) > max_len:
        raise ProductError(f"texto excede {max_len} caracteres")
    return cleaned


def _unique_slug(session: Session, raw: str, exclude_id: UUID | None = None) -> str:
    base = slugify(raw) or "receita"
    slug = base
    suffix = 2
    while True:
        query = select(WeekRecipe.id).where(WeekRecipe.slug == slug)
        if exclude_id is not None:
            query = query.where(WeekRecipe.id != exclude_id)
        if session.scalar(query) is None:
            return slug
        slug = f"{base}-{suffix}"[:80]
        suffix += 1


def _lock(session: Session, recipe_id: UUID) -> WeekRecipe:
    recipe = session.execute(
        select(WeekRecipe).where(WeekRecipe.id == recipe_id).with_for_update()
    ).scalar_one_or_none()
    if recipe is None:
        raise NotFoundError("receita não encontrada")
    return recipe


def _replace_children(session: Session, recipe: WeekRecipe, payload: dict) -> None:
    session.execute(delete(WeekRecipeIngredient).where(WeekRecipeIngredient.recipe_id == recipe.id))
    session.execute(delete(WeekRecipeStep).where(WeekRecipeStep.recipe_id == recipe.id))
    session.execute(delete(WeekRecipeBread).where(WeekRecipeBread.recipe_id == recipe.id))
    for index, raw in enumerate(ingredients_from_lines(payload.get("ingredients") or [])):
        body = _plain(raw, max_len=280)
        if not body:
            continue
        session.add(WeekRecipeIngredient(recipe_id=recipe.id, sort_order=index, body=body))
    method = payload.get("method_text")
    if method is None:
        method = steps_to_method_text(payload.get("steps") or [])
    method = _plain(method, max_len=_METHOD_MAX, allow_newlines=True)
    recipe.method_text = method or None
    for index, raw in enumerate(method_text_to_steps(method)):
        body = _plain(raw, max_len=_STEP_MAX, allow_newlines=True)
        if not body:
            continue
        session.add(WeekRecipeStep(recipe_id=recipe.id, sort_order=index, body=body))
    seen: set[UUID] = set()
    order = 0
    for raw in payload.get("product_ids") or []:
        product = session.get(Product, UUID(str(raw)))
        if product is None:
            raise ProductError("pão da vitrine não encontrado")
        if product.id in seen:
            continue
        seen.add(product.id)
        session.add(
            WeekRecipeBread(
                recipe_id=recipe.id,
                product_id=product.id,
                sort_order=order,
                name_snapshot=product.name,
            )
        )
        order += 1
    session.flush()


def publication_gaps(session: Session, recipe: WeekRecipe) -> list[str]:
    gaps: list[str] = []
    if not recipe.title.strip():
        gaps.append("o título")
    if not recipe.summary.strip():
        gaps.append("o resumo")
    if recipe.featured_image_id is None:
        gaps.append("a foto de destaque")
    if not recipe.featured_image_alt.strip():
        gaps.append("o texto alternativo da foto")
    ingredients = session.scalars(
        select(WeekRecipeIngredient).where(WeekRecipeIngredient.recipe_id == recipe.id)
    ).all()
    if not ingredients:
        gaps.append("pelo menos um ingrediente")
    steps = session.scalars(select(WeekRecipeStep).where(WeekRecipeStep.recipe_id == recipe.id)).all()
    if not method_text_for_recipe(recipe) and not steps:
        gaps.append("o modo de preparo")
    return gaps


def apply_payload(session: Session, recipe: WeekRecipe, payload: dict, actor_ref: str) -> WeekRecipe:
    if recipe.editorial_status == EditorialStatus.ARCHIVED.value:
        raise ProductError("receita arquivada não pode ser editada; reabra o cadastro se precisar")
    recipe.title = _plain(payload.get("title"), max_len=160)
    recipe.summary = _plain(payload.get("summary"), max_len=280)
    recipe.featured_image_alt = _plain(payload.get("featured_image_alt"), max_len=160)
    recipe.featured_image_caption = _plain(payload.get("featured_image_caption"), max_len=200)
    recipe.prep_time_text = _plain(payload.get("prep_time_text"), max_len=80)
    recipe.yield_text = _plain(payload.get("yield_text"), max_len=80)
    recipe.image_focus_x = max(0, min(100, int(payload.get("image_focus_x") or 50)))
    recipe.image_focus_y = max(0, min(100, int(payload.get("image_focus_y") or 50)))
    recipe.slug = _unique_slug(session, str(payload.get("slug") or recipe.title or recipe.slug), recipe.id)
    recipe.updated_by_ref = actor_ref
    session.flush()
    _replace_children(session, recipe, payload)
    if recipe.editorial_status == EditorialStatus.PUBLISHED.value:
        gaps = publication_gaps(session, recipe)
        if gaps:
            raise ProductError("uma receita publicada precisa de " + ", ".join(gaps))
    return recipe


def create_recipe(session: Session, actor_ref: str, payload: dict) -> WeekRecipe:
    recipe = WeekRecipe(
        title="",
        slug=_unique_slug(session, str(payload.get("slug") or payload.get("title") or "receita")),
        summary="",
        updated_by_ref=actor_ref,
    )
    session.add(recipe)
    session.flush()
    return apply_payload(session, recipe, payload, actor_ref)


def update_recipe(session: Session, recipe_id: UUID, actor_ref: str, payload: dict) -> WeekRecipe:
    recipe = _lock(session, recipe_id)
    return apply_payload(session, recipe, payload, actor_ref)


def attach_image(
    session: Session, settings: Settings, recipe_id: UUID, actor_ref: str, payload: bytes, alt: str | None
) -> WeekRecipe:
    recipe = _lock(session, recipe_id)
    stored_name, backend_name, content_type, size, width, height = store_image(settings, payload)
    asset = MediaAsset(
        stored_name=stored_name,
        object_key=stored_name,
        storage_backend=backend_name,
        content_type=content_type,
        byte_size=size,
        width=width,
        height=height,
        created_by_ref=actor_ref,
    )
    session.add(asset)
    session.flush()
    recipe.featured_image_id = asset.id
    if alt and str(alt).strip():
        recipe.featured_image_alt = _plain(alt, max_len=160)
    recipe.updated_by_ref = actor_ref
    session.flush()
    return recipe


def publish_recipe(session: Session, recipe_id: UUID, actor_ref: str) -> WeekRecipe:
    recipe = _lock(session, recipe_id)
    if recipe.editorial_status == EditorialStatus.ARCHIVED.value:
        raise ProductError("receita arquivada não pode ser publicada")
    gaps = publication_gaps(session, recipe)
    if gaps:
        raise ProductError("para publicar, complete: " + ", ".join(gaps))
    recipe.editorial_status = EditorialStatus.PUBLISHED.value
    recipe.published_at = recipe.published_at or utc_now()
    recipe.archived_at = None
    recipe.updated_by_ref = actor_ref
    session.flush()
    return recipe


def unpublish_recipe(session: Session, recipe_id: UUID, actor_ref: str) -> WeekRecipe:
    recipe = _lock(session, recipe_id)
    if recipe.editorial_status != EditorialStatus.PUBLISHED.value:
        raise ProductError("só uma receita publicada pode voltar a rascunho")
    recipe.editorial_status = EditorialStatus.DRAFT.value
    recipe.is_featured = False
    recipe.updated_by_ref = actor_ref
    session.flush()
    return recipe


def archive_recipe(session: Session, recipe_id: UUID, actor_ref: str) -> WeekRecipe:
    recipe = _lock(session, recipe_id)
    recipe.editorial_status = EditorialStatus.ARCHIVED.value
    recipe.is_featured = False
    recipe.archived_at = utc_now()
    recipe.updated_by_ref = actor_ref
    session.flush()
    return recipe


def current_featured_title(session: Session, exclude_id: UUID | None = None) -> str | None:
    query = select(WeekRecipe.title).where(WeekRecipe.is_featured.is_(True))
    if exclude_id is not None:
        query = query.where(WeekRecipe.id != exclude_id)
    return session.scalar(query)


def feature_recipe(session: Session, recipe_id: UUID, actor_ref: str) -> WeekRecipe:
    recipe = _lock(session, recipe_id)
    if recipe.editorial_status != EditorialStatus.PUBLISHED.value:
        raise ProductError("só uma receita publicada pode ser o destaque da semana")
    session.execute(update(WeekRecipe).where(WeekRecipe.is_featured.is_(True)).values(is_featured=False))
    recipe.is_featured = True
    recipe.updated_by_ref = actor_ref
    session.flush()
    return recipe


def publish_and_feature(session: Session, recipe_id: UUID, actor_ref: str) -> WeekRecipe:
    publish_recipe(session, recipe_id, actor_ref)
    return feature_recipe(session, recipe_id, actor_ref)


def unfeature_recipe(session: Session, recipe_id: UUID, actor_ref: str) -> WeekRecipe:
    recipe = _lock(session, recipe_id)
    recipe.is_featured = False
    recipe.updated_by_ref = actor_ref
    session.flush()
    return recipe


def list_recipes(session: Session) -> list[WeekRecipe]:
    return list(
        session.scalars(
            select(WeekRecipe)
            .options(
                selectinload(WeekRecipe.ingredients),
                selectinload(WeekRecipe.steps),
                selectinload(WeekRecipe.breads),
            )
            .order_by(WeekRecipe.is_featured.desc(), WeekRecipe.updated_at.desc())
        )
    )


def get_recipe(session: Session, recipe_id: UUID) -> WeekRecipe:
    recipe = session.scalar(
        select(WeekRecipe)
        .options(
            selectinload(WeekRecipe.ingredients),
            selectinload(WeekRecipe.steps),
            selectinload(WeekRecipe.breads),
        )
        .where(WeekRecipe.id == recipe_id)
    )
    if recipe is None:
        raise NotFoundError("receita não encontrada")
    return recipe


def _like_term(raw: str) -> str:
    cleaned = (raw or "").replace("\\", " ").replace("%", " ").replace("_", " ").strip()
    return f"%{cleaned}%" if cleaned else ""


def search_published(session: Session, q: str, page: int, page_size: int) -> dict:
    filters = [WeekRecipe.editorial_status == EditorialStatus.PUBLISHED.value]
    term = _like_term(q)
    if term:
        filters.append(
            or_(
                WeekRecipe.title.ilike(term),
                WeekRecipe.summary.ilike(term),
                WeekRecipe.method_text.ilike(term),
                exists().where(
                    WeekRecipeIngredient.recipe_id == WeekRecipe.id,
                    WeekRecipeIngredient.body.ilike(term),
                ),
                exists().where(
                    WeekRecipeStep.recipe_id == WeekRecipe.id,
                    WeekRecipeStep.body.ilike(term),
                ),
            )
        )
    filtered = select(WeekRecipe.id).where(*filters)
    total = int(session.scalar(select(func.count()).select_from(filtered.subquery())) or 0)
    rows = list(
        session.scalars(
            select(WeekRecipe)
            .options(
                selectinload(WeekRecipe.ingredients),
                selectinload(WeekRecipe.steps),
                selectinload(WeekRecipe.breads),
            )
            .where(*filters)
            .order_by(WeekRecipe.is_featured.desc(), WeekRecipe.updated_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    )
    return {
        "q": (q or "").strip(),
        "page": page,
        "page_size": page_size,
        "total": total,
        "items": [public_list_item(session, recipe) for recipe in rows],
    }


def public_list_item(_session: Session, recipe: WeekRecipe) -> dict:
    return {
        "title": recipe.title,
        "slug": recipe.slug,
        "summary": recipe.summary,
        "href": f"/receitas/{recipe.slug}",
        "image_url": f"/api/v1/catalog/media/{recipe.featured_image_id}"
        if recipe.featured_image_id
        else None,
    }


def featured_published(session: Session) -> WeekRecipe | None:
    return session.scalar(
        select(WeekRecipe)
        .options(
            selectinload(WeekRecipe.ingredients),
            selectinload(WeekRecipe.steps),
            selectinload(WeekRecipe.breads),
        )
        .where(
            WeekRecipe.editorial_status == EditorialStatus.PUBLISHED.value,
            WeekRecipe.is_featured.is_(True),
        )
    )


def published_by_slug(session: Session, slug: str) -> WeekRecipe:
    recipe = session.scalar(
        select(WeekRecipe)
        .options(
            selectinload(WeekRecipe.ingredients),
            selectinload(WeekRecipe.steps),
            selectinload(WeekRecipe.breads),
        )
        .where(
            WeekRecipe.slug == slug,
            WeekRecipe.editorial_status == EditorialStatus.PUBLISHED.value,
        )
    )
    if recipe is None:
        raise NotFoundError("receita não encontrada")
    return recipe


def public_breads(session: Session, recipe: WeekRecipe) -> list[dict]:
    items = []
    for row in sorted(recipe.breads, key=lambda item: item.sort_order):
        product = session.get(Product, row.product_id) if row.product_id else None
        published = (
            product is not None
            and product.editorial_status == EditorialStatus.PUBLISHED.value
        )
        items.append(
            {
                "name": row.name_snapshot,
                "slug": product.slug if published else None,
                "href": f"/paes/{product.slug}" if published else None,
            }
        )
    return items


def public_view(session: Session, recipe: WeekRecipe) -> dict:
    return {
        "title": recipe.title,
        "slug": recipe.slug,
        "summary": recipe.summary,
        "image_url": f"/api/v1/catalog/media/{recipe.featured_image_id}"
        if recipe.featured_image_id
        else None,
        "image_alt": recipe.featured_image_alt,
        "image_caption": recipe.featured_image_caption,
        "image_focus": f"{recipe.image_focus_x}% {recipe.image_focus_y}%",
        "prep_time": recipe.prep_time_text or None,
        "yield_text": recipe.yield_text or None,
        "ingredients": [row.body for row in sorted(recipe.ingredients, key=lambda item: item.sort_order)],
        "method_text": method_text_for_recipe(recipe),
        "steps": method_text_to_steps(method_text_for_recipe(recipe)),
        "breads": public_breads(session, recipe),
        "href": f"/receitas/{recipe.slug}",
    }


def admin_view(session: Session, recipe: WeekRecipe) -> dict:
    public = public_view(session, recipe)
    return {
        **public,
        "image_url": f"/api/v1/admin/media/{recipe.featured_image_id}"
        if recipe.featured_image_id
        else None,
        "id": str(recipe.id),
        "editorial_status": recipe.editorial_status,
        "is_featured": recipe.is_featured,
        "featured_image_id": str(recipe.featured_image_id) if recipe.featured_image_id else None,
        "featured_image_alt": recipe.featured_image_alt,
        "featured_image_caption": recipe.featured_image_caption,
        "image_focus_x": recipe.image_focus_x,
        "image_focus_y": recipe.image_focus_y,
        "prep_time_text": recipe.prep_time_text,
        "yield_text": recipe.yield_text,
        "product_ids": [str(row.product_id) for row in recipe.breads if row.product_id],
        "publish_gaps": publication_gaps(session, recipe),
        "other_featured_title": current_featured_title(session, recipe.id),
    }

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, File, Form, UploadFile

from app.api.deps import AdminUser, AppSettings, DbSession
from app.domain.errors import ProductError
from app.domain.week_recipes import (
    admin_view,
    archive_recipe,
    attach_image,
    create_recipe,
    feature_recipe,
    get_recipe,
    list_recipes,
    publish_and_feature,
    publish_recipe,
    unfeature_recipe,
    unpublish_recipe,
    update_recipe,
)
from app.schemas.week_recipes import WeekRecipeSaveIn

router = APIRouter(prefix="/admin/week-recipes", tags=["admin-week-recipes"])


def _detail(db, recipe) -> dict:
    return admin_view(db, get_recipe(db, recipe.id))


@router.get("")
def admin_list_week_recipes(db: DbSession, principal: AdminUser) -> dict:
    del principal
    return {"items": [admin_view(db, recipe) for recipe in list_recipes(db)]}


@router.post("")
def admin_create_week_recipe(
    payload: WeekRecipeSaveIn, db: DbSession, principal: AdminUser
) -> dict:
    recipe = create_recipe(db, principal.actor_ref, payload.model_dump())
    db.flush()
    return _detail(db, recipe)


@router.get("/{recipe_id}")
def admin_get_week_recipe(recipe_id: UUID, db: DbSession, principal: AdminUser) -> dict:
    del principal
    return admin_view(db, get_recipe(db, recipe_id))


@router.put("/{recipe_id}")
def admin_update_week_recipe(
    recipe_id: UUID, payload: WeekRecipeSaveIn, db: DbSession, principal: AdminUser
) -> dict:
    recipe = update_recipe(db, recipe_id, principal.actor_ref, payload.model_dump())
    db.flush()
    return _detail(db, recipe)


@router.post("/{recipe_id}/image")
async def admin_upload_week_recipe_image(
    recipe_id: UUID,
    db: DbSession,
    settings: AppSettings,
    principal: AdminUser,
    file: UploadFile = File(...),
    alt: Annotated[str | None, Form()] = None,
) -> dict:
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
    recipe = attach_image(db, settings, recipe_id, principal.actor_ref, b"".join(chunks), alt)
    db.flush()
    return _detail(db, recipe)


@router.post("/{recipe_id}/publish")
def admin_publish_week_recipe(recipe_id: UUID, db: DbSession, principal: AdminUser) -> dict:
    recipe = publish_recipe(db, recipe_id, principal.actor_ref)
    db.flush()
    return _detail(db, recipe)


@router.post("/{recipe_id}/unpublish")
def admin_unpublish_week_recipe(recipe_id: UUID, db: DbSession, principal: AdminUser) -> dict:
    recipe = unpublish_recipe(db, recipe_id, principal.actor_ref)
    db.flush()
    return _detail(db, recipe)


@router.post("/{recipe_id}/archive")
def admin_archive_week_recipe(recipe_id: UUID, db: DbSession, principal: AdminUser) -> dict:
    recipe = archive_recipe(db, recipe_id, principal.actor_ref)
    db.flush()
    return _detail(db, recipe)


@router.post("/{recipe_id}/publish-featured")
def admin_publish_featured_week_recipe(
    recipe_id: UUID, db: DbSession, principal: AdminUser
) -> dict:
    recipe = publish_and_feature(db, recipe_id, principal.actor_ref)
    db.flush()
    return _detail(db, recipe)


@router.post("/{recipe_id}/feature")
def admin_feature_week_recipe(recipe_id: UUID, db: DbSession, principal: AdminUser) -> dict:
    recipe = feature_recipe(db, recipe_id, principal.actor_ref)
    db.flush()
    return _detail(db, recipe)


@router.post("/{recipe_id}/unfeature")
def admin_unfeature_week_recipe(recipe_id: UUID, db: DbSession, principal: AdminUser) -> dict:
    recipe = unfeature_recipe(db, recipe_id, principal.actor_ref)
    db.flush()
    return _detail(db, recipe)

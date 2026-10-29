from uuid import UUID

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from app.api.deps import AdminUser, AppSettings, DbSession
from app.domain.accompaniments import delete_admin, get_admin, list_admin, search_hub, upsert_admin

router = APIRouter(prefix="/admin/accompaniments", tags=["admin-accompaniments"])


class AccompanimentIn(BaseModel):
    hub_offer_id: str = Field(min_length=1, max_length=80)
    occasion: str = Field(default="", max_length=80)
    story_title: str = Field(default="", max_length=160)
    story_lead: str = Field(default="", max_length=600)
    why_pairs: str = Field(default="", max_length=400)
    serving_tip: str = Field(default="", max_length=400)
    related_product_slugs: list[str] = Field(default_factory=list)
    related_recipe_slugs: list[str] = Field(default_factory=list)
    sort_order: int = Field(default=0, ge=0, le=999)
    published: bool = False
    refresh: bool = False


@router.get("")
def admin_list_accompaniments(db: DbSession, settings: AppSettings, principal: AdminUser) -> dict:
    del principal
    return list_admin(db, settings)


@router.get("/search")
def admin_search_hub(settings: AppSettings, principal: AdminUser, q: str = Query(default="", max_length=80)) -> dict:
    del principal
    return search_hub(settings, q)


@router.get("/{item_id}")
def admin_get_accompaniment(item_id: UUID, db: DbSession, principal: AdminUser) -> dict:
    del principal
    return get_admin(db, item_id)


@router.post("")
def admin_create_accompaniment(payload: AccompanimentIn, db: DbSession, settings: AppSettings, principal: AdminUser) -> dict:
    del principal
    return upsert_admin(db, settings, payload.model_dump())


@router.put("/{item_id}")
def admin_update_accompaniment(
    item_id: UUID, payload: AccompanimentIn, db: DbSession, settings: AppSettings, principal: AdminUser
) -> dict:
    del principal
    return upsert_admin(db, settings, payload.model_dump(), item_id)


@router.delete("/{item_id}")
def admin_delete_accompaniment(item_id: UUID, db: DbSession, principal: AdminUser) -> dict:
    del principal
    delete_admin(db, item_id)
    return {"ok": True}

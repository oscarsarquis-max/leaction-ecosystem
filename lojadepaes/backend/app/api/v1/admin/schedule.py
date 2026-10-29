from datetime import date, timedelta
from uuid import UUID

from fastapi import APIRouter
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.api.deps import AdminUser, AppSettings, DbSession
from app.domain.custom_loaf import list_ingredients, update_custom_loaf_price, update_ingredient
from app.domain.recipe_bases import (
    create_recipe_base,
    link_dough_type,
    list_recipe_bases,
    update_recipe_base,
)
from app.domain.schedule import (
    admin_day_view,
    delete_date_override,
    delete_week_override,
    eligible_ids,
    ensure_schedule_settings,
    preview_week_change,
    save_date_override,
    save_defaults,
    save_week_override,
)
from app.domain.schedule_closures import (
    cancel_closure,
    commitments_in_range,
    list_closure_events,
    list_closures,
    serialize_closure,
    update_closure,
    upsert_closure,
)
from app.models.catalog import DoughType
from app.models.products import Product
from app.schemas.schedule import (
    DateOverrideIn,
    DefaultsIn,
    DoughLinkIn,
    LinkedProductOut,
    RecipeBaseIn,
    RecipeBaseOut,
    WeekOverrideIn,
)

router = APIRouter(prefix="/admin", tags=["admin-schedule"])


class CustomLoafIn(BaseModel):
    price_cents: int = Field(gt=0)
    weight_grams: int = Field(gt=0)


class IngredientAdminIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(min_length=1, max_length=280)
    is_active: bool = True
    compatible_dough_ids: list[UUID] = Field(default_factory=list)


class ClosureIn(BaseModel):
    start_date: date
    end_date: date
    first_eligible_date: date
    pause_intake: bool = False
    internal_reason: str = Field(min_length=1, max_length=120)
    public_notice: str | None = None


def _base_out(row) -> RecipeBaseOut:
    return RecipeBaseOut(id=row.id, code=row.code, name=row.name, is_active=row.is_active)


@router.get("/recipe-bases", response_model=list[RecipeBaseOut])
def admin_list_bases(db: DbSession, principal: AdminUser) -> list[RecipeBaseOut]:
    del principal
    rows = list_recipe_bases(db, include_inactive=True)
    linked = db.scalars(
        select(Product).where(Product.recipe_base_id.is_not(None)).order_by(Product.name)
    ).all()
    by_base: dict[UUID, list[LinkedProductOut]] = {}
    for product in linked:
        if product.recipe_base_id is None:
            continue
        by_base.setdefault(product.recipe_base_id, []).append(
            LinkedProductOut(id=product.id, name=product.name)
        )
    return [
        RecipeBaseOut(
            id=row.id,
            code=row.code,
            name=row.name,
            is_active=row.is_active,
            products=by_base.get(row.id, []),
        )
        for row in rows
    ]


@router.post("/recipe-bases", response_model=RecipeBaseOut)
def admin_create_base(payload: RecipeBaseIn, db: DbSession, principal: AdminUser) -> RecipeBaseOut:
    del principal
    return _base_out(create_recipe_base(db, code=payload.code, name=payload.name))


@router.put("/recipe-bases/{base_id}", response_model=RecipeBaseOut)
def admin_update_base(
    base_id, payload: RecipeBaseIn, db: DbSession, principal: AdminUser
) -> RecipeBaseOut:
    del principal
    return _base_out(
        update_recipe_base(
            db, base_id, code=payload.code, name=payload.name, is_active=payload.is_active
        )
    )


@router.put("/dough-types/{dough_type_id}/recipe-base")
def admin_link_dough(
    dough_type_id, payload: DoughLinkIn, db: DbSession, principal: AdminUser
) -> dict:
    del principal
    dough = link_dough_type(db, dough_type_id, payload.recipe_base_id)
    return {"id": str(dough.id), "recipe_base_id": str(dough.recipe_base_id) if dough.recipe_base_id else None}


@router.get("/dough-types")
def admin_list_doughs(db: DbSession, principal: AdminUser) -> list[dict]:
    del principal
    rows = db.scalars(select(DoughType).order_by(DoughType.sort_order, DoughType.name)).all()
    return [
        {
            "id": str(row.id),
            "name": row.name,
            "code": row.slug,
            "is_active": row.is_active,
            "creator_kind": row.creator_kind,
            "recipe_base_id": str(row.recipe_base_id) if row.recipe_base_id else None,
        }
        for row in rows
    ]


def _schedule_out(db, row) -> dict:
    eligible = eligible_ids(db, "default", None)
    return {
        "production_weekdays": row.production_weekdays,
        "daily_physical_limit": row.daily_physical_limit,
        "daily_base_limit": row.daily_base_limit,
        "horizon_days": row.horizon_days,
        "min_advance_hours": row.min_advance_hours,
        "eligibility_mode": row.eligibility_mode,
        "eligible_base_ids": [str(item) for item in sorted(eligible, key=str)] if eligible else [],
        "occupancy_enabled": row.occupancy_enabled,
        "reservation_policy": row.reservation_policy,
    }


@router.get("/schedule")
def admin_get_schedule(db: DbSession, principal: AdminUser) -> dict:
    del principal
    return _schedule_out(db, ensure_schedule_settings(db))


@router.put("/schedule")
def admin_put_schedule(
    payload: DefaultsIn, db: DbSession, settings: AppSettings, principal: AdminUser
) -> dict:
    del principal
    row = save_defaults(
        db,
        settings,
        production_weekdays=payload.production_weekdays,
        daily_physical_limit=payload.daily_physical_limit,
        daily_base_limit=payload.daily_base_limit,
        horizon_days=payload.horizon_days,
        min_advance_hours=payload.min_advance_hours,
        eligibility_mode=payload.eligibility_mode,
        eligible_base_ids=payload.eligible_base_ids,
    )
    return _schedule_out(db, row)


@router.get("/schedule/days/{local_date}")
def admin_get_day(local_date: date, db: DbSession, settings: AppSettings, principal: AdminUser) -> dict:
    del principal
    return admin_day_view(db, settings, local_date)


@router.post("/schedule/weeks/preview")
def admin_preview_week(
    payload: WeekOverrideIn, db: DbSession, settings: AppSettings, principal: AdminUser
) -> dict:
    del principal
    return preview_week_change(
        db,
        settings,
        payload.week_start,
        production_weekdays=payload.production_weekdays,
        daily_physical_limit=payload.daily_physical_limit,
        daily_base_limit=payload.daily_base_limit,
        eligibility_mode=payload.eligibility_mode,
        eligible_base_ids=payload.eligible_base_ids,
    )


@router.put("/schedule/weeks")
def admin_put_week(
    payload: WeekOverrideIn, db: DbSession, settings: AppSettings, principal: AdminUser
) -> dict:
    del principal
    row = save_week_override(
        db,
        settings,
        payload.week_start,
        production_weekdays=payload.production_weekdays,
        daily_physical_limit=payload.daily_physical_limit,
        daily_base_limit=payload.daily_base_limit,
        eligibility_mode=payload.eligibility_mode,
        eligible_base_ids=payload.eligible_base_ids,
    )
    return {"id": str(row.id), "week_start": row.week_start.isoformat()}


@router.delete("/schedule/weeks/{week_start}")
def admin_delete_week(
    week_start: date, db: DbSession, settings: AppSettings, principal: AdminUser
) -> dict:
    del principal
    delete_week_override(db, settings, week_start)
    return {"removed": True}


@router.put("/schedule/dates")
def admin_put_date(
    payload: DateOverrideIn, db: DbSession, settings: AppSettings, principal: AdminUser
) -> dict:
    del principal
    row = save_date_override(
        db,
        settings,
        payload.local_date,
        open_state=payload.open_state,
        daily_physical_limit=payload.daily_physical_limit,
        daily_base_limit=payload.daily_base_limit,
        eligibility_mode=payload.eligibility_mode,
        eligible_base_ids=payload.eligible_base_ids,
    )
    return {"id": str(row.id), "date": row.local_date.isoformat()}


@router.delete("/schedule/dates/{local_date}")
def admin_delete_date(
    local_date: date, db: DbSession, settings: AppSettings, principal: AdminUser
) -> dict:
    del principal
    delete_date_override(db, settings, local_date)
    return {"removed": True}


@router.get("/schedule/closures")
def admin_list_closures(db: DbSession, settings: AppSettings, principal: AdminUser) -> dict:
    del principal
    return list_closures(db, settings)


@router.get("/schedule/closures/commitments")
def admin_closure_commitments(
    db: DbSession,
    principal: AdminUser,
    start: date,
    end: date | None = None,
    first_eligible_date: date | None = None,
) -> dict:
    del principal
    last = end
    if first_eligible_date is not None:
        last = first_eligible_date - timedelta(days=1)
    if last is None or last < start:
        return {"orders": [], "date_requests": [], "order_count": 0, "date_request_count": 0}
    return commitments_in_range(db, start, last)


@router.post("/schedule/closures")
def admin_upsert_closure(
    payload: ClosureIn, db: DbSession, settings: AppSettings, principal: AdminUser
) -> dict:
    row = upsert_closure(
        db,
        settings,
        start_date=payload.start_date,
        end_date=payload.end_date,
        first_eligible_date=payload.first_eligible_date,
        pause_intake=payload.pause_intake,
        internal_reason=payload.internal_reason,
        public_notice=payload.public_notice,
        actor_ref=principal.actor_ref,
    )
    return serialize_closure(db, settings, row)


@router.put("/schedule/closures/{closure_id}")
def admin_update_closure(
    closure_id: UUID, payload: ClosureIn, db: DbSession, settings: AppSettings, principal: AdminUser
) -> dict:
    row = update_closure(
        db,
        settings,
        closure_id,
        start_date=payload.start_date,
        end_date=payload.end_date,
        first_eligible_date=payload.first_eligible_date,
        pause_intake=payload.pause_intake,
        internal_reason=payload.internal_reason,
        public_notice=payload.public_notice,
        actor_ref=principal.actor_ref,
    )
    return serialize_closure(db, settings, row)


@router.post("/schedule/closures/{closure_id}/cancel")
def admin_cancel_closure(
    closure_id: UUID, db: DbSession, settings: AppSettings, principal: AdminUser
) -> dict:
    row = cancel_closure(db, closure_id, actor_ref=principal.actor_ref)
    return serialize_closure(db, settings, row)


@router.get("/schedule/closures/{closure_id}/events")
def admin_closure_events(closure_id: UUID, db: DbSession, principal: AdminUser) -> dict:
    del principal
    return {"items": list_closure_events(db, closure_id)}


@router.get("/custom-loaf")
def admin_custom_loaf(db: DbSession, principal: AdminUser) -> dict:
    del principal
    from app.domain.custom_loaf import public_builder_catalog

    catalog = public_builder_catalog(db)
    return {
        "price_cents": catalog["price_cents"],
        "weight_grams": catalog["weight_grams"],
        "ingredients": list_ingredients(db),
    }


@router.put("/custom-loaf")
def admin_put_custom_loaf(payload: CustomLoafIn, db: DbSession, principal: AdminUser) -> dict:
    del principal
    return update_custom_loaf_price(db, payload.price_cents, payload.weight_grams)


@router.put("/ingredients/{ingredient_id}")
def admin_put_ingredient(
    ingredient_id: UUID, payload: IngredientAdminIn, db: DbSession, principal: AdminUser
) -> dict:
    del principal
    return update_ingredient(db, ingredient_id, payload.model_dump(mode="json"))

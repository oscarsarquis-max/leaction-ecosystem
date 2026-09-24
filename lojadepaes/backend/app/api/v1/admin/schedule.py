from datetime import date
from uuid import UUID

from fastapi import APIRouter
from sqlalchemy import select

from app.api.deps import AdminUser, AppSettings, DbSession
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

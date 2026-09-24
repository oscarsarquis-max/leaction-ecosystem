from fastapi import APIRouter

from app.api.deps import AdminUser, DbSession
from app.domain.showcase import assign_slot, list_admin_slots, move_slot, save_slots
from app.schemas.showcase import (
    ShowcaseAdminOut,
    ShowcaseAssignIn,
    ShowcaseMoveIn,
    ShowcaseSaveIn,
)

router = APIRouter(prefix="/admin/showcase", tags=["admin-showcase"])


@router.get("", response_model=ShowcaseAdminOut)
def admin_get_showcase(db: DbSession, principal: AdminUser) -> ShowcaseAdminOut:
    del principal
    return list_admin_slots(db)


@router.put("", response_model=ShowcaseAdminOut)
def admin_put_showcase(
    payload: ShowcaseSaveIn, db: DbSession, principal: AdminUser
) -> ShowcaseAdminOut:
    del principal
    return save_slots(db, payload.slots)


@router.put("/slots/{position}", response_model=ShowcaseAdminOut)
def admin_put_slot(
    position: int, payload: ShowcaseAssignIn, db: DbSession, principal: AdminUser
) -> ShowcaseAdminOut:
    del principal
    return assign_slot(db, position, payload.product_id)


@router.post("/slots/{position}/move", response_model=ShowcaseAdminOut)
def admin_move_slot(
    position: int, payload: ShowcaseMoveIn, db: DbSession, principal: AdminUser
) -> ShowcaseAdminOut:
    del principal
    return move_slot(db, position, payload.direction)

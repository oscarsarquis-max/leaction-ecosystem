from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.admin import MoneyOut


class ShowcaseProductOut(BaseModel):
    id: UUID
    name: str
    slug: str
    editorial_status: str
    is_available: bool
    thumbnail_url: str | None
    from_price: MoneyOut


class ShowcaseSlotOut(BaseModel):
    position: int
    product_id: UUID | None
    product: ShowcaseProductOut | None


class ShowcaseAdminOut(BaseModel):
    slots: list[ShowcaseSlotOut]


class ShowcaseSlotIn(BaseModel):
    position: int = Field(ge=1, le=10)
    product_id: UUID | None = None


class ShowcaseSaveIn(BaseModel):
    slots: list[ShowcaseSlotIn]


class ShowcaseAssignIn(BaseModel):
    product_id: UUID | None = None


class ShowcaseMoveIn(BaseModel):
    direction: Literal["up", "down"]

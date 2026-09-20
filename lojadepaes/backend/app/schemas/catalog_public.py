from uuid import UUID

from pydantic import BaseModel

from app.schemas.admin import MoneyOut


class PublicVariantOut(BaseModel):
    id: UUID
    display_name: str
    presentation_type: str
    net_weight_grams: int | None
    units_per_pack: int | None
    pack_label: str | None
    price: MoneyOut


class PublicIngredientOut(BaseModel):
    name: str


class PublicProductListItem(BaseModel):
    name: str
    slug: str
    short_description: str
    image_url: str | None
    image_alt: str
    is_available: bool
    from_price: MoneyOut
    price_is_from: bool
    variants: list[PublicVariantOut]


class PublicProductList(BaseModel):
    items: list[PublicProductListItem]
    page: int
    page_size: int
    total: int


class PublicProductDetail(PublicProductListItem):
    long_description: str | None
    ingredients: list[PublicIngredientOut]
    allergen_note: str

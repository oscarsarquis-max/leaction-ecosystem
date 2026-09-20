from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

from app.domain.money import parse_brl_to_cents, slugify
from app.schemas.admin import MoneyOut

EditorialLiteral = Literal["draft", "published", "archived"]
PresentationLiteral = Literal["weight", "pack"]


class IngredientIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    catalog_ingredient_id: UUID | None = None

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("informe o nome do ingrediente")
        return cleaned


class IngredientOut(BaseModel):
    id: UUID
    name: str
    sort_order: int
    catalog_ingredient_id: UUID | None = None


class VariantIn(BaseModel):
    id: UUID | None = None
    display_name: str = Field(min_length=1, max_length=80)
    presentation_type: PresentationLiteral
    net_weight_grams: int | None = Field(default=None, ge=1)
    units_per_pack: int | None = Field(default=None, ge=1)
    price_cents: int | None = Field(default=None, ge=1)
    price_text: str | None = None
    is_active: bool = True

    @field_validator("display_name")
    @classmethod
    def strip_display(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("informe o nome da opção")
        return cleaned

    @model_validator(mode="after")
    def coerce_price(self) -> "VariantIn":
        if self.price_text is not None and self.price_text.strip():
            from app.domain.errors import ProductError

            try:
                parsed = parse_brl_to_cents(self.price_text)
            except ProductError as exc:
                raise ValueError(str(exc)) from exc
            object.__setattr__(self, "price_cents", parsed)
        return self


class VariantOut(BaseModel):
    id: UUID
    display_name: str
    presentation_type: str
    net_weight_grams: int | None
    units_per_pack: int | None
    price: MoneyOut
    is_active: bool
    sort_order: int


class MediaOut(BaseModel):
    id: UUID
    content_type: str
    width: int
    height: int
    url: str
    public_url: str


class ProductEventOut(BaseModel):
    id: UUID
    action: str
    actor_ref: str | None
    detail: str | None
    created_at: datetime


class ProductSaveIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    slug: str | None = Field(default=None, max_length=80)
    short_description: str = Field(default="", max_length=280)
    long_description: str | None = Field(default=None, max_length=8000)
    featured_image_alt: str = Field(default="", max_length=160)
    is_available: bool = True
    sort_order: int = 0
    expected_updated_at: datetime | None = None
    ingredients: list[IngredientIn] = Field(default_factory=list)
    variants: list[VariantIn] = Field(default_factory=list)

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("informe o nome do produto")
        return cleaned

    @field_validator("slug")
    @classmethod
    def clean_slug(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        slug = slugify(value)
        if not slug:
            raise ValueError("identificação pública inválida")
        return slug

    @field_validator("short_description", "featured_image_alt")
    @classmethod
    def strip_text(cls, value: str) -> str:
        return value.strip()


class ProductListQuery(BaseModel):
    query: str | None = Field(default=None, max_length=120)
    status: EditorialLiteral | None = None
    available: bool | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=50)


class AdminProductListItem(BaseModel):
    id: UUID
    name: str
    slug: str
    editorial_status: str
    is_available: bool
    updated_at: datetime
    thumbnail_url: str | None
    from_price: MoneyOut


class AdminProductList(BaseModel):
    items: list[AdminProductListItem]
    page: int
    page_size: int
    total: int


class AdminProductDetail(BaseModel):
    id: UUID
    name: str
    slug: str
    short_description: str
    long_description: str | None
    featured_image: MediaOut | None
    featured_image_alt: str
    editorial_status: str
    is_available: bool
    sort_order: int
    created_at: datetime
    updated_at: datetime
    published_at: datetime | None
    ingredients: list[IngredientOut]
    variants: list[VariantOut]
    events: list[ProductEventOut]
    publication_gaps: list[str]
    from_price: MoneyOut


class AvailabilityIn(BaseModel):
    is_available: bool

from datetime import date

from pydantic import BaseModel


class PartnerCreate(BaseModel):
    partner_type: str
    brand_name: str
    brand_slug: str
    logo_url: str = ""
    photo_url: str = ""
    story: str = ""
    city: str
    region: str
    highlight_hex: str
    document: str
    contact: str
    fee_cents: int = 250
    email: str


class PartnerPatch(BaseModel):
    brand_name: str | None = None
    brand_slug: str | None = None
    logo_url: str | None = None
    photo_url: str | None = None
    story: str | None = None
    city: str | None = None
    region: str | None = None
    highlight_hex: str | None = None
    document: str | None = None
    contact: str | None = None
    fee_cents: int | None = None


class BrandPatch(BaseModel):
    brand_name: str | None = None
    brand_slug: str | None = None
    logo_url: str | None = None
    photo_url: str | None = None
    story: str | None = None
    city: str | None = None
    region: str | None = None
    highlight_hex: str | None = None


class LinkCreate(BaseModel):
    category: str
    link_type: str
    starts_on: date
    ends_on: date | None = None


class LinkEnd(BaseModel):
    ends_on: date | None = None


class PairingIn(BaseModel):
    house_product_slug: str
    reason: str


class ProductCreate(BaseModel):
    category: str
    name: str
    description: str = ""
    photos: list[str] = []
    price_cents: int
    is_available: bool = True
    delivery_cities: list[str] = []
    delivery_districts: list[str] = []
    delivery_cep_prefixes: list[str] = []
    delivery_days: int | None = None
    freight_cents: int | None = None
    perishable: bool = False
    pairings: list[PairingIn] = []


class ProductPatch(BaseModel):
    category: str | None = None
    name: str | None = None
    description: str | None = None
    photos: list[str] | None = None
    price_cents: int | None = None
    is_available: bool | None = None
    delivery_cities: list[str] | None = None
    delivery_districts: list[str] | None = None
    delivery_cep_prefixes: list[str] | None = None
    delivery_days: int | None = None
    freight_cents: int | None = None
    perishable: bool | None = None
    pairings: list[PairingIn] | None = None


class ReviewIn(BaseModel):
    quality: int
    visual: int
    complementarity: int
    decision: str
    note: str = ""


class InviteAccept(BaseModel):
    token: str
    password: str


class PartnerLogin(BaseModel):
    email: str
    password: str

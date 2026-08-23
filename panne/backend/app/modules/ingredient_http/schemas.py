from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.modules.production_http.schemas import StrictModel


class IngredientCreate(StrictModel):
    code: str = Field(min_length=1, max_length=80)
    display_name: str = Field(min_length=1, max_length=200)
    ingredient_type: str
    nutrition_basis_unit_id: UUID
    notes: str | None = Field(default=None, max_length=2000)


class IdentityPatch(StrictModel):
    code: str | None = Field(default=None, max_length=80)
    display_name: str | None = Field(default=None, max_length=200)
    status: str | None = None


class VersionCreate(StrictModel):
    source_version_id: UUID | None = None
    nutrition_basis_unit_id: UUID
    notes: str | None = Field(default=None, max_length=2000)


class DraftPatch(StrictModel):
    notes: str | None = Field(default=None, max_length=2000)
    data_source_id: UUID | None = None


class CompositionWrite(StrictModel):
    component_version_id: UUID
    component_type: str
    quantity: str
    measurement_unit_id: UUID
    sequence: int = Field(ge=0, le=9999)


class NutrientWrite(StrictModel):
    nutrient_id: UUID
    value: str | None = None
    value_status: str
    limit_of_quantification: str | None = None
    loq_unit_id: UUID | None = None
    method_or_source: str | None = Field(default=None, max_length=500)


class AllergenWrite(StrictModel):
    allergen_id: UUID
    presence: str
    data_source_id: UUID | None = None
    evidence_note: str | None = Field(default=None, max_length=500)


class SupplierCreate(StrictModel):
    code: str = Field(min_length=1, max_length=80)
    display_name: str = Field(min_length=1, max_length=200)


class SupplierPatch(StrictModel):
    display_name: str | None = Field(default=None, max_length=200)
    status: str | None = None


class SupplierItemCreate(StrictModel):
    ingredient_id: UUID
    supplier_sku: str = Field(min_length=1, max_length=80)
    description: str | None = Field(default=None, max_length=200)
    package_quantity: str
    measurement_unit_id: UUID


class PriceWrite(StrictModel):
    unit_price: str
    currency: str = Field(min_length=3, max_length=3)
    observed_at: datetime
    source: str | None = Field(default=None, max_length=200)

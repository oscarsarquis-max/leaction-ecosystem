from uuid import UUID

from pydantic import Field

from app.modules.production_http.schemas import StrictModel


class RecipeCreate(StrictModel):
    code: str = Field(min_length=1, max_length=80)
    display_name: str = Field(min_length=1, max_length=200)
    product_code: str | None = Field(default=None, max_length=80)
    product_name: str | None = Field(default=None, max_length=200)


class RecipePatch(StrictModel):
    display_name: str | None = Field(default=None, max_length=200)
    status: str | None = None


class VersionCreate(StrictModel):
    source_version_id: UUID | None = None


class DraftPatch(StrictModel):
    notes: str | None = Field(default=None, max_length=2000)
    yield_units: int | None = Field(default=None, ge=1, le=100000)
    target_unit_weight_g: str | None = None
    expected_bake_loss_rate: str | None = None


class ItemWrite(StrictModel):
    ingredient_version_id: UUID
    sequence: int = Field(ge=1, le=9999)
    net_quantity: str
    measurement_unit_id: UUID
    correction_factor: str = "1"
    is_flour_basis: bool = False
    role: str = "ingredient"
    notes: str | None = Field(default=None, max_length=2000)


class StepWrite(StrictModel):
    sequence: int = Field(ge=1, le=9999)
    title: str = Field(min_length=1, max_length=200)
    instructions: str = Field(min_length=1, max_length=8000)
    duration_seconds: int | None = Field(default=None, ge=0, le=604800)
    temperature_celsius: str | None = None


class ScaleWrite(StrictModel):
    mode: str
    target_total_dough_mass: str | None = None
    unit_count: int | None = Field(default=None, ge=1, le=100000)
    final_unit_weight_g: str | None = None
    bake_loss_rate: str | None = None


class ApprovalWrite(StrictModel):
    decision: str
    notes: str | None = Field(default=None, max_length=2000)


class TrialWrite(StrictModel):
    code: str = Field(min_length=1, max_length=80)
    notes: str | None = Field(default=None, max_length=2000)


class TrialStatusWrite(StrictModel):
    status: str
    notes: str | None = Field(default=None, max_length=2000)


class MeasurementWrite(StrictModel):
    measurement_type: str = Field(min_length=1, max_length=80)
    value: str
    measurement_unit_id: UUID | None = None
    notes: str | None = Field(default=None, max_length=2000)


class ReferenceCreate(StrictModel):
    title: str = Field(min_length=1, max_length=300)
    source_type: str
    source_url: str | None = Field(default=None, max_length=500)
    author: str | None = Field(default=None, max_length=200)
    notes: str | None = Field(default=None, max_length=2000)


class ReferenceLinkWrite(StrictModel):
    recipe_reference_id: UUID
    role: str

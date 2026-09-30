from pydantic import BaseModel, ConfigDict, Field


class WeekRecipeSaveIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = ""
    slug: str = ""
    summary: str = ""
    featured_image_alt: str = ""
    featured_image_caption: str = ""
    image_focus_x: int = Field(default=50, ge=0, le=100)
    image_focus_y: int = Field(default=50, ge=0, le=100)
    prep_time_text: str = ""
    yield_text: str = ""
    ingredients: list[str] = Field(default_factory=list)
    steps: list[str] = Field(default_factory=list)
    method_text: str | None = None
    product_ids: list[str] = Field(default_factory=list)

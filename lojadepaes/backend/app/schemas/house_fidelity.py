from pydantic import BaseModel, ConfigDict, Field


class HouseFidelitySignupIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=160)
    email: str = Field(min_length=3, max_length=254)


class HouseFidelityResumeIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str = Field(min_length=3, max_length=254)

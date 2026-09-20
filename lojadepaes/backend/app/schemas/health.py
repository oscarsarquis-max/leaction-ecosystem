from typing import Literal

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
    service: Literal["lojadepaes"] = "lojadepaes"


class ReadyResponse(BaseModel):
    status: Literal["ok"] | Literal["unavailable"]
    service: Literal["lojadepaes"] = "lojadepaes"

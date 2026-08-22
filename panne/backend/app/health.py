from typing import Literal

from pydantic import BaseModel, Field

from app.config import get_settings


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
    service: Literal["panne"] = "panne"
    versao: str = Field(..., description="Versão declarada da fundação")
    ambiente: str


def build_health() -> HealthResponse:
    settings = get_settings()
    return HealthResponse(versao=settings.versao, ambiente=settings.env)

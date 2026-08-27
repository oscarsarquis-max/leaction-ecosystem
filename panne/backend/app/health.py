from __future__ import annotations

import os
from typing import Literal
from urllib.parse import urlparse

from pydantic import BaseModel, Field

from app.config import get_settings


class DemoRuntimeInfo(BaseModel):
    """Identidade da execução demo — sem segredos, só em PANNE_ENV=demo."""

    instance_id: str | None = None
    started_at: str | None = None
    logical_database: str | None = None
    demo_anchor_date: str | None = None
    process_id: int | None = None


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
    service: Literal["panne"] = "panne"
    versao: str = Field(..., description="Versão declarada da fundação")
    ambiente: str
    demo: DemoRuntimeInfo | None = None


def _logical_database_name(url: str) -> str | None:
    if not url:
        return None
    # Evita vazar user/senha: só o path lógico.
    try:
        parsed = urlparse(url)
        name = (parsed.path or "").lstrip("/").split("/")[0]
        return name or None
    except Exception:
        return None


def build_health() -> HealthResponse:
    settings = get_settings()
    demo: DemoRuntimeInfo | None = None
    if settings.env == "demo":
        demo = DemoRuntimeInfo(
            instance_id=settings.demo_instance_id or None,
            started_at=settings.demo_started_at or None,
            logical_database=_logical_database_name(settings.database_url),
            demo_anchor_date=settings.demo_anchor_date or None,
            process_id=os.getpid(),
        )
    return HealthResponse(versao=settings.versao, ambiente=settings.env, demo=demo)

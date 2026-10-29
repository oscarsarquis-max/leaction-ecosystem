"""GET /dashboard/today — leitura org-scoped e establishment-scoped. Sem escrita."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db import get_runtime_session
from app.modules.dashboard_today.charts import PERIODS
from app.modules.dashboard_today.service import build_today
from app.modules.identity_organization.authorization import Principal
from app.modules.production_http.deps import get_runtime_principal
from app.modules.production_http.errors import raise_domain
from app.modules.production_planning.errors import ValidationError

router = APIRouter()


@router.get("/dashboard/today")
def dashboard_today(
    organization_id: UUID,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
    establishment_id: UUID | None = Query(default=None),
    period: str = Query(default="today"),
) -> dict:
    if period not in PERIODS:
        raise_domain(ValidationError("contrato_invalido"))
    try:
        return build_today(session, principal, organization_id, establishment_id, period)
    except Exception as exc:
        raise_domain(exc)
        raise

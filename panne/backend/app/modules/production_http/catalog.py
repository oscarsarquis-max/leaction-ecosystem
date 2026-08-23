"""Catálogos autenticados para o modo operacional. Sem duplicar regras no cliente."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_runtime_session
from app.modules.identity_organization.authorization import (
    PERMISSION_PRODUCTION_ORDER_READ,
    Principal,
    require_permission,
)
from app.modules.ingredient_catalog.models import MeasurementUnit
from app.modules.production_execution.constants import (
    CONSUMPTION_TYPES,
    OCCURRENCE_CATEGORIES,
    SEVERITIES,
    SHEET_PURPOSES,
    STEP_STATUSES,
    VERIFY_DECISIONS,
    VERIFICATION_POLICIES,
    WEIGHING_POLICIES,
    YIELD_TYPES,
)
from app.modules.production_http.deps import get_runtime_principal
from app.modules.production_http.errors import raise_domain
from app.modules.production_http.schemas import envelope
from app.modules.production_planning.constants import BATCH_STATUSES, ORDER_STATUSES

router = APIRouter()


@router.get("/catalog")
def get_operational_catalog(
    organization_id: UUID,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
):
    try:
        require_permission(principal, PERMISSION_PRODUCTION_ORDER_READ)
    except Exception as exc:
        raise_domain(exc)
    units = list(
        session.scalars(
            select(MeasurementUnit)
            .where(MeasurementUnit.dimension == "mass", MeasurementUnit.status == "active")
            .order_by(MeasurementUnit.code)
        )
    )
    mass_units = [
        unit
        for unit in units
        if unit.code in {"g", "kg"} or (unit.symbol or "").lower() in {"g", "kg"}
    ]
    if not mass_units:
        mass_units = units
    return envelope(
        {
            "mass_units": [
                {
                    "id": str(unit.id),
                    "code": unit.code,
                    "name": unit.name,
                    "symbol": unit.symbol or unit.code,
                    "dimension": unit.dimension,
                }
                for unit in mass_units
            ],
            "yield_types": list(YIELD_TYPES),
            "occurrence_categories": list(OCCURRENCE_CATEGORIES),
            "occurrence_severities": list(SEVERITIES),
            "consumption_types": list(CONSUMPTION_TYPES),
            "verification_decisions": list(VERIFY_DECISIONS),
            "sheet_purposes": list(SHEET_PURPOSES),
            "weighing_policies": list(WEIGHING_POLICIES),
            "verification_policies": list(VERIFICATION_POLICIES),
            "order_statuses": list(ORDER_STATUSES),
            "batch_statuses": list(BATCH_STATUSES),
            "step_statuses": list(STEP_STATUSES),
        }
    )

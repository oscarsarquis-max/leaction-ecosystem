"""Perfil de Campo — satélite, elementos acompanhados e catálogo de papéis por indústria.

Definido pelo sysadmin no Framework Builder ao editar um framework publicado.
Fonte de verdade pra app.core.professional_role_catalog quando presente
(com fallback pro dict hardcoded quando a indústria ainda não tem perfil definido).
"""
from __future__ import annotations

from typing import Any

from app.database.models import Framework, db
from app.models.operational_models import IndustryType

FIELD_PROFILE_KEY = "field_operations_profile"
VALID_INDUSTRY_TYPES = tuple(t.value for t in IndustryType)


def get_field_operations_profile(framework_id: str) -> dict[str, Any]:
    framework = db.session.get(Framework, framework_id)
    if not framework:
        raise ValueError(f"Framework '{framework_id}' não encontrado.")
    profile = (framework.rules_metadata or {}).get(FIELD_PROFILE_KEY) or {}
    return {
        "industry_type": profile.get("industry_type"),
        "satellite_type": profile.get("satellite_type"),
        "tracked_elements": profile.get("tracked_elements") or [],
        "role_catalog": profile.get("role_catalog") or [],
    }


def update_field_operations_profile(framework_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    framework = db.session.get(Framework, framework_id)
    if not framework:
        raise ValueError(f"Framework '{framework_id}' não encontrado.")

    industry_type = str(payload.get("industry_type") or "").strip() or None
    satellite_type = str(payload.get("satellite_type") or "").strip() or None
    tracked_elements_raw = payload.get("tracked_elements") or []
    role_catalog_raw = payload.get("role_catalog") or []

    has_content = bool(satellite_type or tracked_elements_raw or role_catalog_raw)
    if has_content and not industry_type:
        raise ValueError("Selecione a indústria antes de definir satélite, elementos ou papéis.")
    if industry_type and industry_type not in VALID_INDUSTRY_TYPES:
        raise ValueError(f"industry_type inválido. Use um de: {', '.join(VALID_INDUSTRY_TYPES)}")

    # Cada indústria só pode ter UM framework como referência operacional — evita
    # ambiguidade na resolução do catálogo de papéis (professional_role_catalog).
    if industry_type:
        others = Framework.query.filter(
            Framework.id != framework_id, Framework.is_active.is_(True)
        ).all()
        for other in others:
            other_profile = (other.rules_metadata or {}).get(FIELD_PROFILE_KEY) or {}
            if other_profile.get("industry_type") == industry_type:
                raise ValueError(
                    f"O framework '{other.name}' já é o Perfil de Campo da indústria "
                    f"'{industry_type}'. Cada indústria só pode ter um framework de referência."
                )

    tracked_elements = []
    for item in tracked_elements_raw:
        key = str(item.get("key") or "").strip()
        label = str(item.get("label") or "").strip()
        if not key or not label:
            continue
        tracked_elements.append(
            {
                "key": key,
                "label": label,
                "description": str(item.get("description") or "").strip() or None,
            }
        )

    role_catalog = []
    for item in role_catalog_raw:
        value = str(item.get("value") or "").strip()
        label = str(item.get("label") or value).strip()
        if not value:
            continue
        role_catalog.append({"value": value, "label": label})

    profile = {
        "industry_type": industry_type,
        "satellite_type": satellite_type,
        "tracked_elements": tracked_elements,
        "role_catalog": role_catalog,
    }
    framework.rules_metadata = {**(framework.rules_metadata or {}), FIELD_PROFILE_KEY: profile}
    db.session.commit()
    return profile

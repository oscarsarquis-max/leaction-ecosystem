"""Catálogo de papéis funcionais — base (TD/Capacity) + extensões por indústria.

Fonte preferencial: Perfil de Campo (`field_operations_profile`) no Framework
publicado para aquela indústria. O dict hardcoded INDUSTRY_ROLE_CATALOG é
fallback quando a indústria ainda não tem perfil definido no Builder.
"""

from __future__ import annotations

from app.database.models import Framework
from app.models.capacity_models import PROFESSIONAL_ROLES
from app.models.operational_models import IndustryType

FIELD_PROFILE_KEY = "field_operations_profile"

# Fallback — usado só quando a indústria ainda não tem Perfil de Campo definido
# no Framework Builder. Construção começou aqui (Prompt 7); pode ser substituído
# a qualquer momento por um framework publicado com Perfil de Campo pra Construção,
# sem exigir mudança de código.
INDUSTRY_ROLE_CATALOG: dict[str, tuple[tuple[str, str], ...]] = {
    IndustryType.CONSTRUCAO.value: (
        ("Engenheiro", "Engenheiro"),
        ("Mestre_de_Obras", "Mestre de Obras / Gerente de Canteiro"),
    ),
}

BASE_ROLE_LABELS: dict[str, str] = {
    "PO": "Product Owner (PO)",
    "Scrum_Master": "Scrum Master",
    "Dev": "Dev",
    "QA": "QA",
    "Analista_TI": "Analista de TI",
    "Analista_Negocio": "Analista de Negócio",
    "Gerente_Projeto": "Gerente de Projeto",
    "Outro": "Outro",
}


def _framework_role_catalog(industry_type: str) -> list[dict[str, str]] | None:
    """Catálogo definido pelo sysadmin (Perfil de Campo) pra essa indústria, se existir."""
    frameworks = Framework.query.filter_by(is_active=True).all()
    for framework in frameworks:
        profile = (framework.rules_metadata or {}).get(FIELD_PROFILE_KEY) or {}
        if profile.get("industry_type") == industry_type:
            roles = profile.get("role_catalog") or []
            if roles:
                return [
                    {"value": r["value"], "label": r.get("label", r["value"])}
                    for r in roles
                    if r.get("value")
                ]
    return None


def get_role_catalog(industry_types: set[str] | None = None) -> list[dict[str, str]]:
    catalog = [
        {"value": v, "label": BASE_ROLE_LABELS.get(v, v), "group": "squad"}
        for v in PROFESSIONAL_ROLES
    ]
    keys = set(INDUSTRY_ROLE_CATALOG.keys()) if industry_types is None else industry_types
    for key in keys:
        dynamic = _framework_role_catalog(key)
        source = (
            dynamic
            if dynamic is not None
            else [{"value": v, "label": l} for v, l in INDUSTRY_ROLE_CATALOG.get(key, ())]
        )
        for item in source:
            if not any(existing["value"] == item["value"] for existing in catalog):
                catalog.append({"value": item["value"], "label": item["label"], "group": key})
    return catalog


def get_valid_roles(industry_types: set[str] | None = None) -> tuple[str, ...]:
    return tuple(item["value"] for item in get_role_catalog(industry_types))

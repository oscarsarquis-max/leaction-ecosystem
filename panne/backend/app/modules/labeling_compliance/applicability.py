"""Perfil de aplicabilidade. Ausência não é isenção."""

from app.modules.labeling_compliance.constants import REQUIRED_PROFILE_FIELDS
from app.modules.labeling_compliance.models import LabelingApplicabilityProfile
from app.modules.labeling_compliance.portions import get_portion


def profile_payload(profile: LabelingApplicabilityProfile | None) -> dict:
    if profile is None:
        return {field: None for field in REQUIRED_PROFILE_FIELDS} | {
            "category_confirmed": False,
            "completeness": "incomplete",
        }
    return {
        "jurisdiction": profile.jurisdiction,
        "evaluation_date": None if profile.evaluation_date is None else profile.evaluation_date.isoformat(),
        "packed_food": profile.packed_food,
        "packed_away_from_consumer": profile.packed_away_from_consumer,
        "packed_at_point_of_sale": profile.packed_at_point_of_sale,
        "packed_on_request": profile.packed_on_request,
        "same_establishment": profile.same_establishment,
        "sales_channel": profile.sales_channel,
        "food_service": profile.food_service,
        "physical_state": profile.physical_state,
        "ready_to_eat": profile.ready_to_eat,
        "regulatory_category_code": profile.regulatory_category_code,
        "category_confirmed": profile.category_confirmed,
        "package_area_cm2": None if profile.package_area_cm2 is None else format(profile.package_area_cm2, "f"),
        "net_content_g": None if profile.net_content_g is None else format(profile.net_content_g, "f"),
        "servings_per_package": profile.servings_per_package,
        "purpose": profile.purpose,
        "destination_market": profile.destination_market,
        "completeness": profile.completeness,
    }


def classify_profile(data: dict) -> str:
    missing = [field for field in REQUIRED_PROFILE_FIELDS if data.get(field) in (None, "")]
    if missing:
        return "incomplete"
    if not data.get("category_confirmed"):
        return "incomplete"
    if get_portion(data.get("regulatory_category_code")) is None:
        return "incomplete"
    return "complete"


def front_labeling_scope(profile: LabelingApplicabilityProfile | None) -> str:
    if profile is None or profile.completeness != "complete":
        return "insufficient_context"
    if profile.physical_state not in {"solid", "semisolid"}:
        return "insufficient_context"
    if profile.packed_food is True and profile.packed_away_from_consumer is True:
        return "applicable"
    if (
        profile.packed_food is False
        or profile.same_establishment is True
        or profile.packed_on_request is True
    ) and profile.packed_away_from_consumer is False:
        return "not_applicable"
    return "insufficient_context"

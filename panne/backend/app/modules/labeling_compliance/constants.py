"""Constantes fechadas. Sem selo de conformidade."""

from decimal import Decimal

ALGORITHM_NAME = "labeling_compliance"
ALGORITHM_VERSION = "1"

FINDING_RESULTS = frozenset(
    {
        "pass",
        "fail",
        "insufficient_evidence",
        "insufficient_context",
        "manual_review_required",
        "not_applicable",
    }
)
ENGINE_RESULT_MAP = {
    "pass": "pass",
    "fail": "fail",
    "insufficient_data": "insufficient_evidence",
    "manual_review": "manual_review_required",
    "not_applicable": "not_applicable",
}

DOSSIER_STATUSES = frozenset({"draft", "evaluated", "reviewed", "invalidated"})
REVIEW_DECISIONS = frozenset({"accepted", "rejected", "needs_changes"})
WATERMARKS = {
    "draft": "Proposta técnica — não é rótulo aprovado",
    "evaluated": "Proposta técnica para revisão",
    "reviewed": "Revisado internamente — não é declaração de conformidade",
    "invalidated": "Candidato invalidado",
}

SOLID_ADDED_SUGARS_G = Decimal("15")
SOLID_SATURATED_FAT_G = Decimal("6")
SOLID_SODIUM_MG = Decimal("600")
LIQUID_ADDED_SUGARS_G = Decimal("7.5")
LIQUID_SATURATED_FAT_G = Decimal("3")
LIQUID_SODIUM_MG = Decimal("300")

DAILY_VALUES = {
    "energy_kcal": Decimal("2000"),
    "carbohydrate": Decimal("300"),
    "added_sugars": Decimal("50"),
    "protein": Decimal("50"),
    "total_fat": Decimal("55"),
    "saturated_fat": Decimal("22"),
    "fiber": Decimal("25"),
    "sodium": Decimal("2000"),
}

MANDATORY_NUTRIENTS = (
    "energy_kcal",
    "carbohydrate",
    "total_sugars",
    "added_sugars",
    "protein",
    "total_fat",
    "saturated_fat",
    "trans_fat",
    "fiber",
    "sodium",
)

MANDATORY_ITEMS = (
    "denominacao_venda",
    "lista_ingredientes",
    "advertencias",
    "conteudo_liquido",
    "origem",
    "lote",
    "prazo_validade",
    "conservacao",
    "preparo",
    "identificacao_responsavel",
    "registro",
)

REQUIRED_PROFILE_FIELDS = (
    "jurisdiction",
    "evaluation_date",
    "packed_food",
    "packed_away_from_consumer",
    "packed_at_point_of_sale",
    "packed_on_request",
    "same_establishment",
    "sales_channel",
    "food_service",
    "physical_state",
    "ready_to_eat",
    "regulatory_category_code",
    "net_content_g",
    "servings_per_package",
    "purpose",
    "destination_market",
)

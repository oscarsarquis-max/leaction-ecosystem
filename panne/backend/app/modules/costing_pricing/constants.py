"""Vocabulário e constantes fechadas. Markup não é margem."""

from decimal import Decimal

ALGORITHM_NAME = "costing_pricing"
ALGORITHM_VERSION = "1"

COST_KINDS = frozenset({"planned", "standard", "actual"})
COMPLETENESS = frozenset({"complete", "partial", "insufficient_data", "invalidated"})
SOURCE_QUALITIES = frozenset(
    {
        "operational_fact",
        "current_price",
        "standard_cost",
        "manual_assumption",
        "estimate",
        "missing",
    }
)
CATEGORIES = (
    "ingredient",
    "packaging",
    "labor",
    "energy",
    "outsourced",
    "variable_indirect",
    "fixed_allocation",
    "waste",
    "rework",
    "other",
)
PRICE_CRITERIA = frozenset({"latest_observed", "explicit_item"})
POLICY_STATUSES = frozenset({"draft", "published", "retired"})
PRICE_STATUSES = frozenset({"draft", "approved", "active", "retired", "cancelled"})
CHANNELS = (
    "own_counter",
    "made_to_order",
    "wholesale",
    "own_delivery",
    "marketplace",
    "other",
)
SIMULATION_KINDS = frozenset(
    {"markup_factor", "markup_percent", "gross_margin", "contribution_margin", "reverse"}
)

MONEY_QUANTUM = Decimal("0.000001")
PERCENT_QUANTUM = Decimal("0.0001")
ONE = Decimal("1")
HUNDRED = Decimal("100")
ZERO = Decimal("0")

FISCAL_DISCLAIMER = (
    "Premissa comercial manual. A Panne não apura nem valida obrigação fiscal."
)

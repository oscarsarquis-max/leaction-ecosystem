"""Catálogos fechados da governança. Sem expressão livre."""

ALGORITHM_NAME = "deterministic_compliance"
ALGORITHM_VERSION = "1"

REGULATORY_DOMAINS = frozenset(
    {
        "labeling",
        "nutrition",
        "gmp",
        "sop",
        "haccp",
        "allergens",
        "ingredients_additives_packaging",
        "regularization",
        "occupational_safety",
        "state_municipal",
        "private_technical_standards",
    }
)
FRAMEWORK_SCOPES = frozenset({"global", "organizational"})
FRAMEWORK_STATUSES = frozenset({"draft", "active", "archived"})
VERSION_STATUSES = frozenset(
    {"draft", "pending_review", "active", "superseded", "revoked"}
)
EDITABLE_VERSION_STATUSES = frozenset({"draft"})
NORMATIVE_FORCES = frozenset({"mandatory", "recommended", "informational"})
SEVERITIES = frozenset({"critical", "major", "minor", "info"})
EVALUATION_TYPES = frozenset(
    {
        "evidence_presence",
        "numeric_comparison",
        "boolean_condition",
        "catalog_membership",
        "mandatory_manual_review",
        "compound",
    }
)
CITATION_ROLES = frozenset(
    {"foundation", "definition", "threshold", "exception", "guidance"}
)
REQUIREMENT_REVIEW_STATUSES = frozenset({"pending", "reviewed", "rejected"})
ACTIVITIES = frozenset({"food_service", "producer_processor", "hybrid"})
ASSESSMENT_STATUSES = frozenset({"draft", "evaluated", "reviewed", "invalidated"})
COMPLETENESS = frozenset({"complete", "incomplete", "insufficient_context"})
FINDING_RESULTS = frozenset(
    {"pass", "fail", "not_applicable", "insufficient_data", "manual_review"}
)
REVIEW_DECISIONS = frozenset({"accepted", "rejected", "needs_changes", "revoked"})
NORMATIVE_CLASSES = frozenset(
    {
        "in_force_act",
        "future_act",
        "revoked_or_superseded",
        "proposal",
        "official_guidance",
        "private_standard",
        "non_normative_technical",
    }
)
TARGET_TYPES = frozenset(
    {
        "formulation_version",
        "ingredient_version",
        "establishment",
        "technical_product",
    }
)
NUMERIC_OPERATORS = frozenset({"eq", "ne", "gt", "gte", "lt", "lte"})
COMPOUND_OPERATORS = frozenset({"and", "or"})
FOUNDATION_CLASSES = frozenset({"in_force_act", "private_standard"})
PROPOSAL_STATUSES = frozenset({"draft", "public_consultation"})

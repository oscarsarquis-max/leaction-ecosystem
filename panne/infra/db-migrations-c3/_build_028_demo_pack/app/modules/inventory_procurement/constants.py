"""Vocabulário e conjuntos fechados do estoque e das compras."""

from decimal import Decimal

ALGORITHM_NAME = "inventory_procurement"
ALGORITHM_VERSION = "1"
CURRENCY = "BRL"
ZERO = Decimal("0")

LOT_MODES = ("required", "optional", "not_applicable")
LOT_CONSUMPTION = ("manual", "fefo_suggest")
CANCELLED_ORDER_TREATMENTS = ("release_reservation",)
NEGATIVE_POLICIES = ("deny", "allow")

LOCATION_KINDS = ("warehouse", "production", "quarantine", "other")
LOCATION_STATUSES = ("active", "inactive")
ITEM_STATUSES = ("active", "inactive")
LOT_STATUSES = ("available", "quarantined", "blocked", "expired", "exhausted", "closed")
BLOCKED_LOT_STATUSES = ("quarantined", "blocked", "expired", "exhausted", "closed")

MOVEMENT_TYPES = (
    "receipt",
    "transfer_out",
    "transfer_in",
    "production_consume",
    "production_return",
    "waste",
    "supplier_return",
    "adjust_plus",
    "adjust_minus",
    "reverse",
    "opening",
)
PHYSICAL_IN = frozenset({"receipt", "transfer_in", "production_return", "adjust_plus", "opening"})
PHYSICAL_OUT = frozenset(
    {"transfer_out", "production_consume", "waste", "supplier_return", "adjust_minus"}
)

RESERVATION_STATUSES = (
    "pending",
    "partial",
    "reserved",
    "released",
    "consumed",
    "cancelled",
    "expired",
)
ACTIVE_RESERVATION_STATUSES = frozenset({"pending", "partial", "reserved"})

PICK_STATUSES = ("draft", "confirmed", "cancelled")
POSTING_STATUSES = ("pending", "posted", "failed")

COUNT_STATUSES = ("draft", "scoped", "counting", "review", "approved", "closed")
COUNT_PASSES = (1, 2)

REQUISITION_STATUSES = ("draft", "submitted", "approved", "rejected", "converted", "cancelled")
ORDER_STATUSES = (
    "draft",
    "approved",
    "issued",
    "partially_received",
    "received",
    "cancelled",
    "closed",
)
RECEIPT_STATUSES = ("draft", "posted", "cancelled")
RETURN_STATUSES = ("draft", "posted")

CODE_KINDS = ("LOT", "REQ", "PO", "RCP", "RET", "PICK", "CNT", "RPL")

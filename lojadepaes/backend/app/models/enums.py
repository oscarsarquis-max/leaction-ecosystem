from enum import StrEnum


class OrderStatus(StrEnum):
    DRAFT = "draft"
    CONFIRMED = "confirmed"
    IN_PRODUCTION = "in_production"
    READY = "ready"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


# Ocupação não deriva só do status: ver Order.holds_capacity.
# confirmed / in_production / ready / completed mantêm a vaga.
# cancelled só mantém se a produção já tiver começado.
CAPACITY_HOLDING_STATUSES: frozenset[str] = frozenset(
    {
        OrderStatus.CONFIRMED.value,
        OrderStatus.IN_PRODUCTION.value,
        OrderStatus.READY.value,
        OrderStatus.COMPLETED.value,
    }
)

ALLOWED_TRANSITIONS: dict[str, frozenset[str]] = {
    OrderStatus.DRAFT.value: frozenset({OrderStatus.CONFIRMED.value, OrderStatus.CANCELLED.value}),
    OrderStatus.CONFIRMED.value: frozenset(
        {OrderStatus.IN_PRODUCTION.value, OrderStatus.CANCELLED.value}
    ),
    OrderStatus.IN_PRODUCTION.value: frozenset(
        {OrderStatus.READY.value, OrderStatus.CANCELLED.value}
    ),
    OrderStatus.READY.value: frozenset({OrderStatus.COMPLETED.value, OrderStatus.CANCELLED.value}),
    OrderStatus.COMPLETED.value: frozenset(),
    OrderStatus.CANCELLED.value: frozenset(),
}


class FulfillmentModality(StrEnum):
    PICKUP = "pickup"
    DELIVERY = "delivery"


class BatchStatus(StrEnum):
    PLANNED = "planned"
    OPEN = "open"
    CLOSED = "closed"
    CANCELLED = "cancelled"


class AllergenPresence(StrEnum):
    CONTAINS = "contains"
    MAY_CONTAIN = "may_contain"


class EditorialStatus(StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class PresentationType(StrEnum):
    WEIGHT = "weight"
    PACK = "pack"


class ProductEventAction(StrEnum):
    CREATED = "created"
    UPDATED = "updated"
    PUBLISHED = "published"
    UNPUBLISHED = "unpublished"
    ARCHIVED = "archived"
    AVAILABILITY = "availability"
    IMAGE = "image"


class PaymentProvider(StrEnum):
    ACTIONHUB = "actionhub"


class FinancialStatus(StrEnum):
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PARTIALLY_REFUNDED = "partially_refunded"
    REFUNDED = "refunded"
    UNKNOWN = "unknown"


class EventProcessStatus(StrEnum):
    RECEIVED = "received"
    IGNORED = "ignored"
    APPLIED = "applied"
    FAILED = "failed"


class ContentSource(StrEnum):
    EDITORIAL = "editorial"
    COMMUNITY = "community"

PLAN_STATUS_DRAFT = "draft"
PLAN_STATUS_SCHEDULED = "scheduled"
PLAN_STATUS_ARCHIVED = "archived"
PLAN_STATUSES = (PLAN_STATUS_DRAFT, PLAN_STATUS_SCHEDULED, PLAN_STATUS_ARCHIVED)

ORDER_STATUS_DRAFT = "draft"
ORDER_STATUS_SCHEDULED = "scheduled"
ORDER_STATUS_RELEASED = "released"
ORDER_STATUS_IN_WEIGHING = "in_weighing"
ORDER_STATUS_READY = "ready"
ORDER_STATUS_IN_PROGRESS = "in_progress"
ORDER_STATUS_ON_HOLD = "on_hold"
ORDER_STATUS_COMPLETED = "completed"
ORDER_STATUS_SHORT_CLOSED = "short_closed"
ORDER_STATUS_CANCELLED = "cancelled"
ORDER_STATUSES = (
    ORDER_STATUS_DRAFT,
    ORDER_STATUS_SCHEDULED,
    ORDER_STATUS_RELEASED,
    ORDER_STATUS_IN_WEIGHING,
    ORDER_STATUS_READY,
    ORDER_STATUS_IN_PROGRESS,
    ORDER_STATUS_ON_HOLD,
    ORDER_STATUS_COMPLETED,
    ORDER_STATUS_SHORT_CLOSED,
    ORDER_STATUS_CANCELLED,
)
ORDER_EDITABLE = (ORDER_STATUS_DRAFT, ORDER_STATUS_SCHEDULED)
ORDER_RELEASED_FAMILY = (
    ORDER_STATUS_RELEASED,
    ORDER_STATUS_IN_WEIGHING,
    ORDER_STATUS_READY,
    ORDER_STATUS_IN_PROGRESS,
    ORDER_STATUS_ON_HOLD,
    ORDER_STATUS_COMPLETED,
    ORDER_STATUS_SHORT_CLOSED,
    ORDER_STATUS_CANCELLED,
)

BATCH_STATUS_PENDING = "pending"
BATCH_STATUS_IN_WEIGHING = "in_weighing"
BATCH_STATUS_READY = "ready"
BATCH_STATUS_IN_PROGRESS = "in_progress"
BATCH_STATUS_ON_HOLD = "on_hold"
BATCH_STATUS_COMPLETED = "completed"
BATCH_STATUS_SCRAPPED = "scrapped"
BATCH_STATUS_CANCELLED = "cancelled"
BATCH_STATUS_SHORT_CLOSED = "short_closed"
BATCH_STATUSES = (
    BATCH_STATUS_PENDING,
    BATCH_STATUS_IN_WEIGHING,
    BATCH_STATUS_READY,
    BATCH_STATUS_IN_PROGRESS,
    BATCH_STATUS_ON_HOLD,
    BATCH_STATUS_COMPLETED,
    BATCH_STATUS_SCRAPPED,
    BATCH_STATUS_CANCELLED,
    BATCH_STATUS_SHORT_CLOSED,
)

SHIFT_MORNING = "morning"
SHIFT_AFTERNOON = "afternoon"
SHIFT_NIGHT = "night"
SHIFTS = (SHIFT_MORNING, SHIFT_AFTERNOON, SHIFT_NIGHT)

TARGET_MODE_UNITS = "units"
TARGET_MODE_MASS = "mass"
TARGET_MODES = (TARGET_MODE_UNITS, TARGET_MODE_MASS)

DEPENDENCY_PREFERMENT = "preferment"
DEPENDENCY_INTERMEDIATE = "intermediate"
DEPENDENCY_OTHER = "other"
DEPENDENCY_TYPES = (DEPENDENCY_PREFERMENT, DEPENDENCY_INTERMEDIATE, DEPENDENCY_OTHER)

CODE_KIND_PLAN = "plan"
CODE_KIND_ORDER = "order"
CODE_KIND_SHEET = "sheet"

COMMAND_CREATE_PLAN = "create_plan"
COMMAND_UPSERT_PLAN_ITEM = "upsert_plan_item"
COMMAND_REMOVE_PLAN_ITEM = "remove_plan_item"
COMMAND_SCHEDULE_PLAN = "schedule_plan"
COMMAND_CREATE_ORDER = "create_order"
COMMAND_SCHEDULE_ORDER = "schedule_order"
COMMAND_ADD_DEPENDENCY = "add_dependency"
COMMAND_SPLIT_BATCHES = "split_batches"
COMMAND_RELEASE_ORDER = "release_order"
COMMAND_HOLD_ORDER = "hold_order"
COMMAND_CANCEL_ORDER = "cancel_order"
COMMAND_CREATE_SUBSTITUTE = "create_substitute_order"

EVENT_PLAN_CREATED = "plan.created"
EVENT_PLAN_ITEM_UPSERTED = "plan.item_upserted"
EVENT_PLAN_ITEM_REMOVED = "plan.item_removed"
EVENT_PLAN_SCHEDULED = "plan.scheduled"
EVENT_ORDER_CREATED = "order.created"
EVENT_ORDER_SCHEDULED = "order.scheduled"
EVENT_DEPENDENCY_ADDED = "dependency.added"
EVENT_BATCH_SPLIT = "batch.split"
EVENT_ORDER_RELEASED = "order.released"
EVENT_ORDER_HELD = "order.held"
EVENT_ORDER_CANCELLED = "order.cancelled"
EVENT_ORDER_SUBSTITUTED = "order.substituted"

EVENT_PAYLOADS: dict[str, frozenset[str]] = {
    EVENT_PLAN_CREATED: frozenset({"public_code", "operational_date", "shift"}),
    EVENT_PLAN_ITEM_UPSERTED: frozenset({"plan_item_id", "technical_product_id", "sort_order"}),
    EVENT_PLAN_ITEM_REMOVED: frozenset({"plan_item_id", "technical_product_id", "sort_order"}),
    EVENT_PLAN_SCHEDULED: frozenset({"public_code"}),
    EVENT_ORDER_CREATED: frozenset({"public_code", "technical_product_id", "target_mode"}),
    EVENT_ORDER_SCHEDULED: frozenset({"public_code"}),
    EVENT_DEPENDENCY_ADDED: frozenset({"dependency_id", "predecessor_order_id", "dependency_type"}),
    EVENT_BATCH_SPLIT: frozenset({"batch_count", "method"}),
    EVENT_ORDER_RELEASED: frozenset(
        {"public_code", "materials_hash", "steps_hash", "snapshot_hash", "policy_hash"}
    ),
    EVENT_ORDER_HELD: frozenset({"reason"}),
    EVENT_ORDER_CANCELLED: frozenset({"reason"}),
    EVENT_ORDER_SUBSTITUTED: frozenset({"substitute_order_id", "public_code"}),
}

REMAINDER_FIRST_BATCHES = "first_batches_in_sequence"
SPLIT_METHOD = "equal_share_plus_remainder"
ALGORITHM_CODE = "deterministic_scale"
SNAPSHOT_SCHEMA_VERSION = 1

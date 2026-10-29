POLICY_WEIGHING_REQUIRED = "required"
POLICY_WEIGHING_OPTIONAL = "optional"
POLICY_WEIGHING_NOT_APPLICABLE = "not_applicable"
WEIGHING_POLICIES = (
    POLICY_WEIGHING_REQUIRED,
    POLICY_WEIGHING_OPTIONAL,
    POLICY_WEIGHING_NOT_APPLICABLE,
)

VERIFICATION_NONE = "none"
VERIFICATION_SECOND_PERSON = "second_person"
VERIFICATION_POLICIES = (VERIFICATION_NONE, VERIFICATION_SECOND_PERSON)

SESSION_OPEN = "open"
SESSION_COMPLETED = "completed"
SESSION_CANCELLED = "cancelled"
SESSION_STATUSES = (SESSION_OPEN, SESSION_COMPLETED, SESSION_CANCELLED)

ENTRY_RECORD = "record"
ENTRY_REVERSAL = "reversal"
ENTRY_CORRECTION = "correction"
ENTRY_TYPES = (ENTRY_RECORD, ENTRY_REVERSAL, ENTRY_CORRECTION)

VERIFY_ACCEPTED = "accepted"
VERIFY_REJECTED = "rejected"
VERIFY_DECISIONS = (VERIFY_ACCEPTED, VERIFY_REJECTED)

CONSUMPTION_CONSUME = "consume"
CONSUMPTION_RETURN = "return"
CONSUMPTION_WASTE = "waste"
CONSUMPTION_CORRECTION = "correction"
CONSUMPTION_TYPES = (
    CONSUMPTION_CONSUME,
    CONSUMPTION_RETURN,
    CONSUMPTION_WASTE,
    CONSUMPTION_CORRECTION,
)

STEP_PENDING = "pending"
STEP_READY = "ready"
STEP_IN_PROGRESS = "in_progress"
STEP_ON_HOLD = "on_hold"
STEP_COMPLETED = "completed"
STEP_SKIPPED = "skipped"
STEP_CANCELLED = "cancelled"
STEP_STATUSES = (
    STEP_PENDING,
    STEP_READY,
    STEP_IN_PROGRESS,
    STEP_ON_HOLD,
    STEP_COMPLETED,
    STEP_SKIPPED,
    STEP_CANCELLED,
)

YIELD_PRE_BAKE_MASS = "pre_bake_mass"
YIELD_POST_BAKE_MASS = "post_bake_mass"
YIELD_GOOD_UNITS = "good_units"
YIELD_REJECTED_UNITS = "rejected_units"
YIELD_LEFTOVER = "leftover"
YIELD_SCRAP = "scrap"
YIELD_OTHER = "other"
YIELD_TYPES = (
    YIELD_PRE_BAKE_MASS,
    YIELD_POST_BAKE_MASS,
    YIELD_GOOD_UNITS,
    YIELD_REJECTED_UNITS,
    YIELD_LEFTOVER,
    YIELD_SCRAP,
    YIELD_OTHER,
)

OCCURRENCE_MATERIAL = "material"
OCCURRENCE_SUBSTITUTION = "substitution"
OCCURRENCE_EQUIPMENT = "equipment"
OCCURRENCE_QUALITY = "quality"
OCCURRENCE_PROCESS = "process"
OCCURRENCE_SAFETY = "safety"
OCCURRENCE_ALLERGEN = "allergen"
OCCURRENCE_TIME = "time"
OCCURRENCE_TEMPERATURE = "temperature"
OCCURRENCE_OTHER = "other"
OCCURRENCE_CATEGORIES = (
    OCCURRENCE_MATERIAL,
    OCCURRENCE_SUBSTITUTION,
    OCCURRENCE_EQUIPMENT,
    OCCURRENCE_QUALITY,
    OCCURRENCE_PROCESS,
    OCCURRENCE_SAFETY,
    OCCURRENCE_ALLERGEN,
    OCCURRENCE_TIME,
    OCCURRENCE_TEMPERATURE,
    OCCURRENCE_OTHER,
)

SEVERITY_LOW = "low"
SEVERITY_MEDIUM = "medium"
SEVERITY_HIGH = "high"
SEVERITY_CRITICAL = "critical"
SEVERITIES = (SEVERITY_LOW, SEVERITY_MEDIUM, SEVERITY_HIGH, SEVERITY_CRITICAL)

OCCURRENCE_OPEN = "open"
OCCURRENCE_RESOLVED = "resolved"
OCCURRENCE_STATUSES = (OCCURRENCE_OPEN, OCCURRENCE_RESOLVED)

SHEET_OPERATIONAL = "operational"
SHEET_CONTINGENCY = "contingency"
SHEET_PURPOSES = (SHEET_OPERATIONAL, SHEET_CONTINGENCY)

POLICY_ALGORITHM = "execution_policy"
POLICY_ALGORITHM_VERSION = "1"
YIELD_ALGORITHM = "deterministic_yield"
YIELD_ALGORITHM_VERSION = "1"
SHEET_TEMPLATE_VERSION = "2"

COMMAND_SET_EXECUTION_POLICY = "set_execution_policy"
COMMAND_ADOPT_EXECUTION_POLICY = "adopt_execution_policy"
COMMAND_OPEN_WEIGHING_SESSION = "open_weighing_session"
COMMAND_COMPLETE_WEIGHING_SESSION = "complete_weighing_session"
COMMAND_CANCEL_WEIGHING_SESSION = "cancel_weighing_session"
COMMAND_RECORD_WEIGHING = "record_weighing"
COMMAND_REVERSE_WEIGHING = "reverse_weighing"
COMMAND_CORRECT_WEIGHING = "correct_weighing"
COMMAND_VERIFY_WEIGHING = "verify_weighing"
COMMAND_RECORD_CONSUMPTION = "record_consumption"
COMMAND_MARK_STEP_READY = "mark_step_ready"
COMMAND_START_STEP = "start_step"
COMMAND_HOLD_STEP = "hold_step"
COMMAND_RESUME_STEP = "resume_step"
COMMAND_COMPLETE_STEP = "complete_step"
COMMAND_SKIP_STEP = "skip_step"
COMMAND_CANCEL_STEP = "cancel_step"
COMMAND_MARK_READY = "mark_order_ready"
COMMAND_RESUME_ORDER = "resume_order"
COMMAND_RECORD_YIELD = "record_yield"
COMMAND_REVERSE_YIELD = "reverse_yield"
COMMAND_RECORD_OCCURRENCE = "record_occurrence"
COMMAND_RESOLVE_OCCURRENCE = "resolve_occurrence"
COMMAND_OVERRIDE_DEPENDENCY = "override_dependency"
COMMAND_COMPLETE_BATCH = "complete_batch"
COMMAND_COMPLETE_ORDER = "complete_order"
COMMAND_SHORT_CLOSE_ORDER = "short_close_order"
COMMAND_ISSUE_SHEET = "issue_sheet"

EVENT_POLICY_SET = "execution.policy_set"
EVENT_POLICY_ADOPTED = "execution.policy_adopted"
EVENT_WEIGHING_SESSION_OPENED = "weighing.session_opened"
EVENT_WEIGHING_SESSION_COMPLETED = "weighing.session_completed"
EVENT_WEIGHING_SESSION_CANCELLED = "weighing.session_cancelled"
EVENT_WEIGHING_RECORDED = "weighing.recorded"
EVENT_WEIGHING_VERIFIED = "weighing.verified"
EVENT_CONSUMPTION_RECORDED = "consumption.recorded"
EVENT_STEP_TRANSITIONED = "step.transitioned"
EVENT_ORDER_IN_WEIGHING = "order.in_weighing"
EVENT_ORDER_READY = "order.ready"
EVENT_ORDER_STARTED = "order.started"
EVENT_ORDER_RESUMED = "order.resumed"
EVENT_ORDER_COMPLETED = "order.completed"
EVENT_ORDER_SHORT_CLOSED = "order.short_closed"
EVENT_BATCH_STATUS_CHANGED = "batch.status_changed"
EVENT_YIELD_RECORDED = "yield.recorded"
EVENT_OCCURRENCE_RECORDED = "occurrence.recorded"
EVENT_OCCURRENCE_RESOLVED = "occurrence.resolved"
EVENT_DEPENDENCY_OVERRIDDEN = "dependency.overridden"
EVENT_SHEET_ISSUED = "sheet.issued"

EVENT_PAYLOADS: dict[str, frozenset[str]] = {
    EVENT_POLICY_SET: frozenset({"policy_id", "weighing_policy", "verification_policy"}),
    EVENT_POLICY_ADOPTED: frozenset({"policy_id", "reason", "policy_hash"}),
    EVENT_WEIGHING_SESSION_OPENED: frozenset({"session_id", "batch_id"}),
    EVENT_WEIGHING_SESSION_COMPLETED: frozenset({"session_id"}),
    EVENT_WEIGHING_SESSION_CANCELLED: frozenset({"session_id", "reason"}),
    EVENT_WEIGHING_RECORDED: frozenset({"entry_id", "session_id", "entry_type"}),
    EVENT_WEIGHING_VERIFIED: frozenset({"verification_id", "entry_id", "decision"}),
    EVENT_CONSUMPTION_RECORDED: frozenset({"consumption_id", "consumption_type"}),
    EVENT_STEP_TRANSITIONED: frozenset({"execution_id", "from_status", "to_status"}),
    EVENT_ORDER_IN_WEIGHING: frozenset({"public_code"}),
    EVENT_ORDER_READY: frozenset({"public_code"}),
    EVENT_ORDER_STARTED: frozenset({"public_code"}),
    EVENT_ORDER_RESUMED: frozenset({"public_code"}),
    EVENT_ORDER_COMPLETED: frozenset({"public_code", "result_digest"}),
    EVENT_ORDER_SHORT_CLOSED: frozenset({"public_code", "reason", "result_digest"}),
    EVENT_BATCH_STATUS_CHANGED: frozenset({"batch_id", "from_status", "to_status"}),
    EVENT_YIELD_RECORDED: frozenset({"measurement_id", "measurement_type"}),
    EVENT_OCCURRENCE_RECORDED: frozenset({"occurrence_id", "category", "blocking"}),
    EVENT_OCCURRENCE_RESOLVED: frozenset({"occurrence_id"}),
    EVENT_DEPENDENCY_OVERRIDDEN: frozenset({"dependency_id", "predecessor_status", "reason"}),
    EVENT_SHEET_ISSUED: frozenset({"issue_id", "issue_number", "payload_sha256"}),
}

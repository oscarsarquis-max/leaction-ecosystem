"""Limites e versões do domínio analítico."""

from decimal import Decimal

REPORT_VERSION = "2"
QUERY_VERSION = "2"
METRICS_VERSION = "2"
CURRENCY = "BRL"
DEFAULT_TIMEZONE = "America/Sao_Paulo"
DEFAULT_PERIOD_DAYS = 7
MAX_PERIOD_DAYS = 90
DETAIL_PAGE_SIZE = 50
DETAIL_PAGE_MAX = 200
EXPORT_ROW_LIMIT = 2000
SNAPSHOT_BYTES_MAX = 1_000_000
QUERY_BUDGET = 16
CACHE_TTL_SECONDS = 30
ZERO = Decimal("0")
ONE = Decimal("1")
HUNDRED = Decimal("100")
PERCENT_QUANTUM = Decimal("0.0001")

PLANNED_STATUSES = ("draft", "scheduled")
RELEASED_STATUSES = ("released",)
IN_EXECUTION_STATUSES = ("in_weighing", "ready", "in_progress", "on_hold")
COMPLETED_STATUSES = ("completed",)
SHORT_CLOSED_STATUSES = ("short_closed",)
CANCELLED_STATUSES = ("cancelled",)

IMPOSSIBLE_METRICS = (
    "revenue_realized",
    "net_profit",
    "sales_volume",
    "inventory_turnover",
    "stockout",
    "payroll_cost",
    "tax_assessment",
)

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from uuid import UUID, uuid5

NAMESPACE = UUID("8f2c6d1a-0250-4b11-9c3e-a11e00000025")


def seed_uuid(*parts: str) -> UUID:
    return uuid5(NAMESPACE, ":".join(parts))


def as_date(value: str | date) -> date:
    if isinstance(value, date):
        return value
    return date.fromisoformat(value)


def at(anchor: date, days: int = 0, hours: int = 12) -> datetime:
    moment = datetime.combine(anchor, datetime.min.time(), tzinfo=timezone.utc)
    return moment + timedelta(days=days, hours=hours)

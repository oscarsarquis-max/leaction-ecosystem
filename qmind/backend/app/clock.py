"""The one place the application asks what time it is.

Domain rules that compare against "now" — a reading cannot be taken in the
future, a cadence cannot already be late the moment it is created — are only
testable if the clock can be replaced. Calling `datetime.now()` inline makes
those rules either untestable or testable only by sleeping.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import datetime, timezone

_override: Callable[[], datetime] | None = None


def now() -> datetime:
    """Current instant, always timezone-aware and always UTC."""
    if _override is not None:
        moment = _override()
        if moment.tzinfo is None:
            return moment.replace(tzinfo=timezone.utc)
        return moment.astimezone(timezone.utc)
    return datetime.now(timezone.utc)


@contextmanager
def frozen(at: datetime) -> Iterator[datetime]:
    """Pin the clock for the duration of the block (tests only)."""
    fixed = at if at.tzinfo else at.replace(tzinfo=timezone.utc)
    yield from _using(lambda: fixed)


@contextmanager
def shifted(*, seconds: float) -> Iterator[None]:
    """Run the block as if `seconds` had already elapsed (tests only)."""
    from datetime import timedelta

    delta = timedelta(seconds=seconds)
    yield from _using(lambda: datetime.now(timezone.utc) + delta)


def _using(fn: Callable[[], datetime]):
    global _override
    previous = _override
    _override = fn
    try:
        yield fn()
    finally:
        _override = previous

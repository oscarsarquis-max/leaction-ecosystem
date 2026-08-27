from datetime import date, datetime
from decimal import Decimal
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest
from app.config import Settings, get_settings
from app.modules.inventory_procurement.eligibility import (
    is_lot_production_eligible,
    project_balance_quantities,
)
from app.modules.inventory_procurement.models import InventoryLot
from app.modules.inventory_procurement.operational_date import (
    OPERATIONAL_TIMEZONE,
    OperationalDateError,
    inventory_as_of_payload,
    inventory_operational_date,
)
from app.seed import DEFAULT_ANCHOR


def _lot(**kwargs) -> InventoryLot:
    base = dict(
        organization_id=uuid4(),
        inventory_item_id=uuid4(),
        inventory_location_id=uuid4(),
        received_quantity=Decimal("100"),
        unit_code="g",
    )
    base.update(kwargs)
    return InventoryLot(**base)


def test_eligibility_status_and_calendar() -> None:
    as_of = date(2026, 8, 24)
    available = _lot(
        id=uuid4(),
        internal_lot_code="LOT-OK",
        status="available",
        expires_on=date(2026, 8, 24),
    )
    blocked = _lot(
        id=uuid4(),
        internal_lot_code="LOT-BLK",
        status="blocked",
        expires_on=date(2026, 9, 13),
    )
    quarantine = _lot(
        id=uuid4(),
        internal_lot_code="LOT-Q",
        status="quarantined",
        expires_on=date(2026, 9, 8),
    )
    expired = _lot(
        id=uuid4(),
        internal_lot_code="LOT-EXP",
        status="available",
        expires_on=date(2026, 8, 23),
    )
    future = _lot(
        id=uuid4(),
        internal_lot_code="LOT-000002",
        status="available",
        expires_on=date(2026, 8, 27),
    )
    assert is_lot_production_eligible(available, as_of=as_of) == (True, None)
    assert is_lot_production_eligible(blocked, as_of=as_of)[0] is False
    assert is_lot_production_eligible(quarantine, as_of=as_of)[0] is False
    assert is_lot_production_eligible(expired, as_of=as_of) == (False, "expired_calendar")
    assert is_lot_production_eligible(future, as_of=as_of) == (True, None)
    # Relógio civil posterior não altera o julgamento quando as_of é a âncora.
    assert is_lot_production_eligible(future, as_of=date(2026, 8, 28)) == (False, "expired_calendar")


def test_project_quantities_impeded_subset_of_unreserved() -> None:
    ok = project_balance_quantities(Decimal("3800"), Decimal("0"), eligible=True)
    assert ok["unreserved_quantity"] == Decimal("3800")
    assert ok["eligible_quantity"] == Decimal("3800")
    assert ok["impeded_quantity"] == Decimal("0")

    blocked = project_balance_quantities(Decimal("1500"), Decimal("0"), eligible=False)
    assert blocked["unreserved_quantity"] == Decimal("1500")
    assert blocked["eligible_quantity"] == Decimal("0")
    assert blocked["impeded_quantity"] == Decimal("1500")

    reserved = project_balance_quantities(Decimal("20000"), Decimal("20000"), eligible=True)
    assert reserved["unreserved_quantity"] == Decimal("0")
    assert reserved["eligible_quantity"] == Decimal("0")
    assert reserved["impeded_quantity"] == Decimal("0")


def test_demo_operational_date_uses_anchor_not_wall_clock() -> None:
    get_settings.cache_clear()
    demo = Settings(env="demo", demo_anchor_date="")
    assert inventory_operational_date(settings=demo) == date.fromisoformat(DEFAULT_ANCHOR)
    later = datetime(2026, 8, 28, 18, 0, tzinfo=ZoneInfo(OPERATIONAL_TIMEZONE))
    assert inventory_operational_date(settings=demo, now=later) == date(2026, 8, 24)
    custom = Settings(env="demo", demo_anchor_date="2026-08-24")
    payload = inventory_as_of_payload(settings=custom, now=later)
    assert payload == {"as_of": "2026-08-24", "timezone": OPERATIONAL_TIMEZONE}


def test_demo_invalid_anchor_fails_clearly() -> None:
    bad = Settings(env="demo", demo_anchor_date="24/08/2026")
    with pytest.raises(OperationalDateError):
        inventory_operational_date(settings=bad)


def test_production_ignores_demo_anchor_and_uses_sao_paulo() -> None:
    get_settings.cache_clear()
    prod = Settings(env="production", demo_anchor_date="2026-08-24")
    moment = datetime(2026, 8, 28, 1, 30, tzinfo=ZoneInfo("UTC"))
    # 01:30 UTC = 22:30 do dia anterior em America/Sao_Paulo
    assert inventory_operational_date(settings=prod, now=moment) == date(2026, 8, 27)
    afternoon = datetime(2026, 8, 28, 15, 0, tzinfo=ZoneInfo(OPERATIONAL_TIMEZONE))
    assert inventory_operational_date(settings=prod, now=afternoon) == date(2026, 8, 28)


def test_local_env_does_not_use_demo_anchor() -> None:
    local = Settings(env="local", demo_anchor_date="2026-08-24")
    moment = datetime(2026, 9, 1, 12, 0, tzinfo=ZoneInfo(OPERATIONAL_TIMEZONE))
    assert inventory_operational_date(settings=local, now=moment) == date(2026, 9, 1)

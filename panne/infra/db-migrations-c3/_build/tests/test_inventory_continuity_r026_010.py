"""R026-010 — serialização enriquecida sem N+1 (reservas / movimentos / picks)."""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from app.modules.inventory_http import serialize
from app.modules.inventory_procurement.models import (
    InventoryItem,
    InventoryLocation,
    InventoryLot,
    InventoryMovement,
    InventoryPick,
    InventoryPickLine,
    InventoryReservation,
    InventoryReservationAllocation,
)
from app.modules.production_planning.models import ProductionOrder


def test_reservation_out_includes_shortage_and_unit_without_session() -> None:
    row = InventoryReservation(
        id=uuid4(),
        organization_id=uuid4(),
        production_order_id=uuid4(),
        inventory_item_id=uuid4(),
        required_quantity=Decimal("90000"),
        reserved_quantity=Decimal("21500"),
        shortage_quantity=Decimal("68500"),
        unit_code="g",
        status="partial",
        adopted=True,
        inventory_policy_version_id=uuid4(),
        created_by_user_id=uuid4(),
        created_at=datetime(2026, 8, 24, 12, 0, tzinfo=UTC),
    )
    payload = serialize.reservation_out(row, allocations=[])
    assert payload["shortage_quantity"] == "68500"
    assert payload["unit_code"] == "g"
    assert payload["adopted"] is True
    assert payload["allocations"] == []


def test_movement_out_exposes_sign_unit_and_nature() -> None:
    row = InventoryMovement(
        id=uuid4(),
        organization_id=uuid4(),
        inventory_item_id=uuid4(),
        inventory_lot_id=uuid4(),
        movement_type="supplier_return",
        quantity=Decimal("200"),
        unit_code="g",
        canonical_quantity=Decimal("200"),
        conversion_factor=Decimal("1"),
        sign=-1,
        nature="physical_out",
        origin_type="procurement_return",
        inventory_policy_version_id=uuid4(),
        actor_user_id=uuid4(),
        effective_at=datetime(2026, 8, 24, 14, 0, tzinfo=UTC),
        content_hash="abc",
        created_at=datetime(2026, 8, 24, 14, 0, tzinfo=UTC),
    )
    payload = serialize.movement_out(row)
    assert payload["sign"] == -1
    assert payload["unit_code"] == "g"
    assert payload["nature"] == "physical_out"
    assert payload["movement_type"] == "supplier_return"


def test_pick_out_includes_line_metadata_flags() -> None:
    pick = InventoryPick(
        id=uuid4(),
        organization_id=uuid4(),
        public_code="PICK-000001",
        production_order_id=uuid4(),
        status="confirmed",
        inventory_policy_version_id=uuid4(),
        created_by_user_id=uuid4(),
        created_at=datetime(2026, 8, 24, 15, 0, tzinfo=UTC),
    )
    line = InventoryPickLine(
        id=uuid4(),
        organization_id=pick.organization_id,
        inventory_pick_id=pick.id,
        inventory_item_id=uuid4(),
        inventory_lot_id=uuid4(),
        inventory_location_id=uuid4(),
        quantity=Decimal("500"),
        suggested=True,
        substituted=False,
        reason=None,
        created_at=datetime(2026, 8, 24, 15, 0, tzinfo=UTC),
    )
    payload = serialize.pick_out(pick, [line])
    assert payload["public_code"] == "PICK-000001"
    assert payload["line_count"] == 1
    assert payload["lines"][0]["suggested"] is True
    assert payload["lines"][0]["lot_id"] == str(line.inventory_lot_id)

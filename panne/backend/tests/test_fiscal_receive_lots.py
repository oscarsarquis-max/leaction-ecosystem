"""Lote e validade na confirmação de estoque — nota manual e XML."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from app.modules.fiscal_inbound import commands
from app.modules.fiscal_inbound.models import FiscalPhysicalLine
from app.modules.inventory_procurement.eligibility import is_lot_production_eligible
from app.modules.inventory_procurement.models import InventoryLot, InventoryMovement, ProcurementReceipt
from app.modules.inventory_procurement.operational_date import inventory_operational_date
from app.modules.production_planning.errors import ValidationError
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from tests.test_fiscal_draft_items import _header, _line
from tests.test_fiscal_inbound import _review_document, _stock_ready, _world

FIXTURE_XML = Path(__file__).parent / "fixtures" / "fiscal" / "demo_nfe.xml"


def _ensure_head(engine) -> None:
    root = Path(__file__).resolve().parents[1]
    config = Config(str(root / "alembic.ini"))
    config.set_main_option("script_location", str(root / "alembic"))
    with engine.begin() as conn:
        config.attributes["connection"] = conn
        command.upgrade(config, "head")


@pytest.fixture(scope="module", autouse=True)
def _schema(engine) -> None:
    _ensure_head(engine)


def _prepare_note(ctx, number: str, description="Farinha"):
    session, principal = ctx["session"], ctx["principal"]
    document = commands.create_manual(
        session, principal, _header(ctx["place"].id, number), idempotency_key=uuid4()
    )
    document = commands.replace_items(
        session,
        principal,
        document.id,
        {
            "expected_row_version": document.row_version,
            "items": [{**_line(description, "10", "KG", "5"), "ingredient_id": str(ctx["ingredient"].id)}],
        },
        idempotency_key=uuid4(),
    )
    location, stock = _stock_ready(ctx)
    document = _review_document(session, principal, document)
    item = commands._items(session, ctx["organization"].id, document.id)[0]
    return document, item, location, stock


def _receive(ctx, document, item, location, *, lots=None, extra=None):
    line = {
        "item_id": str(item.id),
        "ingredient_id": str(ctx["ingredient"].id),
        "stock_unit": "g",
        "conversion_factor": "1000",
        "received_quantity": "10000",
        "result": "ok",
    }
    if lots is not None:
        line["lots"] = lots
    if extra:
        line.update(extra)
    return commands.receive_receipt(
        ctx["session"],
        ctx["principal"],
        document.id,
        {"inventory_location_id": str(location.id), "lines": [line]},
        idempotency_key=uuid4(),
    )


def test_saving_note_does_not_create_stock_or_lots(db_session: Session):
    ctx = _world(db_session, f"lotn{uuid4().hex[:6]}")
    session, principal = ctx["session"], ctx["principal"]
    document = commands.create_manual(
        session, principal, _header(ctx["place"].id, "9201"), idempotency_key=uuid4()
    )
    commands.replace_items(
        session,
        principal,
        document.id,
        {
            "expected_row_version": document.row_version,
            "items": [{**_line(), "ingredient_id": str(ctx["ingredient"].id)}],
        },
        idempotency_key=uuid4(),
    )
    _review_document(session, principal, document)
    assert (
        session.scalar(
            select(func.count()).select_from(InventoryLot).where(InventoryLot.organization_id == ctx["organization"].id)
        )
        == 0
    )
    assert (
        session.scalar(
            select(func.count())
            .select_from(InventoryMovement)
            .where(InventoryMovement.organization_id == ctx["organization"].id)
        )
        == 0
    )


def test_manual_split_lots_keep_note_and_block_expired(db_session: Session):
    ctx = _world(db_session, f"lots{uuid4().hex[:6]}")
    session = ctx["session"]
    document, item, location, _stock = _prepare_note(ctx, "9202")
    issued = item.quantity
    assert issued == Decimal("10")
    past = (inventory_operational_date() - timedelta(days=3)).isoformat()
    future = (inventory_operational_date() + timedelta(days=40)).isoformat()
    _receive(
        ctx,
        document,
        item,
        location,
        lots=[
            {"quantity": "4000", "supplier_lot_code": "L-A", "expires_on": past},
            {"quantity": "6000", "supplier_lot_code": "L-B", "expires_on": future},
        ],
    )
    lots = list(
        session.scalars(
            select(InventoryLot).where(InventoryLot.organization_id == ctx["organization"].id).order_by(InventoryLot.created_at)
        )
    )
    assert len(lots) == 2
    assert {lot.supplier_lot_code for lot in lots} == {"L-A", "L-B"}
    expired = next(lot for lot in lots if lot.supplier_lot_code == "L-A")
    fresh = next(lot for lot in lots if lot.supplier_lot_code == "L-B")
    assert expired.expires_on == date.fromisoformat(past)
    assert expired.status == "expired"
    assert is_lot_production_eligible(expired)[0] is False
    assert is_lot_production_eligible(fresh)[0] is True
    physical = list(
        session.scalars(select(FiscalPhysicalLine).where(FiscalPhysicalLine.fiscal_inbound_item_id == item.id))
    )
    assert len(physical) == 2
    assert commands._items(session, ctx["organization"].id, document.id)[0].quantity == Decimal("10")


def test_uninformed_expiry_is_explicit_and_required_policy_blocks(db_session: Session):
    ctx = _world(db_session, f"lotu{uuid4().hex[:6]}")
    session = ctx["session"]
    document, item, location, stock = _prepare_note(ctx, "9203")
    with pytest.raises(ValidationError, match="validade_pendente"):
        _receive(
            ctx,
            document,
            item,
            location,
            lots=[{"quantity": "10000", "supplier_lot_code": "L-X"}],
        )
    assert session.scalar(select(func.count()).select_from(InventoryLot).where(InventoryLot.organization_id == ctx["organization"].id)) == 0
    _receive(
        ctx,
        document,
        item,
        location,
        lots=[{"quantity": "10000", "supplier_lot_code": "L-X", "expiry_uninformed": True}],
    )
    lot = session.scalar(select(InventoryLot).where(InventoryLot.organization_id == ctx["organization"].id))
    assert lot is not None
    assert lot.expires_on is None
    phys = session.scalar(select(FiscalPhysicalLine).where(FiscalPhysicalLine.fiscal_inbound_item_id == item.id))
    assert phys.expiry_uninformed is True

    ctx_req = _world(db_session, f"lotr{uuid4().hex[:6]}")
    session_r, principal_r = ctx_req["session"], ctx_req["principal"]
    from app.modules.inventory_procurement.services import create_item, create_location, create_policy, publish_policy

    document_r = commands.create_manual(
        session_r, principal_r, _header(ctx_req["place"].id, "9204"), idempotency_key=uuid4()
    )
    document_r = commands.replace_items(
        session_r,
        principal_r,
        document_r.id,
        {
            "expected_row_version": document_r.row_version,
            "items": [{**_line("Farinha", "10", "KG", "5"), "ingredient_id": str(ctx_req["ingredient"].id)}],
        },
        idempotency_key=uuid4(),
    )
    policy = create_policy(
        session_r,
        principal_r,
        {
            "code": f"POL-{uuid4().hex[:6]}",
            "effective_from": "2026-08-01T00:00:00+00:00",
            "justification": "validade obrigatória",
            "expiry_required": True,
        },
        idempotency_key=uuid4(),
    )
    publish_policy(session_r, principal_r, policy.id, idempotency_key=uuid4(), expected_version=policy.row_version)
    location_r = create_location(
        session_r,
        principal_r,
        {
            "establishment_id": ctx_req["place"].id,
            "code": f"LOC-{uuid4().hex[:6]}",
            "display_name": "Almoxarifado",
            "kind": "warehouse",
        },
        idempotency_key=uuid4(),
    )
    create_item(
        session_r,
        principal_r,
        {
            "ingredient_id": ctx_req["ingredient"].id,
            "unit_code": "g",
            "lot_control": "required",
            "expiry_control": True,
        },
        idempotency_key=uuid4(),
    )
    document_r = _review_document(session_r, principal_r, document_r)
    item_r = commands._items(session_r, ctx_req["organization"].id, document_r.id)[0]
    with pytest.raises(ValidationError, match="validade_obrigatoria"):
        _receive(
            ctx_req,
            document_r,
            item_r,
            location_r,
            lots=[{"quantity": "10000", "expiry_uninformed": True}],
        )


def test_lot_sum_must_match_and_replay_does_not_duplicate(db_session: Session):
    ctx = _world(db_session, f"loti{uuid4().hex[:6]}")
    session = ctx["session"]
    document, item, location, _stock = _prepare_note(ctx, "9205")
    with pytest.raises(ValidationError, match="lotes_quantidade_divergente"):
        _receive(
            ctx,
            document,
            item,
            location,
            lots=[
                {"quantity": "1000", "expires_on": "2027-01-01"},
                {"quantity": "1000", "expires_on": "2027-02-01"},
            ],
        )
    body = {
        "inventory_location_id": str(location.id),
        "lines": [
            {
                "item_id": str(item.id),
                "ingredient_id": str(ctx["ingredient"].id),
                "stock_unit": "g",
                "conversion_factor": "1000",
                "received_quantity": "10000",
                "result": "ok",
                "lots": [{"quantity": "10000", "supplier_lot_code": "UNICO", "expires_on": "2027-04-01"}],
            }
        ],
    }
    key = uuid4()
    commands.receive_receipt(session, ctx["principal"], document.id, body, idempotency_key=key)
    commands.receive_receipt(session, ctx["principal"], document.id, body, idempotency_key=key)
    assert (
        session.scalar(
            select(func.count()).select_from(InventoryLot).where(InventoryLot.organization_id == ctx["organization"].id)
        )
        == 1
    )
    assert (
        session.scalar(
            select(func.count()).select_from(ProcurementReceipt).where(
                ProcurementReceipt.organization_id == ctx["organization"].id
            )
        )
        == 1
    )


def test_xml_receive_accepts_lots_without_inferring_expiry(db_session: Session):
    ctx = _world(db_session, f"lotx{uuid4().hex[:6]}")
    session, principal = ctx["session"], ctx["principal"]
    document = commands.import_xml(
        session,
        principal,
        {
            "establishment_id": str(ctx["place"].id),
            "content": FIXTURE_XML.read_text(encoding="utf-8"),
            "synthetic": True,
        },
        idempotency_key=uuid4(),
    )
    location, _stock = _stock_ready(ctx)
    document = _review_document(session, principal, document)
    items = commands._items(session, ctx["organization"].id, document.id)
    lines = []
    for index, item in enumerate(items):
        received = format(item.converted_quantity or item.quantity, "f")
        line = {
            "item_id": str(item.id),
            "create_ingredient": True,
            "new_ingredient_name": item.description or f"Insumo {index}",
            "stock_unit": item.converted_unit_code or item.unit_code or "g",
            "conversion_factor": "1",
            "received_quantity": received,
            "result": "ok",
            "lots": [{"quantity": received, "expiry_uninformed": True, "supplier_lot_code": f"XML-{index}"}],
        }
        lines.append(line)
    commands.receive_receipt(
        session,
        principal,
        document.id,
        {"inventory_location_id": str(location.id), "lines": lines},
        idempotency_key=uuid4(),
    )
    lots = list(session.scalars(select(InventoryLot).where(InventoryLot.organization_id == ctx["organization"].id)))
    assert len(lots) == len(items)
    assert all(lot.expires_on is None for lot in lots)
    assert all(lot.supplier_lot_code.startswith("XML-") for lot in lots)

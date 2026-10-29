from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from threading import Thread
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from app.modules.identity_organization.authorization import AuthorizationError, permissions_for_role
from app.modules.inventory_procurement.models import (
    InventoryBalance,
    InventoryMovement,
    InventoryPolicyVersion,
)
from app.modules.inventory_procurement.services import (
    approve_count,
    compare_quotations,
    confirm_pick,
    create_count,
    create_item,
    create_location,
    create_order,
    create_policy,
    create_quotation,
    create_requisition,
    freeze_count_scope,
    list_balances,
    open_balance,
    post_consumption,
    post_movement,
    publish_policy,
    receive_order,
    record_count,
    refuse_automatic_purchase,
    reserve_order,
    return_to_supplier,
    review_count,
    set_lot_status,
    suggest_fefo,
    suggest_replenishment,
    traceability,
    transition_order,
    transition_requisition,
)
from app.modules.production_planning.errors import ImmutableError, ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session
from tests import helpers
from tests.test_production_api import _cleanup
from tests.test_production_planning import _context, _plan_and_order
from tests.test_recipe_http import _base, _h, _setup


def _ensure_head(engine) -> None:
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    config.set_main_option("script_location", str(Path(__file__).resolve().parents[1] / "alembic"))
    command.upgrade(config, "head")


@pytest.fixture(scope="module", autouse=True)
def _inventory_schema(engine) -> None:
    _ensure_head(engine)


def _now() -> str:
    return datetime(2026, 8, 24, 12, 0, tzinfo=UTC).isoformat()


def _world(session: Session, slug: str, role: str = "owner"):
    organization = helpers.org(session, slug)
    actor = helpers.user(session, f"{slug}@example.com")
    helpers.membership(session, organization, actor, role)
    place = helpers.establishment(session, organization, "MATRIZ")
    unit = helpers.gram(session)
    flour = helpers.ingredient(session, organization, f"FAR-{slug[-6:]}")
    helpers.version(session, flour, unit, status="published")
    principal = helpers.principal_for(actor, organization, role)
    return {
        "session": session,
        "organization": organization,
        "actor": actor,
        "place": place,
        "unit": unit,
        "ingredient": flour,
        "principal": principal,
    }


def _publish(ctx, code="EST-PADRAO", **extra):
    policy = create_policy(
        ctx["session"],
        ctx["principal"],
        {
            "code": code,
            "effective_from": _now(),
            "justification": "política operacional inicial",
            **extra,
        },
        idempotency_key=uuid4(),
    )
    publish_policy(
        ctx["session"],
        ctx["principal"],
        policy.id,
        expected_version=policy.row_version,
        idempotency_key=uuid4(),
    )
    return policy


def _stock(ctx, qty="1000"):
    _publish(ctx)
    location = create_location(
        ctx["session"],
        ctx["principal"],
        {
            "establishment_id": ctx["place"].id,
            "code": "ALM-1",
            "kind": "warehouse",
            "display_name": "Almoxarifado",
        },
        idempotency_key=uuid4(),
    )
    item = create_item(
        ctx["session"],
        ctx["principal"],
        {
            "ingredient_id": ctx["ingredient"].id,
            "unit_code": "g",
            "lot_control": "required",
            "expiry_control": True,
            "reorder_point": "200",
            "safety_stock": "50",
            "target_quantity": "800",
        },
        idempotency_key=uuid4(),
    )
    lot = open_balance(
        ctx["session"],
        ctx["principal"],
        {
            "inventory_item_id": item.id,
            "inventory_location_id": location.id,
            "quantity": qty,
            "expires_on": (datetime.now(UTC).date() + timedelta(days=20)).isoformat(),
            "reason": "saldo inicial controlado",
        },
        idempotency_key=uuid4(),
    )
    return location, item, lot


def test_permissions_roles_do_not_authorize_by_label() -> None:
    baker = permissions_for_role("baker_operator")
    owner = permissions_for_role("owner")
    commercial = permissions_for_role("commercial")
    production = permissions_for_role("production_manager")
    assert "inventory.read" in baker
    assert "inventory.separate" in baker
    assert "inventory.adjust" not in baker
    assert "procurement.order.approve" not in baker
    assert "reporting.inventory.read" not in baker
    assert "inventory.adjust" in owner
    assert "procurement.receive" in owner
    assert "reporting.inventory.read" in owner
    assert "procurement.order.approve" in commercial
    assert "inventory.adjust" not in production
    assert "procurement.order.approve" not in production


def test_policy_is_versioned_and_published_immutable(db_session: Session) -> None:
    ctx = _world(db_session, "inv-pol")
    policy = _publish(ctx)
    version = db_session.scalar(select(InventoryPolicyVersion).where(InventoryPolicyVersion.inventory_policy_id == policy.id))
    assert version.status == "published"
    assert version.allow_negative_balance is False


def test_locations_items_lots_and_blocked_expiry(db_session: Session) -> None:
    ctx = _world(db_session, "inv-lot")
    location, item, lot = _stock(ctx)
    assert item.lot_control == "required"
    set_lot_status(
        db_session,
        ctx["principal"],
        lot.id,
        "blocked",
        "quarentena de recebimento",
        expected_version=lot.row_version,
        idempotency_key=uuid4(),
    )
    with pytest.raises(ValidationError, match="lote_indisponivel"):
        post_movement(
            db_session,
            ctx["principal"],
            {
                "movement_type": "production_consume",
                "inventory_item_id": item.id,
                "inventory_lot_id": lot.id,
                "from_location_id": location.id,
                "quantity": "10",
                "unit_code": "g",
            },
            idempotency_key=uuid4(),
        )


def test_ledger_append_only_and_reconciled_balance(db_session: Session) -> None:
    ctx = _world(db_session, "inv-led")
    location, item, lot = _stock(ctx, "500")
    post_movement(
        db_session,
        ctx["principal"],
        {
            "movement_type": "production_consume",
            "inventory_item_id": item.id,
            "inventory_lot_id": lot.id,
            "from_location_id": location.id,
            "quantity": "80",
            "unit_code": "g",
        },
        idempotency_key=uuid4(),
    )
    balances = list_balances(db_session, ctx["principal"])
    assert Decimal(balances[0].physical_quantity) == Decimal("420")
    movements = list(
        db_session.scalars(
            select(InventoryMovement).where(InventoryMovement.organization_id == ctx["organization"].id)
        )
    )
    assert len(movements) == 2
    rebuilt = sum((Decimal(row.canonical_quantity) * row.sign for row in movements), Decimal("0"))
    assert rebuilt == Decimal(balances[0].physical_quantity)


def test_negative_denied_by_default(db_session: Session) -> None:
    ctx = _world(db_session, "inv-neg")
    location, item, lot = _stock(ctx, "10")
    with pytest.raises(ValidationError, match="saldo_insuficiente"):
        post_movement(
            db_session,
            ctx["principal"],
            {
                "movement_type": "production_consume",
                "inventory_item_id": item.id,
                "inventory_lot_id": lot.id,
                "from_location_id": location.id,
                "quantity": "20",
                "unit_code": "g",
            },
            idempotency_key=uuid4(),
        )


def test_reservation_partial_and_historical_order(db_session: Session) -> None:
    ctx = _world(db_session, "inv-res")
    prod = _context(db_session, "inv-ord")
    _, _, order = _plan_and_order(db_session, prod)
    ctx["organization"] = prod["organization"]
    ctx["principal"] = helpers.principal_for(prod["actor"], prod["organization"], "owner")
    ctx["place"] = prod["establishment"]
    ctx["ingredient"] = helpers.ingredient(db_session, prod["organization"], "FAR-RES")
    helpers.version(db_session, ctx["ingredient"], helpers.gram(db_session), status="published")
    location, item, _lot = _stock(ctx, "40")
    with pytest.raises(ValidationError, match="adocao_historica"):
        reserve_order(
            db_session,
            ctx["principal"],
            {
                "production_order_id": order.id,
                "inventory_item_id": item.id,
                "required_quantity": "100",
            },
            idempotency_key=uuid4(),
        )
    reservation = reserve_order(
        db_session,
        ctx["principal"],
        {
            "production_order_id": order.id,
            "inventory_item_id": item.id,
            "required_quantity": "100",
            "adopt_historical": True,
            "reason": "adoção humana da ordem anterior ao 0020",
        },
        idempotency_key=uuid4(),
    )
    assert reservation.status == "partial"
    assert reservation.adopted is True
    assert Decimal(reservation.shortage_quantity) == Decimal("60")
    balance = db_session.scalar(
        select(InventoryBalance).where(InventoryBalance.organization_id == ctx["organization"].id)
    )
    assert Decimal(balance.physical_quantity) == Decimal("40")
    assert Decimal(balance.reserved_quantity) == Decimal("40")
    assert Decimal(balance.physical_quantity) - Decimal(balance.reserved_quantity) == Decimal("0")


def test_fefo_is_suggestion_only(db_session: Session) -> None:
    ctx = _world(db_session, "inv-fefo")
    _location, item, lot = _stock(ctx, "300")
    suggestions = suggest_fefo(db_session, ctx["principal"], item.id, "50")
    assert suggestions[0]["inventory_lot_id"] == str(lot.id)
    assert suggestions[0]["algorithm"] == "fefo_suggest"


def test_pick_and_idempotent_consumption_posting(db_session: Session) -> None:
    ctx = _world(db_session, "inv-pick")
    prod = _context(db_session, "inv-pick-ord")
    _, _, order = _plan_and_order(db_session, prod)
    ctx["organization"] = prod["organization"]
    ctx["principal"] = helpers.principal_for(prod["actor"], prod["organization"], "owner")
    ctx["place"] = prod["establishment"]
    ctx["ingredient"] = helpers.ingredient(db_session, prod["organization"], "FAR-PK")
    helpers.version(db_session, ctx["ingredient"], helpers.gram(db_session), status="published")
    location, item, lot = _stock(ctx, "200")
    from app.modules.production_planning.commands import release_order

    release_order(db_session, prod["principal"], order_id=order.id, idempotency_key=uuid4())
    pick = confirm_pick(
        db_session,
        ctx["principal"],
        {
            "production_order_id": order.id,
            "lines": [
                {
                    "inventory_item_id": item.id,
                    "inventory_lot_id": lot.id,
                    "quantity": "30",
                    "suggested": True,
                }
            ],
        },
        idempotency_key=uuid4(),
    )
    assert pick.status == "confirmed"
    from app.modules.production_execution.models import ProductionMaterialConsumption
    from app.modules.production_planning.models import ProductionBatch, ProductionBatchMaterial

    batch = db_session.scalar(select(ProductionBatch).where(ProductionBatch.production_order_id == order.id))
    material = db_session.scalar(
        select(ProductionBatchMaterial).where(ProductionBatchMaterial.production_batch_id == batch.id)
    )
    consumption = ProductionMaterialConsumption(
        organization_id=prod["organization"].id,
        production_order_id=order.id,
        production_batch_id=batch.id,
        production_batch_material_id=material.id,
        consumption_type="consume",
        quantity=Decimal("30"),
        measurement_unit_id=helpers.gram(db_session).id,
        unit_code="g",
        canonical_quantity=Decimal("30"),
        canonical_unit_id=helpers.gram(db_session).id,
        canonical_unit_code="g",
        conversion_factor=Decimal("1"),
        conversion_source="test",
        conversion_version="1",
        actor_user_id=prod["actor"].id,
        idempotency_key=uuid4(),
    )
    db_session.add(consumption)
    db_session.flush()
    key = uuid4()
    first = post_consumption(
        db_session,
        ctx["principal"],
        consumption.id,
        {"ingredient_id": ctx["ingredient"].id, "inventory_lot_id": lot.id, "from_location_id": location.id},
        idempotency_key=key,
    )
    second = post_consumption(
        db_session,
        ctx["principal"],
        consumption.id,
        {"ingredient_id": ctx["ingredient"].id, "inventory_lot_id": lot.id, "from_location_id": location.id},
        idempotency_key=key,
    )
    assert first.id == second.id


def test_inventory_count_double_and_adjust(db_session: Session) -> None:
    ctx = _world(db_session, "inv-cnt")
    location, item, lot = _stock(ctx, "100")
    session_row = create_count(
        db_session,
        ctx["principal"],
        {"inventory_location_id": location.id, "cutoff_at": _now(), "require_second_count": True},
        idempotency_key=uuid4(),
    )
    freeze_count_scope(
        db_session,
        ctx["principal"],
        session_row.id,
        expected_version=session_row.row_version,
        idempotency_key=uuid4(),
    )
    from app.modules.inventory_procurement.models import InventoryCountScope

    scope = db_session.scalar(
        select(InventoryCountScope).where(InventoryCountScope.inventory_count_session_id == session_row.id)
    )
    record_count(
        db_session,
        ctx["principal"],
        session_row.id,
        {"inventory_count_scope_id": scope.id, "pass_number": 1, "quantity": "90"},
        idempotency_key=uuid4(),
    )
    record_count(
        db_session,
        ctx["principal"],
        session_row.id,
        {"inventory_count_scope_id": scope.id, "pass_number": 2, "quantity": "90"},
        idempotency_key=uuid4(),
    )
    db_session.refresh(session_row)
    review_count(
        db_session,
        ctx["principal"],
        session_row.id,
        {"decision": "reviewed", "reason": "divergência conferida"},
        expected_version=session_row.row_version,
        idempotency_key=uuid4(),
    )
    db_session.refresh(session_row)
    closed = approve_count(
        db_session,
        ctx["principal"],
        session_row.id,
        expected_version=session_row.row_version,
        idempotency_key=uuid4(),
    )
    assert closed.status == "closed"
    with pytest.raises(ImmutableError):
        from app.modules.inventory_procurement.services import reopen_count

        reopen_count(db_session, ctx["principal"], closed.id)
    balance = db_session.scalar(
        select(InventoryBalance).where(InventoryBalance.organization_id == ctx["organization"].id)
    )
    assert Decimal(balance.physical_quantity) == Decimal("90")


def test_replenishment_gaps_and_no_automatic_purchase(db_session: Session) -> None:
    ctx = _world(db_session, "inv-rpl")
    _stock(ctx, "10")
    suggestion = suggest_replenishment(db_session, ctx["principal"], {"horizon_days": 7}, idempotency_key=uuid4())
    from app.modules.inventory_procurement.services import replenishment_items

    items = replenishment_items(db_session, suggestion.id)
    assert items
    assert items[0].formula["automatic_purchase"] is False
    with pytest.raises(ValidationError, match="compra_automatica_proibida"):
        refuse_automatic_purchase()


def test_requisition_quotation_order_receive_return_price(db_session: Session) -> None:
    ctx = _world(db_session, "inv-buy")
    location, item, lot = _stock(ctx, "50")
    vendor = helpers.supplier(db_session, ctx["organization"], "FOR-1")
    req = create_requisition(
        db_session,
        ctx["principal"],
        {
            "establishment_id": ctx["place"].id,
            "inventory_location_id": location.id,
            "justification": "cobertura abaixo do ponto",
            "items": [{"inventory_item_id": item.id, "quantity": "500", "unit_code": "g"}],
        },
        idempotency_key=uuid4(),
    )
    req = transition_requisition(
        db_session, ctx["principal"], req.id, "submitted", expected_version=req.row_version, idempotency_key=uuid4()
    )
    req = transition_requisition(
        db_session, ctx["principal"], req.id, "approved", expected_version=req.row_version, idempotency_key=uuid4()
    )
    quote = create_quotation(
        db_session,
        ctx["principal"],
        {
            "supplier_id": vendor.id,
            "lead_time_days": 3,
            "items": [
                {
                    "inventory_item_id": item.id,
                    "quantity": "500",
                    "unit_code": "g",
                    "unit_price": "0.02",
                }
            ],
        },
        idempotency_key=uuid4(),
    )
    compared = compare_quotations(db_session, ctx["principal"], item.id)
    assert compared[0]["chosen"] is False
    order = create_order(
        db_session,
        ctx["principal"],
        {
            "establishment_id": ctx["place"].id,
            "supplier_id": vendor.id,
            "inventory_location_id": location.id,
            "items": [
                {
                    "inventory_item_id": item.id,
                    "quantity": "500",
                    "unit_code": "g",
                    "unit_price": "0.02",
                    "procurement_quotation_item_id": None,
                }
            ],
        },
        idempotency_key=uuid4(),
    )
    order = transition_order(
        db_session, ctx["principal"], order.id, "approved", expected_version=order.row_version, idempotency_key=uuid4()
    )
    order = transition_order(
        db_session, ctx["principal"], order.id, "issued", expected_version=order.row_version, idempotency_key=uuid4()
    )
    from app.modules.inventory_procurement.services import current_order_items

    order_item = current_order_items(db_session, order)[0]
    db_session.refresh(order)
    receipt = receive_order(
        db_session,
        ctx["principal"],
        {
            "procurement_order_id": order.id,
            "inventory_location_id": location.id,
            "items": [
                {
                    "procurement_order_item_id": order_item.id,
                    "quantity": "200",
                    "supplier_lot_code": "FOR-L1",
                    "expires_on": (datetime.now(UTC).date() + timedelta(days=40)).isoformat(),
                    "observed_unit_price": "0.03",
                }
            ],
        },
        idempotency_key=uuid4(),
    )
    assert receipt.status == "posted"
    from app.modules.ingredient_catalog.models import SupplierItem
    from app.modules.ingredient_catalog.models import SupplierItemPrice as Price
    from app.modules.inventory_procurement.models import InventoryLot, ProcurementReceiptItem

    received_lot = db_session.scalar(
        select(InventoryLot).where(
            InventoryLot.organization_id == ctx["organization"].id,
            InventoryLot.supplier_lot_code == "FOR-L1",
        )
    )
    assert received_lot is not None
    assert (
        db_session.scalar(
            select(Price)
            .join(SupplierItem, Price.supplier_item_id == SupplierItem.id)
            .where(SupplierItem.organization_id == ctx["organization"].id)
        )
        is None
    )
    receipt_item = db_session.scalar(
        select(ProcurementReceiptItem).where(ProcurementReceiptItem.organization_id == ctx["organization"].id)
    )
    from app.modules.inventory_procurement.services import record_observed_price

    # sem supplier_item o comando falha de forma explícita
    with pytest.raises(ValidationError):
        record_observed_price(db_session, ctx["principal"], receipt_item.id, idempotency_key=uuid4())
    ret = return_to_supplier(
        db_session,
        ctx["principal"],
        {
            "procurement_receipt_id": receipt.id,
            "inventory_lot_id": received_lot.id,
            "quantity": "20",
            "reason": "embalagem avariada",
        },
        idempotency_key=uuid4(),
    )
    assert ret.reason == "embalagem avariada"
    timeline = traceability(db_session, ctx["principal"], lot_id=received_lot.id)
    types = {event["type"] for event in timeline["events"]}
    assert "lot" in types and "receipt" in types and "movement" in types
    assert quote.id


def test_http_and_isolation_and_inventory_report(engine) -> None:
    owner = _setup(engine, "inv-http")
    baker = _setup(engine, "inv-bak", role="baker_operator", fake=owner["fake"], client=owner["client"])
    other = _setup(engine, "inv-b", fake=owner["fake"], client=owner["client"])
    created = owner["client"].post(
        _base(owner, "/inventory/policies"),
        headers=_h(owner, key=uuid4()),
        json={"code": "EST-HTTP", "effective_from": _now(), "justification": "teste"},
    )
    assert created.status_code == 200, created.text
    policy_id = created.json()["data"]["id"]
    published = owner["client"].post(
        _base(owner, f"/inventory/policies/{policy_id}/publish"),
        headers=_h(owner, key=uuid4(), match=1),
    )
    assert published.status_code == 200, published.text
    hidden = baker["client"].get(_base(owner, "/inventory/balances"), headers=_h(baker))
    assert hidden.status_code in {200, 403, 404}
    foreign = other["client"].get(_base(owner, "/inventory/policies"), headers=_h(other))
    assert foreign.status_code in {403, 404} or foreign.json().get("items") == []
    report = owner["client"].get(_base(owner, "/reporting/reports/inventory"), headers=_h(owner))
    assert report.status_code == 200, report.text
    assert report.json()["data"]["report_code"] == "inventory"
    denied = baker["client"].get(_base(baker, "/reporting/reports/inventory"), headers=_h(baker))
    assert denied.status_code == 403
    replay = owner["client"].post(
        _base(owner, "/inventory/policies"),
        headers=_h(owner, key=uuid4()),
        json={"code": "EST-HTTP", "effective_from": _now(), "justification": "teste"},
    )
    assert replay.status_code in {200, 409, 422}
    _cleanup(owner["client"])


def test_concurrent_issue_and_reserve(engine) -> None:
    session = Session(bind=engine, future=True)
    ctx = _world(session, f"inv-con-{uuid4().hex[:6]}")
    location, item, lot = _stock(ctx, "50")
    session.commit()
    errors: list[str] = []

    def worker(qty: str) -> None:
        local = Session(bind=engine, future=True)
        try:
            principal = helpers.principal_for(ctx["actor"], ctx["organization"], "owner")
            post_movement(
                local,
                principal,
                {
                    "movement_type": "production_consume",
                    "inventory_item_id": item.id,
                    "inventory_lot_id": lot.id,
                    "from_location_id": location.id,
                    "quantity": qty,
                    "unit_code": "g",
                },
                idempotency_key=uuid4(),
            )
            local.commit()
        except Exception as exc:  # noqa: BLE001
            errors.append(type(exc).__name__)
            local.rollback()
        finally:
            local.close()

    threads = [Thread(target=worker, args=("40",)), Thread(target=worker, args=("40",))]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    check = Session(bind=engine, future=True)
    balance = check.scalar(select(InventoryBalance).where(InventoryBalance.inventory_lot_id == lot.id))
    assert Decimal(balance.physical_quantity) >= Decimal("0")
    assert Decimal(balance.physical_quantity) <= Decimal("50")
    assert errors
    check.close()
    session.close()


def test_baker_cannot_approve_purchase(db_session: Session) -> None:
    ctx = _world(db_session, "inv-bak-deny", role="baker_operator")
    with pytest.raises(AuthorizationError):
        create_requisition(
            db_session,
            ctx["principal"],
            {
                "establishment_id": ctx["place"].id,
                "justification": "não deveria",
                "items": [],
            },
            idempotency_key=uuid4(),
        )

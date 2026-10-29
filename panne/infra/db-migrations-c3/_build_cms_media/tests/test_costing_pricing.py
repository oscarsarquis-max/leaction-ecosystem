from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.costing_pricing.engine import calculate
from app.modules.costing_pricing.formulas import (
    price_from_contribution,
    price_from_gross_margin,
    price_from_markup_factor,
    reverse_metrics,
)
from app.modules.costing_pricing.models import CostingPolicy, CostingPolicyVersion
from app.modules.costing_pricing.valuation import convert_quantity, select_price
from app.modules.identity_organization.authorization import permissions_for_role
from app.modules.ingredient_catalog.models import MeasurementUnit, SupplierItem, SupplierItemPrice
from app.modules.production_planning.errors import ValidationError
from tests import helpers
from tests.test_production_api import _cleanup
from tests.test_recipe_http import _base, _h, _setup


def _ensure_head(engine) -> None:
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    config.set_main_option("script_location", str(Path(__file__).resolve().parents[1] / "alembic"))
    command.upgrade(config, "head")


@pytest.fixture(scope="module", autouse=True)
def _costing_schema(engine) -> None:
    _ensure_head(engine)


def _now() -> datetime:
    return datetime(2026, 8, 23, 12, 0, tzinfo=UTC)


def _policy(session: Session, organization, actor, **extra) -> CostingPolicyVersion:
    policy = CostingPolicy(
        organization_id=organization.id,
        code=extra.get("code", f"POL-{uuid4().hex[:6]}"),
        display_name="Padrão",
        status="published",
        created_by_user_id=actor.id,
    )
    session.add(policy)
    session.flush()
    version = CostingPolicyVersion(
        organization_id=organization.id,
        costing_policy_id=policy.id,
        version_number=1,
        status="published",
        currency="BRL",
        timezone="America/Sao_Paulo",
        price_criterion=extra.get("price_criterion", "latest_observed"),
        enabled_categories=extra.get(
            "enabled_categories",
            ["ingredient", "packaging", "labor", "waste", "rework", "other"],
        ),
        algorithm_name="costing_pricing",
        algorithm_version="1",
        effective_from=_now(),
        created_by_user_id=actor.id,
    )
    session.add(version)
    session.flush()
    return version


def _offer(session, organization, ingredient_id, unit, price, observed_at, sku: str):
    vendor = helpers.supplier(session, organization, f"FOR-{sku}")
    item = SupplierItem(
        organization_id=organization.id,
        supplier_id=vendor.id,
        ingredient_id=ingredient_id,
        supplier_sku=sku,
        package_quantity=Decimal("1000"),
        measurement_unit_id=unit.id,
        status="active",
    )
    session.add(item)
    session.flush()
    session.add(
        SupplierItemPrice(
            supplier_item_id=item.id,
            unit_price=price,
            currency="BRL",
            observed_at=observed_at,
            source="nota",
        )
    )
    session.flush()
    return item


def test_formulas_distinct_and_invalid_denominator() -> None:
    assert price_from_markup_factor(Decimal("10"), Decimal("2")) == Decimal("20")
    assert price_from_gross_margin(Decimal("10"), Decimal("0.20")) == Decimal("12.5")
    assert price_from_contribution(Decimal("10"), Decimal("0.10"), Decimal("0.20")) == Decimal(
        "14.285714"
    )
    reverse = reverse_metrics(
        Decimal("20"), Decimal("10"), variable_product=Decimal("8"), variable_selling=Decimal("2")
    )
    assert reverse["markup_percent"] == Decimal("100.0000")
    with pytest.raises(ValidationError, match="denominador_invalido"):
        price_from_gross_margin(Decimal("10"), Decimal("1"))
    with pytest.raises(ValidationError, match="denominador_invalido"):
        price_from_contribution(Decimal("10"), Decimal("0.6"), Decimal("0.5"))


def test_baker_has_no_costing_permission() -> None:
    granted = permissions_for_role("baker_operator")
    assert "costing.read" not in granted
    assert "pricing.publish" not in granted
    assert "pricing.publish" in permissions_for_role("owner")
    assert "pricing.publish" not in permissions_for_role("technical_responsible")


def test_price_selection_and_incompatible_conversion(db_session: Session) -> None:
    organization = helpers.org(db_session, "org-cost-val")
    unit = helpers.gram(db_session)
    flour = helpers.published_ingredient(db_session, organization, unit, "FAR-V")
    older = _now() - timedelta(days=10)
    newer = _now() - timedelta(days=1)
    _offer(db_session, organization, flour.ingredient_id, unit, Decimal("20"), older, "OLD")
    _offer(db_session, organization, flour.ingredient_id, unit, Decimal("30"), newer, "NEW")
    chosen = select_price(
        db_session,
        ingredient_version_id=flour.id,
        valuation_at=_now(),
        currency="BRL",
        criterion="latest_observed",
    )
    assert chosen is not None
    assert chosen["unit_price"] == Decimal("30")
    assert (
        select_price(
            db_session,
            ingredient_version_id=flour.id,
            valuation_at=older - timedelta(days=1),
            currency="BRL",
            criterion="latest_observed",
        )
        is None
    )
    volume = MeasurementUnit(
        code=f"l-{uuid4().hex[:6]}",
        name="litro",
        dimension="volume",
        si_factor=Decimal("1"),
        status="active",
    )
    db_session.add(volume)
    db_session.flush()
    with pytest.raises(ValidationError, match="conversao_massa_volume_proibida"):
        convert_quantity(Decimal("1"), unit, volume)


def test_planned_cost_missing_price_is_not_zero(db_session: Session) -> None:
    organization = helpers.org(db_session, "org-cost-plan")
    actor = helpers.user(db_session, "plan@example.com")
    unit = helpers.gram(db_session)
    product = helpers.technical_product(db_session, organization, "PAO-C")
    recipe = helpers.formulation(db_session, product, "REC-C")
    version = helpers.formulation_version(db_session, recipe)
    flour = helpers.published_ingredient(db_session, organization, unit, "FAR-C")
    helpers.formulation_item(db_session, version, flour, unit, 1, Decimal("500"))
    policy = _policy(db_session, organization, actor)
    calc = calculate(
        db_session,
        policy=policy,
        kind="planned",
        actor_user_id=actor.id,
        valuation_at=_now(),
        formulation_version_id=version.id,
    )
    assert calc.completeness == "insufficient_data"
    assert calc.total_amount is None
    _offer(
        db_session,
        organization,
        flour.ingredient_id,
        unit,
        Decimal("10"),
        _now() - timedelta(days=1),
        "OK",
    )
    calc2 = calculate(
        db_session,
        policy=policy,
        kind="planned",
        actor_user_id=actor.id,
        valuation_at=_now(),
        formulation_version_id=version.id,
        planned_batches=2,
    )
    assert calc2.completeness == "complete"
    assert calc2.total_amount == Decimal("10")
    assert calc2.batch_amount == Decimal("5")
    assert calc.id != calc2.id


def test_http_permissions_idempotency_and_no_auto_publish(engine) -> None:
    owner = _setup(engine, "cost-own", "owner")
    baker = _setup(
        engine, "cost-bak", "baker_operator", fake=owner["fake"], client=owner["client"]
    )
    other = None
    try:
        created = owner["client"].post(
            _base(owner, "/costing/policies"),
            headers=_h(owner, key=uuid4()),
            json={
                "code": "POL-HTTP",
                "effective_from": _now().isoformat(),
                "enabled_categories": ["ingredient", "other"],
            },
        )
        assert created.status_code == 200, created.text
        policy_id = created.json()["data"]["id"]
        version_id = created.json()["data"]["version"]["id"]
        published = owner["client"].post(
            _base(owner, f"/costing/policies/{policy_id}/publish"),
            headers=_h(owner, key=uuid4(), match=str(created.json()["row_version"])),
        )
        assert published.status_code == 200
        forbidden = baker["client"].get(_base(baker, "/costing/policies"), headers=_h(baker))
        assert forbidden.status_code == 403
        unit = owner["unit"]
        flour = helpers.published_ingredient(owner["admin"], owner["organization"], unit, "FAR-H")
        product = helpers.technical_product(owner["admin"], owner["organization"], "PAO-H")
        recipe = helpers.formulation(owner["admin"], product, "REC-H")
        version = helpers.formulation_version(owner["admin"], recipe)
        helpers.formulation_item(owner["admin"], version, flour, unit, 1, Decimal("1000"))
        _offer(
            owner["admin"],
            owner["organization"],
            flour.ingredient_id,
            unit,
            Decimal("8"),
            _now() - timedelta(days=1),
            "HTTP",
        )
        owner["admin"].commit()
        key = uuid4()
        payload = {
            "kind": "planned",
            "policy_version_id": version_id,
            "valuation_at": _now().isoformat(),
            "formulation_version_id": str(version.id),
        }
        first = owner["client"].post(
            _base(owner, "/costing/calculations"),
            headers=_h(owner, key=key),
            json=payload,
        )
        assert first.status_code == 200, first.text
        replay = owner["client"].post(
            _base(owner, "/costing/calculations"),
            headers=_h(owner, key=key),
            json=payload,
        )
        assert replay.status_code == 200
        assert replay.json()["data"]["id"] == first.json()["data"]["id"]
        assert first.json()["data"]["auto_published"] is False
        calc_id = first.json()["data"]["id"]
        sim = owner["client"].post(
            _base(owner, f"/costing/calculations/{calc_id}/simulations"),
            headers=_h(owner, key=uuid4()),
            json={"kind": "markup_factor", "factor": "2", "channel": "own_counter"},
        )
        assert sim.status_code == 200, sim.text
        assert Decimal(sim.json()["data"]["suggested_price"]) == Decimal("16")
        practiced = owner["client"].post(
            _base(owner, "/pricing/practiced"),
            headers=_h(owner, key=uuid4()),
            json={
                "technical_product_id": str(product.id),
                "channel": "own_counter",
                "amount": "16",
                "valid_from": _now().isoformat(),
                "simulation_id": sim.json()["data"]["id"],
                "justification": "revisão humana",
            },
        )
        assert practiced.status_code == 200, practiced.text
        assert practiced.json()["data"]["status"] == "draft"
        published_price = owner["client"].post(
            _base(owner, f"/pricing/practiced/{practiced.json()['data']['id']}/decide"),
            headers=_h(owner, key=uuid4(), match=str(practiced.json()["row_version"])),
            json={"decision": "publish", "notes": "ok"},
        )
        assert published_price.status_code == 200
        assert published_price.json()["data"]["status"] == "active"
        conflict = owner["client"].post(
            _base(owner, f"/pricing/practiced/{practiced.json()['data']['id']}/decide"),
            headers=_h(owner, key=uuid4(), match="1"),
            json={"decision": "retire"},
        )
        assert conflict.status_code == 409
        other = _setup(
            engine, "cost-b", "owner", fake=owner["fake"], client=owner["client"]
        )
        isolated = other["client"].get(
            _base(owner, f"/costing/calculations/{calc_id}"),
            headers=_h(other),
        )
        assert isolated.status_code in {403, 404, 422}
        reverse = owner["client"].post(
            _base(owner, f"/costing/calculations/{calc_id}/simulations"),
            headers=_h(owner, key=uuid4()),
            json={
                "kind": "reverse",
                "price": "20",
                "variable_product": "8",
                "variable_selling": "2",
                "channel": "wholesale",
            },
        )
        assert reverse.status_code == 200, reverse.text
        assert reverse.json()["data"]["snapshot"]["markup_percent"] == "150.0000"
        invalid = owner["client"].post(
            _base(owner, f"/costing/calculations/{calc_id}/invalidate"),
            headers=_h(owner, key=uuid4()),
        )
        assert invalid.status_code == 200
        assert invalid.json()["data"]["completeness"] == "invalidated"
        detail = owner["client"].get(
            _base(owner, f"/costing/calculations/{calc_id}"),
            headers=_h(owner),
        )
        assert detail.status_code == 200
        assert detail.json()["data"]["completeness"] == "invalidated"
        assert detail.json()["data"]["total_amount"] == first.json()["data"]["total_amount"]
    finally:
        _cleanup(owner["client"])
        if other is not None:
            other["admin"].close()
        baker["admin"].close()


def test_currency_mismatch_and_double_count(db_session: Session) -> None:
    organization = helpers.org(db_session, "org-cost-fx")
    unit = helpers.gram(db_session)
    flour = helpers.published_ingredient(db_session, organization, unit, "FAR-FX")
    vendor = helpers.supplier(db_session, organization, "FOR-USD")
    from app.modules.ingredient_catalog.models import SupplierItem, SupplierItemPrice

    item = SupplierItem(
        organization_id=organization.id,
        supplier_id=vendor.id,
        ingredient_id=flour.ingredient_id,
        supplier_sku="USD-1",
        package_quantity=Decimal("1000"),
        measurement_unit_id=unit.id,
        status="active",
    )
    db_session.add(item)
    db_session.flush()
    db_session.add(
        SupplierItemPrice(
            supplier_item_id=item.id,
            unit_price=Decimal("10"),
            currency="USD",
            observed_at=_now() - timedelta(days=1),
            source="nota",
        )
    )
    db_session.flush()
    with pytest.raises(ValidationError, match="moeda_incompativel"):
        select_price(
            db_session,
            ingredient_version_id=flour.id,
            valuation_at=_now(),
            currency="BRL",
            criterion="latest_observed",
        )
    actor = helpers.user(db_session, "fx@example.com")
    product = helpers.technical_product(db_session, organization, "PAO-FX")
    recipe = helpers.formulation(db_session, product, "REC-FX")
    version = helpers.formulation_version(db_session, recipe)
    salt = helpers.published_ingredient(db_session, organization, unit, "SAL-FX")
    helpers.formulation_item(db_session, version, salt, unit, 1, Decimal("500"))
    policy = _policy(db_session, organization, actor, code="POL-FX")
    from app.modules.costing_pricing.engine import _add_component
    from app.modules.costing_pricing.models import CostingComponent

    calc = calculate(
        db_session,
        policy=policy,
        kind="standard",
        actor_user_id=actor.id,
        valuation_at=_now(),
        formulation_version_id=version.id,
    )
    first = db_session.scalar(
        select(CostingComponent).where(CostingComponent.costing_calculation_id == calc.id)
    )
    assert first.quality == "missing"
    with pytest.raises(ValidationError, match="dupla_contagem"):
        _add_component(
            db_session,
            calc,
            category="ingredient",
            origin_type=first.origin_type,
            origin_id=first.origin_id,
            nature="direct",
            behavior="variable",
            quantity=Decimal("1"),
            unit_code="g",
            rate=None,
            amount=None,
            quality="missing",
            evidence={},
        )


def test_actual_cost_distinguishes_return_waste_and_yield(db_session: Session) -> None:
    from app.modules.formula_lab.models import FormulationItem
    from app.modules.ingredient_catalog.models import IngredientVersion
    from app.modules.production_execution.constants import (
        CONSUMPTION_CONSUME,
        CONSUMPTION_RETURN,
        CONSUMPTION_WASTE,
        YIELD_LEFTOVER,
        YIELD_POST_BAKE_MASS,
    )
    from app.modules.production_execution.consumption import record_consumption
    from app.modules.production_execution.lifecycle import mark_order_ready
    from app.modules.production_execution.yields import record_yield
    from app.modules.production_planning.commands import release_order
    from tests.test_production_execution import _batches, _materials
    from tests.test_production_planning import _context, _plan_and_order

    ctx = _context(db_session, "org-cact")
    _, _, order = _plan_and_order(db_session, ctx, batches=1)
    release_order(db_session, ctx["principal"], order_id=order.id, idempotency_key=uuid4())
    mark_order_ready(db_session, ctx["principal"], order_id=order.id, idempotency_key=uuid4())
    items = list(
        db_session.scalars(
            select(FormulationItem).where(
                FormulationItem.formulation_version_id == ctx["version"].id
            )
        )
    )
    for index, item in enumerate(items):
        version = db_session.get(IngredientVersion, item.ingredient_version_id)
        _offer(
            db_session,
            ctx["organization"],
            version.ingredient_id,
            ctx["unit"],
            Decimal("10"),
            _now() - timedelta(days=1),
            f"ACT{index}",
        )
    batch = _batches(db_session, order.id)[0]
    for material in _materials(db_session, batch.id):
        record_consumption(
            db_session,
            ctx["principal"],
            batch_id=batch.id,
            batch_material_id=material.id,
            consumption_type=CONSUMPTION_CONSUME,
            quantity=material.planned_gross_quantity,
            measurement_unit_id=ctx["unit"].id,
            idempotency_key=uuid4(),
        )
    waste_material = _materials(db_session, batch.id)[0]
    record_consumption(
        db_session,
        ctx["principal"],
        batch_id=batch.id,
        batch_material_id=waste_material.id,
        consumption_type=CONSUMPTION_WASTE,
        quantity=Decimal("50"),
        measurement_unit_id=ctx["unit"].id,
        idempotency_key=uuid4(),
    )
    record_consumption(
        db_session,
        ctx["principal"],
        batch_id=batch.id,
        batch_material_id=waste_material.id,
        consumption_type=CONSUMPTION_RETURN,
        quantity=Decimal("20"),
        measurement_unit_id=ctx["unit"].id,
        idempotency_key=uuid4(),
    )
    record_yield(
        db_session,
        ctx["principal"],
        batch_id=batch.id,
        measurement_type=YIELD_POST_BAKE_MASS,
        quantity=Decimal("3000"),
        measurement_unit_id=ctx["unit"].id,
        idempotency_key=uuid4(),
    )
    record_yield(
        db_session,
        ctx["principal"],
        batch_id=batch.id,
        measurement_type=YIELD_LEFTOVER,
        quantity=Decimal("100"),
        measurement_unit_id=ctx["unit"].id,
        idempotency_key=uuid4(),
    )
    policy = _policy(db_session, ctx["organization"], ctx["actor"], code="POL-ACT")
    calc = calculate(
        db_session,
        policy=policy,
        kind="actual",
        actor_user_id=ctx["actor"].id,
        valuation_at=_now(),
        production_order_id=order.id,
    )
    from app.modules.costing_pricing.models import CostingComponent, CostingGap

    components = list(
        db_session.scalars(
            select(CostingComponent).where(CostingComponent.costing_calculation_id == calc.id)
        )
    )
    categories = {row.category for row in components}
    origins = {row.origin_type for row in components}
    assert "waste" in categories
    assert "leftover" in origins
    assert calc.total_amount is not None
    assert calc.sellable_unit_amount is None
    gaps = list(
        db_session.scalars(select(CostingGap).where(CostingGap.costing_calculation_id == calc.id))
    )
    assert any(row.code == "rendimento_ausente" for row in gaps)
    assert calc.completeness == "partial"

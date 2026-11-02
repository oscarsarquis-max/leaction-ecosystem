"""Encerrar a operação por lançamentos, sem apagar (CURSOR-032, só do comando)."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from app.modules.fiscal_inbound.models import FiscalInboundDocument
from app.modules.formula_lab.models import TechnicalProduct
from app.modules.identity_organization.models import Establishment, OrganizationMembership
from app.modules.ingredient_catalog.models import Ingredient
from app.modules.inventory_procurement import services as inventory
from app.modules.inventory_procurement.models import (
    InventoryBalance,
    InventoryCountSession,
    InventoryItem,
    InventoryLocation,
    InventoryMovement,
    InventoryReservation,
)
from app.modules.production_planning.commands import release_order
from app.modules.production_planning.models import ProductionOrder
from app.ops import close_operations
from sqlalchemy import func, select
from sqlalchemy.orm import sessionmaker
from tests import helpers
from tests.rls_support import runtime_engine as build_runtime_engine
from tests.test_production_planning import _context, _plan_and_order


@pytest.fixture
def runtime(engine):
    created = build_runtime_engine(engine)
    try:
        yield created
    finally:
        created.dispose()


class World:
    """Uma organização com cadastro, estoque, reservas, pedidos e notas. Tudo gravado de verdade."""

    def __init__(self, engine, tag: str) -> None:
        self.engine = engine
        self.factory = sessionmaker(bind=engine, future=True, expire_on_commit=False)
        self.slug = f"enc{tag}{uuid4().hex[:6]}"
        session = self.factory()
        ctx = _context(session, self.slug, role="owner")
        session.commit()
        self.ctx = ctx
        self.org_id = ctx["organization"].id
        self.principal = ctx["principal"]
        self.place = ctx["establishment"]

        # estoque: política e abertura num commit antes dos pedidos (reserva não é "histórica")
        location = inventory.create_location(
            session,
            self.principal,
            {
                "establishment_id": str(self.place.id),
                "code": "DESP",
                "display_name": "Despensa",
                "kind": "warehouse",
            },
            idempotency_key=uuid4(),
        )
        self.location_id = location.id
        unit = ctx["unit"]
        self.flour = helpers.published_ingredient(
            session, ctx["organization"], unit, f"FA-{self.slug[-6:]}"
        )
        self.sugar = helpers.published_ingredient(
            session, ctx["organization"], unit, f"AC-{self.slug[-6:]}"
        )
        for ingredient, quantity, expires in (
            (self.flour, "5000", "2099-01-01"),
            (self.sugar, "1200", "2099-01-01"),
            (self.sugar, "300", "2020-01-01"),  # vencido: só zera com o override do domínio
        ):
            inventory.open_balance(
                session,
                self.principal,
                {
                    "ingredient_id": str(ingredient.ingredient_id),
                    "unit_code": "g",
                    "quantity": quantity,
                    "confirmed": True,
                    "cost_unknown": True,
                    "origin": "teste",
                    "inventory_location_id": str(location.id),
                    "expires_on": expires,
                },
                idempotency_key=uuid4(),
            )
        session.commit()
        self.flour_item_id = session.scalar(
            select(InventoryItem.id).where(
                InventoryItem.organization_id == self.org_id,
                InventoryItem.ingredient_id == self.flour.ingredient_id,
            )
        )

        # pedidos: um agendado (sem reserva), um liberado (com reserva), um já iniciado
        _, _, scheduled = _plan_and_order(session, ctx)
        _, _, released = _plan_and_order(session, ctx)
        _, _, started = _plan_and_order(session, ctx)
        for order in (released, started):
            release_order(session, self.principal, order_id=order.id, idempotency_key=uuid4())
        session.commit()
        started_row = session.get(ProductionOrder, started.id)
        started_row.status = "in_progress"
        session.commit()
        inventory.reserve_order(
            session,
            self.principal,
            {
                "production_order_id": str(released.id),
                "inventory_item_id": str(self.flour_item_id),
                "required_quantity": "800",
            },
            idempotency_key=uuid4(),
        )
        session.commit()
        self.order_ids = {"scheduled": scheduled.id, "released": released.id, "started": started.id}

        # notas: duas abertas, uma já recebida (histórico)
        for status in ("awaiting_check", "reviewed", "received"):
            session.add(
                FiscalInboundDocument(
                    organization_id=self.org_id,
                    establishment_id=self.place.id,
                    status=status,
                    capture_origin="manual",
                    number=f"{status}-{self.slug[-4:]}",
                    created_by=self.ctx["actor"].id,
                )
            )
        session.commit()
        session.close()

    def snapshot(self) -> dict:
        session = self.factory()
        try:
            org = self.org_id

            def count(model, *where):
                return session.scalar(
                    select(func.count())
                    .select_from(model)
                    .where(model.organization_id == org, *where)
                )

            return {
                "balances_nonzero": count(
                    InventoryBalance, InventoryBalance.physical_quantity != 0
                ),
                "physical_total": session.scalar(
                    select(func.coalesce(func.sum(InventoryBalance.physical_quantity), 0)).where(
                        InventoryBalance.organization_id == org
                    )
                ),
                "reservations_active": count(
                    InventoryReservation,
                    InventoryReservation.status.in_(("pending", "partial", "reserved")),
                ),
                "movements": count(InventoryMovement),
                "orders": dict(
                    session.execute(
                        select(ProductionOrder.status, func.count())
                        .where(ProductionOrder.organization_id == org)
                        .group_by(ProductionOrder.status)
                    ).all()
                ),
                "notes": dict(
                    session.execute(
                        select(FiscalInboundDocument.status, func.count())
                        .where(FiscalInboundDocument.organization_id == org)
                        .group_by(FiscalInboundDocument.status)
                    ).all()
                ),
            }
        finally:
            session.close()

    def cadastro(self) -> dict:
        session = self.factory()
        try:
            org = self.org_id

            def count(model):
                return session.scalar(
                    select(func.count()).select_from(model).where(model.organization_id == org)
                )

            return {
                "ingredients": count(Ingredient),
                "items": count(InventoryItem),
                "locations": count(InventoryLocation),
                "products": count(TechnicalProduct),
                "establishments": count(Establishment),
                "memberships": count(OrganizationMembership),
            }
        finally:
            session.close()


def _run(runtime, org_id, *flags, capsys):
    factory = sessionmaker(bind=runtime, expire_on_commit=False, future=True)
    code = close_operations.main(["--org", str(org_id), *flags], session_factory=factory)
    out = capsys.readouterr()
    payload = None
    for line in out.out.splitlines():
        if line.startswith("RESULT_JSON "):
            payload = json.loads(line[len("RESULT_JSON ") :])
    return code, payload, out


@pytest.fixture
def target(engine):
    return World(engine, "a")


@pytest.fixture
def other(engine):
    return World(engine, "b")


def test_dry_run_reports_and_changes_nothing(engine, runtime, target, capsys) -> None:
    before = target.snapshot()
    code, payload, _ = _run(runtime, target.org_id, "--dry-run", capsys=capsys)
    assert code == 0, payload
    steps = {step["step"]: step for step in payload["steps"]}
    assert steps["reservas"]["affected"] == 1
    assert steps["producao"]["affected"] == 3
    assert steps["producao"]["no_command"] == 3  # planos: sem comando no domínio
    assert steps["notas"]["affected"] == 2
    assert steps["saldos"]["affected"] == 3
    assert payload["errors_total"] == 0
    assert payload["residual_nonzero_balances"] == 0
    assert target.snapshot() == before


def test_execute_zeroes_balances_and_closes_without_deleting(
    engine, runtime, target, other, capsys
) -> None:
    other_before = other.snapshot()
    other_cadastro = other.cadastro()
    cadastro = target.cadastro()
    before = target.snapshot()
    assert before["balances_nonzero"] == 3

    code, payload, out = _run(
        runtime, target.org_id, "--execute", "--confirm", target.slug, capsys=capsys
    )
    assert code == 0, out.out + out.err
    assert payload["errors_total"] == 0

    after = target.snapshot()
    assert after["balances_nonzero"] == 0
    assert after["physical_total"] == 0
    assert after["reservations_active"] == 0
    assert after["orders"].get("scheduled", 0) == 0
    assert after["orders"].get("cancelled") == 2  # agendado e liberado
    assert after["orders"].get("short_closed") == 1  # já iniciado
    assert after["notes"].get("cancelled") == 2
    assert after["notes"].get("received") == 1  # confirmada fica como histórico
    # nada foi apagado: o histórico só cresce
    assert after["movements"] == before["movements"] + 3
    assert target.cadastro() == cadastro

    session = target.factory()
    try:
        adjusts = list(
            session.scalars(
                select(InventoryMovement).where(
                    InventoryMovement.organization_id == target.org_id,
                    InventoryMovement.movement_type == "adjust_minus",
                )
            )
        )
        assert len(adjusts) == 3
        assert {row.reason for row in adjusts} == {"Encerramento do piloto"}
    finally:
        session.close()

    # a outra organização não foi tocada
    assert other.snapshot() == other_before
    assert other.cadastro() == other_cadastro


def test_second_execution_does_nothing(engine, runtime, target, capsys) -> None:
    first, payload, out = _run(
        runtime, target.org_id, "--execute", "--confirm", target.slug, capsys=capsys
    )
    assert first == 0, out.out + out.err
    state = target.snapshot()
    second, payload, out = _run(
        runtime, target.org_id, "--execute", "--confirm", target.slug, capsys=capsys
    )
    assert second == 0, out.out + out.err
    assert payload["affected_total"] == 0
    assert payload["errors_total"] == 0
    assert target.snapshot() == state
    third, payload, _ = _run(runtime, target.org_id, "--dry-run", capsys=capsys)
    assert third == 0
    assert payload["affected_total"] == 0


@pytest.mark.parametrize("flags", [(), ("--confirm", "slug-errado")])
def test_refuses_without_the_right_confirm(engine, runtime, target, flags, capsys) -> None:
    before = target.snapshot()
    code, payload, out = _run(runtime, target.org_id, "--execute", *flags, capsys=capsys)
    assert code == 3
    assert payload is None
    assert "RECUSADO" in out.err
    assert target.snapshot() == before


def test_execute_with_errors_rolls_everything_back(engine, runtime, target, capsys) -> None:
    # contagem aberta trava o local: o ajuste de saída é recusado pelo domínio.
    # Resultado: erro no relatório e nada é aplicado (uma transação só).
    session = target.factory()
    policy = inventory.published_policy(session, target.org_id)
    session.add(
        InventoryCountSession(
            organization_id=target.org_id,
            public_code=f"CNT-{uuid4().hex[:6]}",
            inventory_location_id=target.location_id,
            cutoff_at=datetime.now(UTC),
            status="counting",
            lock_location=True,
            inventory_policy_version_id=policy.id,
            created_by_user_id=target.ctx["actor"].id,
        )
    )
    session.commit()
    session.close()
    before = target.snapshot()
    code, payload, out = _run(
        runtime, target.org_id, "--execute", "--confirm", target.slug, capsys=capsys
    )
    assert code == 1
    assert payload["errors_total"] == 3
    assert {row["erro"] for row in payload["steps"][3]["error_cases"]} == {"inventario_fechado"}
    assert "ROLLBACK" in out.err
    assert target.snapshot() == before

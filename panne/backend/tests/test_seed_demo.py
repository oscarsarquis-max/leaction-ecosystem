from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.identity_organization.models import Organization
from app.modules.ingredient_catalog.models import Ingredient, MeasurementUnit
from app.modules.inventory_procurement.models import ProcurementOrder, ProcurementQuotation, ProcurementRequisition, ProcurementReturn
from app.modules.production_planning.models import ProductionOrder
from app.seed import ALEMBIC_HEAD
from app.seed.demo import seed_demo
from app.seed.dry_run import inspect_dry_run
from app.seed.manifest import build_manifest, table_counts
from app.seed.reference import seed_reference
from app.seed.smoke import run_journeys
from app.seed.target import SeedTargetError, assert_seed_target


def test_reference_is_idempotent(db_session: Session) -> None:
    first = seed_reference(db_session)
    second = seed_reference(db_session)
    assert first["units"] >= 0
    assert second["units"] == 0
    assert db_session.scalar(select(func.count()).select_from(MeasurementUnit)) >= 3


def test_demo_creates_two_orgs_and_orders(db_session: Session) -> None:
    world = seed_demo(db_session, anchor=date(2026, 8, 24))
    slugs = set(db_session.scalars(select(Organization.slug)))
    assert "panne-demonstracao" in slugs
    assert "padaria-horizonte-demo" in slugs
    assert db_session.scalar(select(func.count()).select_from(Ingredient)) >= 10
    assert db_session.scalar(select(func.count()).select_from(ProductionOrder)) >= 5
    assert world.organization.display_name == "Panne Demonstração"


def test_demo_second_run_does_not_duplicate_orgs(db_session: Session) -> None:
    seed_demo(db_session, anchor=date(2026, 8, 24))
    seed_demo(db_session, anchor=date(2026, 8, 24))
    assert db_session.scalar(select(func.count()).select_from(Organization).where(Organization.slug == "panne-demonstracao")) == 1


def test_dry_run_empty_and_populated_do_not_mutate(db_session: Session) -> None:
    target = {"database": "panne_smoke", "host": "127.0.0.1", "port": "5434", "env": "test"}
    empty_before = table_counts(db_session)
    empty = inspect_dry_run(db_session, anchor=date(2026, 8, 24), target=target)
    empty_after = table_counts(db_session)
    assert empty["mutated"] is False
    assert empty["database_state"] == "empty"
    assert empty_before == empty_after
    assert empty["hashes"]["before"] == empty["hashes"]["after"]
    assert empty["planned_actions"]
    seed_demo(db_session, anchor=date(2026, 8, 24))
    populated_before = table_counts(db_session)
    populated = inspect_dry_run(db_session, anchor=date(2026, 8, 24), target=target)
    populated_after = table_counts(db_session)
    assert populated["mutated"] is False
    assert populated["database_state"] == "populated"
    assert populated_before == populated_after
    assert populated["hashes"]["before"] == populated["hashes"]["after"]
    assert any("imutável" in item for item in populated["impediments"])


def test_demo_procurement_is_complete(db_session: Session) -> None:
    world = seed_demo(db_session, anchor=date(2026, 8, 24))
    assert not [gap for gap in world.gaps if gap.startswith("estoque:compras")]
    statuses = set(db_session.scalars(select(ProcurementRequisition.status)))
    assert {"draft", "submitted", "approved", "converted"} <= statuses
    assert db_session.scalar(select(func.count()).select_from(ProcurementQuotation)) >= 2
    order_statuses = set(db_session.scalars(select(ProcurementOrder.status)))
    assert {"partially_received", "received"} <= order_statuses
    assert db_session.scalar(select(func.count()).select_from(ProcurementReturn)) >= 1


def test_same_anchor_reproduces_org_ids(db_session: Session) -> None:
    first = seed_demo(db_session, anchor=date(2026, 8, 24))
    second = seed_demo(db_session, anchor=date(2026, 8, 24))
    assert second.organization.id == first.organization.id


def test_rls_orgs_are_distinct(db_session: Session) -> None:
    world = seed_demo(db_session, anchor=date(2026, 8, 24))
    assert world.organization.id != world.other.id
    hidden = db_session.scalar(
        select(func.count())
        .select_from(Ingredient)
        .where(Ingredient.organization_id == world.other.id, Ingredient.code == "FAR-TRIGO")
    )
    assert int(hidden or 0) == 0


def test_manifest_matches_counts(db_session: Session) -> None:
    world = seed_demo(db_session, anchor=date(2026, 8, 24))
    payload = build_manifest(db_session, anchor=date(2026, 8, 24), gaps=world.gaps, elapsed_s=0.1, alembic_head="0022_fiscal_inbound")
    assert payload["alembic_head"] == "0022_fiscal_inbound"
    assert payload["table_counts"]["organization"] >= 2
    journeys = run_journeys(db_session)
    assert payload["alembic_head"] == ALEMBIC_HEAD
    for name, result in journeys.items():
        assert result["ok"], f"{name}: {result.get('error')}"
        assert "duration_ms" in result
        assert result["entities"]


def test_guards_still_refuse_panne() -> None:
    try:
        assert_seed_target("postgresql+psycopg://admin:x@127.0.0.1:5434/panne", "local")
        raise AssertionError("deveria recusar")
    except SeedTargetError:
        pass


def test_guards_refuse_production_and_keep_alembic_head() -> None:
    try:
        assert_seed_target("postgresql+psycopg://admin:x@127.0.0.1:5434/panne_demo", "production")
        raise AssertionError("deveria recusar")
    except SeedTargetError:
        pass
    assert ALEMBIC_HEAD == "0022_fiscal_inbound"

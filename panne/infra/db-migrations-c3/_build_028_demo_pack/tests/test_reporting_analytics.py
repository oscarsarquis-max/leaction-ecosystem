from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from app.modules.identity_organization.authorization import permissions_for_role
from app.modules.production_planning.commands import create_order
from app.modules.production_planning.constants import TARGET_MODE_MASS
from app.modules.production_planning.errors import ImmutableError, ValidationError
from app.modules.reporting_analytics.filters import normalize_filters
from app.modules.reporting_analytics.formulas import ratio_percent, unavailable
from app.modules.reporting_analytics.services import (
    _CACHE,
    authorized_catalog,
    create_snapshot,
    open_snapshot,
    refuse_recalculate_snapshot,
    run_drill_down,
    run_report,
)
from app.modules.reporting_http.csv_export import build_csv, neutralize
from sqlalchemy.orm import Session
from tests import helpers
from tests.test_production_api import _cleanup
from tests.test_recipe_http import _base, _h, _setup


def _ensure_head(engine) -> None:
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    config.set_main_option("script_location", str(Path(__file__).resolve().parents[1] / "alembic"))
    command.upgrade(config, "head")


@pytest.fixture(scope="module", autouse=True)
def _reporting_schema(engine) -> None:
    _ensure_head(engine)


@pytest.fixture(autouse=True)
def _clear_cache() -> None:
    _CACHE.clear()


def _period() -> dict:
    end = datetime.now(UTC) + timedelta(days=1)
    start = end - timedelta(days=7)
    return {"period_start": start.isoformat(), "period_end": end.isoformat(), "timezone": "America/Sao_Paulo"}


def test_baker_has_no_executive_or_cost_reporting() -> None:
    baker = permissions_for_role("baker_operator")
    owner = permissions_for_role("owner")
    assert "reporting.production.read" in baker
    assert "reporting.dashboard.read" not in baker
    assert "reporting.costing.read" not in baker
    assert "reporting.pricing.read" not in baker
    assert "reporting.dashboard.read" in owner
    assert "reporting.costing.read" in owner
    assert "reporting.dashboard.read" in permissions_for_role("production_manager")
    assert "reporting.costing.read" not in permissions_for_role("production_manager")


def test_period_and_empty_ratio() -> None:
    filters = normalize_filters(_period())
    assert filters.period_end > filters.period_start
    with pytest.raises(ValidationError, match="periodo_excedido"):
        normalize_filters(
            {
                "period_start": "2026-01-01T00:00:00+00:00",
                "period_end": "2026-08-01T00:00:00+00:00",
            }
        )
    with pytest.raises(ValidationError, match="filtro_invalido"):
        normalize_filters({"order_by": "drop table"})
    assert ratio_percent(Decimal("0"), Decimal("0")) is None
    assert unavailable("conjunto_vazio")["value"] is None


def test_empty_report_is_not_zero(db_session: Session) -> None:
    organization = helpers.org(db_session, "org-rep-empty")
    actor = helpers.user(db_session, "rep-empty@example.com")
    helpers.membership(db_session, organization, actor, "owner")
    principal = helpers.principal_for(actor, organization, "owner")
    payload = run_report(db_session, principal, "production", _period())
    status_card = next(item for item in payload["indicators"] if item["code"] == "orders_by_status")
    assert status_card["status"] == "unavailable"
    assert status_card["value"] is None
    rate = next(item for item in payload["indicators"] if item["code"] == "normal_completion_rate")
    assert rate["status"] == "unavailable"
    assert "faturamento" in payload["impossible"]
    assert payload["not_realtime"] is True
    assert payload["query_count"] <= 16


def test_order_states_and_snapshot(db_session: Session) -> None:
    organization = helpers.org(db_session, "org-rep-ord")
    establishment = helpers.establishment(db_session, organization, "E-R")
    actor = helpers.user(db_session, "rep-ord@example.com")
    helpers.membership(db_session, organization, actor, "owner")
    principal = helpers.principal_for(actor, organization, "owner")
    product = helpers.technical_product(db_session, organization, "PAO-R")
    helpers.ensure_published_recipe(db_session, product, actor)
    create_order(
        db_session,
        principal,
        establishment_id=establishment.id,
        technical_product_id=product.id,
        target_mode=TARGET_MODE_MASS,
        target_quantity=Decimal("1000"),
        idempotency_key=uuid4(),
    )
    period = _period()
    payload = run_report(db_session, principal, "executive", period)
    card = next(item for item in payload["indicators"] if item["code"] == "orders_by_status")
    assert card["by_status"]["draft"] == 1
    assert card["by_group"]["planned"] == 1
    assert card["by_group"]["completed"] == 0
    snapshot = create_snapshot(db_session, principal, "executive", period, idempotency_key=uuid4())
    opened = open_snapshot(db_session, principal, snapshot.id)
    assert opened["content_hash"] == payload["content_hash"]
    with pytest.raises(ImmutableError, match="snapshot_imutavel"):
        refuse_recalculate_snapshot(db_session, principal, snapshot.id)
    csv_text = build_csv(payload)
    assert "orders_by_status" in csv_text
    assert neutralize("=cmd") == "'=cmd"
    assert neutralize("12.5") == "12.5"


def test_isolation_and_catalog(db_session: Session) -> None:
    org_a = helpers.org(db_session, "org-rep-a")
    org_b = helpers.org(db_session, "org-rep-b")
    actor_a = helpers.user(db_session, "rep-a@example.com")
    actor_b = helpers.user(db_session, "rep-b@example.com")
    helpers.membership(db_session, org_a, actor_a, "owner")
    helpers.membership(db_session, org_b, actor_b, "baker_operator")
    pa = helpers.principal_for(actor_a, org_a, "owner")
    pb = helpers.principal_for(actor_b, org_b, "baker_operator")
    codes_a = {item["code"] for item in authorized_catalog(pa)}
    codes_b = {item["code"] for item in authorized_catalog(pb)}
    assert "executive" in codes_a
    assert "costing" in codes_a
    assert "executive" not in codes_b
    assert "costing" not in codes_b
    assert "production" in codes_b


def test_http_catalog_snapshot_and_baker(engine) -> None:
    owner = _setup(engine, "rep-http")
    baker = _setup(engine, "rep-bak", role="baker_operator", fake=owner["fake"], client=owner["client"])
    catalog = owner["client"].get(_base(owner, "/reporting/catalog"), headers=_h(owner))
    assert catalog.status_code == 200, catalog.text
    assert any(item["code"] == "executive" for item in catalog.json()["items"])
    report = owner["client"].get(
        _base(owner, "/reporting/reports/executive"),
        headers=_h(owner),
        params=_period(),
    )
    assert report.status_code == 200, report.text
    assert report.json()["data"]["not_realtime"] is True
    snapshot = owner["client"].post(
        _base(owner, "/reporting/snapshots?report_code=executive"),
        headers=_h(owner, key=uuid4()),
        json=_period(),
    )
    assert snapshot.status_code == 200, snapshot.text
    snap_id = snapshot.json()["data"]["id"]
    denied = owner["client"].post(
        _base(owner, f"/reporting/snapshots/{snap_id}/recalculate"),
        headers=_h(owner),
    )
    assert denied.status_code == 409
    export = owner["client"].get(
        _base(owner, f"/reporting/snapshots/{snap_id}/export.csv"),
        headers=_h(owner, key=uuid4()),
    )
    assert export.status_code == 200
    assert "text/csv" in export.headers["content-type"]
    hidden = baker["client"].get(_base(baker, "/reporting/reports/costing"), headers=_h(baker))
    assert hidden.status_code == 403
    other = baker["client"].get(_base(baker, f"/reporting/snapshots/{snap_id}"), headers=_h(baker))
    assert other.status_code in {403, 404}
    invalid = owner["client"].get(
        _base(owner, "/reporting/reports/executive"),
        headers=_h(owner),
        params={"order_by": "drop_table"},
    )
    assert invalid.status_code == 422
    replay_key = uuid4()
    replay_body = _period()
    first = owner["client"].post(
        _base(owner, "/reporting/snapshots?report_code=production"),
        headers=_h(owner, key=replay_key),
        json=replay_body,
    )
    second = owner["client"].post(
        _base(owner, "/reporting/snapshots?report_code=production"),
        headers=_h(owner, key=replay_key),
        json=replay_body,
    )
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["data"]["id"] == second.json()["data"]["id"]
    _cleanup(owner["admin"])
    _cleanup(baker["admin"])


def test_timezone_half_open_and_cache_isolation(db_session: Session) -> None:
    from zoneinfo import ZoneInfo

    organization = helpers.org(db_session, "org-rep-tz")
    other = helpers.org(db_session, "org-rep-tz-b")
    establishment = helpers.establishment(db_session, organization, "E-TZ")
    actor = helpers.user(db_session, "rep-tz@example.com")
    other_actor = helpers.user(db_session, "rep-tz-b@example.com")
    helpers.membership(db_session, organization, actor, "owner")
    helpers.membership(db_session, other, other_actor, "owner")
    principal = helpers.principal_for(actor, organization, "owner")
    other_principal = helpers.principal_for(other_actor, other, "owner")
    product = helpers.technical_product(db_session, organization, "PAO-TZ")
    helpers.ensure_published_recipe(db_session, product, actor)
    zone = ZoneInfo("America/Sao_Paulo")
    start = datetime(2026, 8, 17, 0, 0, tzinfo=zone)
    end = datetime(2026, 8, 24, 0, 0, tzinfo=zone)
    create_order(
        db_session,
        principal,
        establishment_id=establishment.id,
        technical_product_id=product.id,
        target_mode=TARGET_MODE_MASS,
        target_quantity=Decimal("10"),
        planned_start_at=start,
        idempotency_key=uuid4(),
    )
    create_order(
        db_session,
        principal,
        establishment_id=establishment.id,
        technical_product_id=product.id,
        target_mode=TARGET_MODE_MASS,
        target_quantity=Decimal("20"),
        planned_start_at=end,
        idempotency_key=uuid4(),
    )
    filters = {
        "period_start": start.isoformat(),
        "period_end": end.isoformat(),
        "timezone": "America/Sao_Paulo",
    }
    payload = run_report(db_session, principal, "production", filters)
    card = next(item for item in payload["indicators"] if item["code"] == "orders_by_status")
    assert card["value"] == "1"
    detail = run_drill_down(db_session, principal, "production", "orders_by_status", filters)
    assert detail["reconciled"] is True
    assert len(detail["rows"]) == 1
    other_payload = run_report(db_session, other_principal, "production", filters)
    other_card = next(item for item in other_payload["indicators"] if item["code"] == "orders_by_status")
    assert other_card["status"] == "unavailable"
    assert payload["content_hash"] != other_payload["content_hash"]


def test_csv_absence_and_formula_guard() -> None:
    csv_text = build_csv(
        {
            "report_code": "production",
            "report_version": "1",
            "content_hash": "abc",
            "data_cutoff_at": "2026-08-24T12:00:00+00:00",
            "period_start": "2026-08-17T00:00:00-03:00",
            "period_end": "2026-08-24T00:00:00-03:00",
            "timezone": "America/Sao_Paulo",
            "completeness": "partial",
            "indicators": [
                {"code": "orders_by_status", "name": "Ordens", "status": "available", "value": "0", "unit": "count", "coverage": {"universe": 1, "valid_count": 1, "missing_count": 0}},
                {"code": "yield_actual", "name": "=CMD", "status": "unavailable", "value": None, "reason": "conjunto_vazio"},
            ],
        }
    )
    assert ",0," in csv_text or csv_text.splitlines()[-2].endswith("0") or "\norders_by_status,Ordens,available,0," in csv_text
    assert "'=CMD" in csv_text
    assert "yield_actual,'=CMD,unavailable,," in csv_text or "unavailable,," in csv_text


def test_weighted_average_and_incompatible_units() -> None:
    from app.modules.reporting_analytics.formulas import weighted_average

    assert weighted_average([]) is None
    assert weighted_average([(Decimal("10"), Decimal("0"))]) is None
    assert weighted_average([(Decimal("10"), Decimal("1")), (Decimal("20"), Decimal("3"))]) == Decimal("17.500000")
    with pytest.raises(ValidationError, match="filtro_invalido"):
        normalize_filters({"timezone": "Not/AZone"})

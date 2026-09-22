from uuid import uuid4

from app.modules.identity_organization.access_tokens import FakeAccessTokenVerifier
from sqlalchemy.orm import sessionmaker
from tests import helpers
from tests.jwt_support import ISSUER
from tests.test_production_api import _cleanup, _client, _headers


def _setup(engine, slug_prefix: str, role: str = "owner", fake=None, client=None):
    fake = fake or FakeAccessTokenVerifier()
    admin = sessionmaker(bind=engine, future=True, expire_on_commit=False)()
    slug = f"{slug_prefix}-{uuid4().hex[:6]}"
    organization = helpers.org(admin, slug)
    helpers.establishment(admin, organization, "LOJA")
    actor = helpers.user(admin, f"{slug}@example.com")
    helpers.membership(admin, organization, actor, role)
    subject = f"sub-{slug}"
    helpers.auth_identity(admin, actor, ISSUER, subject)
    admin.commit()
    token = f"token-{slug}"
    fake.register(token, issuer=ISSUER, subject=subject)
    if client is None:
        client = _client(engine, fake)
    return {
        "client": client,
        "admin": admin,
        "organization": organization,
        "actor": actor,
        "token": token,
        "fake": fake,
    }


def _h(ctx):
    return _headers(ctx["token"], ctx["organization"].id)


def _base(ctx) -> str:
    return f"/api/v1/organizations/{ctx['organization'].id}/dashboard/today"


def test_today_empty_org_does_not_invent_zero(engine):
    ctx = _setup(engine, "dash-empty")
    try:
        response = ctx["client"].get(_base(ctx), headers=_h(ctx))
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["organization"]["name"]
        assert body["timezone"] == "America/Sao_Paulo"
        assert body["permissions"]["economy"] is True
        assert body["business"] is not None
        assert body["yesterday"]["produced"]["empty"] is True
        assert body["yesterday"]["orders_completed"]["empty"] is True
        assert body["attentions"] == []
        assert body["business"]["margin"] is None
        assert body["business"]["cost_coverage"]["available"] is False
        assert body["charts"]["production"]["available"] is False
        assert body["charts"]["movements"]["available"] is False
        assert body["charts"]["costs"]["available"] is False
        assert "zero" not in body["charts"]["production"]["empty_title"].lower()
        assert "uuid" not in str(body).lower()
    finally:
        _cleanup(ctx["client"])
        ctx["admin"].close()


def test_today_hides_economy_without_costing(engine):
    baker = _setup(engine, "dash-bak", "baker_operator")
    try:
        response = baker["client"].get(_base(baker), headers=_h(baker))
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["permissions"]["economy"] is False
        assert body["business"] is None
        assert body["charts"]["costs"] is None
        assert body["charts"]["prices"] is None
    finally:
        _cleanup(baker["client"])
        baker["admin"].close()


def test_today_rejects_unknown_period(engine):
    ctx = _setup(engine, "dash-period")
    try:
        response = ctx["client"].get(f"{_base(ctx)}?period=semana", headers=_h(ctx))
        assert response.status_code == 422
    finally:
        _cleanup(ctx["client"])
        ctx["admin"].close()


def test_today_rejects_other_organization(engine):
    fake = FakeAccessTokenVerifier()
    owner = _setup(engine, "dash-own", "owner", fake=fake)
    other = _setup(engine, "dash-oth", "owner", fake=fake, client=owner["client"])
    try:
        response = owner["client"].get(
            f"/api/v1/organizations/{other['organization'].id}/dashboard/today",
            headers=_headers(owner["token"], owner["organization"].id),
        )
        assert response.status_code == 403
    finally:
        _cleanup(owner["client"])
        owner["admin"].close()
        other["admin"].close()


def test_agenda_and_running_kpi_respect_period_window(engine):
    from datetime import date, datetime, time, timedelta
    from decimal import Decimal
    from zoneinfo import ZoneInfo

    from sqlalchemy import select

    from app.modules.identity_organization.models import Establishment
    from app.modules.inventory_procurement.operational_date import OPERATIONAL_TIMEZONE
    from app.modules.production_planning.constants import (
        ORDER_STATUS_IN_PROGRESS,
        ORDER_STATUS_RELEASED,
    )
    from app.modules.production_planning.models import ProductionOrder, ProductionPlan

    ctx = _setup(engine, "dash-win")
    try:
        first = ctx["client"].get(_base(ctx), headers=_h(ctx))
        assert first.status_code == 200, first.text
        today = date.fromisoformat(first.json()["operational_date"])
        yesterday = today - timedelta(days=1)
        tomorrow = today + timedelta(days=1)
        admin = ctx["admin"]
        org = ctx["organization"]
        actor = ctx["actor"]
        est = admin.execute(select(Establishment).where(Establishment.organization_id == org.id)).scalar_one()
        product = helpers.technical_product(admin, org, "PAO-WIN")
        zone = ZoneInfo(OPERATIONAL_TIMEZONE)

        def add_order(code: str, day: date, status: str, shift: str, with_start: bool) -> None:
            plan = ProductionPlan(
                organization_id=org.id,
                establishment_id=est.id,
                public_code=f"PL-{code}",
                operational_date=day,
                shift=shift,
                status="scheduled",
                created_by_user_id=actor.id,
            )
            admin.add(plan)
            admin.flush()
            order = ProductionOrder(
                organization_id=org.id,
                establishment_id=est.id,
                public_code=code,
                plan_id=plan.id,
                technical_product_id=product.id,
                target_mode="units",
                target_quantity=Decimal("10"),
                status=status,
                created_by_user_id=actor.id,
                planned_start_at=datetime.combine(day, time(6, 0), tzinfo=zone) if with_start else None,
            )
            admin.add(order)

        add_order("ORD-HOJE", today, ORDER_STATUS_IN_PROGRESS, "morning", False)
        add_order("ORD-ONTEM", yesterday, ORDER_STATUS_RELEASED, "afternoon", True)
        add_order("ORD-AMANHA", tomorrow, ORDER_STATUS_IN_PROGRESS, "night", True)
        admin.commit()

        today_body = ctx["client"].get(f"{_base(ctx)}?period=today", headers=_h(ctx)).json()
        today_labels = [row["label"] for row in today_body["charts"]["agenda"]["series"]]
        today_when = [row["when_label"] for row in today_body["charts"]["agenda"]["series"]]
        prod_labels = [row["label"] for row in today_body["charts"]["production"]["series"]]
        assert any("ORD-HOJE" in label for label in today_labels)
        assert not any("ORD-AMANHA" in label for label in today_labels)
        assert not any("ORD-ONTEM" in label for label in today_labels)
        assert today_body["today"]["orders_in_progress"]["value"] == "1"
        assert today_body["today"]["orders_in_progress"]["source"].startswith("Ordens em pesagem")
        assert "Manhã" in today_when
        assert "morning" not in " ".join(today_when)
        assert "afternoon" not in " ".join(today_when)
        assert "night" not in " ".join(today_when)
        assert any(" · ORD-HOJE" in label for label in prod_labels)
        assert today_body["charts"]["meta"]["timezone"] == "America/Sao_Paulo"
        assert "cost_coverage" in today_body["business"]

        yesterday_body = ctx["client"].get(f"{_base(ctx)}?period=yesterday", headers=_h(ctx)).json()
        y_labels = [row["label"] for row in yesterday_body["charts"]["agenda"]["series"]]
        assert any("ORD-ONTEM" in label for label in y_labels)
        assert not any("ORD-HOJE" in label for label in y_labels)
        assert not any("ORD-AMANHA" in label for label in y_labels)

        week_body = ctx["client"].get(f"{_base(ctx)}?period=last_7_days", headers=_h(ctx)).json()
        w_labels = [row["label"] for row in week_body["charts"]["agenda"]["series"]]
        assert any("ORD-HOJE" in label for label in w_labels)
        assert any("ORD-ONTEM" in label for label in w_labels)
        assert not any("ORD-AMANHA" in label for label in w_labels)
    finally:
        _cleanup(ctx["client"])
        ctx["admin"].close()

"""GATE4: testes explícitos de idempotência, concorrência, RLS, auditoria e permissões."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.modules.costing_pricing.models import PricingMarkupPolicy
from app.modules.costing_pricing.policy_resolve import resolve_markup_policy
from app.modules.costing_pricing.services import (
    activate_markup_policy,
    create_markup_policy,
    create_practiced_price,
    decide_price,
    list_economic_audit,
    list_prices,
    retire_markup_policy,
)
from app.modules.identity_organization.authorization import permissions_for_role
from app.modules.production_planning.errors import ConcurrencyError, ValidationError
from tests import helpers


def _now() -> datetime:
    return datetime(2026, 9, 1, 12, 0, tzinfo=UTC)


def test_rls_and_force_rls_on_economic_tables(db_session: Session) -> None:
    rows = {
        r[0]: (bool(r[1]), bool(r[2]))
        for r in db_session.execute(
            text(
                """
                SELECT c.relname, c.relrowsecurity, c.relforcerowsecurity
                FROM pg_class c
                JOIN pg_namespace n ON n.oid = c.relnamespace
                WHERE n.nspname = 'public'
                  AND c.relname IN ('pricing_markup_policy', 'pricing_economic_audit')
                """
            )
        )
    }
    assert rows["pricing_markup_policy"] == (True, True)
    assert rows["pricing_economic_audit"] == (True, True)
    policies = {
        r[0]
        for r in db_session.execute(
            text(
                """
                SELECT pol.polname
                FROM pg_policy pol
                JOIN pg_class c ON c.oid = pol.polrelid
                WHERE c.relname IN ('pricing_markup_policy', 'pricing_economic_audit')
                """
            )
        )
    }
    assert "rls_pricing_markup_policy_org" in policies
    assert "rls_pricing_economic_audit_org" in policies


def test_unique_active_policy_and_temporal_succession(db_session: Session) -> None:
    organization = helpers.org(db_session, "org-g4-uniq")
    actor = helpers.user(db_session, "g4-uniq@example.com")
    principal = helpers.principal_for(actor, organization, "owner")
    first = create_markup_policy(
        db_session,
        principal,
        {
            "code": "U1",
            "kind": "markup_factor",
            "value": "2",
            "scope_level": "organization",
            "valid_from": _now().isoformat(),
        },
        idempotency_key=uuid4(),
    )
    activate_markup_policy(
        db_session, principal, first["id"], expected_version=first["row_version"], idempotency_key=uuid4()
    )
    second = create_markup_policy(
        db_session,
        principal,
        {
            "code": "U2",
            "kind": "markup_factor",
            "value": "2.2",
            "scope_level": "organization",
            "valid_from": (_now() + timedelta(hours=1)).isoformat(),
        },
        idempotency_key=uuid4(),
    )
    with pytest.raises(ValidationError, match="politica_vigencia_conflito"):
        activate_markup_policy(
            db_session, principal, second["id"], expected_version=second["row_version"], idempotency_key=uuid4()
        )
    first_row = db_session.get(PricingMarkupPolicy, first["id"])
    assert first_row is not None
    retired = retire_markup_policy(
        db_session,
        principal,
        first["id"],
        expected_version=int(first_row.row_version or 1),
        idempotency_key=uuid4(),
        valid_to=(_now() + timedelta(minutes=30)).isoformat(),
        notes="substituição temporal GATE4",
    )
    assert retired["status"] == "retired"
    activated = activate_markup_policy(
        db_session, principal, second["id"], expected_version=second["row_version"], idempotency_key=uuid4()
    )
    assert activated["status"] == "active"
    active_rows = list(
        db_session.scalars(
            select(PricingMarkupPolicy).where(
                PricingMarkupPolicy.organization_id == organization.id,
                PricingMarkupPolicy.status == "active",
                PricingMarkupPolicy.scope_level == "organization",
            )
        )
    )
    assert len(active_rows) == 1
    assert str(active_rows[0].id) == activated["id"]


def test_policy_activate_idempotency_and_concurrency(db_session: Session) -> None:
    organization = helpers.org(db_session, "org-g4-idem")
    actor = helpers.user(db_session, "g4-idem@example.com")
    principal = helpers.principal_for(actor, organization, "owner")
    created = create_markup_policy(
        db_session,
        principal,
        {
            "code": "IDEM1",
            "kind": "margin_rate",
            "value": "0.25",
            "scope_level": "organization",
            "valid_from": _now().isoformat(),
        },
        idempotency_key=uuid4(),
    )
    key = uuid4()
    first = activate_markup_policy(
        db_session, principal, created["id"], expected_version=created["row_version"], idempotency_key=key
    )
    replay = activate_markup_policy(
        db_session, principal, created["id"], expected_version=created["row_version"], idempotency_key=key
    )
    assert first["id"] == replay["id"]
    assert first["row_version"] == replay["row_version"]
    with pytest.raises(ConcurrencyError, match="versao_conflito"):
        retire_markup_policy(
            db_session,
            principal,
            created["id"],
            expected_version=1,
            idempotency_key=uuid4(),
        )


def test_publish_price_idempotency_audit_snapshot(db_session: Session) -> None:
    organization = helpers.org(db_session, "org-g4-pub")
    actor = helpers.user(db_session, "g4-pub@example.com")
    principal = helpers.principal_for(actor, organization, "owner")
    product = helpers.technical_product(db_session, organization, "PROD-G4")
    unit = helpers.gram(db_session)
    draft = create_practiced_price(
        db_session,
        principal,
        {
            "technical_product_id": str(product.id),
            "channel": "own_counter",
            "amount": "12.50",
            "valid_from": _now().isoformat(),
            "justification": "GATE4-VALIDACAO publish",
            "sale_basis_quantity": "1",
            "sale_basis_unit_id": str(unit.id),
        },
        idempotency_key=uuid4(),
    )
    key = uuid4()
    first = decide_price(
        db_session,
        principal,
        draft.id,
        {"decision": "publish", "notes": "GATE4-VALIDACAO"},
        expected_version=draft.row_version,
        idempotency_key=key,
    )
    replay = decide_price(
        db_session,
        principal,
        draft.id,
        {"decision": "publish", "notes": "GATE4-VALIDACAO"},
        expected_version=draft.row_version,
        idempotency_key=key,
    )
    assert first.id == replay.id
    assert first.status == "active"
    audits = list_economic_audit(db_session, principal)
    publish_audits = [a for a in audits if a["operation"] == "pricing.decide.publish" and a["resource_id"] == str(first.id)]
    assert len(publish_audits) == 1
    snap = publish_audits[0]
    assert snap["before_state"]["status"] == "draft"
    assert snap["after_state"]["status"] == "active"
    assert Decimal(snap["after_state"]["amount"]) == Decimal("12.50")


def test_publish_concurrency_stale_version(db_session: Session) -> None:
    organization = helpers.org(db_session, "org-g4-conc")
    actor = helpers.user(db_session, "g4-conc@example.com")
    principal = helpers.principal_for(actor, organization, "owner")
    product = helpers.technical_product(db_session, organization, "PROD-CONC")
    unit = helpers.gram(db_session)
    draft = create_practiced_price(
        db_session,
        principal,
        {
            "technical_product_id": str(product.id),
            "channel": "own_counter",
            "amount": "9.90",
            "valid_from": _now().isoformat(),
            "justification": "GATE4-VALIDACAO concurrency",
            "sale_basis_quantity": "1",
            "sale_basis_unit_id": str(unit.id),
        },
        idempotency_key=uuid4(),
    )
    decide_price(
        db_session,
        principal,
        draft.id,
        {"decision": "publish", "notes": "ok"},
        expected_version=draft.row_version,
        idempotency_key=uuid4(),
    )
    with pytest.raises(ConcurrencyError, match="versao_conflito"):
        decide_price(
            db_session,
            principal,
            draft.id,
            {"decision": "retire", "notes": "stale"},
            expected_version=1,
            idempotency_key=uuid4(),
        )


def test_human_summary_and_vigency_window(db_session: Session) -> None:
    organization = helpers.org(db_session, "org-g4-hum")
    actor = helpers.user(db_session, "g4-hum@example.com")
    principal = helpers.principal_for(actor, organization, "owner")
    product = helpers.technical_product(db_session, organization, "MANTEIGA-G4")
    product.display_name = "Manteiga tablete"
    db_session.flush()
    org_pol = create_markup_policy(
        db_session,
        principal,
        {
            "code": "ORG-H",
            "kind": "markup_factor",
            "value": "2.5",
            "scope_level": "organization",
            "valid_from": _now().isoformat(),
        },
        idempotency_key=uuid4(),
    )
    activate_markup_policy(
        db_session, principal, org_pol["id"], expected_version=org_pol["row_version"], idempotency_key=uuid4()
    )
    prod_pol = create_markup_policy(
        db_session,
        principal,
        {
            "code": "PROD-H",
            "kind": "margin_rate",
            "value": "0.277",
            "scope_level": "product",
            "technical_product_id": str(product.id),
            "valid_from": _now().isoformat(),
            "valid_to": (_now() + timedelta(days=30)).isoformat(),
        },
        idempotency_key=uuid4(),
    )
    activate_markup_policy(
        db_session, principal, prod_pol["id"], expected_version=prod_pol["row_version"], idempotency_key=uuid4()
    )
    resolved = resolve_markup_policy(
        db_session, organization_id=organization.id, technical_product_id=product.id, at=_now()
    )
    assert resolved["origin_level"] == "product"
    assert "Margem" in (resolved.get("human_summary") or "")
    assert "organização" in (resolved.get("human_summary") or "").lower()
    future = resolve_markup_policy(
        db_session,
        organization_id=organization.id,
        technical_product_id=product.id,
        at=_now() + timedelta(days=40),
    )
    assert future["origin_level"] == "organization"


def test_permissions_matrix_gate4() -> None:
    owner = permissions_for_role("owner")
    viewer = permissions_for_role("viewer")
    baker = permissions_for_role("baker_operator")
    assert "pricing.policy.manage" in owner and "pricing.publish" in owner
    assert "pricing.audit.read" in owner
    assert "costing.read" in viewer
    assert "pricing.publish" not in viewer
    assert "pricing.policy.manage" not in viewer
    assert "pricing.audit.read" not in viewer
    assert "costing.read" not in baker
    assert "pricing.policy.manage" not in baker

def test_isolation_audit_after_retire(db_session: Session) -> None:
    org_a = helpers.org(db_session, "org-g4-a")
    org_b = helpers.org(db_session, "org-g4-b")
    ua = helpers.user(db_session, "g4-a@example.com")
    ub = helpers.user(db_session, "g4-b@example.com")
    pa = helpers.principal_for(ua, org_a, "owner")
    pb = helpers.principal_for(ub, org_b, "owner")
    created = create_markup_policy(
        db_session,
        pa,
        {
            "code": "ISO-A",
            "kind": "markup_factor",
            "value": "2",
            "scope_level": "organization",
            "valid_from": _now().isoformat(),
        },
        idempotency_key=uuid4(),
    )
    activate_markup_policy(
        db_session, pa, created["id"], expected_version=created["row_version"], idempotency_key=uuid4()
    )
    retire_markup_policy(
        db_session,
        pa,
        created["id"],
        expected_version=created["row_version"] + 1,
        idempotency_key=uuid4(),
    )
    audits_b = list_economic_audit(db_session, pb)
    assert all(a["resource_id"] != created["id"] for a in audits_b)
    assert (
        db_session.scalar(
            text("SELECT count(*) FROM pricing_markup_policy WHERE organization_id = :org"),
            {"org": org_b.id},
        )
        == 0
    )
    assert db_session.get(PricingMarkupPolicy, created["id"]) is not None
    assert (
        db_session.scalar(
            text(
                "SELECT count(*) FROM pricing_economic_audit WHERE organization_id = :org AND resource_id = :rid"
            ),
            {"org": org_a.id, "rid": created["id"]},
        )
        >= 1
    )


def test_create_practiced_same_key_counts_no_duplication(db_session: Session) -> None:
    organization = helpers.org(db_session, "org-g4-idem-key")
    actor = helpers.user(db_session, "g4-idem-key@example.com")
    principal = helpers.principal_for(actor, organization, "owner")
    product = helpers.technical_product(db_session, organization, "PROD-IDEM")
    unit = helpers.gram(db_session)
    body = {
        "technical_product_id": str(product.id),
        "channel": "own_counter",
        "amount": "11.90",
        "valid_from": _now().isoformat(),
        "justification": "GATE4-H1 idempotency create",
        "sale_basis_quantity": "1",
        "sale_basis_unit_id": str(unit.id),
    }
    before_prices = db_session.scalar(
        text("SELECT count(*) FROM practiced_price WHERE organization_id = :org"),
        {"org": organization.id},
    )
    before_audit = db_session.scalar(
        text("SELECT count(*) FROM pricing_economic_audit WHERE organization_id = :org"),
        {"org": organization.id},
    )
    create_key = uuid4()
    first = create_practiced_price(db_session, principal, body, idempotency_key=create_key)
    second = create_practiced_price(db_session, principal, body, idempotency_key=create_key)
    assert first.id == second.id
    after_create = db_session.scalar(
        text("SELECT count(*) FROM practiced_price WHERE organization_id = :org"),
        {"org": organization.id},
    )
    assert after_create == (before_prices or 0) + 1
    decide_key = uuid4()
    published = decide_price(
        db_session,
        principal,
        first.id,
        {"decision": "publish", "notes": "GATE4-H1 idempotency decide"},
        expected_version=first.row_version,
        idempotency_key=decide_key,
    )
    replay = decide_price(
        db_session,
        principal,
        first.id,
        {"decision": "publish", "notes": "GATE4-H1 idempotency decide"},
        expected_version=first.row_version,
        idempotency_key=decide_key,
    )
    assert published.id == replay.id
    assert published.status == "active"
    prices = list_prices(db_session, principal)
    assert len(prices) == 1
    assert prices[0].status == "active"
    assert Decimal(str(prices[0].amount)) == Decimal("11.90")
    audits = list_economic_audit(db_session, principal)
    publish_audits = [
        a
        for a in audits
        if a["operation"] == "pricing.decide.publish" and a["resource_id"] == str(published.id)
    ]
    assert len(publish_audits) == 1
    after_audit = db_session.scalar(
        text("SELECT count(*) FROM pricing_economic_audit WHERE organization_id = :org"),
        {"org": organization.id},
    )
    assert (after_audit or 0) >= (before_audit or 0) + 1

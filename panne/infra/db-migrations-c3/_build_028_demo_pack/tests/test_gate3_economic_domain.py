"""GATE3: markup policy resolution, permissions, isolation (generic, not demo SKUs)."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.costing_pricing.comparison import build_comparison, sale_basis_payload
from app.modules.costing_pricing.models import PricingMarkupPolicy
from app.modules.costing_pricing.policy_resolve import derive_from_policy, resolve_markup_policy
from app.modules.costing_pricing.services import (
    activate_markup_policy,
    create_markup_policy,
    list_economic_audit,
)
from app.modules.formula_lab.models import ProductFamily
from app.modules.identity_organization.authorization import permissions_for_role
from app.modules.production_planning.errors import ValidationError
from tests import helpers


def _now() -> datetime:
    return datetime(2026, 8, 23, 12, 0, tzinfo=UTC)


def _family(session: Session, organization, code: str) -> ProductFamily:
    row = ProductFamily(
        organization_id=organization.id,
        code=code,
        display_name=code,
        status="active",
    )
    session.add(row)
    session.flush()
    return row


def test_policy_precedence_product_over_family_over_org(db_session: Session) -> None:
    organization = helpers.org(db_session, "org-pol-prec")
    actor = helpers.user(db_session, "actor-pol@example.com")
    principal = helpers.principal_for(actor, organization, "owner")
    family = _family(db_session, organization, "FAM-X")
    product = helpers.technical_product(db_session, organization, "PROD-X")
    product.family_id = family.id
    db_session.flush()

    org_pol = create_markup_policy(
        db_session,
        principal,
        {
            "code": "ORG1",
            "kind": "markup_factor",
            "value": "2",
            "scope_level": "organization",
            "valid_from": _now().isoformat(),
        },
        idempotency_key=uuid4(),
    )
    activate_markup_policy(
        db_session, principal, org_pol["id"], expected_version=org_pol["row_version"], idempotency_key=uuid4()
    )
    fam = create_markup_policy(
        db_session,
        principal,
        {
            "code": "FAM1",
            "kind": "markup_factor",
            "value": "2.5",
            "scope_level": "family",
            "product_family_id": str(family.id),
            "valid_from": _now().isoformat(),
        },
        idempotency_key=uuid4(),
    )
    activate_markup_policy(
        db_session, principal, fam["id"], expected_version=fam["row_version"], idempotency_key=uuid4()
    )
    resolved = resolve_markup_policy(
        db_session, organization_id=organization.id, technical_product_id=product.id, at=_now()
    )
    assert resolved["origin_level"] == "family"
    prod = create_markup_policy(
        db_session,
        principal,
        {
            "code": "PROD1",
            "kind": "margin_rate",
            "value": "0.3",
            "scope_level": "product",
            "technical_product_id": str(product.id),
            "valid_from": _now().isoformat(),
        },
        idempotency_key=uuid4(),
    )
    activate_markup_policy(
        db_session, principal, prod["id"], expected_version=prod["row_version"], idempotency_key=uuid4()
    )
    resolved2 = resolve_markup_policy(
        db_session, organization_id=organization.id, technical_product_id=product.id, at=_now()
    )
    assert resolved2["origin_level"] == "product"
    assert resolved2["effective"]["kind"] == "margin_rate"


def test_policy_overlap_rejected(db_session: Session) -> None:
    organization = helpers.org(db_session, "org-pol-ov")
    actor = helpers.user(db_session, "actor-ov@example.com")
    principal = helpers.principal_for(actor, organization, "owner")
    first = create_markup_policy(
        db_session,
        principal,
        {
            "code": "O1",
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
            "code": "O2",
            "kind": "markup_factor",
            "value": "3",
            "scope_level": "organization",
            "valid_from": _now().isoformat(),
        },
        idempotency_key=uuid4(),
    )
    with pytest.raises(ValidationError, match="politica_vigencia_conflito"):
        activate_markup_policy(
            db_session, principal, second["id"], expected_version=second["row_version"], idempotency_key=uuid4()
        )


def test_derive_markup_and_margin_exclusive() -> None:
    out_m = derive_from_policy(kind="markup_factor", value=Decimal("2.5"), cost=Decimal("4"), places=2)
    assert out_m["suggested_price"] == "10.00"
    out_g = derive_from_policy(kind="margin_rate", value=Decimal("0.2"), cost=Decimal("8"), places=2)
    assert Decimal(out_g["suggested_price"]) == Decimal("10.00")


def test_mass_conversion_g_kg_in_comparison() -> None:
    sale = sale_basis_payload(
        quantity="1000",
        unit_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        unit_code="g",
        unit_display_name="grama",
    )
    cmp = build_comparison(
        price_amount="20",
        price_currency="BRL",
        sale_basis=sale,
        cost_amount="10",
        cost_currency="BRL",
        cost_basis_quantity="1",
        cost_basis_unit_id="bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
        sale_unit_dimension="mass",
        sale_unit_si_factor="0.001",
        cost_unit_dimension="mass",
        cost_unit_si_factor="1",
    )
    assert cmp["allowed"] is True
    assert cmp["conversion"] == "mass_si"
    assert Decimal(cmp["markup_factor"]) == Decimal("2")


def test_permissions_roles_economic() -> None:
    owner = permissions_for_role("owner")
    baker = permissions_for_role("baker_operator")
    viewer = permissions_for_role("viewer")
    assert "pricing.publish" in owner
    assert "pricing.policy.manage" in owner
    assert "pricing.audit.read" in owner
    assert "costing.read" not in baker
    assert "pricing.publish" not in baker
    assert "costing.read" in viewer
    assert "pricing.publish" not in viewer
    assert "pricing.policy.manage" not in viewer
    # Leitor econômico: consulta/simulação local; auditoria restrita fica com gestor/auditor.
    assert "pricing.audit.read" not in viewer
    assert "pricing.review" not in viewer
    assert "pricing.simulation.manage" not in viewer

def test_isolation_policy_and_audit_org_scoped(db_session: Session) -> None:
    org_a = helpers.org(db_session, "org-iso-a")
    org_b = helpers.org(db_session, "org-iso-b")
    user_a = helpers.user(db_session, "u-iso-a@example.com")
    user_b = helpers.user(db_session, "u-iso-b@example.com")
    pa = helpers.principal_for(user_a, org_a, "owner")
    pb = helpers.principal_for(user_b, org_b, "owner")
    created = create_markup_policy(
        db_session,
        pa,
        {
            "code": "A-ORG",
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
    product_b = helpers.technical_product(db_session, org_b, "BX")
    resolved = resolve_markup_policy(
        db_session, organization_id=org_b.id, technical_product_id=product_b.id, at=_now()
    )
    assert resolved["effective"] is None
    audits_b = list_economic_audit(db_session, pb)
    assert all(a["resource_id"] != created["id"] for a in audits_b)
    # org A still sees its policy
    assert (
        db_session.scalar(
            select(PricingMarkupPolicy).where(
                PricingMarkupPolicy.organization_id == org_a.id, PricingMarkupPolicy.code == "A-ORG"
            )
        )
        is not None
    )

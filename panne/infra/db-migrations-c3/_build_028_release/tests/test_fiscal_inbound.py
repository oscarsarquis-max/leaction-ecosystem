"""CURSOR-028-D — entrada fiscal + Fazenda preparada/desativada."""

from __future__ import annotations

import os
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from app.modules.fiscal_inbound import commands
from app.modules.fiscal_inbound.constants import DEMO_ACCESS_KEY_PREFIX, DEMO_RECIPIENT_TAX_ID
from app.modules.fiscal_inbound.distribution import (
    CertificateConfigView,
    FixtureDistributionProvider,
    NFeDistribuicaoDFe,
    fiscal_live_enabled,
    validate_certificate_config,
)
from app.modules.fiscal_inbound.xml_parser import parse_document
from app.modules.identity_organization.authorization import AuthorizationError, permissions_for_role
from app.modules.inventory_procurement.models import InventoryBalance, InventoryMovement
from app.modules.inventory_procurement.services import create_item, create_location, create_policy, publish_policy
from app.modules.production_planning.errors import InvalidStateError, ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session
from tests import helpers

FIXTURE_XML = Path(__file__).parent / "fixtures" / "fiscal" / "demo_nfe.xml"


def _ensure_head(engine) -> None:
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    config.set_main_option("script_location", str(Path(__file__).resolve().parents[1] / "alembic"))
    command.upgrade(config, "head")


@pytest.fixture(scope="module", autouse=True)
def _fiscal_schema(engine) -> None:
    _ensure_head(engine)


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


def _stock_ready(ctx):
    session, principal = ctx["session"], ctx["principal"]
    policy = create_policy(
        session,
        principal,
        {
            "code": f"POL-{uuid4().hex[:6]}",
            "effective_from": "2026-08-01T00:00:00+00:00",
            "justification": "política fiscal demo",
        },
        idempotency_key=uuid4(),
    )
    publish_policy(session, principal, policy.id, idempotency_key=uuid4(), expected_version=policy.row_version)
    location = create_location(
        session,
        principal,
        {
            "establishment_id": ctx["place"].id,
            "code": f"LOC-{uuid4().hex[:6]}",
            "display_name": "Almoxarifado",
            "kind": "warehouse",
        },
        idempotency_key=uuid4(),
    )
    item = create_item(
        session,
        principal,
        {
            "ingredient_id": ctx["ingredient"].id,
            "unit_code": "g",
            "lot_control": "required",
        },
        idempotency_key=uuid4(),
    )
    return location, item


def test_permissions_wired():
    owner = permissions_for_role("owner")
    baker = permissions_for_role("baker_operator")
    assert "fiscal.document.confirm" in owner
    assert "fiscal.price.read" in owner
    assert "fiscal.document.read" in baker
    assert "fiscal.price.read" not in baker
    assert "fiscal.integration.manage" not in baker


def test_xml_parser_rejects_xxe_and_reads_demo():
    with pytest.raises(ValidationError):
        parse_document(b'<?xml version="1.0"?><!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///etc/passwd">]><a>&xxe;</a>')
    parsed = parse_document(FIXTURE_XML.read_bytes())
    assert parsed.number == "99001"
    assert len(parsed.items) == 2
    assert parsed.access_key and parsed.access_key.startswith(DEMO_ACCESS_KEY_PREFIX)


def test_manual_import_match_physical_confirm_idempotent(db_session: Session):
    ctx = _world(db_session, f"fisc{uuid4().hex[:6]}")
    location, inv_item = _stock_ready(ctx)
    session, principal = ctx["session"], ctx["principal"]

    document = commands.create_manual(
        session,
        principal,
        {
            "establishment_id": str(ctx["place"].id),
            "supplier_name": "Moinho Demo",
            "document_number": "1001",
            "items": [
                {
                    "description": "Farinha demo",
                    "quantity": "10",
                    "unit_code": "g",
                    "gross_amount": "50",
                }
            ],
        },
        idempotency_key=uuid4(),
    )
    assert document.status == "awaiting_match"
    item = commands._items(session, ctx["organization"].id, document.id)[0]

    # Sem confirmação humana → zero movimento.
    assert session.scalar(select(InventoryMovement).limit(1)) is None

    commands.match_item(
        session,
        principal,
        document.id,
        item.id,
        {
            "target_type": "ingredient",
            "target_id": str(ctx["ingredient"].id),
            "inventory_item_id": str(inv_item.id),
            "unit_code": "g",
            "conversion_factor": "1",
        },
        idempotency_key=uuid4(),
    )
    document = commands._get_document(session, ctx["organization"].id, document.id)
    assert document.status == "awaiting_check"

    commands.record_physical(
        session,
        principal,
        document.id,
        item.id,
        {"received_quantity": "10", "unit_code": "g", "lot_code": "L1"},
        idempotency_key=uuid4(),
    )

    key = uuid4()
    confirmed = commands.confirm_document(
        session,
        principal,
        document.id,
        {"inventory_location_id": str(location.id), "force_received": True},
        idempotency_key=key,
    )
    assert confirmed.status == "received"
    movements = list(session.scalars(select(InventoryMovement)))
    assert len(movements) == 1
    balance = session.scalar(select(InventoryBalance))
    assert balance is not None
    assert Decimal(balance.physical_quantity) == Decimal("10")

    again = commands.confirm_document(
        session,
        principal,
        document.id,
        {"inventory_location_id": str(location.id), "force_received": True},
        idempotency_key=key,
    )
    assert again.id == confirmed.id
    assert len(list(session.scalars(select(InventoryMovement)))) == 1


def test_xml_import_duplicate_key(db_session: Session):
    ctx = _world(db_session, f"xml{uuid4().hex[:6]}")
    session, principal = ctx["session"], ctx["principal"]
    payload = FIXTURE_XML.read_bytes()
    first = commands.import_xml(
        session,
        principal,
        {"establishment_id": str(ctx["place"].id), "content": payload, "filename": "demo.xml", "synthetic": True},
        idempotency_key=uuid4(),
    )
    assert first.status == "awaiting_match"
    with pytest.raises(ValidationError):
        commands.import_xml(
            session,
            principal,
            {"establishment_id": str(ctx["place"].id), "content": payload, "filename": "demo.xml"},
            idempotency_key=uuid4(),
        )


def test_baker_cannot_see_prices(db_session: Session):
    ctx = _world(db_session, f"bak{uuid4().hex[:6]}", role="baker_operator")
    assert commands.can_read_prices(ctx["principal"]) is False
    with pytest.raises(AuthorizationError):
        from app.modules.identity_organization.authorization import (
            PERMISSION_FISCAL_DOCUMENT_CONFIRM,
            require_permission,
        )

        require_permission(ctx["principal"], PERMISSION_FISCAL_DOCUMENT_CONFIRM)


def test_distribution_fixtures_and_live_guard(db_session: Session):
    assert fiscal_live_enabled() is False
    fixtures = FixtureDistributionProvider()
    provider = NFeDistribuicaoDFe(fixtures=fixtures)
    result = provider.distribute(tax_id=DEMO_RECIPIENT_TAX_ID, last_nsu=None, environment="homologation")
    assert result.synthetic is True
    assert result.c_stat == "138"
    assert len(result.documents) == 2

    page2 = provider.distribute(
        tax_id=DEMO_RECIPIENT_TAX_ID, last_nsu=result.last_nsu, environment="homologation"
    )
    assert page2.c_stat == "138"
    assert len(page2.documents) == 1

    empty = provider.distribute(
        tax_id=DEMO_RECIPIENT_TAX_ID, last_nsu=page2.last_nsu, environment="homologation"
    )
    assert empty.c_stat == "137"

    fixtures.arm_temporary_failure()
    temp = provider.distribute(tax_id=DEMO_RECIPIENT_TAX_ID, last_nsu=None, environment="homologation")
    assert temp.temporary_failure is True

    key = f"{DEMO_ACCESS_KEY_PREFIX}{'1' * 40}"
    doc = provider.consult_access_key(access_key=key)
    assert doc is not None
    assert doc.label == "DEMONSTRACAO"

    view = CertificateConfigView(
        establishment_id=uuid4(),
        status="not_configured",
        tax_id=None,
        environment="homologation",
        distribution_enabled=False,
        secret_ref_present=False,
        not_before=None,
        not_after=None,
        last_consultation_at=None,
        last_nsu=None,
        diagnosis=None,
        live_global_enabled=False,
    )
    problems = validate_certificate_config(view)
    assert "certificado_nao_configurado" in problems
    assert "flag_global_desligada" in problems

    os.environ["PANNE_FISCAL_LIVE"] = "1"
    try:
        live = NFeDistribuicaoDFe(fixtures=fixtures, certificate=view)
        with pytest.raises(InvalidStateError):
            live.distribute(tax_id=DEMO_RECIPIENT_TAX_ID, last_nsu=None, environment="homologation")
    finally:
        os.environ["PANNE_FISCAL_LIVE"] = "0"


def test_org_isolation(db_session: Session):
    a = _world(db_session, f"orga{uuid4().hex[:5]}")
    b = _world(db_session, f"orgb{uuid4().hex[:5]}")
    doc = commands.create_manual(
        a["session"],
        a["principal"],
        {
            "establishment_id": str(a["place"].id),
            "supplier_name": "A",
            "document_number": "1",
            "items": [{"description": "x", "quantity": "1", "unit_code": "g"}],
        },
        idempotency_key=uuid4(),
    )
    with pytest.raises(ValidationError):
        commands._get_document(b["session"], b["organization"].id, doc.id)


def test_alembic_head_constant():
    from app.seed import ALEMBIC_HEAD

    assert ALEMBIC_HEAD == "0022_fiscal_inbound"

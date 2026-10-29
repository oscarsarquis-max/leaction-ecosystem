"""Seed incremental de entrada fiscal sintética (CURSOR-028-D). Não faz reseed integral."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.fiscal_inbound.constants import (
    DEMO_ACCESS_KEY_PREFIX,
    DEMO_EMITTER_TAX_ID,
    DEMO_LABEL,
    DEMO_RECIPIENT_TAX_ID,
    ORIGIN_MANUAL,
    ORIGIN_XML,
    STATUS_AWAITING_CHECK,
    STATUS_DIVERGENT,
    STATUS_PARTIALLY_RECEIVED,
    STATUS_RECEIVED,
)
from app.modules.fiscal_inbound.models import FiscalInboundDocument, FiscalInboundItem
from app.modules.identity_organization.models import AppUser, Establishment, Organization


def seed_fiscal_inbound_demo(session: Session, organization_id: UUID, actor_user_id: UUID) -> list[UUID]:
    """Cria documentos sintéticos se ainda não existirem (idempotente por access_key/number)."""
    place = session.scalar(
        select(Establishment)
        .where(Establishment.organization_id == organization_id)
        .order_by(Establishment.created_at)
        .limit(1)
    )
    if place is None:
        return []

    created: list[UUID] = []
    specs = [
        {
            "number": "99001",
            "access_key": f"{DEMO_ACCESS_KEY_PREFIX}{'0' * 40}",
            "status": STATUS_AWAITING_CHECK,
            "origin": ORIGIN_XML,
            "label": f"XML {DEMO_LABEL}",
        },
        {
            "number": "99002",
            "access_key": f"{DEMO_ACCESS_KEY_PREFIX}{'3' * 40}",
            "status": STATUS_PARTIALLY_RECEIVED,
            "origin": ORIGIN_MANUAL,
            "label": f"Parcial {DEMO_LABEL}",
        },
        {
            "number": "99003",
            "access_key": f"{DEMO_ACCESS_KEY_PREFIX}{'2' * 40}",
            "status": STATUS_DIVERGENT,
            "origin": ORIGIN_MANUAL,
            "label": f"Divergência {DEMO_LABEL}",
        },
        {
            "number": "99004",
            "access_key": f"{DEMO_ACCESS_KEY_PREFIX}{'1' * 40}",
            "status": STATUS_RECEIVED,
            "origin": ORIGIN_XML,
            "label": f"Concluída {DEMO_LABEL}",
        },
    ]
    for spec in specs:
        exists = session.scalar(
            select(FiscalInboundDocument).where(
                FiscalInboundDocument.organization_id == organization_id,
                FiscalInboundDocument.access_key == spec["access_key"],
            )
        )
        if exists is not None:
            continue
        document = FiscalInboundDocument(
            organization_id=organization_id,
            establishment_id=place.id,
            status=spec["status"],
            capture_origin=spec["origin"],
            access_key=spec["access_key"],
            number=spec["number"],
            series="1",
            issued_at=datetime(2026, 8, 20, 10, 0, tzinfo=UTC),
            emitter_tax_id=DEMO_EMITTER_TAX_ID,
            emitter_name=f"FORNECEDOR {DEMO_LABEL} LTDA",
            recipient_tax_id=DEMO_RECIPIENT_TAX_ID,
            recipient_name=f"PADARIA {DEMO_LABEL}",
            currency="BRL",
            totals={"vNF": "100.00", "vProd": "95.00"},
            freight=Decimal("5"),
            discount=Decimal("0"),
            distribution_label=DEMO_LABEL,
            notes=spec["label"],
            created_by=actor_user_id,
            updated_by=actor_user_id,
        )
        session.add(document)
        session.flush()
        session.add(
            FiscalInboundItem(
                organization_id=organization_id,
                fiscal_inbound_document_id=document.id,
                line_number=1,
                supplier_code="FAR-DEMO-01",
                description=f"Farinha — {DEMO_LABEL}",
                unit_code="KG",
                quantity=Decimal("25"),
                unit_price=Decimal("3.2"),
                gross_amount=Decimal("80"),
                match_status="matched" if spec["status"] != STATUS_AWAITING_CHECK else "unmatched",
            )
        )
        session.add(
            FiscalInboundItem(
                organization_id=organization_id,
                fiscal_inbound_document_id=document.id,
                line_number=2,
                supplier_code="ITEM-PENDENTE",
                description=f"Insumo pendente — {DEMO_LABEL}",
                unit_code="UN",
                quantity=Decimal("10"),
                unit_price=Decimal("1.5"),
                gross_amount=Decimal("15"),
                match_status="unmatched",
            )
        )
        created.append(document.id)
    return created


def seed_fiscal_for_demo_orgs(session: Session) -> dict:
    """Aplica seed fiscal nas orgs de demo conhecidas, se existirem."""
    report: dict[str, list[str]] = {}
    orgs = list(session.scalars(select(Organization).limit(20)))
    for org in orgs:
        actor = session.scalar(select(AppUser).limit(1))
        if actor is None:
            continue
        ids = seed_fiscal_inbound_demo(session, org.id, actor.id)
        if ids:
            report[str(org.id)] = [str(i) for i in ids]
    return report

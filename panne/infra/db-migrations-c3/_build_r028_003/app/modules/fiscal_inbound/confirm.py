"""Confirmação humana → receipt fiscal + lotes + movimentos + custo. Idempotente."""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.fiscal_inbound.constants import (
    EVENT_CONFIRMED,
    MATCH_MATCHED,
    RECEIPT_SOURCE_FISCAL,
    STATUS_AWAITING_CHECK,
    STATUS_DIVERGENT,
    STATUS_PARTIALLY_RECEIVED,
    STATUS_RECEIVED,
)
from app.modules.fiscal_inbound.costing import allocate_costs
from app.modules.fiscal_inbound.models import (
    FiscalCostAllocation,
    FiscalDocumentEvent,
    FiscalInboundDocument,
    FiscalInboundItem,
    FiscalPhysicalLine,
)
from app.modules.fiscal_inbound.states import assert_transition
from app.modules.identity_organization.authorization import (
    PERMISSION_FISCAL_DOCUMENT_CONFIRM,
    Principal,
    require_permission,
)
from app.modules.identity_organization.models import AuditEvent
from app.modules.inventory_procurement.models import (
    InventoryItem,
    InventoryLocation,
    ProcurementReceipt,
)
from app.modules.inventory_procurement.services import (
    _next_code,
    _org,
    _qty,
    _replay,
    _store_command,
    post_receipt_stock_line,
)
from app.modules.production_planning.errors import InvalidStateError, ValidationError


def confirm_receipt(
    session: Session,
    principal: Principal,
    document_id: UUID,
    body: dict,
    *,
    idempotency_key,
) -> FiscalInboundDocument:
    require_permission(principal, PERMISSION_FISCAL_DOCUMENT_CONFIRM)
    org = _org(principal)
    payload = {"document_id": str(document_id), **{k: body.get(k) for k in ("inventory_location_id",)}}
    replay = _replay(session, org, idempotency_key, "fiscal.confirm_receipt", payload)
    if replay is not None:
        return session.get(FiscalInboundDocument, replay.resource_id)

    document = session.scalar(
        select(FiscalInboundDocument).where(
            FiscalInboundDocument.id == document_id,
            FiscalInboundDocument.organization_id == org,
        )
    )
    if document is None:
        raise ValidationError("recurso_nao_encontrado")
    if document.status not in {
        STATUS_AWAITING_CHECK,
        STATUS_PARTIALLY_RECEIVED,
        STATUS_DIVERGENT,
    }:
        raise InvalidStateError("transicao_invalida")

    items = list(
        session.scalars(
            select(FiscalInboundItem).where(
                FiscalInboundItem.fiscal_inbound_document_id == document.id,
                FiscalInboundItem.organization_id == org,
            )
        )
    )
    if not items or any(item.match_status != MATCH_MATCHED for item in items):
        raise ValidationError("correspondencia_incompleta")

    physicals = list(
        session.scalars(
            select(FiscalPhysicalLine).where(
                FiscalPhysicalLine.fiscal_inbound_item_id.in_([item.id for item in items]),
                FiscalPhysicalLine.organization_id == org,
            )
        )
    )
    by_item: dict[UUID, list[FiscalPhysicalLine]] = {}
    for line in physicals:
        by_item.setdefault(line.fiscal_inbound_item_id, []).append(line)
    if any(item.id not in by_item for item in items):
        raise ValidationError("conferencia_incompleta")

    location = None
    if body.get("inventory_location_id"):
        location = session.get(InventoryLocation, body["inventory_location_id"])
    if location is None:
        location = session.scalar(
            select(InventoryLocation)
            .where(
                InventoryLocation.organization_id == org,
                InventoryLocation.establishment_id == document.establishment_id,
            )
            .order_by(InventoryLocation.created_at)
            .limit(1)
        )
    if location is None or location.organization_id != org:
        raise ValidationError("recurso_nao_encontrado")

    # Custo antes do estoque — memória fiscal separada do movimento.
    cost_lines = allocate_costs(
        lines=[
            {
                "item_id": item.id,
                "gross_amount": item.gross_amount or Decimal("0"),
                "quantity": item.converted_quantity or item.quantity,
            }
            for item in items
        ],
        freight=document.freight,
        discount=document.discount,
    )
    cost_by_item = {row["item_id"]: row for row in cost_lines}
    for item in items:
        row = cost_by_item[item.id]
        session.add(
            FiscalCostAllocation(
                organization_id=org,
                fiscal_inbound_document_id=document.id,
                fiscal_inbound_item_id=item.id,
                basis=row["basis"],
                freight_share=row["freight_share"],
                discount_share=row["discount_share"],
                other_share=row["other_share"],
                net_amount=row["net_amount"],
                unit_cost=row["unit_cost"],
                memory=row["memory"],
                algorithm_name=row["algorithm_name"],
                algorithm_version=row["algorithm_version"],
            )
        )
        item.unit_cost = row["unit_cost"]

    receipt = ProcurementReceipt(
        organization_id=org,
        public_code=_next_code(session, org, "RCP"),
        procurement_order_id=None,
        fiscal_inbound_document_id=document.id,
        source=RECEIPT_SOURCE_FISCAL,
        inventory_location_id=location.id,
        evidence_ref=body.get("evidence_ref"),
        created_by_user_id=principal.user_id,
        status="posted",
    )
    session.add(receipt)
    session.flush()

    total_invoiced = Decimal("0")
    total_received = Decimal("0")
    any_divergence = False
    for item in items:
        inv = session.get(InventoryItem, item.inventory_item_id)
        if inv is None or inv.organization_id != org:
            raise ValidationError("item_estoque_obrigatorio")
        for phys in by_item[item.id]:
            qty = _qty(phys.received_quantity)
            total_received += qty
            total_invoiced += item.converted_quantity or item.quantity
            divergence = dict(phys.divergence or {})
            if divergence:
                any_divergence = True
            post_receipt_stock_line(
                session,
                principal,
                receipt=receipt,
                location=location,
                inventory_item=inv,
                quantity=qty,
                unit_code=phys.unit_code or item.converted_unit_code or inv.unit_code,
                supplier_id=document.supplier_id,
                supplier_lot_code=phys.supplier_lot_code,
                manufactured_on=phys.manufactured_on,
                expires_on=phys.expires_on,
                observed_unit_price=item.unit_cost,
                fiscal_inbound_item_id=item.id,
                divergence=divergence,
            )

    if any_divergence or total_received < total_invoiced:
        target = STATUS_PARTIALLY_RECEIVED if total_received < total_invoiced else STATUS_DIVERGENT
        if total_received >= total_invoiced and not any_divergence:
            target = STATUS_RECEIVED
        elif total_received >= total_invoiced and any_divergence:
            target = STATUS_RECEIVED if body.get("accept_divergence") else STATUS_DIVERGENT
        elif total_received > 0 and total_received < total_invoiced:
            target = STATUS_PARTIALLY_RECEIVED
        else:
            target = STATUS_DIVERGENT
    else:
        target = STATUS_RECEIVED

    # Simplifica: se body pede confirmação plena e tudo conferido, received.
    if body.get("force_received") and total_received > 0:
        target = STATUS_RECEIVED
    if target == STATUS_DIVERGENT and body.get("accept_divergence"):
        target = STATUS_RECEIVED

    previous = document.status
    assert_transition(previous, target)
    document.status = target
    document.row_version = int(document.row_version or 1) + 1
    document.updated_by = principal.user_id

    session.add(
        FiscalDocumentEvent(
            organization_id=org,
            fiscal_inbound_document_id=document.id,
            event_type=EVENT_CONFIRMED,
            from_status=previous,
            to_status=target,
            payload={
                "receipt_id": str(receipt.id),
                "receipt_code": receipt.public_code,
                "location_id": str(location.id),
            },
            actor_user_id=principal.user_id,
            correlation_id=body.get("correlation_id"),
        )
    )
    session.add(
        AuditEvent(
            organization_id=org,
            actor_user_id=principal.user_id,
            event_type="fiscal.confirmed",
            aggregate_type="fiscal_inbound_document",
            aggregate_id=document.id,
            payload={"receipt_id": str(receipt.id), "status": target},
        )
    )
    _store_command(
        session,
        org,
        idempotency_key,
        "fiscal.confirm_receipt",
        payload,
        "fiscal_inbound_document",
        document.id,
        principal.user_id,
    )
    return document

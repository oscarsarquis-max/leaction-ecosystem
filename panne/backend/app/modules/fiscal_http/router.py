"""HTTP da entrada fiscal sob /api/v1/organizations/{organization_id}/fiscal/..."""

from __future__ import annotations

from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_runtime_session
from app.modules.fiscal_inbound import commands
from app.modules.fiscal_inbound.constants import STATUS_RECEIVED
from app.modules.fiscal_inbound.models import (
    FiscalDocumentEvent,
    FiscalInboundAttachment,
    FiscalInboundItem,
    FiscalPhysicalLine,
    FiscalCostAllocation,
)
from app.modules.fiscal_inbound.object_store import default_object_store
from app.modules.identity_organization.authorization import Principal
from app.modules.identity_organization.models import AppUser
from app.modules.inventory_procurement.models import ProcurementReceipt
from app.modules.production_http.deps import (
    get_runtime_principal,
    require_correlation_id,
    require_idempotency_key,
)
from app.modules.production_http.errors import raise_domain

router = APIRouter()


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


def _run(action):
    try:
        return action()
    except Exception as exc:
        raise_domain(exc)


def _keys(idempotency_key: str | None, x_correlation_id: str | None):
    require_correlation_id(x_correlation_id)
    return require_idempotency_key(idempotency_key)


STATUS_LABEL = {
    "draft": "Rascunho",
    "captured": "Documento recebido",
    "awaiting_xml": "Aguardando XML",
    "awaiting_match": "Aguardando correspondência",
    "awaiting_check": "Aguardando conferência",
    "partially_received": "Recebida em parte",
    "received": "Entrada confirmada",
    "divergent": "Com divergência",
    "cancelled": "Cancelada",
    "refused": "Recusada",
    "superseded": "Substituída",
}

ORIGIN_LABEL = {
    "access_key": "Chave de acesso",
    "xml": "Arquivo XML",
    "scan": "Foto ou anexo do DANFE",
    "manual": "Digitação manual",
    "distribution": "Consulta à Fazenda (simulação)",
}

EVENT_LABEL = {
    "fiscal.document.captured": "Documento capturado",
    "fiscal.document.xml_imported": "XML importado",
    "fiscal.document.scan_attached": "Anexo enviado",
    "fiscal.document.match_confirmed": "Correspondência confirmada",
    "fiscal.document.physical_recorded": "Conferência registrada",
    "fiscal.document.confirmed": "Entrada confirmada no estoque",
    "fiscal.document.cancelled": "Entrada cancelada",
    "fiscal.document.refused": "Entrada recusada",
}


def _dec(value) -> str | None:
    if value is None:
        return None
    return format(Decimal(value), "f")


def _serialize_card(session: Session, document, *, include_costs: bool) -> dict:
    items = list(
        session.scalars(
            select(FiscalInboundItem).where(
                FiscalInboundItem.fiscal_inbound_document_id == document.id
            )
        )
    )
    physical_ids = {item.id for item in items}
    checked = 0
    divergences = 0
    if physical_ids:
        lines = list(
            session.scalars(
                select(FiscalPhysicalLine).where(
                    FiscalPhysicalLine.fiscal_inbound_item_id.in_(physical_ids)
                )
            )
        )
        checked_items = {line.fiscal_inbound_item_id for line in lines}
        checked = len(checked_items)
        divergences = sum(1 for line in lines if line.divergence)
    matched = sum(1 for item in items if item.match_status == "matched")
    status = document.status
    # FE histórico usa "confirmed" como filtro; mantemos código canônico + label.
    return {
        "id": str(document.id),
        "public_code": None,
        "document_number": document.number,
        "series": document.series,
        "access_key": document.access_key,
        "issued_on": document.issued_at.date().isoformat() if document.issued_at else None,
        "status": "confirmed" if status == STATUS_RECEIVED else status,
        "status_label": STATUS_LABEL.get(status, status),
        "origin": document.capture_origin,
        "supplier": {
            "id": str(document.supplier_id) if document.supplier_id else None,
            "display_name": document.emitter_name or "Fornecedor não identificado",
            "tax_id": document.emitter_tax_id,
            "registered": document.supplier_id is not None,
        }
        if document.emitter_name or document.emitter_tax_id or document.supplier_id
        else None,
        "item_count": len(items),
        "matched_item_count": matched,
        "checked_item_count": checked,
        "divergence_count": divergences,
        "received_at": None,
        "updated_at": document.updated_at.isoformat() if document.updated_at else None,
        "document_total": _dec((document.totals or {}).get("vNF")) if include_costs else None,
        "currency": document.currency if include_costs else None,
    }


def _physical_for(session: Session, item_id: UUID) -> FiscalPhysicalLine | None:
    return session.scalar(
        select(FiscalPhysicalLine)
        .where(FiscalPhysicalLine.fiscal_inbound_item_id == item_id)
        .order_by(FiscalPhysicalLine.recorded_at.desc())
    )


def _serialize_detail(session: Session, document, principal: Principal) -> dict:
    include_costs = commands.can_read_prices(principal)
    card = _serialize_card(session, document, include_costs=include_costs)
    items = list(
        session.scalars(
            select(FiscalInboundItem)
            .where(FiscalInboundItem.fiscal_inbound_document_id == document.id)
            .order_by(FiscalInboundItem.line_number)
        )
    )
    attachments = list(
        session.scalars(
            select(FiscalInboundAttachment).where(
                FiscalInboundAttachment.fiscal_inbound_document_id == document.id
            )
        )
    )
    events = list(
        session.scalars(
            select(FiscalDocumentEvent)
            .where(FiscalDocumentEvent.fiscal_inbound_document_id == document.id)
            .order_by(FiscalDocumentEvent.created_at.desc())
        )
    )
    receipt = session.scalar(
        select(ProcurementReceipt).where(
            ProcurementReceipt.fiscal_inbound_document_id == document.id
        )
    )
    costs = None
    if include_costs:
        costs = {
            "currency": document.currency,
            "items_total": _dec((document.totals or {}).get("vProd")),
            "freight_total": _dec(document.freight),
            "discount_total": _dec(document.discount),
            "taxes_total": _dec((document.taxes or {}).get("vICMS")),
            "document_total": _dec((document.totals or {}).get("vNF")),
        }

    serialized_items = []
    for item in items:
        phys = _physical_for(session, item.id)
        actor_label = None
        if phys:
            user = session.get(AppUser, phys.recorded_by)
            actor_label = user.display_name if user else None
        cost_alloc = None
        if include_costs:
            cost_alloc = session.scalar(
                select(FiscalCostAllocation).where(
                    FiscalCostAllocation.fiscal_inbound_item_id == item.id
                )
            )
        serialized_items.append(
            {
                "id": str(item.id),
                "sequence": item.line_number,
                "supplier_description": item.description,
                "supplier_sku": item.supplier_code,
                "invoiced_quantity": _dec(item.quantity),
                "unit_code": item.unit_code,
                "match": {
                    "status": item.match_status,
                    "target_kind": item.target_type,
                    "target_id": str(item.target_id) if item.target_id else None,
                    "target_label": None,
                    "suggestion_reason": None,
                },
                "physical": {
                    "result": (phys.divergence or {}).get("result") if phys else None,
                    "received_quantity": _dec(phys.received_quantity) if phys else None,
                    "unit_code": phys.unit_code if phys else None,
                    "lot_code": phys.supplier_lot_code if phys else None,
                    "expires_on": phys.expires_on.isoformat() if phys and phys.expires_on else None,
                    "location_label": None,
                    "notes": phys.notes if phys else None,
                    "checked_at": phys.recorded_at.isoformat() if phys else None,
                    "checked_by_label": actor_label,
                }
                if phys
                else None,
                "unit_cost": _dec(cost_alloc.unit_cost if cost_alloc else item.unit_cost)
                if include_costs
                else None,
                "total_cost": _dec(cost_alloc.net_amount) if include_costs and cost_alloc else None,
            }
        )

    pending = []
    if card["matched_item_count"] < card["item_count"]:
        pending.append("Há itens sem correspondência com o cadastro da Panne.")
    if card["checked_item_count"] < card["item_count"]:
        pending.append("Há itens sem conferência física.")
    if document.status == "divergent":
        pending.append("Há divergências a resolver antes de concluir.")

    next_action = "none"
    next_label = "Nada pendente nesta entrada."
    if document.status in {"awaiting_match", "captured", "draft"}:
        next_action, next_label = "match_items", "Fazer a correspondência dos itens com o cadastro da Panne."
    elif document.status == "awaiting_check":
        next_action, next_label = "record_physical", "Registrar o que realmente chegou."
    elif document.status == "divergent":
        next_action, next_label = "resolve_divergence", "Resolver as divergências apontadas na conferência."
    elif document.status in {"awaiting_check", "partially_received"} or (
        card["checked_item_count"] == card["item_count"]
        and document.status not in {"received", "cancelled", "refused"}
        and receipt is None
    ):
        if document.status not in {"awaiting_match", "captured", "draft"}:
            next_action, next_label = "confirm_receipt", "Confirmar a entrada e atualizar o estoque."

    history = []
    for event in events:
        actor = session.get(AppUser, event.actor_user_id)
        history.append(
            {
                "id": str(event.id),
                "occurred_at": event.created_at.isoformat(),
                "action": event.event_type,
                "action_label": EVENT_LABEL.get(event.event_type, "Evento da entrada"),
                "actor_label": actor.display_name if actor else None,
                "detail": None,
            }
        )

    return {
        **card,
        "items": serialized_items,
        "attachments": [
            {
                "id": str(row.id),
                "kind": row.kind,
                "filename": row.original_filename,
                "uploaded_at": row.created_at.isoformat(),
            }
            for row in attachments
        ],
        "history": history,
        "cost_access": include_costs,
        "costs": costs,
        "storage_location_label": None,
        "stock_applied": receipt is not None,
        "stock_summary": (
            f"Estoque atualizado pelo recebimento {receipt.public_code}."
            if receipt
            else "Estoque ainda não foi atualizado por esta entrada."
        ),
        "next_action": next_action,
        "next_action_label": next_label,
        "pending_reasons": pending,
        "operational_notes": [
            note
            for note in [
                f"Documento sintético de {document.distribution_label}."
                if document.distribution_label
                else None,
                "Consulta automática à Fazenda permanece desativada."
                if document.capture_origin in {"access_key", "distribution"}
                else None,
            ]
            if note
        ],
        "row_version": document.row_version,
    }


class ManualBody(StrictModel):
    establishment_id: UUID | None = None
    supplier_id: UUID | None = None
    supplier_name: str | None = None
    supplier_tax_id: str | None = None
    document_number: str | None = None
    series: str | None = None
    issued_on: str | None = None
    notes: str | None = None
    items: list[dict] = Field(default_factory=list)
    synthetic: bool = False


class XmlBody(StrictModel):
    establishment_id: UUID | None = None
    supplier_id: UUID | None = None
    filename: str | None = None
    content: str
    synthetic: bool = False


class ScanBody(StrictModel):
    establishment_id: UUID | None = None
    filename: str | None = None
    kind: str | None = None
    content: str
    content_type: str | None = None


class AccessKeyBody(StrictModel):
    establishment_id: UUID | None = None
    access_key: str


class MatchBody(StrictModel):
    target_type: str
    target_id: UUID
    inventory_item_id: UUID | None = None
    unit_code: str | None = None
    conversion_factor: str | None = None
    persist_link: bool = True


class PhysicalBody(StrictModel):
    received_quantity: str
    unit_code: str | None = None
    lot_code: str | None = None
    supplier_lot_code: str | None = None
    manufactured_on: str | None = None
    expires_on: str | None = None
    result: str | None = None
    notes: str | None = None
    observed_unit_price: str | None = None


class ConfirmBody(StrictModel):
    inventory_location_id: UUID | None = None
    evidence_ref: str | None = None
    accept_divergence: bool = False
    force_received: bool = True


class SimulateDistBody(StrictModel):
    establishment_id: UUID | None = None
    tax_id: str | None = None
    last_nsu: str | None = None
    environment: str | None = None
    ingest: bool = False


@router.get("/fiscal/documents/summary")
def get_summary(
    organization_id: UUID,
    session: Annotated[Session, Depends(get_runtime_session)],
    principal: Annotated[Principal, Depends(get_runtime_principal)],
):
    return {"data": _run(lambda: commands.document_summary(session, principal))}


@router.get("/fiscal/documents")
def list_documents(
    organization_id: UUID,
    session: Annotated[Session, Depends(get_runtime_session)],
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    status: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    def action():
        rows, total = commands.list_documents(
            session, principal, status=status, limit=limit, offset=offset
        )
        include_costs = commands.can_read_prices(principal)
        return {
            "items": [_serialize_card(session, row, include_costs=include_costs) for row in rows],
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    return _run(action)


@router.get("/fiscal/documents/{document_id}")
def get_document(
    organization_id: UUID,
    document_id: UUID,
    session: Annotated[Session, Depends(get_runtime_session)],
    principal: Annotated[Principal, Depends(get_runtime_principal)],
):
    def action():
        document = commands._get_document(session, commands._org(principal), document_id)
        return {
            "data": _serialize_detail(session, document, principal),
            "row_version": document.row_version,
        }

    return _run(action)


@router.post("/fiscal/documents")
def create_manual(
    organization_id: UUID,
    body: ManualBody,
    session: Annotated[Session, Depends(get_runtime_session)],
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    x_correlation_id: Annotated[str | None, Header(alias="X-Correlation-Id")] = None,
):
    key = _keys(idempotency_key, x_correlation_id)

    def action():
        document = commands.create_manual(session, principal, body.model_dump(), idempotency_key=key)
        return {
            "data": _serialize_detail(session, document, principal),
            "row_version": document.row_version,
        }

    return _run(action)


@router.post("/fiscal/documents/import-xml")
def import_xml(
    organization_id: UUID,
    body: XmlBody,
    session: Annotated[Session, Depends(get_runtime_session)],
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    x_correlation_id: Annotated[str | None, Header(alias="X-Correlation-Id")] = None,
):
    key = _keys(idempotency_key, x_correlation_id)

    def action():
        document = commands.import_xml(session, principal, body.model_dump(), idempotency_key=key)
        return {
            "data": _serialize_detail(session, document, principal),
            "row_version": document.row_version,
        }

    return _run(action)


@router.post("/fiscal/documents/scan")
def attach_scan(
    organization_id: UUID,
    body: ScanBody,
    session: Annotated[Session, Depends(get_runtime_session)],
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    x_correlation_id: Annotated[str | None, Header(alias="X-Correlation-Id")] = None,
):
    key = _keys(idempotency_key, x_correlation_id)

    def action():
        document = commands.attach_scan(session, principal, body.model_dump(), idempotency_key=key)
        return {
            "data": _serialize_detail(session, document, principal),
            "row_version": document.row_version,
        }

    return _run(action)


@router.post("/fiscal/access-keys/lookup")
def lookup_key(
    organization_id: UUID,
    body: AccessKeyBody,
    session: Annotated[Session, Depends(get_runtime_session)],
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    x_correlation_id: Annotated[str | None, Header(alias="X-Correlation-Id")] = None,
):
    key = _keys(idempotency_key, x_correlation_id)

    def action():
        document = commands.lookup_access_key(
            session, principal, body.model_dump(), idempotency_key=key
        )
        return {
            "data": _serialize_detail(session, document, principal),
            "row_version": document.row_version,
        }

    return _run(action)


@router.post("/fiscal/distribution/simulate")
def simulate_distribution(
    organization_id: UUID,
    body: SimulateDistBody,
    session: Annotated[Session, Depends(get_runtime_session)],
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    x_correlation_id: Annotated[str | None, Header(alias="X-Correlation-Id")] = None,
):
    key = _keys(idempotency_key, x_correlation_id)

    def action():
        return {
            "data": commands.simulate_distribution_poll(
                session, principal, body.model_dump(), idempotency_key=key
            )
        }

    return _run(action)


@router.get("/fiscal/distribution/status")
def distribution_status(
    organization_id: UUID,
    establishment_id: UUID,
    session: Annotated[Session, Depends(get_runtime_session)],
    principal: Annotated[Principal, Depends(get_runtime_principal)],
):
    return {
        "data": _run(
            lambda: commands.distribution_status(session, principal, establishment_id)
        )
    }


@router.post("/fiscal/documents/{document_id}/items/{item_id}/match")
def match_item(
    organization_id: UUID,
    document_id: UUID,
    item_id: UUID,
    body: MatchBody,
    session: Annotated[Session, Depends(get_runtime_session)],
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    x_correlation_id: Annotated[str | None, Header(alias="X-Correlation-Id")] = None,
):
    key = _keys(idempotency_key, x_correlation_id)

    def action():
        document = commands.match_item(
            session,
            principal,
            document_id,
            item_id,
            body.model_dump(mode="json"),
            idempotency_key=key,
        )
        return {
            "data": _serialize_detail(session, document, principal),
            "row_version": document.row_version,
        }

    return _run(action)


@router.post("/fiscal/documents/{document_id}/items/{item_id}/physical")
def record_physical(
    organization_id: UUID,
    document_id: UUID,
    item_id: UUID,
    body: PhysicalBody,
    session: Annotated[Session, Depends(get_runtime_session)],
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    x_correlation_id: Annotated[str | None, Header(alias="X-Correlation-Id")] = None,
):
    key = _keys(idempotency_key, x_correlation_id)

    def action():
        document = commands.record_physical(
            session,
            principal,
            document_id,
            item_id,
            body.model_dump(),
            idempotency_key=key,
        )
        return {
            "data": _serialize_detail(session, document, principal),
            "row_version": document.row_version,
        }

    return _run(action)


@router.post("/fiscal/documents/{document_id}/confirm")
def confirm(
    organization_id: UUID,
    document_id: UUID,
    body: ConfirmBody,
    session: Annotated[Session, Depends(get_runtime_session)],
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    x_correlation_id: Annotated[str | None, Header(alias="X-Correlation-Id")] = None,
):
    key = _keys(idempotency_key, x_correlation_id)

    def action():
        document = commands.confirm_document(
            session,
            principal,
            document_id,
            body.model_dump(mode="json"),
            idempotency_key=key,
        )
        return {
            "data": _serialize_detail(session, document, principal),
            "row_version": document.row_version,
        }

    return _run(action)


@router.get("/fiscal/documents/{document_id}/attachments/{attachment_id}")
def attachment_url(
    organization_id: UUID,
    document_id: UUID,
    attachment_id: UUID,
    session: Annotated[Session, Depends(get_runtime_session)],
    principal: Annotated[Principal, Depends(get_runtime_principal)],
):
    def action():
        commands.require_permission_read = None  # silence linters
        from app.modules.identity_organization.authorization import (
            PERMISSION_FISCAL_DOCUMENT_READ,
            require_permission,
        )

        require_permission(principal, PERMISSION_FISCAL_DOCUMENT_READ)
        org = commands._org(principal)
        attachment = session.scalar(
            select(FiscalInboundAttachment).where(
                FiscalInboundAttachment.id == attachment_id,
                FiscalInboundAttachment.organization_id == org,
                FiscalInboundAttachment.fiscal_inbound_document_id == document_id,
            )
        )
        if attachment is None:
            from app.modules.production_planning.errors import ValidationError

            raise ValidationError("recurso_nao_encontrado")
        store = default_object_store()
        # Demo: confirma existência; URL pré-assinada real virá com S3.
        exists = store.exists(attachment.storage_key)
        return {
            "data": {
                "attachment_id": str(attachment.id),
                "available": exists,
                "content_type": attachment.content_type,
                "expires_in_seconds": 300,
                "url": None,
                "message": "Anexo disponível no armazenamento privado da demo."
                if exists
                else "Anexo não encontrado no armazenamento.",
            }
        }

    return _run(action)

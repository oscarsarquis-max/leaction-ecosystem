"""Comandos de entrada fiscal. Captura/importação nunca movimentam estoque."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.fiscal_inbound.confirm import confirm_receipt
from app.modules.fiscal_inbound.constants import (
    ATTACHMENT_IMAGE,
    ATTACHMENT_PDF,
    DEMO_LABEL,
    DEMO_RECIPIENT_TAX_ID,
    EVENT_CANCELLED,
    EVENT_CAPTURED,
    EVENT_MATCH_CONFIRMED,
    EVENT_PHYSICAL_RECORDED,
    EVENT_REFUSED,
    EVENT_SCAN_ATTACHED,
    EVENT_XML_IMPORTED,
    MATCH_MATCHED,
    MAX_ITEMS_PER_DOCUMENT,
    MIME_JPEG,
    MIME_PDF,
    MIME_PNG,
    MIME_XML,
    ORIGIN_ACCESS_KEY,
    ORIGIN_DISTRIBUTION,
    ORIGIN_MANUAL,
    ORIGIN_SCAN,
    ORIGIN_XML,
    STATUS_AWAITING_CHECK,
    STATUS_AWAITING_MATCH,
    STATUS_AWAITING_XML,
    STATUS_CANCELLED,
    STATUS_CAPTURED,
    STATUS_DIVERGENT,
    STATUS_DRAFT,
    STATUS_PARTIALLY_RECEIVED,
    STATUS_RECEIVED,
    STATUS_REFUSED,
)
from app.modules.fiscal_inbound.distribution import (
    default_distribution_provider,
    establishment_distribution_ready,
    fiscal_live_enabled,
)
from app.modules.fiscal_inbound.matching import (
    all_items_matched,
    confirm_match,
    suggest_matches,
    apply_suggestion,
)
from app.modules.fiscal_inbound.models import (
    EstablishmentFiscalCertificate,
    FiscalDocumentEvent,
    FiscalInboundAttachment,
    FiscalInboundDocument,
    FiscalInboundExtraction,
    FiscalInboundItem,
    FiscalPhysicalLine,
)
from app.modules.fiscal_inbound.object_store import (
    build_key,
    default_object_store,
    kind_for,
)
from app.modules.fiscal_inbound.ocr import default_ocr_provider
from app.modules.fiscal_inbound.states import assert_mutable, assert_transition
from app.modules.fiscal_inbound.xml_parser import parse_document
from app.modules.identity_organization.authorization import (
    PERMISSION_FISCAL_DOCUMENT_CAPTURE,
    PERMISSION_FISCAL_DOCUMENT_CHECK,
    PERMISSION_FISCAL_DOCUMENT_MATCH,
    PERMISSION_FISCAL_DOCUMENT_READ,
    PERMISSION_FISCAL_PRICE_READ,
    PERMISSION_SUPPLIER_PRICE_RECORD,
    Principal,
    require_permission,
)
from app.modules.identity_organization.models import Establishment
from app.modules.inventory_procurement.services import _org, _replay, _store_command
from app.modules.production_planning.errors import InvalidStateError, ValidationError


def _now():
    return datetime.now(UTC)


def _resolve_establishment(session: Session, org: UUID, body: dict) -> UUID:
    raw = body.get("establishment_id")
    if raw:
        return UUID(str(raw))
    place = session.scalar(
        select(Establishment)
        .where(Establishment.organization_id == org)
        .order_by(Establishment.created_at)
        .limit(1)
    )
    if place is None:
        raise ValidationError("estabelecimento_obrigatorio")
    return place.id


def _get_document(session: Session, org: UUID, document_id: UUID) -> FiscalInboundDocument:
    document = session.scalar(
        select(FiscalInboundDocument).where(
            FiscalInboundDocument.id == document_id,
            FiscalInboundDocument.organization_id == org,
        )
    )
    if document is None:
        raise ValidationError("recurso_nao_encontrado")
    return document


def _items(session: Session, org: UUID, document_id: UUID) -> list[FiscalInboundItem]:
    return list(
        session.scalars(
            select(FiscalInboundItem)
            .where(
                FiscalInboundItem.fiscal_inbound_document_id == document_id,
                FiscalInboundItem.organization_id == org,
            )
            .order_by(FiscalInboundItem.line_number)
        )
    )


def _event(session, org, document_id, event_type, actor, *, from_status=None, to_status=None, payload=None):
    session.add(
        FiscalDocumentEvent(
            organization_id=org,
            fiscal_inbound_document_id=document_id,
            event_type=event_type,
            from_status=from_status,
            to_status=to_status,
            payload=payload or {},
            actor_user_id=actor,
        )
    )


def _add_items_from_parsed(session, org, document, parsed):
    if len(parsed.items) > MAX_ITEMS_PER_DOCUMENT:
        raise ValidationError("xml_itens_excedem_limite")
    for row in parsed.items:
        session.add(
            FiscalInboundItem(
                organization_id=org,
                fiscal_inbound_document_id=document.id,
                line_number=row.line_number,
                supplier_code=row.supplier_code,
                gtin=row.gtin,
                description=row.description,
                ncm=row.ncm,
                cfop=row.cfop,
                cest=row.cest,
                unit_code=row.unit_code,
                quantity=row.quantity,
                unit_price=row.unit_price,
                gross_amount=row.gross_amount,
                discount=row.discount,
                freight=row.freight,
                declared_total=row.declared_total,
                taxes=row.taxes,
            )
        )


def _apply_header(document: FiscalInboundDocument, parsed) -> None:
    document.access_key = parsed.access_key or document.access_key
    document.fiscal_model = parsed.fiscal_model
    document.number = parsed.number
    document.series = parsed.series
    document.issued_at = parsed.issued_at
    document.emitter_tax_id = parsed.emitter_tax_id
    document.emitter_name = parsed.emitter_name
    document.recipient_tax_id = parsed.recipient_tax_id
    document.recipient_name = parsed.recipient_name
    document.protocol = parsed.protocol
    document.fiscal_status = parsed.fiscal_status
    document.currency = parsed.currency
    document.totals = parsed.totals
    document.taxes = parsed.taxes
    document.freight = parsed.freight
    document.discount = parsed.discount


def can_read_prices(principal: Principal) -> bool:
    return (
        PERMISSION_FISCAL_PRICE_READ in principal.permissions
        or PERMISSION_SUPPLIER_PRICE_RECORD in principal.permissions
    )


def create_manual(
    session: Session,
    principal: Principal,
    body: dict,
    *,
    idempotency_key,
) -> FiscalInboundDocument:
    require_permission(principal, PERMISSION_FISCAL_DOCUMENT_CAPTURE)
    org = _org(principal)
    replay = _replay(session, org, idempotency_key, "fiscal.create_manual", body)
    if replay is not None:
        return session.get(FiscalInboundDocument, replay.resource_id)

    document = FiscalInboundDocument(
        organization_id=org,
        establishment_id=_resolve_establishment(session, org, body),
        supplier_id=body.get("supplier_id"),
        status=STATUS_AWAITING_MATCH if body.get("items") else STATUS_DRAFT,
        capture_origin=ORIGIN_MANUAL,
        number=body.get("document_number") or body.get("number"),
        series=body.get("series"),
        issued_at=(
            datetime.fromisoformat(body["issued_on"]).replace(tzinfo=UTC)
            if body.get("issued_on") and "T" not in str(body["issued_on"])
            else datetime.fromisoformat(body["issued_on"])
            if body.get("issued_on")
            else None
        ),
        emitter_tax_id=body.get("supplier_tax_id") or body.get("emitter_tax_id"),
        emitter_name=body.get("supplier_name") or body.get("emitter_name"),
        notes=body.get("notes"),
        distribution_label=DEMO_LABEL if body.get("synthetic") else None,
        created_by=principal.user_id,
        updated_by=principal.user_id,
    )
    session.add(document)
    session.flush()

    for index, line in enumerate(body.get("items") or [], start=1):
        session.add(
            FiscalInboundItem(
                organization_id=org,
                fiscal_inbound_document_id=document.id,
                line_number=line.get("line_number") or index,
                supplier_code=line.get("supplier_code"),
                gtin=line.get("gtin"),
                description=line["description"],
                unit_code=line.get("unit_code"),
                quantity=Decimal(str(line["quantity"])),
                unit_price=Decimal(str(line["unit_price"])) if line.get("unit_price") else None,
                gross_amount=Decimal(str(line["gross_amount"])) if line.get("gross_amount") else None,
            )
        )
    if body.get("items"):
        document.status = STATUS_AWAITING_MATCH
    _event(
        session,
        org,
        document.id,
        EVENT_CAPTURED,
        principal.user_id,
        to_status=document.status,
        payload={"origin": ORIGIN_MANUAL},
    )
    _store_command(
        session, org, idempotency_key, "fiscal.create_manual", body, "fiscal_inbound_document", document.id, principal.user_id
    )
    return document


def import_xml(
    session: Session,
    principal: Principal,
    body: dict,
    *,
    idempotency_key,
    store=None,
) -> FiscalInboundDocument:
    require_permission(principal, PERMISSION_FISCAL_DOCUMENT_CAPTURE)
    org = _org(principal)
    replay = _replay(session, org, idempotency_key, "fiscal.import_xml", {"sha": body.get("content_sha")})
    if replay is not None:
        return session.get(FiscalInboundDocument, replay.resource_id)

    raw = body["content"]
    if isinstance(raw, str):
        raw_bytes = raw.encode("utf-8")
    else:
        raw_bytes = raw
    parsed = parse_document(raw_bytes)

    if parsed.access_key:
        existing = session.scalar(
            select(FiscalInboundDocument).where(
                FiscalInboundDocument.organization_id == org,
                FiscalInboundDocument.access_key == parsed.access_key,
            )
        )
        if existing is not None:
            raise ValidationError("chave_acesso_duplicada")

    document = FiscalInboundDocument(
        organization_id=org,
        establishment_id=_resolve_establishment(session, org, body),
        supplier_id=body.get("supplier_id"),
        status=STATUS_AWAITING_MATCH,
        capture_origin=ORIGIN_XML,
        created_by=principal.user_id,
        updated_by=principal.user_id,
        distribution_label=DEMO_LABEL if body.get("synthetic") else None,
    )
    _apply_header(document, parsed)
    session.add(document)
    session.flush()
    _add_items_from_parsed(session, org, document, parsed)

    store = store or default_object_store()
    digest = __import__("hashlib").sha256(raw_bytes).hexdigest()
    key = build_key(org, document.id, digest, MIME_XML)
    stored = store.put(key, raw_bytes, content_type=MIME_XML)
    document.xml_sha256 = stored.sha256
    session.add(
        FiscalInboundAttachment(
            organization_id=org,
            fiscal_inbound_document_id=document.id,
            kind=kind_for(MIME_XML),
            content_type=MIME_XML,
            byte_size=stored.byte_size,
            sha256=stored.sha256,
            storage_key=stored.key,
            original_filename=body.get("filename"),
            created_by=principal.user_id,
        )
    )
    _event(
        session,
        org,
        document.id,
        EVENT_XML_IMPORTED,
        principal.user_id,
        to_status=STATUS_AWAITING_MATCH,
        payload={"sha256": stored.sha256, "items": len(parsed.items)},
    )
    # Sugestões automáticas (ainda exigem confirmação humana).
    session.flush()
    for item in _items(session, org, document.id):
        for suggestion in suggest_matches(
            session, organization_id=org, supplier_id=document.supplier_id, item=item
        ):
            apply_suggestion(session, item, suggestion, principal.user_id)
            break
    _store_command(
        session,
        org,
        idempotency_key,
        "fiscal.import_xml",
        {"sha": stored.sha256},
        "fiscal_inbound_document",
        document.id,
        principal.user_id,
    )
    return document


def attach_scan(
    session: Session,
    principal: Principal,
    body: dict,
    *,
    idempotency_key,
    store=None,
    ocr=None,
) -> FiscalInboundDocument:
    require_permission(principal, PERMISSION_FISCAL_DOCUMENT_CAPTURE)
    org = _org(principal)
    replay = _replay(session, org, idempotency_key, "fiscal.attach_scan", body)
    if replay is not None:
        return session.get(FiscalInboundDocument, replay.resource_id)

    content = body["content"]
    if isinstance(content, str) and content.startswith("data:"):
        import base64

        header, b64 = content.split(",", 1)
        raw = base64.b64decode(b64)
        content_type = header.split(";")[0].removeprefix("data:") or MIME_JPEG
    elif isinstance(content, str):
        raw = content.encode("utf-8")
        content_type = body.get("content_type") or MIME_PDF
    else:
        raw = content
        content_type = body.get("content_type") or MIME_JPEG

    document = FiscalInboundDocument(
        organization_id=org,
        establishment_id=_resolve_establishment(session, org, body),
        status=STATUS_CAPTURED,
        capture_origin=ORIGIN_SCAN,
        created_by=principal.user_id,
        updated_by=principal.user_id,
        distribution_label=DEMO_LABEL,
    )
    session.add(document)
    session.flush()

    store = store or default_object_store()
    digest = __import__("hashlib").sha256(raw).hexdigest()
    key = build_key(org, document.id, digest, content_type)
    stored = store.put(key, raw, content_type=content_type)
    document.attachment_sha256 = stored.sha256
    attachment = FiscalInboundAttachment(
        organization_id=org,
        fiscal_inbound_document_id=document.id,
        kind=kind_for(content_type),
        content_type=stored.content_type,
        byte_size=stored.byte_size,
        sha256=stored.sha256,
        storage_key=stored.key,
        original_filename=body.get("filename"),
        created_by=principal.user_id,
    )
    session.add(attachment)
    session.flush()

    ocr = ocr or default_ocr_provider()
    result = ocr.extract(raw, content_type=content_type)
    fields = {field.name: {"value": field.value, "confidence": format(field.confidence, "f")} for field in result.fields}
    session.add(
        FiscalInboundExtraction(
            organization_id=org,
            fiscal_inbound_document_id=document.id,
            fiscal_inbound_attachment_id=attachment.id,
            provider=result.provider,
            provider_version=result.provider_version,
            status="completed",
            confidence=result.confidence,
            fields=fields,
            created_by=principal.user_id,
        )
    )
    # Preenche cabeçalho sugestivo — confirmação humana ainda necessária.
    document.access_key = fields.get("access_key", {}).get("value")
    document.emitter_name = fields.get("emitter_name", {}).get("value")
    document.emitter_tax_id = fields.get("emitter_tax_id", {}).get("value")
    document.recipient_tax_id = fields.get("recipient_tax_id", {}).get("value")
    document.number = fields.get("number", {}).get("value")
    document.series = fields.get("series", {}).get("value")
    document.status = STATUS_AWAITING_MATCH
    if fields.get("item_1_description"):
        session.add(
            FiscalInboundItem(
                organization_id=org,
                fiscal_inbound_document_id=document.id,
                line_number=1,
                description=fields["item_1_description"]["value"],
                quantity=Decimal(fields.get("item_1_quantity", {}).get("value") or "1"),
                unit_code=fields.get("item_1_unit", {}).get("value"),
            )
        )
    _event(
        session,
        org,
        document.id,
        EVENT_SCAN_ATTACHED,
        principal.user_id,
        to_status=document.status,
        payload={"provider": result.provider, "label": result.raw_label},
    )
    _store_command(
        session, org, idempotency_key, "fiscal.attach_scan", {"sha": stored.sha256}, "fiscal_inbound_document", document.id, principal.user_id
    )
    return document


def lookup_access_key(
    session: Session,
    principal: Principal,
    body: dict,
    *,
    idempotency_key,
    provider=None,
) -> FiscalInboundDocument:
    require_permission(principal, PERMISSION_FISCAL_DOCUMENT_CAPTURE)
    org = _org(principal)
    access_key = "".join(ch for ch in body["access_key"] if ch.isdigit())
    replay = _replay(session, org, idempotency_key, "fiscal.lookup_access_key", {"access_key": access_key})
    if replay is not None:
        return session.get(FiscalInboundDocument, replay.resource_id)

    existing = session.scalar(
        select(FiscalInboundDocument).where(
            FiscalInboundDocument.organization_id == org,
            FiscalInboundDocument.access_key == access_key,
        )
    )
    if existing is not None:
        raise ValidationError("chave_acesso_duplicada")

    provider = provider or default_distribution_provider()
    dist_doc = provider.consult_access_key(access_key=access_key)
    if dist_doc is None:
        raise ValidationError("documento_nao_encontrado")

    document = FiscalInboundDocument(
        organization_id=org,
        establishment_id=_resolve_establishment(session, org, body),
        status=STATUS_AWAITING_XML if dist_doc.xml_payload is None else STATUS_AWAITING_MATCH,
        capture_origin=ORIGIN_ACCESS_KEY,
        access_key=access_key,
        nsu=dist_doc.nsu,
        distribution_source="synthetic" if not fiscal_live_enabled() else "live",
        distribution_label=dist_doc.label,
        created_by=principal.user_id,
        updated_by=principal.user_id,
    )
    session.add(document)
    session.flush()

    if dist_doc.xml_payload:
        parsed = parse_document(dist_doc.xml_payload)
        _apply_header(document, parsed)
        document.access_key = access_key
        _add_items_from_parsed(session, org, document, parsed)
        document.status = STATUS_AWAITING_MATCH
        store = default_object_store()
        digest = __import__("hashlib").sha256(dist_doc.xml_payload).hexdigest()
        key = build_key(org, document.id, digest, MIME_XML)
        stored = store.put(key, dist_doc.xml_payload, content_type=MIME_XML)
        document.xml_sha256 = stored.sha256
        session.add(
            FiscalInboundAttachment(
                organization_id=org,
                fiscal_inbound_document_id=document.id,
                kind="xml",
                content_type=MIME_XML,
                byte_size=stored.byte_size,
                sha256=stored.sha256,
                storage_key=stored.key,
                original_filename=f"{DEMO_LABEL}-{dist_doc.nsu}.xml",
                created_by=principal.user_id,
            )
        )

    _event(
        session,
        org,
        document.id,
        EVENT_CAPTURED,
        principal.user_id,
        to_status=document.status,
        payload={"origin": ORIGIN_ACCESS_KEY, "synthetic": True, "nsu": dist_doc.nsu},
    )
    _store_command(
        session,
        org,
        idempotency_key,
        "fiscal.lookup_access_key",
        {"access_key": access_key},
        "fiscal_inbound_document",
        document.id,
        principal.user_id,
    )
    return document


def simulate_distribution_poll(
    session: Session,
    principal: Principal,
    body: dict,
    *,
    idempotency_key,
    provider=None,
) -> dict:
    """Simulação explícita da consulta DistDFe — nunca rede real nesta fase."""
    require_permission(principal, PERMISSION_FISCAL_DOCUMENT_CAPTURE)
    org = _org(principal)
    provider = provider or default_distribution_provider()
    result = provider.distribute(
        tax_id=body.get("tax_id") or DEMO_RECIPIENT_TAX_ID,
        last_nsu=body.get("last_nsu"),
        environment=body.get("environment") or "homologation",
    )
    created: list[str] = []
    if result.documents and body.get("ingest"):
        for dist_doc in result.documents:
            if dist_doc.cancelled or not dist_doc.xml_payload:
                continue
            doc = import_xml(
                session,
                principal,
                {
                    "establishment_id": body["establishment_id"],
                    "content": dist_doc.xml_payload,
                    "filename": f"{DEMO_LABEL}-{dist_doc.nsu}.xml",
                    "synthetic": True,
                },
                idempotency_key=None,
            )
            doc.capture_origin = ORIGIN_DISTRIBUTION
            doc.nsu = dist_doc.nsu
            doc.distribution_source = "synthetic"
            doc.distribution_label = DEMO_LABEL
            created.append(str(doc.id))
    return {
        "c_stat": result.c_stat,
        "x_motivo": result.x_motivo,
        "max_nsu": result.max_nsu,
        "last_nsu": result.last_nsu,
        "temporary_failure": result.temporary_failure,
        "retry_after_seconds": result.retry_after_seconds,
        "synthetic": True,
        "label": DEMO_LABEL,
        "documents_ingested": created,
        "document_count": len(result.documents),
    }


def match_item(
    session: Session,
    principal: Principal,
    document_id: UUID,
    item_id: UUID,
    body: dict,
    *,
    idempotency_key,
) -> FiscalInboundDocument:
    require_permission(principal, PERMISSION_FISCAL_DOCUMENT_MATCH)
    org = _org(principal)
    payload = {"document_id": str(document_id), "item_id": str(item_id), **body}
    replay = _replay(session, org, idempotency_key, "fiscal.match_item", payload)
    if replay is not None:
        return session.get(FiscalInboundDocument, replay.resource_id)

    document = _get_document(session, org, document_id)
    assert_mutable(document.status)
    item = session.scalar(
        select(FiscalInboundItem).where(
            FiscalInboundItem.id == item_id,
            FiscalInboundItem.organization_id == org,
            FiscalInboundItem.fiscal_inbound_document_id == document_id,
        )
    )
    if item is None:
        raise ValidationError("recurso_nao_encontrado")

    confirm_match(
        session,
        item=item,
        target_type=body["target_type"],
        target_id=UUID(str(body["target_id"])),
        inventory_item_id=UUID(str(body["inventory_item_id"])) if body.get("inventory_item_id") else None,
        unit_code=body.get("unit_code"),
        conversion_factor=Decimal(str(body["conversion_factor"])) if body.get("conversion_factor") else None,
        actor_user_id=principal.user_id,
        supplier_id=document.supplier_id,
        persist_link=bool(body.get("persist_link", True)),
    )
    items = _items(session, org, document.id)
    previous = document.status
    if all_items_matched(items) and document.status in {STATUS_AWAITING_MATCH, STATUS_CAPTURED, STATUS_DRAFT}:
        assert_transition(previous, STATUS_AWAITING_CHECK)
        document.status = STATUS_AWAITING_CHECK
    document.row_version = int(document.row_version or 1) + 1
    document.updated_by = principal.user_id
    _event(
        session,
        org,
        document.id,
        EVENT_MATCH_CONFIRMED,
        principal.user_id,
        from_status=previous,
        to_status=document.status,
        payload={"item_id": str(item_id)},
    )
    _store_command(
        session, org, idempotency_key, "fiscal.match_item", payload, "fiscal_inbound_document", document.id, principal.user_id
    )
    return document


def record_physical(
    session: Session,
    principal: Principal,
    document_id: UUID,
    item_id: UUID,
    body: dict,
    *,
    idempotency_key,
) -> FiscalInboundDocument:
    require_permission(principal, PERMISSION_FISCAL_DOCUMENT_CHECK)
    org = _org(principal)
    payload = {"document_id": str(document_id), "item_id": str(item_id), **body}
    replay = _replay(session, org, idempotency_key, "fiscal.record_physical", payload)
    if replay is not None:
        return session.get(FiscalInboundDocument, replay.resource_id)

    document = _get_document(session, org, document_id)
    assert_mutable(document.status)
    item = session.scalar(
        select(FiscalInboundItem).where(
            FiscalInboundItem.id == item_id,
            FiscalInboundItem.organization_id == org,
            FiscalInboundItem.fiscal_inbound_document_id == document_id,
        )
    )
    if item is None:
        raise ValidationError("recurso_nao_encontrado")
    if item.match_status != MATCH_MATCHED:
        raise ValidationError("correspondencia_obrigatoria")

    qty = Decimal(str(body["received_quantity"]))
    expected = item.converted_quantity or item.quantity
    divergence: dict = {}
    if qty != expected:
        divergence["quantity"] = {
            "expected": format(expected, "f"),
            "received": format(qty, "f"),
        }
    if body.get("result") in {"damaged", "shortage", "excess", "missing"}:
        divergence["result"] = body["result"]
    if body.get("observed_unit_price") and item.unit_price is not None:
        observed = Decimal(str(body["observed_unit_price"]))
        if observed != item.unit_price:
            divergence["price"] = {
                "expected": format(item.unit_price, "f"),
                "observed": format(observed, "f"),
            }

    session.add(
        FiscalPhysicalLine(
            organization_id=org,
            fiscal_inbound_item_id=item.id,
            received_quantity=qty,
            unit_code=body.get("unit_code") or item.converted_unit_code or item.unit_code or "UN",
            supplier_lot_code=body.get("supplier_lot_code") or body.get("lot_code"),
            manufactured_on=datetime.fromisoformat(body["manufactured_on"]).date()
            if body.get("manufactured_on")
            else None,
            expires_on=datetime.fromisoformat(body["expires_on"]).date() if body.get("expires_on") else None,
            divergence=divergence,
            notes=body.get("notes"),
            recorded_by=principal.user_id,
        )
    )
    previous = document.status
    if divergence and document.status != STATUS_DIVERGENT:
        if document.status in {STATUS_AWAITING_CHECK, STATUS_PARTIALLY_RECEIVED}:
            assert_transition(document.status, STATUS_DIVERGENT)
            document.status = STATUS_DIVERGENT
    document.row_version = int(document.row_version or 1) + 1
    document.updated_by = principal.user_id
    _event(
        session,
        org,
        document.id,
        EVENT_PHYSICAL_RECORDED,
        principal.user_id,
        from_status=previous,
        to_status=document.status,
        payload={"item_id": str(item_id), "divergence": bool(divergence)},
    )
    _store_command(
        session,
        org,
        idempotency_key,
        "fiscal.record_physical",
        payload,
        "fiscal_inbound_document",
        document.id,
        principal.user_id,
    )
    return document


def cancel_document(session, principal, document_id, body, *, idempotency_key):
    require_permission(principal, PERMISSION_FISCAL_DOCUMENT_CAPTURE)
    org = _org(principal)
    document = _get_document(session, org, document_id)
    previous = document.status
    assert_transition(previous, STATUS_CANCELLED)
    document.status = STATUS_CANCELLED
    document.row_version = int(document.row_version or 1) + 1
    _event(session, org, document.id, EVENT_CANCELLED, principal.user_id, from_status=previous, to_status=STATUS_CANCELLED, payload=body or {})
    return document


def refuse_document(session, principal, document_id, body, *, idempotency_key):
    require_permission(principal, PERMISSION_FISCAL_DOCUMENT_CAPTURE)
    org = _org(principal)
    document = _get_document(session, org, document_id)
    previous = document.status
    assert_transition(previous, STATUS_REFUSED)
    document.status = STATUS_REFUSED
    document.row_version = int(document.row_version or 1) + 1
    _event(session, org, document.id, EVENT_REFUSED, principal.user_id, from_status=previous, to_status=STATUS_REFUSED, payload=body or {})
    return document


def list_documents(session: Session, principal: Principal, *, status: str | None = None, limit=50, offset=0):
    require_permission(principal, PERMISSION_FISCAL_DOCUMENT_READ)
    org = _org(principal)
    query = select(FiscalInboundDocument).where(FiscalInboundDocument.organization_id == org)
    if status:
        # FE usa "confirmed" para received
        mapped = STATUS_RECEIVED if status == "confirmed" else status
        query = query.where(FiscalInboundDocument.status == mapped)
    total = session.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = list(
        session.scalars(query.order_by(FiscalInboundDocument.updated_at.desc()).limit(limit).offset(offset))
    )
    return rows, int(total)


def document_summary(session: Session, principal: Principal) -> dict:
    require_permission(principal, PERMISSION_FISCAL_DOCUMENT_READ)
    org = _org(principal)
    rows = session.execute(
        select(FiscalInboundDocument.status, func.count())
        .where(FiscalInboundDocument.organization_id == org)
        .group_by(FiscalInboundDocument.status)
    ).all()
    counts = {status: count for status, count in rows}
    return {
        "total": sum(counts.values()),
        "awaiting_match": counts.get(STATUS_AWAITING_MATCH, 0),
        "awaiting_check": counts.get(STATUS_AWAITING_CHECK, 0),
        "partially_received": counts.get(STATUS_PARTIALLY_RECEIVED, 0),
        "divergent": counts.get(STATUS_DIVERGENT, 0),
        "confirmed": counts.get(STATUS_RECEIVED, 0),
    }


def distribution_status(session: Session, principal: Principal, establishment_id: UUID) -> dict:
    require_permission(principal, PERMISSION_FISCAL_DOCUMENT_READ)
    org = _org(principal)
    cert = session.scalar(
        select(EstablishmentFiscalCertificate).where(
            EstablishmentFiscalCertificate.organization_id == org,
            EstablishmentFiscalCertificate.establishment_id == establishment_id,
        )
    )
    from app.modules.fiscal_inbound.distribution import CertificateConfigView

    view = None
    if cert is not None:
        view = CertificateConfigView(
            establishment_id=establishment_id,
            status=cert.status,
            tax_id=cert.tax_id,
            environment=cert.environment,
            distribution_enabled=bool(cert.distribution_enabled),
            secret_ref_present=bool(cert.secret_ref),
            not_before=cert.not_before,
            not_after=cert.not_after,
            last_consultation_at=cert.last_consultation_at,
            last_nsu=cert.last_nsu,
            diagnosis=cert.diagnosis,
            live_global_enabled=fiscal_live_enabled(),
        )
    return establishment_distribution_ready(view)


# Re-export confirm for HTTP layer.
confirm_document = confirm_receipt

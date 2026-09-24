"""Comandos de entrada fiscal. Captura/importação nunca movimentam estoque."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
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
    EVENT_REVIEW_SAVED,
    EVENT_SCAN_ATTACHED,
    EVENT_XML_IMPORTED,
    MATCH_MATCHED,
    MAX_ITEMS_PER_DOCUMENT,
    MIME_XML,
    ORIGIN_ACCESS_KEY,
    ORIGIN_DISTRIBUTION,
    ORIGIN_MANUAL,
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
    STATUS_REVIEWED,
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
    assert_allowed_mime,
    assert_size,
    build_key,
    default_object_store,
    kind_for,
    sha256_of,
)
from app.modules.fiscal_inbound.states import assert_mutable, assert_transition
from app.modules.fiscal_inbound.xml_parser import parse_document
from app.modules.identity_organization.authorization import (
    PERMISSION_FISCAL_DOCUMENT_CAPTURE,
    PERMISSION_FISCAL_DOCUMENT_CHECK,
    PERMISSION_FISCAL_DOCUMENT_CONFIRM,
    PERMISSION_FISCAL_DOCUMENT_MATCH,
    PERMISSION_FISCAL_DOCUMENT_READ,
    PERMISSION_FISCAL_PRICE_READ,
    PERMISSION_SUPPLIER_PRICE_RECORD,
    Principal,
    require_permission,
)
from app.modules.identity_organization.models import Establishment
from app.modules.inventory_procurement.services import _org, _replay, _store_command
from app.modules.production_planning.errors import ConcurrencyError, InvalidStateError, ValidationError


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
    if body.get("synthetic"):
        raise ValidationError("documento_sintetico_proibido")
    replay = _replay(session, org, idempotency_key, "fiscal.create_manual", body)
    if replay is not None:
        return session.get(FiscalInboundDocument, replay.resource_id)

    access_key = "".join(ch for ch in str(body.get("access_key") or "") if ch.isdigit()) or None
    if access_key and len(access_key) != 44:
        raise ValidationError("chave_acesso_invalida")
    if access_key:
        existing = session.scalar(
            select(FiscalInboundDocument).where(
                FiscalInboundDocument.organization_id == org,
                FiscalInboundDocument.access_key == access_key,
            )
        )
        if existing is not None:
            raise ValidationError("chave_acesso_duplicada")

    document = FiscalInboundDocument(
        organization_id=org,
        establishment_id=_resolve_establishment(session, org, body),
        supplier_id=body.get("supplier_id"),
        status=STATUS_AWAITING_MATCH if body.get("items") else STATUS_DRAFT,
        capture_origin=ORIGIN_MANUAL,
        access_key=access_key,
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
    """Guarda foto/PDF como referência. Não lê, não preenche e não cria nota."""
    _ = ocr
    require_permission(principal, PERMISSION_FISCAL_DOCUMENT_CAPTURE)
    org = _org(principal)
    document_id = body.get("document_id")
    if not document_id:
        raise ValidationError("anexo_nao_cria_nota")

    replay = _replay(session, org, idempotency_key, "fiscal.attach_scan", body)
    if replay is not None:
        return session.get(FiscalInboundDocument, replay.resource_id)

    document = _get_document(session, org, UUID(str(document_id)))
    assert_mutable(document.status)

    content = body["content"]
    if isinstance(content, str) and content.startswith("data:"):
        import base64

        header, b64 = content.split(",", 1)
        raw = base64.b64decode(b64)
        content_type = header.split(";")[0].removeprefix("data:") or "image/jpeg"
    elif isinstance(content, str):
        raw = content.encode("utf-8")
        content_type = body.get("content_type") or "application/pdf"
    else:
        raw = content
        content_type = body.get("content_type") or "image/jpeg"

    content_type = assert_allowed_mime(content_type)
    assert_size(raw)
    kind = kind_for(content_type)
    if kind not in {ATTACHMENT_IMAGE, ATTACHMENT_PDF}:
        raise ValidationError("anexo_referencia_apenas_foto_pdf")

    digest = sha256_of(raw)
    existing = session.scalar(
        select(FiscalInboundAttachment).where(
            FiscalInboundAttachment.organization_id == org,
            FiscalInboundAttachment.fiscal_inbound_document_id == document.id,
            FiscalInboundAttachment.sha256 == digest,
        )
    )
    if existing is not None:
        _store_command(
            session,
            org,
            idempotency_key,
            "fiscal.attach_scan",
            {"sha": digest, "document_id": str(document.id)},
            "fiscal_inbound_document",
            document.id,
            principal.user_id,
        )
        return document

    store = store or default_object_store()
    key = build_key(org, document.id, digest, content_type)
    stored = store.put(key, raw, content_type=content_type)
    document.attachment_sha256 = stored.sha256
    session.add(
        FiscalInboundAttachment(
            organization_id=org,
            fiscal_inbound_document_id=document.id,
            kind=kind,
            content_type=stored.content_type,
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
        EVENT_SCAN_ATTACHED,
        principal.user_id,
        to_status=document.status,
        payload={"kind": kind, "byte_size": stored.byte_size, "extracted": False},
    )
    _store_command(
        session,
        org,
        idempotency_key,
        "fiscal.attach_scan",
        {"sha": stored.sha256, "document_id": str(document.id)},
        "fiscal_inbound_document",
        document.id,
        principal.user_id,
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
    if not fiscal_live_enabled():
        raise InvalidStateError("consulta_fiscal_nao_ativada")
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
    if body.get("ingest"):
        raise InvalidStateError("simulacao_nao_grava_documento")
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


def _positive_quantity(raw) -> Decimal:
    text = str(raw).strip().replace(",", ".")
    try:
        qty = Decimal(text)
    except InvalidOperation as exc:
        raise ValidationError("quantidade_invalida") from exc
    if not qty.is_finite() or qty <= 0:
        raise ValidationError("quantidade_invalida")
    return qty


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

    qty = _positive_quantity(body["received_quantity"])
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
        "reviewed": counts.get(STATUS_REVIEWED, 0),
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


def save_review(session: Session, principal: Principal, document_id: UUID, body: dict, *, idempotency_key):
    """Persiste a revisão humana da nota. Não cria cadastro, política, movimento, saldo nem custo."""
    if (
        PERMISSION_FISCAL_DOCUMENT_MATCH not in principal.permissions
        and PERMISSION_FISCAL_DOCUMENT_CHECK not in principal.permissions
    ):
        require_permission(principal, PERMISSION_FISCAL_DOCUMENT_MATCH)
    org = _org(principal)
    replay = _replay(session, org, idempotency_key, "fiscal.receipt.review", body)
    if replay is not None:
        return _get_document(session, org, document_id)

    document = _get_document(session, org, document_id)
    if document.status in {STATUS_RECEIVED, STATUS_PARTIALLY_RECEIVED}:
        raise ValidationError("nota_ja_lancada")
    from app.modules.inventory_procurement.models import ProcurementReceipt

    already = session.scalar(
        select(ProcurementReceipt).where(
            ProcurementReceipt.organization_id == org,
            ProcurementReceipt.fiscal_inbound_document_id == document.id,
        )
    )
    if already is not None:
        raise ValidationError("nota_ja_lancada")
    expected = body.get("expected_row_version")
    if expected is None:
        raise ValidationError("contrato_invalido")
    if int(expected) != int(document.row_version or 1):
        raise ConcurrencyError("versao_conflito")
    lines = body.get("lines")
    if not isinstance(lines, list) or not lines:
        raise ValidationError("contrato_invalido")
    known = {item.id: item for item in _items(session, org, document.id)}
    if {UUID(str(line["item_id"])) for line in lines} != set(known):
        raise ValidationError("conferencia_incompleta")
    originals = {
        item.id: (
            item.description,
            item.unit_code,
            item.quantity,
            item.unit_price,
            item.gross_amount,
        )
        for item in known.values()
    }
    for line in lines:
        item = known[UUID(str(line["item_id"]))]
        quantity = _positive_quantity(line.get("reviewed_quantity"))
        name = str(line.get("suggested_ingredient_name") or item.description or "").strip()
        if not name:
            raise ValidationError("contrato_invalido")
        ingredient_id = line.get("suggested_ingredient_id")
        item.human_review = {
            "suggested_ingredient_name": name,
            "suggested_ingredient_id": str(ingredient_id) if ingredient_id else None,
            "reviewed_quantity": format(quantity, "f"),
            "as_expected": bool(line.get("as_expected", True)),
            "issue": line.get("issue") or None,
            "notes": line.get("notes") or None,
        }
        item.row_version = int(item.row_version or 1) + 1
    for item in known.values():
        original = originals[item.id]
        if (
            item.description,
            item.unit_code,
            item.quantity,
            item.unit_price,
            item.gross_amount,
        ) != original:
            raise ValidationError("contrato_invalido")
    previous = document.status
    if previous != STATUS_REVIEWED:
        assert_transition(previous, STATUS_REVIEWED)
    document.status = STATUS_REVIEWED
    document.row_version = int(document.row_version or 1) + 1
    document.updated_by = principal.user_id
    _event(
        session,
        org,
        document.id,
        EVENT_REVIEW_SAVED,
        principal.user_id,
        from_status=previous,
        to_status=STATUS_REVIEWED,
        payload={"stock_applied": False},
    )
    _store_command(
        session,
        org,
        idempotency_key,
        "fiscal.receipt.review",
        body,
        "fiscal_inbound_document",
        document.id,
        principal.user_id,
    )
    return document


def receive_receipt(session: Session, principal: Principal, document_id: UUID, body: dict, *, idempotency_key):
    """Cria insumo, item, local, conferência e estoque na mesma transação da requisição.

    Qualquer falha propaga antes do commit: cadastro novo não permanece sem o recebimento.
    """
    from uuid import uuid4

    from app.modules.identity_organization.authorization import (
        PERMISSION_INGREDIENT_CREATE,
        PERMISSION_INVENTORY_ITEM_MANAGE,
    )
    from app.modules.ingredient_catalog.commands import create_ingredient
    from app.modules.ingredient_catalog.models import Ingredient, MeasurementUnit
    from app.modules.inventory_procurement.models import InventoryItem
    from app.modules.inventory_procurement.services import create_item, create_location, resolve_measurement_unit

    require_permission(principal, PERMISSION_FISCAL_DOCUMENT_MATCH)
    require_permission(principal, PERMISSION_FISCAL_DOCUMENT_CHECK)
    require_permission(principal, PERMISSION_FISCAL_DOCUMENT_CONFIRM)
    org = _org(principal)
    replay = _replay(session, org, idempotency_key, "fiscal.receipt.receive", body)
    if replay is not None:
        return _get_document(session, org, document_id)

    lines = body.get("lines")
    if not isinstance(lines, list) or not lines:
        raise ValidationError("contrato_invalido")
    document = _get_document(session, org, document_id)
    if document.status in {STATUS_RECEIVED, STATUS_PARTIALLY_RECEIVED}:
        raise ValidationError("nota_ja_lancada")
    if document.status != STATUS_REVIEWED:
        raise ValidationError("revisao_obrigatoria")
    known = {item.id: item for item in _items(session, org, document.id)}
    prepared = []
    for line in lines:
        item_id = UUID(str(line["item_id"]))
        if item_id not in known:
            raise ValidationError("recurso_nao_encontrado")
        ingredient_id = line.get("ingredient_id")
        new_name = str(line.get("new_ingredient_name") or "").strip()
        explicit_create = bool(line.get("create_ingredient"))
        if ingredient_id and explicit_create:
            raise ValidationError("escolha_insumo_ambigua")
        if not ingredient_id and not explicit_create:
            raise ValidationError("escolha_insumo_obrigatoria")
        if explicit_create and not new_name:
            raise ValidationError("nome_insumo_obrigatorio")
        stock_unit = str(line.get("stock_unit") or "").strip()
        if not stock_unit:
            raise ValidationError("contrato_invalido")
        stock_unit = resolve_measurement_unit(session, stock_unit).code
        prepared.append(
            {
                "item_id": item_id,
                "ingredient_id": UUID(str(ingredient_id)) if ingredient_id else None,
                "new_name": new_name,
                "invoice_unit": known[item_id].unit_code,
                "stock_unit": stock_unit,
                "factor": _positive_quantity(line.get("conversion_factor")),
                "package_content_quantity": line.get("package_content_quantity"),
                "package_content_unit": line.get("package_content_unit"),
                "received": _positive_quantity(line.get("received_quantity")),
                "result": line.get("result") or "ok",
                "supplier_lot_code": line.get("supplier_lot_code"),
                "expires_on": line.get("expires_on"),
                "notes": line.get("notes"),
            }
        )
    if {row["item_id"] for row in prepared} != set(known):
        raise ValidationError("conferencia_incompleta")
    location_id = body.get("inventory_location_id")
    new_location = str(body.get("new_location_name") or "").strip()
    if not location_id and not new_location:
        raise ValidationError("contrato_invalido")
    if not location_id and document.establishment_id is None:
        raise ValidationError("estabelecimento_obrigatorio")
    if any(row["ingredient_id"] is None for row in prepared):
        require_permission(principal, PERMISSION_INGREDIENT_CREATE)
    if not location_id:
        require_permission(principal, PERMISSION_INVENTORY_ITEM_MANAGE)

    gram = session.scalar(select(MeasurementUnit).where(MeasurementUnit.code == "g"))
    for row in prepared:
        ingredient_id = row["ingredient_id"]
        if ingredient_id is None:
            if gram is None:
                raise ValidationError("unidade incompatível")
            created = create_ingredient(
                session,
                principal,
                code=f"nf-{uuid4().hex[:12]}",
                display_name=row["new_name"],
                ingredient_type="simple",
                nutrition_basis_unit_id=gram.id,
                notes=None,
                idempotency_key=uuid4(),
            )
            ingredient_id = created.id
            row["ingredient_id"] = ingredient_id
        else:
            ingredient = session.get(Ingredient, ingredient_id)
            if ingredient is None or ingredient.organization_id != org:
                raise ValidationError("recurso_nao_encontrado")
        stock = session.scalar(
            select(InventoryItem).where(
                InventoryItem.organization_id == org,
                InventoryItem.ingredient_id == ingredient_id,
            )
        )
        if stock is None:
            require_permission(principal, PERMISSION_INVENTORY_ITEM_MANAGE)
            stock = create_item(
                session,
                principal,
                {
                    "ingredient_id": ingredient_id,
                    "unit_code": row["stock_unit"],
                    "lot_control": "optional",
                },
                idempotency_key=uuid4(),
            )
        elif stock.unit_code.casefold() != row["stock_unit"].casefold():
            raise ValidationError("unidade_incompativel")
        match_item(
            session,
            principal,
            document_id,
            row["item_id"],
            {
                "target_type": "ingredient",
                "target_id": str(ingredient_id),
                "inventory_item_id": str(stock.id),
                "unit_code": stock.unit_code,
                "conversion_factor": format(row["factor"], "f"),
            },
            idempotency_key=uuid4(),
        )
        record_physical(
            session,
            principal,
            document_id,
            row["item_id"],
            {
                "received_quantity": format(row["received"], "f"),
                "unit_code": stock.unit_code,
                "result": row["result"],
                "supplier_lot_code": row["supplier_lot_code"],
                "expires_on": row["expires_on"],
                "notes": row["notes"],
            },
            idempotency_key=uuid4(),
        )

    if not location_id:
        place = create_location(
            session,
            principal,
            {
                "establishment_id": document.establishment_id,
                "code": f"loc-{uuid4().hex[:10]}",
                "display_name": new_location,
                "kind": "warehouse",
            },
            idempotency_key=uuid4(),
        )
        location_id = place.id

    confirm_receipt(
        session,
        principal,
        document_id,
        {
            "inventory_location_id": str(location_id),
            "accept_divergence": bool(body.get("accept_divergence")),
        },
        idempotency_key=uuid4(),
    )
    from app.modules.inventory_procurement.models import InventoryLot, ProcurementReceiptItem

    for row in prepared:
        pack_qty = row.get("package_content_quantity")
        pack_unit = row.get("package_content_unit")
        invoice_unit = (row.get("invoice_unit") or "").casefold()
        stock_unit = (row.get("stock_unit") or "").casefold()
        if (not pack_qty or not pack_unit) and invoice_unit and invoice_unit != stock_unit:
            pack_qty = row["factor"]
            pack_unit = row["stock_unit"]
        if not pack_qty or not pack_unit:
            continue
        receipt_line = session.scalar(
            select(ProcurementReceiptItem).where(
                ProcurementReceiptItem.organization_id == org,
                ProcurementReceiptItem.fiscal_inbound_item_id == row["item_id"],
            )
        )
        if receipt_line is None or receipt_line.inventory_lot_id is None:
            continue
        lot = session.get(InventoryLot, receipt_line.inventory_lot_id)
        if lot is None:
            continue
        lot.package_content_quantity = pack_qty if hasattr(pack_qty, "quantize") else _positive_quantity(pack_qty)
        lot.package_content_unit = str(pack_unit)
        lot.package_content_declared_at = _now()
        lot.package_content_declared_by = principal.user_id
    _store_command(
        session,
        org,
        idempotency_key,
        "fiscal.receipt.receive",
        body,
        "fiscal_inbound_document",
        document.id,
        principal.user_id,
    )
    return _get_document(session, org, document_id)


# Re-export confirm for HTTP layer.
confirm_document = confirm_receipt

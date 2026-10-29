"""Persistência da entrada fiscal. Totais declarados nunca são recalculados."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKeyConstraint,
    Index,
    Integer,
    Numeric,
    Text,
    Uuid,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


def _uuid_pk():
    return mapped_column(Uuid, primary_key=True, server_default=text("gen_random_uuid()"))


def _created_at():
    return mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


def _updated_at():
    return mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


def _document_fk(column: str = "fiscal_inbound_document_id") -> ForeignKeyConstraint:
    return ForeignKeyConstraint(
        [column, "organization_id"],
        ["fiscal_inbound_document.id", "fiscal_inbound_document.organization_id"],
        ondelete="RESTRICT",
    )


def _item_fk(column: str = "fiscal_inbound_item_id") -> ForeignKeyConstraint:
    return ForeignKeyConstraint(
        [column, "organization_id"],
        ["fiscal_inbound_item.id", "fiscal_inbound_item.organization_id"],
        ondelete="RESTRICT",
    )


class FiscalInboundDocument(Base):
    __tablename__ = "fiscal_inbound_document"
    __table_args__ = (
        Index("uq_fiscal_inbound_document_id_org", "id", "organization_id", unique=True),
        Index(
            "uq_fiscal_inbound_document_access_key",
            "organization_id",
            "access_key",
            unique=True,
            postgresql_where=text("access_key IS NOT NULL"),
        ),
        Index("ix_fiscal_inbound_document_org_status", "organization_id", "status"),
        Index("ix_fiscal_inbound_document_org_supplier", "organization_id", "supplier_id"),
        ForeignKeyConstraint(
            ["establishment_id", "organization_id"],
            ["establishment.id", "establishment.organization_id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["supplier_id", "organization_id"],
            ["supplier.id", "supplier.organization_id"],
            ondelete="RESTRICT",
        ),
    )

    id: Mapped[UUID] = _uuid_pk()
    organization_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    establishment_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    supplier_id: Mapped[UUID | None] = mapped_column(Uuid)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="draft")
    capture_origin: Mapped[str] = mapped_column(Text, nullable=False)
    access_key: Mapped[str | None] = mapped_column(Text)
    fiscal_model: Mapped[str | None] = mapped_column(Text)
    number: Mapped[str | None] = mapped_column(Text)
    series: Mapped[str | None] = mapped_column(Text)
    issued_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    emitter_tax_id: Mapped[str | None] = mapped_column(Text)
    emitter_name: Mapped[str | None] = mapped_column(Text)
    recipient_tax_id: Mapped[str | None] = mapped_column(Text)
    recipient_name: Mapped[str | None] = mapped_column(Text)
    protocol: Mapped[str | None] = mapped_column(Text)
    fiscal_status: Mapped[str | None] = mapped_column(Text)
    currency: Mapped[str] = mapped_column(Text, nullable=False, server_default="BRL")
    totals: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    freight: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    discount: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    taxes: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    nsu: Mapped[str | None] = mapped_column(Text)
    xml_sha256: Mapped[str | None] = mapped_column(Text)
    attachment_sha256: Mapped[str | None] = mapped_column(Text)
    distribution_source: Mapped[str | None] = mapped_column(Text)
    distribution_label: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
    superseded_by_id: Mapped[UUID | None] = mapped_column(Uuid)
    row_version: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    created_by: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    updated_by: Mapped[UUID | None] = mapped_column(Uuid)
    created_at: Mapped[datetime] = _created_at()
    updated_at: Mapped[datetime] = _updated_at()


class FiscalInboundItem(Base):
    __tablename__ = "fiscal_inbound_item"
    __table_args__ = (
        Index("uq_fiscal_inbound_item_id_org", "id", "organization_id", unique=True),
        Index(
            "uq_fiscal_inbound_item_line",
            "fiscal_inbound_document_id",
            "line_number",
            unique=True,
        ),
        Index("ix_fiscal_inbound_item_match", "organization_id", "match_status"),
        _document_fk(),
    )

    id: Mapped[UUID] = _uuid_pk()
    organization_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    fiscal_inbound_document_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    line_number: Mapped[int] = mapped_column(Integer, nullable=False)
    supplier_code: Mapped[str | None] = mapped_column(Text)
    gtin: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    ncm: Mapped[str | None] = mapped_column(Text)
    cfop: Mapped[str | None] = mapped_column(Text)
    cest: Mapped[str | None] = mapped_column(Text)
    unit_code: Mapped[str | None] = mapped_column(Text)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    unit_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    gross_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    discount: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    freight: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    declared_total: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    taxes: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    match_status: Mapped[str] = mapped_column(Text, nullable=False, server_default="unmatched")
    target_type: Mapped[str | None] = mapped_column(Text)
    target_id: Mapped[UUID | None] = mapped_column(Uuid)
    inventory_item_id: Mapped[UUID | None] = mapped_column(Uuid)
    conversion_factor: Mapped[Decimal | None] = mapped_column(Numeric(28, 10))
    converted_quantity: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    converted_unit_code: Mapped[str | None] = mapped_column(Text)
    conversion_memory: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    unit_cost: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    row_version: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    created_at: Mapped[datetime] = _created_at()
    updated_at: Mapped[datetime] = _updated_at()


class FiscalInboundAttachment(Base):
    __tablename__ = "fiscal_inbound_attachment"
    __table_args__ = (
        Index("uq_fiscal_inbound_attachment_id_org", "id", "organization_id", unique=True),
        Index(
            "uq_fiscal_inbound_attachment_digest",
            "fiscal_inbound_document_id",
            "sha256",
            unique=True,
        ),
        _document_fk(),
    )

    id: Mapped[UUID] = _uuid_pk()
    organization_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    fiscal_inbound_document_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    kind: Mapped[str] = mapped_column(Text, nullable=False)
    content_type: Mapped[str] = mapped_column(Text, nullable=False)
    byte_size: Mapped[int] = mapped_column(Integer, nullable=False)
    sha256: Mapped[str] = mapped_column(Text, nullable=False)
    storage_key: Mapped[str] = mapped_column(Text, nullable=False)
    original_filename: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    created_at: Mapped[datetime] = _created_at()


class FiscalInboundExtraction(Base):
    __tablename__ = "fiscal_inbound_extraction"
    __table_args__ = (
        Index("uq_fiscal_inbound_extraction_id_org", "id", "organization_id", unique=True),
        _document_fk(),
        ForeignKeyConstraint(
            ["fiscal_inbound_attachment_id", "organization_id"],
            ["fiscal_inbound_attachment.id", "fiscal_inbound_attachment.organization_id"],
            ondelete="RESTRICT",
        ),
    )

    id: Mapped[UUID] = _uuid_pk()
    organization_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    fiscal_inbound_document_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    fiscal_inbound_attachment_id: Mapped[UUID | None] = mapped_column(Uuid)
    provider: Mapped[str] = mapped_column(Text, nullable=False)
    provider_version: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="completed")
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(6, 4))
    fields: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    error: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    created_at: Mapped[datetime] = _created_at()


class FiscalItemMatch(Base):
    __tablename__ = "fiscal_item_match"
    __table_args__ = (
        Index("uq_fiscal_item_match_id_org", "id", "organization_id", unique=True),
        Index("ix_fiscal_item_match_item", "fiscal_inbound_item_id", "decision"),
        _item_fk(),
    )

    id: Mapped[UUID] = _uuid_pk()
    organization_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    fiscal_inbound_item_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    target_type: Mapped[str] = mapped_column(Text, nullable=False)
    target_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    inventory_item_id: Mapped[UUID | None] = mapped_column(Uuid)
    unit_code: Mapped[str | None] = mapped_column(Text)
    conversion_factor: Mapped[Decimal | None] = mapped_column(Numeric(28, 10))
    score: Mapped[Decimal | None] = mapped_column(Numeric(6, 4))
    strategy: Mapped[str] = mapped_column(Text, nullable=False)
    decision: Mapped[str] = mapped_column(Text, nullable=False, server_default="suggested")
    decided_by: Mapped[UUID | None] = mapped_column(Uuid)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = _created_at()


class FiscalPhysicalLine(Base):
    __tablename__ = "fiscal_physical_line"
    __table_args__ = (
        Index("uq_fiscal_physical_line_id_org", "id", "organization_id", unique=True),
        Index("ix_fiscal_physical_line_item", "fiscal_inbound_item_id", "recorded_at"),
        _item_fk(),
    )

    id: Mapped[UUID] = _uuid_pk()
    organization_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    fiscal_inbound_item_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    received_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    unit_code: Mapped[str] = mapped_column(Text, nullable=False)
    supplier_lot_code: Mapped[str | None] = mapped_column(Text)
    manufactured_on: Mapped[date | None] = mapped_column(Date)
    expires_on: Mapped[date | None] = mapped_column(Date)
    divergence: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    notes: Mapped[str | None] = mapped_column(Text)
    recorded_by: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    created_at: Mapped[datetime] = _created_at()


class FiscalCostAllocation(Base):
    __tablename__ = "fiscal_cost_allocation"
    __table_args__ = (
        Index("uq_fiscal_cost_allocation_id_org", "id", "organization_id", unique=True),
        Index("uq_fiscal_cost_allocation_item", "fiscal_inbound_item_id", unique=True),
        _document_fk(),
        _item_fk(),
    )

    id: Mapped[UUID] = _uuid_pk()
    organization_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    fiscal_inbound_document_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    fiscal_inbound_item_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    basis: Mapped[str] = mapped_column(Text, nullable=False)
    freight_share: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False, server_default="0")
    discount_share: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False, server_default="0")
    other_share: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False, server_default="0")
    net_amount: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    memory: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    algorithm_name: Mapped[str] = mapped_column(Text, nullable=False)
    algorithm_version: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = _created_at()


class FiscalDocumentEvent(Base):
    __tablename__ = "fiscal_document_event"
    __table_args__ = (
        Index("uq_fiscal_document_event_id_org", "id", "organization_id", unique=True),
        Index("ix_fiscal_document_event_document", "fiscal_inbound_document_id", "created_at"),
        _document_fk(),
    )

    id: Mapped[UUID] = _uuid_pk()
    organization_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    fiscal_inbound_document_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    event_type: Mapped[str] = mapped_column(Text, nullable=False)
    from_status: Mapped[str | None] = mapped_column(Text)
    to_status: Mapped[str | None] = mapped_column(Text)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    actor_user_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    correlation_id: Mapped[UUID | None] = mapped_column(Uuid)
    created_at: Mapped[datetime] = _created_at()


class EstablishmentFiscalCertificate(Base):
    """Contrato de certificado. `secret_ref` aponta para o cofre; nunca guarda chave privada."""

    __tablename__ = "establishment_fiscal_certificate"
    __table_args__ = (
        Index("uq_establishment_fiscal_certificate_id_org", "id", "organization_id", unique=True),
        Index(
            "uq_establishment_fiscal_certificate_alias",
            "organization_id",
            "establishment_id",
            "alias",
            unique=True,
        ),
        ForeignKeyConstraint(
            ["establishment_id", "organization_id"],
            ["establishment.id", "establishment.organization_id"],
            ondelete="RESTRICT",
        ),
    )

    id: Mapped[UUID] = _uuid_pk()
    organization_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    establishment_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    alias: Mapped[str] = mapped_column(Text, nullable=False)
    subject_name: Mapped[str | None] = mapped_column(Text)
    tax_id: Mapped[str | None] = mapped_column(Text)
    not_before: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    not_after: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Referência ao cofre (Secrets Manager). Nunca certificado/senha em claro.
    secret_ref: Mapped[str] = mapped_column(Text, nullable=False)
    environment: Mapped[str] = mapped_column(Text, nullable=False, server_default="homologation")
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="not_configured")
    distribution_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    last_consultation_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_nsu: Mapped[str | None] = mapped_column(Text)
    diagnosis: Mapped[str | None] = mapped_column(Text)  # sanitizado; sem segredo
    row_version: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    created_by: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    created_at: Mapped[datetime] = _created_at()
    updated_at: Mapped[datetime] = _updated_at()


class SupplierItemLink(Base):
    __tablename__ = "supplier_item_link"
    __table_args__ = (
        Index("uq_supplier_item_link_id_org", "id", "organization_id", unique=True),
        Index(
            "uq_supplier_item_link_code",
            "organization_id",
            "supplier_id",
            "supplier_code",
            unique=True,
            postgresql_where=text("supplier_code IS NOT NULL"),
        ),
        Index(
            "uq_supplier_item_link_gtin",
            "organization_id",
            "supplier_id",
            "gtin",
            unique=True,
            postgresql_where=text("gtin IS NOT NULL"),
        ),
        ForeignKeyConstraint(
            ["supplier_id", "organization_id"],
            ["supplier.id", "supplier.organization_id"],
            ondelete="RESTRICT",
        ),
    )

    id: Mapped[UUID] = _uuid_pk()
    organization_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    supplier_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    supplier_code: Mapped[str | None] = mapped_column(Text)
    gtin: Mapped[str | None] = mapped_column(Text)
    target_type: Mapped[str] = mapped_column(Text, nullable=False)
    target_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    unit_code: Mapped[str | None] = mapped_column(Text)
    conversion_factor: Mapped[Decimal] = mapped_column(
        Numeric(28, 10), nullable=False, server_default="1"
    )
    confirmed_by: Mapped[UUID | None] = mapped_column(Uuid)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    row_version: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    created_at: Mapped[datetime] = _created_at()
    updated_at: Mapped[datetime] = _updated_at()

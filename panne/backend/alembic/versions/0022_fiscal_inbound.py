"""Entrada fiscal de mercadoria (NF-e/NFC-e) com conferência, amarração e custo.

Revision ID: 0022_fiscal_inbound
Revises: 0021_product_canonical
Create Date: 2026-08-31
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from app.modules.identity_organization.authorization import (
    FISCAL_PERMISSION_DEFINITIONS,
    ROLE_PERMISSIONS,
)
from sqlalchemy.dialects import postgresql

revision: str = "0022_fiscal_inbound"
down_revision: Union[str, Sequence[str], None] = "0021_product_canonical"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_CODES = {code for code, _ in FISCAL_PERMISSION_DEFINITIONS}
_ORG_EQ = "organization_id IS NOT NULL AND organization_id = panne_current_org_id()"
_RUNTIME_ROLES = ("panne_runtime", "panne_demo_runtime")

_DOCUMENT_STATUSES = (
    "draft",
    "captured",
    "awaiting_xml",
    "awaiting_match",
    "awaiting_check",
    "partially_received",
    "received",
    "divergent",
    "cancelled",
    "refused",
    "superseded",
)
_CAPTURE_ORIGINS = ("access_key", "xml", "scan", "manual", "distribution")
_TABLES = (
    "fiscal_inbound_document",
    "fiscal_inbound_item",
    "fiscal_inbound_attachment",
    "fiscal_inbound_extraction",
    "fiscal_item_match",
    "fiscal_physical_line",
    "fiscal_cost_allocation",
    "fiscal_document_event",
    "establishment_fiscal_certificate",
    "supplier_item_link",
)
_APPEND_ONLY = ("fiscal_document_event",)


def _in_list(column: str, values: Sequence[str]) -> str:
    rendered = ",".join(f"'{value}'" for value in values)
    return f"{column} IN ({rendered})"


def _uuid() -> sa.Column:
    return sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False)


def _created_at() -> sa.Column:
    return sa.Column(
        "created_at",
        sa.DateTime(timezone=True),
        server_default=sa.text("now()"),
        nullable=False,
    )


def _updated_at() -> sa.Column:
    return sa.Column(
        "updated_at",
        sa.DateTime(timezone=True),
        server_default=sa.text("now()"),
        nullable=False,
    )


def _row_version() -> sa.Column:
    return sa.Column("row_version", sa.Integer(), server_default="1", nullable=False)


def _jsonb(name: str, default: str = "'{}'::jsonb") -> sa.Column:
    return sa.Column(
        name,
        postgresql.JSONB(astext_type=sa.Text()),
        server_default=sa.text(default),
        nullable=False,
    )


def _enable_rls(table: str) -> None:
    op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
    op.execute(
        f"CREATE POLICY rls_{table}_org ON {table} FOR ALL "
        f"USING ({_ORG_EQ}) WITH CHECK ({_ORG_EQ})"
    )


def _document_fk(column: str = "fiscal_inbound_document_id", ondelete: str = "RESTRICT"):
    return sa.ForeignKeyConstraint(
        [column, "organization_id"],
        ["fiscal_inbound_document.id", "fiscal_inbound_document.organization_id"],
        ondelete=ondelete,
    )


def _item_fk(column: str = "fiscal_inbound_item_id"):
    return sa.ForeignKeyConstraint(
        [column, "organization_id"],
        ["fiscal_inbound_item.id", "fiscal_inbound_item.organization_id"],
        ondelete="RESTRICT",
    )


def _create_document() -> None:
    op.create_table(
        "fiscal_inbound_document",
        _uuid(),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("establishment_id", sa.Uuid(), nullable=False),
        sa.Column("supplier_id", sa.Uuid(), nullable=True),
        sa.Column("status", sa.Text(), server_default=sa.text("'draft'"), nullable=False),
        sa.Column("capture_origin", sa.Text(), nullable=False),
        sa.Column("access_key", sa.Text(), nullable=True),
        sa.Column("fiscal_model", sa.Text(), nullable=True),
        sa.Column("number", sa.Text(), nullable=True),
        sa.Column("series", sa.Text(), nullable=True),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("emitter_tax_id", sa.Text(), nullable=True),
        sa.Column("emitter_name", sa.Text(), nullable=True),
        sa.Column("recipient_tax_id", sa.Text(), nullable=True),
        sa.Column("recipient_name", sa.Text(), nullable=True),
        sa.Column("protocol", sa.Text(), nullable=True),
        sa.Column("fiscal_status", sa.Text(), nullable=True),
        sa.Column("currency", sa.Text(), server_default=sa.text("'BRL'"), nullable=False),
        _jsonb("totals"),
        sa.Column("freight", sa.Numeric(18, 6), nullable=True),
        sa.Column("discount", sa.Numeric(18, 6), nullable=True),
        _jsonb("taxes"),
        sa.Column("nsu", sa.Text(), nullable=True),
        sa.Column("xml_sha256", sa.Text(), nullable=True),
        sa.Column("attachment_sha256", sa.Text(), nullable=True),
        sa.Column("distribution_source", sa.Text(), nullable=True),
        sa.Column("distribution_label", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("superseded_by_id", sa.Uuid(), nullable=True),
        _row_version(),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("updated_by", sa.Uuid(), nullable=True),
        _created_at(),
        _updated_at(),
        sa.CheckConstraint(
            _in_list("status", _DOCUMENT_STATUSES), name="ck_fiscal_inbound_document_status"
        ),
        sa.CheckConstraint(
            _in_list("capture_origin", _CAPTURE_ORIGINS),
            name="ck_fiscal_inbound_document_origin",
        ),
        sa.CheckConstraint(
            "access_key IS NULL OR access_key ~ '^[0-9]{44}$'",
            name="ck_fiscal_inbound_document_access_key",
        ),
        sa.CheckConstraint("freight IS NULL OR freight >= 0", name="ck_fiscal_inbound_document_freight"),
        sa.CheckConstraint("discount IS NULL OR discount >= 0", name="ck_fiscal_inbound_document_discount"),
        sa.ForeignKeyConstraint(["organization_id"], ["organization.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["establishment_id", "organization_id"],
            ["establishment.id", "establishment.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["supplier_id", "organization_id"],
            ["supplier.id", "supplier.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(["created_by"], ["app_user.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["updated_by"], ["app_user.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_fiscal_inbound_document_id_org",
        "fiscal_inbound_document",
        ["id", "organization_id"],
        unique=True,
    )
    op.create_index(
        "uq_fiscal_inbound_document_access_key",
        "fiscal_inbound_document",
        ["organization_id", "access_key"],
        unique=True,
        postgresql_where=sa.text("access_key IS NOT NULL"),
    )
    op.create_index(
        "ix_fiscal_inbound_document_org_status",
        "fiscal_inbound_document",
        ["organization_id", "status"],
    )
    op.create_index(
        "ix_fiscal_inbound_document_org_supplier",
        "fiscal_inbound_document",
        ["organization_id", "supplier_id"],
    )
    op.create_foreign_key(
        "fk_fiscal_inbound_document_superseded_by",
        "fiscal_inbound_document",
        "fiscal_inbound_document",
        ["superseded_by_id", "organization_id"],
        ["id", "organization_id"],
        ondelete="RESTRICT",
    )


def _create_item() -> None:
    op.create_table(
        "fiscal_inbound_item",
        _uuid(),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("fiscal_inbound_document_id", sa.Uuid(), nullable=False),
        sa.Column("line_number", sa.Integer(), nullable=False),
        sa.Column("supplier_code", sa.Text(), nullable=True),
        sa.Column("gtin", sa.Text(), nullable=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("ncm", sa.Text(), nullable=True),
        sa.Column("cfop", sa.Text(), nullable=True),
        sa.Column("cest", sa.Text(), nullable=True),
        sa.Column("unit_code", sa.Text(), nullable=True),
        sa.Column("quantity", sa.Numeric(18, 6), nullable=False),
        sa.Column("unit_price", sa.Numeric(18, 6), nullable=True),
        sa.Column("gross_amount", sa.Numeric(18, 6), nullable=True),
        sa.Column("discount", sa.Numeric(18, 6), nullable=True),
        sa.Column("freight", sa.Numeric(18, 6), nullable=True),
        sa.Column("declared_total", sa.Numeric(18, 6), nullable=True),
        _jsonb("taxes"),
        sa.Column(
            "match_status", sa.Text(), server_default=sa.text("'unmatched'"), nullable=False
        ),
        sa.Column("target_type", sa.Text(), nullable=True),
        sa.Column("target_id", sa.Uuid(), nullable=True),
        sa.Column("inventory_item_id", sa.Uuid(), nullable=True),
        sa.Column("conversion_factor", sa.Numeric(28, 10), nullable=True),
        sa.Column("converted_quantity", sa.Numeric(18, 6), nullable=True),
        sa.Column("converted_unit_code", sa.Text(), nullable=True),
        _jsonb("conversion_memory"),
        sa.Column("unit_cost", sa.Numeric(18, 6), nullable=True),
        _row_version(),
        _created_at(),
        _updated_at(),
        sa.CheckConstraint("line_number > 0", name="ck_fiscal_inbound_item_line"),
        sa.CheckConstraint("quantity > 0", name="ck_fiscal_inbound_item_quantity"),
        sa.CheckConstraint(
            "match_status IN ('unmatched','suggested','matched','ignored')",
            name="ck_fiscal_inbound_item_match_status",
        ),
        sa.CheckConstraint(
            "target_type IS NULL OR target_type IN ('ingredient','product')",
            name="ck_fiscal_inbound_item_target_type",
        ),
        sa.CheckConstraint(
            "(target_type IS NULL) = (target_id IS NULL)",
            name="ck_fiscal_inbound_item_target_pair",
        ),
        sa.CheckConstraint(
            "conversion_factor IS NULL OR conversion_factor > 0",
            name="ck_fiscal_inbound_item_factor",
        ),
        _document_fk(),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_fiscal_inbound_item_id_org",
        "fiscal_inbound_item",
        ["id", "organization_id"],
        unique=True,
    )
    op.create_index(
        "uq_fiscal_inbound_item_line",
        "fiscal_inbound_item",
        ["fiscal_inbound_document_id", "line_number"],
        unique=True,
    )
    op.create_index(
        "ix_fiscal_inbound_item_match",
        "fiscal_inbound_item",
        ["organization_id", "match_status"],
    )


def _create_attachment() -> None:
    op.create_table(
        "fiscal_inbound_attachment",
        _uuid(),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("fiscal_inbound_document_id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("content_type", sa.Text(), nullable=False),
        sa.Column("byte_size", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.Text(), nullable=False),
        sa.Column("storage_key", sa.Text(), nullable=False),
        sa.Column("original_filename", sa.Text(), nullable=True),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        _created_at(),
        sa.CheckConstraint(
            "kind IN ('xml','pdf','image','other')", name="ck_fiscal_inbound_attachment_kind"
        ),
        sa.CheckConstraint(
            "content_type IN ('application/xml','text/xml','application/pdf','image/jpeg','image/png')",
            name="ck_fiscal_inbound_attachment_mime",
        ),
        sa.CheckConstraint(
            "byte_size > 0 AND byte_size <= 8388608",
            name="ck_fiscal_inbound_attachment_size",
        ),
        sa.CheckConstraint(
            "strpos(storage_key, '..') = 0 AND left(storage_key, 1) <> '/' "
            "AND strpos(storage_key, chr(92)) = 0",
            name="ck_fiscal_inbound_attachment_key",
        ),
        _document_fk(),
        sa.ForeignKeyConstraint(["created_by"], ["app_user.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_fiscal_inbound_attachment_id_org",
        "fiscal_inbound_attachment",
        ["id", "organization_id"],
        unique=True,
    )
    op.create_index(
        "uq_fiscal_inbound_attachment_digest",
        "fiscal_inbound_attachment",
        ["fiscal_inbound_document_id", "sha256"],
        unique=True,
    )


def _create_extraction() -> None:
    op.create_table(
        "fiscal_inbound_extraction",
        _uuid(),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("fiscal_inbound_document_id", sa.Uuid(), nullable=False),
        sa.Column("fiscal_inbound_attachment_id", sa.Uuid(), nullable=True),
        sa.Column("provider", sa.Text(), nullable=False),
        sa.Column("provider_version", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), server_default=sa.text("'completed'"), nullable=False),
        sa.Column("confidence", sa.Numeric(6, 4), nullable=True),
        _jsonb("fields"),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        _created_at(),
        sa.CheckConstraint(
            "status IN ('pending','completed','failed')",
            name="ck_fiscal_inbound_extraction_status",
        ),
        sa.CheckConstraint(
            "confidence IS NULL OR (confidence >= 0 AND confidence <= 1)",
            name="ck_fiscal_inbound_extraction_confidence",
        ),
        _document_fk(),
        sa.ForeignKeyConstraint(
            ["fiscal_inbound_attachment_id", "organization_id"],
            ["fiscal_inbound_attachment.id", "fiscal_inbound_attachment.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(["created_by"], ["app_user.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_fiscal_inbound_extraction_id_org",
        "fiscal_inbound_extraction",
        ["id", "organization_id"],
        unique=True,
    )


def _create_item_match() -> None:
    op.create_table(
        "fiscal_item_match",
        _uuid(),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("fiscal_inbound_item_id", sa.Uuid(), nullable=False),
        sa.Column("target_type", sa.Text(), nullable=False),
        sa.Column("target_id", sa.Uuid(), nullable=False),
        sa.Column("inventory_item_id", sa.Uuid(), nullable=True),
        sa.Column("unit_code", sa.Text(), nullable=True),
        sa.Column("conversion_factor", sa.Numeric(28, 10), nullable=True),
        sa.Column("score", sa.Numeric(6, 4), nullable=True),
        sa.Column("strategy", sa.Text(), nullable=False),
        sa.Column("decision", sa.Text(), server_default=sa.text("'suggested'"), nullable=False),
        sa.Column("decided_by", sa.Uuid(), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        _created_at(),
        sa.CheckConstraint(
            "target_type IN ('ingredient','product')", name="ck_fiscal_item_match_target_type"
        ),
        sa.CheckConstraint(
            "decision IN ('suggested','confirmed','rejected')",
            name="ck_fiscal_item_match_decision",
        ),
        sa.CheckConstraint(
            "score IS NULL OR (score >= 0 AND score <= 1)", name="ck_fiscal_item_match_score"
        ),
        _item_fk(),
        sa.ForeignKeyConstraint(["decided_by"], ["app_user.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_fiscal_item_match_id_org",
        "fiscal_item_match",
        ["id", "organization_id"],
        unique=True,
    )
    op.create_index(
        "ix_fiscal_item_match_item",
        "fiscal_item_match",
        ["fiscal_inbound_item_id", "decision"],
    )


def _create_physical_line() -> None:
    op.create_table(
        "fiscal_physical_line",
        _uuid(),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("fiscal_inbound_item_id", sa.Uuid(), nullable=False),
        sa.Column("received_quantity", sa.Numeric(18, 6), nullable=False),
        sa.Column("unit_code", sa.Text(), nullable=False),
        sa.Column("supplier_lot_code", sa.Text(), nullable=True),
        sa.Column("manufactured_on", sa.Date(), nullable=True),
        sa.Column("expires_on", sa.Date(), nullable=True),
        _jsonb("divergence"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("recorded_by", sa.Uuid(), nullable=False),
        sa.Column(
            "recorded_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        _created_at(),
        sa.CheckConstraint("received_quantity >= 0", name="ck_fiscal_physical_line_quantity"),
        _item_fk(),
        sa.ForeignKeyConstraint(["recorded_by"], ["app_user.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_fiscal_physical_line_id_org",
        "fiscal_physical_line",
        ["id", "organization_id"],
        unique=True,
    )
    op.create_index(
        "ix_fiscal_physical_line_item",
        "fiscal_physical_line",
        ["fiscal_inbound_item_id", "recorded_at"],
    )


def _create_cost_allocation() -> None:
    op.create_table(
        "fiscal_cost_allocation",
        _uuid(),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("fiscal_inbound_document_id", sa.Uuid(), nullable=False),
        sa.Column("fiscal_inbound_item_id", sa.Uuid(), nullable=False),
        sa.Column("basis", sa.Text(), nullable=False),
        sa.Column("freight_share", sa.Numeric(18, 6), server_default="0", nullable=False),
        sa.Column("discount_share", sa.Numeric(18, 6), server_default="0", nullable=False),
        sa.Column("other_share", sa.Numeric(18, 6), server_default="0", nullable=False),
        sa.Column("net_amount", sa.Numeric(18, 6), nullable=False),
        sa.Column("unit_cost", sa.Numeric(18, 6), nullable=False),
        _jsonb("memory"),
        sa.Column("algorithm_name", sa.Text(), nullable=False),
        sa.Column("algorithm_version", sa.Text(), nullable=False),
        _created_at(),
        sa.CheckConstraint(
            "basis IN ('gross_amount','quantity')", name="ck_fiscal_cost_allocation_basis"
        ),
        sa.CheckConstraint("unit_cost >= 0", name="ck_fiscal_cost_allocation_unit_cost"),
        _document_fk(),
        _item_fk(),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_fiscal_cost_allocation_id_org",
        "fiscal_cost_allocation",
        ["id", "organization_id"],
        unique=True,
    )
    op.create_index(
        "uq_fiscal_cost_allocation_item",
        "fiscal_cost_allocation",
        ["fiscal_inbound_item_id"],
        unique=True,
    )


def _create_document_event() -> None:
    op.create_table(
        "fiscal_document_event",
        _uuid(),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("fiscal_inbound_document_id", sa.Uuid(), nullable=False),
        sa.Column("event_type", sa.Text(), nullable=False),
        sa.Column("from_status", sa.Text(), nullable=True),
        sa.Column("to_status", sa.Text(), nullable=True),
        _jsonb("payload"),
        sa.Column("actor_user_id", sa.Uuid(), nullable=False),
        sa.Column("correlation_id", sa.Uuid(), nullable=True),
        _created_at(),
        _document_fk(),
        sa.ForeignKeyConstraint(["actor_user_id"], ["app_user.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_fiscal_document_event_id_org",
        "fiscal_document_event",
        ["id", "organization_id"],
        unique=True,
    )
    op.create_index(
        "ix_fiscal_document_event_document",
        "fiscal_document_event",
        ["fiscal_inbound_document_id", "created_at"],
    )


def _create_certificate() -> None:
    op.create_table(
        "establishment_fiscal_certificate",
        _uuid(),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("establishment_id", sa.Uuid(), nullable=False),
        sa.Column("alias", sa.Text(), nullable=False),
        sa.Column("subject_name", sa.Text(), nullable=True),
        sa.Column("tax_id", sa.Text(), nullable=True),
        sa.Column("not_before", sa.DateTime(timezone=True), nullable=True),
        sa.Column("not_after", sa.DateTime(timezone=True), nullable=True),
        sa.Column("secret_ref", sa.Text(), nullable=False),
        sa.Column(
            "environment",
            sa.Text(),
            server_default=sa.text("'homologation'"),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Text(),
            server_default=sa.text("'not_configured'"),
            nullable=False,
        ),
        sa.Column(
            "distribution_enabled",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column("last_consultation_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_nsu", sa.Text(), nullable=True),
        sa.Column("diagnosis", sa.Text(), nullable=True),
        _row_version(),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        _created_at(),
        _updated_at(),
        sa.CheckConstraint(
            "status IN ('not_configured','validating','active','expired','revoked','error')",
            name="ck_establishment_fiscal_certificate_status",
        ),
        sa.CheckConstraint(
            "environment IN ('homologation','production')",
            name="ck_establishment_fiscal_certificate_environment",
        ),
        sa.CheckConstraint(
            "char_length(secret_ref) > 0 AND secret_ref NOT LIKE '%PRIVATE KEY%' "
            "AND secret_ref NOT LIKE '%password%' AND lower(secret_ref) NOT LIKE '%senha%'",
            name="ck_establishment_fiscal_certificate_secret_ref",
        ),
        sa.ForeignKeyConstraint(["organization_id"], ["organization.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["establishment_id", "organization_id"],
            ["establishment.id", "establishment.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(["created_by"], ["app_user.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_establishment_fiscal_certificate_id_org",
        "establishment_fiscal_certificate",
        ["id", "organization_id"],
        unique=True,
    )
    op.create_index(
        "uq_establishment_fiscal_certificate_alias",
        "establishment_fiscal_certificate",
        ["organization_id", "establishment_id", "alias"],
        unique=True,
    )


def _create_supplier_item_link() -> None:
    op.create_table(
        "supplier_item_link",
        _uuid(),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("supplier_id", sa.Uuid(), nullable=False),
        sa.Column("supplier_code", sa.Text(), nullable=True),
        sa.Column("gtin", sa.Text(), nullable=True),
        sa.Column("target_type", sa.Text(), nullable=False),
        sa.Column("target_id", sa.Uuid(), nullable=False),
        sa.Column("unit_code", sa.Text(), nullable=True),
        sa.Column("conversion_factor", sa.Numeric(28, 10), server_default="1", nullable=False),
        sa.Column("confirmed_by", sa.Uuid(), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        _row_version(),
        _created_at(),
        _updated_at(),
        sa.CheckConstraint(
            "target_type IN ('ingredient','product')", name="ck_supplier_item_link_target_type"
        ),
        sa.CheckConstraint(
            "supplier_code IS NOT NULL OR gtin IS NOT NULL",
            name="ck_supplier_item_link_reference",
        ),
        sa.CheckConstraint("conversion_factor > 0", name="ck_supplier_item_link_factor"),
        sa.ForeignKeyConstraint(["organization_id"], ["organization.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["supplier_id", "organization_id"],
            ["supplier.id", "supplier.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(["confirmed_by"], ["app_user.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_supplier_item_link_id_org",
        "supplier_item_link",
        ["id", "organization_id"],
        unique=True,
    )
    op.create_index(
        "uq_supplier_item_link_code",
        "supplier_item_link",
        ["organization_id", "supplier_id", "supplier_code"],
        unique=True,
        postgresql_where=sa.text("supplier_code IS NOT NULL"),
    )
    op.create_index(
        "uq_supplier_item_link_gtin",
        "supplier_item_link",
        ["organization_id", "supplier_id", "gtin"],
        unique=True,
        postgresql_where=sa.text("gtin IS NOT NULL"),
    )


def _relax_receipt() -> None:
    op.execute(
        """
        DO $$
        DECLARE target text;
        BEGIN
          SELECT c.conname INTO target
          FROM pg_constraint c
          WHERE c.conrelid = 'procurement_receipt'::regclass
            AND c.contype = 'f'
            AND c.conkey @> ARRAY[(
              SELECT a.attnum FROM pg_attribute a
              WHERE a.attrelid = 'procurement_receipt'::regclass
                AND a.attname = 'procurement_order_id'
            )]
          LIMIT 1;
          IF target IS NOT NULL THEN
            EXECUTE format('ALTER TABLE procurement_receipt DROP CONSTRAINT %I', target);
          END IF;
        END
        $$
        """
    )
    op.alter_column("procurement_receipt", "procurement_order_id", nullable=True)
    op.create_foreign_key(
        "fk_procurement_receipt_order",
        "procurement_receipt",
        "procurement_order",
        ["procurement_order_id", "organization_id"],
        ["id", "organization_id"],
        ondelete="RESTRICT",
    )
    op.add_column(
        "procurement_receipt",
        sa.Column("source", sa.Text(), server_default=sa.text("'order'"), nullable=False),
    )
    op.add_column(
        "procurement_receipt",
        sa.Column("fiscal_inbound_document_id", sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        "fk_procurement_receipt_fiscal_document",
        "procurement_receipt",
        "fiscal_inbound_document",
        ["fiscal_inbound_document_id", "organization_id"],
        ["id", "organization_id"],
        ondelete="RESTRICT",
    )
    op.create_check_constraint(
        "ck_procurement_receipt_source",
        "procurement_receipt",
        "(source = 'order' AND procurement_order_id IS NOT NULL AND fiscal_inbound_document_id IS NULL)"
        " OR (source = 'fiscal' AND fiscal_inbound_document_id IS NOT NULL AND procurement_order_id IS NULL)",
    )
    op.create_index(
        "ix_procurement_receipt_fiscal_document",
        "procurement_receipt",
        ["organization_id", "fiscal_inbound_document_id"],
    )

    op.alter_column("procurement_receipt_item", "procurement_order_item_id", nullable=True)
    op.add_column(
        "procurement_receipt_item",
        sa.Column("fiscal_inbound_item_id", sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        "fk_procurement_receipt_item_fiscal_item",
        "procurement_receipt_item",
        "fiscal_inbound_item",
        ["fiscal_inbound_item_id", "organization_id"],
        ["id", "organization_id"],
        ondelete="RESTRICT",
    )
    op.create_check_constraint(
        "ck_procurement_receipt_item_origin",
        "procurement_receipt_item",
        "procurement_order_item_id IS NOT NULL OR fiscal_inbound_item_id IS NOT NULL",
    )


def _seed_permissions() -> None:
    bind = op.get_bind()
    for code, description in FISCAL_PERMISSION_DEFINITIONS:
        bind.execute(
            sa.text(
                "INSERT INTO permission (code, description) "
                "SELECT :code, :description WHERE NOT EXISTS "
                "(SELECT 1 FROM permission WHERE code = :code)"
            ),
            {"code": code, "description": description},
        )
    for role, codes in ROLE_PERMISSIONS.items():
        for code in codes:
            if code not in _CODES:
                continue
            bind.execute(
                sa.text(
                    "INSERT INTO role_permission (role, permission_id) "
                    "SELECT :role, id FROM permission WHERE code = :code "
                    "AND NOT EXISTS ("
                    "SELECT 1 FROM role_permission rp "
                    "WHERE rp.role = :role AND rp.permission_id = permission.id)"
                ),
                {"role": role, "code": code},
            )


def _grant_runtime() -> None:
    table_list = ", ".join(_TABLES)
    for role in _RUNTIME_ROLES:
        op.execute(
            f"""
            DO $$
            BEGIN
              IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{role}') THEN
                GRANT SELECT, INSERT, UPDATE, DELETE ON {table_list} TO {role};
              END IF;
            END
            $$
            """
        )


def upgrade() -> None:
    _create_document()
    _create_item()
    _create_attachment()
    _create_extraction()
    _create_item_match()
    _create_physical_line()
    _create_cost_allocation()
    _create_document_event()
    _create_certificate()
    _create_supplier_item_link()
    _relax_receipt()

    for table in _TABLES:
        _enable_rls(table)
    for table in _TABLES:
        op.execute(
            f"""
            CREATE TRIGGER {table}_forbid_delete
            BEFORE DELETE ON {table}
            FOR EACH ROW EXECUTE FUNCTION panne_forbid_physical_delete();
            """
        )
    for table in _APPEND_ONLY:
        op.execute(
            f"""
            CREATE TRIGGER {table}_append_only
            BEFORE UPDATE ON {table}
            FOR EACH ROW EXECUTE FUNCTION panne_inventory_append_only();
            """
        )

    _seed_permissions()
    _grant_runtime()


def downgrade() -> None:
    bind = op.get_bind()
    for code in sorted(_CODES):
        bind.execute(
            sa.text(
                "DELETE FROM role_permission WHERE permission_id IN "
                "(SELECT id FROM permission WHERE code = :code)"
            ),
            {"code": code},
        )
        bind.execute(sa.text("DELETE FROM permission WHERE code = :code"), {"code": code})

    # Recebimentos de origem fiscal não existem no contrato anterior; removê-los
    # exige suspender o gatilho de proibição de exclusão física.
    op.execute("ALTER TABLE procurement_receipt_item DISABLE TRIGGER procurement_receipt_item_forbid_delete")
    op.execute("ALTER TABLE procurement_receipt DISABLE TRIGGER procurement_receipt_forbid_delete")
    op.execute(
        "DELETE FROM procurement_receipt_item WHERE procurement_receipt_id IN "
        "(SELECT id FROM procurement_receipt WHERE source = 'fiscal')"
    )
    op.execute("DELETE FROM procurement_receipt WHERE source = 'fiscal'")
    op.execute("ALTER TABLE procurement_receipt ENABLE TRIGGER procurement_receipt_forbid_delete")
    op.execute("ALTER TABLE procurement_receipt_item ENABLE TRIGGER procurement_receipt_item_forbid_delete")

    op.drop_constraint(
        "ck_procurement_receipt_item_origin", "procurement_receipt_item", type_="check"
    )
    op.drop_constraint(
        "fk_procurement_receipt_item_fiscal_item", "procurement_receipt_item", type_="foreignkey"
    )
    op.drop_column("procurement_receipt_item", "fiscal_inbound_item_id")
    op.alter_column("procurement_receipt_item", "procurement_order_item_id", nullable=False)

    op.drop_index("ix_procurement_receipt_fiscal_document", table_name="procurement_receipt")
    op.drop_constraint("ck_procurement_receipt_source", "procurement_receipt", type_="check")
    op.drop_constraint(
        "fk_procurement_receipt_fiscal_document", "procurement_receipt", type_="foreignkey"
    )
    op.drop_column("procurement_receipt", "fiscal_inbound_document_id")
    op.drop_column("procurement_receipt", "source")
    op.alter_column("procurement_receipt", "procurement_order_id", nullable=False)

    for table in reversed(_TABLES):
        op.execute(f"DROP TRIGGER IF EXISTS {table}_append_only ON {table}")
        op.execute(f"DROP TRIGGER IF EXISTS {table}_forbid_delete ON {table}")
        op.execute(f"DROP POLICY IF EXISTS rls_{table}_org ON {table}")
    for table in reversed(_TABLES):
        op.drop_table(table)

"""Schema marketplace, só aditivo. Sem chave para fora e sem alterar tabela existente.

Revision ID: b7c4e2a91f30
Revises: e7b3c9a41d06
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "b7c4e2a91f30"
down_revision: Union[str, Sequence[str], None] = "e7b3c9a41d06"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_SCHEMA = "marketplace"


def _json_list():
    return sa.text("'[]'::jsonb")


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS marketplace")
    op.create_table(
        "partners",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("partner_type", sa.String(length=20), nullable=False),
        sa.Column("brand_name", sa.String(length=120), nullable=False),
        sa.Column("brand_slug", sa.String(length=80), nullable=False),
        sa.Column("logo_url", sa.String(length=500), nullable=False, server_default=""),
        sa.Column("photo_url", sa.String(length=500), nullable=False, server_default=""),
        sa.Column("story", sa.Text(), nullable=False, server_default=""),
        sa.Column("city", sa.String(length=80), nullable=False),
        sa.Column("region", sa.String(length=80), nullable=False),
        sa.Column("highlight_hex", sa.String(length=7), nullable=False),
        sa.Column("document", sa.String(length=40), nullable=False),
        sa.Column("contact", sa.String(length=160), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="invited"),
        sa.Column("pay_recipient_id", sa.String(length=80), nullable=True),
        sa.Column("commission_percent", sa.Integer(), nullable=False),
        sa.CheckConstraint(
            "partner_type IN ('producer','distributor','restaurant')",
            name="ck_mp_partners_type",
        ),
        sa.CheckConstraint("status IN ('invited','active','paused')", name="ck_mp_partners_status"),
        sa.CheckConstraint("commission_percent BETWEEN 0 AND 100", name="ck_mp_partners_commission"),
        sa.UniqueConstraint("brand_slug", name="uq_mp_partners_slug"),
        schema=_SCHEMA,
    )
    op.create_table(
        "partner_users",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("email", sa.String(length=160), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=True),
        sa.Column("partner_id", sa.Uuid(), sa.ForeignKey("marketplace.partners.id", ondelete="CASCADE"), nullable=False),
        sa.Column("invite_token_hash", sa.String(length=64), nullable=True),
        sa.Column("invite_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("email", name="uq_mp_partner_users_email"),
        schema=_SCHEMA,
    )
    op.create_table(
        "partner_sessions",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column(
            "partner_user_id",
            sa.Uuid(),
            sa.ForeignKey("marketplace.partner_users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("csrf_token", sa.String(length=128), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("token_hash", name="uq_mp_partner_sessions_token"),
        schema=_SCHEMA,
    )
    op.create_table(
        "partner_links",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("partner_id", sa.Uuid(), sa.ForeignKey("marketplace.partners.id", ondelete="CASCADE"), nullable=False),
        sa.Column("category", sa.String(length=32), nullable=False),
        sa.Column("link_type", sa.String(length=20), nullable=False),
        sa.Column("starts_on", sa.Date(), nullable=False),
        sa.Column("ends_on", sa.Date(), nullable=True),
        sa.CheckConstraint("link_type IN ('exclusive','partial','none')", name="ck_mp_partner_links_type"),
        sa.CheckConstraint("ends_on IS NULL OR ends_on >= starts_on", name="ck_mp_partner_links_range"),
        schema=_SCHEMA,
    )
    op.create_table(
        "partner_products",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("partner_id", sa.Uuid(), sa.ForeignKey("marketplace.partners.id", ondelete="CASCADE"), nullable=False),
        sa.Column("category", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("photos", JSONB(), nullable=False, server_default=_json_list()),
        sa.Column("price_cents", sa.Integer(), nullable=False),
        sa.Column("is_available", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("delivery_cities", JSONB(), nullable=False, server_default=_json_list()),
        sa.Column("delivery_districts", JSONB(), nullable=False, server_default=_json_list()),
        sa.Column("delivery_cep_prefixes", JSONB(), nullable=False, server_default=_json_list()),
        sa.Column("delivery_days", sa.Integer(), nullable=True),
        sa.Column("freight_cents", sa.Integer(), nullable=True),
        sa.Column("perishable", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="draft"),
        sa.CheckConstraint(
            "status IN ('draft','pending','returned','approved','rejected','paused')",
            name="ck_mp_products_status",
        ),
        sa.CheckConstraint("price_cents >= 0", name="ck_mp_products_price"),
        sa.CheckConstraint("delivery_days IS NULL OR delivery_days >= 0", name="ck_mp_products_days"),
        sa.CheckConstraint("freight_cents IS NULL OR freight_cents >= 0", name="ck_mp_products_freight"),
        schema=_SCHEMA,
    )
    op.create_table(
        "product_pairings",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column(
            "product_id",
            sa.Uuid(),
            sa.ForeignKey("marketplace.partner_products.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("house_product_slug", sa.String(length=80), nullable=False),
        sa.Column("reason", sa.String(length=400), nullable=False),
        sa.CheckConstraint("char_length(reason) >= 1", name="ck_mp_pairings_reason"),
        schema=_SCHEMA,
    )
    op.create_table(
        "product_reviews",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column(
            "product_id",
            sa.Uuid(),
            sa.ForeignKey("marketplace.partner_products.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("quality", sa.Integer(), nullable=False),
        sa.Column("visual", sa.Integer(), nullable=False),
        sa.Column("complementarity", sa.Integer(), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("decision", sa.String(length=20), nullable=False),
        sa.Column("reviewer_ref", sa.String(length=120), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("quality BETWEEN 1 AND 5", name="ck_mp_reviews_quality"),
        sa.CheckConstraint("visual BETWEEN 1 AND 5", name="ck_mp_reviews_visual"),
        sa.CheckConstraint("complementarity BETWEEN 1 AND 5", name="ck_mp_reviews_complementarity"),
        sa.CheckConstraint("decision IN ('approve','return','reject')", name="ck_mp_reviews_decision"),
        schema=_SCHEMA,
    )


def downgrade() -> None:
    op.execute("DROP SCHEMA IF EXISTS marketplace CASCADE")

"""M8: pedido da combo (pão da Loja + item do parceiro).

- public.orders: combo_ref + combo_fee_cents (cópia; sem chave para o marketplace).
- marketplace.product_combos: house_unit_price_cents (preço do pão nesta combo).
- marketplace.partner_orders: parte do parceiro; só chaves dentro do schema marketplace.
- email_outbox: kinds combo_order_customer e combo_order_partner.

Revision ID: d8b3f1a65c92
Revises: c4e8b2a91f70
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d8b3f1a65c92"
down_revision: Union[str, Sequence[str], None] = "c4e8b2a91f70"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_SCHEMA = "marketplace"

_PREVIOUS_KINDS = (
    "'order_submitted','payment_approved','order_accepted',"
    "'date_request_received','date_request_proposed','adaptation_proposed',"
    "'customer_verify','customer_resume','order_submitted_admin',"
    "'date_request_received_admin','date_request_available',"
    "'date_request_declined','adaptation_customer_replied_admin',"
    "'ops_attendance_summary','order_auto_accepted_admin',"
    "'date_request_complete','acceptance_update_admin','payment_sync_alert',"
    "'order_date_changed','partner_lead_admin'"
)

_KINDS = _PREVIOUS_KINDS + ",'combo_order_customer','combo_order_partner'"


def upgrade() -> None:
    op.add_column("orders", sa.Column("combo_ref", sa.Uuid(), nullable=True))
    op.add_column("orders", sa.Column("combo_fee_cents", sa.Integer(), nullable=True))
    op.create_check_constraint(
        "ck_orders_combo_fee",
        "orders",
        "combo_fee_cents IS NULL OR combo_fee_cents >= 0",
    )
    op.create_index(
        "ix_orders_combo_ref",
        "orders",
        ["combo_ref"],
        postgresql_where=sa.text("combo_ref IS NOT NULL"),
    )

    op.add_column(
        "product_combos",
        sa.Column("house_unit_price_cents", sa.Integer(), nullable=True),
        schema=_SCHEMA,
    )
    op.create_check_constraint(
        "ck_mp_combos_house_price",
        "product_combos",
        "house_unit_price_cents IS NULL OR house_unit_price_cents > 0",
        schema=_SCHEMA,
    )

    op.create_table(
        "partner_orders",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("public_reference", sa.String(length=20), nullable=False),
        sa.Column("combo_ref", sa.Uuid(), nullable=False),
        sa.Column(
            "partner_id",
            sa.Uuid(),
            sa.ForeignKey("marketplace.partners.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "partner_product_id",
            sa.Uuid(),
            sa.ForeignKey("marketplace.partner_products.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("product_name", sa.String(length=120), nullable=False),
        sa.Column("house_product_name", sa.String(length=120), nullable=False),
        sa.Column("house_order_id", sa.Uuid(), nullable=False),
        sa.Column("requested_date", sa.Date(), nullable=False),
        sa.Column("customer_name", sa.String(length=160), nullable=False),
        sa.Column("address_line", sa.String(length=400), nullable=False),
        sa.Column("item_quantity", sa.Integer(), nullable=False),
        sa.Column("item_cents", sa.Integer(), nullable=False),
        sa.Column("freight_cents", sa.Integer(), nullable=True),
        sa.Column("fee_cents", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="submitted"),
        sa.Column("accept_deadline", sa.DateTime(timezone=True), nullable=True),
        sa.Column("refuse_reason", sa.Text(), nullable=True),
        sa.Column("submit_idempotency_key", sa.String(length=120), nullable=True),
        sa.CheckConstraint(
            "status IN ('submitted','accepted','refused','expired','cancelled','delivered')",
            name="ck_mp_partner_orders_status",
        ),
        sa.CheckConstraint("item_quantity BETWEEN 1 AND 10", name="ck_mp_partner_orders_quantity"),
        sa.CheckConstraint("item_cents >= 0", name="ck_mp_partner_orders_item"),
        sa.CheckConstraint("freight_cents IS NULL OR freight_cents >= 0", name="ck_mp_partner_orders_freight"),
        sa.CheckConstraint("fee_cents >= 0", name="ck_mp_partner_orders_fee"),
        sa.UniqueConstraint("public_reference", name="uq_mp_partner_orders_reference"),
        schema=_SCHEMA,
    )
    op.create_index("ix_mp_partner_orders_combo_ref", "partner_orders", ["combo_ref"], schema=_SCHEMA)
    op.create_index(
        "ix_mp_partner_orders_partner_status",
        "partner_orders",
        ["partner_id", "status"],
        schema=_SCHEMA,
    )
    op.create_index(
        "uq_mp_partner_orders_idempotency",
        "partner_orders",
        ["partner_id", "submit_idempotency_key"],
        unique=True,
        schema=_SCHEMA,
        postgresql_where=sa.text("submit_idempotency_key IS NOT NULL"),
    )

    op.drop_constraint("ck_email_outbox_kind", "email_outbox", type_="check")
    op.create_check_constraint("ck_email_outbox_kind", "email_outbox", f"kind IN ({_KINDS})")


def downgrade() -> None:
    op.execute("DELETE FROM email_outbox WHERE kind IN ('combo_order_customer','combo_order_partner')")
    op.drop_constraint("ck_email_outbox_kind", "email_outbox", type_="check")
    op.create_check_constraint("ck_email_outbox_kind", "email_outbox", f"kind IN ({_PREVIOUS_KINDS})")

    op.drop_index("uq_mp_partner_orders_idempotency", table_name="partner_orders", schema=_SCHEMA)
    op.drop_index("ix_mp_partner_orders_partner_status", table_name="partner_orders", schema=_SCHEMA)
    op.drop_index("ix_mp_partner_orders_combo_ref", table_name="partner_orders", schema=_SCHEMA)
    op.drop_table("partner_orders", schema=_SCHEMA)

    op.drop_constraint("ck_mp_combos_house_price", "product_combos", schema=_SCHEMA, type_="check")
    op.drop_column("product_combos", "house_unit_price_cents", schema=_SCHEMA)

    op.drop_index("ix_orders_combo_ref", table_name="orders")
    op.drop_constraint("ck_orders_combo_fee", "orders", type_="check")
    op.drop_column("orders", "combo_fee_cents")
    op.drop_column("orders", "combo_ref")

"""Marcador gerencial de teste e alertas do proprietário. Não apaga pedido.

Revision ID: f9c2a6e81b04
Revises: e8a1b7c42d19
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "f9c2a6e81b04"
down_revision: Union[str, Sequence[str], None] = "e8a1b7c42d19"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_KINDS = (
    "'order_submitted','payment_approved','order_accepted',"
    "'date_request_received','date_request_proposed','adaptation_proposed',"
    "'customer_verify','customer_resume','order_submitted_admin',"
    "'date_request_received_admin','date_request_available',"
    "'date_request_declined','adaptation_customer_replied_admin',"
    "'ops_attendance_summary','order_auto_accepted_admin',"
    "'date_request_complete','acceptance_update_admin'"
)


def upgrade() -> None:
    op.create_table(
        "managerial_exclusions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("subject_type", sa.String(length=20), nullable=False),
        sa.Column("subject_id", sa.Uuid(), nullable=False),
        sa.Column("reason", sa.String(length=280), nullable=False),
        sa.Column("author_ref", sa.String(length=120), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("reversed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reversed_by", sa.String(length=120), nullable=True),
        sa.Column("reverse_reason", sa.String(length=280), nullable=True),
        sa.CheckConstraint(
            "subject_type IN ('order','date_request')",
            name="ck_managerial_exclusions_subject",
        ),
    )
    op.create_index(
        "uq_managerial_exclusion_active",
        "managerial_exclusions",
        ["subject_type", "subject_id"],
        unique=True,
        postgresql_where=sa.text("reversed_at IS NULL"),
    )
    op.create_table(
        "ops_owner_alerts",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("channel", sa.String(length=20), nullable=False),
        sa.Column("event_key", sa.String(length=160), nullable=False),
        sa.Column("kind", sa.String(length=40), nullable=False),
        sa.Column("order_id", sa.Uuid(), nullable=True),
        sa.Column("date_request_id", sa.Uuid(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("summary", sa.String(length=500), nullable=False),
        sa.Column("last_error", sa.String(length=280), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("provider_reference", sa.String(length=120), nullable=True),
        sa.Column("email_outbox_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("channel IN ('email','whatsapp')", name="ck_ops_owner_alerts_channel"),
        sa.CheckConstraint(
            "status IN ('awaiting','accepted','delivered','failed','disabled')",
            name="ck_ops_owner_alerts_status",
        ),
        sa.UniqueConstraint("event_key", "channel", name="uq_ops_owner_alerts_event_channel"),
    )
    op.create_table(
        "ops_channel_settings",
        sa.Column("channel", sa.String(length=20), primary_key=True),
        sa.Column("destination", sa.String(length=40), nullable=False, server_default=""),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_by", sa.String(length=120), nullable=False, server_default=""),
        sa.CheckConstraint("channel IN ('whatsapp')", name="ck_ops_channel_settings_channel"),
    )
    op.drop_constraint("ck_email_outbox_kind", "email_outbox", type_="check")
    op.create_check_constraint(
        "ck_email_outbox_kind",
        "email_outbox",
        f"kind IN ({_KINDS})",
    )


def downgrade() -> None:
    op.drop_constraint("ck_email_outbox_kind", "email_outbox", type_="check")
    op.create_check_constraint(
        "ck_email_outbox_kind",
        "email_outbox",
        "kind IN ("
        "'order_submitted','payment_approved','order_accepted',"
        "'date_request_received','date_request_proposed','adaptation_proposed',"
        "'customer_verify','customer_resume','order_submitted_admin',"
        "'date_request_received_admin','date_request_available',"
        "'date_request_declined','adaptation_customer_replied_admin',"
        "'ops_attendance_summary','order_auto_accepted_admin',"
        "'date_request_complete')",
    )
    op.drop_table("ops_channel_settings")
    op.drop_table("ops_owner_alerts")
    op.drop_index("uq_managerial_exclusion_active", table_name="managerial_exclusions")
    op.drop_table("managerial_exclusions")

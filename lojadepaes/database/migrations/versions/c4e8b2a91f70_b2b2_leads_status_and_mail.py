"""B2B2: status dos leads + kind partner_lead_admin no outbox.

Revision ID: c4e8b2a91f70
Revises: f2a9c1b84e30
"""

from typing import Sequence, Union

from alembic import op

revision: str = "c4e8b2a91f70"
down_revision: Union[str, Sequence[str], None] = "f2a9c1b84e30"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_SCHEMA = "marketplace"

_KINDS = (
    "'order_submitted','payment_approved','order_accepted',"
    "'date_request_received','date_request_proposed','adaptation_proposed',"
    "'customer_verify','customer_resume','order_submitted_admin',"
    "'date_request_received_admin','date_request_available',"
    "'date_request_declined','adaptation_customer_replied_admin',"
    "'ops_attendance_summary','order_auto_accepted_admin',"
    "'date_request_complete','acceptance_update_admin','payment_sync_alert',"
    "'order_date_changed','partner_lead_admin'"
)

_PREVIOUS_KINDS = (
    "'order_submitted','payment_approved','order_accepted',"
    "'date_request_received','date_request_proposed','adaptation_proposed',"
    "'customer_verify','customer_resume','order_submitted_admin',"
    "'date_request_received_admin','date_request_available',"
    "'date_request_declined','adaptation_customer_replied_admin',"
    "'ops_attendance_summary','order_auto_accepted_admin',"
    "'date_request_complete','acceptance_update_admin','payment_sync_alert',"
    "'order_date_changed'"
)


def upgrade() -> None:
    op.drop_constraint("ck_mp_partner_leads_status", "partner_leads", schema=_SCHEMA, type_="check")
    op.create_check_constraint(
        "ck_mp_partner_leads_status",
        "partner_leads",
        "status IN ('new','contacting','invited','discarded')",
        schema=_SCHEMA,
    )
    op.drop_constraint("ck_email_outbox_kind", "email_outbox", type_="check")
    op.create_check_constraint(
        "ck_email_outbox_kind",
        "email_outbox",
        f"kind IN ({_KINDS})",
    )


def downgrade() -> None:
    op.execute("DELETE FROM email_outbox WHERE kind = 'partner_lead_admin'")
    op.drop_constraint("ck_email_outbox_kind", "email_outbox", type_="check")
    op.create_check_constraint(
        "ck_email_outbox_kind",
        "email_outbox",
        f"kind IN ({_PREVIOUS_KINDS})",
    )
    op.execute(
        "UPDATE marketplace.partner_leads SET status = 'new' "
        "WHERE status NOT IN ('new')"
    )
    op.drop_constraint("ck_mp_partner_leads_status", "partner_leads", schema=_SCHEMA, type_="check")
    op.create_check_constraint(
        "ck_mp_partner_leads_status",
        "partner_leads",
        "status IN ('new')",
        schema=_SCHEMA,
    )
